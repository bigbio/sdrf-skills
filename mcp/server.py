"""
SDRF Skills MCP Server

Implements tools for SDRF annotation workflow:
- PRIDE: project metadata (with pre-resolved publications) + file list
- Europe PMC: unified article metadata (PMID/PMCID/DOI) + JATS full text
- Unpaywall: open-access PDF discovery and download
- OLS: ontology term search for SDRF column annotation
"""

import os
import re
import threading
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
import httpx

mcp = FastMCP(
    "sdrf-pride-pmc",
    instructions="PRIDE, Europe PMC, Unpaywall, and OLS tools for SDRF annotation workflow",
)

PRIDE_BASE = "https://www.ebi.ac.uk/pride/ws/archive/v2"
EUROPE_PMC_BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"
OLS_BASE = "https://www.ebi.ac.uk/ols4/api"
UNPAYWALL_BASE = "https://api.unpaywall.org/v2"

_USER_AGENT = "sdrf-skills-mcp/0.1 (+https://github.com/bigbio/sdrf-skills)"
_DEFAULT_TIMEOUT = 30.0

# -----------------------------------------------------------------------------
# Shared HTTP client (process-wide singleton) — enables TCP/TLS connection reuse
# across tool calls within a single MCP session.
# -----------------------------------------------------------------------------
_client: httpx.Client | None = None
_client_lock = threading.Lock()


def _get_client() -> httpx.Client:
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = httpx.Client(
                    timeout=_DEFAULT_TIMEOUT,
                    follow_redirects=True,
                    headers={
                        "User-Agent": _USER_AGENT,
                        "Accept": "application/json",
                    },
                )
    return _client


# -----------------------------------------------------------------------------
# Process-local JSON cache keyed by url + params. Bounded FIFO to avoid leak.
# -----------------------------------------------------------------------------
_json_cache: dict[str, Any] = {}
_CACHE_MAX = 512


def _cached_get_json(
    url: str, params: dict | None = None, timeout: float | None = None
) -> dict | None:
    """GET → JSON with process-local caching. Returns None on non-200 or network error."""
    key = url + "|" + repr(sorted((params or {}).items()))
    hit = _json_cache.get(key)
    if hit is not None:
        return hit
    try:
        resp = _get_client().get(
            url, params=params, timeout=timeout or _DEFAULT_TIMEOUT
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
    except Exception:
        return None
    if len(_json_cache) >= _CACHE_MAX:
        _json_cache.pop(next(iter(_json_cache)))
    _json_cache[key] = data
    return data


def _resolve_publication(pmid: str | None, doi: str | None, reference: str) -> dict:
    """
    Resolve a single PRIDE reference to {pmid, pmcid, doi, is_open_access, reference}
    via Europe PMC (one request, cached). Prefer PMID as query; fall back to DOI.
    If neither resolves, return whatever PRIDE gave us.
    """
    pmid = str(pmid).strip() if pmid else None
    doi = str(doi).strip() if doi else None

    hit = None
    if pmid and pmid != "0":
        hit = _europe_pmc_lookup(f"EXT_ID:{pmid}")
    if hit is None and doi:
        hit = _europe_pmc_lookup(f"DOI:{doi}")

    if hit is None:
        return {
            "pmid": pmid, "pmcid": None, "doi": doi,
            "is_open_access": False, "reference": reference,
        }
    return {
        "pmid": hit.get("pmid") or pmid,
        "pmcid": hit.get("pmcid"),
        "doi": hit.get("doi") or doi,
        "is_open_access": hit.get("isOpenAccess") == "Y",
        "reference": reference,
    }


# --- 1.1 Get PRIDE project metadata ---
@mcp.tool()
def get_project_details(project_accession: str) -> dict:
    """
    Get PRIDE project metadata by accession (e.g., PXD012345).

    `publications` is a list of resolved records, one per PRIDE reference:
    {pmid, pmcid, doi, is_open_access, reference}. Use these fields directly
    to decide which article tool to call next:
      - pmcid set AND is_open_access=True → get_full_text_article(pmc_ids=[pmcid])
      - otherwise (pmid and/or doi set)   → get_article_metadata(ids=[<any-id>])
      - nothing set                       → ask the user for the publication.

    Returns: title, description, sample_processing_protocol, data_processing_protocol,
    organism, instruments, modifications, publications, keywords.
    """
    data = _cached_get_json(f"{PRIDE_BASE}/projects/{project_accession}")
    if data is None:
        return {
            "accession": project_accession,
            "error": "PRIDE project not found or API unreachable",
        }

    organisms = [o.get("name", "") for o in data.get("organisms", [])]
    instruments = [i.get("name", "") for i in data.get("instruments", [])]
    mods = [m.get("name", "") for m in data.get("identifiedPTMStrings", [])]

    publications: list[dict] = []
    for r in data.get("references", []) or []:
        pmid = r.get("pubmedID")
        doi = r.get("doi")
        reference = r.get("referenceLine", "") or ""
        if not pmid and not doi:
            publications.append({
                "pmid": None, "pmcid": None, "doi": None,
                "is_open_access": False, "reference": reference,
            })
            continue
        publications.append(_resolve_publication(pmid, doi, reference))

    return {
        "accession": data.get("accession"),
        "title": data.get("title"),
        "description": data.get("projectDescription"),
        "sample_processing_protocol": data.get("sampleProcessingProtocol"),
        "data_processing_protocol": data.get("dataProcessingProtocol"),
        "organism": organisms,
        "instruments": instruments,
        "modifications": mods,
        "publications": publications,
        "keywords": data.get("keywords", []),
    }


# --- 1.2 Get project file list ---
# PRIDE 的 fileCategory 只覆盖主流厂商，其余落到 extension 判定
RAW_LIKE_CATEGORIES = {"RAW", "SWIFF"}
RAW_LIKE_EXTENSIONS = {
    ".raw",            # Thermo
    ".wiff", ".wiff2", ".wiff.scan",  # Sciex
    ".d",              # Bruker (文件夹但 PRIDE 打包成 .d.zip / .d.tar)
    ".mzml", ".mzxml", # Bruker/其它仪器导出的峰列表（也算 raw-like）
    ".lcd",            # Shimadzu
    ".baf", ".tdf", ".tsf",  # Bruker timsTOF
}


def _is_raw_like(name: str, category: str) -> bool:
    if category in RAW_LIKE_CATEGORIES:
        return True
    name_lower = name.lower()
    # 处理 .d.tar / .d.zip / foo.raw.gz 这类打包
    for ext in RAW_LIKE_EXTENSIONS:
        if name_lower.endswith(ext) or ext + "." in name_lower:
            return True
    return False


def _extract_root_urls(files: list[dict]) -> dict:
    """
    Derive the PRIDE project-level download root from any file's publicFileLocations.
    PRIDE stores each file under .../archive/YYYY/MM/PXDxxxxxx/[generated/]<file>.
    We strip the filename to expose the shared parent directory.
    """
    ftp_root = None
    aspera_root = None
    for f in files:
        for loc in f.get("publicFileLocations", []) or []:
            if not isinstance(loc, dict):
                continue
            name = loc.get("name", "")
            val = loc.get("value", "") or ""
            if not val:
                continue
            parent = val.rsplit("/", 1)[0] + "/"
            # Trim trailing 'generated/' so the root is the PXD folder itself
            if parent.endswith("/generated/"):
                parent = parent[: -len("generated/")]
            if name == "FTP Protocol" and ftp_root is None:
                # Prefer HTTPS mirror (ftp.ebi.ac.uk supports https directly)
                if parent.startswith("ftp://ftp.pride.ebi.ac.uk/"):
                    ftp_root = "https://ftp.pride.ebi.ac.uk/" + parent[len("ftp://ftp.pride.ebi.ac.uk/"):]
                elif parent.startswith("ftp://"):
                    ftp_root = parent.replace("ftp://", "https://", 1)
                else:
                    ftp_root = parent
            elif name == "Aspera Protocol" and aspera_root is None:
                aspera_root = parent
        if ftp_root and aspera_root:
            break
    return {"ftp_root_url": ftp_root, "aspera_root_url": aspera_root}


@mcp.tool()
def get_project_files(project_accession: str) -> dict:
    """
    Get file list for a PRIDE project. Classifies files as raw-like (Thermo/Sciex/
    Bruker/Shimadzu/mzML...) vs other (fasta, result tables, metadata).
    Returns: rawfile_count, raw_file_names, other_files_names,
    ftp_root_url (HTTPS mirror of the PRIDE FTP directory containing all files),
    aspera_root_url (Aspera path for high-throughput transfer).
    """
    data = _cached_get_json(f"{PRIDE_BASE}/projects/{project_accession}/files")
    if data is None:
        return {
            "project_accession": project_accession,
            "rawfile_count": 0,
            "raw_file_names": [],
            "other_files_names": [],
            "ftp_root_url": None,
            "aspera_root_url": None,
            "error": "PRIDE files API unreachable",
        }

    files = (
        data if isinstance(data, list)
        else data.get("content", []) if isinstance(data, dict) else []
    )

    raw_file_names: list[str] = []
    other_files_names: list[str] = []
    for f in files:
        name = f.get("fileName", "")
        if not name:
            continue
        cat = f.get("fileCategory", {})
        ftype = (cat.get("value", "") if isinstance(cat, dict) else str(cat)).upper()
        if _is_raw_like(name, ftype):
            raw_file_names.append(name)
        else:
            other_files_names.append(name)

    roots = _extract_root_urls(files)
    return {
        "project_accession": project_accession,
        "rawfile_count": len(raw_file_names),
        "raw_file_names": raw_file_names,
        "other_files_names": other_files_names,
        "ftp_root_url": roots["ftp_root_url"],
        "aspera_root_url": roots["aspera_root_url"],
    }


# 下载大小上限：避免 OOM（可通过环境变量覆盖，单位 MB）
_MAX_DOWNLOAD_MB = int(os.environ.get("SDRF_MCP_MAX_DOWNLOAD_MB", "500"))
_MAX_DOWNLOAD_BYTES = _MAX_DOWNLOAD_MB * 1024 * 1024


def _stream_download(
    client: httpx.Client, url: str, dest: Path, timeout: float = 180.0
) -> tuple[bool, str]:
    """
    流式下载到 dest。返回 (success, message)。超过 _MAX_DOWNLOAD_BYTES 立刻中止。
    """
    try:
        with client.stream("GET", url, timeout=timeout) as resp:
            if resp.status_code != 200:
                return False, f"HTTP {resp.status_code}"
            total = 0
            with open(dest, "wb") as fh:
                for chunk in resp.iter_bytes():
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > _MAX_DOWNLOAD_BYTES:
                        fh.close()
                        dest.unlink(missing_ok=True)
                        return False, (
                            f"Download aborted: exceeded {_MAX_DOWNLOAD_MB} MB cap"
                        )
                    fh.write(chunk)
            return True, "ok"
    except Exception as e:
        dest.unlink(missing_ok=True)
        return False, str(e)


def _extract_pdf_url(r: dict) -> str | None:
    """从 Europe PMC 结果中提取 PDF URL。"""
    ft_list = r.get("fullTextUrlList", {})
    if isinstance(ft_list, dict):
        urls = ft_list.get("fullTextUrl", [])
    else:
        urls = []
    if not isinstance(urls, list):
        urls = [urls] if urls else []
    for u in urls:
        if isinstance(u, dict) and u.get("documentStyle") == "pdf":
            return u.get("url")
    return None


# -----------------------------------------------------------------------------
# Europe PMC unified lookup + article record helpers (used by multiple tools)
# -----------------------------------------------------------------------------
def _europe_pmc_lookup(query: str) -> dict | None:
    """Query Europe PMC /search with given Lucene query; return first hit or None."""
    data = _cached_get_json(
        f"{EUROPE_PMC_BASE}/search",
        params={"query": query, "format": "json", "pageSize": 1, "resultType": "core"},
    )
    if not data:
        return None
    hits = data.get("resultList", {}).get("result", [])
    return hits[0] if hits else None


def _hit_to_article_record(hit: dict) -> dict:
    """Convert a Europe PMC core hit into the standard article record shape."""
    pmid = hit.get("pmid")
    doi = hit.get("doi")
    return {
        "pmid": pmid,
        "pmcid": hit.get("pmcid"),
        "doi": doi,
        "title": hit.get("title"),
        "authors": hit.get("authorString"),
        "journal": hit.get("journalTitle"),
        "year": hit.get("pubYear"),
        "abstract": hit.get("abstractText", "") or "",
        "inPMC": hit.get("inPMC") == "Y",
        "isOpenAccess": hit.get("isOpenAccess") == "Y",
        "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None,
        "doi_url": f"https://doi.org/{doi}" if doi else None,
        "pdf_url": _extract_pdf_url(hit),
    }


def _empty_article_record(**known: Any) -> dict:
    """Standard article record with all keys None/default; `known` overrides."""
    base = {
        "pmid": None, "pmcid": None, "doi": None,
        "title": None, "authors": None, "abstract": "",
        "journal": None, "year": None,
        "pubmed_url": None, "doi_url": None, "pdf_url": None,
        "inPMC": False, "isOpenAccess": False,
    }
    base.update(known)
    return base


# DOI 基本形状：10.<registrant>/<suffix>，其中 suffix 里允许 [-._;()/:A-Za-z0-9]
_DOI_REGEX = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$")


def _classify_article_id(raw: str) -> tuple[str, str] | None:
    """
    Classify a free-form article identifier into ('pmid'|'pmcid'|'doi', normalised).
    Returns None if the string is empty or not recognised.
    """
    s = str(raw).strip()
    if not s or s == "0":
        return None
    su = s.upper()
    if su.startswith("PMC") and su[3:].isdigit():
        return ("pmcid", su)
    if s.isdigit():
        return ("pmid", s)
    # DOI (strict)
    if _DOI_REGEX.match(s):
        return ("doi", s)
    # Defensive: sometimes PRIDE/user strips the "10." prefix
    if "." in s and "/" in s and _DOI_REGEX.match(f"10.{s}"):
        return ("doi", f"10.{s}")
    return None


# --- 1.3 Get article metadata (unified: PMID / PMCID / DOI) ---
@mcp.tool()
def get_article_metadata(ids: list[str]) -> list[dict]:
    """
    Get article metadata via Europe PMC for any mix of PMID / PMCID / DOI.
    Each element of `ids` is auto-classified:
      - all digits              → PMID   (query EXT_ID:<id>)
      - starts with 'PMC'+digits → PMCID (query PMCID:<id>)
      - matches DOI regex       → DOI   (query DOI:<id>)
    Unrecognised identifiers yield a record with an `error` field.

    Returns one record per input with:
      pmid, pmcid, doi, title, authors, abstract, journal, year,
      pubmed_url, doi_url, pdf_url, inPMC, isOpenAccess.
    """
    results: list[dict] = []
    for raw in ids:
        cls = _classify_article_id(raw)
        if cls is None:
            rec = _empty_article_record()
            rec["input"] = raw
            rec["error"] = "Unrecognised identifier (need PMID / PMCID / DOI)"
            results.append(rec)
            continue
        kind, val = cls
        if kind == "pmid":
            query = f"EXT_ID:{val}"
        elif kind == "pmcid":
            query = f"PMCID:{val}"
        else:  # doi
            query = f"DOI:{val}"

        hit = _europe_pmc_lookup(query)
        if hit is None:
            rec = _empty_article_record(**{kind: val})
            if kind == "pmid":
                rec["pubmed_url"] = f"https://pubmed.ncbi.nlm.nih.gov/{val}/"
            elif kind == "doi":
                rec["doi_url"] = f"https://doi.org/{val}"
            rec["error"] = "Not found in Europe PMC"
            results.append(rec)
            continue

        rec = _hit_to_article_record(hit)
        # Preserve the queried identifier even if Europe PMC omits it from the hit
        if kind == "pmid":
            rec["pmid"] = rec.get("pmid") or val
            rec["pubmed_url"] = (
                rec.get("pubmed_url") or f"https://pubmed.ncbi.nlm.nih.gov/{val}/"
            )
        elif kind == "pmcid":
            rec["pmcid"] = rec.get("pmcid") or val
        else:  # doi
            rec["doi"] = rec.get("doi") or val
            rec["doi_url"] = rec.get("doi_url") or f"https://doi.org/{val}"
        results.append(rec)
    return results


def _looks_like_doi(s: str) -> bool:
    return bool(_DOI_REGEX.match(s))


def _parse_identifier(s: str) -> tuple[str, str] | None:
    """解析 identifier，返回 (type, value) 或 None（如果无法识别）。
    支持：DOI、PMID、pubmed URL、doi.org URL。非法字符串返回 None。"""
    s = str(s).strip()
    if not s:
        return None
    s_lower = s.lower()

    if "doi.org/" in s_lower:
        idx = s_lower.find("doi.org/")
        doi = s[idx + len("doi.org/") :].split("?", 1)[0].strip("/")
        return ("doi", doi) if _looks_like_doi(doi) else None

    if "pubmed.ncbi.nlm.nih.gov" in s_lower or "pubmed.gov" in s_lower:
        parts = s.replace("?", "/").rstrip("/").split("/")
        for p in reversed(parts):
            if p.isdigit():
                return ("pmid", p)
        return None

    if s.isdigit():
        return ("pmid", s)

    if s.upper().startswith("PMC"):
        return None  # PMCID 不在本函数处理范围

    # Candidate DOI: strip query string, then strict regex test
    candidate = s.split("?", 1)[0]
    if _looks_like_doi(candidate):
        return ("doi", candidate)

    return None  # 严格模式：不认识的字符串一律拒


def _doi_to_subdir_name(doi: str) -> str:
    """将 DOI 转为安全的子目录名（用于 pdf/{subdir}/）。"""
    return doi.replace("/", "_").replace(":", "_").strip()


def _unpaywall_save_dir(out_path: Path, parsed_type: str, pmid: str | None, doi: str) -> Path:
    """
    按输入类型决定保存目录：PMID/PubMed URL → pdf/{PMID}/；DOI 或 doi.org 链接 → pdf/{sanitized_doi}/。
    """
    if parsed_type == "pmid" and pmid:
        return out_path / pmid
    return out_path / _doi_to_subdir_name(doi)


# MCP 目录下的 pdf 子目录为默认保存路径
DEFAULT_PDF_DIR = Path(__file__).resolve().parent / "pdf"


_PDF_MAGIC = b"%PDF-"


def _is_pdf_file(path: Path) -> bool:
    """PDF 魔数校验：首 5 字节为 '%PDF-'。防止 publisher 反爬把 HTML 存成 .pdf。"""
    try:
        with open(path, "rb") as fh:
            return fh.read(5) == _PDF_MAGIC
    except OSError:
        return False


def _unpaywall_result(
    raw: str,
    *,
    doi: str | None = None,
    pmid: str | None = None,
    pdf_url: str | None = None,
    local_path: str | None = None,
    oa_status: str | None = None,
    license_val: str | None = None,
    host_type: str | None = None,
    error: str | None = None,
) -> dict:
    """统一结构的 Unpaywall 结果记录。"""
    rec = {
        "identifier": raw, "doi": doi, "pmid": pmid,
        "pdf_url": pdf_url, "local_path": local_path,
        "oa_status": oa_status, "license": license_val, "host_type": host_type,
    }
    if error:
        rec["error"] = error
    return rec


# --- 1.3f Get PDF via Unpaywall 并下载到本地 ---
@mcp.tool()
def get_pdf_by_unpaywall(identifiers: list[str], output_dir: str | None = None) -> list[dict]:
    """
    Find OA PDF via Unpaywall and download to local. Accepts DOI, PMID, doi_url, or pubmed_url.
    For PMID: resolves to DOI via Europe PMC first. When Unpaywall has no pdf_url, falls back
    to Europe PMC PDF. Downloaded files are validated against the PDF magic bytes; non-PDF
    responses (e.g. publisher anti-bot HTML) are rejected.
    Download is streamed with a size cap (env SDRF_MCP_MAX_DOWNLOAD_MB, default 500 MB).

    Returns: identifier, doi, pmid, pdf_url, local_path, oa_status, license, host_type.
    output_dir: base directory (default: mcp/pdf). Saves as output_dir/{PMID}/fulltext.pdf when
    input is PMID/PubMed URL; otherwise output_dir/{sanitized_doi}/fulltext.pdf.
    """
    email = os.environ.get("UNPAYWALL_EMAIL", "unpaywall@sdrf-skills.local")
    out_path = Path(output_dir if output_dir is not None else DEFAULT_PDF_DIR).resolve()
    out_path.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    client = _get_client()

    for raw in identifiers:
        parsed = _parse_identifier(raw)
        if not parsed:
            results.append(_unpaywall_result(
                raw, error="Could not parse identifier (need DOI or PMID/URL)"))
            continue

        typ, val = parsed
        save_layout_type = typ
        doi: str | None = val if typ == "doi" else None
        pmid: str | None = val if typ == "pmid" else None

        # PMID → DOI via cached Europe PMC lookup
        if typ == "pmid":
            hit = _europe_pmc_lookup(f"EXT_ID:{val}")
            if hit is None:
                results.append(_unpaywall_result(
                    raw, pmid=val, error="PMID not found in Europe PMC"))
                continue
            doi = hit.get("doi")
            if not doi:
                results.append(_unpaywall_result(
                    raw, pmid=val, error="No DOI for this PMID"))
                continue

        if not doi:
            results.append(_unpaywall_result(
                raw, pmid=pmid, error="No DOI to query Unpaywall"))
            continue

        # Unpaywall lookup
        pdf_url = None
        oa_status = "closed"
        license_val = None
        host_type = None
        uw = _cached_get_json(f"{UNPAYWALL_BASE}/{doi}", params={"email": email})
        if uw:
            best = uw.get("best_oa_location") or {}
            pdf_url = best.get("url_for_pdf")
            oa_status = uw.get("oa_status") or "closed"
            license_val = best.get("license")
            host_type = best.get("host_type")

        # Fallback to Europe PMC PDF if Unpaywall had nothing
        if not pdf_url:
            hit = _europe_pmc_lookup(f"DOI:{doi}")
            if hit:
                pdf_url = _extract_pdf_url(hit)

        if not pdf_url:
            results.append(_unpaywall_result(
                raw, doi=doi, pmid=pmid,
                oa_status=oa_status, license_val=license_val, host_type=host_type,
                error="No PDF URL found (Unpaywall and Europe PMC)"))
            continue

        # Stream-download and verify PDF magic bytes
        item_dir = _unpaywall_save_dir(out_path, save_layout_type, pmid, doi)
        item_dir.mkdir(parents=True, exist_ok=True)
        local_file = item_dir / "fulltext.pdf"
        ok, msg = _stream_download(client, pdf_url, local_file, timeout=120.0)
        if not ok:
            results.append(_unpaywall_result(
                raw, doi=doi, pmid=pmid, pdf_url=pdf_url,
                oa_status=oa_status, license_val=license_val, host_type=host_type,
                error=f"Download failed: {msg}"))
            continue
        if not _is_pdf_file(local_file):
            local_file.unlink(missing_ok=True)
            results.append(_unpaywall_result(
                raw, doi=doi, pmid=pmid, pdf_url=pdf_url,
                oa_status=oa_status, license_val=license_val, host_type=host_type,
                error="Downloaded file is not a valid PDF (likely publisher anti-bot HTML)"))
            continue

        results.append(_unpaywall_result(
            raw, doi=doi, pmid=pmid, pdf_url=pdf_url, local_path=str(local_file),
            oa_status=oa_status, license_val=license_val, host_type=host_type,
        ))
    return results


# --- 4.3 Search OLS for ontology terms (single ontology) ---
def _ols_doc_to_result(d: dict) -> dict:
    """Minimal OLS hit representation: only the fields needed to cite a term in SDRF."""
    return {
        "label": d.get("label"),
        "accession": d.get("obo_id"),
        "ontology": d.get("ontology_prefix") or d.get("ontology_name"),
    }


def _search_ontology_classes(
    query: str, ontology_id: str, page_size: int = 10, exact: bool = False
) -> dict:
    """Shared impl for OLS search filtered by ontology."""
    params: dict[str, Any] = {
        "q": query,
        "ontology": ontology_id.lower().strip(),
        "rows": min(page_size, 50),
    }
    if exact:
        params["exact"] = "true"
    data = _cached_get_json(f"{OLS_BASE}/search", params=params)
    if not data:
        return {"query": query, "ontology_id": ontology_id, "numFound": 0, "results": []}
    docs = data.get("response", {}).get("docs", [])
    num_found = data.get("response", {}).get("numFound", 0)
    return {
        "query": query,
        "ontology_id": ontology_id,
        "numFound": num_found,
        "results": [_ols_doc_to_result(d) for d in docs],
    }


def _search_all_ontologies(query: str, page_size: int, exact: bool) -> dict:
    """Shared impl for OLS cross-ontology search (no ontology filter)."""
    params: dict[str, Any] = {"q": query, "rows": min(page_size, 50)}
    if exact:
        params["exact"] = "true"
    data = _cached_get_json(f"{OLS_BASE}/search", params=params)
    if not data:
        return {"query": query, "numFound": 0, "results": []}
    docs = data.get("response", {}).get("docs", [])
    num_found = data.get("response", {}).get("numFound", 0)
    return {
        "query": query,
        "numFound": num_found,
        "results": [_ols_doc_to_result(d) for d in docs],
    }


@mcp.tool()
def searchClasses(
    query: str,
    ontologyId: str,
    page_size: int = 3,
    mode: str = "smart",
) -> dict:
    """
    Search OLS (Ontology Lookup Service) for a term in ONE ontology.

    ontologyId: ncbitaxon, uberon, bto, cl, clo, efo, mondo, doid, ncit, pato,
    pride, ms, unimod, mod, chebi, hancestro, envo, po, fbbt, wbbt, zfa, gaz,
    xlmod, go.

    mode (default "smart"):
      - "smart" : try EXACT label/synonym first; if a hit exists, return JUST
                  that single exact match (page_size is ignored). Only when
                  nothing matches exactly, fall back to fuzzy top-`page_size`
                  (default 3). This keeps downstream reasoning uncluttered.
      - "exact" : exact-only, cap results at page_size. Returns empty on miss.
      - "fuzzy" : fuzzy-only, returns top-`page_size` regardless of exact hits.

    Returns {query, ontology_id, numFound, results:[{label, accession, ontology}]}.
    When smart mode falls back to fuzzy, the returned dict carries
    `fallback: "fuzzy"` so callers can tell the match is not exact.
    """
    m = (mode or "smart").lower().strip()
    if m == "exact":
        return _search_ontology_classes(query, ontologyId, page_size, exact=True)
    if m == "fuzzy":
        return _search_ontology_classes(query, ontologyId, page_size, exact=False)

    # smart: exact first (single), fuzzy top-N fallback
    exact_hit = _search_ontology_classes(query, ontologyId, page_size=1, exact=True)
    if exact_hit.get("results"):
        # Align numFound with the slice we actually return, so the AI reads
        # `numFound == len(results)` as "this IS the exact answer".
        exact_hit["numFound"] = len(exact_hit["results"])
        return exact_hit
    fuzzy = _search_ontology_classes(query, ontologyId, page_size, exact=False)
    fuzzy["numFound"] = len(fuzzy.get("results", []))
    fuzzy["fallback"] = "fuzzy"
    return fuzzy


# --- 4.1 Search OLS across ALL ontologies (no filter) ---
@mcp.tool()
def search(query: str, page_size: int = 3, mode: str = "smart") -> dict:
    """
    Search OLS across ALL ontologies. Prefer searchClasses with a specific
    ontologyId for SDRF column annotation; use this only when the target
    ontology is unknown.

    mode (default "smart"):
      - "smart" : exact-first (single hit), fuzzy top-`page_size` fallback.
      - "exact" : exact-only, cap at page_size. Empty on miss.
      - "fuzzy" : fuzzy-only, returns top-`page_size`.

    Returns {query, numFound, results:[{label, accession, ontology}]}.
    Carries `fallback: "fuzzy"` when smart mode falls back.
    """
    m = (mode or "smart").lower().strip()
    if m == "exact":
        return _search_all_ontologies(query, page_size, exact=True)
    if m == "fuzzy":
        return _search_all_ontologies(query, page_size, exact=False)

    exact_hit = _search_all_ontologies(query, page_size=1, exact=True)
    if exact_hit.get("results"):
        exact_hit["numFound"] = len(exact_hit["results"])
        return exact_hit
    fuzzy = _search_all_ontologies(query, page_size, exact=False)
    fuzzy["numFound"] = len(fuzzy.get("results", []))
    fuzzy["fallback"] = "fuzzy"
    return fuzzy


# --- 4.2 Get children of an ontology term (specificity check) ---
def _accession_to_ols_iri(accession: str) -> tuple[str, str] | None:
    """Map 'UNIMOD:1' / 'MONDO:0004992' / ... to (ontology_id, full IRI)."""
    if ":" not in accession:
        return None
    prefix, local = accession.split(":", 1)
    prefix_l = prefix.lower().strip()
    iri_bases = {
        "ncbitaxon": f"http://purl.obolibrary.org/obo/NCBITaxon_{local}",
        "uberon":    f"http://purl.obolibrary.org/obo/UBERON_{local}",
        "efo":       f"http://www.ebi.ac.uk/efo/EFO_{local}",
        "mondo":     f"http://purl.obolibrary.org/obo/MONDO_{local}",
        "cl":        f"http://purl.obolibrary.org/obo/CL_{local}",
        "doid":      f"http://purl.obolibrary.org/obo/DOID_{local}",
        "pato":      f"http://purl.obolibrary.org/obo/PATO_{local}",
        "ms":        f"http://purl.obolibrary.org/obo/MS_{local}",
        "unimod":    f"http://www.unimod.org/obo/unimod#UNIMOD:{local}",
        "hancestro": f"http://purl.obolibrary.org/obo/HANCESTRO_{local}",
        "chebi":     f"http://purl.obolibrary.org/obo/CHEBI_{local}",
        "bto":       f"http://purl.obolibrary.org/obo/BTO_{local}",
        "pride":     f"http://purl.obolibrary.org/obo/PRIDE_{local}",
        "clo":       f"http://purl.obolibrary.org/obo/CLO_{local}",
        "go":        f"http://purl.obolibrary.org/obo/GO_{local}",
        "ncit":      f"http://purl.obolibrary.org/obo/NCIT_{local}",
    }
    iri = iri_bases.get(prefix_l)
    return (prefix_l, iri) if iri else None


def _resolve_ols_term(accession: str) -> tuple[str, str] | None:
    """Fallback: look up (ontology_id, iri) via OLS /search for arbitrary accession.
    Handles ontologies not in our static map (XLMOD, MOD, ENVO, PO, FBBT, ...)."""
    data = _cached_get_json(
        f"{OLS_BASE}/search",
        params={"q": accession, "queryFields": "obo_id", "exact": "true", "rows": 1},
    )
    if not data:
        return None
    docs = data.get("response", {}).get("docs", [])
    if not docs:
        return None
    d = docs[0]
    iri = d.get("iri")
    ont_id = (d.get("ontology_name") or d.get("ontology_prefix") or "").lower()
    return (ont_id, iri) if (iri and ont_id) else None


@mcp.tool()
def getChildren(accession: str, rows: int = 20) -> dict:
    """
    Get direct child terms for an ontology accession (e.g. 'MONDO:0004992').
    Useful for specificity checks: if a term has many specific children, prefer
    a more specific child term in the SDRF characteristic.
    Falls back to OLS /search for ontologies not in the static IRI map.
    Returns: accession, count, children [{label, accession, ontology}].
    """
    parsed = _accession_to_ols_iri(accession)
    if parsed is None:
        # Unknown prefix (e.g. XLMOD, MOD, PO, ENVO) → resolve via OLS search
        parsed = _resolve_ols_term(accession)
        if parsed is None:
            return {"accession": accession, "count": 0, "children": [],
                    "error": "Could not resolve accession in OLS"}
    ont_id, iri = parsed
    encoded_iri = urllib.parse.quote(urllib.parse.quote(iri, safe=""))
    data = _cached_get_json(
        f"{OLS_BASE}/ontologies/{ont_id}/terms/{encoded_iri}/children",
        params={"size": rows},
    )
    if not data:
        return {"accession": accession, "count": 0, "children": [],
                "error": "No children or lookup failed"}
    terms = data.get("_embedded", {}).get("terms", []) or []
    children = []
    for t in terms:
        children.append({
            "label": t.get("label"),
            "accession": t.get("obo_id") or t.get("short_form"),
            "ontology": t.get("ontology_prefix") or t.get("ontology_name") or ont_id,
        })
    return {"accession": accession, "count": len(children), "children": children}


# --- 1.3c Get full-text article (JATS XML from Europe PMC, OA subset) ---
def _iter_text(elem: ET.Element) -> str:
    """Concatenate all text inside an XML element, collapsing whitespace."""
    parts = [t for t in elem.itertext() if t]
    return " ".join(" ".join(parts).split())


_XLINK_HREF = "{http://www.w3.org/1999/xlink}href"


def _table_to_markdown(table_el: ET.Element) -> str:
    """Render a JATS <table> element to a simple markdown pipe-table."""
    rows: list[list[str]] = []
    for tr in table_el.iter("tr"):
        cells = [_iter_text(cell) for cell in tr if cell.tag in ("td", "th")]
        if cells:
            rows.append(cells)
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    md_lines = ["| " + " | ".join(rows[0]) + " |",
                "| " + " | ".join(["---"] * width) + " |"]
    for r in rows[1:]:
        md_lines.append("| " + " | ".join(r) + " |")
    return "\n".join(md_lines)


def _parse_jats_tables(root: ET.Element) -> list[dict]:
    """Extract all <table-wrap> as {label, caption, markdown}.

    `markdown` is the pipe-table rendering of <table>. If the JATS uses an
    unusual layout that _table_to_markdown cannot parse, fall back to the
    flattened text of the whole <table-wrap> so callers still see the data.
    """
    out: list[dict] = []
    for tw in root.iter("table-wrap"):
        label_el = tw.find("label")
        caption_el = tw.find("caption")
        table_el = tw.find("table")
        md = _table_to_markdown(table_el) if table_el is not None else ""
        if not md:
            # Fallback to flattened text so the data is not lost
            md = _iter_text(tw)
        out.append({
            "label": _iter_text(label_el) if label_el is not None else "",
            "caption": _iter_text(caption_el) if caption_el is not None else "",
            "markdown": md,
        })
    return out


def _parse_jats_supplementary(root: ET.Element) -> list[dict]:
    """Extract all <supplementary-material> as {label, caption, href, media_type}.

    JATS commonly repeats the same <supplementary-material> in both <front>
    and <back> sections; deduplicate by href to keep the response compact.
    Entries with empty href are kept as-is (they carry unique captions)."""
    out: list[dict] = []
    seen_hrefs: set[str] = set()
    for sm in root.iter("supplementary-material"):
        label_el = sm.find("label")
        caption_el = sm.find("caption")
        href = sm.get(_XLINK_HREF) or ""
        # Also check nested <media> element (common pattern)
        if not href:
            media = sm.find("media")
            if media is not None:
                href = media.get(_XLINK_HREF) or ""
        if href and href in seen_hrefs:
            continue
        if href:
            seen_hrefs.add(href)
        out.append({
            "label": _iter_text(label_el) if label_el is not None else "",
            "caption": _iter_text(caption_el) if caption_el is not None else "",
            "href": href,
            "media_type": sm.get("mimetype", "") or "",
        })
    return out


# Default keywords for filtering SDRF-relevant sections. Deliberately excludes
# "results" and "discussion" — they rarely carry sample / protocol metadata and
# balloon response size (observed 38 KB of "Results and discussion" in a single
# mid-sized paper). Callers can still opt in via `sections=["results"]`.
_DEFAULT_SDRF_SECTION_KEYWORDS: tuple[str, ...] = (
    "methods",
    "materials and methods",
    "experimental procedures",
    "sample processing",
    "sample preparation",
)


def _parse_jats_sections(xml_text: str, keywords: list[str] | None = None) -> dict:
    """Parse JATS XML: extract title, abstract, ALL sections, tables, and
    supplementary material.

    When `keywords` is non-empty, sections are filtered on <sec-type> or <title>
    by case-insensitive substring. When `keywords` is None or empty, ALL sections
    are returned (used by TOC mode and `get_full_text_section`).
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        return {
            "title": None, "abstract": "",
            "sections": {}, "tables": [], "supplementary": [],
            "error": f"XML parse error: {e}",
        }

    title_el = root.find(".//article-title")
    title = _iter_text(title_el) if title_el is not None else None

    abstract_el = root.find(".//abstract")
    abstract = _iter_text(abstract_el) if abstract_el is not None else ""

    kws = [k.lower() for k in (keywords or [])]
    sections: dict[str, str] = {}
    for sec in root.iter("sec"):
        sec_type = (sec.get("sec-type") or "").lower()
        title_child = sec.find("title")
        sec_title = _iter_text(title_child) if title_child is not None else ""
        hay = f"{sec_type} {sec_title}".lower()
        if kws and not any(kw in hay for kw in kws):
            continue
        key = sec_title or sec_type or "section"
        body_parts: list[str] = []
        for child in sec:
            if child.tag == "title":
                continue
            body_parts.append(_iter_text(child))
        sections[key] = " ".join(p for p in body_parts if p).strip()

    return {
        "title": title,
        "abstract": abstract,
        "sections": sections,
        "tables": _parse_jats_tables(root),
        "supplementary": _parse_jats_supplementary(root),
    }


def _normalize_pmcid(raw: str) -> str:
    """Normalize input to canonical 'PMC<digits>' form."""
    v = str(raw).strip().upper()
    if not v:
        return ""
    return v if v.startswith("PMC") else f"PMC{v}"


def _fetch_jats_xml(pmc_id: str) -> tuple[str | None, str, str | None]:
    """Fetch JATS XML for one PMCID. Returns (xml_text, url, error).
    `xml_text` is None when error is set."""
    url = f"{EUROPE_PMC_BASE}/{pmc_id}/fullTextXML"
    try:
        resp = _get_client().get(
            url, timeout=60.0, headers={"Accept": "application/xml"},
        )
    except Exception as e:  # noqa: BLE001 — surface any network error
        return None, url, str(e)
    if resp.status_code != 200:
        return None, url, f"HTTP {resp.status_code} (not in OA subset?)"
    return resp.text, url, None


def _toc_projection(parsed: dict) -> dict:
    """Project a full `_parse_jats_sections` result down to a skeleton:
    per-section char counts (no body text), table captions (no markdown),
    supplementary captions. Abstract is kept because it is already short and
    high-signal. Shrinks typical 16-70 KB responses to 1-3 KB."""
    return {
        "title": parsed.get("title"),
        "abstract": parsed.get("abstract", ""),
        "sections": {
            name: {"chars": len(text)}
            for name, text in (parsed.get("sections") or {}).items()
        },
        "tables": [
            {"label": t.get("label", ""), "caption": t.get("caption", "")}
            for t in (parsed.get("tables") or [])
        ],
        "supplementary": [
            {
                "label": s.get("label", ""),
                "caption": s.get("caption", ""),
                "href": s.get("href", ""),
                "media_type": s.get("media_type", ""),
            }
            for s in (parsed.get("supplementary") or [])
        ],
    }


@mcp.tool()
def get_full_text_article(
    pmc_ids: list[str],
    sections: list[str] | None = None,
    mode: str = "content",
) -> list[dict]:
    """
    Fetch full-text JATS XML from Europe PMC (OA subset only) and extract sections.

    Args:
      pmc_ids: list of PMCIDs (with or without the 'PMC' prefix).
      sections: case-insensitive keywords matched against each <sec>'s sec-type
                or title. Default targets SDRF-relevant sections only (methods,
                materials, experimental procedures, sample processing/preparation).
                Results/Discussion are EXCLUDED by default — pass
                sections=["results"] to include them.
      mode:
        - "content" (default): full matching-section text + tables + deduped
          supplementary. Typical 12-20 KB per paper.
        - "toc": skeleton only — section titles + char counts, table/suppl
          captions, abstract. Typical 1-3 KB. Use for long papers, then call
          `get_full_text_section(pmc_id, section)` to expand specific sections.

    Returns per input (content mode):
      {
        pmcid, raw_xml_url,
        title, abstract,
        sections: {section_title: text},
        tables:   [{label, caption, markdown}, ...],
        supplementary: [{label, caption, href, media_type}, ...],
      }
    In toc mode, `sections` becomes {section_title: {chars: N}} and `tables`
    drops the `markdown` body.
    """
    m = (mode or "content").lower().strip()
    if m not in ("content", "toc"):
        return [{"error": "mode must be 'content' or 'toc'"}]

    # TOC mode forces an unfiltered parse so the AI sees ALL available sections.
    keywords: list[str] | None
    if m == "toc":
        keywords = None
    else:
        keywords = [s.lower() for s in (sections or _DEFAULT_SDRF_SECTION_KEYWORDS)]

    out: list[dict] = []
    for raw in pmc_ids:
        v = _normalize_pmcid(raw)
        if not v:
            continue
        xml_text, url, err = _fetch_jats_xml(v)
        if err:
            out.append({"pmcid": v, "raw_xml_url": url, "error": err})
            continue
        parsed = _parse_jats_sections(xml_text, keywords)
        if m == "toc":
            parsed = _toc_projection(parsed)
        parsed["pmcid"] = v
        parsed["raw_xml_url"] = url
        out.append(parsed)
    return out


@mcp.tool()
def get_full_text_section(pmc_id: str, section: str) -> dict:
    """
    Fetch ONE section (full text) from a JATS article on Europe PMC.

    Use this after `get_full_text_article(..., mode="toc")` to drill into a
    specific section by name without pulling the entire paper.

    Args:
      pmc_id: PMCID with or without the 'PMC' prefix.
      section: case-insensitive substring matched against each <sec>'s
               sec-type or <title>. First match wins.

    Returns:
      Hit      : {pmcid, section, text, chars}
      Miss     : {pmcid, section, error: "section not found", available: [...]}
      Fetch err: {pmcid, raw_xml_url, error: "<http/network error>"}
    """
    v = _normalize_pmcid(pmc_id)
    if not v:
        return {"error": "pmc_id is required"}
    if not section or not section.strip():
        return {"pmcid": v, "error": "section name is required"}

    xml_text, url, err = _fetch_jats_xml(v)
    if err:
        return {"pmcid": v, "raw_xml_url": url, "error": err}

    # Parse ALL sections (no keyword filter) so we can both look up the
    # requested one AND surface available titles on miss.
    parsed = _parse_jats_sections(xml_text, keywords=None)
    if parsed.get("error"):
        return {"pmcid": v, "raw_xml_url": url, "error": parsed["error"]}

    needle = section.lower().strip()
    all_sections = parsed.get("sections") or {}
    for name, body in all_sections.items():
        if needle in name.lower():
            return {"pmcid": v, "section": name, "text": body, "chars": len(body)}

    return {
        "pmcid": v,
        "section": section,
        "error": "section not found",
        "available": list(all_sections.keys()),
    }


def main() -> None:
    """CLI entry point."""
    mcp.run()


if __name__ == "__main__":
    main()

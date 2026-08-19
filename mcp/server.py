"""
SDRF Skills MCP Server

Implements tools for SDRF annotation workflow:
- PRIDE: project metadata (with pre-resolved publications) + file list
- Europe PMC: unified article metadata (PMID/PMCID/DOI) + JATS full text
- Unpaywall: open-access PDF discovery and download
- OLS: ontology term search for SDRF column annotation
"""

import json
import os
import re
import threading
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
import httpx

mcp = FastMCP(
    "sdrf-pride-pmc",
    instructions="PRIDE, MassIVE, Europe PMC, Unpaywall, and OLS tools for SDRF annotation workflow",
)

PRIDE_BASE = "https://www.ebi.ac.uk/pride/ws/archive/v2"
MASSIVE_BASE = "https://massive.ucsd.edu/ProteoSAFe/proxi/v0.1"
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
    url: str,
    params: dict | None = None,
    timeout: float | None = None,
    not_found_ok: bool = False,
) -> dict | None:
    """GET → JSON with process-local caching. Returns None on non-200 or network error.

    `not_found_ok=True` maps a 404 to `[]` instead of None, so callers can tell
    "nothing there" apart from "request failed". MassIVE's PROXI search 404s when
    you page past the last page; without this the two are indistinguishable and a
    transient failure looks like the end of the result set.
    """
    key = url + "|" + repr(sorted((params or {}).items()))
    hit = _json_cache.get(key)
    if hit is not None:
        return hit
    try:
        resp = _get_client().get(
            url, params=params, timeout=timeout or _DEFAULT_TIMEOUT
        )
        if resp.status_code != 200:
            return [] if (not_found_ok and resp.status_code == 404) else None
        try:
            data = resp.json()
        except UnicodeDecodeError:
            # httpx .json() decodes the raw bytes as UTF-8. MassIVE serves
            # `application/json;charset=ISO-8859-1`, so any record carrying an
            # accented character (author names, European affiliations) blows up
            # and would silently drop a whole page. .text honours the declared
            # charset — decode through it instead.
            data = json.loads(resp.text)
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


# -----------------------------------------------------------------------------
# MassIVE (PROXI) adapter.
#
# MassIVE serves the PROXI standard, whose records differ from PRIDE's in three
# ways that all corrupt silently if ignored:
#   1. the payload sits in `value`, not `name` (`name` is the CV term label)
#   2. species / publications / contacts are nested one list deeper
#   3. a missing value is often the literal STRING "null", not JSON null
# _proxi_values() is the single place all three are handled.
# -----------------------------------------------------------------------------
_PROXI_EMPTY = {"", "null", "none", "n/a", "na"}


def _proxi_cv_groups(record: dict, key: str) -> list[list[dict]]:
    """Normalize a PROXI CvParam field into its item groups, each a list of
    {accession, value} dicts with non-dict junk and empty/null values dropped.
    The single place that handles all three PROXI parsing traps described
    above — `_proxi_values()` and `_proxi_publications()` both build on it."""
    groups: list[list[dict]] = []
    for entry in record.get(key, []) or []:
        cleaned: list[dict] = []
        for cv in (entry if isinstance(entry, list) else [entry]):
            if not isinstance(cv, dict):
                continue
            val = cv.get("value")
            if val is None:
                continue
            val = str(val).strip()
            if val.lower() in _PROXI_EMPTY:
                continue
            cleaned.append({"accession": cv.get("accession"), "value": val})
        groups.append(cleaned)
    return groups


def _proxi_values(record: dict, key: str) -> list[str]:
    """Flatten a PROXI CvParam field to real string values, dropping empties."""
    return [cv["value"] for group in _proxi_cv_groups(record, key) for cv in group]


def _proxi_publications(record: dict) -> list[dict]:
    """Resolve PROXI publication CvParams into the PRIDE publication shape."""
    publications: list[dict] = []
    for group in _proxi_cv_groups(record, "publications"):
        pmid = doi = None
        reference = ""
        for cv in group:
            if cv["accession"] == "MS:1000879":       # PubMed identifier
                pmid = cv["value"]
            elif cv["accession"] == "MS:1001922":     # Digital Object Identifier
                doi = cv["value"]
            elif cv["accession"] == "MS:1002866":     # Reference
                reference = cv["value"]
        if not (pmid or doi or reference):
            continue
        if pmid or doi:
            publications.append(_resolve_publication(pmid, doi, reference))
        else:
            publications.append({
                "pmid": None, "pmcid": None, "doi": None,
                "is_open_access": False, "reference": reference,
            })
    return publications


def _massive_to_project(record: dict, queried: str | None = None) -> dict:
    """Map a MassIVE PROXI dataset record onto the get_project_details schema."""
    accessions = _proxi_values(record, "accession")
    primary = queried or next(
        (a for a in accessions if a.upper().startswith("PXD")),
        accessions[0] if accessions else None,
    )
    return {
        "accession": primary,
        "all_accessions": accessions,
        "repository": "MassIVE",
        "title": record.get("title"),
        "description": record.get("summary"),
        # MassIVE PROXI exposes no protocol text and no experiment/quantification
        # CV terms. Empty is honest here — screen these from the publication.
        "sample_processing_protocol": None,
        "data_processing_protocol": None,
        "organism": _proxi_values(record, "species"),
        "organism_parts": [],
        "countries": [],
        "instruments": _proxi_values(record, "instruments"),
        "experiment_types": [],
        "quantification_methods": [],
        "modifications": _proxi_values(record, "modifications"),
        "publications": _proxi_publications(record),
        "keywords": _proxi_values(record, "keywords"),
    }


def _massive_search_hit(record: dict) -> dict:
    """Cheap projection of a PROXI search hit — NOT _massive_to_project().

    A search page returns up to `page_size` records and none of them expose
    `publications` in the output shape, so resolving publications here (a live
    Europe PMC call per record, via _proxi_publications) would be pure waste —
    measured at 17 discarded Europe PMC requests for one 30-record page. Only
    compute what a search hit actually reports.
    """
    accessions = _proxi_values(record, "accession")
    return {
        "accession": next((a for a in accessions if a.upper().startswith("PXD")),
                          accessions[0] if accessions else None),
        "all_accessions": accessions,
        "repository": "MassIVE",
        "title": record.get("title"),
        "description": record.get("summary"),
        "organism": _proxi_values(record, "species"),
        "organism_parts": [],
        "instruments": _proxi_values(record, "instruments"),
        "experiment_types": [],
        "quantification_methods": [],
        "keywords": _proxi_values(record, "keywords"),
        "publication_date": None,
        "has_sdrf": False,
    }


def _massive_get_dataset(accession: str) -> dict | None:
    """Fetch one MassIVE dataset by MSV… or PXD… accession."""
    data = _cached_get_json(f"{MASSIVE_BASE}/datasets/{accession}")
    if isinstance(data, dict) and data.get("title"):
        return data
    # Direct path can 200 with an empty body for unknown ids; the accession
    # filter is the reliable confirmation.
    hits = _cached_get_json(
        f"{MASSIVE_BASE}/datasets",
        params={"resultType": "full", "accession": accession},
    )
    if isinstance(hits, list) and hits:
        return hits[0]
    return None


# --- 1.0 Search projects across PRIDE + MassIVE (discovery) ---
@mcp.tool()
def search_projects(
    keyword: str,
    page_size: int = 100,
    page: int = 0,
    repository: str = "all",
) -> dict:
    """
    Search proteomics projects by keyword across PRIDE and MassIVE. Use this to
    resolve a free-text dataset category ("human gut metaproteomics") into
    concrete accessions.

    `repository`: "all" (default, both), "pride", or "massive".

    Each hit carries the structured screening fields, so a candidate set can be
    pre-filtered on organism / instrument / experiment_types /
    quantification_methods WITHOUT one get_project_details call per hit. Fetch
    details only for survivors. Each hit reports its `repository`.

    MassIVE hits carry BOTH accessions (`all_accessions`: MSV… and, when the
    dataset is in ProteomeXchange, PXD…). Results are deduplicated on any shared
    accession, preferring the PRIDE copy because MassIVE PROXI publishes no
    experiment_types, quantification_methods, organism_parts or countries.

    Keyword behaviour (measured, not documented upstream): PRIDE ANDs the terms
    and narrows HARD — "metaproteomics" returns 100+, "human gut metaproteomics"
    returns 2. For recall, issue several SHORT keyword searches and union the
    accessions; do not pass a whole category sentence as one keyword. Hits are
    ranked, not filtered, so always re-check the structured fields yourself.

    Results cap at `page_size` per call; page through until a call returns fewer
    than `page_size` hits.

    Returns {keyword, repository, page, page_size, count, results:[{accession,
    all_accessions, repository, title, description, organism, organism_parts,
    instruments, experiment_types, quantification_methods, keywords,
    publication_date, has_sdrf}], errors:[...]}.
    """
    repo = (repository or "all").lower().strip()
    if repo not in {"all", "pride", "massive"}:
        return {"keyword": keyword, "count": 0, "results": [],
                "error": f"repository must be all|pride|massive, got {repository!r}"}

    results: list[dict] = []
    errors: list[str] = []

    _names = _pride_names

    if repo in {"all", "pride"}:
        items = _pride_search_page(keyword, page, page_size)
        if items is None:
            errors.append("PRIDE search unreachable")
            items = []
        for it in items:
            results.append(_pride_search_hit(it, _names))

    if repo in {"all", "massive"}:
        # PROXI requires resultType; `keywords=` is silently IGNORED and returns
        # the unfiltered listing — `search=` is the only real filter. pageNumber
        # is 1-based (`page=` is ignored). Paging past the end 404s, which
        # not_found_ok maps to [] so it reads as exhaustion, not failure.
        mparams = {
            "resultType": "full",
            "search": keyword,
            "pageSize": str(page_size),
            "pageNumber": str(page + 1),
        }
        mdata = _cached_get_json(
            f"{MASSIVE_BASE}/datasets", params=mparams, not_found_ok=True
        )
        if mdata is None:
            errors.append(
                f"MassIVE search failed for page {page} — results are INCOMPLETE, retry this page"
            )
        else:
            seen = {a for r in results for a in r["all_accessions"] if a}
            for rec in mdata if isinstance(mdata, list) else []:
                hit = _massive_search_hit(rec)
                if any(a in seen for a in hit["all_accessions"]):
                    continue  # already covered by the richer PRIDE record
                results.append(hit)
                seen.update(a for a in hit["all_accessions"] if a)

    out = {
        "keyword": keyword,
        "repository": repo,
        "page": page,
        "page_size": page_size,
        "count": len(results),
        "results": results,
    }
    if errors:
        out["errors"] = errors
    return out


def _pride_names(rec: dict, key: str) -> list[str]:
    """/search/projects returns plain strings where /projects/{acc} returns CvParam dicts."""
    out = []
    for v in rec.get(key, []) or []:
        out.append(v.get("name", "") if isinstance(v, dict) else str(v))
    return out


def _pride_search_page(
    keyword: str, page: int, page_size: int, year: int | None = None
) -> list | None:
    """One page of PRIDE /search/projects. None means the request failed."""
    params = {"keyword": keyword, "pageSize": str(page_size), "page": str(page)}
    if year is not None:
        # field==value is the documented filter grammar (pridepy --filters).
        params["filter"] = f"submissionDate=={year}"
    data = _cached_get_json(f"{PRIDE_BASE}/search/projects", params=params)
    if data is None:
        return None
    if isinstance(data, list):
        return data
    return data.get("_embedded", {}).get("compactprojects", []) or []


# A keyword search that ends on a page boundary is ambiguous: the result set may
# be exhausted, or the endpoint may be refusing to serve past a cap. PRIDE has
# historically done the latter (a bare keyword capped at 100 while reporting an
# empty next page — indistinguishable from exhaustion, see #28). It paginates
# correctly today, so this is not worked around unconditionally; it is DETECTED,
# and the year-partitioned retry runs only when detection fires.
_PRIDE_MAX_PAGES = 200
_PRIDE_FIRST_YEAR = 2004


def _pride_walk(
    keyword: str,
    page_size: int,
    year: int | None = None,
    max_results: int = 10000,
) -> tuple[list[dict], str]:
    """Page one PRIDE query to exhaustion.

    Returns (hits, status) where status is one of:
      exhausted      — a short page ended it; the result set is complete
      suspected_cap  — the last full page was followed by an empty one, so
                       "complete" cannot be distinguished from "truncated"
      page_error     — a page request failed; the result set is INCOMPLETE
      max_results    — the caller's ceiling stopped the walk
    """
    hits: list[dict] = []
    for page in range(_PRIDE_MAX_PAGES):
        items = _pride_search_page(keyword, page, page_size, year)
        if items is None:
            return hits, "page_error"
        if not items:
            # An empty FIRST page is a genuinely empty result set. An empty page
            # after a full one is the ambiguous case: exhaustion and a refusal to
            # serve past a cap look identical from here.
            return hits, "suspected_cap" if hits else "exhausted"
        hits.extend(items)
        if len(items) < page_size:
            return hits, "exhausted"
        if len(hits) >= max_results:
            return hits, "max_results"
    return hits, "suspected_cap"


def _pride_walk_partitioned(
    keyword: str, page_size: int, max_results: int, until_year: int
) -> tuple[list[dict], list[str]]:
    """Re-run a capped keyword one submission year at a time.

    A filter makes the endpoint paginate past the cap even when a bare keyword
    will not, so partitioning recovers what the plain walk could not reach.
    """
    hits: list[dict] = []
    still_capped: list[str] = []
    for year in range(until_year, _PRIDE_FIRST_YEAR - 1, -1):
        part, status = _pride_walk(keyword, page_size, year=year,
                                   max_results=max_results - len(hits))
        hits.extend(part)
        if status in ("suspected_cap", "page_error", "max_results"):
            still_capped.append(f"{keyword}@{year}:{status}")
        if len(hits) >= max_results:
            break
    return hits, still_capped


def _massive_walk(keyword: str, page_size: int, max_results: int) -> tuple[list[dict], str]:
    """Page MassIVE PROXI to exhaustion. pageNumber is 1-based; 404 = exhausted."""
    hits: list[dict] = []
    for page in range(_PRIDE_MAX_PAGES):
        data = _cached_get_json(
            f"{MASSIVE_BASE}/datasets",
            params={
                "resultType": "full",
                "search": keyword,
                "pageSize": str(page_size),
                "pageNumber": str(page + 1),
            },
            not_found_ok=True,
        )
        if data is None:
            return hits, "page_error"
        items = data if isinstance(data, list) else []
        hits.extend(items)
        if len(items) < page_size:
            return hits, "exhausted"
        if len(hits) >= max_results:
            return hits, "max_results"
    return hits, "suspected_cap"


# --- 1.0b Multi-keyword exhaustive discovery ---
@mcp.tool()
def search_extensive(
    keywords: list[str] | str,
    repository: str = "all",
    page_size: int = 100,
    max_results: int = 5000,
) -> dict:
    """
    Discover datasets across PRIDE + MassIVE by sweeping SEVERAL keywords and
    unioning the results. Use this, not repeated search_projects calls, whenever
    the target is a whole category ("all single-cell proteomics datasets") and
    completeness matters.

    Two measured facts drive this tool:

    1. **One keyword under-recalls.** PRIDE ANDs the terms in a keyword and then
       RANKS rather than filters, so a category sentence collapses recall
       ("metaproteomics" 100+, "human gut metaproteomics" 2) and no single term
       covers a field: a 16-keyword single-cell sweep (SCoPE2, nanoPOTS, plexDIA,
       CellenONE, proteoCHIP, …) unions to more datasets than "single-cell
       proteomics" returns on its own. Pass the sweep, not the sentence.
    2. **Truncation must never be silent.** Each keyword is paged to a SHORT page,
       which is the only unambiguous end-of-results signal. If a full page is
       followed by an empty one — historically how PRIDE served a capped query —
       the walk is retried partitioned by submission year, and anything still
       unresolved is reported in `truncated` rather than passed off as complete.

    `keywords` accepts a list or a single string. `repository`: "all" (default),
    "pride", or "massive". `max_results` caps the union (reported when it bites).

    Returns {keywords, repository, count, results:[<same hit shape as
    search_projects>], per_keyword:{kw:{hits, new, status}}, truncated:[...],
    errors:[...], requests_note}.
    """
    repo = (repository or "all").lower().strip()
    if repo not in {"all", "pride", "massive"}:
        return {"keywords": keywords, "count": 0, "results": [],
                "error": f"repository must be all|pride|massive, got {repository!r}"}

    if isinstance(keywords, str):
        kws = [keywords]
    else:
        kws = list(keywords or [])
    kws = [k.strip() for k in kws if k and k.strip()]
    if not kws:
        return {"keywords": [], "count": 0, "results": [],
                "error": "keywords must contain at least one non-empty term"}

    until_year = date.today().year
    results: list[dict] = []
    seen: set[str] = set()
    per_keyword: dict[str, dict] = {}
    truncated: list[str] = []
    errors: list[str] = []

    def _add(hit: dict) -> bool:
        accs = [a for a in hit["all_accessions"] if a]
        if any(a in seen for a in accs):
            return False
        results.append(hit)
        seen.update(accs)
        return True

    for kw in kws:
        stats = {"hits": 0, "new": 0, "status": "exhausted"}

        if repo in {"all", "pride"}:
            raw, status = _pride_walk(kw, page_size, max_results=max_results)
            if status == "suspected_cap":
                extra, still = _pride_walk_partitioned(
                    kw, page_size, max_results, until_year)
                raw = raw + extra
                status = "partitioned" if not still else "truncated"
                truncated.extend(still)
            if status == "page_error":
                errors.append(
                    f"PRIDE search for {kw!r} lost a page — results are INCOMPLETE, retry")
            if status == "max_results":
                truncated.append(f"{kw}:max_results")
            stats["status"] = status
            for it in raw:
                stats["hits"] += 1
                if _add(_pride_search_hit(it, _pride_names)):
                    stats["new"] += 1

        if repo in {"all", "massive"}:
            mraw, mstatus = _massive_walk(kw, page_size, max_results)
            if mstatus == "page_error":
                errors.append(
                    f"MassIVE search for {kw!r} lost a page — results are INCOMPLETE, retry")
            elif mstatus in ("suspected_cap", "max_results"):
                truncated.append(f"{kw}@massive:{mstatus}")
            stats["status"] = f"{stats['status']}/{mstatus}" if repo == "all" else mstatus
            for rec in mraw:
                stats["hits"] += 1
                if _add(_massive_search_hit(rec)):
                    stats["new"] += 1

        per_keyword[kw] = stats

    out = {
        "keywords": kws,
        "repository": repo,
        "count": len(results),
        "results": results,
        "per_keyword": per_keyword,
        "requests_note": (
            "per_keyword.new is what each keyword contributed that no earlier "
            "keyword had; a keyword with new=0 is redundant for this sweep"
        ),
    }
    if truncated:
        out["truncated"] = truncated
        out["warning"] = (
            "Coverage is NOT complete for the entries in `truncated` — report "
            "them rather than presenting this union as the full result set."
        )
    if errors:
        out["errors"] = errors
    return out


def _pride_search_hit(it: dict, _names) -> dict:
    acc = it.get("accession")
    return {
            "accession": acc,
            "all_accessions": [acc] if acc else [],
            "repository": "PRIDE",
            "title": it.get("title"),
            "description": it.get("projectDescription"),
            "organism": _names(it, "organisms"),
            # search spells this "organismsPart"; project details uses "organismParts"
            "organism_parts": _names(it, "organismsPart") or _names(it, "organismParts"),
            "instruments": _names(it, "instruments"),
            "experiment_types": _names(it, "experimentTypes"),
            "quantification_methods": _names(it, "quantificationMethods"),
            "keywords": it.get("keywords", []),
            "publication_date": it.get("publicationDate"),
            "has_sdrf": bool(it.get("sdrf")),
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

    Resolves across BOTH repositories, so callers need no routing logic:
      - MSV…  → MassIVE
      - PXD…  → PRIDE, falling back to MassIVE when PRIDE does not hold it
                (MassIVE-hosted ProteomeXchange datasets 404 in PRIDE —
                e.g. PXD003626 — so the fallback is required, not cosmetic)

    Returns: accession, all_accessions, repository, title, description,
    sample_processing_protocol, data_processing_protocol, organism,
    organism_parts, countries, instruments, experiment_types,
    quantification_methods, modifications, publications, keywords.

    `experiment_types` (e.g. "Shotgun proteomics") and `quantification_methods`
    (e.g. "TIC", "TMT") are the structured screening fields — prefer them over
    parsing the free-text protocols when filtering candidates. MassIVE PROXI
    publishes neither, and no protocol text; those come back empty and must be
    screened from the publication instead. An empty field is not a failed check.
    """
    accession = (project_accession or "").strip()

    if accession.upper().startswith("MSV"):
        record = _massive_get_dataset(accession)
        if record is None:
            return {"accession": accession,
                    "error": "MassIVE dataset not found or API unreachable"}
        return _massive_to_project(record, queried=accession)

    data = _cached_get_json(f"{PRIDE_BASE}/projects/{accession}")
    if data is None:
        record = _massive_get_dataset(accession)
        if record is not None:
            return _massive_to_project(record, queried=accession)
        return {
            "accession": accession,
            "error": "Not found in PRIDE or MassIVE, or both APIs unreachable",
        }

    organisms = [o.get("name", "") for o in data.get("organisms", [])]
    instruments = [i.get("name", "") for i in data.get("instruments", [])]
    mods = [m.get("name", "") for m in data.get("identifiedPTMStrings", [])]
    organism_parts = [p.get("name", "") for p in data.get("organismParts", []) or []]
    experiment_types = [e.get("name", "") for e in data.get("experimentTypes", []) or []]
    quant_methods = [q.get("name", "") for q in data.get("quantificationMethods", []) or []]

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
        "all_accessions": [data.get("accession")] if data.get("accession") else [],
        "repository": "PRIDE",
        "title": data.get("title"),
        "description": data.get("projectDescription"),
        "sample_processing_protocol": data.get("sampleProcessingProtocol"),
        "data_processing_protocol": data.get("dataProcessingProtocol"),
        "organism": organisms,
        "organism_parts": organism_parts,
        "countries": data.get("countries", []),
        "instruments": instruments,
        "experiment_types": experiment_types,
        "quantification_methods": quant_methods,
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
    data = _cached_get_json(f"{PRIDE_BASE}/projects/{project_accession}/files/all")
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
        # Sanitize the PMID before using it as a path component to guard against
        # path traversal (e.g. "../"); PMIDs are plain integers in practice.
        safe_pmid = pmid.replace("/", "_").replace("\\", "_").replace("..", "_").strip()
        return out_path / safe_pmid
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


def _smart_search(searcher, page_size: int) -> dict:
    """Exact-first search that refuses to present a non-exact / one-of-many hit
    as if it were THE answer (issue #35 C4).

    Previously smart mode probed exact with ``page_size=1`` and collapsed
    ``numFound`` to 1, so ``HeLa`` → ``HeLa-MAGI-CCR5`` (a synonym-matched
    *different* entity) came back looking authoritative. Here we probe exact
    **wide**: if more than one *distinct accession* matches the query exactly
    (label or synonym), we return them all with ``ambiguous: true`` so the
    caller must disambiguate rather than trust a single hit. Only a single
    distinct exact match is returned as confident; otherwise we fall back to
    fuzzy (flagged ``fallback: "fuzzy"``).

    ``searcher(page_size, exact) -> dict`` runs one OLS query and returns a dict
    carrying ``results`` (each ``{label, accession, ontology}``).
    """
    probe = min(max(page_size, 10), 50)
    hit = searcher(probe, True)
    results = hit.get("results", [])
    distinct = {r.get("accession") for r in results if r.get("accession")}
    if distinct:
        hit["numFound"] = len(results)
        if len(distinct) > 1:
            hit["ambiguous"] = True
            hit["note"] = (
                "Multiple distinct terms match this query exactly (label or "
                "synonym). This is NOT a single authoritative hit — verify which "
                "entity is intended (e.g. parental cell line vs a derivative, the "
                "drug vs a regimen) before citing an accession."
            )
        return hit
    fuzzy = searcher(page_size, False)
    fuzzy["numFound"] = len(fuzzy.get("results", []))
    fuzzy["fallback"] = "fuzzy"
    return fuzzy


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
      - "smart" : EXACT label/synonym first, probed WIDE. A single distinct
                  exact match is returned as confident; if several *distinct*
                  terms match exactly (e.g. a cell line and its derivatives),
                  all are returned with `ambiguous: true` so you disambiguate
                  rather than trust one hit. Only when nothing matches exactly
                  does it fall back to fuzzy top-`page_size`.
      - "exact" : exact-only, cap results at page_size. Returns empty on miss.
      - "fuzzy" : fuzzy-only, returns top-`page_size` regardless of exact hits.

    NOTE: for controlled identifiers where a query commonly names several
    entities — cell lines (`HeLa`), drugs (`methotrexate`), anatomy
    (`hippocampus`) — prefer `mode="fuzzy"` and eyeball the candidates; smart
    mode's exact probe can surface a synonym-matched *different* entity.

    Returns {query, ontology_id, numFound, results:[{label, accession, ontology}]}.
    `fallback: "fuzzy"` marks a non-exact result; `ambiguous: true` marks
    several distinct exact matches (not a single authoritative hit).
    """
    m = (mode or "smart").lower().strip()
    if m == "exact":
        return _search_ontology_classes(query, ontologyId, page_size, exact=True)
    if m == "fuzzy":
        return _search_ontology_classes(query, ontologyId, page_size, exact=False)

    return _smart_search(
        lambda ps, ex: _search_ontology_classes(query, ontologyId, ps, exact=ex),
        page_size,
    )


# --- 4.1 Search OLS across ALL ontologies (no filter) ---
@mcp.tool()
def search(query: str, page_size: int = 3, mode: str = "smart") -> dict:
    """
    Search OLS across ALL ontologies. Prefer searchClasses with a specific
    ontologyId for SDRF column annotation; use this only when the target
    ontology is unknown.

    mode (default "smart"):
      - "smart" : exact-first probed WIDE; a single distinct exact match is
                  confident, several distinct exact matches come back with
                  `ambiguous: true`, else fuzzy top-`page_size` fallback.
      - "exact" : exact-only, cap at page_size. Empty on miss.
      - "fuzzy" : fuzzy-only, returns top-`page_size`.

    Returns {query, numFound, results:[{label, accession, ontology}]}.
    `fallback: "fuzzy"` marks a non-exact result; `ambiguous: true` marks
    several distinct exact matches (not a single authoritative hit).
    """
    m = (mode or "smart").lower().strip()
    if m == "exact":
        return _search_all_ontologies(query, page_size, exact=True)
    if m == "fuzzy":
        return _search_all_ontologies(query, page_size, exact=False)

    return _smart_search(
        lambda ps, ex: _search_all_ontologies(query, ps, ex), page_size
    )


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
def getChildren(accession: str, rows: int = 100) -> dict:
    """
    Get the **descendant** terms (transitive children) of an ontology accession
    (e.g. 'PRIDE:0000895'). Useful for specificity / enumeration checks.

    Returns descendants, not just direct children (issue #35 B7): OLS's own
    `/children` returns only the immediate level, so `getChildren(PRIDE:0000895)`
    would omit `pooled` / `empty` / `bulk control` — genuine descendants reached
    via an intermediate node — and an annotator that trusted it would force
    `not applicable` onto valid rows. The validator's `examples` treat these
    grandchildren as members, so "children" here means *descendant*.

    Falls back to OLS /search for ontologies not in the static IRI map.
    Returns: accession, count, children [{label, accession, ontology}]
    (`children` key kept for backward compatibility; entries are descendants).
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
        f"{OLS_BASE}/ontologies/{ont_id}/terms/{encoded_iri}/descendants",
        params={"size": rows},
    )
    if not data:
        return {"accession": accession, "count": 0, "children": [],
                "error": "No descendants or lookup failed"}
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

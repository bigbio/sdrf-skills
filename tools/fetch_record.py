"""Fetch a PRIDE project record into the evidence/ layout that offline annotation reads.

For agents that have network access but no MCP server. Writes:

- ``pride.json``      the PRIDE ``/projects/{acc}`` record, unmodified
- ``files.json``      ``{"files": [vendor raw names], "other_files": [...], "urls": {name: url}}``;
                      ``sdrf-tools build --files`` reads its ``files`` key. When a deposit holds no
                      vendor raw file, ``files`` lists its mzML/mzXML files and ``note`` says so.
- ``manuscript.txt``  one section per linked publication: Europe PMC open-access full text
                      when there is one, else the abstract. Absent when PRIDE links no paper.

Nothing is written unless every lookup succeeded, so a failed fetch never leaves an
``evidence/`` directory that looks complete. An existing non-empty output directory is
refused unless ``force`` is set, and then replaced as a whole.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.parse
from functools import lru_cache
from pathlib import Path
from types import ModuleType

import requests

from tools.massive_raw_files import VENDOR_RAW_SUFFIXES
from tools.services import PRIDEClient

EUROPEPMC_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "europepmc_fulltext.py"
_ARCHIVE_SUFFIXES = (".zip", ".gz", ".tar", ".rar", ".7z", ".bz2")
_PEAK_LIST_SUFFIXES = (".mzml", ".mzxml")
_RETRY_HINT = ("Retry once; if it fails again, gather the record per "
               "skills/sdrf-annotate/references/gather-context.md using the PRIDE and Europe PMC REST endpoints.")


class FetchError(Exception):
    """A lookup failed; the evidence would be incomplete, so nothing is written."""


@lru_cache(maxsize=1)
def europepmc() -> ModuleType:
    """Load the bundled Europe PMC full-text helper (scripts/ is not an installed package)."""
    if not EUROPEPMC_SCRIPT.exists():
        raise FetchError(f"{EUROPEPMC_SCRIPT} is missing; run sdrf-tools from an sdrf-skills checkout")
    spec = importlib.util.spec_from_file_location("europepmc_fulltext", EUROPEPMC_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve their module through sys.modules
    spec.loader.exec_module(module)
    return module


def _unarchived(name: str) -> str:
    lower = name.lower()
    while lower.endswith(_ARCHIVE_SUFFIXES):
        lower = lower.rsplit(".", 1)[0]
    return lower


def is_vendor_raw(name: str, category: str) -> bool:
    """A run file for comment[data file]; a Sciex .wiff.scan is the .wiff's companion, not a run."""
    lower = _unarchived(name)
    if lower.endswith(".wiff.scan"):
        return False
    return category.upper() == "RAW" or lower.endswith(VENDOR_RAW_SUFFIXES)


def _https(url: str) -> str:
    return "https://" + url[len("ftp://"):] if url.startswith("ftp://") else url


def file_evidence(accession: str, files: list[dict]) -> dict:
    raw, other, urls = [], [], {}
    for f in files:
        name = f.get("fileName") or ""
        if not name:
            continue
        owners = f.get("projectAccessions")
        if owners and accession not in owners:
            raise FetchError(f"PRIDE file list for {accession} contains '{name}' of {owners}")
        category = (f.get("fileCategory") or {}).get("value", "")
        (raw if is_vendor_raw(name, category) else other).append(name)
        for loc in f.get("publicFileLocations") or []:
            if loc.get("name") == "FTP Protocol" and loc.get("value"):
                urls[name] = _https(loc["value"])
    if not raw and not other:
        raise FetchError(
            f"PRIDE lists no files for {accession}. A dataset hosted at MassIVE, iProX or PanoramaPublic "
            f"has an empty PRIDE file list: try `sdrf-tools massive-files {accession}` or "
            f"`sdrf-tools iprox-files {accession}`"
        )
    evidence = {"accession": accession, "files": sorted(raw), "other_files": sorted(other), "urls": urls}
    if not raw:
        peaks = sorted(n for n in other if _unarchived(n).endswith(_PEAK_LIST_SUFFIXES))
        if not peaks:
            raise FetchError(f"PRIDE lists no vendor raw or mzML/mzXML file for {accession}; {len(other)} other "
                             "files found. Find the run files per gather-context.md 1.2 before annotating.")
        evidence["files"] = peaks
        evidence["other_files"] = sorted(set(other) - set(peaks))
        evidence["note"] = "no vendor raw file deposited: files are the open-format peak lists"
    return evidence


def _plain(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()


def _epmc_record(epmc: ModuleType, identifier: str, id_type: str) -> dict | None:
    query = epmc.search_query_for_identifier(identifier, id_type)
    params = urllib.parse.urlencode({"query": query, "format": "json", "resultType": "core", "pageSize": 1})
    results = epmc.fetch_json(f"{epmc.EUROPE_PMC_BASE}/search?{params}").get("resultList", {}).get("result", [])
    return results[0] if results else None


def publication_text(reference: dict) -> str:
    """One manuscript.txt section for a PRIDE reference: full text, else abstract, else the citation."""
    epmc = europepmc()
    line = reference.get("referenceLine") or ""
    pmid = str(reference.get("pubmedID") or "").strip()
    pmid = "" if pmid == "0" else pmid
    doi = epmc.normalize_doi(reference.get("doi") or "")
    head = f"=== PUBLICATION: {line or pmid or doi}"

    record = None
    for identifier, id_type in ((pmid, "pmid"), (doi, "doi")):
        if identifier and record is None:
            record = _epmc_record(epmc, identifier, id_type)
    if record is None:
        return f"{head}\nNOT IN EUROPE PMC: no text retrieved (pmid={pmid or '-'}, doi={doi or '-'})\n"

    pmcid = epmc.normalize_pmcid(str(record.get("pmcid") or record.get("fullTextId") or ""))
    if pmcid:
        try:
            xml_text = epmc.fetch_text(f"{epmc.EUROPE_PMC_BASE}/{pmcid}/fullTextXML")
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise
        else:
            record["resolvedPmcid"] = pmcid
            payload = epmc.build_payload(epmc._safe_fromstring(xml_text), record)
            text = epmc.render_text(payload, None, True)
            return f"{head}\nFULL TEXT: Europe PMC open-access XML ({pmcid})\n\n{text}\n"

    meta = [
        f"title: {record.get('title', '')}",
        f"journal: {(record.get('journalInfo') or {}).get('journal', {}).get('title', '')}",
        f"authors: {record.get('authorString', '')}",
        f"pmid: {record.get('pmid', '')}",
        f"doi: {record.get('doi', '')}",
    ]
    return (f"{head}\nABSTRACT ONLY: Europe PMC holds no open full text for this article\n\n"
            + "\n".join(meta) + f"\n\nABSTRACT\n{_plain(record.get('abstractText', ''))}\n")


def fetch(accession: str, pride: PRIDEClient | None = None) -> dict[str, str]:
    """Gather the evidence files' contents; raises FetchError on any failed lookup."""
    pride = pride or PRIDEClient()
    try:
        project = pride.get_project_record(accession)
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status == 404:
            raise FetchError(
                f"PRIDE has no project {accession} (HTTP 404). MassIVE- and iProX-hosted datasets "
                f"404 in PRIDE: try `sdrf-tools massive-files {accession}` or `sdrf-tools iprox-files {accession}`"
            ) from exc
        raise FetchError(f"PRIDE project lookup failed: {exc}. {_RETRY_HINT}") from exc
    except (requests.RequestException, ValueError) as exc:
        raise FetchError(f"PRIDE project lookup failed: {exc}. {_RETRY_HINT}") from exc

    try:
        listed = pride.get_all_files(accession)
    except (requests.RequestException, ValueError) as exc:
        raise FetchError(f"PRIDE file list lookup failed: {exc}. {_RETRY_HINT}") from exc
    files = file_evidence(accession, listed)

    out = {
        "pride.json": json.dumps(project, indent=2, ensure_ascii=False) + "\n",
        "files.json": json.dumps(files, indent=2, ensure_ascii=False) + "\n",
    }
    references = project.get("references") or []
    if references:
        try:
            out["manuscript.txt"] = "\n".join(publication_text(r) for r in references)
        except (OSError, ValueError, SyntaxError) as exc:  # urllib errors are OSErrors; XML ParseError is a SyntaxError
            raise FetchError(f"Europe PMC lookup failed: {exc}. {_RETRY_HINT}") from exc
    return out


def write_evidence(out_dir: Path, contents: dict[str, str]) -> None:
    """Write into a temporary sibling directory, then swap it in, so the output is never half old."""
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=f".{out_dir.name}.", dir=out_dir.parent))
    umask = os.umask(0)
    os.umask(umask)
    tmp.chmod(0o777 & ~umask)  # mkdtemp makes it 0700; give it the mode a plain mkdir would
    try:
        for name, text in contents.items():
            (tmp / name).write_text(text, encoding="utf-8")
        if out_dir.exists():
            old = out_dir.with_name(f"{tmp.name}.old")
            out_dir.rename(old)
            tmp.rename(out_dir)
            shutil.rmtree(old)
        else:
            tmp.rename(out_dir)
    finally:
        if tmp.exists():
            shutil.rmtree(tmp)


def run(accession: str, out_dir: str | Path, pride: PRIDEClient | None = None, force: bool = False) -> int:
    accession = accession.strip().upper()
    out = Path(out_dir)
    if out.exists() and (not out.is_dir() or any(out.iterdir())) and not force:
        print(f"fetch refused: {out} already exists; remove it or pass --force", file=sys.stderr)
        return 2
    try:
        contents = fetch(accession, pride)
        write_evidence(out, contents)
    except FetchError as exc:
        print(f"fetch failed: {exc}\nNothing was written to {out}; do not treat it as offline evidence.",
              file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - any other failure must still be a clear exit 2
        print(f"fetch failed: unexpected {type(exc).__name__}: {exc}\n{_RETRY_HINT}\n"
              f"Do not treat {out} as offline evidence.", file=sys.stderr)
        return 2
    files = json.loads(contents["files.json"])
    print(f"wrote {out / 'pride.json'}")
    print(f"wrote {out / 'files.json'}: {len(files['files'])} run files, {len(files['other_files'])} other files")
    if "note" in files:
        print(f"warning: {files['note']}")
    if "manuscript.txt" in contents:
        kinds = re.findall(r"^(FULL TEXT|ABSTRACT ONLY|NOT IN EUROPE PMC)", contents["manuscript.txt"], re.MULTILINE)
        print(f"wrote {out / 'manuscript.txt'}: {', '.join(k.lower() for k in kinds)}")
    else:
        print("no publication linked in PRIDE: manuscript.txt not written")
    return 0

"""Resolve iProX raw or deposited file names for an iProX project or PXD accession.

This helper is intended for SDRF curation when:
- a ProteomeXchange accession is hosted by iProX
- PRIDE `/projects/{PXD}/files/all` is empty or incomplete
- you need actual deposited file names for `comment[data file]`

Resolution chain:
1. If the input is a PXD, query ProteomeCentral PROXI to resolve the iProX ID.
   NOTE: iProX datasets that are not yet released are absent from PROXI; pass the
   IPX project id shown on the dataset page instead.
2. For an IPX project id, ask iProX `findByProjectId.jsonp` for the project record
   and `selectSubprosByPid.jsonp` for the subproject list (the project page's own
   lightweight endpoint — never the full browse tree).
3. For each subproject, ask `findBySubProjectId.jsonp`, which returns the file list
   inline: `subdatafilesInfo[]` carries `fileName`, `fileType` and `fileSize` (KB).
4. Filter by file type: iProX marks vendor raw files with `fileType == "RAW"`
   (Bruker `.d` folders are usually deposited as `.zip`/`.rar` archives; Thermo
   `.raw` files are bare). Search outputs and the PX XML are `SEARCH`, `XML` or
   `PRIDEXML` and are excluded in `--mode raw`.

An IPX id of 10 digits is ambiguous: both projects and subprojects use that shape.
The helper asks for a project first and falls back to a single-subproject lookup
when no project record comes back.

A private project (privacy != 1) still returns its file list through the API, so
the helper prints a warning instead of failing; downloads will need a login.

Extras for the SDRF workflow:
- ``--subproject IPX...`` (repeatable) restricts the output to one subproject, for
  multi-subproject datasets annotated as several SDRF files;
- ``--record FILE`` writes a reconcile-compatible record JSON (PRIDE /projects/{acc}
  shape) so `sdrf-tools reconcile` can check the SDRF against the iProX prose;
- ``--px-xml PATH|URL|auto`` parses the PX XML for the species/instrument lists and
  attaches each file's original acquisition name when the deposit renamed it (matched
  by size, since the XML rounds sizes to 2-decimal MB).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

IPROX_BASE = "https://www.iprox.cn"
PROJECT_URL = f"{IPROX_BASE}/PMD009Controller/findByProjectId.jsonp"
SUBPROJECT_URL = f"{IPROX_BASE}/PMD009Controller/findBySubProjectId.jsonp"
SUBPROJECTS_URL = f"{IPROX_BASE}/selectSubprosByPid.jsonp"
DOWNLOAD_BASE = "http://download.iprox.org"  # HTTP, not HTTPS — TLS breaks here
PX_PROXI_TEMPLATE = "https://proteomecentral.proteomexchange.org/api/proxi/v0.1/datasets/{accession}"

PXD_RE = re.compile(r"^PXD\d{6,}$", re.IGNORECASE)
IPX_RE = re.compile(r"^IPX\d{10}$", re.IGNORECASE)

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "sdrf-skills/iprox-raw-files/0.1",
    "X-Requested-With": "XMLHttpRequest",  # the iProX app rejects requests without it
    "Referer": "https://www.iprox.cn/page/project.html",
}

RAW_FILE_TYPE = "RAW"
DEFAULT_TIMEOUT = 300  # iProX responds slowly; the default must be generous
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 4


@dataclass
class IproxFile:
    name: str
    file_type: str
    size_kb: float | None
    subproject_id: str
    uri: str = ""

    @property
    def is_raw(self) -> bool:
        return (self.file_type or "").strip().upper() == RAW_FILE_TYPE


@dataclass
class IproxSubproject:
    subproject_id: str
    title: str | None = None
    species: str | None = None
    instrument: str | None = None
    file_count_hint: int | None = None
    size_hint: int | None = None
    privacy: int | None = None
    experiment_protocol: str | None = None
    informatics_protocol: str | None = None
    experiment_type: str | None = None
    files: list[IproxFile] = field(default_factory=list)


@dataclass
class PxXmlOrphan:
    """An XML entry naming a file the API list does not have — e.g. an original
    acquisition name the deposit renamed. The same-size candidates are hints, not
    claims: DIA deposits often contain distinct files of identical size."""
    name: str
    size_kb: float | None
    subproject_id: str
    same_size_candidates: list[str] = field(default_factory=list)


@dataclass
class IproxResolution:
    input_accession: str
    pxd_accession: str | None = None
    project_id: str | None = None
    title: str | None = None
    description: str | None = None
    privacy: int | None = None
    subproject_count_hint: int | None = None
    subprojects: list[IproxSubproject] = field(default_factory=list)
    px_species: list[str] = field(default_factory=list)
    px_instruments: list[str] = field(default_factory=list)
    px_orphans: list[PxXmlOrphan] = field(default_factory=list)

    @property
    def is_public(self) -> bool:
        return self.privacy == 1


def normalize_accession(value: str) -> str:
    return value.strip()


def _post_json(url: str, data: dict, timeout: int) -> dict:
    body = urllib.parse.urlencode(data).encode()
    request = urllib.request.Request(url, data=body, headers=HEADERS)
    last_error: Exception | None = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
                payload = json.loads(raw.decode("utf-8", errors="replace"))
                if not isinstance(payload, dict):
                    raise RuntimeError(f"Unexpected iProX payload from {url}")
                return payload
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt + 1 < RETRY_ATTEMPTS:
                time.sleep(RETRY_BACKOFF_SECONDS)
    raise RuntimeError(f"iProX request failed after {RETRY_ATTEMPTS} attempts ({url}): {last_error}")


def _get_json(url: str, params: dict, timeout: int) -> dict | list:
    request = urllib.request.Request(f"{url}?{urllib.parse.urlencode(params)}", headers=HEADERS)
    last_error: Exception | None = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
                payload = json.loads(raw.decode("utf-8", errors="replace"))
                if not isinstance(payload, (dict, list)):
                    raise RuntimeError(f"Unexpected iProX payload from {url}")
                return payload
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt + 1 < RETRY_ATTEMPTS:
                time.sleep(RETRY_BACKOFF_SECONDS)
    raise RuntimeError(f"iProX request failed after {RETRY_ATTEMPTS} attempts ({url}): {last_error}")


def fetch_project_record(project_id: str, timeout: int) -> dict:
    """POST findByProjectId.jsonp; returns the ``data`` object."""
    payload = _post_json(PROJECT_URL, {"projectId": project_id}, timeout)
    data = payload.get("data")
    if not isinstance(data, dict):
        raise RuntimeError(f"No project record returned for {project_id}")
    return data


def fetch_subproject_record(subproject_id: str, timeout: int) -> dict:
    """POST findBySubProjectId.jsonp; returns the ``data`` object."""
    payload = _post_json(
        SUBPROJECT_URL, {"subProjectId": subproject_id, "language": "en"}, timeout
    )
    data = payload.get("data")
    if not isinstance(data, dict):
        raise RuntimeError(f"No subproject record returned for {subproject_id}")
    return data


def fetch_subproject_list(project_id: str, timeout: int) -> list[dict]:
    """GET selectSubprosByPid.jsonp — the project page's own subproject table."""
    payload = _get_json(SUBPROJECTS_URL, {"pid": project_id, "langType": "en"}, timeout)
    if not isinstance(payload, list):
        raise RuntimeError(f"Unexpected subproject list payload for {project_id}")
    return [entry for entry in payload if isinstance(entry, dict)]


def fetch_proxi_json(url: str, timeout: int) -> dict:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": HEADERS["User-Agent"]},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8", errors="replace"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Unexpected ProteomeCentral payload from {url}")
    return payload


def resolve_pxd(accession: str, timeout: int) -> IproxResolution:
    payload = fetch_proxi_json(
        PX_PROXI_TEMPLATE.format(accession=urllib.parse.quote(accession.upper())),
        timeout,
    )
    if payload.get("status") == "ERROR":
        message = payload.get("description") or payload.get("error_code") or "lookup failed"
        raise RuntimeError(
            f"ProteomeCentral cannot resolve {accession.upper()} ({message}). "
            "If this is an unreleased iProX dataset, pass the IPX project id directly."
        )
    resolution = IproxResolution(
        input_accession=accession,
        pxd_accession=accession.upper(),
        title=payload.get("title"),
    )
    for item in payload.get("identifiers", []) or []:
        if not isinstance(item, dict):
            continue
        if "iprox" in (item.get("name") or "").lower() and item.get("value"):
            resolution.project_id = str(item["value"]).upper()
    for link in payload.get("fullDatasetLinks", []) or []:
        if not isinstance(link, dict):
            continue
        value = str(link.get("value") or "")
        if "iprox" in (link.get("name") or "").lower() and value:
            match = re.search(r"(IPX\d{10})", value, flags=re.IGNORECASE)
            if match:
                resolution.project_id = resolution.project_id or match.group(1).upper()
    if not resolution.project_id:
        raise RuntimeError(
            f"ProteomeCentral has no iProX identifier for {accession.upper()}; "
            "pass the IPX project id shown on the dataset page."
        )
    return resolution


def resolve_project(resolution: IproxResolution, timeout: int) -> IproxResolution:
    data = fetch_project_record(resolution.project_id, timeout)  # type: ignore[arg-type]
    info = data.get("projectInfo")
    if not isinstance(info, dict):
        # A 10-digit IPX id can also be a subproject; treat it as one.
        return resolve_subproject(resolution, timeout)
    resolution.title = info.get("projectTitleEnglish") or resolution.title
    resolution.description = info.get("descriptionEnglish") or None
    resolution.privacy = _as_int(info.get("privacy"))
    resolution.subproject_count_hint = _as_int(data.get("subproject_count"))
    for entry in fetch_subproject_list(resolution.project_id, timeout):  # type: ignore[arg-type]
        sub = IproxSubproject(
            subproject_id=str(entry.get("subprojectId") or ""),
            title=entry.get("subtitleEn"),
            species=entry.get("species"),
            instrument=entry.get("instrument"),
            file_count_hint=_as_int(entry.get("fileCount")),
            size_hint=_as_int(entry.get("fileSize")),
            privacy=_as_int(entry.get("privacy")),
        )
        if not sub.subproject_id:
            continue
        resolution.subprojects.append(sub)
    if not resolution.subprojects:
        raise RuntimeError(f"No subprojects listed for {resolution.project_id}")
    for sub in resolution.subprojects:
        fill_subproject_files(sub, timeout)
    return resolution


def resolve_subproject(resolution: IproxResolution, timeout: int) -> IproxResolution:
    data = fetch_subproject_record(resolution.project_id, timeout)  # type: ignore[arg-type]
    info = data.get("subProjectInfo")
    if not isinstance(info, dict):
        raise RuntimeError(f"iProX has no record for {resolution.input_accession}")
    sub = IproxSubproject(
        subproject_id=str(info.get("subprojectId") or resolution.project_id),
        title=info.get("subtitleEn"),
        species=info.get("species"),
        instrument=info.get("instrument"),
        privacy=_as_int(info.get("privacy")),
    )
    parent = info.get("projectId")
    if parent:
        # The subproject record names its parent project; it beats the input id.
        resolution.project_id = str(parent)
    elif not resolution.project_id:
        resolution.project_id = sub.subproject_id
    if not resolution.title:
        resolution.title = info.get("subtitleEn")
    fill_subproject_files(sub, timeout)
    resolution.subprojects = [sub]
    return resolution


def fill_subproject_files(sub: IproxSubproject, timeout: int) -> None:
    data = fetch_subproject_record(sub.subproject_id, timeout)
    info = data.get("subProjectInfo")
    if isinstance(info, dict):
        sub.experiment_protocol = info.get("experimentprotocol") or None
        sub.informatics_protocol = info.get("informaticsprotocol") or None
        sub.experiment_type = info.get("erperimentType") or None
    raw_files = data.get("subdatafilesInfo") or []
    for entry in raw_files:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("fileName") or "")
        if not name:
            continue
        size = entry.get("fileSize")
        try:
            size_kb = float(size) if size not in (None, "") else None
        except (TypeError, ValueError):
            size_kb = None
        sub.files.append(
            IproxFile(
                name=name,
                file_type=str(entry.get("fileType") or ""),
                size_kb=size_kb,
                subproject_id=sub.subproject_id,
            )
        )


def _as_int(value: object) -> int | None:
    try:
        return int(str(value)) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def make_uri(project_id: str, subproject_id: str, name: str) -> str:
    return f"{DOWNLOAD_BASE}/{project_id}/{subproject_id}/{name}"


# --------------------------------------------------------------------------- PX XML
@dataclass
class PxXmlEntry:
    name: str
    size_kb: float | None = None
    uri: str = ""


@dataclass
class PxXml:
    species: list[str] = field(default_factory=list)
    instruments: list[str] = field(default_factory=list)
    entries: dict[str, list[PxXmlEntry]] = field(default_factory=dict)


_SIZE_MATCH_TOLERANCE_KB = 30.0  # the XML rounds to 2-decimal MB (10.24 KB) plus API rounding


def px_xml_url(project_id: str) -> str:
    """The canonical PX XML location on the download server."""
    return f"{DOWNLOAD_BASE}/{project_id}/PX_{project_id}.xml"


def _read_xml_source(source: str, timeout: int) -> str:
    """Return XML text from a local path or a URL."""
    if re.match(r"^https?://", source, re.IGNORECASE):
        request = urllib.request.Request(
            source, headers={"Accept": "*/*", "User-Agent": HEADERS["User-Agent"]}
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    with open(source, encoding="utf-8-sig", errors="replace") as fh:
        return fh.read()


def fetch_px_xml_texts(source: str, project_id: str, subproject_ids: list[str],
                       timeout: int) -> list[str]:
    """The PX XML text(s) to parse.

    'auto' fetches the canonical project-level PX XML *and* every subproject's own
    XML — the project XML carries species/instruments and the renamed file list, while
    the subproject XMLs are the ones that sometimes keep an original acquisition name
    (an extra entry sharing the renamed file's size). A missing subproject XML is
    warned about, not fatal.
    """
    if source.lower() != "auto":
        return [_read_xml_source(source, timeout)]
    texts = [_read_xml_source(px_xml_url(project_id), timeout)]
    for sub in subproject_ids:
        try:
            texts.append(_read_xml_source(
                f"{DOWNLOAD_BASE}/{project_id}/{sub}/{sub}.xml", timeout))
        except OSError as exc:
            print(f"warning: no subproject XML for {sub}: {exc}", file=sys.stderr)
    return texts


def merge_px(pieces: list[PxXml]) -> PxXml:
    """Combine several PX XML parses (project- and subproject-level) into one."""
    merged = PxXml()
    for px in pieces:
        for species in px.species:
            if species not in merged.species:
                merged.species.append(species)
        for instrument in px.instruments:
            if instrument not in merged.instruments:
                merged.instruments.append(instrument)
        for subproject, entries in px.entries.items():
            merged.entries.setdefault(subproject, []).extend(entries)
    return merged


def parse_px_xml(text: str) -> PxXml:
    """Parse an iProX PX XML (project- or subproject-level; namespaces tolerated).

    Extracts the species list, the instrument list, and every ``DatasetFile`` with
    its URI (the URI's path segments give the subproject) and its MB size.
    """
    px = PxXml()
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ValueError(f"not a parseable PX XML: {exc}") from exc

    def strip(tag: str) -> str:
        return tag.split("}")[-1]

    for elem in root.iter():
        tag = strip(elem.tag)
        if tag == "cvParam":
            name = (elem.get("name") or "").strip()
            value = (elem.get("value") or "").strip()
            if name == "taxonomy: scientific name" and value and value not in px.species:
                px.species.append(value)
        if tag == "Instrument":
            for cv in elem.iter():
                if strip(cv.tag) == "cvParam":
                    name = (cv.get("name") or "").strip()
                    if name and name not in px.instruments:
                        px.instruments.append(name)
        if tag == "DatasetFile":
            name = (elem.get("name") or "").strip()
            if not name:
                continue
            entry = PxXmlEntry(name=name)
            for cv in elem.iter():
                if strip(cv.tag) != "cvParam":
                    continue
                value = (cv.get("value") or "").strip()
                if value.startswith("http://") or value.startswith("https://"):
                    entry.uri = value
                size = cv.get("filesize") or ""
                if size and entry.size_kb is None:
                    m = re.match(r"^([\d.]+)\s*MB$", size, re.IGNORECASE)
                    if m:
                        entry.size_kb = float(m.group(1)) * 1024.0
            subproject = ""
            if entry.uri:
                parts = entry.uri.split("/")
                for i, part in enumerate(parts):
                    if re.match(r"^IPX\d{10}$", part, re.IGNORECASE):
                        if i + 1 < len(parts) and re.match(r"^IPX\d{10}$", parts[i + 1], re.IGNORECASE):
                            subproject = parts[i + 1].upper()
                        break
            px.entries.setdefault(subproject, []).append(entry)
    return px


def apply_xml_names(resolution: IproxResolution, px: PxXml) -> None:
    """Record the PX XML's species/instruments, and report XML entries no deposited
    file matches by name as *orphans* (a renamed acquisition name, or a leftover).

    Deliberately no automatic size-matching: DIA deposits contain distinct files of
    identical size (several G-*.zip and B-*.zip share one 2-decimal-MB size), so a
    size-based rename mapping would fabricate correspondences. The orphans carry
    their same-size deposited candidates as hints for a human to judge.
    """
    if px.species:
        resolution.px_species = list(px.species)
    if px.instruments:
        resolution.px_instruments = list(px.instruments)
    for sub in resolution.subprojects:
        entries = px.entries.get(sub.subproject_id, [])
        api_names = {f.name for f in sub.files}
        for entry in entries:
            if entry.name in api_names:
                continue
            candidates = [
                f.name for f in sub.files
                if f.size_kb is not None and entry.size_kb is not None
                and abs(f.size_kb - entry.size_kb) <= _SIZE_MATCH_TOLERANCE_KB
            ]
            resolution.px_orphans.append(
                PxXmlOrphan(entry.name, entry.size_kb, sub.subproject_id, candidates)
            )


def build_record(resolution: IproxResolution) -> dict:
    """A reconcile-compatible record (the PRIDE /projects/{acc} shape, flat).

    The prose keys map onto the iProX fields: title/projectDescription from the project,
    the sample- and data-processing protocols joined from the subprojects, and the
    quantificationMethods list carries each subproject's experiment type and title so the
    labelling check catches e.g. a "TMT-labeled" subproject annotated label-free.
    """
    protocols = [s.experiment_protocol for s in resolution.subprojects if s.experiment_protocol]
    informatics = [s.informatics_protocol for s in resolution.subprojects if s.informatics_protocol]
    methods = []
    for s in resolution.subprojects:
        for value in (s.experiment_type, s.title):
            if value and value not in methods:
                methods.append(value)
    return {
        "accession": resolution.pxd_accession or resolution.input_accession,
        "title": resolution.title or "",
        "projectDescription": resolution.description or "",
        "sampleProcessingProtocol": "\n\n".join(dict.fromkeys(protocols)),
        "dataProcessingProtocol": "\n\n".join(dict.fromkeys(informatics)),
        "quantificationMethods": methods,
    }


def file_matches_mode(file: IproxFile, mode: str) -> bool:
    if mode == "all":
        return True
    return file.is_raw


def resolve_accession(accession: str, timeout: int) -> IproxResolution:
    accession = normalize_accession(accession)
    if PXD_RE.match(accession):
        return resolve_project(resolve_pxd(accession.upper(), timeout), timeout)
    if IPX_RE.match(accession):
        resolution = IproxResolution(
            input_accession=accession.upper(), project_id=accession.upper()
        )
        return resolve_project(resolution, timeout)
    raise SystemExit(
        f"Unsupported accession format: {accession} (expected PXD###### or IPX##########)"
    )


def emit_text(files: list[IproxFile]) -> None:
    for file in files:
        print(file.name)


def emit_tsv(resolution: IproxResolution, files: list[IproxFile]) -> None:
    print(
        "\t".join(
            [
                "input_accession",
                "pxd_accession",
                "project_id",
                "subproject_id",
                "subproject_title",
                "basename",
                "file_type",
                "size_kb",
                "uri",
            ]
        )
    )
    sub_titles = {s.subproject_id: s.title or "" for s in resolution.subprojects}
    for file in files:
        print(
            "\t".join(
                [
                    resolution.input_accession,
                    resolution.pxd_accession or "",
                    resolution.project_id or "",
                    file.subproject_id,
                    sub_titles.get(file.subproject_id, ""),
                    file.name,
                    file.file_type,
                    str(file.size_kb) if file.size_kb is not None else "",
                    make_uri(resolution.project_id or "", file.subproject_id, file.name),
                ]
            )
        )


def emit_json(resolution: IproxResolution, files: list[IproxFile]) -> None:
    payload = {
        "input_accession": resolution.input_accession,
        "pxd_accession": resolution.pxd_accession,
        "iprox_project": resolution.project_id,
        "title": resolution.title,
        "privacy": resolution.privacy,
        "subproject_count_hint": resolution.subproject_count_hint,
        "px_xml": {
            "species": resolution.px_species,
            "instruments": resolution.px_instruments,
            "orphan_entries": [
                {
                    "name": o.name,
                    "size_kb": o.size_kb,
                    "subproject_id": o.subproject_id,
                    "same_size_candidates": o.same_size_candidates,
                }
                for o in resolution.px_orphans
            ],
        },
        "subprojects": [
            {
                "subproject_id": s.subproject_id,
                "title": s.title,
                "species": s.species,
                "instrument": s.instrument,
                "file_count_hint": s.file_count_hint,
                "size_hint": s.size_hint,
                "files": [
                    {
                        "name": f.name,
                        "file_type": f.file_type,
                        "size_kb": f.size_kb,
                        "uri": make_uri(resolution.project_id or "", f.subproject_id, f.name),
                    }
                    for f in s.files
                ],
            }
            for s in resolution.subprojects
        ],
        "raw_file_count": len(files),
    }
    json.dump(payload, sys.stdout, indent=2)
    print()


def warn_privacy(resolution: IproxResolution) -> None:
    if not resolution.is_public:
        print(
            f"WARNING: iProX project {resolution.project_id} is not public "
            "(privacy={resolution.privacy}); file lists are returned but downloads "
            "require a login.",
            file=sys.stderr,
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("accession", help="iProX project/subproject id (IPX##########) or PXD accession")
    parser.add_argument(
        "--mode",
        choices=("raw", "all"),
        default="raw",
        help="Which file classes to emit: vendor raw only (fileType RAW), or every deposited file",
    )
    parser.add_argument(
        "--format",
        choices=("text", "tsv", "json"),
        default="text",
        help="Output format: bare file names (files.json-compatible), a per-file table, or structured JSON",
    )
    parser.add_argument(
        "--subproject",
        help="Only emit files of this subproject id (IPX##########); repeatable",
        action="append",
        default=None,
    )
    parser.add_argument(
        "--record",
        help="Also write a reconcile-compatible record JSON (PRIDE /projects/{acc} shape) to this path",
        default=None,
    )
    parser.add_argument(
        "--px-xml",
        help="Parse a PX XML for species/instruments and original file names: a local path, "
        "a URL, or 'auto' for the canonical project PX_<project>.xml plus every subproject XML "
        "(the subproject XMLs are the ones that keep original acquisition names)",
        default=None,
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="Request timeout in seconds (iProX is slow; default %(default)s)",
    )
    return parser.parse_args(argv)


def run_cli(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    resolution = resolve_accession(args.accession, args.timeout)
    warn_privacy(resolution)
    if args.px_xml:
        texts = fetch_px_xml_texts(
            args.px_xml, resolution.project_id or "",
            [s.subproject_id for s in resolution.subprojects], args.timeout)
        apply_xml_names(resolution, merge_px([parse_px_xml(t) for t in texts]))
    if args.record:
        record = build_record(resolution)
        with open(args.record, "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=2, ensure_ascii=False)
        print(f"record written to {args.record}", file=sys.stderr)
    if args.subproject:
        wanted = {s.upper() for s in args.subproject}
        resolution.subprojects = [s for s in resolution.subprojects if s.subproject_id in wanted]
        if not resolution.subprojects:
            raise SystemExit(f"none of the requested subprojects {sorted(wanted)} exist")
    files = [
        file
        for sub in resolution.subprojects
        for file in sub.files
        if file_matches_mode(file, args.mode)
    ]
    if args.format == "json":
        emit_json(resolution, files)
    elif args.format == "tsv":
        emit_tsv(resolution, files)
    else:
        emit_text(files)
    return 0


def main() -> None:
    sys.exit(run_cli())


if __name__ == "__main__":
    main()

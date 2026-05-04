"""Resolve MassIVE raw or acquisition file names for a PXD/MSV accession.

This helper is intended for SDRF curation when:
- a ProteomeXchange accession is hosted by MassIVE
- PRIDE `/projects/{PXD}/files/all` is empty or incomplete
- you need actual file names for `comment[data file]`

Resolution chain:
1. If the input is a PXD, query ProteomeCentral PROXI to resolve the MassIVE ID.
2. If a MassIVE task is available, query the MassIVE detail JSON endpoint.
3. Recursively walk the MassIVE FTP tree to list files.

The helper defaults to vendor raw-like files, but can also include open formats
such as mzML/mzXML or emit every file under the dataset FTP root.
"""

from __future__ import annotations

import argparse
import ftplib
import json
import posixpath
import re
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass


PX_PROXI_TEMPLATE = "https://proteomecentral.proteomexchange.org/api/proxi/v0.1/datasets/{accession}"
MASSIVE_DETAIL_TEMPLATE = (
    "https://massive.ucsd.edu/ProteoSAFe/MassiveServlet?task={task}&function=massiveinformation"
)

PXD_RE = re.compile(r"^PXD\d{6,}$", re.IGNORECASE)
MSV_RE = re.compile(r"^MSV\d+(?:\.\d+)?$", re.IGNORECASE)
TASK_RE = re.compile(r"^[0-9a-f]{32}$", re.IGNORECASE)

VENDOR_RAW_SUFFIXES = (
    ".raw",
    ".wiff",
    ".wiff.scan",
    ".d",
    ".baf",
    ".yep",
    ".lcd",
    ".tdf",
    ".tsf",
    ".fid",
)
OPEN_ACQUISITION_SUFFIXES = (".mzml", ".mzxml")

DEFAULT_TIMEOUT = 120
USER_AGENT = "sdrf-skills/massive-raw-files/0.1"


@dataclass
class MassiveResolution:
    input_accession: str
    pxd_accession: str | None = None
    massive_accession: str | None = None
    task: str | None = None
    ftp_url: str | None = None
    title: str | None = None
    hosting_repository: str | None = None
    filecount_hint: int | None = None
    filesize_hint: str | None = None


def fetch_json(url: str) -> object:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT) as response:
        return json.load(response)


def normalize_accession(value: str) -> str:
    return value.strip()


def parse_task_from_url(url: str) -> str | None:
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    task = query.get("task", [None])[0]
    if task and TASK_RE.match(task):
        return task
    return None


def parse_massive_from_url(url: str) -> str | None:
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    for key in ("id", "dataset", "dataset_id"):
        value = query.get(key, [None])[0]
        if value and MSV_RE.match(value):
            return value.upper()
    match = re.search(r"(MSV\d+(?:\.\d+)?)", url, flags=re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def resolve_from_proteomecentral(pxd_accession: str) -> MassiveResolution:
    payload = fetch_json(PX_PROXI_TEMPLATE.format(accession=urllib.parse.quote(pxd_accession)))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Unexpected ProteomeCentral payload for {pxd_accession}")

    resolution = MassiveResolution(
        input_accession=pxd_accession,
        pxd_accession=pxd_accession.upper(),
        title=payload.get("title"),
    )

    dataset_summary = payload.get("datasetSummary") or {}
    if isinstance(dataset_summary, dict):
        resolution.hosting_repository = dataset_summary.get("hostingRepository")

    for item in payload.get("identifiers", []) or []:
        if not isinstance(item, dict):
            continue
        name = (item.get("name") or "").lower()
        value = item.get("value") or ""
        if "massive dataset identifier" in name and value:
            resolution.massive_accession = value.upper()

    for item in payload.get("fullDatasetLinks", []) or []:
        if not isinstance(item, dict):
            continue
        name = (item.get("name") or "").lower()
        value = item.get("value") or ""
        if not value:
            continue
        if "massive dataset uri" in name:
            resolution.task = resolution.task or parse_task_from_url(value)
            resolution.massive_accession = resolution.massive_accession or parse_massive_from_url(value)
        elif "dataset ftp location" in name:
            resolution.ftp_url = value

    return resolution


def enrich_from_massive_detail(resolution: MassiveResolution) -> MassiveResolution:
    if not resolution.task:
        return resolution
    payload = fetch_json(MASSIVE_DETAIL_TEMPLATE.format(task=urllib.parse.quote(resolution.task)))
    if not isinstance(payload, dict):
        return resolution

    if not resolution.massive_accession and payload.get("dataset_id"):
        resolution.massive_accession = str(payload["dataset_id"]).upper()
    if not resolution.pxd_accession and payload.get("pxaccession"):
        resolution.pxd_accession = str(payload["pxaccession"]).upper()
    if not resolution.ftp_url and payload.get("ftp"):
        resolution.ftp_url = str(payload["ftp"])
    if not resolution.title and payload.get("title"):
        resolution.title = str(payload["title"])
    filecount = payload.get("filecount")
    if filecount not in (None, "", "null"):
        try:
            resolution.filecount_hint = int(str(filecount))
        except ValueError:
            pass
    filesize = payload.get("filesize")
    if filesize not in (None, "", "null"):
        resolution.filesize_hint = str(filesize)
    return resolution


def ftp_candidates(resolution: MassiveResolution) -> list[str]:
    candidates: list[str] = []
    if resolution.ftp_url:
        candidates.append(resolution.ftp_url)
    if resolution.massive_accession:
        msv = resolution.massive_accession
        for url in (
            f"ftp://massive-ftp.ucsd.edu/v02/{msv}/",
            f"ftp://massive.ucsd.edu/v02/{msv}/",
            f"ftp://massive.ucsd.edu/{msv}/",
        ):
            if url not in candidates:
                candidates.append(url)
    return candidates


def parse_ftp_url(url: str) -> tuple[str, str]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "ftp" or not parsed.hostname:
        raise ValueError(f"Unsupported FTP URL: {url}")
    path = parsed.path or "/"
    return parsed.hostname, path


def is_container_raw_dir(name: str) -> bool:
    return name.lower().endswith(".d")


def file_matches_mode(path: str, mode: str) -> bool:
    lower = path.lower()
    if mode == "all":
        return True
    if lower.endswith(VENDOR_RAW_SUFFIXES):
        return True
    if mode == "acquisition" and lower.endswith(OPEN_ACQUISITION_SUFFIXES):
        return True
    return False


def ftp_walk_files(host: str, root_path: str, mode: str) -> list[str]:
    ftp = ftplib.FTP(host, timeout=DEFAULT_TIMEOUT)
    ftp.login("anonymous", "anonymous")
    found: list[str] = []

    def walk_nlst(path: str) -> None:
        try:
            entries = ftp.nlst(path)
        except ftplib.error_perm:
            return

        for entry in entries:
            normalized = entry.rstrip("/")
            if not normalized or normalized == path.rstrip("/"):
                continue
            base = posixpath.basename(normalized)
            if base in (".", ".."):
                continue

            current_dir = ftp.pwd()
            try:
                ftp.cwd(normalized)
            except ftplib.error_perm:
                if file_matches_mode(normalized, mode):
                    found.append(normalized)
                continue
            else:
                ftp.cwd(current_dir)
                if is_container_raw_dir(base):
                    if file_matches_mode(normalized, mode):
                        found.append(normalized)
                    continue
                walk_nlst(normalized)

    def walk(path: str) -> None:
        try:
            entries = list(ftp.mlsd(path))
        except (ftplib.error_perm, AttributeError):
            # Some MassIVE servers expose only NLST-style directory listings.
            # Recurse by probing each entry with cwd() so we do not stop at the
            # top-level folder names.
            walk_nlst(path)
            return

        for name, facts in entries:
            if name in (".", ".."):
                continue
            full_path = posixpath.join(path.rstrip("/"), name) if path != "/" else f"/{name}"
            entry_type = (facts.get("type") or "").lower()
            if entry_type == "dir":
                if is_container_raw_dir(name):
                    if file_matches_mode(full_path, mode):
                        found.append(full_path)
                    continue
                walk(full_path)
            elif entry_type == "file":
                if file_matches_mode(full_path, mode):
                    found.append(full_path)

    try:
        walk(root_path.rstrip("/") or "/")
    finally:
        try:
            ftp.quit()
        except Exception:
            ftp.close()
    return sorted(set(found))


def resolve_accession(accession: str) -> MassiveResolution:
    accession = normalize_accession(accession)
    if PXD_RE.match(accession):
        resolution = resolve_from_proteomecentral(accession.upper())
        return enrich_from_massive_detail(resolution)
    if MSV_RE.match(accession):
        return MassiveResolution(input_accession=accession.upper(), massive_accession=accession.upper())
    if TASK_RE.match(accession):
        resolution = MassiveResolution(input_accession=accession.lower(), task=accession.lower())
        return enrich_from_massive_detail(resolution)
    raise SystemExit(f"Unsupported accession format: {accession}")


def emit_text(files: list[str]) -> None:
    for file_path in files:
        print(file_path)


def emit_tsv(resolution: MassiveResolution, files: list[str]) -> None:
    print("\t".join(["input_accession", "pxd_accession", "massive_accession", "basename", "ftp_path"]))
    for file_path in files:
        print(
            "\t".join(
                [
                    resolution.input_accession,
                    resolution.pxd_accession or "",
                    resolution.massive_accession or "",
                    posixpath.basename(file_path.rstrip("/")),
                    file_path,
                ]
            )
        )


def emit_json(resolution: MassiveResolution, ftp_url: str | None, files: list[str]) -> None:
    payload = {
        "input_accession": resolution.input_accession,
        "pxd_accession": resolution.pxd_accession,
        "massive_accession": resolution.massive_accession,
        "task": resolution.task,
        "title": resolution.title,
        "hosting_repository": resolution.hosting_repository,
        "ftp_url": ftp_url,
        "filecount_hint": resolution.filecount_hint,
        "filesize_hint": resolution.filesize_hint,
        "raw_file_count": len(files),
        "files": files,
    }
    json.dump(payload, sys.stdout, indent=2)
    print()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("accession", help="PXD accession, MassIVE MSV accession, or MassIVE task id")
    parser.add_argument(
        "--mode",
        choices=("raw", "acquisition", "all"),
        default="raw",
        help="Which file classes to emit: vendor raw only, acquisition files (raw + mzML/mzXML), or all files",
    )
    parser.add_argument(
        "--format",
        choices=("text", "tsv", "json"),
        default="text",
        help="Output format",
    )
    parser.add_argument(
        "--ftp-url",
        help="Override the FTP root when the repository metadata is incomplete",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Resolve and print dataset-level metadata without walking the FTP tree",
    )
    return parser.parse_args(argv)


def run_cli(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    resolution = resolve_accession(args.accession)
    if args.summary_only:
        emit_json(resolution, resolution.ftp_url, [])
        return 0

    candidates = [args.ftp_url] if args.ftp_url else ftp_candidates(resolution)
    if not candidates:
        raise SystemExit("Could not determine a MassIVE FTP root for this accession.")

    last_error: Exception | None = None
    files: list[str] = []
    chosen_ftp: str | None = None
    for ftp_url in candidates:
        try:
            host, path = parse_ftp_url(ftp_url)
            files = ftp_walk_files(host, path, args.mode)
            chosen_ftp = ftp_url
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue

    if chosen_ftp is None:
        if last_error:
            raise SystemExit(f"Failed to list MassIVE files: {last_error}")
        raise SystemExit("Failed to list MassIVE files.")

    if args.format == "json":
        emit_json(resolution, chosen_ftp, files)
    elif args.format == "tsv":
        emit_tsv(resolution, files)
    else:
        emit_text(files)
    return 0


def main() -> None:
    sys.exit(run_cli())


if __name__ == "__main__":
    main()

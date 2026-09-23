"""Expand a sample table and a technical table into a structurally valid SDRF.

The model writes two small tables; this tool produces the SDRF. Fractions, technical
replicates, channel rows, repeated columns and column order are decided here, the same
way every time. Anything the tool would have to guess - above all a channel-to-sample
map - it refuses, names the row, and writes nothing.

Multiple-cardinality values in technical.tsv are separated by '|' (not ';', which is
part of the NT=;AC= value syntax)."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from tools.contract import Contract, template_contract

CHANNEL_RE = re.compile(r"^(TMT|iTRAQ|SILAC)", re.I)
MULTI_SEP = "|"
STRUCTURAL = {"source name", "files", "label", "assay name", "technical replicate"}
BIO_REP = "characteristics[biological replicate]"


class BuildError(Exception):
    pass


@dataclass
class Sample:
    source: str
    files: list[str]
    label: str
    assay: str | None
    technical_replicate: int
    values: dict[str, str] = field(default_factory=dict)


def read_table(path: str | Path) -> tuple[list[str], list[dict[str, str]]]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        header = [h.strip() for h in (reader.fieldnames or [])]
        rows = [{(k or "").strip(): (v or "").strip() for k, v in r.items()} for r in reader]
    return header, rows


def parse_samples(header: list[str], rows: list[dict[str, str]]) -> list[Sample]:
    for need in ("source name", "files", "label"):
        if need not in header:
            raise BuildError(f"samples.tsv: missing required column '{need}'")
    out = []
    for n, r in enumerate(rows, start=2):
        files = [f.strip() for f in r["files"].split(",") if f.strip()]
        if not files:
            raise BuildError(f"samples.tsv row {n} ('{r['source name']}'): 'files' is empty")
        if not r["label"]:
            raise BuildError(f"samples.tsv row {n} ('{r['source name']}'): 'label' is empty")
        tr = r.get("technical replicate") or "1"
        if not tr.isdigit():
            raise BuildError(f"samples.tsv row {n}: 'technical replicate' must be an integer, got '{tr}'")
        values = {k: v for k, v in r.items() if k not in STRUCTURAL and k}
        out.append(Sample(r["source name"], files, r["label"], r.get("assay name") or None, int(tr), values))
    return out


def parse_technical(rows: list[dict[str, str]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for n, r in enumerate(rows, start=2):
        col, val = r.get("column", ""), r.get("value", "")
        if not col:
            raise BuildError(f"technical.tsv row {n}: 'column' is empty")
        out[col] = [v.strip() for v in val.split(MULTI_SEP) if v.strip()] or [""]
    return out


def is_channel(label: str) -> bool:
    return bool(CHANNEL_RE.match(label.strip()))


def check_files(samples: list[Sample], files: list[str]) -> None:
    known = set(files)
    owner: dict[str, str] = {}
    for s in samples:
        for f in s.files:
            if f not in known:
                raise BuildError(f"samples.tsv ('{s.source}'): file '{f}' is not in files.json")
            if not is_channel(s.label) and f in owner:
                raise BuildError(f"samples.tsv: file '{f}' is claimed by both '{owner[f]}' and '{s.source}'")
            owner[f] = s.source


def check_channels(samples: list[Sample]) -> None:
    multiplexed = [s for s in samples if is_channel(s.label)]
    if not multiplexed:
        return
    plex = sorted({s.label for s in multiplexed})
    per_run: dict[str, set[str]] = {}
    for s in multiplexed:
        for f in s.files:
            per_run.setdefault(f, set()).add(s.label)
    for run, channels in sorted(per_run.items()):
        missing = [c for c in plex if c not in channels]
        if missing:
            raise BuildError(
                f"channel map incomplete for run '{run}': no row for {', '.join(missing)}. "
                f"Add a row per missing channel (empty 'source name' marks it unused); build never fills a channel in.")


def check_coordinates(samples: list[Sample]) -> None:
    """(source name, biological replicate, technical replicate, fraction identifier) must be unique.

    Two rows of the same source with the same replicates would both number their files from
    fraction 1: that is two replicate runs written as if they were the same injection. The
    fix is the model's to make, so this refuses instead of renumbering."""
    seen: dict[tuple[str, str, int, int, str], str] = {}
    for s in samples:
        if not s.source:
            continue
        for k in range(1, len(s.files) + 1):
            key = (s.source, s.values.get(BIO_REP, ""), s.technical_replicate, k, s.label)
            if key in seen:
                raise BuildError(
                    f"samples.tsv: two rows for source '{s.source}' share biological replicate "
                    f"'{key[1] or '-'}', technical replicate {s.technical_replicate} and fraction {k} "
                    f"(files '{seen[key]}' and '{s.files[k - 1]}'). Separate replicate runs need a different "
                    f"'{BIO_REP}' or 'technical replicate'; fractions of one injection go in one row's 'files'.")
            seen[key] = s.files[k - 1]


def _stem(name: str) -> str:
    return re.sub(r"\.(raw|d|wiff2?|mzml|mzxml|mgf|zip|gz)$", "", name, flags=re.I)


def expand(samples: list[Sample], technical: dict[str, list[str]], contract: Contract
           ) -> tuple[list[str], list[list[str]]]:
    spec = {c.name: c for c in contract.columns}
    contract_names = [c.name for c in contract.columns]
    extra_char = sorted({k for s in samples for k in s.values
                         if k.startswith("characteristics[") and k not in spec})
    extra_fv = sorted({k for s in samples for k in s.values if k.startswith("factor value[")})
    used = ({k for s in samples for k, v in s.values.items() if v}
            | {k for k, v in technical.items() if any(v)})
    # header: contract order; optional columns only when something fills them; extra characteristics
    # after the contract's; factor values last; 'multiple' columns repeated per value
    header: list[str] = []
    for name in contract_names:
        col = spec[name]
        if name == "comment[sdrf template]":
            header += [name] * len(contract.templates)
            continue
        if col.requirement != "required" and name not in used:
            continue
        if col.multiple and name in technical:
            header += [name] * len(technical[name])
        else:
            header.append(name)
    last_char = max((i for i, h in enumerate(header) if h.startswith("characteristics[")), default=0)
    header[last_char + 1:last_char + 1] = extra_char
    header += extra_fv
    rows: list[list[str]] = []
    template_cells = [f"NT={t};VV=v{contract.versions[t]}" for t in contract.templates]
    for s in samples:
        if not s.source:  # explicitly unused channel
            continue
        for k, f in enumerate(s.files, start=1):
            fixed = {
                "source name": s.source,
                "assay name": s.assay or (f"{_stem(f)}-{s.label}" if is_channel(s.label) else _stem(f)),
                "comment[data file]": f,
                "comment[label]": s.label,
                "comment[fraction identifier]": str(k),
                "comment[technical replicate]": str(s.technical_replicate),
            }
            row: list[str] = []
            multi_i: dict[str, int] = {}
            tmpl_i = 0
            for h in header:
                if h == "comment[sdrf template]":
                    row.append(template_cells[tmpl_i])
                    tmpl_i += 1
                elif h in fixed:
                    row.append(fixed[h])
                elif s.values.get(h):
                    row.append(s.values[h])
                elif h in technical:
                    i = multi_i.get(h, 0)
                    multi_i[h] = i + 1
                    vals = technical[h]
                    row.append(vals[i] if i < len(vals) else "")
                else:
                    col = spec.get(h)
                    row.append("not available" if (col and col.requirement == "required"
                                                   and col.allow_not_available) else "")
            rows.append(row)
    return header, rows


def write_sdrf(header: list[str], rows: list[list[str]], path: str | Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n", quoting=csv.QUOTE_NONE, escapechar="\\")
        w.writerow(header)
        w.writerows(rows)


def build(samples_path, technical_path, files_path, templates: list[str], out_path) -> int:
    contract = template_contract(templates)
    header, rows = read_table(samples_path)
    samples = parse_samples(header, rows)
    technical = parse_technical(read_table(technical_path)[1]) if technical_path else {}
    files = json.loads(Path(files_path).read_text())
    if isinstance(files, dict):
        files = files.get("files", [])
    check_files(samples, list(files))
    check_channels(samples)
    check_coordinates(samples)
    h, r = expand(samples, technical, contract)
    write_sdrf(h, r, out_path)
    print(f"wrote {out_path}: {len(r)} rows x {len(h)} columns")
    return 0

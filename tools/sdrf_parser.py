"""Lightweight SDRF TSV parser.

Reads .sdrf.tsv files into structured representations without pandas.
Extracts column metadata, parses structured values (modifications,
instruments, templates), and groups unique values per column for
efficient ontology validation.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Column type classification
# ---------------------------------------------------------------------------

_COL_PATTERNS = {
    "characteristics": re.compile(r"^characteristics\[(.+)\]$", re.I),
    "comment": re.compile(r"^comment\[(.+)\]$", re.I),
    "factor_value": re.compile(r"^factor value\[(.+)\]$", re.I),
}

_ANCHOR_COLUMNS = frozenset({
    "source name",
    "assay name",
    "technology type",
})


@dataclass
class ColumnInfo:
    """Metadata about a single SDRF column."""
    raw_name: str
    col_type: str  # "characteristics", "comment", "factor_value", "anchor", "other"
    inner_name: str  # e.g. "organism" from "characteristics[organism]"
    index: int  # positional index in the TSV


@dataclass
class ModificationParam:
    """Parsed modification parameter (NT=;AC=;TA=/PP=;MT=)."""
    nt: str = ""   # name
    ac: str = ""   # accession (e.g. UNIMOD:1)
    ta: str = ""   # target amino acid
    pp: str = ""   # positional parameter (e.g. Protein N-term)
    mt: str = ""   # modification type (Fixed / Variable)
    raw: str = ""  # original string


@dataclass
class InstrumentParam:
    """Parsed instrument value (AC=;NT=)."""
    ac: str = ""
    nt: str = ""
    raw: str = ""


@dataclass
class TemplateParam:
    """Parsed template declaration (NT=;VV=)."""
    nt: str = ""  # template name
    vv: str = ""  # version
    raw: str = ""


@dataclass
class SDRFFile:
    """Parsed representation of an SDRF file."""
    path: str | None
    columns: list[ColumnInfo]
    rows: list[dict[str, str]]  # list of {col_key: value}
    raw_headers: list[str]
    col_keys: list[str] = field(default_factory=list)  # disambiguated keys for row dicts
    warnings: list[str] = field(default_factory=list)  # parse-time warnings

    # ---- convenience properties ----

    @property
    def n_rows(self) -> int:
        return len(self.rows)

    @property
    def n_columns(self) -> int:
        return len(self.columns)

    def column_names(self, col_type: str | None = None) -> list[str]:
        """Return column raw names, optionally filtered by type."""
        if col_type is None:
            return [c.raw_name for c in self.columns]
        return [c.raw_name for c in self.columns if c.col_type == col_type]

    def key_for_column(self, index: int) -> str:
        """Return the disambiguated dict key for column at given index."""
        if self.col_keys and index < len(self.col_keys):
            return self.col_keys[index]
        return self.columns[index].raw_name

    def unique_values(self, col_key: str) -> set[str]:
        """Return unique non-empty values for a column key (case-sensitive)."""
        return {row[col_key] for row in self.rows if row.get(col_key, "").strip()}

    def all_keys_for_name(self, raw_name: str) -> list[str]:
        """Return all disambiguated keys that match a raw column name."""
        keys = []
        for i, col in enumerate(self.columns):
            if col.raw_name == raw_name:
                keys.append(self.key_for_column(i))
        return keys

    def detected_templates(self) -> list[TemplateParam]:
        """Extract template declarations from comment[sdrf template] columns."""
        templates: list[TemplateParam] = []
        for i, col in enumerate(self.columns):
            if col.col_type == "comment" and col.inner_name.lower() == "sdrf template":
                key = self.key_for_column(i)
                for val in self.unique_values(key):
                    templates.append(parse_template_value(val))
        return templates

    def detected_template_names(self) -> list[str]:
        """Return just the template name strings."""
        return [t.nt for t in self.detected_templates() if t.nt]

    def auto_detect_templates(self) -> list[str]:
        """Auto-detect applicable templates from content (when not declared)."""
        declared = self.detected_template_names()
        if declared:
            return declared
        return _auto_detect_templates(self)


# ---------------------------------------------------------------------------
# Parsers for structured cell values
# ---------------------------------------------------------------------------

_KV_RE = re.compile(r"(\w+)=([^;]*)")


def parse_modification(value: str) -> ModificationParam:
    """Parse a modification parameter string like NT=Acetyl;AC=UNIMOD:1;TA=K;MT=Variable."""
    m = ModificationParam(raw=value)
    for key, val in _KV_RE.findall(value):
        key_lower = key.upper()
        if key_lower == "NT":
            m.nt = val.strip()
        elif key_lower == "AC":
            m.ac = val.strip()
        elif key_lower == "TA":
            m.ta = val.strip()
        elif key_lower == "PP":
            m.pp = val.strip()
        elif key_lower == "MT":
            m.mt = val.strip()
    return m


def parse_instrument(value: str) -> InstrumentParam:
    """Parse an instrument string like AC=MS:1001911;NT=Q Exactive HF."""
    inst = InstrumentParam(raw=value)
    for key, val in _KV_RE.findall(value):
        key_upper = key.upper()
        if key_upper == "AC":
            inst.ac = val.strip()
        elif key_upper == "NT":
            inst.nt = val.strip()
    return inst


def parse_template_value(value: str) -> TemplateParam:
    """Parse a template declaration (NT=ms-proteomics;VV=v1.1.0 or free text)."""
    t = TemplateParam(raw=value)
    kvs = dict(_KV_RE.findall(value))
    if kvs:
        t.nt = kvs.get("NT", "").strip()
        t.vv = kvs.get("VV", "").strip()
    else:
        # Free text: "ms-proteomics v1.1.0"
        parts = value.strip().split()
        if parts:
            t.nt = parts[0]
        if len(parts) > 1:
            t.vv = parts[1]
    return t


# ---------------------------------------------------------------------------
# Column classification
# ---------------------------------------------------------------------------

def _classify_column(raw_name: str, index: int) -> ColumnInfo:
    stripped = raw_name.strip()
    lower = stripped.lower()
    if lower in _ANCHOR_COLUMNS:
        return ColumnInfo(raw_name=stripped, col_type="anchor", inner_name=lower, index=index)
    for col_type, pattern in _COL_PATTERNS.items():
        m = pattern.match(stripped)
        if m:
            return ColumnInfo(raw_name=stripped, col_type=col_type, inner_name=m.group(1).strip(), index=index)
    return ColumnInfo(raw_name=stripped, col_type="other", inner_name=lower, index=index)


# ---------------------------------------------------------------------------
# Auto-detect templates from content
# ---------------------------------------------------------------------------

def _auto_detect_templates(sdrf: SDRFFile) -> list[str]:
    """Heuristic template detection matching sdrf-validate SKILL.md rules."""
    templates: list[str] = []
    col_names_lower = {c.raw_name.lower() for c in sdrf.columns}

    # Technology type
    tech_values = set()
    for i, col in enumerate(sdrf.columns):
        if col.inner_name.lower() == "technology type":
            key = sdrf.key_for_column(i)
            tech_values = {v.lower() for v in sdrf.unique_values(key)}
    if "proteomic profiling by mass spectrometry" in tech_values:
        templates.append("ms-proteomics")
    if "protein expression profiling by aptamer array" in tech_values:
        templates.append("somascan")
    if "protein expression profiling by antibody array" in tech_values:
        templates.append("olink")

    # Organism
    organism_values = set()
    for i, col in enumerate(sdrf.columns):
        if col.col_type == "characteristics" and col.inner_name.lower() == "organism":
            key = sdrf.key_for_column(i)
            organism_values = {v.lower() for v in sdrf.unique_values(key)}
    if any("homo sapiens" in v for v in organism_values):
        templates.append("human")
    if any(org in v for v in organism_values for org in ("mus musculus", "rattus", "danio")):
        templates.append("vertebrates")
    if any(org in v for v in organism_values for org in ("drosophila", "caenorhabditis")):
        templates.append("invertebrates")
    if any(org in v for v in organism_values for org in ("arabidopsis", "oryza")):
        templates.append("plants")

    # Specific columns
    if "characteristics[cell line]" in col_names_lower:
        templates.append("cell-lines")
    if "characteristics[mhc protein complex]" in col_names_lower:
        templates.append("immunopeptidomics")
    if "comment[cross-linker]" in col_names_lower:
        templates.append("crosslinking")
    if "characteristics[single cell isolation protocol]" in col_names_lower:
        templates.append("single-cell")
    if "characteristics[environmental sample type]" in col_names_lower:
        templates.append("metaproteomics")
    if any(c in col_names_lower for c in ("characteristics[tumor grading]", "characteristics[tumor stage]")):
        templates.append("oncology-metadata")

    return templates


# ---------------------------------------------------------------------------
# Main parsing entry point
# ---------------------------------------------------------------------------

def parse_sdrf(source: str | Path) -> SDRFFile:
    """Parse an SDRF TSV file.

    Args:
        source: Path to a .sdrf.tsv file, or the raw TSV content as a string.

    Returns:
        An SDRFFile with parsed columns and rows.
    """
    path_obj: Path | None = None
    source_str = str(source)
    if "\t" not in source_str and "\n" not in source_str and source_str.strip():
        path_obj = Path(source_str)
        if path_obj.is_file():
            text = path_obj.read_text(encoding="utf-8-sig")  # handles BOM
        elif path_obj.suffix in (".tsv", ".txt", ".sdrf") or "/" in source_str or "\\" in source_str:
            raise FileNotFoundError(f"SDRF file not found: {source_str}")
        else:
            text = source_str
    else:
        text = source_str

    # Normalise line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    # Remove empty trailing lines
    while lines and not lines[-1].strip():
        lines.pop()

    if not lines:
        return SDRFFile(path=str(path_obj) if path_obj else None,
                        columns=[], rows=[], raw_headers=[], col_keys=[],
                        warnings=[])

    reader = csv.reader(lines, delimiter="\t")
    raw_headers = next(reader)
    columns = [_classify_column(h, i) for i, h in enumerate(raw_headers)]

    # Disambiguate duplicate column names (e.g. multiple comment[modification parameters])
    seen: dict[str, int] = {}
    col_keys: list[str] = []
    for col in columns:
        name = col.raw_name
        if name in seen:
            seen[name] += 1
            key = f"{name}__{seen[name]}"
        else:
            seen[name] = 1
            key = name
        col_keys.append(key)

    rows: list[dict[str, str]] = []
    warnings: list[str] = []
    for row_idx, row_values in enumerate(reader):
        if not any(v.strip() for v in row_values):
            continue  # skip blank rows
        if len(row_values) > len(col_keys):
            warnings.append(
                f"Row {row_idx + 1} has {len(row_values)} columns "
                f"(header has {len(col_keys)}); extra columns truncated"
            )
        # Pad short rows with empty strings; truncate wide rows to header width
        padded = row_values[:len(col_keys)] + [""] * max(0, len(col_keys) - len(row_values))
        rows.append({col_keys[i]: padded[i] for i in range(len(col_keys))})

    return SDRFFile(
        path=str(path_obj) if path_obj else None,
        columns=columns,
        rows=rows,
        raw_headers=raw_headers,
        col_keys=col_keys,
        warnings=warnings,
    )

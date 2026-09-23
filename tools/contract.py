"""The column contract of a template union: what an SDRF built for these templates must
contain, in order, with the value form and reserved-word permissions of every column.

Reads the merged template view from sdrf-pipelines' own registry (so the contract is
exactly what the validator enforces) and joins per-term permissions from TERMS.tsv.
No network."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from tools.column_ontology_map import resolve_terms_tsv

SECTION_ORDER = ["source name", "characteristics", "special", "comment", "factor value"]
TOLERANCE_COLUMNS = {"comment[precursor mass tolerance]", "comment[fragment mass tolerance]"}
INTEGER_COLUMNS = {"comment[fraction identifier]", "comment[technical replicate]",
                   "characteristics[biological replicate]"}
FREE_TEXT_COLUMNS = {"source name", "assay name", "comment[data file]", "comment[sdrf version]",
                     "comment[sdrf template]", "comment[sdrf annotation tool]",
                     "comment[sdrf validation hash]", "comment[acquisition date]",
                     "comment[sample preparation batch]", "comment[lc batch]"}
# comment columns whose values are ontology terms and therefore take NT=;AC=
TERM_COMMENT_COLUMNS = {"comment[instrument]", "comment[cleavage agent details]", "comment[label]",
                        "comment[proteomics data acquisition method]", "comment[dissociation method]",
                        "comment[fractionation method]", "comment[reduction reagent]",
                        "comment[alkylation reagent]", "comment[ms2 mass analyzer]",
                        "comment[modification parameters]"}


@dataclass
class ColumnSpec:
    name: str
    section: str
    requirement: str
    multiple: bool
    ontology: str | None
    allow_not_available: bool
    allow_not_applicable: bool
    value_form: str
    ontologies: str = ""  # TERMS.tsv 'values': which ontologies to search, or a fixed list


@dataclass
class Contract:
    templates: list[str]
    versions: dict[str, str]
    columns: list[ColumnSpec]
    rules: list[str] = field(default_factory=list)
    technology_type: str | None = None  # fixed by the technology template when it is MS; else the model's call


MS_TECHNOLOGY_TYPE = "proteomic profiling by mass spectrometry"  # TERMS.tsv: fixed value for MS templates


def _extends_chain(registry, name: str) -> list[str]:
    """The template and every ancestor it extends, e.g. dia-acquisition -> ms-proteomics -> ..."""
    chain, seen = [], set()
    while name and name not in seen:
        seen.add(name)
        chain.append(name)
        schema = registry.get_schema(name)
        parent = getattr(schema, "extends", None) if schema else None
        if isinstance(parent, list):
            parent = parent[0] if parent else None
        name = str(parent).split("@")[0].strip() if parent else ""
    return chain


def _truthy(s: str | None) -> bool:
    return (s or "").strip().lower() in ("true", "1", "yes")


def load_terms(terms_path: str | Path | None = None) -> dict[str, dict[str, object]]:
    """TERMS.tsv keyed by lower-case inner term name."""
    path = resolve_terms_tsv(terms_path)
    if path is None:
        return {}
    out: dict[str, dict[str, object]] = {}
    with path.open(newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            name = (row.get("term") or row.get("name") or "").strip().lower()
            if not name:
                continue
            out[name] = {
                "values": (row.get("values") or "").strip(),
                "allow_not_available": _truthy(row.get("allow_not_available")),
                "allow_not_applicable": _truthy(row.get("allow_not_applicable")),
            }
    return out


def inner_name(column: str) -> str:
    """'comment[fraction identifier]' -> 'fraction identifier'; 'source name' -> 'source name'."""
    c = column.strip()
    if "[" in c and c.endswith("]"):
        return c[c.index("[") + 1:-1].strip().lower()
    return c.lower()


def _section_of(column: str) -> str:
    c = column.lower()
    if c == "source name":
        return "source name"
    if c.startswith("characteristics["):
        return "characteristics"
    if c.startswith("comment["):
        return "comment"
    if c.startswith("factor value["):
        return "factor value"
    return "special"


def value_form(column: str, section: str) -> str:
    if column in TOLERANCE_COLUMNS:
        return "<number> ppm|Da"
    if column in INTEGER_COLUMNS:
        return "integer"
    if column in FREE_TEXT_COLUMNS:
        return "free text"
    if section in ("characteristics", "factor value"):
        return "bare value"
    if column in TERM_COMMENT_COLUMNS:
        return "NT=<name>;AC=<accession>"
    return "free text"


def template_contract(templates: list[str], terms_path: str | Path | None = None) -> Contract:
    from sdrf_pipelines.sdrf.schemas.registry import SchemaRegistry

    registry = SchemaRegistry()
    known = sorted(registry.get_schema_names())
    unknown = [t for t in templates if t not in known]
    if unknown:
        raise ValueError(f"unknown template(s) {unknown}; known templates: {', '.join(known)}")
    ordered, sections = registry.compile_columns_from_schemas(list(templates))
    terms = load_terms(terms_path)
    defs = {name: col for sec in sections.values() for name, col in sec.items()}
    columns: list[ColumnSpec] = []
    for name in ordered:
        d = defs[name].model_dump()
        section = _section_of(name)
        term = terms.get(inner_name(name), {})
        req = d["requirement"]
        req = req.value if hasattr(req, "value") else str(req)
        columns.append(ColumnSpec(
            name=name, section=section, requirement=req,
            multiple=(d.get("cardinality") == "multiple"),
            ontology=d.get("ontology_accession"),
            allow_not_available=bool(d.get("allow_not_available")) or bool(term.get("allow_not_available")),
            allow_not_applicable=bool(d.get("allow_not_applicable")) or bool(term.get("allow_not_applicable")),
            value_form=value_form(name, section),
            ontologies=str(term.get("values") or "")[:70],
        ))
    columns.sort(key=lambda c: SECTION_ORDER.index(c.section))  # stable: keeps registry order within a section
    versions = {t: str(registry.get_schema(t).version) for t in templates}
    ms = any("ms-proteomics" in _extends_chain(registry, t) for t in templates)
    rules = [
        "source name first; characteristics[...]; assay name, technology type; comment[...]; factor value[...] last.",
        "(source name, assay name, comment[label]) must be unique per row.",
        "Repeated column names are legal for 'multiple' columns; never suffix them.",
        "Sample properties (characteristics) carry the bare value; ontology-backed comments take NT=<name>;AC=<accession>.",
        "'not available' / 'not applicable' only where the column permits it (flags below).",
    ]
    return Contract(templates=list(templates), versions=versions, columns=columns, rules=rules,
                    technology_type=MS_TECHNOLOGY_TYPE if ms else None)


def render_text(c: Contract) -> str:
    lines = [f"CONTRACT for templates: {', '.join(f'{t} v{c.versions[t]}' for t in c.templates)}", ""]
    lines += ["Rules:"] + [f"  - {r}" for r in c.rules] + [""]
    lines.append("Columns, in order  [req/rec/opt] [multiple] value form | reserved words allowed:")
    for col in c.columns:
        flags = []
        if col.allow_not_available:
            flags.append("not available")
        if col.allow_not_applicable:
            flags.append("not applicable")
        mult = " [multiple]" if col.multiple else ""
        onto = f"  <- {col.ontologies}" if col.ontologies and col.section in ("characteristics", "comment") else ""
        lines.append(f"  {col.name}  [{col.requirement[:3]}]{mult}  {col.value_form} | {', '.join(flags) or '-'}{onto}")
    lines.append("")
    lines.append("factor value[...] last: add one column per experimental variable you set, after every comment column.")
    return "\n".join(lines)


def render_json(c: Contract) -> str:
    return json.dumps(asdict(c), indent=1)

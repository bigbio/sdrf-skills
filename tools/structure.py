"""Structural invariants an SDRF must satisfy whatever the experiment is.

These are the rules a file can be checked against without knowing any biology: one acquisition
method per file, a template declaration that is constant and agrees with the data, multi-valued
annotations carried as repeated columns, factor columns last, and reserved words only where
TERMS.tsv permits them. Each is decidable from the file alone (the last one against the bundled
spec), so a model can be told to run this before it finishes rather than be trusted to remember.

Motivated by bigbio/sdrf-skills#85, where a weak model produced files that mixed DDA and DIA rows,
varied the template declaration row by row, and packed two templates into one cell. Only the last
of those was caught by parse_sdrf; the other two validated cleanly.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from tools.column_ontology_map import resolve_terms_tsv
from tools.sdrf_parser import SDRFFile, parse_sdrf, parse_template_value

ACQUISITION_COLUMN = "comment[proteomics data acquisition method]"
TEMPLATE_COLUMN = "comment[sdrf template]"

#: PRIDE accessions for data-independent acquisition and its descendants.
DIA_ACCESSIONS = {"PRIDE:0000450", "PRIDE:0000650", "PRIDE:0000447"}
#: PRIDE accession for data-dependent acquisition.
DDA_ACCESSIONS = {"PRIDE:0000627"}
#: Templates that constrain the acquisition method of every row.
DIA_TEMPLATES = {"dia-acquisition"}
#: Order matters: it lines up with TERMS.tsv's allow_not_available / allow_not_applicable.
RESERVED_WORDS = ("not available", "not applicable")


@dataclass(frozen=True)
class Finding:
    """One violated invariant. `rule` is stable, so callers can filter or suppress by name."""

    rule: str
    message: str
    column: str | None = None

    def __str__(self) -> str:
        where = f" [{self.column}]" if self.column else ""
        return f"{self.rule}{where}: {self.message}"


def acquisition_family(value: str) -> str | None:
    """'dia', 'dda', or None when the value names neither.

    Reads the accession first, since it is unambiguous, and falls back to the label. Matching on
    'independent' before 'dependent' matters: the former contains the latter as a substring.
    """
    text = value.strip()
    if not text:
        return None
    upper = text.upper()
    if any(ac in upper for ac in DIA_ACCESSIONS):
        return "dia"
    if any(ac in upper for ac in DDA_ACCESSIONS):
        return "dda"
    lowered = text.lower()
    if "independent" in lowered:
        return "dia"
    if "dependent" in lowered:
        return "dda"
    return None


def _column_values(sdrf: SDRFFile, raw_name: str) -> list[tuple[str, list[str]]]:
    """(column key, per-row values) for every column carrying this header."""
    return [(key, [row.get(key, "") for row in sdrf.rows]) for key in sdrf.all_keys_for_name(raw_name)]


def check_single_acquisition_method(sdrf: SDRFFile) -> list[Finding]:
    """DDA and DIA runs belong in separate files: they are different experiments."""
    findings = []
    for _key, values in _column_values(sdrf, ACQUISITION_COLUMN):
        families = {f for f in (acquisition_family(v) for v in values) if f}
        if len(families) > 1:
            findings.append(
                Finding(
                    "mixed-acquisition-methods",
                    f"file mixes {' and '.join(sorted(families)).upper()} runs; "
                    "annotate each acquisition method in its own SDRF",
                    ACQUISITION_COLUMN,
                )
            )
    return findings


def check_template_declaration_constant(sdrf: SDRFFile) -> list[Finding]:
    """The template set describes the file, so it cannot differ between rows."""
    findings = []
    for key, values in _column_values(sdrf, TEMPLATE_COLUMN):
        distinct = {v.strip() for v in values if v.strip()}
        if len(distinct) > 1:
            findings.append(
                Finding(
                    "template-varies-by-row",
                    f"declares {len(distinct)} different template values "
                    f"({', '.join(sorted(distinct))}); the declaration describes the file, not the row",
                    key,
                )
            )
    return findings


def check_one_template_per_cell(sdrf: SDRFFile) -> list[Finding]:
    """Several templates are several repeated columns, never one ';'-joined cell."""
    findings = []
    for key, values in _column_values(sdrf, TEMPLATE_COLUMN):
        for value in {v.strip() for v in values if v.strip()}:
            if value.upper().count("NT=") > 1:
                findings.append(
                    Finding(
                        "multiple-templates-in-one-cell",
                        f"{value!r} packs several templates into one cell; repeat the "
                        f"{TEMPLATE_COLUMN} column once per template instead",
                        key,
                    )
                )
    return findings


def check_template_matches_acquisition(sdrf: SDRFFile) -> list[Finding]:
    """A declared dia-acquisition template and a DDA value contradict each other."""
    declared = {t.nt.strip().lower() for t in sdrf.detected_templates() if t.nt}
    # detected_templates() keeps only the last NT= of a packed cell, so read the raw values too.
    for _key, values in _column_values(sdrf, TEMPLATE_COLUMN):
        for value in values:
            for part in value.split(";"):
                if part.strip().upper().startswith("NT="):
                    declared.add(parse_template_value(part.strip()).nt.strip().lower())
    if not declared & DIA_TEMPLATES:
        return []
    findings = []
    for _key, values in _column_values(sdrf, ACQUISITION_COLUMN):
        offending = sorted({v.strip() for v in values if acquisition_family(v) == "dda"})
        if offending:
            findings.append(
                Finding(
                    "template-contradicts-acquisition",
                    f"declares a DIA template but annotates {', '.join(offending)}; "
                    "the declared template and the acquisition method must agree",
                    ACQUISITION_COLUMN,
                )
            )
    return findings


def check_factor_values_last(sdrf: SDRFFile) -> list[Finding]:
    """factor value[...] columns close the file, after everything they are a factor of."""
    names = sdrf.column_names()
    factor_positions = [i for i, n in enumerate(names) if n.lower().startswith("factor value[")]
    if not factor_positions:
        return []
    trailing = set(range(len(names) - len(factor_positions), len(names)))
    if set(factor_positions) == trailing:
        return []
    after = [names[i] for i in range(min(factor_positions) + 1, len(names)) if i not in factor_positions]
    return [
        Finding(
            "factor-values-not-last",
            f"{len(after)} column(s) follow a factor value column ({', '.join(after[:3])}"
            f"{'...' if len(after) > 3 else ''}); factor value columns come last",
        )
    ]


def reserved_word_rules(spec_path: str | Path | None = None) -> dict[str, tuple[bool, bool]]:
    """term -> (may say 'not available', may say 'not applicable'), from TERMS.tsv.

    Empty when the spec submodule is absent, which makes the check silent rather than wrong.
    TERMS.tsv is CRLF-terminated with a blank row, so read it with newline='' and strip every
    field: 'false\\r' is truthy compared naively.
    """
    path = resolve_terms_tsv(spec_path)
    if path is None:
        return {}
    rules: dict[str, tuple[bool, bool]] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            term = (row.get("term") or "").strip()
            if not term:
                continue
            rules[term.lower()] = (
                (row.get("allow_not_available") or "").strip().lower() == "true",
                (row.get("allow_not_applicable") or "").strip().lower() == "true",
            )
    return rules


def check_reserved_words_allowed(sdrf: SDRFFile, spec_path: str | Path | None = None) -> list[Finding]:
    """'not available' / 'not applicable' only where TERMS.tsv permits them.

    Where a column forbids both, the annotation is to omit the column, not to fill it with a
    reserved word: characteristics[cell line] on a tissue experiment is the common case.
    """
    rules = reserved_word_rules(spec_path)
    if not rules:
        return []
    findings = []
    for index, column in enumerate(sdrf.columns):
        allowed = rules.get((column.inner_name or column.raw_name).strip().lower())
        if allowed is None:
            continue
        permitted = {word for word, ok in zip(RESERVED_WORDS, allowed) if ok}
        used = {v.strip().lower() for v in sdrf.unique_values(sdrf.key_for_column(index))}
        for word in sorted(used & set(RESERVED_WORDS) - permitted):
            findings.append(
                Finding(
                    "reserved-word-not-allowed",
                    f"{word!r} is not an allowed value for this column; omit the column instead",
                    column.raw_name,
                )
            )
    return findings


CHECKS = (
    check_single_acquisition_method,
    check_template_declaration_constant,
    check_one_template_per_cell,
    check_template_matches_acquisition,
    check_factor_values_last,
    check_reserved_words_allowed,
)


def check_structure(source: str | Path | SDRFFile) -> list[Finding]:
    """Run every structural check. An empty list means the file satisfies all of them."""
    sdrf = source if isinstance(source, SDRFFile) else parse_sdrf(source)
    return [finding for check in CHECKS for finding in check(sdrf)]

"""Structural invariants an SDRF must satisfy whatever the experiment is.

These are the rules a file can be checked against without knowing any biology: one acquisition
method per file, a template declaration that is constant and agrees with the data, multi-valued
annotations carried as repeated columns, factor columns last, reserved words only where TERMS.tsv
permits them, sample properties written bare, and a row coordinate that identifies each
measurement exactly once. Each is decidable
from the file alone (reserved words against the bundled spec), so a model can be told to run this
before it finishes rather than be trusted to remember.

Motivated by bigbio/sdrf-skills#85, where a weak model produced files that mixed DDA and DIA rows,
varied the template declaration row by row, and packed two templates into one cell. Only the last
of those was caught by parse_sdrf; the other two validated cleanly.
"""

from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
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
SOURCE_COLUMN = "source name"
REPLICATE_COLUMN = "comment[technical replicate]"
BIO_REPLICATE_COLUMN = "characteristics[biological replicate]"
FRACTION_COLUMN = "comment[fraction identifier]"
DATA_FILE_COLUMN = "comment[data file]"
#: NT=/AC= key-value form. Belongs to comment[...]; sample properties are bare.
NT_AC_RE = re.compile(r"\b(NT|AC)=", re.I)


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


def _row_value(sdrf: SDRFFile, row: dict, raw_name: str, default: str = "") -> str:
    keys = sdrf.all_keys_for_name(raw_name)
    return row.get(keys[0], default).strip() if keys else default


def check_technical_replicate_indices(sdrf: SDRFFile) -> list[Finding]:
    """Within one sample, technical replicates are numbered 1..n with no gaps.

    A sample whose only row says 'technical replicate 3', or that jumps 1,2,4, is using the column
    to tell rows apart rather than to count re-injections of the same material. The common form is
    a labelled experiment where the channels of one run get replicate 1..n: those rows are
    different samples measured together, not the same sample measured repeatedly.
    """
    if not sdrf.all_keys_for_name(REPLICATE_COLUMN) or not sdrf.all_keys_for_name(SOURCE_COLUMN):
        return []
    by_source: dict[str, list[str]] = defaultdict(list)
    for row in sdrf.rows:
        by_source[_row_value(sdrf, row, SOURCE_COLUMN)].append(_row_value(sdrf, row, REPLICATE_COLUMN))
    offenders = []
    for source, values in by_source.items():
        numbers = sorted({int(v) for v in values if v.isdigit()})
        if numbers and numbers != list(range(1, len(numbers) + 1)):
            offenders.append((source, numbers))
    if not offenders:
        return []
    shown = "; ".join(f"{s!r} has {n}" for s, n in offenders[:3])
    return [
        Finding(
            "technical-replicate-not-contiguous",
            f"{len(offenders)} sample(s) number technical replicates with a gap or not from 1 "
            f"({shown}{'; ...' if len(offenders) > 3 else ''}); within one sample they run 1..n",
            REPLICATE_COLUMN,
        )
    ]


def check_technical_replicates_have_distinct_files(sdrf: SDRFFile) -> list[Finding]:
    """A sample with n technical replicates was acquired into n distinct files.

    Re-injecting a sample writes another raw file, so replicate indices and files go together.
    When one file carries several replicate numbers for the same sample, the column is being used
    to separate rows that share a run -- the labelled channels of a plex, typically, which are
    different samples rather than repeated measurements of one.
    """
    needed = (REPLICATE_COLUMN, SOURCE_COLUMN, DATA_FILE_COLUMN)
    if any(not sdrf.all_keys_for_name(name) for name in needed):
        return []
    by_source: dict[str, tuple[set[str], set[str]]] = defaultdict(lambda: (set(), set()))
    for row in sdrf.rows:
        files, replicates = by_source[_row_value(sdrf, row, SOURCE_COLUMN)]
        files.add(_row_value(sdrf, row, DATA_FILE_COLUMN))
        replicates.add(_row_value(sdrf, row, REPLICATE_COLUMN))
    offenders = [(s, len(r), len(f)) for s, (f, r) in by_source.items() if len(r) > len(f)]
    if not offenders:
        return []
    shown = "; ".join(f"{s!r}: {r} replicates across {f} file(s)" for s, r, f in offenders[:3])
    return [
        Finding(
            "technical-replicates-share-a-file",
            f"{len(offenders)} sample(s) claim more technical replicates than they have data files "
            f"({shown}{'; ...' if len(offenders) > 3 else ''}); rows sharing one run are usually "
            "channels of a plex, which are separate samples",
            REPLICATE_COLUMN,
        )
    ]


def check_row_coordinate_unique(sdrf: SDRFFile) -> list[Finding]:
    """(source name, biological replicate, technical replicate, fraction identifier) is unique.

    Two rows sharing all four describe the same measurement of the same material twice, so one of
    the four is carrying the wrong value. Missing columns default to '1', which is what a file that
    omits them means.
    """
    if not sdrf.all_keys_for_name(SOURCE_COLUMN):
        return []
    seen: Counter[tuple[str, ...]] = Counter()
    for row in sdrf.rows:
        seen[(
            _row_value(sdrf, row, SOURCE_COLUMN),
            _row_value(sdrf, row, BIO_REPLICATE_COLUMN, "1") or "1",
            _row_value(sdrf, row, REPLICATE_COLUMN, "1") or "1",
            _row_value(sdrf, row, FRACTION_COLUMN, "1") or "1",
        )] += 1
    collisions = {k: n for k, n in seen.items() if n > 1}
    if not collisions:
        return []
    shown = "; ".join(f"{k[0]!r} (bio {k[1]}, tech {k[2]}, fraction {k[3]}) x{n}"
                      for k, n in list(collisions.items())[:2])
    return [
        Finding(
            "duplicate-row-coordinate",
            f"{sum(collisions.values()) - len(collisions)} row(s) repeat a coordinate that must be "
            f"unique: {shown}{'; ...' if len(collisions) > 2 else ''}",
            SOURCE_COLUMN,
        )
    ]


def check_characteristics_are_bare(sdrf: SDRFFile) -> list[Finding]:
    """characteristics[...] carries a bare value, never an NT=/AC= pair.

    A sample property is written as the ontology label on its own ('HeLa', 'colon'), or as the
    identifier itself where the column is an accession ('CVCL_0030' in
    characteristics[cellosaurus accession]). The NT=<label>;AC=<accession> form belongs to
    comment[...] columns. Structured sample properties that legitimately carry keys -- SN= for
    pooled sample, CT=/QY= for spiked compound -- use other keys and are untouched by this rule.
    """
    findings = []
    for index, column in enumerate(sdrf.columns):
        if not column.raw_name.strip().lower().startswith("characteristics["):
            continue
        offenders = sorted(
            v.strip() for v in sdrf.unique_values(sdrf.key_for_column(index))
            if NT_AC_RE.search(v)
        )
        if offenders:
            shown = ", ".join(repr(o[:48]) for o in offenders[:2])
            findings.append(
                Finding(
                    "characteristics-uses-nt-ac",
                    f"{len(offenders)} value(s) written as an NT=/AC= pair ({shown}"
                    f"{', ...' if len(offenders) > 2 else ''}); a sample property is the bare "
                    "label, or the accession alone where the column is an accession",
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
    check_technical_replicate_indices,
    check_technical_replicates_have_distinct_files,
    check_row_coordinate_unique,
    check_characteristics_are_bare,
)


def check_structure(source: str | Path | SDRFFile) -> list[Finding]:
    """Run every structural check. An empty list means the file satisfies all of them."""
    sdrf = source if isinstance(source, SDRFFile) else parse_sdrf(source)
    return [finding for check in CHECKS for finding in check(sdrf)]

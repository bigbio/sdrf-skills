"""Ontology hallucination detector for SDRF files.

Programmatically verifies that ontology accessions in an SDRF file are real
and match their labels. Catches fabricated accessions, label-accession
mismatches, wrong ontology sources, and the well-known UNIMOD swap errors.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from tools.column_ontology_map import (
    COLUMN_ONTOLOGY_MAP,
    UNIMOD_KNOWN,
    UNIMOD_SWAPS,
    try_load_terms_tsv,
)
from tools.ols_client import OLSClient
from tools.sdrf_parser import (
    SDRFFile,
    parse_modification,
    parse_sdrf,
)


# ---------------------------------------------------------------------------
# Report dataclasses
# ---------------------------------------------------------------------------

@dataclass
class VerifiedTerm:
    """A term that passed all checks."""
    column: str
    accession: str
    label: str
    ontology: str


@dataclass
class HallucinatedTerm:
    """An accession that does not exist in OLS."""
    column: str
    accession: str
    label: str
    rows: list[int]
    message: str = ""


@dataclass
class MismatchedTerm:
    """An accession that exists but has the wrong label."""
    column: str
    accession: str
    expected_label: str
    actual_label: str
    rows: list[int]
    message: str = ""


@dataclass
class WrongOntologyTerm:
    """A term from the wrong ontology for its column."""
    column: str
    accession: str
    label: str
    expected_ontologies: list[str]
    actual_ontology: str
    rows: list[int]


@dataclass
class UnimodSwap:
    """A known UNIMOD accession swap error."""
    column: str
    wrong_accession: str
    wrong_name_for_accession: str
    correct_accession: str
    correct_name: str
    rows: list[int]


@dataclass
class HallucinationReport:
    """Full report from hallucination detection."""
    file_path: str | None
    total_terms_checked: int = 0
    verified: list[VerifiedTerm] = field(default_factory=list)
    hallucinated: list[HallucinatedTerm] = field(default_factory=list)
    mismatched: list[MismatchedTerm] = field(default_factory=list)
    wrong_ontology: list[WrongOntologyTerm] = field(default_factory=list)
    unimod_swaps: list[UnimodSwap] = field(default_factory=list)

    @property
    def total_issues(self) -> int:
        return (len(self.hallucinated) + len(self.mismatched)
                + len(self.wrong_ontology) + len(self.unimod_swaps))

    @property
    def is_clean(self) -> bool:
        return self.total_issues == 0

    def summary(self) -> str:
        lines = [
            f"Hallucination Report: {self.file_path or '<inline>'}",
            f"  Terms checked:     {self.total_terms_checked}",
            f"  Verified:          {len(self.verified)}",
            f"  Hallucinated:      {len(self.hallucinated)}",
            f"  Label mismatches:  {len(self.mismatched)}",
            f"  Wrong ontology:    {len(self.wrong_ontology)}",
            f"  UNIMOD swaps:      {len(self.unimod_swaps)}",
            f"  Status:            {'CLEAN' if self.is_clean else 'ISSUES FOUND'}",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Accession extraction
# ---------------------------------------------------------------------------

_ACCESSION_RE = re.compile(
    r"\b([A-Z]+(?:Taxon)?):(\d{1,10})\b"
)


def _extract_accession_label_pairs(value: str, column_inner: str) -> list[tuple[str, str]]:
    """Extract (accession, label) pairs from a cell value.

    For modification parameters, parse the NT/AC structure.
    For instrument/cleavage agent, parse AC/NT structure.
    For other columns, the value IS the label and we look for accessions elsewhere.
    """
    pairs: list[tuple[str, str]] = []

    if column_inner in ("modification parameters",):
        mod = parse_modification(value)
        if mod.ac:
            pairs.append((mod.ac, mod.nt))
        return pairs

    if column_inner in ("instrument", "cleavage agent details"):
        from tools.sdrf_parser import parse_instrument
        inst = parse_instrument(value)
        if inst.ac:
            pairs.append((inst.ac, inst.nt))
        return pairs

    # For ontology-controlled columns, the value is the label
    # We don't have the accession in the cell value itself for most columns
    # (organism, disease, tissue, cell type are just labels)
    return pairs


# ---------------------------------------------------------------------------
# UNIMOD-specific checks
# ---------------------------------------------------------------------------

def _check_unimod_swap(accession: str, name: str) -> UnimodSwap | None:
    """Check if this is a known UNIMOD swap error."""
    key = (accession.upper(), name.strip())
    swap = UNIMOD_SWAPS.get(key)
    if swap:
        return UnimodSwap(
            column="",  # filled by caller
            wrong_accession=accession,
            wrong_name_for_accession=name,
            correct_accession=swap[0],
            correct_name=swap[1],
            rows=[],  # filled by caller
        )

    # Also check: accession is known and name doesn't match
    known_name = UNIMOD_KNOWN.get(accession.upper())
    if known_name and known_name.lower() != name.strip().lower():
        return UnimodSwap(
            column="",
            wrong_accession=accession,
            wrong_name_for_accession=name,
            correct_accession=accession,
            correct_name=known_name,
            rows=[],
        )
    return None


def _check_modification_cell(
    value: str, column_name: str, row_indices: list[int]
) -> tuple[list[VerifiedTerm], list[UnimodSwap], list[str]]:
    """Check a modification parameter value for UNIMOD issues.

    Returns (verified_terms, swaps, warnings).
    """
    mod = parse_modification(value)
    verified: list[VerifiedTerm] = []
    swaps: list[UnimodSwap] = []
    warnings: list[str] = []

    if not mod.ac:
        return verified, swaps, warnings

    # Check MT= value
    if mod.mt and mod.mt not in ("Fixed", "Variable"):
        warnings.append(
            f"MT= should be 'Fixed' or 'Variable', got '{mod.mt}'"
        )

    # Check TA= vs PP=
    if mod.ta and len(mod.ta) > 1 and not mod.pp:
        # TA should be a single amino acid letter; multi-char suggests PP
        if mod.ta in ("Protein N-term", "Protein C-term", "Any N-term", "Any C-term"):
            warnings.append(
                f"TA='{mod.ta}' looks like a positional parameter; use PP= instead"
            )

    # UNIMOD swap check (offline, no API needed)
    swap = _check_unimod_swap(mod.ac, mod.nt)
    if swap:
        swap.column = column_name
        swap.rows = row_indices
        swaps.append(swap)
    elif mod.ac.upper().startswith("UNIMOD:"):
        known = UNIMOD_KNOWN.get(mod.ac.upper())
        if known and known.lower() == mod.nt.lower():
            verified.append(VerifiedTerm(
                column=column_name,
                accession=mod.ac,
                label=mod.nt,
                ontology="UNIMOD",
            ))

    return verified, swaps, warnings


# ---------------------------------------------------------------------------
# Main detection logic
# ---------------------------------------------------------------------------

def detect_hallucinations(
    source: str | Path,
    ols_client: OLSClient | None = None,
    verify_online: bool = True,
    spec_path: str | Path | None = None,
) -> HallucinationReport:
    """Detect ontology hallucinations in an SDRF file.

    Args:
        source: Path to SDRF file or raw TSV content.
        ols_client: OLS client instance (created if None and verify_online=True).
        verify_online: Whether to verify accessions against OLS API.
        spec_path: Path to TERMS.tsv for column-ontology mappings.

    Returns:
        HallucinationReport with all findings.
    """
    sdrf = parse_sdrf(source) if isinstance(source, (str, Path)) else source

    report = HallucinationReport(file_path=sdrf.path if isinstance(sdrf, SDRFFile) else None)

    # Load column->ontology mappings
    ont_map = COLUMN_ONTOLOGY_MAP.copy()
    if spec_path:
        loaded = try_load_terms_tsv(spec_path)
        if loaded:
            ont_map.update(loaded)

    if verify_online and ols_client is None:
        ols_client = OLSClient()

    # Process each column (use disambiguated col_keys for row access)
    for i, col in enumerate(sdrf.columns):
        inner = col.inner_name.lower()
        expected_onts = ont_map.get(inner, [])
        col_key = sdrf.key_for_column(i)

        if inner == "modification parameters":
            _check_modification_column(sdrf, col_key, report)
        elif inner in ("instrument", "cleavage agent details"):
            _check_structured_column(sdrf, col_key, inner, expected_onts,
                                     report, ols_client, verify_online)
        elif expected_onts:
            _check_ontology_column(sdrf, col_key, inner, expected_onts,
                                   report, ols_client, verify_online)

    return report


def _check_modification_column(
    sdrf: SDRFFile, col_name: str, report: HallucinationReport
) -> None:
    """Check all modification parameter values in a column."""
    # Group by unique value to avoid redundant checks
    value_rows: dict[str, list[int]] = {}
    for i, row in enumerate(sdrf.rows):
        val = row.get(col_name, "").strip()
        if val and val.lower() not in ("not available", "not applicable"):
            value_rows.setdefault(val, []).append(i + 1)  # 1-indexed

    for value, rows in value_rows.items():
        report.total_terms_checked += 1
        verified, swaps, warnings = _check_modification_cell(value, col_name, rows)
        report.verified.extend(verified)
        report.unimod_swaps.extend(swaps)


def _check_structured_column(
    sdrf: SDRFFile,
    col_name: str,
    inner_name: str,
    expected_onts: list[str],
    report: HallucinationReport,
    ols_client: OLSClient | None,
    verify_online: bool,
) -> None:
    """Check instrument or cleavage agent columns (AC=;NT= format)."""
    from tools.sdrf_parser import parse_instrument

    value_rows: dict[str, list[int]] = {}
    for i, row in enumerate(sdrf.rows):
        val = row.get(col_name, "").strip()
        if val and val.lower() not in ("not available", "not applicable"):
            value_rows.setdefault(val, []).append(i + 1)

    for value, rows in value_rows.items():
        inst = parse_instrument(value)
        if not inst.ac:
            continue

        report.total_terms_checked += 1

        if not verify_online or not ols_client:
            continue

        result = ols_client.verify_accession(inst.ac, inst.nt)
        if not result.exists:
            report.hallucinated.append(HallucinatedTerm(
                column=col_name,
                accession=inst.ac,
                label=inst.nt,
                rows=rows,
                message=result.message,
            ))
        elif not result.label_match:
            report.mismatched.append(MismatchedTerm(
                column=col_name,
                accession=inst.ac,
                expected_label=inst.nt,
                actual_label=result.resolved_term.label if result.resolved_term else "",
                rows=rows,
                message=result.message,
            ))
        else:
            report.verified.append(VerifiedTerm(
                column=col_name,
                accession=inst.ac,
                label=inst.nt,
                ontology=result.resolved_term.ontology_name if result.resolved_term else "",
            ))

        # Check ontology source
        if expected_onts and result.exists and result.resolved_term:
            prefix = inst.ac.split(":")[0].upper()
            if prefix not in [o.upper() for o in expected_onts]:
                report.wrong_ontology.append(WrongOntologyTerm(
                    column=col_name,
                    accession=inst.ac,
                    label=inst.nt,
                    expected_ontologies=expected_onts,
                    actual_ontology=prefix,
                    rows=rows,
                ))


def _check_ontology_column(
    sdrf: SDRFFile,
    col_name: str,
    inner_name: str,
    expected_onts: list[str],
    report: HallucinationReport,
    ols_client: OLSClient | None,
    verify_online: bool,
) -> None:
    """Check a standard ontology-controlled column (label-only values).

    These columns contain just labels (e.g. "Homo sapiens", "breast carcinoma"),
    not accession-structured values. We verify the label resolves to a real
    term in the expected ontology.
    """
    value_rows: dict[str, list[int]] = {}
    for i, row in enumerate(sdrf.rows):
        val = row.get(col_name, "").strip()
        if val and val.lower() not in ("not available", "not applicable", "normal"):
            value_rows.setdefault(val, []).append(i + 1)

    if not verify_online or not ols_client:
        return

    for value, rows in value_rows.items():
        report.total_terms_checked += 1

        # Search in expected ontologies
        found = False
        for ont in expected_onts:
            terms = ols_client.search_term(value, ontology_id=ont, rows=5)
            for term in terms:
                if term.label.lower() == value.lower():
                    report.verified.append(VerifiedTerm(
                        column=col_name,
                        accession=term.short_form,
                        label=value,
                        ontology=ont,
                    ))
                    found = True
                    break
            if found:
                break

        if not found:
            # Try broad search
            terms = ols_client.search_term(value, rows=5)
            for term in terms:
                if term.label.lower() == value.lower():
                    prefix = term.short_form.split(":")[0].upper() if ":" in term.short_form else ""
                    if prefix and prefix not in [o.upper() for o in expected_onts]:
                        report.wrong_ontology.append(WrongOntologyTerm(
                            column=col_name,
                            accession=term.short_form,
                            label=value,
                            expected_ontologies=expected_onts,
                            actual_ontology=prefix,
                            rows=rows,
                        ))
                    else:
                        report.verified.append(VerifiedTerm(
                            column=col_name,
                            accession=term.short_form,
                            label=value,
                            ontology=term.ontology_name,
                        ))
                    found = True
                    break

            # If still not found, it might be a hallucinated label
            if not found:
                report.hallucinated.append(HallucinatedTerm(
                    column=col_name,
                    accession="(label-only)",
                    label=value,
                    rows=rows,
                    message=f"Label '{value}' not found in {', '.join(expected_onts)}",
                ))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Detect ontology hallucinations in SDRF files"
    )
    parser.add_argument("sdrf_file", help="Path to .sdrf.tsv file")
    parser.add_argument(
        "--offline", action="store_true",
        help="Skip OLS API calls (only check UNIMOD swaps offline)"
    )
    parser.add_argument(
        "--spec", default=None,
        help="Path to TERMS.tsv (default: spec/sdrf-proteomics/TERMS.tsv)"
    )
    args = parser.parse_args(argv)

    report = detect_hallucinations(
        args.sdrf_file,
        verify_online=not args.offline,
        spec_path=args.spec,
    )
    print(report.summary())

    if report.unimod_swaps:
        print("\nUNIMOD Swaps Detected:")
        for swap in report.unimod_swaps:
            print(f"  Row(s) {swap.rows}: {swap.column}")
            print(f"    Wrong:   {swap.wrong_accession} labeled '{swap.wrong_name_for_accession}'")
            print(f"    Correct: {swap.correct_accession} = '{swap.correct_name}'")

    if report.hallucinated:
        print("\nHallucinated Terms:")
        for h in report.hallucinated:
            print(f"  Row(s) {h.rows}: {h.column}")
            print(f"    '{h.label}' ({h.accession}) — {h.message}")

    if report.mismatched:
        print("\nLabel Mismatches:")
        for m in report.mismatched:
            print(f"  Row(s) {m.rows}: {m.column}")
            print(f"    Expected: '{m.expected_label}', OLS says: '{m.actual_label}'")

    if not report.is_clean:
        sys.exit(1)


if __name__ == "__main__":
    main()

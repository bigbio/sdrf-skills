"""Programmatic auto-fixer for common SDRF errors.

Implements the 10 error patterns from sdrf-fix SKILL.md as deterministic
transformations. Does NOT fix ontology terms requiring human judgment.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tools.column_ontology_map import UNIMOD_KNOWN, UNIMOD_SWAPS, WRONG_RESERVED
from tools.sdrf_parser import SDRFFile, parse_sdrf, parse_modification


# ---------------------------------------------------------------------------
# Fix record
# ---------------------------------------------------------------------------

@dataclass
class FixRecord:
    """A single fix applied to the SDRF."""
    row: int | str   # 1-indexed row number or "all"
    column: str
    old_value: str
    new_value: str
    reason: str
    pattern: str     # which error pattern (e.g. "unimod_swap")


@dataclass
class FixReport:
    """Summary of all fixes applied."""
    file_path: str | None
    fixes: list[FixRecord] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)  # things not auto-fixed

    @property
    def total_fixes(self) -> int:
        return len(self.fixes)

    def by_pattern(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for f in self.fixes:
            counts[f.pattern] = counts.get(f.pattern, 0) + 1
        return counts

    def changelog(self) -> str:
        lines = ["Changes Applied:"]
        for fix in self.fixes:
            lines.append(f"  Row {fix.row}, {fix.column}:")
            lines.append(f"    OLD: {fix.old_value}")
            lines.append(f"    NEW: {fix.new_value}")
            lines.append(f"    FIX: {fix.reason}")
            lines.append("")

        counts = self.by_pattern()
        parts = [f"{v} {k}" for k, v in sorted(counts.items(), key=lambda x: -x[1])]
        lines.append(f"Summary: {self.total_fixes} fixes applied ({', '.join(parts)})")

        if self.skipped:
            lines.append(f"\nSkipped (manual review needed): {len(self.skipped)}")
            for s in self.skipped:
                lines.append(f"  - {s}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Pattern fixers
# ---------------------------------------------------------------------------

_AGE_RE = re.compile(r"^(\d+)\s*(years?|months?|weeks?|days?|yo|y\.?o\.?)$", re.I)
_AGE_UNIT_MAP = {
    "year": "Y", "years": "Y", "y": "Y", "yo": "Y", "y.o.": "Y",
    "month": "M", "months": "M", "m": "M",
    "week": "W", "weeks": "W", "w": "W",
    "day": "D", "days": "D", "d": "D",
}

_PYTHON_ARTIFACT_RE = re.compile(r"^\[?['\"](.+?)['\"]\]?$")

_DDA_DIA_FIXES = {
    "data-dependent acquisition": "Data-Dependent Acquisition",
    "data-independent acquisition": "Data-Independent Acquisition",
    "data-independent": "Data-Independent Acquisition",
    "data-dependent": "Data-Dependent Acquisition",
    "dda": "Data-Dependent Acquisition",
    "dia": "Data-Independent Acquisition",
}


def _fix_unimod_swap(mod_str: str) -> tuple[str | None, str]:
    """Fix UNIMOD accession swaps. Returns (fixed_str, reason) or (None, "")."""
    mod = parse_modification(mod_str)
    if not mod.ac:
        return None, ""

    key = (mod.ac.upper(), mod.nt.strip())
    swap = UNIMOD_SWAPS.get(key)
    if swap:
        correct_ac, correct_name = swap
        fixed = mod_str.replace(f"AC={mod.ac}", f"AC={correct_ac}")
        reason = (f"{mod.ac} is {UNIMOD_KNOWN.get(mod.ac.upper(), '?')}, not {mod.nt}. "
                  f"Correct accession is {correct_ac}")
        return fixed, reason

    # Check accession is known but name doesn't match
    known = UNIMOD_KNOWN.get(mod.ac.upper())
    if known and known.lower() != mod.nt.strip().lower():
        fixed = mod_str.replace(f"NT={mod.nt}", f"NT={known}")
        reason = f"{mod.ac} = {known}, not {mod.nt}"
        return fixed, reason

    # Fix TA= -> PP= for positional parameters
    if mod.ta in ("Protein N-term", "Protein C-term", "Any N-term", "Any C-term"):
        fixed = mod_str.replace(f"TA={mod.ta}", f"PP={mod.ta}")
        reason = f"Positional parameter should use PP=, not TA="
        return fixed, reason

    return None, ""


def _fix_case(value: str, inner_name: str) -> tuple[str | None, str]:
    """Fix case issues."""
    if inner_name == "sex":
        if value != value.lower() and value.lower() in ("male", "female", "not available", "not applicable"):
            return value.lower(), "Sex values must be lowercase"

    if inner_name == "organism":
        parts = value.split()
        if len(parts) >= 2:
            corrected = parts[0].capitalize() + " " + " ".join(p.lower() for p in parts[1:])
            if corrected != value:
                return corrected, "Organism follows binomial nomenclature (Genus species)"

    return None, ""


def _fix_reserved_words(value: str) -> tuple[str | None, str]:
    """Fix non-standard reserved words."""
    if value in WRONG_RESERVED:
        correct = WRONG_RESERVED[value]
        return correct, f"'{value}' is not a valid SDRF reserved word; use '{correct}'"
    return None, ""


def _fix_python_artifacts(value: str) -> tuple[str | None, str]:
    """Fix Python/programming artifacts."""
    if value in ("nan", "NaN", "None", "null"):
        return "not available", f"'{value}' is a programming artifact; use 'not available'"

    if value == '""' or value == "''":
        return "not available", "Empty quoted string; use 'not available'"

    m = _PYTHON_ARTIFACT_RE.match(value)
    if m and (value.startswith("[") or value.startswith("'")):
        clean = m.group(1)
        return clean, f"Stripped Python list/string artifact from '{value}'"

    return None, ""


def _fix_age_format(value: str) -> tuple[str | None, str]:
    """Fix age format to standard {number}{unit}."""
    if value.lower() in ("not available", "not applicable"):
        return None, ""

    # Already correct format
    if re.match(r"^\d+[YMWD]$", value):
        return None, ""

    # Bare number -> assume years
    if re.match(r"^\d+$", value):
        return f"{value}Y", f"Age '{value}' needs unit suffix; assumed years"

    m = _AGE_RE.match(value)
    if m:
        number = m.group(1)
        unit_text = m.group(2).lower().rstrip(".")
        unit = _AGE_UNIT_MAP.get(unit_text, "Y")
        return f"{number}{unit}", f"Age format standardized from '{value}'"

    return None, ""


def _fix_dda_dia(value: str) -> tuple[str | None, str]:
    """Fix DDA/DIA terminology."""
    fixed = _DDA_DIA_FIXES.get(value.lower())
    if fixed and fixed != value:
        return fixed, f"Standardized acquisition method to ontology term"
    return None, ""


def _fix_whitespace(value: str) -> tuple[str | None, str]:
    """Fix trailing/leading whitespace."""
    stripped = value.strip()
    if stripped != value:
        return stripped, "Trimmed whitespace"
    return None, ""


# ---------------------------------------------------------------------------
# Main fixer
# ---------------------------------------------------------------------------

def fix_sdrf(source: str | Path) -> tuple[str, FixReport]:
    """Apply deterministic fixes to an SDRF file.

    Args:
        source: Path to SDRF file or raw TSV content.

    Returns:
        Tuple of (fixed TSV content, FixReport with changelog).
    """
    sdrf = parse_sdrf(source)
    report = FixReport(file_path=sdrf.path)

    # Work on a mutable copy of rows
    fixed_rows: list[dict[str, str]] = []
    for row in sdrf.rows:
        fixed_rows.append(dict(row))

    # Apply fixes per column
    for col_idx, col in enumerate(sdrf.columns):
        inner = col.inner_name.lower()
        col_key = sdrf.key_for_column(col_idx)

        for row_idx, row in enumerate(fixed_rows):
            value = row.get(col_key, "")
            if not value.strip():
                continue

            row_num = row_idx + 1  # 1-indexed

            # Apply fixes in priority order
            fixers = []

            # Pattern 1: UNIMOD swaps (modification parameters)
            if inner == "modification parameters":
                fixers.append(("unimod_swap", _fix_unimod_swap))

            # Pattern 3: Case normalization
            if inner in ("sex", "organism"):
                fixers.append(("case", lambda v, i=inner: _fix_case(v, i)))

            # Pattern 4: Python artifacts (all columns)
            fixers.append(("python_artifact", _fix_python_artifacts))

            # Pattern 5: Reserved words (all columns)
            fixers.append(("reserved_word", _fix_reserved_words))

            # Pattern 6: DDA/DIA terminology
            if inner in ("dissociation method",) or "acquisition" in inner:
                fixers.append(("dda_dia", _fix_dda_dia))

            # Pattern 7: Age format
            if inner == "age":
                fixers.append(("age_format", _fix_age_format))

            # Pattern 9: Whitespace (all columns)
            fixers.append(("whitespace", _fix_whitespace))

            for pattern_name, fixer in fixers:
                current = row[col_key]
                fixed, reason = fixer(current)
                if fixed is not None and fixed != current:
                    report.fixes.append(FixRecord(
                        row=row_num,
                        column=col.raw_name,
                        old_value=current,
                        new_value=fixed,
                        reason=reason,
                        pattern=pattern_name,
                    ))
                    row[col_key] = fixed

    # Also fix column name whitespace
    fixed_headers = []
    for col in sdrf.columns:
        col_key = sdrf.key_for_column(col.index)
        stripped = col.raw_name.strip()
        if stripped != col.raw_name:
            report.fixes.append(FixRecord(
                row="header",
                column=col.raw_name,
                old_value=col.raw_name,
                new_value=stripped,
                reason="Trimmed whitespace from column name",
                pattern="whitespace",
            ))
        fixed_headers.append(stripped)

    # Reconstruct TSV
    output = io.StringIO()
    writer = csv.writer(output, delimiter="\t", lineterminator="\n")

    # Write header using original column names (not disambiguated keys)
    writer.writerow(fixed_headers)

    # Write data rows — map from col_keys back to column order
    for row in fixed_rows:
        row_values = []
        for col_idx in range(len(sdrf.columns)):
            col_key = sdrf.key_for_column(col_idx)
            row_values.append(row.get(col_key, ""))
        writer.writerow(row_values)

    return output.getvalue(), report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Auto-fix common SDRF errors")
    parser.add_argument("sdrf_file", help="Path to .sdrf.tsv file")
    parser.add_argument("-o", "--output", help="Output path for fixed SDRF")
    args = parser.parse_args(argv)

    fixed_content, report = fix_sdrf(args.sdrf_file)
    print(report.changelog())

    if args.output:
        Path(args.output).write_text(fixed_content)
        print(f"\nFixed SDRF written to: {args.output}")
    else:
        print("\n--- Fixed SDRF ---")
        print(fixed_content)


if __name__ == "__main__":
    main()

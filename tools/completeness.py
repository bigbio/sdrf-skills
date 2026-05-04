"""Annotation completeness scorer for SDRF files.

Implements the 5-dimension quality scoring from sdrf-improve SKILL.md:
  Completeness (0.30) + Specificity (0.25) + Consistency (0.15)
  + Standards (0.15) + Design (0.15)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tools.column_ontology_map import RESERVED_WORDS, WRONG_RESERVED
from tools.sdrf_parser import SDRFFile, parse_sdrf, parse_modification


# ---------------------------------------------------------------------------
# Known required/recommended columns per template
# ---------------------------------------------------------------------------

# Base (ms-proteomics) required columns
BASE_REQUIRED = [
    "source name",
    "assay name",
    "technology type",
    "comment[data file]",
    "comment[fraction identifier]",
    "comment[technical replicate]",
    "comment[sdrf version]",
]

# Columns required for ms-proteomics template
MS_PROTEOMICS_REQUIRED = BASE_REQUIRED + [
    "characteristics[organism]",
    "comment[instrument]",
    "comment[modification parameters]",
    "comment[cleavage agent details]",
    "comment[precursor mass tolerance]",
    "comment[fragment mass tolerance]",
    "comment[label]",
]

# Columns recommended for human studies
HUMAN_RECOMMENDED = [
    "characteristics[disease]",
    "characteristics[organism part]",
    "characteristics[cell type]",
    "characteristics[sex]",
    "characteristics[age]",
    "characteristics[ancestry category]",
    "characteristics[developmental stage]",
]

# Template -> required columns mapping
TEMPLATE_REQUIRED: dict[str, list[str]] = {
    "ms-proteomics": MS_PROTEOMICS_REQUIRED,
}

# Template -> recommended columns mapping
TEMPLATE_RECOMMENDED: dict[str, list[str]] = {
    "human": HUMAN_RECOMMENDED,
    "cell-lines": [
        "characteristics[cell line]",
        "characteristics[cellosaurus accession]",
        "characteristics[cellosaurus name]",
    ],
}

# Known generic terms that should be more specific
GENERIC_TERMS: dict[str, list[str]] = {
    "disease": ["cancer", "tumor", "tumour", "carcinoma", "disease"],
    "organism part": ["tissue", "organ", "body part"],
    "cell type": ["cell", "cells"],
}

# Age format pattern
AGE_PATTERN = re.compile(r"^\d+[YMWD]$")

# Valid sex values
VALID_SEX = {"male", "female", "not available", "not applicable", "mixed"}


# ---------------------------------------------------------------------------
# Report dataclasses
# ---------------------------------------------------------------------------

@dataclass
class DimensionScore:
    """Score for a single quality dimension."""
    name: str
    score: float  # 0-100
    weight: float
    issues: list[str] = field(default_factory=list)

    @property
    def weighted(self) -> float:
        return self.score * self.weight

    def bar(self, width: int = 10) -> str:
        filled = int(self.score / 100 * width)
        return "\u2588" * filled + "\u2591" * (width - filled)


@dataclass
class QualityReport:
    """Full quality scoring report."""
    file_path: str | None
    completeness: DimensionScore = field(default_factory=lambda: DimensionScore("Completeness", 0, 0.30))
    specificity: DimensionScore = field(default_factory=lambda: DimensionScore("Specificity", 0, 0.25))
    consistency: DimensionScore = field(default_factory=lambda: DimensionScore("Consistency", 0, 0.15))
    standards: DimensionScore = field(default_factory=lambda: DimensionScore("Standards", 0, 0.15))
    design: DimensionScore = field(default_factory=lambda: DimensionScore("Design", 0, 0.15))

    @property
    def overall(self) -> float:
        return (
            self.completeness.weighted
            + self.specificity.weighted
            + self.consistency.weighted
            + self.standards.weighted
            + self.design.weighted
        )

    @property
    def grade(self) -> str:
        s = self.overall
        if s >= 90:
            return "Excellent"
        elif s >= 70:
            return "Good"
        elif s >= 50:
            return "Needs work"
        return "Poor"

    def summary(self) -> str:
        lines = [
            f"Quality Score: {self.overall:.0f}/100 ({self.grade})",
            "",
            f"  Completeness:  {self.completeness.score:.0f}/100 {self.completeness.bar()}",
            f"  Specificity:   {self.specificity.score:.0f}/100 {self.specificity.bar()}",
            f"  Consistency:   {self.consistency.score:.0f}/100 {self.consistency.bar()}",
            f"  Standards:     {self.standards.score:.0f}/100 {self.standards.bar()}",
            f"  Design:        {self.design.score:.0f}/100 {self.design.bar()}",
        ]

        # Append issues per dimension
        for dim in [self.completeness, self.specificity, self.consistency,
                    self.standards, self.design]:
            if dim.issues:
                lines.append(f"\n  {dim.name} issues:")
                for issue in dim.issues[:5]:
                    lines.append(f"    - {issue}")
                if len(dim.issues) > 5:
                    lines.append(f"    ... and {len(dim.issues) - 5} more")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------

def score_sdrf(
    source: str | Path,
    spec_path: str | Path | None = None,
) -> QualityReport:
    """Score an SDRF file on 5 quality dimensions.

    Args:
        source: Path to SDRF file or raw TSV content.
        spec_path: Path to TERMS.tsv (optional, for dynamic column requirements).

    Returns:
        QualityReport with per-dimension scores and overall weighted score.
    """
    sdrf = parse_sdrf(source)
    templates = sdrf.auto_detect_templates()
    report = QualityReport(file_path=sdrf.path)

    report.completeness = _score_completeness(sdrf, templates)
    report.specificity = _score_specificity(sdrf)
    report.consistency = _score_consistency(sdrf)
    report.standards = _score_standards(sdrf, templates)
    report.design = _score_design(sdrf)

    return report


def _score_completeness(sdrf: SDRFFile, templates: list[str]) -> DimensionScore:
    """Score completeness: are all required/recommended columns present?"""
    dim = DimensionScore("Completeness", 100, 0.30)
    col_names_lower = {c.raw_name.lower() for c in sdrf.columns}

    # Check required columns for each template
    required_present = 0
    required_total = 0
    for tmpl in templates:
        for col in TEMPLATE_REQUIRED.get(tmpl, []):
            required_total += 1
            if col.lower() in col_names_lower:
                required_present += 1
            else:
                dim.issues.append(f"Missing required column: {col} (template: {tmpl})")

    # Check recommended columns
    recommended_present = 0
    recommended_total = 0
    for tmpl in templates:
        for col in TEMPLATE_RECOMMENDED.get(tmpl, []):
            recommended_total += 1
            if col.lower() in col_names_lower:
                recommended_present += 1
            else:
                dim.issues.append(f"Missing recommended column: {col}")

    # Calculate score
    if required_total > 0:
        req_score = (required_present / required_total) * 60
    else:
        req_score = 60

    if recommended_total > 0:
        rec_score = (recommended_present / recommended_total) * 40
    else:
        rec_score = 40

    dim.score = min(100, req_score + rec_score)
    return dim


def _score_specificity(sdrf: SDRFFile) -> DimensionScore:
    """Score specificity: are ontology terms precise enough?"""
    dim = DimensionScore("Specificity", 100, 0.25)
    deductions = 0
    checks = 0

    for i, col in enumerate(sdrf.columns):
        if col.col_type != "characteristics":
            continue
        inner = col.inner_name.lower()
        generic_list = GENERIC_TERMS.get(inner)
        if not generic_list:
            continue

        key = sdrf.key_for_column(i)
        for val in sdrf.unique_values(key):
            checks += 1
            val_lower = val.strip().lower()
            if val_lower in generic_list:
                dim.issues.append(
                    f"'{val}' in {col.raw_name} is too generic — use a more specific term"
                )
                deductions += 1

    if checks > 0:
        dim.score = max(0, 100 - (deductions / checks) * 100)
    return dim


def _score_consistency(sdrf: SDRFFile) -> DimensionScore:
    """Score consistency: case, format, naming uniformity."""
    dim = DimensionScore("Consistency", 100, 0.15)
    deductions = 0
    checks = 0

    for i, col in enumerate(sdrf.columns):
        inner = col.inner_name.lower()
        key = sdrf.key_for_column(i)
        values = list(sdrf.unique_values(key))

        if not values:
            continue

        # Case consistency check
        if inner == "sex":
            checks += 1
            for val in values:
                if val != val.lower() and val.lower() in VALID_SEX:
                    dim.issues.append(f"'{val}' should be lowercase '{val.lower()}'")
                    deductions += 1

        # Age format consistency
        if inner == "age":
            checks += 1
            for val in values:
                if val.lower() in ("not available", "not applicable"):
                    continue
                if not AGE_PATTERN.match(val):
                    dim.issues.append(f"Age '{val}' not in standard format (e.g. 58Y)")
                    deductions += 1

        # Organism case consistency (binomial nomenclature)
        if inner == "organism":
            checks += 1
            for val in values:
                parts = val.split()
                if len(parts) >= 2:
                    if not parts[0][0].isupper() or not parts[1][0].islower():
                        dim.issues.append(
                            f"Organism '{val}' — should follow binomial nomenclature"
                        )
                        deductions += 1

        # Reserved word consistency
        if col.col_type in ("characteristics", "comment"):
            for val in values:
                if val in WRONG_RESERVED:
                    checks += 1
                    dim.issues.append(
                        f"'{val}' in {col.raw_name} — use '{WRONG_RESERVED[val]}'"
                    )
                    deductions += 1

        # Python artifact detection
        for val in values:
            if re.match(r"^\[.*\]$", val) or val in ("nan", "None", "NaN"):
                checks += 1
                dim.issues.append(f"Python artifact '{val}' in {col.raw_name}")
                deductions += 1

    if checks > 0:
        dim.score = max(0, 100 - (deductions / max(1, checks)) * 50)
    return dim


def _score_standards(sdrf: SDRFFile, templates: list[str]) -> DimensionScore:
    """Score standards compliance: metadata columns, format correctness."""
    dim = DimensionScore("Standards", 100, 0.15)
    checks = 0
    ok = 0

    col_names_lower = {c.raw_name.lower() for c in sdrf.columns}

    # SDRF version present
    checks += 1
    if "comment[sdrf version]" in col_names_lower:
        ok += 1
    else:
        dim.issues.append("Missing comment[sdrf version]")

    # Template declared
    checks += 1
    if "comment[sdrf template]" in col_names_lower:
        ok += 1
    else:
        dim.issues.append("Missing comment[sdrf template]")

    # First column is source name
    checks += 1
    if sdrf.columns and sdrf.columns[0].raw_name.lower() == "source name":
        ok += 1
    else:
        dim.issues.append("First column should be 'source name'")

    # Modification format correctness
    for i, col in enumerate(sdrf.columns):
        if col.inner_name.lower() != "modification parameters":
            continue
        key = sdrf.key_for_column(i)
        for val in sdrf.unique_values(key):
            if val.lower() in ("not available", "not applicable"):
                continue
            checks += 1
            mod = parse_modification(val)
            if mod.ac and mod.nt and mod.mt:
                ok += 1
            else:
                missing = []
                if not mod.ac:
                    missing.append("AC")
                if not mod.nt:
                    missing.append("NT")
                if not mod.mt:
                    missing.append("MT")
                dim.issues.append(
                    f"Modification missing {', '.join(missing)}: '{val}'"
                )

    if checks > 0:
        dim.score = (ok / checks) * 100
    return dim


def _score_design(sdrf: SDRFFile) -> DimensionScore:
    """Score experimental design clarity: factor values, replication."""
    dim = DimensionScore("Design", 100, 0.15)
    checks = 0
    ok = 0

    # Factor values present
    factor_cols = sdrf.column_names("factor_value")
    checks += 1
    if factor_cols:
        ok += 1
    else:
        dim.issues.append("No factor value columns defined")

    # Factor values correspond to characteristics
    char_names = {c.inner_name.lower() for c in sdrf.columns if c.col_type == "characteristics"}
    for fc in factor_cols:
        checks += 1
        # Extract inner name from "factor value[disease]"
        inner = fc.split("[", 1)[1].rstrip("]").lower() if "[" in fc else ""
        if inner in char_names:
            ok += 1
        else:
            dim.issues.append(
                f"Factor value '{fc}' has no matching characteristics column"
            )

    # Biological replicate column
    checks += 1
    col_names_lower = {c.raw_name.lower() for c in sdrf.columns}
    if "characteristics[biological replicate]" in col_names_lower:
        ok += 1
    else:
        dim.issues.append("Missing characteristics[biological replicate]")

    # Technical replicate column
    checks += 1
    if "comment[technical replicate]" in col_names_lower:
        ok += 1
    else:
        dim.issues.append("Missing comment[technical replicate]")

    if checks > 0:
        dim.score = (ok / checks) * 100
    return dim


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Score SDRF annotation completeness and quality"
    )
    parser.add_argument("sdrf_file", help="Path to .sdrf.tsv file")
    args = parser.parse_args(argv)

    report = score_sdrf(args.sdrf_file)
    print(report.summary())


if __name__ == "__main__":
    main()

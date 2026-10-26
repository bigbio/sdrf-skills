"""Find SDRF columns whose values no claim in the evidence manifest covers.

The adversarial reviewer's omission-safety pass traces every value to a cited source, so a column
with a real value and no claim fails the review even when `parse_sdrf` and `sdrf-tools check` pass.
Seen on PXD074155: the manifest had no claim for the mass tolerances or the dissociation method.

A claim covers a column when the column header occurs in the claim's `location` (the contract field
that maps a claim to a column or row, `characteristics[organism] rows 1-12`). A claim without
`location` falls back to a `column` field, with a warning. Matching is by column only: row ranges
in `location` are prose, and whether they support each row is the reviewer's call.

The manifest is checked with the shared evidence-manifest schema (`tools/json_schema.py`), but
schema errors are warnings here, not failures: `sdrf-tools schema-check` owns the shape and this
check owns coverage, so a draft manifest still gets its gap list. The `column` fallback stays for
the same reason; the schema rejects it, so such a manifest still fails `schema-check`.

A column needs a claim when at least one cell holds a value other than `not available` or
`not applicable` (the sentinels). The other reserved words (`pooled`, `anonymized`, `normal`)
assert something about the sample, so they need a claim too. Exempt: the anchor columns (identity
and infrastructure, not facts about the experiment) and the SDRF metadata columns, which describe
the file. A `factor value[x]` column copies the column it mirrors, so a claim for either
`factor value[x]` or `characteristics[x]` / `comment[x]` covers both.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from tools.column_ontology_map import RESERVED_WORDS
from tools.json_schema import manifest_errors
from tools.sdrf_parser import parse_sdrf

METADATA_COLUMNS = frozenset({
    "comment[sdrf version]",
    "comment[sdrf template]",
    "comment[sdrf annotation tool]",
    "comment[sdrf validation hash]",
})
#: `not available` / `not applicable`: cells that assert nothing and need no source.
SENTINELS = RESERVED_WORDS
_NO_VALUE = SENTINELS | {""}
#: Distinct values shown per uncovered column.
MAX_EXAMPLES = 3


@dataclass(frozen=True)
class Gap:
    """One column with a value other than a sentinel and no claim."""

    column: str
    rows: int
    examples: tuple[str, ...]

    def __str__(self) -> str:
        shown = ", ".join(repr(v) for v in self.examples)
        return f"{self.column}: {self.rows} row(s) with a value, no claim (e.g. {shown})"


@dataclass
class CoverageReport:
    gaps: list[Gap] = field(default_factory=list)
    covered: list[str] = field(default_factory=list)
    exempt: list[str] = field(default_factory=list)
    sentinel_only: list[str] = field(default_factory=list)
    unlocated_claims: int = 0
    column_alias_claims: int = 0
    schema_errors: list[str] = field(default_factory=list)

    @property
    def is_covered(self) -> bool:
        return not self.gaps

    def to_dict(self) -> dict:
        return {
            "ok": self.is_covered,
            "gaps": [{"column": g.column, "rows": g.rows, "examples": list(g.examples)} for g in self.gaps],
            "covered_columns": self.covered,
            "exempt_columns": self.exempt,
            "sentinel_only_columns": self.sentinel_only,
            "unlocated_claims": self.unlocated_claims,
            "column_alias_claims": self.column_alias_claims,
            "schema_errors": self.schema_errors,
        }

    def render(self) -> str:
        lines = []
        if self.gaps:
            lines.append(f"{len(self.gaps)} column(s) with values but no claim in the manifest:")
            lines.extend(f"  {gap}" for gap in self.gaps)
            lines.append(
                "Add a claim that cites the source of each value and names the column in `location`. "
                "Use a reserved word only when no source supports the value."
            )
        else:
            lines.append(f"Manifest covers every column with a value ({len(self.covered)} column(s)).")
        if self.column_alias_claims:
            lines.append(
                f"warning: {self.column_alias_claims} claim(s) use `column`; the contract field is `location`."
            )
        if self.unlocated_claims:
            lines.append(
                f"{self.unlocated_claims} claim(s) have no `location` and cover no column; "
                "the review contract maps each claim to a column through `location`."
            )
        if self.schema_errors:
            lines.append(
                f"warning: the manifest has {len(self.schema_errors)} problem(s) against the evidence-manifest "
                "schema; run `sdrf-tools schema-check` on it."
            )
        return "\n".join(lines)


def _normalise(text: str) -> str:
    text = re.sub(r"\s+", " ", text.strip().lower())
    return re.sub(r"\s*([\[\]])\s*", r"\1", text)


class ManifestError(ValueError):
    """The evidence manifest cannot be read or has no `claims` list."""


def _as_text(field_value: object) -> str:
    if isinstance(field_value, list):
        field_value = ", ".join(v for v in field_value if isinstance(v, str))
    return field_value.strip() if isinstance(field_value, str) else ""


def load_claim_locations(manifest_path: str | Path) -> tuple[list[str], int, int, list[str]]:
    """Return the normalised location of every claim, the count of claims without one, the count
    that gave it only as `column`, and the manifest's schema errors. Either field may be a string
    or a list of strings here; the schema allows only a string, so `schema-check` rejects a list."""
    try:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestError(f"cannot read evidence manifest {manifest_path}: {exc}") from exc
    claims = manifest.get("claims") if isinstance(manifest, dict) else None
    if not isinstance(claims, list):
        raise ManifestError(f"evidence manifest {manifest_path} must be a JSON object with a `claims` list")
    locations: list[str] = []
    unlocated = aliased = 0
    for claim in claims:
        claim = claim if isinstance(claim, dict) else {}
        location = _as_text(claim.get("location"))
        if not location:
            location = _as_text(claim.get("column"))
            aliased += bool(location)
        if location:
            locations.append(_normalise(location))
        else:
            unlocated += 1
    return locations, unlocated, aliased, manifest_errors(manifest)


def check_coverage(sdrf_path: str | Path, manifest_path: str | Path) -> CoverageReport:
    locations, unlocated, aliased, errors = load_claim_locations(manifest_path)
    sdrf = parse_sdrf(sdrf_path)
    report = CoverageReport(unlocated_claims=unlocated, column_alias_claims=aliased, schema_errors=errors)

    def claimed(name: str) -> bool:
        return any(name in location for location in locations)

    seen: set[str] = set()
    for column in sdrf.columns:
        if column.raw_name in seen:
            continue
        seen.add(column.raw_name)
        name = _normalise(column.raw_name)
        if column.col_type == "anchor" or name in METADATA_COLUMNS:
            report.exempt.append(column.raw_name)
            continue
        keys = sdrf.all_keys_for_name(column.raw_name)
        values: list[str] = []
        rows_with_value = 0
        for row in sdrf.rows:
            row_values = [row[k].strip() for k in keys if row[k].strip().lower() not in _NO_VALUE]
            values += row_values
            rows_with_value += bool(row_values)
        if not values:
            report.sentinel_only.append(column.raw_name)
            continue
        inner = _normalise(column.inner_name)
        candidates = [name]
        if column.col_type == "factor_value":
            candidates += [f"characteristics[{inner}]", f"comment[{inner}]"]
        elif column.col_type in ("characteristics", "comment"):
            candidates.append(f"factor value[{inner}]")
        if any(claimed(c) for c in candidates):
            report.covered.append(column.raw_name)
            continue
        examples = tuple(dict.fromkeys(values))[:MAX_EXAMPLES]
        report.gaps.append(Gap(column=column.raw_name, rows=rows_with_value, examples=examples))
    return report

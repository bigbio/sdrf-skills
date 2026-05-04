"""Benchmark suite for measuring SDRF annotation quality across datasets.

Fetches community-annotated SDRFs from PRIDE/proteomics-sample-metadata
and runs quality analysis to identify systemic annotation patterns.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

from tools.completeness import QualityReport, score_sdrf
from tools.hallucination import HallucinationReport, detect_hallucinations
from tools.sdrf_fixer import FixReport, fix_sdrf


# ---------------------------------------------------------------------------
# Report structures
# ---------------------------------------------------------------------------

@dataclass
class DatasetResult:
    """Analysis result for a single dataset."""
    pxd_accession: str
    sdrf_source: str  # "local", "github", "pride"
    quality: QualityReport | None = None
    hallucinations: HallucinationReport | None = None
    fix_report: FixReport | None = None
    error: str | None = None


@dataclass
class BenchmarkReport:
    """Aggregate report across multiple datasets."""
    datasets: list[DatasetResult] = field(default_factory=list)

    @property
    def successful(self) -> list[DatasetResult]:
        return [d for d in self.datasets if d.error is None and d.quality is not None]

    @property
    def avg_quality(self) -> float:
        scores = [d.quality.overall for d in self.successful if d.quality]
        return sum(scores) / len(scores) if scores else 0

    @property
    def total_hallucinations(self) -> int:
        return sum(
            d.hallucinations.total_issues
            for d in self.successful
            if d.hallucinations
        )

    @property
    def total_fixable(self) -> int:
        return sum(
            d.fix_report.total_fixes
            for d in self.successful
            if d.fix_report
        )

    def summary(self) -> str:
        lines = [
            "Benchmark Report",
            f"  Datasets analyzed: {len(self.datasets)}",
            f"  Successful: {len(self.successful)}/{len(self.datasets)}",
            f"  Average quality score: {self.avg_quality:.1f}/100",
            f"  Total hallucination issues: {self.total_hallucinations}",
            f"  Total auto-fixable issues: {self.total_fixable}",
        ]

        if self.successful:
            lines.append("\n  Per-dataset scores:")
            for d in self.successful:
                q = d.quality.overall if d.quality else 0
                h = d.hallucinations.total_issues if d.hallucinations else 0
                f = d.fix_report.total_fixes if d.fix_report else 0
                lines.append(f"    {d.pxd_accession}: quality={q:.0f} hallucinations={h} fixable={f}")

        # Common patterns
        all_patterns: dict[str, int] = {}
        for d in self.successful:
            if d.fix_report:
                for pattern, count in d.fix_report.by_pattern().items():
                    all_patterns[pattern] = all_patterns.get(pattern, 0) + count

        if all_patterns:
            lines.append("\n  Most common error patterns:")
            for pattern, count in sorted(all_patterns.items(), key=lambda x: -x[1])[:5]:
                lines.append(f"    {pattern}: {count}")

        failed = [d for d in self.datasets if d.error]
        if failed:
            lines.append(f"\n  Failed ({len(failed)}):")
            for d in failed:
                lines.append(f"    {d.pxd_accession}: {d.error}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# SDRF fetchers
# ---------------------------------------------------------------------------

GITHUB_RAW_BASE = "https://raw.githubusercontent.com/bigbio/proteomics-sample-metadata/master"


def fetch_community_sdrf(pxd_accession: str) -> str | None:
    """Fetch an SDRF file from the proteomics-sample-metadata GitHub repo."""
    # Try common path patterns
    paths = [
        f"/annotated-projects/{pxd_accession}/{pxd_accession}.sdrf.tsv",
        f"/projects/{pxd_accession}/{pxd_accession}.sdrf.tsv",
    ]
    for path in paths:
        url = f"{GITHUB_RAW_BASE}{path}"
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                return resp.text
        except requests.RequestException:
            continue
    return None


def fetch_local_sdrf(path: str | Path) -> str | None:
    """Read SDRF from local file."""
    p = Path(path)
    if p.exists():
        return p.read_text(encoding="utf-8-sig")
    return None


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------

class BenchmarkSuite:
    """Runs quality analysis across multiple SDRF datasets."""

    def __init__(self, verify_online: bool = False):
        self.verify_online = verify_online

    def run(
        self,
        pxd_accessions: list[str] | None = None,
        local_files: list[str | Path] | None = None,
    ) -> BenchmarkReport:
        """Run benchmark on given PXD accessions and/or local files."""
        report = BenchmarkReport()

        # Process PXD accessions
        for pxd in (pxd_accessions or []):
            result = self._analyze_pxd(pxd)
            report.datasets.append(result)

        # Process local files
        for filepath in (local_files or []):
            result = self._analyze_local(filepath)
            report.datasets.append(result)

        return report

    def _analyze_pxd(self, pxd: str) -> DatasetResult:
        """Analyze a community-annotated SDRF by PXD accession."""
        result = DatasetResult(pxd_accession=pxd, sdrf_source="github")

        content = fetch_community_sdrf(pxd)
        if not content:
            result.error = f"SDRF not found for {pxd} in proteomics-sample-metadata"
            return result

        return self._analyze_content(content, result)

    def _analyze_local(self, path: str | Path) -> DatasetResult:
        """Analyze a local SDRF file."""
        p = Path(path)
        result = DatasetResult(
            pxd_accession=p.stem.replace(".sdrf", ""),
            sdrf_source="local",
        )

        content = fetch_local_sdrf(path)
        if not content:
            result.error = f"File not found: {path}"
            return result

        return self._analyze_content(content, result)

    def _analyze_content(self, content: str, result: DatasetResult) -> DatasetResult:
        """Run all analyses on SDRF content."""
        try:
            result.quality = score_sdrf(content)
        except Exception as e:
            result.error = f"Quality scoring failed: {e}"
            return result

        try:
            result.hallucinations = detect_hallucinations(
                content, verify_online=self.verify_online
            )
        except Exception as e:
            result.error = f"Hallucination detection failed: {e}"
            return result

        try:
            _, result.fix_report = fix_sdrf(content)
        except Exception as e:
            result.error = f"Fix analysis failed: {e}"
            return result

        return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Benchmark SDRF annotation quality across datasets"
    )
    parser.add_argument(
        "sources", nargs="+",
        help="PXD accessions or local .sdrf.tsv file paths",
    )
    parser.add_argument(
        "--online", action="store_true",
        help="Verify ontology terms against OLS API",
    )
    args = parser.parse_args(argv)

    pxd_accessions = []
    local_files = []
    for src in args.sources:
        if src.upper().startswith("PXD"):
            pxd_accessions.append(src)
        else:
            local_files.append(src)

    suite = BenchmarkSuite(verify_online=args.online)
    report = suite.run(pxd_accessions=pxd_accessions, local_files=local_files)
    print(report.summary())


if __name__ == "__main__":
    main()

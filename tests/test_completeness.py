"""Tests for tools.completeness — quality scoring."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.completeness import score_sdrf, QualityReport


class TestScoreSdrf:
    def test_synthetic_sdrf_scores(self, synthetic_sdrf_path: Path):
        report = score_sdrf(synthetic_sdrf_path)
        assert isinstance(report, QualityReport)
        assert 0 <= report.overall <= 100

    def test_synthetic_has_consistency_issues(self, synthetic_sdrf_path: Path):
        """Synthetic SDRF has deliberate case/format errors."""
        report = score_sdrf(synthetic_sdrf_path)
        assert report.consistency.score < 100
        # Should catch: "Male" (should be lowercase), "58 years" (should be 58Y),
        # "N/A" (should be "not applicable"), "homo sapiens" (case), Python artifacts
        assert len(report.consistency.issues) >= 1

    def test_synthetic_has_design_score(self, synthetic_sdrf_path: Path):
        report = score_sdrf(synthetic_sdrf_path)
        # Has factor value[disease], so design should get partial credit
        assert report.design.score > 0

    def test_synthetic_completeness_partial(self, synthetic_sdrf_path: Path):
        report = score_sdrf(synthetic_sdrf_path)
        # Has most ms-proteomics columns but missing comment[label]
        assert report.completeness.score > 50

    def test_synthetic_standards(self, synthetic_sdrf_path: Path):
        report = score_sdrf(synthetic_sdrf_path)
        # Has sdrf version and template columns
        assert report.standards.score > 50

    def test_minimal_sdrf(self, minimal_sdrf_content: str):
        report = score_sdrf(minimal_sdrf_content)
        # Minimal SDRF lacks many columns
        assert report.completeness.score < 100
        assert report.overall < 80

    def test_summary_format(self, synthetic_sdrf_path: Path):
        report = score_sdrf(synthetic_sdrf_path)
        summary = report.summary()
        assert "Quality Score:" in summary
        assert "Completeness:" in summary
        assert "Specificity:" in summary
        assert "Consistency:" in summary
        assert "Standards:" in summary
        assert "Design:" in summary

    def test_grade_mapping(self):
        report = QualityReport(file_path=None)
        report.completeness.score = 95
        report.specificity.score = 90
        report.consistency.score = 95
        report.standards.score = 100
        report.design.score = 100
        assert report.grade == "Excellent"

        report.completeness.score = 70
        report.specificity.score = 70
        assert report.grade == "Good"

    def test_empty_sdrf(self, empty_sdrf_content: str):
        report = score_sdrf(empty_sdrf_content)
        assert report.overall >= 0

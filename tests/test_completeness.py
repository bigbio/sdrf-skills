"""Tests for tools.completeness — quality scoring."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.completeness import score_sdrf, QualityReport, AGE_PATTERN, MS_PROTEOMICS_REQUIRED


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


class TestAgePattern:
    """Tests for the AGE_PATTERN regex."""

    def test_simple_year(self):
        assert AGE_PATTERN.match("58Y") is not None

    def test_simple_month(self):
        assert AGE_PATTERN.match("6M") is not None

    def test_simple_week(self):
        assert AGE_PATTERN.match("2W") is not None

    def test_simple_day(self):
        assert AGE_PATTERN.match("10D") is not None

    def test_compound_year_month(self):
        """30Y6M (Cellosaurus-emitted format) must be accepted."""
        assert AGE_PATTERN.match("30Y6M") is not None

    def test_compound_year_month_day(self):
        assert AGE_PATTERN.match("1Y6M10D") is not None

    def test_free_text_rejected(self):
        assert AGE_PATTERN.match("58 years") is None

    def test_decimal_rejected(self):
        assert AGE_PATTERN.match("3.5Y") is None

    def test_empty_rejected(self):
        assert AGE_PATTERN.match("") is None


class TestToleranceColumnsNotRequired:
    """precursor/fragment mass tolerance must be recommended, not required."""

    def test_tolerance_columns_absent_from_required(self):
        assert "comment[precursor mass tolerance]" not in MS_PROTEOMICS_REQUIRED
        assert "comment[fragment mass tolerance]" not in MS_PROTEOMICS_REQUIRED

    def test_missing_tolerance_not_flagged_as_required(self):
        """Score an SDRF that lacks tolerance columns but has all other required fields."""
        sdrf_without_tolerance = (
            "source name\tcharacteristics[organism]\tassay name\t"
            "technology type\tcomment[data file]\tcomment[fraction identifier]\t"
            "comment[technical replicate]\tcomment[sdrf version]\t"
            "comment[instrument]\tcomment[modification parameters]\t"
            "comment[cleavage agent details]\tcomment[label]\t"
            "comment[proteomics data acquisition method]\n"
            "s1\tHomo sapiens\trun1\tproteomic profiling by mass spectrometry\t"
            "file1.raw\t1\t1\tv1.1.0\t"
            "AC=MS:1001911;NT=LTQ Orbitrap\tNT=Carbamidomethyl;AC=UNIMOD:4;TA=C;MT=Fixed\t"
            "NT=Trypsin;AC=MS:1001251\tlabel free sample\t"
            "data-independent acquisition\n"
        )
        report = score_sdrf(sdrf_without_tolerance)
        required_issues = [
            i for i in report.completeness.issues
            if "missing required" in i.lower()
            and ("precursor mass tolerance" in i or "fragment mass tolerance" in i)
        ]
        assert required_issues == [], (
            f"Tolerance columns should not be flagged as required: {required_issues}"
        )

    def test_missing_tolerance_flagged_as_recommended(self):
        """Missing tolerance columns should appear under recommended, not required."""
        sdrf_without_tolerance = (
            "source name\tcharacteristics[organism]\tassay name\t"
            "technology type\tcomment[data file]\tcomment[fraction identifier]\t"
            "comment[technical replicate]\tcomment[sdrf version]\t"
            "comment[instrument]\tcomment[modification parameters]\t"
            "comment[cleavage agent details]\tcomment[label]\t"
            "comment[proteomics data acquisition method]\n"
            "s1\tHomo sapiens\trun1\tproteomic profiling by mass spectrometry\t"
            "file1.raw\t1\t1\tv1.1.0\t"
            "AC=MS:1001911;NT=LTQ Orbitrap\tNT=Carbamidomethyl;AC=UNIMOD:4;TA=C;MT=Fixed\t"
            "NT=Trypsin;AC=MS:1001251\tlabel free sample\t"
            "data-independent acquisition\n"
        )
        report = score_sdrf(sdrf_without_tolerance)
        recommended_issues = [
            i for i in report.completeness.issues
            if "recommended" in i.lower()
            and ("precursor mass tolerance" in i or "fragment mass tolerance" in i)
        ]
        assert len(recommended_issues) == 2, (
            f"Both tolerance columns should be flagged as recommended: {report.completeness.issues}"
        )

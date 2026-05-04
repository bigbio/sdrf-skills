"""Tests for tools.sdrf_fixer — auto-fixer."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.sdrf_fixer import fix_sdrf, FixReport


class TestFixSdrf:
    def test_synthetic_fixes_unimod_swap(self, synthetic_sdrf_path: Path):
        """Row 3 has UNIMOD:21 for Acetyl — should become UNIMOD:1."""
        _fixed, report = fix_sdrf(synthetic_sdrf_path)
        unimod_fixes = [f for f in report.fixes if f.pattern == "unimod_swap"]
        assert len(unimod_fixes) >= 1
        assert any("UNIMOD:1" in f.new_value for f in unimod_fixes)

    def test_synthetic_fixes_case(self, synthetic_sdrf_path: Path):
        """Row 3 has 'Male' — should become 'male'."""
        _fixed, report = fix_sdrf(synthetic_sdrf_path)
        case_fixes = [f for f in report.fixes if f.pattern == "case"]
        assert any(f.old_value == "Male" and f.new_value == "male" for f in case_fixes)

    def test_synthetic_fixes_organism_case(self, synthetic_sdrf_path: Path):
        """Row 6 has 'homo sapiens' — should become 'Homo sapiens'."""
        _fixed, report = fix_sdrf(synthetic_sdrf_path)
        case_fixes = [f for f in report.fixes if f.pattern == "case"]
        assert any(
            f.old_value == "homo sapiens" and f.new_value == "Homo sapiens"
            for f in case_fixes
        )

    def test_synthetic_fixes_reserved_words(self, synthetic_sdrf_path: Path):
        """Row 5 has 'N/A' — should become 'not available'."""
        _fixed, report = fix_sdrf(synthetic_sdrf_path)
        rw_fixes = [f for f in report.fixes if f.pattern == "reserved_word"]
        assert any(f.old_value == "N/A" for f in rw_fixes)

    def test_synthetic_fixes_python_artifacts(self, synthetic_sdrf_path: Path):
        """Row 5 has [\"breast carcinoma\"] — should be stripped."""
        _fixed, report = fix_sdrf(synthetic_sdrf_path)
        artifact_fixes = [f for f in report.fixes if f.pattern == "python_artifact"]
        assert len(artifact_fixes) >= 1

    def test_synthetic_fixes_age(self, synthetic_sdrf_path: Path):
        """Row 3 has '58 years' — should become '58Y'."""
        _fixed, report = fix_sdrf(synthetic_sdrf_path)
        age_fixes = [f for f in report.fixes if f.pattern == "age_format"]
        assert any(f.old_value == "58 years" and f.new_value == "58Y" for f in age_fixes)

    def test_changelog_output(self, synthetic_sdrf_path: Path):
        _fixed, report = fix_sdrf(synthetic_sdrf_path)
        changelog = report.changelog()
        assert "Changes Applied:" in changelog
        assert "Summary:" in changelog

    def test_fixed_content_is_valid_tsv(self, synthetic_sdrf_path: Path):
        fixed, report = fix_sdrf(synthetic_sdrf_path)
        lines = fixed.strip().split("\n")
        header_cols = lines[0].split("\t")
        for line in lines[1:]:
            assert len(line.split("\t")) == len(header_cols)

    def test_no_fixes_needed(self):
        """A clean SDRF should produce zero fixes."""
        content = (
            "source name\tcharacteristics[organism]\tcharacteristics[sex]\tassay name\n"
            "s1\tHomo sapiens\tfemale\trun1\n"
        )
        _fixed, report = fix_sdrf(content)
        assert report.total_fixes == 0

    def test_by_pattern_counts(self, synthetic_sdrf_path: Path):
        _fixed, report = fix_sdrf(synthetic_sdrf_path)
        counts = report.by_pattern()
        assert isinstance(counts, dict)
        assert sum(counts.values()) == report.total_fixes


class TestIndividualFixers:
    def test_age_bare_number(self):
        content = "source name\tcharacteristics[age]\n" "s1\t58\n"
        _fixed, report = fix_sdrf(content)
        assert any(f.new_value == "58Y" for f in report.fixes)

    def test_age_months(self):
        content = "source name\tcharacteristics[age]\n" "s1\t6 months\n"
        _fixed, report = fix_sdrf(content)
        assert any(f.new_value == "6M" for f in report.fixes)

    def test_reserved_na(self):
        content = "source name\tcharacteristics[disease]\n" "s1\tNA\n"
        _fixed, report = fix_sdrf(content)
        assert any(f.new_value == "not available" for f in report.fixes)

    def test_python_nan(self):
        content = "source name\tcharacteristics[disease]\n" "s1\tnan\n"
        _fixed, report = fix_sdrf(content)
        assert any(f.new_value == "not available" for f in report.fixes)

    def test_python_none(self):
        content = "source name\tcharacteristics[disease]\n" "s1\tNone\n"
        _fixed, report = fix_sdrf(content)
        assert any(f.new_value == "not available" for f in report.fixes)

    def test_whitespace_trim(self):
        content = "source name\tcharacteristics[disease]\n" "s1\t cancer \n"
        _fixed, report = fix_sdrf(content)
        assert any(f.pattern == "whitespace" for f in report.fixes)

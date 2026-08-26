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

    def test_characteristics_ntac_to_bare_label(self):
        content = (
            "source name\tcharacteristics[organism]\n"
            "s1\tNT=Homo sapiens;AC=NCBITaxon:9606\n"
        )
        fixed, report = fix_sdrf(content)
        assert "\tHomo sapiens\n" in fixed
        assert "NT=" not in fixed.splitlines()[1]
        assert any(f.pattern == "characteristics_bare_label" for f in report.fixes)

    def test_comment_keeps_ntac(self):
        content = (
            "source name\tcomment[cleavage agent details]\n"
            "s1\tNT=Trypsin;AC=MS:1001251\n"
        )
        fixed, report = fix_sdrf(content)
        assert "NT=Trypsin;AC=MS:1001251" in fixed
        assert not any(f.pattern == "characteristics_bare_label" for f in report.fixes)

    def test_structured_characteristic_untouched(self):
        content = (
            "source name\tcharacteristics[spiked compound]\n"
            "s1\tCT=spike;QY=10;PS=PEPTIDE\n"
        )
        fixed, report = fix_sdrf(content)
        assert "CT=spike;QY=10;PS=PEPTIDE" in fixed
        assert not any(f.pattern == "characteristics_bare_label" for f in report.fixes)

    def test_kv_python_artifact(self):
        content = (
            "source name\tcomment[modification parameters]\n"
            "s1\tNT=Carbamidomethyl;AC=UNIMOD:4;MT=Fixed;TA=['C']\n"
        )
        fixed, report = fix_sdrf(content)
        assert "TA=C" in fixed and "TA=['C']" not in fixed
        assert any(f.pattern == "kv_python_artifact" for f in report.fixes)

    def test_quoted_cell_unwrapped(self):
        # A CSV writer may leave the whole value quoted. Reading and rewriting drops the
        # quotes, so the value must come back out unwrapped either way.
        content = 'source name\tcomment[instrument]\ns1\t"NT=timsTOF HT;AC=MS:1003404"\n'
        fixed, _report = fix_sdrf(content)
        assert 'NT=timsTOF HT;AC=MS:1003404' in fixed
        assert '"NT=' not in fixed

    def test_accession_separator(self):
        content = "source name\tcomment[fractionation method]\ns1\tNT=SDS PAGE;AC=PRIDE_0000568\n"
        fixed, report = fix_sdrf(content)
        assert "AC=PRIDE:0000568" in fixed
        assert any(f.pattern == "accession_separator" for f in report.fixes)

    def test_bare_accession_gets_prefix(self):
        content = "source name\tcomment[cleavage agent details]\ns1\tNT=Trypsin;AC=1001251\n"
        fixed, report = fix_sdrf(content)
        assert "AC=MS:1001251" in fixed
        assert any(f.pattern == "bare_accession" for f in report.fixes)

    def test_bare_accession_left_when_column_ontology_ambiguous(self):
        # a column with no single expected ontology cannot have its prefix inferred
        content = "source name\tcomment[some unmapped thing]\ns1\tNT=cancer;AC=1234\n"
        fixed, report = fix_sdrf(content)
        assert "AC=1234" in fixed
        assert not any(f.pattern == "bare_accession" for f in report.fixes)

    def test_sentinel_not_wrapped_in_kv(self):
        content = (
            "source name\tcomment[cleavage agent details]\n"
            "s1\tNT=not applicable;AC=not available\n"
        )
        fixed, report = fix_sdrf(content)
        assert "\tnot applicable" in fixed and "NT=not applicable" not in fixed
        assert any(f.pattern == "sentinel_kv" for f in report.fixes)

    def test_pandas_header_suffix_removed(self):
        content = (
            "source name\tcomment[modification parameters]\tcomment[modification parameters].1\n"
            "s1\tNT=Oxidation;AC=UNIMOD:35\tNT=Acetyl;AC=UNIMOD:1\n"
        )
        fixed, report = fix_sdrf(content)
        assert ".1" not in fixed.splitlines()[0]
        assert fixed.splitlines()[0].count("comment[modification parameters]") == 2
        assert any(f.pattern == "pandas_header_suffix" for f in report.fixes)

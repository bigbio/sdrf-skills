"""Tests for the structural invariant checks."""

from tools.structure import (
    check_characteristics_are_bare,
    acquisition_family,
    check_factor_values_last,
    check_one_template_per_cell,
    check_reserved_words_allowed,
    check_row_coordinate_unique,
    check_technical_replicate_indices,
    check_technical_replicates_have_distinct_files,
    check_single_acquisition_method,
    check_structure,
    check_template_declaration_constant,
    check_template_matches_acquisition,
)
from tools.sdrf_parser import parse_sdrf

DIA = "NT=Data-independent acquisition;AC=PRIDE:0000450"
DDA = "NT=Data-dependent acquisition;AC=PRIDE:0000627"
MS_TEMPLATE = "NT=ms-proteomics;VV=v1.1.0"
DIA_TEMPLATE = "NT=dia-acquisition;VV=v1.1.0"


def build(columns: list[str], rows: list[list[str]]) -> str:
    return "\n".join(["\t".join(columns)] + ["\t".join(r) for r in rows]) + "\n"


def sdrf(acquisitions: list[str], templates: list[str] | None = None) -> str:
    """One row per acquisition value, with a matching template declaration."""
    templates = templates or [MS_TEMPLATE] * len(acquisitions)
    columns = ["source name", "comment[proteomics data acquisition method]", "comment[sdrf template]"]
    rows = [[f"sample {i + 1}", a, t] for i, (a, t) in enumerate(zip(acquisitions, templates))]
    return build(columns, rows)


class TestAcquisitionFamily:
    def test_reads_the_accession(self):
        assert acquisition_family(DIA) == "dia"
        assert acquisition_family(DDA) == "dda"

    def test_independent_is_not_read_as_dependent(self):
        """'independent' contains 'dependent', so substring order matters."""
        assert acquisition_family("Data-independent acquisition") == "dia"
        assert acquisition_family("Data-dependent acquisition") == "dda"

    def test_dia_descendants(self):
        assert acquisition_family("NT=diaPASEF;AC=PRIDE:0000650") == "dia"
        assert acquisition_family("NT=SWATH MS;AC=PRIDE:0000447") == "dia"

    def test_unknown_and_empty(self):
        assert acquisition_family("") is None
        assert acquisition_family("   ") is None
        assert acquisition_family("NT=Parallel reaction monitoring;AC=PRIDE:0000629") is None


class TestSingleAcquisitionMethod:
    def test_one_method_is_fine(self):
        assert check_single_acquisition_method(parse_sdrf(sdrf([DIA, DIA]))) == []

    def test_mixed_methods_are_reported(self):
        findings = check_single_acquisition_method(parse_sdrf(sdrf([DIA, DDA])))
        assert [f.rule for f in findings] == ["mixed-acquisition-methods"]

    def test_unknown_values_do_not_trigger(self):
        assert check_single_acquisition_method(parse_sdrf(sdrf([DIA, "", DIA]))) == []


class TestTemplateDeclaration:
    def test_constant_declaration_is_fine(self):
        assert check_template_declaration_constant(parse_sdrf(sdrf([DIA, DIA]))) == []

    def test_declaration_varying_by_row_is_reported(self):
        content = sdrf([DIA, DIA], templates=[MS_TEMPLATE, DIA_TEMPLATE])
        findings = check_template_declaration_constant(parse_sdrf(content))
        assert [f.rule for f in findings] == ["template-varies-by-row"]

    def test_two_templates_in_one_cell_are_reported(self):
        packed = f"{MS_TEMPLATE};{DIA_TEMPLATE}"
        findings = check_one_template_per_cell(parse_sdrf(sdrf([DIA], templates=[packed])))
        assert [f.rule for f in findings] == ["multiple-templates-in-one-cell"]

    def test_repeated_template_columns_are_the_correct_form(self):
        columns = ["source name", "comment[sdrf template]", "comment[sdrf template]"]
        content = build(columns, [["sample 1", MS_TEMPLATE, DIA_TEMPLATE]])
        assert check_one_template_per_cell(parse_sdrf(content)) == []
        assert check_template_declaration_constant(parse_sdrf(content)) == []


class TestTemplateMatchesAcquisition:
    def test_dia_template_with_dia_values_is_fine(self):
        content = sdrf([DIA, DIA], templates=[DIA_TEMPLATE, DIA_TEMPLATE])
        assert check_template_matches_acquisition(parse_sdrf(content)) == []

    def test_dia_template_with_dda_value_is_reported(self):
        content = sdrf([DDA], templates=[DIA_TEMPLATE])
        findings = check_template_matches_acquisition(parse_sdrf(content))
        assert [f.rule for f in findings] == ["template-contradicts-acquisition"]

    def test_dia_template_hidden_in_a_packed_cell_is_still_found(self):
        """parse_template_value keeps only the last NT=, so the raw cell has to be read too."""
        content = sdrf([DDA], templates=[f"{DIA_TEMPLATE};{MS_TEMPLATE}"])
        findings = check_template_matches_acquisition(parse_sdrf(content))
        assert [f.rule for f in findings] == ["template-contradicts-acquisition"]

    def test_no_dia_template_means_no_opinion(self):
        assert check_template_matches_acquisition(parse_sdrf(sdrf([DDA]))) == []


class TestFactorValuesLast:
    def test_factor_last_is_fine(self):
        columns = ["source name", "comment[data file]", "factor value[disease]"]
        assert check_factor_values_last(parse_sdrf(build(columns, [["s1", "a.raw", "cancer"]]))) == []

    def test_several_trailing_factors_are_fine(self):
        columns = ["source name", "factor value[disease]", "factor value[time]"]
        assert check_factor_values_last(parse_sdrf(build(columns, [["s1", "cancer", "0h"]]))) == []

    def test_column_after_a_factor_is_reported(self):
        columns = ["source name", "factor value[disease]", "comment[data file]"]
        findings = check_factor_values_last(parse_sdrf(build(columns, [["s1", "cancer", "a.raw"]])))
        assert [f.rule for f in findings] == ["factor-values-not-last"]

    def test_no_factor_column_is_fine(self):
        columns = ["source name", "comment[data file]"]
        assert check_factor_values_last(parse_sdrf(build(columns, [["s1", "a.raw"]]))) == []


class TestCheckStructure:
    def test_clean_file_has_no_findings(self):
        assert check_structure(sdrf([DIA, DIA], templates=[DIA_TEMPLATE, DIA_TEMPLATE])) == []

    def test_reports_every_broken_invariant_at_once(self):
        content = sdrf([DDA, DIA], templates=[MS_TEMPLATE, f"{MS_TEMPLATE};{DIA_TEMPLATE}"])
        rules = {f.rule for f in check_structure(content)}
        assert rules == {
            "mixed-acquisition-methods",
            "template-varies-by-row",
            "multiple-templates-in-one-cell",
            "template-contradicts-acquisition",
        }


class TestReservedWords:
    """Rules come from TERMS.tsv, which is a submodule and absent in CI, so build a fixture.

    The fixture is written with CRLF line endings on purpose: that is how the real TERMS.tsv
    ships, and comparing an unstripped 'false\r' reads as true, which would silently make the
    check pass everything.
    """

    def terms(self, tmp_path) -> str:
        header = "term\ttype\tvalues\tallow_not_available\tallow_not_applicable"
        rows = [
            "cell line\tcharacteristics\tCLO\tfalse\tfalse",
            "age\tcharacteristics\tpattern\ttrue\tfalse",
            "disease\tcharacteristics\tMONDO\ttrue\ttrue",
        ]
        path = tmp_path / "TERMS.tsv"
        path.write_bytes(("\r\n".join([header, *rows]) + "\r\n\r\n").encode("utf-8"))
        return str(path)

    def sdrf_with(self, column: str, value: str) -> str:
        return build(["source name", column], [["sample 1", value]])

    def test_disallowed_reserved_word_is_reported(self, tmp_path):
        content = self.sdrf_with("characteristics[cell line]", "not applicable")
        findings = check_reserved_words_allowed(parse_sdrf(content), spec_path=self.terms(tmp_path))
        assert [f.rule for f in findings] == ["reserved-word-not-allowed"]

    def test_a_real_value_is_fine(self, tmp_path):
        content = self.sdrf_with("characteristics[cell line]", "HeLa")
        assert check_reserved_words_allowed(parse_sdrf(content), spec_path=self.terms(tmp_path)) == []

    def test_each_reserved_word_is_permitted_independently(self, tmp_path):
        """characteristics[age] allows 'not available' but not 'not applicable'."""
        terms = self.terms(tmp_path)
        ok = self.sdrf_with("characteristics[age]", "not available")
        assert check_reserved_words_allowed(parse_sdrf(ok), spec_path=terms) == []
        bad = self.sdrf_with("characteristics[age]", "not applicable")
        assert [f.rule for f in check_reserved_words_allowed(parse_sdrf(bad), spec_path=terms)] == [
            "reserved-word-not-allowed"
        ]

    def test_column_allowing_both_is_fine(self, tmp_path):
        terms = self.terms(tmp_path)
        for word in ("not available", "not applicable"):
            content = self.sdrf_with("characteristics[disease]", word)
            assert check_reserved_words_allowed(parse_sdrf(content), spec_path=terms) == []

    def test_missing_spec_makes_the_check_silent(self):
        """No spec means no opinion: the check must not guess, and must not crash."""
        content = self.sdrf_with("characteristics[cell line]", "not applicable")
        assert check_reserved_words_allowed(parse_sdrf(content), spec_path="/nonexistent/TERMS.tsv") == []

    def test_unknown_column_has_no_rule(self, tmp_path):
        content = self.sdrf_with("characteristics[invented thing]", "not applicable")
        assert check_reserved_words_allowed(parse_sdrf(content), spec_path=self.terms(tmp_path)) == []


SRC = "source name"
TECH = "comment[technical replicate]"
BIO = "characteristics[biological replicate]"
FRAC = "comment[fraction identifier]"
LABEL = "comment[label]"
DATA_FILE = "comment[data file]"


class TestTechnicalReplicateIndices:
    def test_contiguous_from_one_is_fine(self):
        content = build([SRC, TECH], [["s1", "1"], ["s1", "2"], ["s2", "1"]])
        assert check_technical_replicate_indices(parse_sdrf(content)) == []

    def test_single_row_numbered_three_is_reported(self):
        """A sample measured once cannot be its own third replicate."""
        content = build([SRC, TECH], [["s1", "3"]])
        findings = check_technical_replicate_indices(parse_sdrf(content))
        assert [f.rule for f in findings] == ["technical-replicate-not-contiguous"]

    def test_gap_is_reported(self):
        content = build([SRC, TECH], [["s1", "1"], ["s1", "2"], ["s1", "4"]])
        assert [f.rule for f in check_technical_replicate_indices(parse_sdrf(content))] == [
            "technical-replicate-not-contiguous"
        ]

    def test_channels_of_one_run_are_not_replicates(self):
        """The real failure: labelled channels numbered 1..n as if re-injections."""
        content = build(
            [SRC, LABEL, TECH, DATA_FILE],
            [["pool", "TMT126", "1", "run.raw"], ["pool", "TMT127", "2", "run.raw"],
             ["pool", "TMT128", "3", "run.raw"]],
        )
        # 1,2,3 is contiguous and the coordinates differ, so only the file rule sees it.
        assert check_technical_replicate_indices(parse_sdrf(content)) == []
        assert check_row_coordinate_unique(parse_sdrf(content)) == []
        assert [f.rule for f in check_technical_replicates_have_distinct_files(parse_sdrf(content))] == [
            "technical-replicates-share-a-file"
        ]

    def test_missing_column_is_silent(self):
        assert check_technical_replicate_indices(parse_sdrf(build([SRC], [["s1"]]))) == []


class TestRowCoordinateUnique:
    def test_distinct_coordinates_are_fine(self):
        content = build([SRC, BIO, TECH, FRAC], [["s1", "1", "1", "1"], ["s1", "1", "2", "1"]])
        assert check_row_coordinate_unique(parse_sdrf(content)) == []

    def test_repeated_coordinate_is_reported(self):
        content = build([SRC, BIO, TECH, FRAC], [["s1", "1", "1", "1"], ["s1", "1", "1", "1"]])
        assert [f.rule for f in check_row_coordinate_unique(parse_sdrf(content))] == [
            "duplicate-row-coordinate"
        ]

    def test_fraction_distinguishes_rows(self):
        content = build([SRC, BIO, TECH, FRAC], [["s1", "1", "1", "1"], ["s1", "1", "1", "2"]])
        assert check_row_coordinate_unique(parse_sdrf(content)) == []

    def test_absent_columns_default_to_one(self):
        """A file with no replicate columns means one measurement per source name."""
        assert check_row_coordinate_unique(parse_sdrf(build([SRC], [["s1"], ["s2"]]))) == []
        assert [f.rule for f in check_row_coordinate_unique(parse_sdrf(build([SRC], [["s1"], ["s1"]])))] == [
            "duplicate-row-coordinate"
        ]


class TestTechnicalReplicatesHaveDistinctFiles:
    def test_replicates_in_separate_files_are_fine(self):
        content = build([SRC, TECH, DATA_FILE], [["s1", "1", "a.raw"], ["s1", "2", "b.raw"]])
        assert check_technical_replicates_have_distinct_files(parse_sdrf(content)) == []

    def test_two_replicates_in_one_file_are_reported(self):
        content = build([SRC, TECH, DATA_FILE], [["s1", "1", "a.raw"], ["s1", "2", "a.raw"]])
        assert [f.rule for f in check_technical_replicates_have_distinct_files(parse_sdrf(content))] == [
            "technical-replicates-share-a-file"
        ]

    def test_one_replicate_across_many_files_is_fine(self):
        """Fractions of one injection share a replicate index and that is correct."""
        content = build([SRC, TECH, DATA_FILE], [["s1", "1", "f1.raw"], ["s1", "1", "f2.raw"]])
        assert check_technical_replicates_have_distinct_files(parse_sdrf(content)) == []

    def test_missing_data_file_column_is_silent(self):
        content = build([SRC, TECH], [["s1", "1"], ["s1", "2"]])
        assert check_technical_replicates_have_distinct_files(parse_sdrf(content)) == []


class TestCharacteristicsAreBare:
    """A sample property is a bare value; NT=/AC= belongs to comment[...] columns."""

    def test_bare_label_is_fine(self):
        content = build([SRC, "characteristics[organism part]"], [["s1", "colon"]])
        assert check_characteristics_are_bare(parse_sdrf(content)) == []

    def test_nt_ac_pair_is_reported(self):
        content = build([SRC, "characteristics[organism part]"], [["s1", "NT=colon;AC=UBERON:0001155"]])
        findings = check_characteristics_are_bare(parse_sdrf(content))
        assert [f.rule for f in findings] == ["characteristics-uses-nt-ac"]

    def test_accession_alone_is_fine(self):
        """characteristics[cellosaurus accession] is the identifier itself."""
        content = build([SRC, "characteristics[cellosaurus accession]"], [["s1", "CVCL_0030"]])
        assert check_characteristics_are_bare(parse_sdrf(content)) == []

    def test_pooled_sample_keys_are_untouched(self):
        content = build([SRC, "characteristics[pooled sample]"], [["s1", "SN=HeLa;SN=liver tissue"]])
        assert check_characteristics_are_bare(parse_sdrf(content)) == []

    def test_spiked_compound_keys_are_untouched(self):
        content = build([SRC, "characteristics[spiked compound]"], [["s1", "CT=mixture;QY=1 fmol"]])
        assert check_characteristics_are_bare(parse_sdrf(content)) == []

    def test_comment_columns_are_not_checked(self):
        """comment[...] is exactly where the NT=/AC= form belongs."""
        content = build([SRC, "comment[instrument]"], [["s1", "NT=Q Exactive;AC=MS:1001911"]])
        assert check_characteristics_are_bare(parse_sdrf(content)) == []

    def test_one_finding_per_column(self):
        content = build(
            [SRC, "characteristics[disease]"],
            [["s1", "NT=colon carcinoma;AC=MONDO:0002032"], ["s2", "NT=healthy;AC=PATO:0000461"]],
        )
        findings = check_characteristics_are_bare(parse_sdrf(content))
        assert len(findings) == 1
        assert "2 value(s)" in findings[0].message

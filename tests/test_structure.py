"""Tests for the structural invariant checks."""

from tools.structure import (
    acquisition_family,
    check_factor_values_last,
    check_one_template_per_cell,
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

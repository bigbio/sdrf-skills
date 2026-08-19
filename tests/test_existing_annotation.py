"""Tests for tools.existing_annotation — auditing an already-annotated dataset."""

from __future__ import annotations

from tools.existing_annotation import BLOCKER, MAJOR, MINOR, audit

HEADER = (
    "source name\tcharacteristics[organism]\tcharacteristics[disease]\t"
    "assay name\tcomment[instrument]\tcomment[dissociation method]\t"
    "comment[fraction identifier]\tcomment[technical replicate]\t"
    "comment[data file]\tfactor value[phenotype]"
)


def _sdrf(rows: list[str], header: str = HEADER) -> str:
    return header + "\n" + "\n".join(rows) + "\n"


def _row(src, org, disease, assay, instr, diss, frac, tech, dfile, factor):
    fields = (src, org, disease, assay, instr, diss, frac, tech, dfile, factor)
    return "\t".join(fields)


GOOD = _sdrf([
    _row("PXD1-Sample-1", "Homo sapiens", "normal", "r1",
         "NT=Orbitrap Fusion Lumos;AC=MS:1002732",
         "NT=beam-type collision-induced dissociation;AC=MS:1000422",
         "1", "1", "r1.raw", "control"),
    _row("PXD1-Sample-1", "Homo sapiens", "normal", "r2",
         "NT=Orbitrap Fusion Lumos;AC=MS:1002732",
         "NT=beam-type collision-induced dissociation;AC=MS:1000422",
         "1", "2", "r2.raw", "control"),
    _row("PXD1-Sample-2", "Homo sapiens", "normal", "r3",
         "NT=Orbitrap Fusion Lumos;AC=MS:1002732",
         "NT=beam-type collision-induced dissociation;AC=MS:1000422",
         "1", "1", "r3.raw", "treated"),
])


class TestCleanAnnotation:
    def test_no_findings_when_consistent(self):
        report = audit(GOOD, deposited_runs=["r1.raw", "r2.raw", "r3.raw"],
                       pride_organisms=["Homo sapiens (human)"], accession="PXD1")
        assert report.clean, report.render()
        assert report.recommendation == "leave"
        assert report.n_rows == 3

    def test_checks_are_skipped_not_guessed_when_context_missing(self):
        """No deposit info supplied -> no coverage/organism findings invented."""
        report = audit(GOOD, accession="PXD1")
        codes = {f.code for f in report.findings}
        assert "missing_runs" not in codes
        assert "organism_mismatch" not in codes


class TestCoverage:
    def test_detects_missing_runs(self):
        report = audit(GOOD, deposited_runs=["r1.raw", "r2.raw", "r3.raw", "r4.raw"],
                       accession="PXD1")
        f = next(f for f in report.findings if f.code == "missing_runs")
        assert f.severity == BLOCKER
        assert "r4.raw" in f.evidence
        assert report.recommendation == "reannotate"

    def test_detects_invented_runs(self):
        report = audit(GOOD, deposited_runs=["r1.raw", "r2.raw"], accession="PXD1")
        assert any(f.code == "invented_runs" and f.severity == BLOCKER
                   for f in report.findings)


class TestOrganism:
    def test_detects_unrepresented_organism(self):
        """The PXD017812 case: a 3-species mixture annotated as one species."""
        report = audit(
            GOOD,
            deposited_runs=["r1.raw", "r2.raw", "r3.raw"],
            pride_organisms=["Homo sapiens (human)", "Saccharomyces cerevisiae",
                             "Escherichia coli"],
            accession="PXD1",
        )
        f = next(f for f in report.findings if f.code == "organism_mismatch")
        assert f.severity == BLOCKER
        assert "saccharomyces cerevisiae" in f.evidence
        assert "escherichia coli" in f.evidence

    def test_parenthetical_common_name_does_not_trip_it(self):
        report = audit(GOOD, pride_organisms=["Homo sapiens (human)"], accession="PXD1")
        assert not any(f.code == "organism_mismatch" for f in report.findings)


class TestCounterAbuse:
    def test_detects_technical_replicate_used_as_row_index(self):
        rows = [
            _row(f"S{i}", "Homo sapiens", "normal", f"r{i}", "NT=x;AC=MS:1", "NT=y;AC=MS:2",
                 "1", str(i), f"r{i}.raw", "c")
            for i in range(1, 6)
        ]
        report = audit(_sdrf(rows))
        f = next(f for f in report.findings if f.code == "counter_abuse")
        assert f.severity == MAJOR
        assert "comment[technical replicate]" in f.summary

    def test_legitimate_replicate_numbering_is_not_flagged(self):
        assert not any(f.code == "counter_abuse" for f in audit(GOOD).findings)


class TestMalformedTerms:
    def test_detects_nt_without_accession(self):
        rows = [_row("PXD1-Sample-1", "Homo sapiens", "normal", "r1",
                     "NT=Orbitrap Fusion Lumos;AC=MS:1002732", "NT=HCD",
                     "1", "1", "r1.raw", "c")]
        report = audit(_sdrf(rows))
        f = next(f for f in report.findings if f.code == "cv_term_no_accession")
        assert f.severity == MAJOR


class TestStructure:
    def test_detects_missing_factor_value(self):
        header = HEADER.replace("\tfactor value[phenotype]", "")
        rows = [_row("PXD1-Sample-1", "Homo sapiens", "normal", "r1", "NT=x;AC=MS:1",
                     "NT=y;AC=MS:2", "1", "1", "r1.raw", "c").rsplit("\t", 1)[0]]
        report = audit(_sdrf(rows, header=header))
        assert any(f.code == "no_factor_value" for f in report.findings)

    def test_empty_file_is_a_blocker(self):
        report = audit("")
        assert report.findings[0].severity == BLOCKER


class TestConventions:
    def test_detects_ntac_in_characteristics(self):
        rows = [_row("PXD1-Sample-1", "NT=Homo sapiens;AC=NCBITaxon:9606", "normal", "r1",
                     "NT=x;AC=MS:1", "NT=y;AC=MS:2", "1", "1", "r1.raw", "c")]
        report = audit(_sdrf(rows))
        f = next(f for f in report.findings if f.code == "characteristics_not_bare_label")
        assert f.severity == MINOR

    def test_detects_source_name_convention_drift(self):
        rows = [_row("Saccharomyces_cerevisiae_1", "Homo sapiens", "normal", "r1",
                     "NT=x;AC=MS:1", "NT=y;AC=MS:2", "1", "1", "r1.raw", "c")]
        report = audit(_sdrf(rows), accession="PXD1")
        assert any(f.code == "source_name_convention" for f in report.findings)

    def test_convention_drift_alone_recommends_fix_not_reannotate(self):
        rows = [_row("Saccharomyces_cerevisiae_1", "NT=Homo sapiens;AC=NCBITaxon:9606",
                     "normal", "r1", "NT=x;AC=MS:1", "NT=y;AC=MS:2", "1", "1",
                     "r1.raw", "c")]
        report = audit(_sdrf(rows), accession="PXD1")
        assert not report.blockers
        assert report.recommendation == "fix"


class TestProvenanceColumnsAreNotOntologyTerms:
    """Regression: comment[sdrf template]/[sdrf annotation tool] use NT=..;VV=..
    and legitimately carry no AC= accession. An earlier version of the audit
    flagged every correctly-annotated file because of this."""

    def test_template_and_tool_columns_are_exempt(self):
        header = HEADER + "\tcomment[sdrf template]\tcomment[sdrf annotation tool]"
        rows = [_row("PXD1-Sample-1", "Homo sapiens", "normal", "r1",
                     "NT=Orbitrap Fusion Lumos;AC=MS:1002732",
                     "NT=beam-type collision-induced dissociation;AC=MS:1000422",
                     "1", "1", "r1.raw", "c")
                + "\tNT=ms-proteomics;VV=v1.1.0\tNT=sdrf-skills;VV=v0.2.0"]
        report = audit(_sdrf(rows, header=header), accession="PXD1")
        assert not any(f.code == "cv_term_no_accession" for f in report.findings), \
            report.render()

    def test_a_real_missing_accession_is_still_caught(self):
        rows = [_row("PXD1-Sample-1", "Homo sapiens", "normal", "r1",
                     "NT=Orbitrap Fusion Lumos;AC=MS:1002732", "NT=HCD",
                     "1", "1", "r1.raw", "c")]
        report = audit(_sdrf(rows), accession="PXD1")
        assert any(f.code == "cv_term_no_accession" for f in report.findings)


class TestReviewFindings:
    """Regression tests for the review feedback on PR #46."""

    def test_utf8_bom_does_not_silently_disable_checks(self):
        """A BOM turned 'source name' into '﻿source name', so every column
        lookup missed and the audit reported a clean file."""
        report = audit("﻿" + GOOD, deposited_runs=["r1.raw", "r9.raw"],
                       accession="PXD1")
        assert any(f.code == "missing_runs" for f in report.findings), report.render()

    def test_blank_data_file_is_not_reported_as_an_invented_run(self):
        rows = [
            _row("PXD1-Sample-1", "Homo sapiens", "normal", "r1", "NT=x;AC=MS:1",
                 "NT=y;AC=MS:2", "1", "1", "r1.raw", "c"),
            _row("PXD1-Sample-2", "Homo sapiens", "normal", "r2", "NT=x;AC=MS:1",
                 "NT=y;AC=MS:2", "1", "1", "", "c"),
        ]
        report = audit(_sdrf(rows), deposited_runs=["r1.raw"], accession="PXD1")
        assert any(f.code == "blank_data_file" for f in report.findings)
        assert not any(f.code == "invented_runs" for f in report.findings)

    def test_surrounding_whitespace_does_not_double_report(self):
        rows = [_row("PXD1-Sample-1", "Homo sapiens", "normal", "r1", "NT=x;AC=MS:1",
                     "NT=y;AC=MS:2", "1", "1", "  r1.raw  ", "c")]
        report = audit(_sdrf(rows), deposited_runs=["r1.raw"], accession="PXD1")
        assert not any(f.code in ("missing_runs", "invented_runs") for f in report.findings)

    def test_evidence_supplied_but_data_file_column_absent_is_reported(self):
        header = HEADER.replace("\tcomment[data file]", "")
        cells = ("PXD1-Sample-1", "Homo sapiens", "normal", "r1",
                 "NT=x;AC=MS:1", "NT=y;AC=MS:2", "1", "1", "c")
        rows = ["\t".join(cells)]
        report = audit(_sdrf(rows, header=header), deposited_runs=["r1.raw"],
                       accession="PXD1")
        f = next(f for f in report.findings if f.code == "no_data_file_column")
        assert f.severity == BLOCKER
        assert report.recommendation == "reannotate"

    def test_evidence_supplied_but_organism_column_absent_is_reported(self):
        header = HEADER.replace("characteristics[organism]\t", "")
        cells = ("PXD1-Sample-1", "normal", "r1", "NT=x;AC=MS:1",
                 "NT=y;AC=MS:2", "1", "1", "r1.raw", "c")
        rows = ["\t".join(cells)]
        report = audit(_sdrf(rows, header=header), pride_organisms=["Homo sapiens"],
                       accession="PXD1")
        assert any(f.code == "no_organism_column" and f.severity == BLOCKER
                   for f in report.findings)

    def test_vv_on_a_real_cv_column_is_not_exempt(self):
        """Only the named provenance columns are exempt — a VV= anywhere else
        must not excuse a missing accession."""
        rows = [_row("PXD1-Sample-1", "Homo sapiens", "normal", "r1",
                     "NT=Some Instrument;VV=v1", "NT=y;AC=MS:2", "1", "1",
                     "r1.raw", "c")]
        report = audit(_sdrf(rows), accession="PXD1")
        assert any(f.code == "cv_term_no_accession" for f in report.findings)

    def test_empty_accession_value_is_not_an_accession(self):
        rows = [_row("PXD1-Sample-1", "Homo sapiens", "normal", "r1",
                     "NT=Some Instrument;AC=", "NT=y;AC=MS:2", "1", "1", "r1.raw", "c")]
        report = audit(_sdrf(rows), accession="PXD1")
        assert any(f.code == "cv_term_no_accession" for f in report.findings)

    def test_source_name_suffix_must_be_numeric(self):
        for bad in ("PXD1-Sample-abc", "PXD1-Sample-"):
            rows = [_row(bad, "Homo sapiens", "normal", "r1", "NT=x;AC=MS:1",
                         "NT=y;AC=MS:2", "1", "1", "r1.raw", "c")]
            report = audit(_sdrf(rows), accession="PXD1")
            assert any(f.code == "source_name_convention" for f in report.findings), bad

    def test_accession_is_regex_escaped(self):
        """A '.' in the accession must not act as a wildcard."""
        rows = [_row("PXDx1-Sample-1", "Homo sapiens", "normal", "r1", "NT=x;AC=MS:1",
                     "NT=y;AC=MS:2", "1", "1", "r1.raw", "c")]
        report = audit(_sdrf(rows), accession="PXD.1")
        assert any(f.code == "source_name_convention" for f in report.findings)


class TestRunNameSuffixMismatch:
    """PRIDE ships Bruker `.d` directories zipped; the SDRF names the `.d`.

    Regression test: a deposited-run list taken straight from the PRIDE file
    listing put every run in BOTH `missing_runs` and `invented_runs`, emitting
    2N blockers that read like a wrong annotation and invite a caller to
    "repair" a correct SDRF.
    """

    @staticmethod
    def _sdrf(runs):
        head = "source name\tcomment[data file]\tfactor value[disease]\n"
        return head + "".join(f"PXD1-Sample-1\t{r}\tnormal\n" for r in runs)

    def test_zip_suffix_mismatch_reported_once(self):
        annotated = ["a_1.d", "b_2.d", "c_3.d"]
        deposited = [f"{r}.zip" for r in annotated]
        report = audit(self._sdrf(annotated), deposited_runs=deposited)
        codes = [f.code for f in report.findings]
        assert "run_name_suffix_mismatch" in codes
        assert "missing_runs" not in codes
        assert "invented_runs" not in codes
        assert sum(c == "run_name_suffix_mismatch" for c in codes) == 1

    def test_identical_sets_produce_no_finding(self):
        runs = ["a_1.d", "b_2.d"]
        report = audit(self._sdrf(runs), deposited_runs=runs)
        codes = [f.code for f in report.findings]
        assert "run_name_suffix_mismatch" not in codes
        assert "missing_runs" not in codes
        assert "invented_runs" not in codes

    def test_genuine_mismatch_still_blocks(self):
        """A real coverage error must not be excused as a suffix mismatch."""
        report = audit(self._sdrf(["a_1.d"]), deposited_runs=["a_1.d", "b_2.d"])
        codes = [f.code for f in report.findings]
        assert "missing_runs" in codes
        assert "run_name_suffix_mismatch" not in codes

    def test_partial_suffix_mismatch_still_blocks(self):
        """Only a wholesale suffix mismatch is benign."""
        report = audit(self._sdrf(["a_1.d", "b_2.d"]),
                       deposited_runs=["a_1.d.zip", "c_3.d.zip"])
        codes = [f.code for f in report.findings]
        assert "run_name_suffix_mismatch" not in codes
        assert "missing_runs" in codes and "invented_runs" in codes

    def test_collapsing_names_are_not_treated_as_suffix_mismatch(self):
        """Two distinct runs must not collapse onto one stripped name."""
        report = audit(self._sdrf(["x.d", "x.d.zip"]),
                       deposited_runs=["x.d.zip", "x.d.zip.zip"])
        codes = [f.code for f in report.findings]
        assert "run_name_suffix_mismatch" not in codes

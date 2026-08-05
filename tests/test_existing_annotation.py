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

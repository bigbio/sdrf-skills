"""Tests for tools.hallucination — ontology hallucination detector."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.hallucination import (
    HallucinationReport,
    detect_hallucinations,
    _check_unimod_swap,
    _check_modification_cell,
)
from tools.ols_client import OLSClient, OLSTerm, VerificationResult


class TestUnimodSwapDetection:
    """Test offline UNIMOD swap detection (no API calls needed)."""

    def test_acetyl_phospho_swap(self):
        """UNIMOD:21 labeled 'Acetyl' is the #1 most common error."""
        swap = _check_unimod_swap("UNIMOD:21", "Acetyl")
        assert swap is not None
        assert swap.correct_accession == "UNIMOD:1"
        assert swap.correct_name == "Acetyl"

    def test_phospho_acetyl_swap(self):
        swap = _check_unimod_swap("UNIMOD:1", "Phospho")
        assert swap is not None
        assert swap.correct_accession == "UNIMOD:21"

    def test_oxidation_methyl_swap(self):
        swap = _check_unimod_swap("UNIMOD:34", "Oxidation")
        assert swap is not None
        assert swap.correct_accession == "UNIMOD:35"

    def test_methyl_oxidation_swap(self):
        swap = _check_unimod_swap("UNIMOD:35", "Methyl")
        assert swap is not None
        assert swap.correct_accession == "UNIMOD:34"

    def test_correct_acetyl_no_swap(self):
        swap = _check_unimod_swap("UNIMOD:1", "Acetyl")
        assert swap is None

    def test_correct_phospho_no_swap(self):
        swap = _check_unimod_swap("UNIMOD:21", "Phospho")
        assert swap is None

    def test_correct_oxidation_no_swap(self):
        swap = _check_unimod_swap("UNIMOD:35", "Oxidation")
        assert swap is None

    def test_unknown_accession_wrong_name(self):
        """Known accession with wrong name (not a swap pair)."""
        swap = _check_unimod_swap("UNIMOD:4", "Phospho")
        assert swap is not None
        assert swap.correct_name == "Carbamidomethyl"


class TestModificationCellCheck:
    def test_correct_mod(self):
        verified, swaps, warnings = _check_modification_cell(
            "NT=Carbamidomethyl;AC=UNIMOD:4;TA=C;MT=Fixed",
            "comment[modification parameters]",
            [1],
        )
        assert len(verified) == 1
        assert len(swaps) == 0
        assert verified[0].accession == "UNIMOD:4"

    def test_swap_detected(self):
        verified, swaps, warnings = _check_modification_cell(
            "NT=Acetyl;AC=UNIMOD:21;PP=Protein N-term;MT=Variable",
            "comment[modification parameters]",
            [3],
        )
        assert len(swaps) == 1
        assert swaps[0].wrong_accession == "UNIMOD:21"
        assert swaps[0].correct_accession == "UNIMOD:1"
        assert swaps[0].rows == [3]

    def test_wrong_mt_value(self):
        verified, swaps, warnings = _check_modification_cell(
            "NT=Oxidation;AC=UNIMOD:35;TA=M;MT=variable",
            "comment[modification parameters]",
            [1],
        )
        assert any("MT=" in w for w in warnings)

    def test_ta_looks_like_pp(self):
        verified, swaps, warnings = _check_modification_cell(
            "NT=Acetyl;AC=UNIMOD:1;TA=Protein N-term;MT=Variable",
            "comment[modification parameters]",
            [1],
        )
        assert any("PP=" in w for w in warnings)


class TestDetectHallucinationsOffline:
    """Test hallucination detection with offline mode (no OLS calls)."""

    def test_synthetic_sdrf_unimod_swaps(self, synthetic_sdrf_path: Path):
        """The synthetic SDRF has deliberate UNIMOD swap errors."""
        report = detect_hallucinations(
            synthetic_sdrf_path, verify_online=False
        )
        assert isinstance(report, HallucinationReport)
        # Row 3 has UNIMOD:21 for Acetyl (should be UNIMOD:1)
        assert len(report.unimod_swaps) >= 1
        swap_accessions = {s.wrong_accession for s in report.unimod_swaps}
        assert "UNIMOD:21" in swap_accessions

    def test_synthetic_sdrf_oxidation_swap(self, synthetic_sdrf_path: Path):
        """Row 6 has UNIMOD:34 for Oxidation (should be UNIMOD:35)."""
        report = detect_hallucinations(
            synthetic_sdrf_path, verify_online=False
        )
        oxidation_swaps = [
            s for s in report.unimod_swaps
            if s.wrong_accession == "UNIMOD:34"
        ]
        assert len(oxidation_swaps) >= 1

    def test_correct_mods_verified(self, synthetic_sdrf_path: Path):
        report = detect_hallucinations(
            synthetic_sdrf_path, verify_online=False
        )
        # Carbamidomethyl (UNIMOD:4) and Oxidation (UNIMOD:35) should be verified
        verified_accessions = {v.accession for v in report.verified}
        assert "UNIMOD:4" in verified_accessions

    def test_summary_output(self, synthetic_sdrf_path: Path):
        report = detect_hallucinations(
            synthetic_sdrf_path, verify_online=False
        )
        summary = report.summary()
        assert "Hallucination Report" in summary
        assert "UNIMOD swaps" in summary

    def test_report_not_clean_with_swaps(self, synthetic_sdrf_path: Path):
        report = detect_hallucinations(
            synthetic_sdrf_path, verify_online=False
        )
        assert not report.is_clean

    def test_minimal_sdrf_is_clean(self, minimal_sdrf_content: str):
        """Minimal SDRF with no ontology columns should be clean."""
        report = detect_hallucinations(
            minimal_sdrf_content, verify_online=False
        )
        assert report.is_clean


class TestDetectHallucinationsOnline:
    """Test with mocked OLS client."""

    def test_verified_term(self):
        mock_client = MagicMock(spec=OLSClient)
        mock_client.search_term.return_value = [
            OLSTerm(
                iri="http://purl.obolibrary.org/obo/NCBITaxon_9606",
                label="Homo sapiens",
                short_form="NCBITaxon:9606",
                ontology_name="ncbitaxon",
            )
        ]

        sdrf_content = (
            "source name\tcharacteristics[organism]\n"
            "s1\tHomo sapiens\n"
        )
        report = detect_hallucinations(
            sdrf_content, ols_client=mock_client, verify_online=True
        )
        assert len(report.verified) == 1
        assert report.verified[0].label == "Homo sapiens"

    def test_hallucinated_term(self):
        mock_client = MagicMock(spec=OLSClient)
        mock_client.search_term.return_value = []

        sdrf_content = (
            "source name\tcharacteristics[organism]\n"
            "s1\tFake organism\n"
        )
        report = detect_hallucinations(
            sdrf_content, ols_client=mock_client, verify_online=True
        )
        assert len(report.hallucinated) == 1
        assert report.hallucinated[0].label == "Fake organism"

    def test_synonym_match_not_hallucinated(self):
        """A term found via synonym must not be reported as hallucinated.

        Mirrors the 'HeLa S3' vs 'HeLa-S3' class of false positives: the SDRF
        value matches a synonym rather than the OLS primary label.
        """
        mock_client = MagicMock(spec=OLSClient)
        # OLS primary label differs (hyphen vs space) but SDRF value is a synonym
        mock_client.search_term.return_value = [
            OLSTerm(
                iri="http://www.ebi.ac.uk/efo/EFO_0002791",
                label="HeLa-S3",          # primary label uses hyphen
                short_form="EFO:0002791",
                ontology_name="efo",
                synonyms=["HeLa S3"],     # SDRF value matches this synonym
            )
        ]

        sdrf_content = (
            "source name\tcharacteristics[cell line]\n"
            "s1\tHeLa S3\n"
        )
        report = detect_hallucinations(
            sdrf_content, ols_client=mock_client, verify_online=True
        )
        assert len(report.hallucinated) == 0, (
            "Term found via synonym should not be reported as hallucinated"
        )
        assert len(report.verified) == 1
        assert report.verified[0].label == "HeLa S3"


class TestStructuredCVColumns:
    """comment[...] CV columns are written NT=<label>;AC=<accession>.

    Regression tests: these columns were routed to the bare-label checker,
    which searched OLS for the literal cell string and always missed, so every
    value was reported as hallucinated.
    """

    @staticmethod
    def _client():
        client = MagicMock(spec=OLSClient)
        client.verify_accession.return_value = VerificationResult(
            accession="MS:1002038",
            expected_label="label free sample",
            exists=True,
            resolved_term=OLSTerm(
                iri="http://purl.obolibrary.org/obo/MS_1002038",
                label="label free sample",
                short_form="MS:1002038",
                ontology_name="ms",
            ),
            label_match=True,
        )
        return client

    def test_label_column_not_hallucinated(self):
        client = self._client()
        sdrf = (
            "source name\tcomment[label]\n"
            "s1\tNT=label free sample;AC=MS:1002038\n"
        )
        report = detect_hallucinations(sdrf, ols_client=client, verify_online=True)
        assert report.hallucinated == []
        assert len(report.verified) == 1
        assert report.verified[0].accession == "MS:1002038"

    def test_dissociation_method_not_hallucinated(self):
        client = self._client()
        client.verify_accession.return_value = VerificationResult(
            accession="MS:1000133",
            expected_label="collision-induced dissociation",
            exists=True,
            resolved_term=OLSTerm(
                iri="http://purl.obolibrary.org/obo/MS_1000133",
                label="collision-induced dissociation",
                short_form="MS:1000133",
                ontology_name="ms",
            ),
            label_match=True,
        )
        sdrf = (
            "source name\tcomment[dissociation method]\n"
            "s1\tNT=collision-induced dissociation;AC=MS:1000133\n"
        )
        report = detect_hallucinations(sdrf, ols_client=client, verify_online=True)
        assert report.hallucinated == []
        assert len(report.verified) == 1

    def test_structured_value_in_unmapped_column_is_checked(self):
        """A column outside COLUMN_ONTOLOGY_MAP still gets verified when its
        values carry AC= — e.g. comment[cross-linker] (XLMOD)."""
        client = MagicMock(spec=OLSClient)
        client.verify_accession.return_value = VerificationResult(
            accession="XLMOD:02126",
            expected_label="DSSO",
            exists=True,
            resolved_term=OLSTerm(
                iri="http://purl.obolibrary.org/obo/XLMOD_02126",
                label="DSSO",
                short_form="XLMOD:02126",
                ontology_name="xlmod",
            ),
            label_match=True,
        )
        sdrf = (
            "source name\tcomment[cross-linker]\n"
            "s1\tNT=DSSO;AC=XLMOD:02126\n"
        )
        report = detect_hallucinations(sdrf, ols_client=client, verify_online=True)
        assert report.total_terms_checked == 1
        assert report.hallucinated == []

    def test_provenance_column_without_accession_is_skipped(self):
        """comment[sdrf template] uses NT=..;VV=.. and carries no accession,
        so it must not be treated as a CV column."""
        client = MagicMock(spec=OLSClient)
        sdrf = (
            "source name\tcomment[sdrf template]\n"
            "s1\tNT=ms-proteomics;VV=v1.1.0\n"
        )
        report = detect_hallucinations(sdrf, ols_client=client, verify_online=True)
        assert report.total_terms_checked == 0
        assert report.hallucinated == []
        client.verify_accession.assert_not_called()

    def test_reserved_words_do_not_decide_column_style(self):
        """A leading 'not applicable' must not make the column look bare-label."""
        client = self._client()
        sdrf = (
            "source name\tcomment[label]\n"
            "s1\tnot applicable\n"
            "s2\tNT=label free sample;AC=MS:1002038\n"
        )
        report = detect_hallucinations(sdrf, ols_client=client, verify_online=True)
        assert report.hallucinated == []
        assert len(report.verified) == 1

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
    _modification_label_matches,
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


class TestModificationLabelMatching:
    """The NT/AC pair must name the same modification.

    Tuned against every NT/AC pair in bigbio/sdrf-annotated-datasets: the
    accept rules below cover 98.3% of rows, and each rejected pair inspected
    named a genuinely different chemistry.
    """

    def test_exact(self):
        assert _modification_label_matches("Oxidation", "Oxidation", "UNIMOD:35")

    def test_case_and_punctuation_insensitive(self):
        assert _modification_label_matches("deamidated", "Deamidated", "UNIMOD:7")
        assert _modification_label_matches("Gln->pyro-Glu", "Gln->pyro Glu", "UNIMOD:28")

    def test_abbreviation_is_substring(self):
        assert _modification_label_matches("TMT", "TMT6plex", "UNIMOD:737")
        assert _modification_label_matches("iTRAQ", "iTRAQ4plex", "UNIMOD:214")

    def test_process_name_vs_residue_name(self):
        assert _modification_label_matches("Phosphorylation", "Phospho", "UNIMOD:21")
        assert _modification_label_matches("Deamidation", "Deamidated", "UNIMOD:7")

    def test_multiname_accession(self):
        """UNIMOD:737 is one term for TMT6/10/11plex."""
        assert _modification_label_matches("TMT10plex", "TMT6plex", "UNIMOD:737")

    def test_different_chemistry_rejected(self):
        assert not _modification_label_matches("Oxidation", "Dimethyl", "UNIMOD:36")
        assert not _modification_label_matches("Oxidation", "Methylthio", "UNIMOD:39")
        assert not _modification_label_matches("Acetyl", "Amidated", "UNIMOD:2")
        assert not _modification_label_matches("Carbamidomethyl", "Asp->Cys", "UNIMOD:1067")
        assert not _modification_label_matches("Ubiquitination", "Label:2H(4)+GG", "UNIMOD:853")

    def test_swapped_pyro_glu_pair_rejected(self):
        """Gln->pyro-Glu is UNIMOD:28; UNIMOD:27 is Glu->pyro-Glu."""
        assert not _modification_label_matches("Gln->pyro-Glu", "Glu->pyro-Glu", "UNIMOD:27")

    def test_multiname_does_not_leak_to_other_accessions(self):
        assert not _modification_label_matches("TMT10plex", "Oxidation", "UNIMOD:35")

    def test_isotope_label_prefix_omitted(self):
        """UNIMOD prefixes isotope labels with 'Label:'; SDRFs often omit it."""
        assert _modification_label_matches("13C6-15N4", "Label:13C(6)15N(4)", "UNIMOD:267")

    def test_containment_alone_must_not_accept(self):
        """The swaps this check exists to catch are all substring-related."""
        assert not _modification_label_matches("Trimethyl", "Methyl", "UNIMOD:34")
        assert not _modification_label_matches("Carbamidomethyl", "Methyl", "UNIMOD:34")
        assert not _modification_label_matches("Acetyl", "Pyridylacetyl", "UNIMOD:25")
        assert not _modification_label_matches(
            "Carbamidomethyl", "Pyro-carbamidomethyl", "UNIMOD:26")

    def test_isotope_labels_are_not_prefix_matched(self):
        """13C(6) is a prefix of 13C(6)15N(2) but a different label."""
        assert not _modification_label_matches(
            "Label:13C(6)", "Label:13C(6)15N(2)", "UNIMOD:259")


class TestModificationAccessionCrossCheck:
    """Online NT<->AC verification for comment[modification parameters]."""

    @staticmethod
    def _sdrf(value):
        return ("source name\tcomment[modification parameters]\n"
                f"s1\t{value}\n")

    @staticmethod
    def _client(term):
        c = MagicMock(spec=OLSClient)
        c.resolve_accession.return_value = term
        return c

    def test_nonexistent_accession_is_hallucinated(self):
        client = self._client(None)
        report = detect_hallucinations(
            self._sdrf("NT=Acetyl;AC=UNIMOD:67;TA=K;MT=Variable"),
            ols_client=client, verify_online=True)
        assert len(report.hallucinated) == 1
        assert report.hallucinated[0].accession == "UNIMOD:67"

    def test_accession_naming_other_chemistry_is_mismatch(self):
        client = self._client(OLSTerm(
            iri="", label="Asp->Cys", short_form="UNIMOD:1067",
            ontology_name="unimod"))
        report = detect_hallucinations(
            self._sdrf("NT=Carbamidomethyl;AC=UNIMOD:1067;TA=C;MT=Fixed"),
            ols_client=client, verify_online=True)
        assert len(report.mismatched) == 1
        assert report.mismatched[0].actual_label == "Asp->Cys"
        assert report.hallucinated == []

    def test_variant_spelling_is_verified_not_flagged(self):
        client = self._client(OLSTerm(
            iri="", label="Deamidated", short_form="UNIMOD:7",
            ontology_name="unimod"))
        report = detect_hallucinations(
            self._sdrf("NT=Deamidation;AC=UNIMOD:7;TA=N,Q;MT=Variable"),
            ols_client=client, verify_online=True)
        assert report.mismatched == [] and report.hallucinated == []
        assert any(v.accession == "UNIMOD:7" for v in report.verified)

    def test_offline_mode_makes_no_calls(self):
        client = MagicMock(spec=OLSClient)
        report = detect_hallucinations(
            self._sdrf("NT=Carbamidomethyl;AC=UNIMOD:1067;TA=C;MT=Fixed"),
            ols_client=client, verify_online=False)
        client.resolve_accession.assert_not_called()
        assert report.mismatched == [] and report.hallucinated == []

    def test_known_swap_is_not_double_reported(self):
        """The offline swap check already names the correct accession."""
        client = self._client(OLSTerm(
            iri="", label="Phospho", short_form="UNIMOD:21",
            ontology_name="unimod"))
        report = detect_hallucinations(
            self._sdrf("NT=Acetyl;AC=UNIMOD:21;TA=K;MT=Variable"),
            ols_client=client, verify_online=True)
        assert len(report.unimod_swaps) == 1
        assert report.mismatched == [] and report.hallucinated == []

    def test_correct_pair_stays_clean(self):
        client = self._client(OLSTerm(
            iri="", label="Carbamidomethyl", short_form="UNIMOD:4",
            ontology_name="unimod"))
        report = detect_hallucinations(
            self._sdrf("NT=Carbamidomethyl;AC=UNIMOD:4;TA=C;MT=Fixed"),
            ols_client=client, verify_online=True)
        assert report.is_clean

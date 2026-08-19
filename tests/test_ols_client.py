"""Tests for tools.ols_client payload normalisation."""

from __future__ import annotations

from tools.ols_client import OLSClient, _collect_synonyms, _labels_match


class TestCollectSynonyms:
    """OLS4 spells the synonym field three different ways.

    Regression tests: only ``synonyms`` was read, so every term resolved via
    the /search endpoint came back with an empty synonym list and any SDRF
    using a term's common name instead of its primary label was reported as a
    label mismatch.
    """

    def test_terms_endpoint_key(self):
        assert _collect_synonyms({"synonyms": ["DSBU"]}) == ["DSBU"]

    def test_search_default_key(self):
        """/search without fieldList returns 'exact_synonyms'."""
        doc = {"label": "BuUrBu", "exact_synonyms": ["DSBU", "NHS-BuUrBu-NHS"]}
        assert _collect_synonyms(doc) == ["DSBU", "NHS-BuUrBu-NHS"]

    def test_search_fieldlist_key(self):
        """/search with fieldList=...synonym returns 'synonym'."""
        assert _collect_synonyms({"synonym": ["DSBU"]}) == ["DSBU"]

    def test_keys_are_merged_and_deduped(self):
        doc = {"synonyms": ["DSBU"], "exact_synonyms": ["DSBU", "other"]}
        assert _collect_synonyms(doc) == ["DSBU", "other"]

    def test_missing_and_empty_are_safe(self):
        assert _collect_synonyms({}) == []
        assert _collect_synonyms({"synonyms": None}) == []
        assert _collect_synonyms({"exact_synonyms": []}) == []

    def test_scalar_string_is_wrapped(self):
        assert _collect_synonyms({"synonym": "DSBU"}) == ["DSBU"]

    def test_doc_to_term_populates_synonyms_from_search_payload(self):
        """The real failure: a /search doc lost its synonyms entirely."""
        doc = {
            "iri": "http://purl.obolibrary.org/obo/XLMOD_02120",
            "label": "BuUrBu",
            "obo_id": "XLMOD:02120",
            "ontology_name": "xlmod",
            "exact_synonyms": ["DSBU", "Disuccinimidyl dibutyric urea"],
        }
        term = OLSClient._doc_to_term(doc)
        assert "DSBU" in term.synonyms
        # DSBU is what an SDRF author writes; BuUrBu is the primary label.
        assert _labels_match("DSBU", term.label, term.synonyms)


class TestAccessionToIri:
    def test_xlmod_resolves_via_term_endpoint(self):
        """XLMOD was absent from the IRI map, forcing the search fallback."""
        iri = OLSClient._accession_to_iri("XLMOD:02120", "xlmod")
        assert iri == "http://purl.obolibrary.org/obo/XLMOD_02120"

    def test_unknown_ontology_returns_none(self):
        assert OLSClient._accession_to_iri("NOPE:0001", "nope") is None

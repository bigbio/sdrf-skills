"""HTTP client for the EBI OLS4 REST API.

Provides term search, verification, and hierarchy navigation with
in-memory caching and rate limiting for efficient SDRF validation.

API docs: https://www.ebi.ac.uk/ols4/swagger-ui/index.html
"""

from __future__ import annotations

import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Any

import requests

OLS4_BASE = "https://www.ebi.ac.uk/ols4/api"

# Default rate-limit: max 10 requests per second
_MIN_INTERVAL = 0.1


@dataclass
class OLSTerm:
    """A resolved ontology term from OLS."""
    iri: str
    label: str
    short_form: str         # e.g. "UNIMOD:1"
    ontology_name: str      # e.g. "unimod"
    description: str = ""
    synonyms: list[str] = field(default_factory=list)
    is_obsolete: bool = False


@dataclass
class VerificationResult:
    """Result of verifying an accession + label pair."""
    accession: str
    expected_label: str
    exists: bool
    resolved_term: OLSTerm | None = None
    label_match: bool = False
    message: str = ""


class OLSClient:
    """Client for EBI OLS4 with caching and rate limiting."""

    def __init__(self, base_url: str = OLS4_BASE, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers["Accept"] = "application/json"
        self._cache: dict[str, Any] = {}
        self._last_request_time = 0.0

    def _rate_limit(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - elapsed)
        self._last_request_time = time.time()

    def _get(self, endpoint: str, params: dict | None = None) -> dict:
        """Perform a cached, rate-limited GET request to OLS4."""
        cache_key = f"{self.base_url}{endpoint}|{params}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        self._rate_limit()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        resp = self._session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        self._cache[cache_key] = data
        return data

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_term(
        self,
        query: str,
        ontology_id: str | None = None,
        exact: bool = False,
        rows: int = 10,
    ) -> list[OLSTerm]:
        """Search for a term across OLS.

        Args:
            query: Search string.
            ontology_id: Restrict to a specific ontology (e.g. "ncbitaxon").
            exact: Require exact match.
            rows: Max results to return.
        """
        params: dict[str, Any] = {"q": query, "rows": rows}
        if ontology_id:
            params["ontology"] = ontology_id.lower()
        if exact:
            params["exact"] = "true"
        data = self._get("/search", params)
        results: list[OLSTerm] = []
        for doc in data.get("response", {}).get("docs", []):
            results.append(self._doc_to_term(doc))
        return results

    # ------------------------------------------------------------------
    # Get term by ontology + accession
    # ------------------------------------------------------------------

    def get_term_by_accession(self, accession: str) -> OLSTerm | None:
        """Resolve an accession like 'UNIMOD:1' or 'MS:1001911' to its OLS term.

        Constructs the appropriate IRI and queries OLS.
        """
        ontology_id, local_id = self._split_accession(accession)
        if not ontology_id:
            return None

        iri = self._accession_to_iri(accession, ontology_id)
        if not iri:
            return None

        encoded_iri = urllib.parse.quote(urllib.parse.quote(iri, safe=""))
        try:
            data = self._get(f"/ontologies/{ontology_id.lower()}/terms/{encoded_iri}")
        except requests.RequestException:
            return None

        return self._api_term_to_term(data)

    def get_term_by_search(self, accession: str) -> OLSTerm | None:
        """Fallback: search for an accession via the search endpoint."""
        ontology_id, _ = self._split_accession(accession)
        terms = self.search_term(accession, ontology_id=ontology_id, exact=True, rows=1)
        if terms:
            return terms[0]
        terms = self.search_term(accession, exact=False, rows=5)
        for t in terms:
            if t.short_form.upper() == accession.upper():
                return t
        return None

    def resolve_accession(self, accession: str) -> OLSTerm | None:
        """Try term lookup first, then search fallback."""
        term = self.get_term_by_accession(accession)
        if term:
            return term
        return self.get_term_by_search(accession)

    # ------------------------------------------------------------------
    # Verify accession + label pair
    # ------------------------------------------------------------------

    def verify_accession(self, accession: str, expected_label: str) -> VerificationResult:
        """Verify that an accession exists and its label matches.

        This is the core building block for hallucination detection.
        """
        term = self.resolve_accession(accession)
        if term is None:
            return VerificationResult(
                accession=accession,
                expected_label=expected_label,
                exists=False,
                message=f"Accession {accession} not found in OLS",
            )

        label_match = _labels_match(expected_label, term.label, term.synonyms)
        msg = ""
        if not label_match:
            msg = (
                f"Label mismatch: expected '{expected_label}', "
                f"OLS says '{term.label}'"
            )

        return VerificationResult(
            accession=accession,
            expected_label=expected_label,
            exists=True,
            resolved_term=term,
            label_match=label_match,
            message=msg,
        )

    # ------------------------------------------------------------------
    # Hierarchy navigation
    # ------------------------------------------------------------------

    def get_children(self, accession: str, rows: int = 20) -> list[OLSTerm]:
        """Get child terms for specificity checks."""
        ontology_id, _ = self._split_accession(accession)
        iri = self._accession_to_iri(accession, ontology_id or "")
        if not iri or not ontology_id:
            return []
        encoded_iri = urllib.parse.quote(urllib.parse.quote(iri, safe=""))
        try:
            data = self._get(
                f"/ontologies/{ontology_id.lower()}/terms/{encoded_iri}/children",
                params={"size": rows},
            )
        except requests.HTTPError:
            return []
        terms = []
        for item in data.get("_embedded", {}).get("terms", []):
            terms.append(self._api_term_to_term(item))
        return terms

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _split_accession(accession: str) -> tuple[str | None, str | None]:
        """Split 'UNIMOD:1' into ('unimod', '1')."""
        if ":" not in accession:
            return None, None
        parts = accession.split(":", 1)
        return parts[0].strip(), parts[1].strip()

    @staticmethod
    def _accession_to_iri(accession: str, ontology_id: str) -> str | None:
        """Convert an accession to its OLS IRI."""
        ont = ontology_id.lower()
        prefix, local = accession.split(":", 1)

        # Common IRI patterns
        iri_bases = {
            "ncbitaxon": f"http://purl.obolibrary.org/obo/NCBITaxon_{local}",
            "uberon": f"http://purl.obolibrary.org/obo/UBERON_{local}",
            "efo": f"http://www.ebi.ac.uk/efo/EFO_{local}",
            "mondo": f"http://purl.obolibrary.org/obo/MONDO_{local}",
            "cl": f"http://purl.obolibrary.org/obo/CL_{local}",
            "doid": f"http://purl.obolibrary.org/obo/DOID_{local}",
            "pato": f"http://purl.obolibrary.org/obo/PATO_{local}",
            "ms": f"http://purl.obolibrary.org/obo/MS_{local}",
            "unimod": f"http://www.unimod.org/obo/unimod#UNIMOD:{local}",
            "hancestro": f"http://purl.obolibrary.org/obo/HANCESTRO_{local}",
            "chebi": f"http://purl.obolibrary.org/obo/CHEBI_{local}",
            "bto": f"http://purl.obolibrary.org/obo/BTO_{local}",
            "pride": f"http://purl.obolibrary.org/obo/PRIDE_{local}",
        }
        return iri_bases.get(ont)

    @staticmethod
    def _doc_to_term(doc: dict) -> OLSTerm:
        """Convert an OLS search result doc to OLSTerm."""
        return OLSTerm(
            iri=doc.get("iri", ""),
            label=doc.get("label", ""),
            short_form=doc.get("short_form", doc.get("obo_id", "")),
            ontology_name=doc.get("ontology_name", ""),
            description=(doc.get("description") or [""])[0] if isinstance(doc.get("description"), list) else doc.get("description", ""),
            synonyms=doc.get("synonyms", []) or [],
            is_obsolete=doc.get("is_obsolete", False),
        )

    @staticmethod
    def _api_term_to_term(data: dict) -> OLSTerm:
        """Convert an OLS term API response to OLSTerm."""
        desc = data.get("description", [])
        if isinstance(desc, list):
            desc = desc[0] if desc else ""
        return OLSTerm(
            iri=data.get("iri", ""),
            label=data.get("label", ""),
            short_form=data.get("short_form", data.get("obo_id", "")),
            ontology_name=data.get("ontology_name", ""),
            description=desc,
            synonyms=data.get("synonyms", []) or [],
            is_obsolete=data.get("is_obsolete", False),
        )


# ---------------------------------------------------------------------------
# Label matching
# ---------------------------------------------------------------------------

def _labels_match(expected: str, actual: str, synonyms: list[str] | None = None) -> bool:
    """Check if an expected label matches the OLS term label or synonyms."""
    expected_norm = expected.strip().lower()
    if expected_norm == actual.strip().lower():
        return True
    if synonyms:
        for syn in synonyms:
            if expected_norm == syn.strip().lower():
                return True
    return False

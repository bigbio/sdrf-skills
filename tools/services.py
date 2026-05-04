"""External biological database clients for SDRF annotation enrichment.

Integrates with UniProt, Cellosaurus, BioSamples, and PRIDE REST APIs
to cross-validate and enrich metadata annotations.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import requests

_MIN_INTERVAL = 0.15  # rate limit between requests


# ---------------------------------------------------------------------------
# Base client
# ---------------------------------------------------------------------------

class _BaseClient:
    """Base HTTP client with caching and rate limiting."""

    def __init__(self, base_url: str, timeout: int = 30):
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

    def _get(self, endpoint: str, params: dict | None = None) -> dict | list:
        """Perform a cached, rate-limited GET request."""
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


# ---------------------------------------------------------------------------
# Cellosaurus client
# ---------------------------------------------------------------------------

@dataclass
class CellLineInfo:
    """Information about a cell line from Cellosaurus."""
    accession: str        # e.g. CVCL_0030
    name: str             # e.g. HeLa
    species: str = ""
    disease: str = ""
    category: str = ""
    synonyms: list[str] = field(default_factory=list)


class CellosaurusClient(_BaseClient):
    """Client for the Cellosaurus REST API (https://api.cellosaurus.org/)."""

    def __init__(self, timeout: int = 30):
        super().__init__("https://api.cellosaurus.org", timeout)
        self._session.headers["Accept"] = "application/json"

    def search(self, query: str, rows: int = 10) -> list[CellLineInfo]:
        """Search Cellosaurus for a cell line by name."""
        try:
            data = self._get("/search/cell-line.json", {
                "q": query,
                "rows": str(rows),
            })
        except requests.RequestException:
            return []

        results: list[CellLineInfo] = []
        for item in data.get("result", {}).get("cell-line-list", []):
            info = CellLineInfo(
                accession=item.get("accession", ""),
                name=item.get("name", ""),
            )
            # Extract species
            species_list = item.get("species-list", {}).get("species", [])
            if species_list:
                info.species = species_list[0].get("species-name", "")
            # Extract disease
            disease_list = item.get("disease-list", {}).get("disease", [])
            if disease_list:
                info.disease = disease_list[0].get("disease-name", "")
            # Category
            info.category = item.get("category", "")
            # Synonyms
            syn_list = item.get("synonym-list", {}).get("synonym", [])
            info.synonyms = [s.get("synonym-value", "") for s in syn_list] if syn_list else []
            results.append(info)
        return results

    def get_by_accession(self, accession: str) -> CellLineInfo | None:
        """Fetch cell line details by Cellosaurus accession (e.g. CVCL_0030)."""
        try:
            data = self._get(f"/cell-line/{accession}.json")
        except requests.RequestException:
            return None

        item = data.get("Cellosaurus", {}).get("cell-line-list", [{}])
        if not item:
            return None
        item = item[0] if isinstance(item, list) else item

        info = CellLineInfo(
            accession=item.get("accession", accession),
            name=item.get("name", ""),
        )
        species_list = item.get("species-list", {}).get("species", [])
        if species_list:
            info.species = species_list[0].get("species-name", "")
        disease_list = item.get("disease-list", {}).get("disease", [])
        if disease_list:
            info.disease = disease_list[0].get("disease-name", "")
        info.category = item.get("category", "")
        return info


# ---------------------------------------------------------------------------
# UniProt client
# ---------------------------------------------------------------------------

@dataclass
class OrganismInfo:
    """Organism info from UniProt taxonomy."""
    taxon_id: int
    scientific_name: str
    common_name: str = ""
    lineage: list[str] = field(default_factory=list)


class UniProtClient(_BaseClient):
    """Client for UniProt REST API (https://rest.uniprot.org/)."""

    def __init__(self, timeout: int = 30):
        super().__init__("https://rest.uniprot.org", timeout)

    def get_taxonomy(self, taxon_id: int) -> OrganismInfo | None:
        """Fetch taxonomy info by NCBITaxon ID."""
        try:
            data = self._get(f"/taxonomy/{taxon_id}.json")
        except requests.RequestException:
            return None

        return OrganismInfo(
            taxon_id=data.get("taxonId", taxon_id),
            scientific_name=data.get("scientificName", ""),
            common_name=data.get("commonName", ""),
            lineage=[item.get("scientificName", "") for item in data.get("lineage", [])],
        )

    def search_taxonomy(self, query: str, rows: int = 5) -> list[OrganismInfo]:
        """Search for an organism by name."""
        try:
            data = self._get("/taxonomy/search", {
                "query": query,
                "size": str(rows),
                "format": "json",
            })
        except requests.RequestException:
            return []

        results: list[OrganismInfo] = []
        for item in data.get("results", []):
            results.append(OrganismInfo(
                taxon_id=item.get("taxonId", 0),
                scientific_name=item.get("scientificName", ""),
                common_name=item.get("commonName", ""),
            ))
        return results


# ---------------------------------------------------------------------------
# BioSamples client
# ---------------------------------------------------------------------------

@dataclass
class BioSampleInfo:
    """Sample info from EBI BioSamples."""
    accession: str
    name: str = ""
    organism: str = ""
    attributes: dict[str, list[str]] = field(default_factory=dict)


class BioSamplesClient(_BaseClient):
    """Client for EBI BioSamples API (https://www.ebi.ac.uk/biosamples/)."""

    def __init__(self, timeout: int = 30):
        super().__init__("https://www.ebi.ac.uk/biosamples/samples", timeout)

    def get_sample(self, accession: str) -> BioSampleInfo | None:
        """Fetch sample metadata by accession (e.g. SAMN12345678)."""
        try:
            data = self._get(f"/{accession}")
        except requests.RequestException:
            return None

        info = BioSampleInfo(
            accession=data.get("accession", accession),
            name=data.get("name", ""),
        )

        # Parse characteristics
        chars = data.get("characteristics", {})
        for key, values in chars.items():
            info.attributes[key] = [v.get("text", "") for v in values]
            if key.lower() == "organism":
                info.organism = info.attributes[key][0] if info.attributes[key] else ""

        return info


# ---------------------------------------------------------------------------
# PRIDE client
# ---------------------------------------------------------------------------

@dataclass
class PRIDEProject:
    """PRIDE project metadata."""
    accession: str
    title: str = ""
    description: str = ""
    organism: list[str] = field(default_factory=list)
    instruments: list[str] = field(default_factory=list)
    modifications: list[str] = field(default_factory=list)
    publication_date: str = ""
    references: list[str] = field(default_factory=list)
    sample_count: int = 0


@dataclass
class PRIDEFile:
    """A file from a PRIDE project."""
    accession: str
    file_name: str
    file_type: str = ""
    file_size: int = 0


class PRIDEClient(_BaseClient):
    """Client for PRIDE REST API (https://www.ebi.ac.uk/pride/ws/archive/v2/)."""

    def __init__(self, timeout: int = 30):
        super().__init__("https://www.ebi.ac.uk/pride/ws/archive/v2", timeout)

    def get_project(self, accession: str) -> PRIDEProject | None:
        """Fetch project metadata by PXD accession."""
        try:
            data = self._get(f"/projects/{accession}")
        except requests.RequestException:
            return None

        organisms = []
        for item in data.get("organisms", []):
            name = item.get("name", "")
            if name:
                organisms.append(name)

        instruments = []
        for item in data.get("instruments", []):
            name = item.get("name", "")
            if name:
                instruments.append(name)

        mods = []
        for item in data.get("ptmNames", []):
            if isinstance(item, str):
                mods.append(item)

        refs = []
        for item in data.get("references", []):
            doi = item.get("doi", "")
            if doi:
                refs.append(doi)

        return PRIDEProject(
            accession=data.get("accession", accession),
            title=data.get("title", ""),
            description=data.get("projectDescription", ""),
            organism=organisms,
            instruments=instruments,
            modifications=mods,
            publication_date=data.get("publicationDate", ""),
            references=refs,
            sample_count=data.get("numAssays", 0),
        )

    def list_files(self, accession: str, page_size: int = 100) -> list[PRIDEFile]:
        """List files for a PRIDE project."""
        try:
            data = self._get(f"/files/byProject", {
                "accession": accession,
                "pageSize": str(page_size),
            })
        except requests.RequestException:
            return []

        files: list[PRIDEFile] = []
        for item in data if isinstance(data, list) else data.get("_embedded", {}).get("files", []):
            files.append(PRIDEFile(
                accession=item.get("accession", ""),
                file_name=item.get("fileName", ""),
                file_type=item.get("fileCategory", {}).get("value", ""),
                file_size=item.get("fileSizeBytes", 0),
            ))
        return files

    def search_projects(self, query: str, page_size: int = 10) -> list[PRIDEProject]:
        """Search PRIDE for projects."""
        try:
            data = self._get("/search/projects", {
                "keyword": query,
                "pageSize": str(page_size),
            })
        except requests.RequestException:
            return []

        projects: list[PRIDEProject] = []
        items = data if isinstance(data, list) else data.get("_embedded", {}).get("compactprojects", [])
        for item in items:
            projects.append(PRIDEProject(
                accession=item.get("accession", ""),
                title=item.get("title", ""),
                description=item.get("projectDescription", ""),
            ))
        return projects

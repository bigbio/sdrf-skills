"""Tests for tools.services — external service clients."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tools.services import (
    CellosaurusClient,
    UniProtClient,
    BioSamplesClient,
    PRIDEClient,
    CellLineInfo,
    OrganismInfo,
    BioSampleInfo,
    PRIDEProject,
)


class TestCellosaurusClient:
    def test_search_mock(self):
        client = CellosaurusClient()
        client._cache["https://api.cellosaurus.org/search/cell-line.json|{'q': 'HeLa', 'rows': '10'}"] = {
            "result": {
                "cell-line-list": [
                    {
                        "accession": "CVCL_0030",
                        "name": "HeLa",
                        "category": "Cancer cell line",
                        "species-list": {"species": [{"species-name": "Homo sapiens"}]},
                        "disease-list": {"disease": [{"disease-name": "Cervical adenocarcinoma"}]},
                        "synonym-list": {"synonym": []},
                    }
                ]
            }
        }
        results = client.search("HeLa")
        assert len(results) == 1
        assert results[0].accession == "CVCL_0030"
        assert results[0].name == "HeLa"
        assert results[0].species == "Homo sapiens"


class TestUniProtClient:
    def test_get_taxonomy_mock(self):
        client = UniProtClient()
        client._cache["https://rest.uniprot.org/taxonomy/9606.json|None"] = {
            "taxonId": 9606,
            "scientificName": "Homo sapiens",
            "commonName": "Human",
            "lineage": [
                {"scientificName": "Eukaryota"},
                {"scientificName": "Mammalia"},
            ],
        }
        info = client.get_taxonomy(9606)
        assert info is not None
        assert info.taxon_id == 9606
        assert info.scientific_name == "Homo sapiens"
        assert info.common_name == "Human"


class TestBioSamplesClient:
    def test_get_sample_mock(self):
        client = BioSamplesClient()
        client._cache["https://www.ebi.ac.uk/biosamples/samples/SAMN12345678|None"] = {
            "accession": "SAMN12345678",
            "name": "test sample",
            "characteristics": {
                "organism": [{"text": "Homo sapiens"}],
                "tissue": [{"text": "liver"}],
            },
        }
        info = client.get_sample("SAMN12345678")
        assert info is not None
        assert info.accession == "SAMN12345678"
        assert info.organism == "Homo sapiens"
        assert "tissue" in info.attributes


class TestPRIDEClient:
    def test_get_project_mock(self):
        client = PRIDEClient()
        client._cache["https://www.ebi.ac.uk/pride/ws/archive/v2/projects/PXD000001|None"] = {
            "accession": "PXD000001",
            "title": "TMT spleen",
            "projectDescription": "A TMT experiment on spleen tissue",
            "organisms": [{"name": "Homo sapiens"}],
            "instruments": [{"name": "Q Exactive"}],
            "ptmNames": ["Oxidation", "Carbamidomethyl"],
            "publicationDate": "2012-03-01",
            "references": [{"doi": "10.1234/test"}],
            "numAssays": 12,
        }
        proj = client.get_project("PXD000001")
        assert proj is not None
        assert proj.accession == "PXD000001"
        assert "Homo sapiens" in proj.organism
        assert "Q Exactive" in proj.instruments
        assert proj.sample_count == 12

    def test_dataclass_defaults(self):
        proj = PRIDEProject(accession="PXD999999")
        assert proj.title == ""
        assert proj.organism == []
        assert proj.sample_count == 0

"""Tests for tools.cellline_db — cell line metadata database."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from tools.cellline_db import (
    CellLineDatabase,
    CellLineEntry,
    MatchResult,
    annotate_sdrf_celllines,
    estimate_developmental_stage,
    DEFAULT_DB_PATH,
)


# ---------------------------------------------------------------------------
# Inline fixture for tests that don't need the full database
# ---------------------------------------------------------------------------

MINI_DB_TSV = (
    "cell line\tcellosaurus name\tcellosaurus accession\tbto cell line\t"
    "organism\torganism part\tsampling site\tage\tdevelopmental stage\tsex\t"
    "ancestry category\tdisease\tcell type\tMaterial type\tsynonyms\tcurated\n"
    "HeLa\tHeLa\tCVCL_0030\tHeLa cell\tHomo sapiens\tCervix\tCervix\t31Y\t"
    "Adult\tFemale\tAfrican American\tCervical adenocarcinoma\tepithelial\tcell\t"
    "HELA;He La;HeLa-CCL2\tcurated\n"
    "MCF-7\tMCF-7\tCVCL_0031\tMCF-7 cell\tHomo sapiens\tBreast\tBreast\t69Y\t"
    "Adult\tFemale\tCaucasian\tBreast carcinoma\tnot available\tcell\t"
    "MCF7;BR_MCF7\tcurated\n"
    "HL-60\tHL-60\tCVCL_0002\tHL-60 cell\tHomo sapiens\tBlood\tPeripheral blood\t"
    "36Y\tAdult\tFemale\tCaucasian\tAcute myeloid leukemia\tnot available\tcell\t"
    "HL60;HL 60\tcurated\n"
    "A549\tA-549\tCVCL_0023\tA549 cell\tHomo sapiens\tLung\tLung\t58Y\t"
    "Adult\tMale\tCaucasian\tLung carcinoma\tepithelial\tcell\t"
    "A-549;LC_A549\tcurated\n"
)


@pytest.fixture
def mini_db_path(tmp_path: Path) -> Path:
    """Write the mini DB to a temp file and return its path."""
    p = tmp_path / "mini-cl-db.tsv"
    p.write_text(MINI_DB_TSV)
    return p


@pytest.fixture
def mini_db(mini_db_path: Path) -> CellLineDatabase:
    """Load the mini DB."""
    db = CellLineDatabase()
    db.load(mini_db_path, synonyms_path=None)
    return db


# ---------------------------------------------------------------------------
# Unit tests (no database needed)
# ---------------------------------------------------------------------------

class TestCellLineEntry:
    def test_from_row(self):
        row = {
            "cell line": "HeLa",
            "cellosaurus name": "HeLa",
            "cellosaurus accession": "CVCL_0030",
            "bto cell line": "HeLa cell",
            "organism": "Homo sapiens",
            "organism part": "Cervix",
            "sampling site": "Cervix",
            "age": "31Y",
            "developmental stage": "Adult",
            "sex": "Female",
            "ancestry category": "African American",
            "disease": "Cervical adenocarcinoma",
            "cell type": "epithelial",
            "Material type": "cell",
            "synonyms": "HELA; HeLa S3; HeLa-S3",
            "curated": "curated",
        }
        entry = CellLineEntry.from_row(row)
        assert entry.cell_line == "HeLa"
        assert entry.cellosaurus_accession == "CVCL_0030"
        assert entry.organism == "Homo sapiens"
        assert len(entry.synonyms) == 3
        assert "HELA" in entry.synonyms

    def test_all_names(self):
        entry = CellLineEntry(
            cell_line="MCF-7",
            cellosaurus_name="MCF-7",
            cellosaurus_accession="CVCL_0031",
            synonyms=["MCF7", "BR_MCF7"],
        )
        names = entry.all_names()
        assert "MCF-7" in names
        assert "CVCL_0031" in names
        assert "MCF7" in names

    def test_enrichment_dict(self):
        entry = CellLineEntry(
            cell_line="A549",
            organism="Homo sapiens",
            disease="Lung carcinoma",
        )
        d = entry.to_enrichment_dict()
        assert d["organism"] == "Homo sapiens"
        assert d["disease"] == "Lung carcinoma"
        assert "cell line" not in d  # not in enrichment


class TestDevelopmentalStage:
    def test_infant(self):
        assert estimate_developmental_stage("1Y") == "Infant"

    def test_children(self):
        assert estimate_developmental_stage("5Y") == "Children"

    def test_adult(self):
        assert estimate_developmental_stage("30Y") == "Adult"

    def test_elderly(self):
        assert estimate_developmental_stage("70Y") == "Elderly"

    def test_not_available(self):
        assert estimate_developmental_stage("not available") == "not available"


# ---------------------------------------------------------------------------
# Database tests (use mini fixture — always runs)
# ---------------------------------------------------------------------------

class TestCellLineDatabase:
    def test_load_size(self, mini_db: CellLineDatabase):
        assert mini_db.size == 4

    def test_exact_match_hela(self, mini_db: CellLineDatabase):
        result = mini_db.find("HeLa")
        assert result.entry is not None
        assert result.match_type == "exact"
        assert result.confidence == 1.0
        assert result.entry.organism == "Homo sapiens"

    def test_exact_match_case_insensitive(self, mini_db: CellLineDatabase):
        result = mini_db.find("hela")
        assert result.entry is not None
        assert result.match_type == "exact"
        assert result.entry.cell_line == "HeLa"

    def test_exact_match_mcf7(self, mini_db: CellLineDatabase):
        result = mini_db.find("MCF-7")
        assert result.entry is not None
        assert result.entry.disease == "Breast carcinoma"

    def test_exact_match_a549(self, mini_db: CellLineDatabase):
        result = mini_db.find("A549")
        assert result.entry is not None
        assert result.entry.organism_part == "Lung"

    def test_accession_match(self, mini_db: CellLineDatabase):
        result = mini_db.find("CVCL_0002")
        assert result.entry is not None
        assert result.match_type == "exact"
        assert result.entry.cell_line == "HL-60"

    def test_synonym_match(self, mini_db: CellLineDatabase):
        result = mini_db.find("HL60")
        assert result.entry is not None
        assert result.entry.cell_line == "HL-60"

    def test_not_found(self, mini_db: CellLineDatabase):
        result = mini_db.find("COMPLETELY_FAKE_CELLLINE_12345")
        assert result.entry is None
        assert result.match_type == "none"

    def test_not_available_skipped(self, mini_db: CellLineDatabase):
        result = mini_db.find("not available")
        assert result.entry is None
        assert result.match_type == "none"

    def test_find_all(self, mini_db: CellLineDatabase):
        results = mini_db.find_all(["HeLa", "MCF-7", "FAKE"])
        assert len(results) == 3
        assert results[0].entry is not None
        assert results[0].query == "HeLa"
        assert results[1].entry is not None
        assert results[1].query == "MCF-7"
        assert results[2].entry is None
        assert results[2].query == "FAKE"

    def test_find_all_preserves_query(self, mini_db: CellLineDatabase):
        """find_all should preserve the original query string for each result."""
        results = mini_db.find_all(["HeLa", "hela"])
        assert results[0].query == "HeLa"
        assert results[1].query == "hela"
        assert results[0].entry == results[1].entry


class TestAnnotateSdrfCelllines:
    def test_annotate_with_cell_line_column(self, mini_db_path: Path):
        content = (
            "source name\tcharacteristics[cell line]\tassay name\n"
            "s1\tHeLa\trun1\n"
            "s2\tMCF-7\trun2\n"
            "s3\tFAKELINE\trun3\n"
        )
        enriched, report = annotate_sdrf_celllines(content, db_path=mini_db_path,
                                                    synonyms_path=None)
        assert report.total_rows == 3
        assert report.matched >= 2
        assert report.unmatched <= 1
        assert "suggested[organism]" in enriched
        assert "match_type" in enriched

    def test_annotate_without_cell_line_column(self, mini_db_path: Path):
        content = (
            "source name\tcharacteristics[organism]\tassay name\n"
            "s1\tHomo sapiens\trun1\n"
        )
        _, report = annotate_sdrf_celllines(content, db_path=mini_db_path,
                                             synonyms_path=None)
        assert report.unmatched == report.total_rows

    def test_report_summary(self, mini_db_path: Path):
        content = (
            "source name\tcharacteristics[cell line]\tassay name\n"
            "s1\tHeLa\trun1\n"
        )
        _, report = annotate_sdrf_celllines(content, db_path=mini_db_path,
                                             synonyms_path=None)
        summary = report.summary()
        assert "Cell Line Annotation Report" in summary


# ---------------------------------------------------------------------------
# Smoke test: bundled database exists
# ---------------------------------------------------------------------------

class TestBundledDatabase:
    @pytest.mark.skipif(not DEFAULT_DB_PATH.exists(),
                        reason="Bundled cell line database not present")
    def test_bundled_db_exists_and_loads(self):
        """Verify the bundled cl-annotations-db.tsv loads successfully."""
        db = CellLineDatabase()
        db.load()
        assert db.size > 100

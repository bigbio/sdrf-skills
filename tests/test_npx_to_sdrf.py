"""Tests for tools.NPXtoSDRF."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.NPXtoSDRF import (
    ConversionDefaults,
    _build_row,
    aggregate_samples,
    clinical_to_sdrf,
    convert_npx_to_sdrf,
    infer_platform,
    inspect_npx_parquet,
    load_npx_samples,
    map_sample_type,
    normalize_panel_name,
    normalize_sample_matrix,
    read_npx_parquet,
    render_sdrf,
)


@pytest.fixture
def sample_npx_rows() -> list[dict]:
    return [
        {
            "SampleID": "S001",
            "SampleType": "SAMPLE",
            "Panel": "Explore_HT",
            "PlateID": "HT053A",
            "WellID": "A01",
            "Normalization": "Intensity",
            "OlinkID": "OID1",
            "NPX": 1.2,
            "Gender": "Female",
            "Patient.Age.At.Collection": "45",
            "Primary.Diagnosis": "Normal",
            "Patient": "P001",
            "Race": "White",
            "InstrumentType": "Illumina NovaSeq 6000",
        },
        {
            "SampleID": "S001",
            "SampleType": "SAMPLE",
            "Panel": "Explore_HT",
            "PlateID": "HT053A",
            "WellID": "A01",
            "Normalization": "Intensity",
            "OlinkID": "OID2",
            "NPX": 2.3,
            "Gender": "Female",
            "Patient.Age.At.Collection": "45",
            "Primary.Diagnosis": "Normal",
            "Patient": "P001",
            "Race": "White",
            "InstrumentType": "Illumina NovaSeq 6000",
        },
        {
            "SampleID": "NEG1",
            "SampleType": "NEGATIVE_CONTROL",
            "Panel": "Explore_HT",
            "PlateID": "HT053A",
            "WellID": "H12",
            "Normalization": "Intensity",
            "OlinkID": "OID1",
            "NPX": 0.1,
        },
        {
            "SampleID": "QC1",
            "SampleType": "SAMPLE_CONTROL",
            "Panel": "Explore_HT",
            "PlateID": "HT053A",
            "WellID": "H11",
            "Normalization": "Intensity",
            "OlinkID": "OID1",
            "NPX": 0.2,
        },
    ]


class TestNpxHelpers:
    def test_aggregate_samples(self, sample_npx_rows: list[dict]):
        samples = aggregate_samples(sample_npx_rows)
        assert len(samples) == 3
        by_id = {s.sample_id: s for s in samples}
        assert by_id["S001"].assay_count == 2
        assert by_id["S001"].panel == "Explore_HT"
        assert by_id["S001"].clinical["Gender"] == "Female"
        assert by_id["NEG1"].sample_type == "NEGATIVE_CONTROL"
        assert by_id["QC1"].sample_type == "SAMPLE_CONTROL"

    def test_map_sample_type(self):
        assert map_sample_type("SAMPLE") == "study sample"
        assert map_sample_type("NEGATIVE_CONTROL") == "negative control"
        assert map_sample_type("SAMPLE_CONTROL") == "quality control sample"
        assert map_sample_type(None) == "study sample"

    def test_infer_platform(self):
        assert infer_platform("Explore_HT") == "Olink Explore HT"
        assert infer_platform("Explore HT") == "Olink Explore HT"
        assert infer_platform("Target 96 Inflammation") == "Olink Target 96"
        assert infer_platform(None, "Illumina NovaSeq 6000") == "Olink Explore HT"
        assert infer_platform("Unknown panel") is None

    def test_normalize_panel_name(self):
        assert normalize_panel_name("Explore_HT") == "Explore HT"

    def test_normalize_sample_matrix(self):
        assert normalize_sample_matrix("plasma") == "blood plasma"
        assert normalize_sample_matrix("blood plasma") == "blood plasma"
        assert normalize_sample_matrix("serum") == "serum"
        assert normalize_sample_matrix("not available") == "not available"

    def test_clinical_to_sdrf(self):
        mapped = clinical_to_sdrf(
            {
                "Gender": "Female",
                "Patient.Age.At.Collection": "45",
                "Primary.Diagnosis": "Normal",
                "Patient": "P001",
                "Race": "White",
            }
        )
        assert mapped["characteristics[sex]"] == "female"
        assert mapped["characteristics[age]"] == "45Y"
        assert mapped["characteristics[disease]"] == "normal"
        assert mapped["characteristics[individual]"] == "P001"
        assert mapped["characteristics[ancestry category]"] == "European"


class TestRenderSdrf:
    def test_render_includes_template_columns(self, sample_npx_rows: list[dict]):
        samples = aggregate_samples(sample_npx_rows)
        defaults = ConversionDefaults(
            organism="homo sapiens",
            organism_part="blood",
            disease="normal",
            sample_matrix="plasma",
            platform="Olink Explore HT",
            data_file="demo.parquet",
        )
        rows = []
        for idx, sample in enumerate(samples, start=1):
            rows.append(
                _build_row(
                    sample,
                    defaults=defaults,
                    metadata={},
                    templates=("human",),
                    data_file="demo.parquet",
                    bio_rep=idx,
                    map_clinical=True,
                )
            )

        content, columns = render_sdrf(rows, templates=("human",))
        assert "source name\t" in content
        assert "comment[platform]" in columns
        assert content.count("comment[sdrf template]") >= 2
        assert "protein expression profiling by antibody array" in content
        assert "S001" in content
        assert "negative control" in content
        assert "quality control sample" in content
        assert "female" in content
        assert "Explore HT" in content

        assay_idx = columns.index("assay name")
        char_indices = [i for i, c in enumerate(columns) if c.startswith("characteristics[")]
        assert char_indices, "expected characteristics columns"
        assert max(char_indices) < assay_idx, "characteristics must precede assay name"

        neg_row = next(r for r in rows if r["source name"] == "NEG1")
        assert neg_row["characteristics[age]"] == "not available"
        assert neg_row["characteristics[sex]"] == "not available"
        assert "not applicable" not in neg_row["characteristics[age]"]

    def test_comment_order_follows_template_not_alphabetical(self, sample_npx_rows: list[dict]):
        samples = aggregate_samples(sample_npx_rows)
        rows = [
            _build_row(
                sample,
                defaults=ConversionDefaults(data_file="demo.parquet"),
                metadata={},
                templates=("human",),
                data_file="demo.parquet",
                bio_rep=1,
                map_clinical=True,
            )
            for sample in samples[:1]
        ]
        _, columns = render_sdrf(rows, templates=("human",))
        if "comment[data file]" in columns and "comment[platform]" in columns:
            assert columns.index("comment[data file]") < columns.index("comment[platform]")


class TestParquetIntegration:
    @pytest.fixture
    def parquet_file(self, tmp_path: Path, sample_npx_rows: list[dict]):
        pa = pytest.importorskip("pyarrow")
        pq = pytest.importorskip("pyarrow.parquet")
        table = pa.Table.from_pylist(sample_npx_rows)
        path = tmp_path / "demo_npx.parquet"
        pq.write_table(table, path)
        return path

    def test_read_npx_parquet(self, parquet_file: Path):
        rows = read_npx_parquet(parquet_file)
        assert len(rows) == 4
        assert rows[0]["SampleID"] == "S001"

    def test_load_npx_samples(self, parquet_file: Path):
        samples, n_rows = load_npx_samples(parquet_file)
        assert n_rows == 4
        assert len(samples) == 3
        by_id = {s.sample_id: s for s in samples}
        assert by_id["S001"].clinical.get("Gender") == "Female"

    def test_inspect_npx_parquet(self, parquet_file: Path):
        report = inspect_npx_parquet(parquet_file)
        assert report.n_rows == 4
        assert report.n_samples == 3
        assert "SampleID" in report.mapped_columns
        assert "Gender" in report.mapped_columns

    def test_convert_npx_to_sdrf(self, parquet_file: Path):
        defaults = ConversionDefaults(
            organism="homo sapiens",
            organism_part="blood",
            sample_matrix="plasma",
        )
        content, report = convert_npx_to_sdrf(
            parquet_file,
            templates=("human",),
            defaults=defaults,
        )
        assert report.n_samples == 3
        assert report.n_assay_rows == 4
        assert report.clinical_mapped == 1
        assert "affinity-proteomics" in ",".join(report.templates)
        assert "S001" in content
        assert "female" in content
        assert "Explore HT" in content
        assert "blood plasma" in content
        assert "NPX" in content

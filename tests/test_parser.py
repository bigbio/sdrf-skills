"""Tests for tools.sdrf_parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.sdrf_parser import (
    parse_sdrf,
    parse_modification,
    parse_instrument,
    parse_template_value,
)


class TestParseSdrf:
    def test_parse_from_file(self, synthetic_sdrf_path: Path):
        sdrf = parse_sdrf(synthetic_sdrf_path)
        assert sdrf.n_rows == 6
        assert sdrf.n_columns == 23
        assert sdrf.path is not None

    def test_parse_from_string(self, minimal_sdrf_content: str):
        sdrf = parse_sdrf(minimal_sdrf_content)
        assert sdrf.n_rows == 2
        assert sdrf.path is None

    def test_parse_empty(self, empty_sdrf_content: str):
        sdrf = parse_sdrf(empty_sdrf_content)
        assert sdrf.n_rows == 0
        assert sdrf.n_columns == 0

    def test_column_classification(self, synthetic_sdrf_path: Path):
        sdrf = parse_sdrf(synthetic_sdrf_path)
        types = {c.raw_name: c.col_type for c in sdrf.columns}
        assert types["source name"] == "anchor"
        assert types["assay name"] == "anchor"
        assert types["technology type"] == "anchor"
        assert types["characteristics[organism]"] == "characteristics"
        assert types["comment[data file]"] == "comment"
        assert types["factor value[disease]"] == "factor_value"

    def test_inner_names(self, synthetic_sdrf_path: Path):
        sdrf = parse_sdrf(synthetic_sdrf_path)
        inner = {c.raw_name: c.inner_name for c in sdrf.columns}
        assert inner["characteristics[organism]"] == "organism"
        assert inner["comment[instrument]"] == "instrument"

    def test_unique_values(self, synthetic_sdrf_path: Path):
        sdrf = parse_sdrf(synthetic_sdrf_path)
        key = sdrf.key_for_column(1)  # characteristics[organism]
        organisms = sdrf.unique_values(key)
        assert "Homo sapiens" in organisms
        assert "homo sapiens" in organisms  # case error row 6

    def test_column_names_filter(self, synthetic_sdrf_path: Path):
        sdrf = parse_sdrf(synthetic_sdrf_path)
        chars = sdrf.column_names("characteristics")
        assert "characteristics[organism]" in chars
        assert "comment[data file]" not in chars

    def test_duplicate_column_keys(self, synthetic_sdrf_path: Path):
        """Duplicate comment[modification parameters] columns get unique keys."""
        sdrf = parse_sdrf(synthetic_sdrf_path)
        mod_keys = sdrf.all_keys_for_name("comment[modification parameters]")
        assert len(mod_keys) == 3
        # First key is plain, subsequent have __N suffix
        assert mod_keys[0] == "comment[modification parameters]"
        assert "__2" in mod_keys[1]
        assert "__3" in mod_keys[2]

    def test_template_detection(self, synthetic_sdrf_path: Path):
        sdrf = parse_sdrf(synthetic_sdrf_path)
        templates = sdrf.detected_templates()
        assert len(templates) >= 1
        names = [t.nt for t in templates]
        assert "ms-proteomics" in names

    def test_auto_detect_templates(self, minimal_sdrf_content: str):
        sdrf = parse_sdrf(minimal_sdrf_content)
        auto = sdrf.auto_detect_templates()
        assert "ms-proteomics" in auto
        assert "human" in auto

    def test_handles_bom(self):
        """UTF-8 BOM should be handled transparently."""
        content = "\ufeffsource name\tassay name\n" "s1\trun1\n"
        sdrf = parse_sdrf(content)
        # BOM is in raw text but csv module can handle it with utf-8-sig
        assert sdrf.n_rows == 1

    def test_handles_crlf(self):
        content = "source name\tassay name\r\ns1\trun1\r\n"
        sdrf = parse_sdrf(content)
        assert sdrf.n_rows == 1


class TestParseModification:
    def test_standard_mod(self):
        m = parse_modification("NT=Carbamidomethyl;AC=UNIMOD:4;TA=C;MT=Fixed")
        assert m.nt == "Carbamidomethyl"
        assert m.ac == "UNIMOD:4"
        assert m.ta == "C"
        assert m.mt == "Fixed"

    def test_positional_mod(self):
        m = parse_modification("NT=Acetyl;AC=UNIMOD:1;PP=Protein N-term;MT=Variable")
        assert m.nt == "Acetyl"
        assert m.ac == "UNIMOD:1"
        assert m.pp == "Protein N-term"
        assert m.mt == "Variable"
        assert m.ta == ""


class TestParseInstrument:
    def test_standard_format(self):
        inst = parse_instrument("AC=MS:1002523;NT=Q Exactive HF-X")
        assert inst.ac == "MS:1002523"
        assert inst.nt == "Q Exactive HF-X"


class TestParseTemplateValue:
    def test_kv_format(self):
        t = parse_template_value("NT=ms-proteomics;VV=v1.1.0")
        assert t.nt == "ms-proteomics"
        assert t.vv == "v1.1.0"

    def test_free_text_format(self):
        t = parse_template_value("ms-proteomics v1.1.0")
        assert t.nt == "ms-proteomics"
        assert t.vv == "v1.1.0"

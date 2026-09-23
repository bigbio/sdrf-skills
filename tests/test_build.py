from __future__ import annotations

from pathlib import Path

import pytest

from tools.build import (BuildError, Sample, check_channels, check_coordinates, check_files, expand,
                         is_channel, parse_samples, parse_technical, read_table, write_sdrf)
from tools.contract import template_contract

FIX = Path(__file__).parent / "fixtures" / "references"


def _tsv(path: Path, header: list[str], rows: list[list[str]]) -> Path:
    path.write_text("\n".join("\t".join(r) for r in [header] + rows) + "\n")
    return path


# ---------- parsing ----------

def test_parse_samples_splits_files_and_defaults_techrep(tmp_path):
    p = _tsv(tmp_path / "samples.tsv",
             ["source name", "files", "label", "characteristics[organism]"],
             [["S1", "a.raw, b.raw", "label free sample", "Homo sapiens"]])
    header, rows = read_table(p)
    s = parse_samples(header, rows)
    assert s[0].source == "S1"
    assert s[0].files == ["a.raw", "b.raw"]
    assert s[0].technical_replicate == 1
    assert s[0].values == {"characteristics[organism]": "Homo sapiens"}


def test_parse_technical_splits_multiple_on_pipe(tmp_path):
    p = _tsv(tmp_path / "technical.tsv", ["column", "value"],
             [["comment[instrument]", "NT=Q Exactive;AC=MS:1001911"],
              ["comment[modification parameters]",
               "NT=Carbamidomethyl;AC=UNIMOD:4;TA=C;MT=Fixed|NT=Oxidation;AC=UNIMOD:35;TA=M;MT=Variable"]])
    _, rows = read_table(p)
    t = parse_technical(rows)
    assert t["comment[instrument]"] == ["NT=Q Exactive;AC=MS:1001911"]
    assert len(t["comment[modification parameters]"]) == 2
    assert t["comment[modification parameters]"][1].startswith("NT=Oxidation")


def test_is_channel():
    assert is_channel("TMT126")
    assert is_channel("TMT127N")
    assert is_channel("iTRAQ114")
    assert not is_channel("label free sample")
    assert not is_channel("NT=label free sample;AC=MS:1002038")


# ---------- refusals ----------

def test_check_files_refuses_unknown_and_duplicate_files():
    s = [Sample("A", ["a.raw"], "label free sample", None, 1, {}),
         Sample("B", ["a.raw"], "label free sample", None, 1, {})]
    with pytest.raises(BuildError) as e:
        check_files(s, ["a.raw"])
    assert "a.raw" in str(e.value) and "B" in str(e.value)
    with pytest.raises(BuildError) as e:
        check_files([Sample("A", ["zzz.raw"], "label free sample", None, 1, {})], ["a.raw"])
    assert "zzz.raw" in str(e.value)


def test_check_channels_refuses_incomplete_plex():
    run = ["run1.raw"]
    s = [Sample("A", run, "TMT126", None, 1, {}),
         Sample("B", run, "TMT127", None, 1, {}),
         Sample("C", ["run2.raw"], "TMT126", None, 1, {})]  # run2 lacks TMT127
    with pytest.raises(BuildError) as e:
        check_channels(s)
    assert "run2.raw" in str(e.value) and "TMT127" in str(e.value)


def test_check_channels_accepts_explicit_unused_channel():
    s = [Sample("A", ["run1.raw"], "TMT126", None, 1, {}),
         Sample("B", ["run1.raw"], "TMT127", None, 1, {}),
         Sample("C", ["run2.raw"], "TMT126", None, 1, {}),
         Sample("", ["run2.raw"], "TMT127", None, 1, {})]  # empty source = unused
    check_channels(s)  # no raise


def test_check_coordinates_refuses_two_rows_with_the_same_coordinate():
    # the same source, same biological and technical replicate, both single-file -> both fraction 1
    s = [Sample("S1", ["rep1.raw"], "label free sample", None, 1, {}),
         Sample("S1", ["rep2.raw"], "label free sample", None, 1, {})]
    with pytest.raises(BuildError) as e:
        check_coordinates(s)
    assert "S1" in str(e.value) and "replicate" in str(e.value)


def test_check_coordinates_accepts_rows_separated_by_replicate():
    s = [Sample("S1", ["rep1.raw"], "label free sample", None, 1, {"characteristics[biological replicate]": "1"}),
         Sample("S1", ["rep2.raw"], "label free sample", None, 1, {"characteristics[biological replicate]": "2"}),
         Sample("S2", ["a.raw"], "label free sample", None, 1, {}),
         Sample("S2", ["b.raw"], "label free sample", None, 2, {})]
    check_coordinates(s)  # no raise


# ---------- expansion ----------

def test_expand_fraction_and_assay_defaults():
    c = template_contract(["ms-proteomics"])
    s = [Sample("S1", ["x_f1.raw", "x_f2.raw"], "label free sample", None, 1,
                {"characteristics[organism]": "Homo sapiens"})]
    header, rows = expand(s, {"comment[instrument]": ["NT=Q Exactive;AC=MS:1001911"]}, c)
    col = {h: i for i, h in enumerate(header)}
    assert header[0] == "source name"
    assert [r[col["comment[fraction identifier]"]] for r in rows] == ["1", "2"]
    assert [r[col["assay name"]] for r in rows] == ["x_f1", "x_f2"]
    assert all(r[col["comment[technical replicate]"]] == "1" for r in rows)
    assert all(r[col["comment[instrument]"]] == "NT=Q Exactive;AC=MS:1001911" for r in rows)
    assert all(r[col["comment[data file]"]] in ("x_f1.raw", "x_f2.raw") for r in rows)


def test_expand_channel_rows_and_unused_channel_emits_nothing():
    c = template_contract(["ms-proteomics"])
    s = [Sample("A", ["run1.raw"], "TMT126", None, 1, {}),
         Sample("", ["run1.raw"], "TMT127", None, 1, {})]
    header, rows = expand(s, {}, c)
    col = {h: i for i, h in enumerate(header)}
    assert len(rows) == 1
    assert rows[0][col["assay name"]] == "run1-TMT126"
    assert rows[0][col["comment[label]"]] == "TMT126"


def test_expand_repeats_multiple_columns_and_orders_factor_last():
    c = template_contract(["ms-proteomics"])
    s = [Sample("S1", ["a.raw"], "label free sample", None, 1,
                {"characteristics[organism]": "Homo sapiens", "factor value[disease]": "normal"})]
    tech = {"comment[modification parameters]": ["NT=Carbamidomethyl;AC=UNIMOD:4;TA=C;MT=Fixed",
                                                  "NT=Oxidation;AC=UNIMOD:35;TA=M;MT=Variable"]}
    header, rows = expand(s, tech, c)
    assert header.count("comment[modification parameters]") == 2
    assert header[-1] == "factor value[disease]"
    i = [k for k, h in enumerate(header) if h == "comment[modification parameters]"]
    assert rows[0][i[0]].startswith("NT=Carbamidomethyl") and rows[0][i[1]].startswith("NT=Oxidation")


def test_expand_fills_reserved_word_only_where_permitted():
    c = template_contract(["ms-proteomics", "human"])
    s = [Sample("S1", ["a.raw"], "label free sample", None, 1, {})]
    header, rows = expand(s, {}, c)
    col = {h: i for i, h in enumerate(header)}
    assert rows[0][col["characteristics[organism part]"]] == "not available"  # permitted
    # instrument is required and does not permit a reserved word: left empty for the validator
    assert rows[0][col["comment[instrument]"]] == ""


def test_expand_sets_template_columns_from_registry():
    c = template_contract(["ms-proteomics", "human"])
    s = [Sample("S1", ["a.raw"], "label free sample", None, 1, {})]
    header, rows = expand(s, {}, c)
    i = [k for k, h in enumerate(header) if h == "comment[sdrf template]"]
    assert len(i) == 2
    assert {rows[0][k] for k in i} == {f"NT=ms-proteomics;VV=v{c.versions['ms-proteomics']}",
                                       f"NT=human;VV=v{c.versions['human']}"}


def test_write_sdrf_keeps_repeated_headers(tmp_path):
    out = tmp_path / "o.sdrf.tsv"
    write_sdrf(["source name", "comment[x]", "comment[x]"], [["a", "1", "2"]], out)
    assert out.read_text().splitlines()[0] == "source name\tcomment[x]\tcomment[x]"

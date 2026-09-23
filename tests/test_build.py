from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tools.build import (BuildError, Sample, build, check_channels, check_coordinates, check_files,
                         expand, is_channel, parse_samples, parse_technical, read_table, write_sdrf)
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
    assert is_channel("SILAC heavy")
    assert not is_channel("label free sample")
    assert not is_channel("NT=label free sample;AC=MS:1002038")
    assert not is_channel("TMT10")  # a plex name, not a channel: the collapsed-plex defect
    assert not is_channel("NT=TMT11plex")


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


def test_expand_fills_technology_type_from_contract_unless_given():
    c = template_contract(["ms-proteomics"])
    s = [Sample("S1", ["a.raw"], "label free sample", None, 1, {})]
    header, rows = expand(s, {}, c)
    assert rows[0][header.index("technology type")] == "proteomic profiling by mass spectrometry"
    header, rows = expand(s, {"technology type": ["something else"]}, c)
    assert rows[0][header.index("technology type")] == "something else"


def test_write_sdrf_keeps_repeated_headers(tmp_path):
    out = tmp_path / "o.sdrf.tsv"
    write_sdrf(["source name", "comment[x]", "comment[x]"], [["a", "1", "2"]], out)
    assert out.read_text().splitlines()[0] == "source name\tcomment[x]\tcomment[x]"


# ---------- round trip against curated references ----------

REFS = {  # accession -> templates the reference declares
    "PXD022949": ["ms-proteomics", "human", "immunopeptidomics"],
    "PXD000878": ["ms-proteomics"],
    "PXD014871": ["ms-proteomics", "human"],
}
STRUCTURAL_OUT = {"assay name", "comment[data file]", "comment[label]", "comment[fraction identifier]",
                  "comment[technical replicate]", "comment[sdrf template]", "technology type"}


def _read_ref(acc: str) -> tuple[list[str], list[list[str]]]:
    lines = (FIX / f"{acc}.reference.tsv").read_text().splitlines()
    return lines[0].split("\t"), [line.split("\t") for line in lines[1:] if line.strip()]


def tables_from_reference(acc: str, tmp_path: Path) -> tuple[Path, Path, Path]:
    """Derive samples.tsv / technical.tsv / files.json from a curated reference.

    One sample row per (source, label, biological replicate, technical replicate) - the row
    coordinate - with that row's files listed in fraction order; comments constant across the
    whole file go to technical.tsv."""
    header, rows = _read_ref(acc)
    idx: dict[str, list[int]] = {}
    for i, h in enumerate(header):
        idx.setdefault(h, []).append(i)

    def g(r, h):
        return r[idx[h][0]] if h in idx and idx[h][0] < len(r) else ""

    groups: dict[tuple[str, str, str, str], list[list[str]]] = {}
    for r in rows:
        key = (g(r, "source name"), g(r, "comment[label]"),
               g(r, "characteristics[biological replicate]"), g(r, "comment[technical replicate]") or "1")
        groups.setdefault(key, []).append(r)
    char_cols = [h for h in header if h.startswith("characteristics[") or h.startswith("factor value[")]
    sample_header = ["source name", "files", "label", "assay name", "technical replicate"] + char_cols
    sample_rows = []
    for (src, label, _bio, trep), rs in groups.items():
        rs = sorted(rs, key=lambda r: int(g(r, "comment[fraction identifier]") or 1))
        files = ", ".join(g(r, "comment[data file]") for r in rs)
        assay = g(rs[0], "assay name") if len(rs) == 1 else ""
        sample_rows.append([src, files, label, assay, trep] + [g(rs[0], c) for c in char_cols])
    # a run that uses fewer channels than the plex gets an explicit unused row per missing channel,
    # which is what build asks of the model; the reference itself simply omits them
    channels = sorted({label for (_s, label, _b, _t) in groups if is_channel(label)})
    if channels:
        per_run: dict[str, set[str]] = {}
        for (_s, label, _b, _t), rs in groups.items():
            if is_channel(label):
                for r in rs:
                    per_run.setdefault(g(r, "comment[data file]"), set()).add(label)
        for run, used in per_run.items():
            for ch in channels:
                if ch not in used:
                    sample_rows.append(["", run, ch, "", "1"] + [""] * len(char_cols))
    files = sorted({g(r, "comment[data file]") for r in rows})
    tech_rows = []
    for h, cols in idx.items():
        if not h.startswith("comment[") or h in STRUCTURAL_OUT:
            continue
        vals = ["|".join(r[i] for i in cols if i < len(r)) for r in rows]
        if len(set(vals)) == 1:
            tech_rows.append([h, vals[0]])
    s = _tsv(tmp_path / "samples.tsv", sample_header, sample_rows)
    t = _tsv(tmp_path / "technical.tsv", ["column", "value"], tech_rows)
    f = tmp_path / "files.json"
    f.write_text(json.dumps(files))
    return s, t, f


@pytest.mark.parametrize("acc", sorted(REFS))
def test_roundtrip_aligns_with_reference_on_file_and_label(acc, tmp_path):
    s, t, f = tables_from_reference(acc, tmp_path)
    out = tmp_path / "out.sdrf.tsv"
    assert build(s, t, f, REFS[acc], out) == 0
    header, rows = _read_ref(acc)
    ref_keys = sorted((r[header.index("comment[data file]")], r[header.index("comment[label]")]) for r in rows)
    lines = out.read_text().splitlines()
    oh = lines[0].split("\t")
    out_keys = sorted((r.split("\t")[oh.index("comment[data file]")], r.split("\t")[oh.index("comment[label]")])
                      for r in lines[1:])
    assert out_keys == ref_keys
    assert oh[0] == "source name"
    fv = [i for i, h in enumerate(oh) if h.startswith("factor value[")]
    assert not fv or fv == list(range(len(oh) - len(fv), len(oh)))


def _ols_available() -> bool:
    try:
        from sdrf_pipelines.sdrf.validators import OLS_AVAILABLE
        return bool(OLS_AVAILABLE)
    except ImportError:
        return False


@pytest.mark.skipif(shutil.which("parse_sdrf") is None or not _ols_available(),
                    reason="parse_sdrf with the [ontology] extra is not installed")
@pytest.mark.parametrize("acc", sorted(REFS))
def test_roundtrip_validates_with_parse_sdrf(acc, tmp_path):
    s, t, f = tables_from_reference(acc, tmp_path)
    out = tmp_path / "out.sdrf.tsv"
    build(s, t, f, REFS[acc], out)
    cmd = ["parse_sdrf", "validate-sdrf", "-s", str(out), "--use_ols_cache_only"]
    for tpl in REFS[acc]:
        cmd += ["-t", tpl]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    errors = [line for line in (p.stdout + p.stderr).splitlines() if "ERROR" in line.upper()]
    assert p.returncode == 0, "\n".join(errors[:20])


def test_cli_build_smoke(tmp_path, capsys):
    import sys

    from tools.cli import main
    s, t, f = tables_from_reference("PXD000878", tmp_path)
    out = tmp_path / "o.sdrf.tsv"
    argv = sys.argv
    sys.argv = ["tools", "build", "--samples", str(s), "--technical", str(t), "--files", str(f),
                "-t", "ms-proteomics", "-o", str(out)]
    try:
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 0
    finally:
        sys.argv = argv
    assert out.exists()
    assert "70 rows" in capsys.readouterr().out

"""Tests for the evidence-manifest coverage check."""

import json
import sys
from pathlib import Path

import pytest

from tools.manifest_coverage import check_coverage

FIX = Path(__file__).parent / "fixtures" / "manifest_coverage"


def write_pair(tmp_path, columns, rows, locations):
    sdrf = tmp_path / "x.sdrf.tsv"
    sdrf.write_text("\n".join("\t".join(r) for r in [columns, *rows]) + "\n")
    manifest = tmp_path / "x.evidence.json"
    claims = [{"location": loc, "value": "v", "source_ids": ["pride"], "evidence": "e"} for loc in locations]
    manifest.write_text(json.dumps({
        "schema_version": 1, "artifact": "x.sdrf.tsv", "dataset": "PXD000001",
        "sources": [{"id": "pride", "kind": "repository", "location": "https://example.org"}],
        "claims": claims,
    }))
    return sdrf, manifest


def test_contract_rewrite_of_pxd074155_reproduces_review_gap():
    """A trimmed PXD074155 SDRF with its manifest rewritten to the contract shape (`location`)
    leaves exactly the three columns the reviewer failed `omission_safety` on."""
    report = check_coverage(FIX / "PXD074155.sdrf.tsv", FIX / "PXD074155.evidence.json")
    assert [g.column for g in report.gaps] == [
        "comment[dissociation method]",
        "comment[precursor mass tolerance]",
        "comment[fragment mass tolerance]",
    ]
    assert report.gaps[1].rows == 2 and report.gaps[1].examples == ("20 ppm",)
    assert "characteristics[age]" in report.sentinel_only


def test_all_covered(tmp_path):
    sdrf, manifest = write_pair(
        tmp_path,
        ["source name", "characteristics[organism]", "comment[instrument]"],
        [["s1", "Homo sapiens", "NT=Q Exactive;AC=MS:1001911"]],
        ["characteristics[organism] rows 1-1", "Comment[ Instrument ]"],
    )
    report = check_coverage(sdrf, manifest)
    assert report.is_covered
    assert report.covered == ["characteristics[organism]", "comment[instrument]"]


def test_one_uncovered_value_column(tmp_path):
    sdrf, manifest = write_pair(
        tmp_path,
        ["source name", "characteristics[organism]", "characteristics[organism part]"],
        [["s1", "Homo sapiens", "liver"], ["s2", "Homo sapiens", "not available"]],
        ["characteristics[organism]"],
    )
    report = check_coverage(sdrf, manifest)
    assert len(report.gaps) == 1
    gap = report.gaps[0]
    assert (gap.column, gap.rows, gap.examples) == ("characteristics[organism part]", 1, ("liver",))


def test_sentinel_only_column_needs_no_claim(tmp_path):
    sdrf, manifest = write_pair(
        tmp_path,
        ["source name", "characteristics[age]", "characteristics[disease]"],
        [["s1", "not available", "Not Applicable"], ["s2", "not available", ""]],
        [],
    )
    report = check_coverage(sdrf, manifest)
    assert report.is_covered
    assert report.sentinel_only == ["characteristics[age]", "characteristics[disease]"]


def test_pooled_and_anonymized_need_a_claim(tmp_path):
    sdrf, manifest = write_pair(
        tmp_path,
        ["source name", "characteristics[pooled sample]", "characteristics[sex]"],
        [["s1", "pooled", "anonymized"]],
        [],
    )
    report = check_coverage(sdrf, manifest)
    assert [g.column for g in report.gaps] == ["characteristics[pooled sample]", "characteristics[sex]"]


def test_anchor_and_metadata_columns_are_exempt(tmp_path):
    columns = ["source name", "assay name", "technology type", "comment[sdrf template]",
               "comment[sdrf template]", "comment[sdrf version]", "comment[sdrf validation hash]",
               "comment[data file]"]
    row = ["s1", "run 1", "proteomic profiling by mass spectrometry", "NT=ms-proteomics;VV=v1.1.0",
           "NT=human;VV=v1.1.0", "v1.1.0", "0f3a", "run1.raw"]
    sdrf, manifest = write_pair(tmp_path, columns, [row], [])
    report = check_coverage(sdrf, manifest)
    assert report.exempt == ["source name", "assay name", "technology type", "comment[sdrf template]",
                             "comment[sdrf version]", "comment[sdrf validation hash]"]
    assert [g.column for g in report.gaps] == ["comment[data file]"]


def test_repeated_column_is_one_entry(tmp_path):
    sdrf, manifest = write_pair(
        tmp_path,
        ["source name", "comment[modification parameters]", "comment[modification parameters]"],
        [["s1", "NT=Oxidation;AC=UNIMOD:35;TA=M;MT=Variable", "NT=Carbamidomethyl;AC=UNIMOD:4;TA=C;MT=Fixed"]],
        [],
    )
    gap, = check_coverage(sdrf, manifest).gaps
    assert gap.column == "comment[modification parameters]" and len(gap.examples) == 2


def test_factor_value_covered_by_the_column_it_mirrors(tmp_path):
    sdrf, manifest = write_pair(
        tmp_path,
        ["source name", "characteristics[disease]", "factor value[disease]", "factor value[treatment]"],
        [["s1", "colon carcinoma", "colon carcinoma", "drug"]],
        ["characteristics[disease]"],
    )
    report = check_coverage(sdrf, manifest)
    assert [g.column for g in report.gaps] == ["factor value[treatment]"]


def test_factor_value_claim_covers_the_column_it_mirrors(tmp_path):
    sdrf, manifest = write_pair(
        tmp_path,
        ["source name", "characteristics[disease]", "factor value[disease]"],
        [["s1", "colon carcinoma", "colon carcinoma"]],
        ["factor value[disease]"],
    )
    assert check_coverage(sdrf, manifest).is_covered


def test_column_field_is_accepted_with_a_warning(tmp_path):
    sdrf, manifest = write_pair(
        tmp_path,
        ["source name", "characteristics[organism]", "comment[instrument]"],
        [["s1", "Homo sapiens", "NT=Q Exactive;AC=MS:1001911"]],
        [],
    )
    manifest.write_text(json.dumps({"claims": [
        {"column": "characteristics[organism]", "value": "Homo sapiens"},
        {"column": ["comment[instrument]"], "value": "Q Exactive"},
    ]}))
    report = check_coverage(sdrf, manifest)
    assert report.is_covered and report.column_alias_claims == 2
    assert "warning: 2 claim(s) use `column`; the contract field is `location`." in report.render()
    assert any("location is required" in e for e in report.schema_errors)
    assert "schema-check" in report.render()


def test_contract_manifest_has_no_schema_warning(tmp_path):
    sdrf, manifest = write_pair(tmp_path, ["source name", "characteristics[organism]"], [["s1", "Homo sapiens"]],
                                ["characteristics[organism] rows 1"])
    report = check_coverage(sdrf, manifest)
    assert report.is_covered and report.schema_errors == []
    assert "warning" not in report.render()


def test_claim_without_location_or_column_covers_nothing(tmp_path):
    sdrf, manifest = write_pair(tmp_path, ["source name", "characteristics[organism]"], [["s1", "Homo sapiens"]], [])
    manifest.write_text(json.dumps({"claims": [{"value": "Homo sapiens"}]}))
    report = check_coverage(sdrf, manifest)
    assert report.unlocated_claims == 1
    assert [g.column for g in report.gaps] == ["characteristics[organism]"]
    assert "no `location`" in report.render()


def _cli(argv):
    from tools.cli import main
    old = sys.argv
    sys.argv = ["tools", "manifest-coverage", *argv]
    try:
        with pytest.raises(SystemExit) as e:
            main()
        return e.value.code
    finally:
        sys.argv = old


def test_cli_exit_codes(tmp_path, capsys):
    assert _cli([str(FIX / "PXD074155.sdrf.tsv"), str(FIX / "PXD074155.evidence.json")]) == 1
    assert "comment[precursor mass tolerance]" in capsys.readouterr().out

    assert _cli([str(FIX / "PXD074155.sdrf.tsv"), str(FIX / "PXD074155.evidence.json"), "--json"]) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is False and len(data["gaps"]) == 3

    sdrf, manifest = write_pair(tmp_path, ["source name", "characteristics[organism]"], [["s1", "Homo sapiens"]],
                                ["characteristics[organism]"])
    assert _cli([str(sdrf), str(manifest)]) == 0

    manifest.write_text("[]")
    assert _cli([str(sdrf), str(manifest)]) == 2
    assert _cli([str(sdrf), str(tmp_path / "missing.json")]) == 2

"""Tests for tools.fetch_record and the `fetch` / `ols` subcommands — no network."""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.parse
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests

from tools import fetch_record
from tools.fetch_record import is_vendor_raw, run
from tools.ols_client import OLSTerm
from tools.services import PRIDEClient

ACC = "PXD000001"
PROJECT = {
    "accession": ACC,
    "title": "HLA class I immunopeptidome",
    "references": [{"referenceLine": "Doe J. Peptides. 2024", "pubmedID": 12345, "doi": "10.1/x"}],
}


def _file(name, category, owner=ACC):
    return {
        "projectAccessions": [owner],
        "fileName": name,
        "fileCategory": {"value": category},
        "publicFileLocations": [
            {"name": "FTP Protocol", "value": f"ftp://ftp.pride.ebi.ac.uk/pride/data/archive/2024/01/{owner}/{name}"},
        ],
    }


FILES = [_file("run2.raw", "RAW"), _file("run1.raw", "RAW"), _file("mqpar.xml", "OTHER"),
         _file("run1.mzML", "PEAK")]

JATS = """<article><front><article-meta>
<article-id pub-id-type="pmcid">PMC111</article-id>
<title-group><article-title>Peptides</article-title></title-group>
<abstract><p>We eluted HLA peptides.</p></abstract></article-meta></front>
<body><sec><title>Materials and methods</title><p>Samples were lysed in CHAPS buffer.</p></sec>
<sec><title>Data availability</title><p>Spectra are at PRIDE and the channel map at Zenodo.</p></sec>
</body></article>"""


def _pride(project=PROJECT, files=FILES):
    pride = MagicMock(spec=PRIDEClient)
    pride.get_project_record.return_value = project
    pride.get_all_files.return_value = files
    return pride


@pytest.fixture
def epmc(monkeypatch):
    """Europe PMC: one record with a PMCID whose full text is JATS."""
    module = fetch_record.europepmc()
    state = {"record": {"pmid": "12345", "pmcid": "PMC111", "title": "Peptides",
                        "abstractText": "<h4>Aim</h4>We eluted <i>HLA</i> peptides."},
             "fulltext": JATS, "urls": []}

    def fetch_json(url):
        state["urls"].append(urllib.parse.unquote(url))
        if isinstance(state["record"], Exception):
            raise state["record"]
        return {"resultList": {"result": [state["record"]] if state["record"] else []}}

    def fetch_text(url):
        state["urls"].append(url)
        if isinstance(state["fulltext"], Exception):
            raise state["fulltext"]
        return state["fulltext"]

    monkeypatch.setattr(module, "fetch_json", fetch_json)
    monkeypatch.setattr(module, "fetch_text", fetch_text)
    return state


def _http_404():
    resp = requests.Response()
    resp.status_code = 404
    return requests.HTTPError("404 Client Error", response=resp)


def test_happy_path_writes_the_offline_layout(tmp_path, epmc, capsys):
    out = tmp_path / "evidence"
    assert run(ACC, out, _pride()) == 0
    assert sorted(p.name for p in out.iterdir()) == ["files.json", "manuscript.txt", "pride.json"]
    assert json.loads((out / "pride.json").read_text()) == PROJECT
    files = json.loads((out / "files.json").read_text())
    assert files["files"] == ["run1.raw", "run2.raw"]
    assert files["other_files"] == ["mqpar.xml", "run1.mzML"]
    assert files["urls"]["mqpar.xml"].startswith("https://ftp.pride.ebi.ac.uk/")
    manuscript = (out / "manuscript.txt").read_text()
    assert "FULL TEXT: Europe PMC open-access XML (PMC111)" in manuscript
    assert "CHAPS buffer" in manuscript
    assert "channel map at Zenodo" in manuscript
    assert "full text" in capsys.readouterr().out


def test_files_json_is_accepted_by_build(tmp_path, epmc):
    from tools.build import Sample, check_files
    out = tmp_path / "evidence"
    run(ACC, out, _pride())
    files = json.loads((out / "files.json").read_text())["files"]
    check_files([Sample("A", ["run1.raw"], "label free sample", None, 1, {}),
                 Sample("B", ["run2.raw"], "label free sample", None, 1, {})], files)


def test_no_open_full_text_falls_back_to_abstract(tmp_path, epmc):
    epmc["fulltext"] = urllib.error.HTTPError("u", 404, "Not Found", None, None)
    assert run(ACC, tmp_path, _pride()) == 0
    manuscript = (tmp_path / "manuscript.txt").read_text()
    assert "ABSTRACT ONLY" in manuscript
    assert "Aim We eluted HLA peptides." in manuscript


def test_paper_missing_from_europepmc_is_said_not_dropped(tmp_path, epmc):
    epmc["record"] = None
    assert run(ACC, tmp_path, _pride()) == 0
    assert "NOT IN EUROPE PMC" in (tmp_path / "manuscript.txt").read_text()


def test_no_publication_writes_no_manuscript(tmp_path, epmc, capsys):
    out = tmp_path / "evidence"
    assert run(ACC, out, _pride(project={**PROJECT, "references": []})) == 0
    assert sorted(p.name for p in out.iterdir()) == ["files.json", "pride.json"]
    assert "manuscript.txt not written" in capsys.readouterr().out
    assert epmc["urls"] == []


def test_doi_only_reference_is_normalised(tmp_path, epmc):
    project = {**PROJECT, "references": [{"doi": "https://doi.org/10.1/X"}]}
    assert run(ACC, tmp_path / "ev", _pride(project=project)) == 0
    assert 'DOI:"10.1/X"' in epmc["urls"][0]


def test_pubmed_id_zero_is_no_pmid(tmp_path, epmc):
    project = {**PROJECT, "references": [{"pubmedID": 0, "doi": "10.1/x"}]}
    assert run(ACC, tmp_path / "ev", _pride(project=project)) == 0
    searches = [u for u in epmc["urls"] if "/search?" in u]
    assert len(searches) == 1 and "EXT_ID" not in searches[0] and 'DOI:"10.1/x"' in searches[0]


def test_full_text_id_stands_in_for_a_missing_pmcid(tmp_path, epmc):
    epmc["record"] = {"pmid": "12345", "fullTextId": "111"}
    assert run(ACC, tmp_path / "ev", _pride()) == 0
    assert "(PMC111)" in (tmp_path / "ev" / "manuscript.txt").read_text()
    assert epmc["urls"][-1].endswith("/PMC111/fullTextXML")


def test_existing_output_is_refused_then_replaced_with_force(tmp_path, epmc, capsys):
    out = tmp_path / "evidence"
    out.mkdir()
    (out / "manuscript.txt").write_text("hand-placed paper")
    (out / "notes.txt").write_text("from another dataset")
    assert run(ACC, out, _pride(project={**PROJECT, "references": []})) == 2
    assert "already exists" in capsys.readouterr().err
    assert (out / "manuscript.txt").read_text() == "hand-placed paper"

    assert run(ACC, out, _pride(project={**PROJECT, "references": []}), force=True) == 0
    assert sorted(p.name for p in out.iterdir()) == ["files.json", "pride.json"]
    assert sorted(p.name for p in tmp_path.iterdir()) == ["evidence"]


def test_empty_existing_output_dir_is_used(tmp_path, epmc):
    out = tmp_path / "evidence"
    out.mkdir()
    assert run(ACC, out, _pride()) == 0
    assert (out / "pride.json").exists()


def test_pride_404_names_the_other_repositories(tmp_path, capsys):
    pride = _pride()
    pride.get_project_record.side_effect = _http_404()
    out = tmp_path / "evidence"
    assert run(ACC, out, pride) == 2
    assert not out.exists()
    err = capsys.readouterr().err
    assert "HTTP 404" in err and "massive-files" in err and "Nothing was written" in err


@pytest.mark.parametrize("stage", ["files", "europepmc_search", "europepmc_fulltext"])
def test_any_failed_lookup_writes_nothing(tmp_path, epmc, capsys, stage):
    pride = _pride()
    if stage == "files":
        pride.get_all_files.side_effect = requests.ConnectionError("connection reset")
    elif stage == "europepmc_search":
        epmc["record"] = urllib.error.URLError("timed out")
    else:
        epmc["fulltext"] = urllib.error.HTTPError("u", 503, "Service Unavailable", None, None)
    out = tmp_path / "evidence"
    assert run(ACC, out, pride) == 2
    assert not out.exists()
    err = capsys.readouterr().err
    assert "fetch failed" in err and "Retry once" in err


def test_empty_pride_file_list_points_at_other_repositories(tmp_path, capsys):
    out = tmp_path / "evidence"
    assert run(ACC, out, _pride(files=[])) == 2
    assert not out.exists()
    assert "massive-files" in capsys.readouterr().err


def test_no_raw_and_no_peak_list_is_a_failure(tmp_path, capsys):
    out = tmp_path / "evidence"
    assert run(ACC, out, _pride(files=[_file("result.txt", "RESULT")])) == 2
    assert not out.exists()
    assert "1 other files found" in capsys.readouterr().err


def test_peak_lists_stand_in_when_no_vendor_raw_is_deposited(tmp_path, epmc, capsys):
    files = [_file("b.mzXML.gz", "PEAK"), _file("a.mzML", "PEAK"), _file("result.txt", "RESULT")]
    out = tmp_path / "evidence"
    assert run(ACC, out, _pride(files=files)) == 0
    evidence = json.loads((out / "files.json").read_text())
    assert evidence["files"] == ["a.mzML", "b.mzXML.gz"]
    assert evidence["other_files"] == ["result.txt"]
    assert "peak lists" in evidence["note"]
    assert "warning:" in capsys.readouterr().out


def test_unexpected_error_is_exit_2_not_a_traceback(tmp_path, capsys):
    pride = _pride()
    pride.get_project_record.side_effect = RuntimeError("boom")
    assert run(ACC, tmp_path / "ev", pride) == 2
    assert "unexpected RuntimeError: boom" in capsys.readouterr().err


def test_file_of_another_project_is_refused(tmp_path):
    out = tmp_path / "evidence"
    assert run(ACC, out, _pride(files=FILES + [_file("x.raw", "RAW", owner="PXD999999")])) == 2
    assert not out.exists()


def test_vendor_raw_classification():
    assert is_vendor_raw("a.d.zip", "OTHER")
    assert is_vendor_raw("a.wiff", "")
    assert not is_vendor_raw("a.wiff.scan", "RAW")
    assert is_vendor_raw("anything.bin", "RAW")
    assert not is_vendor_raw("a.mzML", "PEAK")
    assert not is_vendor_raw("a.mgf.gz", "PEAK")


def _cli(argv):
    from tools.cli import main
    old = sys.argv
    sys.argv = ["tools", *argv]
    try:
        with pytest.raises(SystemExit) as e:
            main()
        return e.value.code
    finally:
        sys.argv = old


def test_fetch_subcommand(tmp_path, epmc, monkeypatch):
    monkeypatch.setattr(fetch_record, "PRIDEClient", lambda: _pride())
    assert _cli(["fetch", ACC.lower(), "--out", str(tmp_path / "ev")]) == 0
    assert (tmp_path / "ev" / "files.json").exists()


def test_ols_subcommand(monkeypatch, capsys):
    from tools.ols_client import OLSClient
    calls = []

    def search_term(self, query, ontology_id=None, exact=False, rows=10):
        calls.append((query, ontology_id, exact, rows))
        return [OLSTerm(iri="i", label="breast carcinoma", short_form="MONDO_0004989", ontology_name="mondo")]

    monkeypatch.setattr(OLSClient, "search_term", search_term)
    assert _cli(["ols", "breast carcinoma", "--ontology", "mondo", "--ontology", "efo", "--rows", "3"]) == 0
    assert calls == [("breast carcinoma", "mondo,efo", False, 3)]
    assert capsys.readouterr().out == "MONDO:0004989\tbreast carcinoma\tmondo\n"

    monkeypatch.setattr(OLSClient, "search_term", lambda self, *a, **k: [])
    assert _cli(["ols", "no such thing"]) == 1

    def boom(self, *a, **k):
        raise requests.ConnectionError("down")
    monkeypatch.setattr(OLSClient, "search_term", boom)
    assert _cli(["ols", "x"]) == 2
    assert "OLS search failed" in capsys.readouterr().err


def test_verify_tells_a_network_failure_from_not_found(monkeypatch, capsys):
    from tools.ols_client import OLSClient
    monkeypatch.setattr(OLSClient, "resolve_accession", lambda self, acc: None)
    assert _cli(["verify", "MONDO:9999999"]) == 1

    def boom(self, acc):
        raise requests.ConnectionError("down")
    monkeypatch.setattr(OLSClient, "resolve_accession", boom)
    assert _cli(["verify", "MONDO:0004989"]) == 2
    assert "OLS lookup failed" in capsys.readouterr().err


def test_new_commands_do_not_import_fastmcp():
    code = ("import sys, tools.cli, tools.fetch_record; fetch_record = tools.fetch_record; "
            "fetch_record.europepmc(); assert 'fastmcp' not in sys.modules and 'mcp.server' not in sys.modules")
    subprocess.run([sys.executable, "-c", code], check=True, cwd=Path(__file__).resolve().parent.parent)

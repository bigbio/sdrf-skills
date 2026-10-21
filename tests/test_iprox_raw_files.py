"""Tests for tools.iprox_raw_files."""

import json
from pathlib import Path

import pytest

import tools.iprox_raw_files as irf
from tools.iprox_raw_files import (
    IproxFile,
    IproxResolution,
    file_matches_mode,
    make_uri,
    normalize_accession,
    resolve_accession,
)


def test_normalize_accession_trims_whitespace():
    assert normalize_accession("  IPX0006823000  ") == "IPX0006823000"


def test_unsupported_accession_format_exits():
    with pytest.raises(SystemExit):
        resolve_accession("not-an-accession", timeout=10)


def test_file_matches_mode_uses_iProX_file_type():
    raw = IproxFile("B-1.zip", "RAW", 100.0, "IPX0000000001")
    search = IproxFile("report.tsv", "SEARCH", 1.0, "IPX0000000001")
    assert file_matches_mode(raw, "raw")
    assert not file_matches_mode(search, "raw")
    assert file_matches_mode(search, "all")


def test_make_uri_points_at_download_iprox_org_over_http():
    assert (
        make_uri("IPX0006823000", "IPX0006823001", "B-1.zip")
        == "http://download.iprox.org/IPX0006823000/IPX0006823001/B-1.zip"
    )


def _project_record(privacy=1, subproject_count=6):
    return {
        "subproject_count": subproject_count,
        "projectInfo": {
            "projectId": "IPX0006823000",
            "projectTitleEnglish": "Test project",
            "privacy": privacy,
            "status": 1,
        },
    }


def _subproject_list():
    return [
        {
            "subprojectId": "IPX0006823001",
            "subtitleEn": "Tissue proteome",
            "species": "Homo sapiens",
            "instrument": "timsTOF Pro",
            "fileCount": 4,
            "fileSize": 1024,
            "privacy": 1,
        }
    ]


def _subproject_record(subproject_id="IPX0006823001"):
    return {
        "subProjectInfo": {
            "subprojectId": subproject_id,
            "projectId": "IPX0006823000",
            "subtitleEn": "Tissue proteome",
            "species": "Homo sapiens",
            "privacy": 1,
        },
        "subdatafilesInfo": [
            {"fileName": "B-1.zip", "fileType": "RAW", "fileSize": "3764.5"},
            {"fileName": "G-17.rar", "fileType": "RAW", "fileSize": "3901.0"},
            {"fileName": "pro_result_AnalysisLog.txt", "fileType": "SEARCH", "fileSize": "1.4"},
            {"fileName": "IPX0006823001.xml", "fileType": "XML", "fileSize": "47.5"},
        ],
    }


def test_resolve_project_lists_raw_files_only(monkeypatch):
    monkeypatch.setattr(irf, "fetch_project_record", lambda pid, t: _project_record())
    monkeypatch.setattr(irf, "fetch_subproject_list", lambda pid, t: _subproject_list())
    monkeypatch.setattr(irf, "fetch_subproject_record", lambda sid, t: _subproject_record(sid))

    resolution = resolve_accession("IPX0006823000", timeout=10)
    files = [f for s in resolution.subprojects for f in s.files if file_matches_mode(f, "raw")]

    assert resolution.title == "Test project"
    assert resolution.is_public
    assert [f.name for f in files] == ["B-1.zip", "G-17.rar"]
    assert files[0].size_kb == pytest.approx(3764.5)
    assert files[0].subproject_id == "IPX0006823001"


def test_resolve_subproject_id_falls_back_to_single_subproject(monkeypatch):
    def no_project(pid, t):
        return {"subproject_count": 0}  # no projectInfo key at all

    monkeypatch.setattr(irf, "fetch_project_record", no_project)
    monkeypatch.setattr(
        irf, "fetch_subproject_record", lambda sid, t: _subproject_record(sid)
    )

    resolution = resolve_accession("IPX0006823001", timeout=10)
    assert len(resolution.subprojects) == 1
    assert resolution.subprojects[0].subproject_id == "IPX0006823001"
    assert resolution.project_id == "IPX0006823000"


def test_project_without_subprojects_raises(monkeypatch):
    monkeypatch.setattr(irf, "fetch_project_record", lambda pid, t: _project_record(privacy=0))
    monkeypatch.setattr(irf, "fetch_subproject_list", lambda pid, t: [])
    with pytest.raises(RuntimeError, match="No subprojects"):
        resolve_accession("IPX0006823000", timeout=10)


def test_private_project_flag_survives_subproject_privacy(monkeypatch):
    monkeypatch.setattr(irf, "fetch_project_record", lambda pid, t: _project_record(privacy=0))
    monkeypatch.setattr(irf, "fetch_subproject_list", lambda pid, t: _subproject_list())
    monkeypatch.setattr(irf, "fetch_subproject_record", lambda sid, t: _subproject_record(sid))

    resolution = resolve_accession("IPX0006823000", timeout=10)
    assert not resolution.is_public


def test_pxd_resolution_through_proteomecentral(monkeypatch):
    def proxi(url, timeout):
        return {
            "title": "Test project",
            "identifiers": [{"name": "iProX dataset identifier", "value": "IPX0006823000"}],
        }

    monkeypatch.setattr(irf, "fetch_proxi_json", proxi)
    monkeypatch.setattr(irf, "fetch_project_record", lambda pid, t: _project_record())
    monkeypatch.setattr(irf, "fetch_subproject_list", lambda pid, t: _subproject_list())
    monkeypatch.setattr(irf, "fetch_subproject_record", lambda sid, t: _subproject_record(sid))

    resolution = resolve_accession("PXD047633", timeout=10)
    assert resolution.pxd_accession == "PXD047633"
    assert resolution.project_id == "IPX0006823000"


def test_pxd_resolution_from_dataset_uri_link(monkeypatch):
    def proxi(url, timeout):
        return {
            "title": "Test project",
            "fullDatasetLinks": [
                {
                    "name": "iProX dataset URI",
                    "value": "http://www.iprox.org/page/subproject.html?id=IPX0006823001",
                }
            ],
        }

    def no_project(pid, t):
        return {"subproject_count": 0}  # a subproject id has no project record

    monkeypatch.setattr(irf, "fetch_proxi_json", proxi)
    monkeypatch.setattr(irf, "fetch_project_record", no_project)
    monkeypatch.setattr(
        irf, "fetch_subproject_record", lambda sid, t: _subproject_record("IPX0006823001")
    )

    resolution = resolve_accession("PXD047633", timeout=10)
    assert resolution.project_id == "IPX0006823000"  # parent project recovered
    assert resolution.subprojects[0].subproject_id == "IPX0006823001"


def test_unreleased_pxd_raises_helpful_error(monkeypatch):
    def proxi(url, timeout):
        return {
            "status": "ERROR",
            "error_code": "DatasetNotYetReleased",
            "description": "Dataset PXD047633 has not yet been released by iProX",
        }

    monkeypatch.setattr(irf, "fetch_proxi_json", proxi)
    with pytest.raises(RuntimeError, match="IPX project id"):
        resolve_accession("PXD047633", timeout=10)


# --------------------------------------------------------------------------- PX XML
PX_XML = Path(__file__).parent / "fixtures" / "iprox" / "px.xml"


def _two_subs_resolution():
    resolution = irf.IproxResolution(
        input_accession="IPX0006823000", project_id="IPX0006823000",
        title="Test project", privacy=1,
    )
    sub1 = irf.IproxSubproject(
        subproject_id="IPX0006823001", title="Tissue proteome",
        experiment_protocol="Digested with trypsin.", informatics_protocol="Searched with X.",
        experiment_type="Shotgun proteomics",
    )
    sub1.files = [
        irf.IproxFile("B-1.zip", "RAW", 3764.4, "IPX0006823001"),
        irf.IproxFile("G-13.zip", "RAW", 4844421.1, "IPX0006823001"),
    ]
    sub2 = irf.IproxSubproject(
        subproject_id="IPX0006823002", title="TMT-labeled plasma", experiment_type="Shotgun proteomics",
    )
    sub2.files = [irf.IproxFile("TMT01.raw", "RAW", 500.0, "IPX0006823002")]
    resolution.subprojects = [sub1, sub2]
    return resolution


def test_px_xml_parses_species_instruments_and_files():
    px = irf.parse_px_xml(PX_XML.read_text(encoding="utf-8"))
    assert px.species == ["Homo sapiens"]
    assert px.instruments == ["timsTOF Pro"]
    assert [e.name for e in px.entries["IPX0006823001"]] == [
        "YS20220223_28_Slot2-33_1_12137.d.zip", "B-1.zip"]


def test_apply_xml_names_reports_renamed_entries_as_orphans():
    resolution = _two_subs_resolution()
    irf.apply_xml_names(resolution, irf.parse_px_xml(PX_XML.read_text(encoding="utf-8")))
    assert resolution.px_species == ["Homo sapiens"]
    orphans = [o for o in resolution.px_orphans]
    assert [o.name for o in orphans] == ["YS20220223_28_Slot2-33_1_12137.d.zip"]
    # G-13.zip (4844421.1 KB = 4730.88 MB) is the only deposited file with the orphan's size
    assert orphans[0].same_size_candidates == ["G-13.zip"]


def test_merge_px_combines_project_and_subproject_xmls():
    px = irf.parse_px_xml(PX_XML.read_text(encoding="utf-8"))
    other = irf.PxXml(species=["Mus musculus"], instruments=["Orbitrap Exploris 480"])
    other.entries["IPX0006823002"] = [irf.PxXmlEntry("TMT01.raw", size_kb=500.0)]
    merged = irf.merge_px([px, other])
    assert merged.species == ["Homo sapiens", "Mus musculus"]
    assert merged.instruments == ["timsTOF Pro", "Orbitrap Exploris 480"]
    assert "IPX0006823001" in merged.entries and "IPX0006823002" in merged.entries


def test_build_record_maps_iprox_prose_to_reconcile_keys():
    resolution = _two_subs_resolution()
    resolution.description = "A description."
    record = irf.build_record(resolution)
    assert record["title"] == "Test project"
    assert record["projectDescription"] == "A description."
    assert "trypsin" in record["sampleProcessingProtocol"].lower()
    assert record["dataProcessingProtocol"] == "Searched with X."
    assert "TMT-labeled plasma" in record["quantificationMethods"]


def test_run_cli_subproject_filter(capsys, monkeypatch):
    monkeypatch.setattr(irf, "resolve_accession", lambda acc, t: _two_subs_resolution())
    assert irf.run_cli(["IPX0006823000", "--subproject", "IPX0006823001", "--mode", "raw"]) == 0
    assert capsys.readouterr().out.split() == ["B-1.zip", "G-13.zip"]


def test_run_cli_record_and_unknown_subproject(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(irf, "resolve_accession", lambda acc, t: _two_subs_resolution())
    record_path = tmp_path / "record.json"
    assert irf.run_cli(
        ["IPX0006823000", "--record", str(record_path), "--subproject", "IPX0006823002"]) == 0
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["title"] == "Test project"
    with pytest.raises(SystemExit):
        irf.run_cli(["IPX0006823000", "--subproject", "IPX0000009999"])

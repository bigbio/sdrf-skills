"""Tests for tools.massive_raw_files."""

import email
import json

import tools.massive_raw_files as mrf
from tools.massive_raw_files import (
    MassiveResolution,
    file_matches_mode,
    ftp_candidates,
    normalize_accession,
    parse_ftp_url,
    parse_massive_from_url,
    parse_task_from_url,
)


def test_normalize_accession_trims_whitespace():
    assert normalize_accession("  PXD016117  ") == "PXD016117"


def test_parse_task_from_url_extracts_valid_task():
    url = "https://massive.ucsd.edu/ProteoSAFe/dataset.jsp?task=d3a5905ada824d43baadb64abbb830d4"
    assert parse_task_from_url(url) == "d3a5905ada824d43baadb64abbb830d4"


def test_parse_task_from_url_rejects_invalid_task():
    url = "https://massive.ucsd.edu/ProteoSAFe/dataset.jsp?task=not-a-real-task"
    assert parse_task_from_url(url) is None


def test_parse_massive_from_url_extracts_query_or_path_id():
    assert parse_massive_from_url("https://example.org/?dataset=MSV000084528") == "MSV000084528"
    assert parse_massive_from_url("https://massive.ucsd.edu/MSV000084528/files") == "MSV000084528"


def test_parse_ftp_url_parses_host_and_path():
    host, path = parse_ftp_url("ftp://massive.ucsd.edu/v02/MSV000084528/")
    assert host == "massive.ucsd.edu"
    assert path == "/v02/MSV000084528/"


def test_ftp_candidates_include_resolution_ftp_and_massive_fallbacks():
    resolution = MassiveResolution(
        input_accession="PXD016117",
        massive_accession="MSV000084528",
        ftp_url="ftp://massive-ftp.ucsd.edu/v02/MSV000084528/",
    )
    candidates = ftp_candidates(resolution)
    assert candidates[0] == "ftp://massive-ftp.ucsd.edu/v02/MSV000084528/"
    assert "ftp://massive.ucsd.edu/v02/MSV000084528/" in candidates


def test_file_matches_mode_for_raw_and_acquisition():
    assert file_matches_mode("/foo/bar/sample.raw", "raw")
    assert not file_matches_mode("/foo/bar/sample.mzML", "raw")
    assert file_matches_mode("/foo/bar/sample.mzML", "acquisition")
    assert file_matches_mode("/foo/bar/sample.anything", "all")


def test_ftp_candidates_prefer_massive_proxi_root():
    """MassIVE's own root wins: ProteomeCentral omits the version directory."""
    resolution = MassiveResolution(
        input_accession="PXD003626",
        massive_accession="MSV000079512",
        ftp_url="ftp://massive.ucsd.edu/MSV000079512",           # ProteomeCentral, no /v01/
        proxi_ftp_url="ftp://massive.ucsd.edu/v01/MSV000079512/",  # MassIVE, authoritative
    )
    candidates = ftp_candidates(resolution)
    assert candidates[0] == "ftp://massive.ucsd.edu/v01/MSV000079512/"
    assert "ftp://massive.ucsd.edu/MSV000079512" in candidates


def test_ftp_candidates_include_v01_fallback():
    """Older datasets (e.g. MSV000078958) live under /v01/, not /v02/."""
    resolution = MassiveResolution(
        input_accession="MSV000078958", massive_accession="MSV000078958"
    )
    assert "ftp://massive.ucsd.edu/v01/MSV000078958/" in ftp_candidates(resolution)


def test_enrich_from_massive_proxi_reads_dataset_ftp_location(monkeypatch):
    payload = {
        "title": "Integrated metagenomics/metaproteomics",
        "datasetLink": [
            {"accession": "MS:1002488", "value": "https://massive.ucsd.edu/ProteoSAFe/QueryMSV?id=MSV000078958"},
            {"accession": "MS:1002852", "value": "ftp://massive.ucsd.edu/v01/MSV000078958"},
        ],
    }
    monkeypatch.setattr(mrf, "fetch_json", lambda url: payload)
    r = mrf.enrich_from_massive_proxi(
        MassiveResolution(input_accession="MSV000078958", massive_accession="MSV000078958")
    )
    assert r.proxi_ftp_url == "ftp://massive.ucsd.edu/v01/MSV000078958/"  # slash normalised
    assert r.title == "Integrated metagenomics/metaproteomics"


def test_enrich_from_massive_proxi_survives_lookup_failure(monkeypatch):
    def boom(url):
        raise OSError("network down")

    monkeypatch.setattr(mrf, "fetch_json", boom)
    r = mrf.enrich_from_massive_proxi(
        MassiveResolution(input_accession="MSV1", massive_accession="MSV1")
    )
    assert r.proxi_ftp_url is None  # degrades to the guessed candidates


class _FakeHTTPResponse:
    """Minimal stand-in for the urllib.request.urlopen() context manager."""

    def __init__(self, data: bytes, charset: str):
        self._data = data
        self.headers = email.message_from_string(
            f"Content-Type: application/json; charset={charset}\n"
        )

    def read(self) -> bytes:
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def test_fetch_json_decodes_declared_iso_8859_1_charset(monkeypatch):
    """MassIVE serves charset=ISO-8859-1; json.loads() assumes UTF-8, so an
    accented byte raises UnicodeDecodeError and drops the whole response
    unless fetch_json honours the declared charset (see its docstring)."""
    payload = json.dumps({"name": "Café"}, ensure_ascii=False).encode("iso-8859-1")
    monkeypatch.setattr(
        mrf.urllib.request,
        "urlopen",
        lambda request, timeout=None: _FakeHTTPResponse(payload, "iso-8859-1"),
    )
    assert mrf.fetch_json("http://example.org/dataset") == {"name": "Café"}

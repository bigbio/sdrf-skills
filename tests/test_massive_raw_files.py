"""Tests for tools.massive_raw_files."""

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

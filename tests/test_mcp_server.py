"""Tests for mcp/server.py — MCP tool functions."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub out optional heavy dependencies so the module can be loaded in CI
# (CI installs only requests + pytest; fastmcp and httpx are not present).
# ---------------------------------------------------------------------------

def _make_stub_modules():
    """Inject minimal stubs for fastmcp and httpx into sys.modules."""
    if "fastmcp" not in sys.modules:
        class _FakeFastMCP:
            def __init__(self, *args, **kwargs):
                pass

            def tool(self, *args, **kwargs):
                """Support @mcp.tool() as a no-op decorator."""
                def decorator(fn):
                    return fn
                return decorator

        fastmcp_mod = types.ModuleType("fastmcp")
        fastmcp_mod.FastMCP = _FakeFastMCP
        sys.modules["fastmcp"] = fastmcp_mod

    if "httpx" not in sys.modules:
        httpx_mod = types.ModuleType("httpx")
        httpx_mod.Client = MagicMock
        httpx_mod.HTTPStatusError = Exception
        sys.modules["httpx"] = httpx_mod


_make_stub_modules()

# Import the local mcp/server.py directly to avoid collision with the
# installed 'mcp' package from fastmcp/anthropic.
_SERVER_PATH = Path(__file__).parent.parent / "mcp" / "server.py"
_spec = importlib.util.spec_from_file_location("sdrf_mcp_server", _SERVER_PATH)
_mcp_server = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mcp_server)


class TestGetProjectFiles:
    """Tests for get_project_files — verifies /files/all endpoint is used."""

    def test_uses_files_all_endpoint(self):
        """get_project_files must call /files/all, never the paginated /files."""
        mcp_server = _mcp_server

        captured_urls: list[str] = []

        def fake_cached_get_json(url, params=None, timeout=None):
            captured_urls.append(url)
            return [
                {
                    "fileName": "sample.raw",
                    "fileCategory": {"value": "RAW"},
                    "publicFileLocations": [],
                },
            ]

        with patch.object(mcp_server, "_cached_get_json", side_effect=fake_cached_get_json):
            result = mcp_server.get_project_files("PXD052416")

        assert len(captured_urls) == 1, "Expected exactly one HTTP call"
        assert captured_urls[0].endswith("/files/all"), (
            f"get_project_files must use the /files/all endpoint to avoid "
            f"silent truncation at 100 files; called {captured_urls[0]!r} instead"
        )

    def test_returns_complete_file_list(self):
        """get_project_files correctly classifies raw and other files."""
        mcp_server = _mcp_server

        # Simulate >100 files returned from /files/all (impossible with /files default)
        raw_files = [
            {"fileName": f"run_{i:03d}.raw", "fileCategory": {"value": "RAW"}, "publicFileLocations": []}
            for i in range(153)
        ]
        other_files = [
            {"fileName": "proteins.fasta", "fileCategory": {"value": "FASTA"}, "publicFileLocations": []}
        ]

        with patch.object(mcp_server, "_cached_get_json", return_value=raw_files + other_files):
            result = mcp_server.get_project_files("PXD052416")

        assert result["rawfile_count"] == 153
        assert len(result["raw_file_names"]) == 153
        assert len(result["other_files_names"]) == 1

    def test_returns_error_dict_on_api_failure(self):
        """get_project_files returns a structured error when the API is unreachable."""
        mcp_server = _mcp_server

        with patch.object(mcp_server, "_cached_get_json", return_value=None):
            result = mcp_server.get_project_files("PXD000001")

        assert result["rawfile_count"] == 0
        assert result["raw_file_names"] == []
        assert "error" in result


def _ols_search_response(obo_ids, num_found=None):
    """Build a minimal OLS /search JSON body from a list of obo_ids."""
    docs = [
        {"label": oid.split(":")[0].lower(), "obo_id": oid, "ontology_prefix": oid.split(":")[0]}
        for oid in obo_ids
    ]
    return {"response": {"numFound": num_found if num_found is not None else len(docs), "docs": docs}}


class TestSmartSearchAmbiguity:
    """issue #35 C4 — smart mode must not present a non-exact / one-of-many hit
    as if it were THE answer."""

    def test_multiple_distinct_exact_matches_flagged_ambiguous(self):
        """`HeLa` exact-matches several distinct entities → ambiguous, not a
        confident single hit."""
        mcp_server = _mcp_server
        # exact probe returns two DIFFERENT accessions (parental + derivative)
        resp = _ols_search_response(["EFO:0001185", "CLO:0003724"])
        with patch.object(mcp_server, "_cached_get_json", return_value=resp):
            out = mcp_server.searchClasses("HeLa", "efo")  # default mode="smart"
        assert out.get("ambiguous") is True
        assert out["numFound"] == 2
        assert "note" in out
        assert {r["accession"] for r in out["results"]} == {"EFO:0001185", "CLO:0003724"}

    def test_single_distinct_exact_match_is_confident(self):
        """A single distinct exact match returns confidently, no ambiguous flag."""
        mcp_server = _mcp_server
        resp = _ols_search_response(["NCBITaxon:562"])
        with patch.object(mcp_server, "_cached_get_json", return_value=resp):
            out = mcp_server.searchClasses("Escherichia coli", "ncbitaxon")
        assert out.get("ambiguous") is None
        assert out.get("fallback") is None
        assert out["numFound"] == 1

    def test_falls_back_to_fuzzy_when_no_exact(self):
        """No exact match → fuzzy fallback, flagged so the caller knows it's not exact."""
        mcp_server = _mcp_server

        def side_effect(url, params=None, timeout=None):
            if params and params.get("exact") == "true":
                return _ols_search_response([])          # exact miss
            return _ols_search_response(["UBERON:0002421"])  # fuzzy hit

        with patch.object(mcp_server, "_cached_get_json", side_effect=side_effect):
            out = mcp_server.searchClasses("hippocampus", "uberon")  # typo → no exact
        assert out.get("fallback") == "fuzzy"
        assert out.get("ambiguous") is None
        assert out["numFound"] == 1

    def test_exact_probe_is_wide_not_one(self):
        """The exact probe must request more than 1 row, or ambiguity is invisible."""
        mcp_server = _mcp_server
        captured = []

        def side_effect(url, params=None, timeout=None):
            captured.append(params or {})
            return _ols_search_response(["EFO:0001185"])

        with patch.object(mcp_server, "_cached_get_json", side_effect=side_effect):
            mcp_server.searchClasses("HeLa", "efo")
        assert captured, "no OLS call made"
        assert captured[0].get("rows", 0) > 1, "exact probe capped at 1 hides ambiguity"


class TestGetChildrenDescendants:
    """issue #35 B7 — getChildren must return descendants, not only direct children."""

    def test_uses_descendants_endpoint(self):
        mcp_server = _mcp_server
        captured_urls = []

        def side_effect(url, params=None, timeout=None):
            captured_urls.append(url)
            return {"_embedded": {"terms": [
                {"label": "pooled sample", "obo_id": "PRIDE:0000544", "ontology_prefix": "PRIDE"},
                {"label": "empty", "obo_id": "PRIDE:0000562", "ontology_prefix": "PRIDE"},
            ]}}

        with patch.object(mcp_server, "_cached_get_json", side_effect=side_effect):
            out = mcp_server.getChildren("PRIDE:0000895")
        assert captured_urls, "no OLS call made"
        assert captured_urls[0].endswith("/descendants")
        assert "/children" not in captured_urls[0]
        assert out["count"] == 2
        assert {c["accession"] for c in out["children"]} == {"PRIDE:0000544", "PRIDE:0000562"}

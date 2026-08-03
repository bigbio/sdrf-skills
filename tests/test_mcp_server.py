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

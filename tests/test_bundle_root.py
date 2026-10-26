"""The bundle root resolves from SDRF_SKILLS_ROOT first, then Claude Code's CLAUDE_PLUGIN_ROOT."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent
ROOT_IDIOM = "${SDRF_SKILLS_ROOT:-${CLAUDE_PLUGIN_ROOT}}"
BARE_PLUGIN_PATH = re.compile(r"\$\{?CLAUDE_PLUGIN_ROOT\}?/")


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        ({"SDRF_SKILLS_ROOT": "/sdrf", "CLAUDE_PLUGIN_ROOT": "/plugin"}, "/sdrf"),
        ({"SDRF_SKILLS_ROOT": "/sdrf"}, "/sdrf"),
        ({"CLAUDE_PLUGIN_ROOT": "/plugin"}, "/plugin"),
        ({}, "."),
    ],
)
def test_check_deps_hook_resolves_bundle_root(tmp_path: Path, env: dict, expected: str):
    # An empty PATH makes parse_sdrf missing, so the hook prints the install hint.
    result = subprocess.run(
        [shutil.which("bash"), str(REPO / "hooks" / "check-deps.sh")],
        env={"PATH": str(tmp_path), **env},
        capture_output=True,
        text=True,
        check=True,
    )
    assert f'"{expected}/environment.yml"' in result.stdout


def test_skills_resolve_bundle_paths_through_sdrf_skills_root():
    for path in (REPO / "skills").rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        if "**Bundle paths.**" in text:
            assert ROOT_IDIOM in text, path
        for line in text.replace(ROOT_IDIOM, "").splitlines():
            # The plugin venv must sit where .mcp.json looks: under the plugin root itself.
            if ".venv" in line or "requirements.txt" in line:
                continue
            assert not BARE_PLUGIN_PATH.search(line), (path, line)

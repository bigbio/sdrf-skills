"""Entry point: python -m tools <command>.

Several commands (contract, build) need sdrf-pipelines' registry. When the interpreter that
ran us cannot import it but parse_sdrf is installed, re-exec under parse_sdrf's own
interpreter, which by construction can - the usual case when a venv's python3 shadows the
one sdrf-pipelines was installed into."""

from __future__ import annotations

import os
import shutil
import sys


def interpreter_for_sdrf_pipelines() -> str | None:
    """The interpreter parse_sdrf runs under, read from its shebang; None when not installed."""
    exe = shutil.which("parse_sdrf")
    if not exe:
        return None
    try:
        with open(exe, "rb") as fh:
            first = fh.readline().decode(errors="ignore").strip()
    except OSError:
        return None
    if first.startswith("#!"):
        cand = first[2:].split()[-1] if "env" in first else first[2:].strip()
        return cand if os.path.exists(cand) else None
    return None


def _reexec_if_needed() -> None:
    if os.environ.get("SDRF_TOOLS_REEXEC") == "1":
        return
    try:
        import sdrf_pipelines  # noqa: F401
        return
    except ImportError:
        pass
    other = interpreter_for_sdrf_pipelines()
    if other and os.path.realpath(other) != os.path.realpath(sys.executable):
        env = {**os.environ, "SDRF_TOOLS_REEXEC": "1"}
        os.execve(other, [other, "-m", "tools", *sys.argv[1:]], env)


if __name__ == "__main__":
    _reexec_if_needed()
    from tools.cli import main
    main()

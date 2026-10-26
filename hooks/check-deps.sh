#!/usr/bin/env bash
# SessionStart hook: check if parse_sdrf is available and recommend setup if not.
#
# The bundle root is where the skills, spec/ and environment.yml actually live —
# a marketplace install puts them in Claude Code's plugin cache, not in the user's cwd.
root="${SDRF_SKILLS_ROOT:-${CLAUDE_PLUGIN_ROOT:-.}}"

if command -v parse_sdrf >/dev/null 2>&1; then
  echo "sdrf-skills loaded — parse_sdrf available."
else
  echo "SDRF skills loaded. Install dependencies for full functionality:"
  echo "  conda: conda env create -f \"$root/environment.yml\" && conda activate sdrf-skills"
  echo "  pip:   pip install -e \"$root[mcp]\""
  echo "Run `sdrf-tools doctor` (install notes: `sdrf-annotate/references/setup.md`) for guided installation."
fi

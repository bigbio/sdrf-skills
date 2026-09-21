---
name: sdrf-setup
description: Use when the user wants to set up SDRF skills dependencies, install parse_sdrf and techsdrf, or configure the environment for the first time.
user-invocable: true
argument-hint: "[optional: conda | pip | check]"
---

# SDRF Setup Workflow

> **Bundle paths.** `spec/`, `tools/` and `data/` ship with this skill, not with your working
> directory. Resolve every such path below against the bundle root — `$CLAUDE_PLUGIN_ROOT` under
> Claude Code (`$CLAUDE_PLUGIN_ROOT/spec/sdrf-proteomics/TERMS.tsv`), or your sdrf-skills checkout
> on other platforms. Run the helpers as `PYTHONPATH="$CLAUDE_PLUGIN_ROOT" python3 -m tools …`.
> Files the user is annotating stay relative to the working directory.

You are guiding the user through installing SDRF skills dependencies. Follow these steps.

**In Cursor**: The user invokes this by asking "install SDRF dependencies" or similar (no `/sdrf-skills:sdrf-setup` slash command). Ensure `environment.yml` and `requirements.txt` exist at the workspace root; if not, suggest cloning the full sdrf-skills repo or copying those files.

## Step 1: Detect Available Package Managers

Check which package managers are available (run these in the terminal or ask the user):

```bash
command -v conda && conda --version
command -v mamba && mamba --version
command -v uv && uv --version
command -v pip && pip --version
```

- **Conda or mamba**: Recommended — best for thermorawfileparser (Thermo .raw files) via bioconda
- **Pip**: Works for sdrf-pipelines and techsdrf; thermorawfileparser requires conda
- **uv**: Can install Python tools; same limitation as pip for thermorawfileparser

## Step 2: Provide Installation Commands

Based on what's available, output the exact commands the user should run.

### Option A — Conda (recommended)

```bash
# From the sdrf-skills project directory:
conda env create -f environment.yml
conda activate sdrf-skills
```

If using **mamba** (faster):
```bash
mamba env create -f environment.yml
conda activate sdrf-skills
```

### Option B — Pip (venv)

```bash
# From the sdrf-skills project directory:
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**Note**: With pip, thermorawfileparser is not available (not on PyPI). For Thermo .raw files, use conda.

### Option C — uv

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

## Step 3: Verify Installation

After the user runs the commands, ask them to verify:

```bash
parse_sdrf --version
techsdrf --version
```

If both succeed, setup is complete.

## Step 4: Optional — Spec Submodule

A marketplace install already carries `spec/` (Claude Code clones submodules), so this step is only
for checkouts. If the user cloned without submodules or wants the latest spec:

```bash
git submodule update --init --recursive
# To pull latest:
git submodule update --remote --recursive
```

## Step 4b: Bundled MCP server (Claude Code plugin installs)

`.mcp.json` runs `mcp/server.py` (PRIDE, Europe PMC, Unpaywall, OLS helpers) from a virtualenv
**inside the plugin directory**, because a marketplace install lives in Claude Code's plugin cache,
not in the user's project. Resolve the directory first and show the user the real path:

```bash
echo "$CLAUDE_PLUGIN_ROOT"
uv venv "$CLAUDE_PLUGIN_ROOT/.venv"
uv pip install --python "$CLAUDE_PLUGIN_ROOT/.venv/bin/python" -r "$CLAUDE_PLUGIN_ROOT/requirements.txt"
```

(`python -m venv` + `pip install -r` works the same way if `uv` is unavailable.) Tell the user a
plugin upgrade replaces that directory, so the venv has to be re-created afterwards. Without it the
`sdrf-pride-pmc` server just fails to connect — the skills fall back to their other sources.

## Step 5: Optional — MCP Servers

For full SDRF annotation (PRIDE, OLS, PubMed), the user needs MCP servers configured. Tell them to check their host's MCP configuration:

- **PRIDE MCP** — project metadata, OLS, EuropePMC
- **PubMed** — literature, PMC full text
- **bioRxiv** — preprint search (optional)
- **Consensus** — evidence search (optional)

For Europe PMC full text, prefer the local normalizer over raw XML inspection:
`python scripts/europepmc_fulltext.py PMC_ID --format text`
This keeps methods/results/discussion easier for LLMs to interpret and preserves
canonical links plus detected accessions in JSON mode.

## Summary Output

Provide a clear summary:

1. **Package manager detected**: conda / pip / uv
2. **Commands to run**: (copy-paste block)
3. **Verify**: parse_sdrf --version, techsdrf --version
4. **Next**: Run /sdrf-skills:sdrf-annotate PXD###### or /sdrf-skills:sdrf-validate yourfile.sdrf.tsv

## If User Passes "check"

When the user invokes `/sdrf-skills:sdrf-setup check`, run the verification step and report status:
- parse_sdrf: ✓ or ✗
- techsdrf: ✓ or ✗
- spec/ submodule: present and init'd or not
- Suggest fixes for any missing items

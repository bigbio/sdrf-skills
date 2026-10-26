# Reference: installing the tools (when `sdrf-tools doctor` reports something missing)

# SDRF Setup Workflow

> **Bundle paths.** `spec/`, `tools/` and `data/` ship with this skill, not with your working
> directory. Resolve every such path below against the bundle root (`SDRF_SKILLS_ROOT`, else
> `CLAUDE_PLUGIN_ROOT`, else your sdrf-skills checkout): `${SDRF_SKILLS_ROOT:-${CLAUDE_PLUGIN_ROOT}}/spec/sdrf-proteomics/TERMS.tsv`.
> The helpers are the `sdrf-tools` command (install notes: `setup.md`; check with `sdrf-tools doctor`); no `PYTHONPATH` or bundle-root variable is needed to run them.
> Files the user is annotating stay relative to the working directory.

You are guiding the user through installing SDRF skills dependencies. Follow these steps.

**In Cursor**: The user invokes this by asking "install SDRF dependencies" or similar (no ``sdrf-tools doctor` (install notes: `setup.md`)` slash command). Install from a full sdrf-skills checkout (`git clone --recurse-submodules https://github.com/bigbio/sdrf-skills`). Copying `environment.yml` or `requirements.txt` alone does not work, because both install the package from that checkout.

## Step 1: Detect Available Package Managers

Check which package managers are available (run these in the terminal or ask the user;
in unattended mode, SKILL.md Step 0, run them yourself):

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
pip install -r requirements.txt   # the sdrf-tools console script + the bundled MCP server's deps
```

`requirements.txt` installs the package with its `[mcp]` extra (`pip install -e '.[mcp]'`). Without
the bundled MCP server, for example in a pipeline, `pip install -e .` installs only the core:
`sdrf-tools`, `sdrf-pipelines` and their dependencies. Keep the install editable: the tools read
`spec/` and `data/` from the checkout.

Afterwards `sdrf-tools --help` must work from any directory; the skills call it that way, with no
`PYTHONPATH` and no plugin-root variable.

**Note**: With pip, thermorawfileparser is not available (not on PyPI). For Thermo .raw files, use conda.

### Option C — uv

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

## Step 3: Verify Installation

After the user runs the commands, ask them to verify (in unattended mode, install nothing
and do not wait: run the checks below yourself, report what is missing, and continue as
SKILL.md Step 0 says):

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
uv pip install --python "$CLAUDE_PLUGIN_ROOT/.venv/bin/python" -e "$CLAUDE_PLUGIN_ROOT[mcp]"
```

(`python -m venv` + `pip install -e "$CLAUDE_PLUGIN_ROOT[mcp]"` works the same way if `uv` is unavailable.) Tell the user a
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
4. **Next**: Run /sdrf-skills:sdrf-annotate PXD###### or `/sdrf-skills:sdrf-annotate <file.sdrf.tsv>` (review mode) yourfile.sdrf.tsv

## If User Passes "check"

When the user invokes `sdrf-tools doctor`, run the verification step and report status:
- parse_sdrf: ✓ or ✗
- techsdrf: ✓ or ✗
- spec/ submodule: present and init'd or not
- Suggest fixes for any missing items

# sdrf-skills

**Turn [Claude Code](https://docs.anthropic.com/en/docs/claude-code), [Cursor](https://cursor.com), [OpenAI Codex](https://developers.openai.com/codex), [Gemini CLI](https://github.com/google-gemini/gemini-cli), or [OpenCode](https://opencode.ai) into an expert proteomics SDRF annotator.**

[![Claude Code Skill](https://img.shields.io/badge/Claude_Code-Skill-blue?logo=anthropic&logoColor=white)](https://docs.anthropic.com/en/docs/claude-code)
[![Cursor](https://img.shields.io/badge/Cursor-Skill-black?logo=cursor&logoColor=white)](https://cursor.com)
[![Codex](https://img.shields.io/badge/Codex-Skill-green?logo=openai&logoColor=white)](https://developers.openai.com/codex)
[![Gemini CLI](https://img.shields.io/badge/Gemini_CLI-Skill-4285F4?logo=google&logoColor=white)](https://github.com/google-gemini/gemini-cli)
[![OpenCode](https://img.shields.io/badge/OpenCode-Skill-purple)](https://opencode.ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![SDRF Spec](https://img.shields.io/badge/SDRF-proteomics--metadata--standard-orange)](https://github.com/bigbio/proteomics-metadata-standard)
[![Skills](https://img.shields.io/badge/skills-16-informational)](#available-skills)

> **Pick a dataset → the agent fetches PRIDE + paper → you review a validated SDRF.**

Structured skills that give AI assistants expert-level capabilities for annotating,
validating, improving, and reviewing proteomics metadata in the
[SDRF](https://github.com/bigbio/proteomics-metadata-standard) format. Instead of guessing
at ontology terms or SDRF rules, the agent follows the methodology of experienced annotators
using real tools (OLS, PRIDE, PubMed). The specification data (column definitions, templates)
lives in a git submodule and is read at runtime, so the skills stay current as the spec evolves.

## Available skills

Twelve skills. Eleven are slash commands under `/sdrf-skills:`; `sdrf-adversarial-review` is dispatched by
`sdrf-annotate` into a fresh context and is never typed as a command:

| Skill | What it does |
|-------|-------------|
| `/sdrf-skills:sdrf-setup` | Guided dependency install (parse_sdrf, techsdrf) — conda or pip |
| `/sdrf-skills:sdrf-knowledge` | Explains the SDRF format in plain language; holds the one canonical copy of the format rules (`references/format-rules.md`) that every other skill points to |
| `/sdrf-skills:sdrf-annotate` | The one entry point. A PXD: record + paper → `samples.tsv` + `technical.tsv` → `sdrf-tools build` → validate → **independent review, always**. An existing `.sdrf.tsv`: review it against the record and the spec. A question: plan. A short core plus `references/` it reads only when a step needs them |
| `/sdrf-skills:sdrf-metascreen` | Shortlist PRIDE / MassIVE / ProteomeXchange studies → resumable TSV |
| `/sdrf-skills:sdrf-autoresearch` | Autonomous retained-improvement loop over a dataset or dataset class |
| `/sdrf-skills:sdrf-validate` | Systematic validation against templates + OLS ontology checking |
| `/sdrf-skills:sdrf-fix` | Auto-fix common errors (UNIMOD swaps, case, format, artifacts) |
| `sdrf-adversarial-review` (dispatched, not typed) | Independent review of an SDRF in a fresh context, checked against the evidence, with a verdict bound to the file's hash |
| `/sdrf-skills:sdrf-contribute` | Contribute an annotated SDRF back to sdrf-annotated-datasets via PR |
| `/sdrf-skills:sdrf-techrefine` | Verify/refine technical metadata from raw files via techsdrf |
| `/sdrf-skills:sdrf-cellline` | Translate Cellosaurus records into SDRF cell-line columns |

## Installation

**Claude Code, in two lines** — no clone needed; the marketplace install fetches the `spec/`
submodules with it:

```text
/plugin marketplace add bigbio/sdrf-skills
/plugin install sdrf-skills@sdrf-skills
```

Then run `/sdrf-skills:sdrf-setup`, which installs the helper tools (`parse_sdrf`, `techsdrf`) and
tells you where the plugin lives. The skills resolve `spec/`, `tools/` and `data/` against
`$CLAUDE_PLUGIN_ROOT`, so you can work from any directory.

**From a checkout** (for development, or for the other platforms below):

```bash
# 1. Clone WITH submodules (the spec data is a submodule):
git clone --recurse-submodules https://github.com/bigbio/sdrf-skills
# already cloned without them?  git submodule update --init --recursive

# 2. Install the deterministic helper tools (conda recommended — includes thermorawfileparser):
conda env create -f environment.yml && conda activate sdrf-skills
# pip alternative (thermorawfileparser not on PyPI):
#   pip install -r requirements.txt && pip install git+https://github.com/bigbio/techsdrf.git
```

Update the bundled spec any time with `git submodule update --remote --recursive`.

## Setup by AI platform

<details><summary>Claude Code (plugin)</summary>

**Marketplace install (recommended)**
```text
/plugin marketplace add bigbio/sdrf-skills
/plugin install sdrf-skills@sdrf-skills
```
Claude Code clones the repository with its submodules, so the SDRF spec data comes with the plugin.
Skills resolve bundled paths through `$CLAUDE_PLUGIN_ROOT`, so any working directory is fine — your
SDRF files stay where they are. Run `/sdrf-skills:sdrf-setup` once for `parse_sdrf`/`techsdrf`, then
`/sdrf-skills:sdrf-annotate PXD######` or `/sdrf-skills:sdrf-validate your_file.sdrf.tsv`.

**From a working tree (development)**
```bash
cd sdrf-skills && claude --plugin-dir .   # loads skills from the working tree
```

**Bundled MCP server (optional).** `.mcp.json` wires `mcp/server.py` (PRIDE + Europe PMC + OLS
helpers) and expects a virtualenv *next to the plugin*, so create it inside the plugin directory —
`/sdrf-skills:sdrf-setup` prints the exact path for your install:

```bash
uv venv "$PLUGIN_ROOT/.venv" && uv pip install --python "$PLUGIN_ROOT/.venv/bin/python" -r "$PLUGIN_ROOT/requirements.txt"
```

Without it the server simply fails to connect; the skills fall back to their other sources.
A plugin upgrade replaces the plugin directory, so re-create the venv after upgrading.

</details>

<details><summary>Cursor</summary>

Ensure `.cursor/rules/sdrf-skills.mdc` is in your project; then ask *"Follow the sdrf setup workflow"* (Cursor does not run Claude Code's `SessionStart` hook).
</details>

<details><summary>Codex / Gemini CLI / OpenCode</summary>

- **Codex** — follow `.codex/INSTALL.md` to symlink `skills/` and `spec/` into your Codex skills path.
- **Gemini CLI** — auto-loads `GEMINI.md` from the repo root.
- **OpenCode** — follow `.opencode/AGENTS.md` to wire the skills in.

For full annotation, configure the **OLS**, **PRIDE**, **PubMed**, and **bioRxiv** MCP servers, and validate with `parse_sdrf validate-sdrf`.
</details>

## Usage

```text
/sdrf-skills:sdrf-annotate PXD045678     → record + paper → tables → sdrf-tools build → validate → independent review
/sdrf-skills:sdrf-annotate file.sdrf.tsv → review an existing SDRF against its record and the spec
/sdrf-skills:sdrf-validate file.sdrf.tsv → template + ontology validation
/sdrf-skills:sdrf-fix file.sdrf.tsv      → repair UNIMOD swaps, case, formats, artifacts (with changelog)
/sdrf-skills:sdrf-contribute PXD045678   → open a PR to bigbio/sdrf-annotated-datasets
```

## Python tools

The repo is **skills-first**: new user-facing workflows go in `skills/`. `tools/` holds deterministic
helpers a skill can call (TSV parsing, OLS client, hallucination detection, quality scoring, auto-fix,
cell-line enrichment, MassIVE fallback, and the review gate). Run them via the unified CLI:

```bash
sdrf-tools check  file.sdrf.tsv          # hallucinated terms / UNIMOD swaps
sdrf-tools score  file.sdrf.tsv          # quality score (0-100, 5 dimensions)
sdrf-tools fix    file.sdrf.tsv -o out.tsv
sdrf-tools verify UNIMOD:1 --label Acetyl
sdrf-tools review-gate gate              # enforce independent-review receipts
sdrf-tools contract -t ms-proteomics -t human          # column contract of a template union
sdrf-tools build --samples samples.tsv --technical technical.tsv \
  --files files.json -t ms-proteomics -t human -o out.sdrf.tsv  # SDRF from a sample table, deterministically
```

**Feeding a pipeline.** quantms reads SDRF natively (`nextflow run bigbio/quantms --input file.sdrf.tsv --fasta proteins.fasta`).
For the others, `sdrf-pipelines` converts: `parse_sdrf convert-maxquant --sdrf file.sdrf.tsv --fastafilepath proteins.fasta`,
`convert-openms --sdrf file.sdrf.tsv --onetable`, `convert-diann --sdrf file.sdrf.tsv`, `convert-msstats`, `convert-normalyzerde`.

**Adversarial review gate.** Changed SDRFs are identified by SHA-256; a passing receipt is valid only
for that exact content, and any edit makes it pending again. Changed artifacts are discovered from git
(measured against the merge base), so the gate works from Claude Code, another assistant, CI, or a plain
shell: `python3 tools/review_gate.py gate --cwd <repo-root>` (exit 1 = review still needed). On Claude
Code a `Stop` hook runs the same check; the hook is a convenience, not the enforcement.

## How it works

The `skills/` directory is platform-agnostic markdown; each platform needs only a thin shim
(`.claude-plugin/`, `.cursor/rules/`, `.codex/`, `GEMINI.md`, `.opencode/`) to discover and load it.
The MCP tools an agent needs already exist (OLS, PRIDE, PubMed) — what was missing was the *expertise*:
which ontology to search per column, how to read a paper for SDRF metadata, the common errors and their
fixes, and what "good" annotation looks like. Skills encode that as step-by-step workflows, and the
`spec/` submodule keeps the column/template data current with no SKILL.md changes.

A skill's `SKILL.md` is loaded whole whenever it is invoked, and it stays in the model's context for every
turn after that, so its length is a per-turn cost. The largest skill, `sdrf-annotate`, is therefore a
short core (the workflow: operating mode, templates, the two tables, `build`, validate) plus
`references/` files — gathering the record, finding sample and technical values, the channel-map
ladder, reconciliation, planning — that it tells the model to read only when that step needs them.
The format rules themselves exist once, in `skills/sdrf-knowledge/references/format-rules.md`.

## Contributing

Add a skill by creating `skills/your-skill/SKILL.md` with YAML frontmatter, writing the workflow in
markdown, and referencing `spec/` for any specification data (never hardcode). For questions about the
SDRF specification itself, open an issue in
[bigbio/proteomics-metadata-standard](https://github.com/bigbio/proteomics-metadata-standard).

## Contributors

Maintained by the [BigBio](https://github.com/bigbio) team.

- **Yasset Perez-Riverol** (maintainer) — [@ypriverol](https://github.com/ypriverol) · [ypriverol@gmail.com](mailto:ypriverol@gmail.com)
- **Timo Sachsenberg** — [@timosachsenberg](https://github.com/timosachsenberg)
- **Julianus Pfeuffer** — [@jpfeuffer](https://github.com/jpfeuffer)
- **Fabian Egli** — [@fabianegli](https://github.com/fabianegli)
- **Enrique Audain** — [@enriquea](https://github.com/enriquea)
- **Husen M. Umer** — [@husensofteng](https://github.com/husensofteng)
- **Chengxin Dai** — [@daichengxin](https://github.com/daichengxin)
- **Yixuan Yang** — [@Yixuan39](https://github.com/Yixuan39)
- **Selvakumar** — [@selva439](https://github.com/selva439)
- **Jonas Scheid** — [@jonasscheid](https://github.com/jonasscheid)
- **Yufei Shen** — [@Shen-YuFei](https://github.com/Shen-YuFei)
- **Asier Larrea Sebal** — [@asierlarrea](https://github.com/asierlarrea) · EMBL-EBI
- [@2024-denglei](https://github.com/2024-denglei)

## License

MIT

# sdrf-skills

**Turn [Claude Code](https://docs.anthropic.com/en/docs/claude-code), [Cursor](https://cursor.com), [OpenAI Codex](https://developers.openai.com/codex), [Gemini CLI](https://github.com/google-gemini/gemini-cli), or [OpenCode](https://opencode.ai) into an expert proteomics SDRF annotator.**

[![Claude Code Skill](https://img.shields.io/badge/Claude_Code-Skill-blue?logo=anthropic&logoColor=white)](https://docs.anthropic.com/en/docs/claude-code)
[![Cursor](https://img.shields.io/badge/Cursor-Skill-black?logo=cursor&logoColor=white)](https://cursor.com)
[![Codex](https://img.shields.io/badge/Codex-Skill-green?logo=openai&logoColor=white)](https://developers.openai.com/codex)
[![Gemini CLI](https://img.shields.io/badge/Gemini_CLI-Skill-4285F4?logo=google&logoColor=white)](https://github.com/google-gemini/gemini-cli)
[![OpenCode](https://img.shields.io/badge/OpenCode-Skill-purple)](https://opencode.ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![SDRF Spec](https://img.shields.io/badge/SDRF-proteomics--metadata--standard-orange)](https://github.com/bigbio/proteomics-metadata-standard)
[![Skills](https://img.shields.io/badge/skills-20-informational)](#available-skills)

> **Pick a dataset → the agent fetches PRIDE + paper → you review a validated SDRF.**

Structured skills that give AI assistants expert-level capabilities for annotating,
validating, improving, and reviewing proteomics metadata in the
[SDRF](https://github.com/bigbio/proteomics-metadata-standard) format. Instead of guessing
at ontology terms or SDRF rules, the agent follows the methodology of experienced annotators
using real tools (OLS, PRIDE, PubMed). The specification data (column definitions, templates)
lives in a git submodule and is read at runtime, so the skills stay current as the spec evolves.

## Available skills

Twenty skills, most in the `sdrf:` namespace (the two review-gate skills use portable hyphenated names):

| Skill | What it does |
|-------|-------------|
| `/sdrf:setup` | Guided dependency install (parse_sdrf, techsdrf) — conda or pip |
| `/sdrf:knowledge` | SDRF format, column rules, ontology mappings, reserved words |
| `/sdrf:templates` | Template selection, layers, and selection rules |
| `/sdrf:metascreen` | Shortlist PRIDE / MassIVE / ProteomeXchange studies → resumable TSV |
| `/sdrf:autoresearch` | Autonomous retained-improvement loop over a dataset or dataset class |
| `/sdrf:annotate` | Full workflow: PXD → PRIDE + paper → draft SDRF → validate |
| `/sdrf:validate` | Systematic validation against templates + OLS ontology checking |
| `/sdrf:improve` | Quality analysis: specificity, completeness, consistency, score |
| `/sdrf:fix` | Auto-fix common errors (UNIMOD swaps, case, format, artifacts) |
| `/sdrf:terms` | Find and verify ontology terms for any column |
| `/sdrf:brainstorm` | Plan metadata strategy before creating an SDRF |
| `/sdrf:review` | Comprehensive quality review cross-referenced to paper + PRIDE |
| `$sdrf-adversarial-review` | Fresh-context, evidence-first review with a hash-bound verdict |
| `$sdrf-annotate-reviewed` | Annotation orchestrator with isolated review, repair, and re-review |
| `/sdrf:explain` | Explain any column, error, or concept in plain language |
| `/sdrf:convert` | Choose and configure analysis pipelines from SDRF |
| `/sdrf:design` | Detect batch effects, confounders, replication issues |
| `/sdrf:contribute` | Contribute an annotated SDRF back to sdrf-annotated-datasets via PR |
| `/sdrf:techrefine` | Verify/refine technical metadata from raw files via techsdrf |
| `/sdrf:cellline` | Translate Cellosaurus records into SDRF cell-line columns |

## Installation

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

```bash
cd sdrf-skills && claude --plugin-dir .   # loads skills from the working tree
```
Start from the repo root (skills reference `spec/` by repo-root-relative path). Then run `/sdrf:setup`, and use `/sdrf:annotate PXD######` or `/sdrf:validate your_file.sdrf.tsv`. Marketplace install is not available yet — see [#27](https://github.com/bigbio/sdrf-skills/issues/27).
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
/sdrf:annotate PXD045678     → fetch PRIDE + paper → select templates → draft SDRF with OLS-verified terms → validate
/sdrf:validate file.sdrf.tsv → template + ontology validation
/sdrf:fix file.sdrf.tsv      → repair UNIMOD swaps, case, formats, artifacts (with changelog)
/sdrf:contribute PXD045678   → open a PR to bigbio/sdrf-annotated-datasets
```

## Python tools

The repo is **skills-first**: new user-facing workflows go in `skills/`. `tools/` holds deterministic
helpers a skill can call (TSV parsing, OLS client, hallucination detection, quality scoring, auto-fix,
cell-line enrichment, MassIVE fallback, and the review gate). Run them via the unified CLI:

```bash
python -m tools check  file.sdrf.tsv          # hallucinated terms / UNIMOD swaps
python -m tools score  file.sdrf.tsv          # quality score (0-100, 5 dimensions)
python -m tools fix    file.sdrf.tsv -o out.tsv
python -m tools verify UNIMOD:1 --label Acetyl
python -m tools review-gate gate              # enforce independent-review receipts
```

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
- [@2024-denglei](https://github.com/2024-denglei)
- **Asier Larrea Sebal** — [@asierlarrea](https://github.com/asierlarrea) · EMBL-EBI

## License

MIT

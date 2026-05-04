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
[![PRIDE](https://img.shields.io/badge/data-PRIDE-2C7BB6)](https://www.ebi.ac.uk/pride/)
[![Ontologies](https://img.shields.io/badge/ontologies-OLS-7E57C2)](https://www.ebi.ac.uk/ols4/)

> **Pick a dataset → The agent fetches PRIDE + paper → You review a validated SDRF.**

Structured skills that give AI assistants expert-level capabilities for annotating,
validating, improving, and brainstorming proteomics metadata in the
[SDRF](https://github.com/bigbio/proteomics-metadata-standard) format.

## Workflow

```text
     SETUP             PLAN             ANNOTATE          VALIDATE           REFINE             SHARE
 ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
 │  Conda   │     │ Templates│     │   PXD    │     │ Columns  │     │  Score   │     │ Convert  │
 │   Pip    │────▶│ Strategy │────▶│  PRIDE   │────▶│   OLS    │────▶│  AutoFix │────▶│   PR     │
 │  Tools   │     │  Layers  │     │  Paper   │     │  Rules   │     │ Raw scan │     │ Pipeline │
 └──────────┘     └──────────┘     └──────────┘     └──────────┘     └──────────┘     └──────────┘
  /sdrf:setup   /sdrf:brainstorm   /sdrf:annotate   /sdrf:validate   /sdrf:improve   /sdrf:contribute
                /sdrf:templates                                      /sdrf:fix         /sdrf:convert
                                                                     /sdrf:review
                                                                     /sdrf:techrefine

                  ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
                  │  Format  │     │ Ontology │     │  Plain   │     │  Batch   │
                  │   Spec   │     │  Lookup  │     │   Lang   │     │ Confound │
                  │  Rules   │     │  Verify  │     │ Concepts │     │ Replic.  │
                  └──────────┘     └──────────┘     └──────────┘     └──────────┘
                 /sdrf:knowledge   /sdrf:terms     /sdrf:explain     /sdrf:design
```

## What it does

Instead of an AI guessing at ontology terms or SDRF rules, these skills teach it
**exactly how** to annotate proteomics datasets — using real tools (OLS, PRIDE, PubMed)
guided by the methodology of experienced annotators.

The SDRF specification data (column definitions, templates) lives in a git submodule
and is read at runtime — so the skills stay current when the spec evolves.

## Available skills

All 16 skills are under the `sdrf:` namespace. In Claude Code, type `/sdrf:` and autocomplete will show them all.

| Skill | What it does |
|-------|-------------|
| `/sdrf:setup` | Install dependencies (parse_sdrf, techsdrf) — conda or pip guided setup |
| `/sdrf:knowledge` | Ask about SDRF format, column rules, ontology mappings, reserved words |
| `/sdrf:templates` | Ask about templates, select templates, understand layers and selection rules |
| `/sdrf:annotate` | Full annotation workflow: PXD → PRIDE + paper → draft SDRF → validate |
| `/sdrf:validate` | Systematic validation against templates + ontology checking via OLS |
| `/sdrf:improve` | Quality analysis: specificity, completeness, consistency, score |
| `/sdrf:fix` | Auto-fix common errors (UNIMOD swaps, case, format, artifacts) |
| `/sdrf:terms` | Find and verify ontology terms for any SDRF column |
| `/sdrf:brainstorm` | Plan metadata strategy before creating an SDRF |
| `/sdrf:review` | Comprehensive quality review with cross-reference to paper + PRIDE |
| `/sdrf:explain` | Explain any column, error, or concept in plain language |
| `/sdrf:convert` | Choose and configure analysis pipelines from SDRF |
| `/sdrf:design` | Detect batch effects, confounders, replication issues |
| `/sdrf:contribute` | Contribute annotated SDRF back to sdrf-annotated-datasets via PR |
| `/sdrf:techrefine` | Verify/refine technical metadata from raw files via techsdrf |
| `/sdrf:cellline` | Translate Cellosaurus records into SDRF cell-line columns (organism, disease, sampling site, sex, ancestry) |

## Installation

### 1. Clone with submodules (required)

The SDRF specification data is included as a git submodule. You must initialize it:

```bash
# Clone with submodules:
git clone --recurse-submodules https://github.com/bigbio/sdrf-skills

# Or if already cloned without submodules:
cd sdrf-skills
git submodule update --init --recursive
```

To update the spec to the latest version:
```bash
git submodule update --remote --recursive
```

### 2. Install dependencies (recommended)

Install the Python tools used by the skills. **Conda** is recommended (includes thermorawfileparser for Thermo .raw files):

```bash
# Recommended (conda):
conda env create -f environment.yml
conda activate sdrf-skills

# Or pip:
pip install -r requirements.txt
```

For Thermo .raw files, `thermorawfileparser` is not on PyPI — use conda: `conda install -c bioconda thermorawfileparser`.

## Setup by AI Platform

<details>
<summary>Claude Code (plugin)</summary>

After dependencies are installed (step 2 above):

1. Install the plugin:
```bash
# From the official marketplace (when published):
/plugin install sdrf-skills

# Or from GitHub:
/plugin install github:bigbio/sdrf-skills
```
2. Run guided dependency setup: `/sdrf:setup`
3. Then use: `/sdrf:annotate PXD######` and/or `/sdrf:validate your_file.sdrf.tsv`

</details>

<details>
<summary>Cursor</summary>

After dependencies are installed (step 2 above):

1. Ensure you have `.cursor/rules/sdrf-skills.mdc` in your project.
2. Cursor does not run Claude Code's `SessionStart` hook, so ask when needed:
   - *"Install SDRF dependencies"*
   - *"Follow the sdrf setup workflow"*
3. The AI will use `skills/sdrf-setup/SKILL.md` to show the exact `conda` / `pip` commands.

</details>

<details>
<summary>Codex (OpenAI)</summary>

After dependencies are installed (step 2 above):

1. Follow `.codex/INSTALL.md` to symlink `skills/` and `spec/` into your Codex agents skills path.
2. When validation/ontology checks are needed, run `parse_sdrf validate-sdrf` (from `sdrf-pipelines`).

</details>

<details>
<summary>Gemini CLI</summary>

After dependencies are installed (step 2 above):

1. Gemini CLI auto-loads `GEMINI.md` from the repo root.
2. When generating SDRF, instruct Gemini to validate with:
`parse_sdrf validate-sdrf --sdrf_file ... --template ...`

</details>

<details>
<summary>OpenCode</summary>

After dependencies are installed (step 2 above):

1. Follow `.opencode/AGENTS.md` to wire the skills into your OpenCode agent.
2. Ask it to consult `skills/sdrf-setup/SKILL.md` if `parse_sdrf` / `techsdrf` are missing.

</details>

### 4. Configure MCP servers

For full SDRF annotation (PRIDE, OLS, literature), configure these MCP servers:

- **OLS** — Ontology Lookup Service (EBI)
- **PRIDE MCP** — Proteomics dataset repository
- **PubMed** — Biomedical literature
- **bioRxiv** — Preprint server

The SessionStart hook checks for `parse_sdrf` and recommends `/sdrf:setup` if dependencies are missing.

## Example Usage

### Ask about templates
```text
You: /sdrf:templates I have a DIA phosphoproteomics study on mouse brain

Claude: For your experiment, I recommend:
  1. ms-proteomics (mass spectrometry)
  2. vertebrates (Mus musculus)
  3. dia-acquisition (DIA method)

  This adds columns for: strain, developmental stage, DIA scan windows...
```

### Annotate a PRIDE dataset
```text
You: /sdrf:annotate PXD045678

Claude:
  → Fetches PRIDE metadata (organism, instrument, files)
  → Finds the paper (PMID from PRIDE → PubMed → full text from PMC)
  → Extracts sample info from methods section
  → Selects templates: ms-proteomics + human + clinical-metadata
  → Drafts SDRF with verified ontology terms from OLS
  → Validates the result
```

### Ask about SDRF rules
```text
You: /sdrf:knowledge What format should modification parameters use?

Claude: The format for comment[modification parameters] is:
  NT=<name>;AC=UNIMOD:<id>;TA=<amino acid>;MT=<Fixed|Variable>

  Example: NT=Carbamidomethyl;AC=UNIMOD:4;TA=C;MT=Fixed
  Warning: UNIMOD:1 = Acetyl, UNIMOD:21 = Phospho (most common swap!)
```

### Fix an SDRF with errors
```text
You: /sdrf:fix [paste SDRF content]

Claude:
  → Identifies: UNIMOD:21 used for Acetyl (should be UNIMOD:1)
  → Fixes case: "Male" → "male"
  → Fixes format: "58 years" → "58Y"
  → Fixes artifacts: "['breast cancer']" → "breast cancer"
  → Shows changelog → outputs corrected SDRF
```

### Contribute an annotation to the community
```text
You: /sdrf:contribute PXD045678

Claude:
  → Checks if PXD045678 already exists in datasets/
  → Validates the SDRF file
  → Forks bigbio/sdrf-annotated-datasets
  → Creates branch annotation/PXD045678
  → Commits the SDRF file to datasets/PXD045678/
  → Opens a PR with dataset summary (organism, templates, row count)
```

### Refine technical metadata from raw files
```text
You: /sdrf:techrefine PXD045678

Claude:
  → Checks techsdrf prerequisites
  → Presents refinement mode (PRIDE download vs local files)
  → Assembles command: techsdrf refine -p PXD045678 -s input.sdrf.tsv -n 5 -o refined.sdrf.tsv
  → Interprets results: instrument, tolerances, modifications, DDA/DIA
  → Shows diff: "Q Exactive" → "Q Exactive HF-X", tolerance 20ppm → 10ppm
  → Lets user approve/reject each change
```

### Clean Europe PMC full text for LLMs
```bash
python scripts/europepmc_fulltext.py PMC4047622 --format text
python scripts/europepmc_fulltext.py 24657495 --id-type pmid --section methods
python scripts/europepmc_fulltext.py 10.1016/j.jprot.2014.03.010 --id-type doi --format json
python scripts/europepmc_fulltext.py https://europepmc.org/articles/PMC10960138 --format toc
```

Use this when you need Europe PMC full text converted from noisy JATS/XML into:
- clean plain text with most citation/link clutter removed
- structured article metadata for downstream prompts
- explicit section splits like `abstract`, `methods`, `results`, `discussion`, and `conclusion`
- a machine-friendly JSON representation for future agent workflows
- canonical article links plus detected accessions such as `PXD`, `MSV`, `PRJNA`, `GSE`, and `E-MTAB`

It also supports canonical URL-style inputs like Europe PMC article URLs and `doi:...`
prefixes, plus `--xml-file` for offline parsing of previously downloaded Europe PMC XML.

### Find the right ontology term
```text
You: /sdrf:terms disease "liver cancer"

Claude:
  → Searches EFO, MONDO, DOID via OLS
  → Recommends: hepatocellular carcinoma (EFO:0000182)
  → Shows alternatives: liver carcinoma, cholangiocarcinoma
  → Checks specificity: "liver cancer" too generic → use subtype
```

## Architecture

```text
sdrf-skills/
├── .claude-plugin/plugin.json    # Claude Code — plugin manifest
├── .cursor/rules/sdrf-skills.mdc # Cursor — rules file (auto-activates on *.sdrf.tsv)
├── .codex/INSTALL.md             # Codex — installation instructions
├── .opencode/AGENTS.md           # OpenCode — agent reference
├── environment.yml               # Conda env (sdrf-pipelines, techsdrf, thermorawfileparser)
├── requirements.txt              # Pip fallback
├── scripts/
│   └── europepmc_fulltext.py     # Europe PMC full text cleaner: JATS/XML → LLM-friendly text/JSON
├── hooks/hooks.json              # Claude Code — session init + dependency check
├── hooks/check-deps.sh           # Checks parse_sdrf, recommends setup
├── spec/                         # ← Git submodule: proteomics-metadata-standard
│   └── sdrf-proteomics/
│       ├── TERMS.tsv             # Column definitions (read by skills at runtime)
│       └── sdrf-templates/       # ← Nested submodule: sdrf-templates
│           ├── templates.yaml    # Template manifest (read by skills at runtime)
│           └── {name}/{ver}/     # Individual template YAMLs
├── skills/                       # ← Portable across ALL platforms
│   ├── sdrf-setup/SKILL.md       # /sdrf:setup — guided dependency installation
│   ├── sdrf-knowledge/SKILL.md   # /sdrf:knowledge — SDRF spec, columns, ontologies
│   ├── sdrf-templates/SKILL.md   # /sdrf:templates — template system, layers, selection
│   ├── sdrf-annotate/SKILL.md    # /sdrf:annotate — full annotation workflow
│   ├── sdrf-validate/SKILL.md    # /sdrf:validate — validation + OLS checking
│   ├── sdrf-improve/SKILL.md     # /sdrf:improve — quality analysis + scoring
│   ├── sdrf-fix/SKILL.md         # /sdrf:fix — auto-fix common errors
│   ├── sdrf-terms/SKILL.md       # /sdrf:terms — ontology term lookup
│   ├── sdrf-brainstorm/SKILL.md  # /sdrf:brainstorm — metadata planning
│   ├── sdrf-review/SKILL.md      # /sdrf:review — comprehensive review
│   ├── sdrf-explain/SKILL.md     # /sdrf:explain — explain any concept
│   ├── sdrf-contribute/SKILL.md   # /sdrf:contribute — PR to community repo
│   ├── sdrf-convert/SKILL.md     # /sdrf:convert — pipeline guidance
│   ├── sdrf-design/SKILL.md      # /sdrf:design — experimental design analysis
│   ├── sdrf-techrefine/SKILL.md  # /sdrf:techrefine — techsdrf raw file refinement
│   └── sdrf-cellline/SKILL.md    # /sdrf:cellline — Cellosaurus → SDRF translation
├── CLAUDE.md                     # Claude Code — project config
├── GEMINI.md                     # Gemini CLI — project config
├── BRAINSTORM.md                 # Design document
└── README.md                     # This file
```

## Cross-Platform Design

The core of this plugin is the `skills/` directory — 15 markdown files that encode
annotation methodology. These are **platform-agnostic**. Each platform just needs a
thin shim to discover and load them:

| Platform | Config File | How It Works |
|----------|------------|--------------|
| Claude Code | `.claude-plugin/plugin.json` + `CLAUDE.md` | Native plugin — skills auto-discovered, `/sdrf:*` commands |
| Cursor | `.cursor/rules/sdrf-skills.mdc` | Rules file with glob trigger on `*.sdrf.tsv` |
| Codex | `.codex/INSTALL.md` | Symlink skills to `~/.agents/skills/` |
| Gemini CLI | `GEMINI.md` | Project-level instructions, auto-loaded |
| OpenCode | `.opencode/AGENTS.md` | Agent reference file |

The skills themselves work on any AI assistant that can read markdown and call
external APIs (OLS, PRIDE, PubMed). The specification data in `spec/` stays
current via the git submodule — no skills need updating when the spec changes.

## Why Skills Instead of an MCP Server?

The tools AI assistants need already exist as MCP servers (OLS, PRIDE, PubMed).
What was missing was **the expertise** — knowing:

- Which ontology to search for which column
- How to read a paper and extract SDRF metadata
- What the most common annotation errors are and how to fix them
- How to select the right templates for an experiment
- What "good" SDRF annotation looks like

Skills encode this expertise as structured workflows that any AI assistant follows step by step.
No custom code to build, deploy, or maintain — just markdown files that teach the AI
the methodology of an experienced SDRF annotator.

## Updating the Specification

The SDRF specification evolves independently. To pull the latest:

```bash
# Update to latest spec:
git submodule update --remote --recursive

# Commit the updated reference:
git add spec
git commit -m "Update SDRF spec to latest version"
```

Skills read `spec/` files at runtime, so updating the submodule is all that's needed.
No SKILL.md files need to be modified when columns or templates change.

## Contributing

To add a new skill:
1. Create `skills/your-skill/SKILL.md` with YAML frontmatter
2. Write the workflow instructions in markdown
3. Reference `spec/` files for any specification data (never hardcode)
4. Test with Claude Code: `/your-skill [arguments]`

## Contact

Maintained by the [BigBio](https://github.com/bigbio) team.

- **Yasset Perez-Riverol** (maintainer) — [@ypriverol](https://github.com/ypriverol) · [ypriverol@gmail.com](mailto:ypriverol@gmail.com) · [@ypriverol](https://twitter.com/ypriverol)

### Contributors

- **Asier Larrea Sebal** — [@asierlarrea](https://github.com/asierlarrea) · EMBL-EBI

For questions about the SDRF specification itself, open an issue in
[bigbio/proteomics-metadata-standard](https://github.com/bigbio/proteomics-metadata-standard).

## License

MIT

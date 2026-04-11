# sdrf-skills — SDRF Annotation Skills

Structured skills that give AI assistants expert-level capabilities for annotating,
validating, improving, and brainstorming proteomics metadata in the
[SDRF](https://github.com/bigbio/proteomics-metadata-standard) format.

## What it does

Instead of an AI guessing at ontology terms or SDRF rules, these skills teach it
**exactly how** to annotate proteomics datasets — using real tools (OLS, PRIDE, PubMed)
guided by the methodology of experienced annotators.

The SDRF specification data (column definitions, templates) lives in a git submodule
and is read at runtime — so the skills stay current when the spec evolves.

All 15 skills are under the `sdrf:` namespace. In Claude Code, type `/sdrf:` and autocomplete will show them all.

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
| `/sdrf:contribute` | Contribute annotated SDRF back to community via PR |
| `/sdrf:techrefine` | Verify/refine technical metadata from raw files via techsdrf |

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

Having trouble? See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common setup issues and fixes.

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

### What Cursor users should do

Cursor does **not** install Claude Code plugins and does **not** support `/sdrf:*` slash commands. In Cursor, you use the same workflows by:

1. Making sure the Cursor rule + workflows are present in your project
2. Opening (or attaching) SDRF-related files in chat
3. Asking in plain English (examples below)

### 1) Put the rules + workflows in your Cursor project

Pick one approach:

- **Option A (recommended): open this repository in Cursor**  
  The rule file (`.cursor/rules/sdrf-skills.mdc`) and workflows (`skills/`) are already here.

- **Option B: copy the minimum files into your own project**  
  Copy these into your project root:
  - `.cursor/rules/sdrf-skills.mdc`
  - `skills/` (all workflows)
  - `spec/` (git submodule data used by the workflows at runtime)

If you copy `spec/`, make sure submodules are initialized:

```bash
git submodule update --init --recursive
```

### 2) Use it in Cursor (how to reliably trigger the workflows)

1. Open a relevant file so the rule activates (any of the following works):
   - a `*.sdrf.tsv` file (or `*.sdrf`)
   - anything under `spec/sdrf-proteomics/`
2. In chat, **attach** the SDRF file (or paste the relevant section) and ask for what you want.

Examples you can copy/paste into Cursor chat:

- **Environment setup**: “Follow `skills/sdrf-setup/SKILL.md` and tell me the exact conda commands for this repo.”
- **Annotate a PRIDE dataset**: “Annotate `PXD045678` and draft an SDRF. Use the templates and validate.”
- **Validate**: “Validate the attached SDRF against the right template(s) and list required fixes.”
- **Fix common issues**: “Fix the common SDRF errors in the attached file (UNIMOD swaps, reserved words, formatting).”
- **Find ontology terms**: “For `characteristics[disease]`, find the best term for ‘liver cancer’ and include label + accession.”

### 3) Note about hooks

Cursor does not run Claude Code’s `SessionStart` hook, so you won’t get an automatic dependency reminder. If something isn’t installed, just ask for setup and the assistant should follow `skills/sdrf-setup/SKILL.md`.

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
  → Checks if PXD045678 already exists in annotated-projects/
  → Validates the SDRF file
  → Forks bigbio/proteomics-sample-metadata
  → Creates branch annotation/PXD045678
  → Commits the SDRF file to annotated-projects/PXD045678/
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
│   └── sdrf-techrefine/SKILL.md   # /sdrf:techrefine — techsdrf raw file refinement
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

## License

MIT

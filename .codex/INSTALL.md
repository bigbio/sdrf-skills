# sdrf-skills for Codex

## Installation

First, ensure submodules are initialized and install dependencies:

```bash
git submodule update --init --recursive
conda env create -f environment.yml && conda activate sdrf-skills
# Or: pip install -r requirements.txt
```

Symlink the skills and spec directories into your Codex agents skills path:

```bash
ln -s "$(pwd)/skills" ~/.agents/skills/sdrf-skills
ln -s "$(pwd)/spec" ~/.agents/skills/sdrf-skills/spec
```

Or copy both directories:

```bash
cp -r skills/ ~/.agents/skills/sdrf-skills/
cp -r spec/ ~/.agents/skills/sdrf-skills/spec/
```

## What it provides

16 structured workflows (SKILL.md files) that encode expert-level SDRF annotation methodology:

| Skill | Purpose |
|-------|---------|
| sdrf-setup | Install dependencies (parse_sdrf, techsdrf) — conda or pip setup |
| sdrf-autoresearch | Autonomous retained-improvement loop over one dataset, a manifest, or a dataset class |
| sdrf-knowledge | SDRF format rules, column names, ontology mappings |
| sdrf-templates | Template system, layer selection, mutual exclusivity |
| sdrf-annotate | Full annotation: PXD → PRIDE + paper → draft SDRF |
| sdrf-validate | Validation against templates + OLS checking |
| sdrf-improve | Quality scoring: specificity, completeness, consistency |
| sdrf-fix | Auto-fix UNIMOD swaps, case, format, artifacts |
| sdrf-terms | Ontology term lookup for any SDRF column |
| sdrf-brainstorm | Pre-annotation metadata planning |
| sdrf-review | Quality review with paper + PRIDE cross-reference |
| sdrf-explain | Plain-language SDRF education |
| sdrf-convert | Pipeline selection (MaxQuant, DIA-NN, quantms) |
| sdrf-design | Experimental design analysis |
| sdrf-contribute | Contribute annotation via PR to community repo |
| sdrf-techrefine | Verify/refine technical metadata from raw files via techsdrf |

## Usage

Each SKILL.md file contains a complete workflow. Reference them from your Codex instructions:

```text
When annotating SDRF files, follow the workflow in skills/sdrf-annotate/SKILL.md
```

For autonomous loops, reference:

```text
Use the workflow in skills/sdrf-autoresearch/SKILL.md with target, profile, objective, evidence, stop, and write settings.
```

## Prerequisites

These skills reference external APIs (OLS, PRIDE, PubMed) for ontology validation
and metadata retrieval. Configure appropriate API access in your Codex environment.

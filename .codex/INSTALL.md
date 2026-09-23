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
ln -s "$(pwd)/tools" ~/.agents/skills/sdrf-skills/tools   # contract and build helpers
```

Or copy both directories:

```bash
cp -r skills/ ~/.agents/skills/sdrf-skills/
cp -r spec/ ~/.agents/skills/sdrf-skills/spec/
cp -r tools/ ~/.agents/skills/sdrf-skills/tools/
```

## What it provides

Five skills (SKILL.md files) that encode expert-level SDRF annotation methodology; `sdrf-annotate` carries
seventeen `references/` it reads on demand:

| Skill | Purpose |
|-------|---------|
| sdrf-annotate | Full annotation: PXD → PRIDE + paper → draft SDRF |
| sdrf-metascreen | Shortlist PRIDE / MassIVE / ProteomeXchange studies → resumable TSV |
| sdrf-autoresearch | Autonomous retained-improvement loop over one dataset, a manifest, or a dataset class |
| sdrf-adversarial-review | Independent fresh-context falsification review with hash-bound approval |
| sdrf-contribute | Contribute annotation via PR to community repo |

## Bundled tools: contract and build

Install the helpers once: `pip install -e <sdrf-skills checkout>` (brings `sdrf-pipelines`), then `sdrf-tools doctor`.

Two deterministic helpers keep annotation short and structurally valid. Run them as `sdrf-tools ...`:

- `sdrf-tools contract -t ms-proteomics [-t human ...]` — prints the column contract of the
  template union: every column in order, required/optional/multiple, value form, permitted reserved
  words and the ontologies to search. Read this instead of `TERMS.tsv` and the template YAMLs.
- `sdrf-tools build --samples samples.tsv --technical technical.tsv --files files.json
  -t ms-proteomics [-t ...] -o output.sdrf.tsv` — expands a sample table (one row per source and
  replicate; `files` = the fractions of one injection; `label` = `label free sample` or one channel)
  plus a technical table (run-level `comment[...]` values, `|` between multiple values) into the SDRF:
  fractions, technical replicates, channel rows, repeated columns and column order are decided by
  code. It refuses, and writes nothing, on a file outside `files.json`, a file claimed twice, two rows
  sharing a (source, biological replicate, technical replicate, fraction) coordinate, or an incomplete
  channel map — it never fills a channel in.

Fix validation errors in the two tables and rebuild; never edit the SDRF by hand.

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

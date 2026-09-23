# sdrf-skills — SDRF Annotation Skills

## Overview

20 structured workflow files that encode expert-level SDRF (Sample and Data
Relationship Format) annotation methodology for proteomics.

## Skills Directory

All workflows are in `skills/*/SKILL.md`. Each file has YAML frontmatter (name,
description) followed by a step-by-step workflow in Markdown.

### Reference Guide

| Skill Directory | What It Does |
|----------------|-------------|
| `sdrf-setup` | Install dependencies (parse_sdrf, techsdrf) — conda or pip guided setup |
| `sdrf-metascreen` | Screen/shortlist PRIDE, MassIVE, or ProteomeXchange studies against user-defined criteria → evidence-backed TSV |
| `sdrf-autoresearch` | Autonomous retained-improvement loop over one dataset, a manifest, or a dataset class |
| `sdrf-knowledge` | SDRF format rules, column naming, ontology-to-column mapping |
| `sdrf-templates` | Template layer system (Technology → Organism → Experiment → Clinical → Platform) |
| `sdrf-annotate` | Full annotation workflow: PXD → PRIDE metadata + publication → SDRF draft |
| `sdrf-validate` | Validation: structural checks + OLS ontology verification |
| `sdrf-fix` | Auto-fix 10 common error patterns (UNIMOD swaps, case, format, artifacts) |
| `sdrf-review` | Quality review: cross-reference SDRF against publication and PRIDE metadata |
| `sdrf-adversarial-review` | Independent fresh-context falsification review with hash-bound approval |
| `sdrf-annotate-reviewed` | Annotation, validation, independent review, repair, and re-review orchestration |
| `sdrf-convert` | Pipeline selection and conversion commands (MaxQuant, DIA-NN, OpenMS, quantms) |
| `sdrf-design` | Experimental design analysis: batch effects, confounders, replication assessment |
| `sdrf-contribute` | Contribute annotated SDRF to community repo via PR (automated or guided) |
| `sdrf-techrefine` | Verify/refine technical metadata (instrument, tolerances, mods, DDA/DIA) from raw files via techsdrf |
| `sdrf-cellline` | Look up cell lines via Cellosaurus and translate them into SDRF cell-line columns (organism, disease, sampling site, sex, ancestry, age) |

## Specification Data

The SDRF specification lives in the `spec/` git submodule:
- `spec/sdrf-proteomics/TERMS.tsv` — column definitions, ontology mappings, allowed values
- `spec/sdrf-proteomics/sdrf-templates/templates.yaml` — template inventory, versions, inheritance

Skills read these files at runtime. Never hardcode specification data.

## Bundled tools: contract and build

Two deterministic helpers keep annotation short and structurally valid. Run them from the
sdrf-skills checkout (`PYTHONPATH=<checkout> python3 -m tools ...`; Claude Code sets
`$CLAUDE_PLUGIN_ROOT` for this):

- `python3 -m tools contract -t ms-proteomics [-t human ...]` — prints the column contract of the
  template union: every column in order, required/optional/multiple, value form, permitted reserved
  words and the ontologies to search. Read this instead of `TERMS.tsv` and the template YAMLs.
- `python3 -m tools build --samples samples.tsv --technical technical.tsv --files files.json
  -t ms-proteomics [-t ...] -o output.sdrf.tsv` — expands a sample table (one row per source and
  replicate; `files` = the fractions of one injection; `label` = `label free sample` or one channel)
  plus a technical table (run-level `comment[...]` values, `|` between multiple values) into the SDRF:
  fractions, technical replicates, channel rows, repeated columns and column order are decided by
  code. It refuses, and writes nothing, on a file outside `files.json`, a file claimed twice, two rows
  sharing a (source, biological replicate, technical replicate, fraction) coordinate, or an incomplete
  channel map — it never fills a channel in.

Fix validation errors in the two tables and rebuild; never edit the SDRF by hand.

## Key Rules

1. Never guess ontology accessions — verify via OLS
2. Column names come from the contract (`python3 -m tools contract -t ...`) for the chosen templates; `spec/sdrf-proteomics/TERMS.tsv` is the underlying glossary
3. PXD accession → fetch PRIDE project + publication before annotation
4. Template selection before annotation — read `spec/sdrf-proteomics/sdrf-templates/templates.yaml`
5. All ontology terms: label + accession (e.g., "breast carcinoma" EFO:0000305)
6. Modification format: NT=;AC=UNIMOD:;TA=;MT= (watch UNIMOD:1↔21 swap)
7. Build the SDRF with `python3 -m tools build` from `samples.tsv` + `technical.tsv`; never hand-write its structure; validate with `parse_sdrf validate-sdrf -s X -t T1 [-t T2 ...]`, at most two rounds, fixing values in the tables and rebuilding

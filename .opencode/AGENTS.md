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
| `sdrf-annotate` | Full annotation workflow: PXD → PRIDE metadata + publication → SDRF draft |
| `sdrf-adversarial-review` | Independent fresh-context falsification review with hash-bound approval |
| `sdrf-contribute` | Contribute annotated SDRF to community repo via PR (automated or guided) |
| `sdrf-campaign` | Screen a class of studies against your criteria into a resumable TSV, then loop annotate over the included ones |

## Specification Data

The SDRF specification lives in the `spec/` git submodule:
- `spec/sdrf-proteomics/TERMS.tsv` — column definitions, ontology mappings, allowed values
- `spec/sdrf-proteomics/sdrf-templates/templates.yaml` — template inventory, versions, inheritance

Skills read these files at runtime. Never hardcode specification data.

## Bundled tools: contract and build

Install the helpers once: `pip install -e <sdrf-skills checkout>` (brings `sdrf-pipelines`), then `sdrf-tools doctor`.

Two deterministic helpers keep annotation short and structurally valid. Run them from the
sdrf-skills checkout (`sdrf-tools ...`; Claude Code sets
`$CLAUDE_PLUGIN_ROOT` for this):

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

## Key Rules

1. Never guess ontology accessions — verify via OLS
2. Column names come from the contract (`sdrf-tools contract -t ...`) for the chosen templates; `spec/sdrf-proteomics/TERMS.tsv` is the underlying glossary
3. PXD accession → fetch PRIDE project + publication before annotation
4. Template selection before annotation — read `spec/sdrf-proteomics/sdrf-templates/templates.yaml`
5. All ontology terms: label + accession (e.g., "breast carcinoma" EFO:0000305)
6. Modification format: NT=;AC=UNIMOD:;TA=;MT= (watch UNIMOD:1↔21 swap)
7. Build the SDRF with `sdrf-tools build` from `samples.tsv` + `technical.tsv`; never hand-write its structure; validate with `parse_sdrf validate-sdrf -s X -t T1 [-t T2 ...]`, at most two rounds, fixing values in the tables and rebuilding

## The review gate on this platform

Every annotation must end with `sdrf-adversarial-review` run in a context that never saw the producer's
reasoning. Claude Code dispatches it automatically at annotate's Step 9.5. Here, open a **separate session**,
give it only the SDRF path, the evidence manifest, the spec revision and the validation output, and have it
follow `skills/sdrf-adversarial-review/SKILL.md`; then enforce the receipt with
`sdrf-tools review-gate gate --cwd <repo-root>` (exit 1 = review still pending). Never let the session that
wrote the file approve it.

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
| `sdrf-improve` | Quality scoring across 5 dimensions (completeness, specificity, consistency, compliance, clarity) |
| `sdrf-fix` | Auto-fix 10 common error patterns (UNIMOD swaps, case, format, artifacts) |
| `sdrf-terms` | Ontology term lookup with column-aware routing (disease→EFO, tissue→UBERON, etc.) |
| `sdrf-brainstorm` | Pre-annotation planning: templates, similar experiments, column recommendations |
| `sdrf-review` | Quality review: cross-reference SDRF against publication and PRIDE metadata |
| `sdrf-adversarial-review` | Independent fresh-context falsification review with hash-bound approval |
| `sdrf-annotate-reviewed` | Annotation, validation, independent review, repair, and re-review orchestration |
| `sdrf-explain` | Plain-language education about any SDRF column, error, or concept |
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

## Key Rules

1. Never guess ontology accessions — verify via OLS
2. Column names follow exact patterns from `spec/sdrf-proteomics/TERMS.tsv`
3. PXD accession → fetch PRIDE project + publication before annotation
4. Template selection before annotation — read `spec/sdrf-proteomics/sdrf-templates/templates.yaml`
5. All ontology terms: label + accession (e.g., "breast carcinoma" EFO:0000305)
6. Modification format: NT=;AC=UNIMOD:;TA=;MT= (watch UNIMOD:1↔21 swap)

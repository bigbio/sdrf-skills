# sdrf-skills — SDRF Annotation Skills

Structured workflows for expert-level SDRF (Sample and Data Relationship Format)
annotation in proteomics.

## Available Workflows

The `skills/` directory contains 20 workflow files (SKILL.md) that encode community
annotation expertise. When working with SDRF files, consult the relevant skill:

- **Screen**: `skills/sdrf-metascreen/SKILL.md` — shortlist PRIDE/MassIVE/ProteomeXchange studies against user criteria → evidence-backed TSV
- **Autoresearch**: `skills/sdrf-autoresearch/SKILL.md` — autonomous retained-improvement loop over a dataset, manifest, or dataset class
- **Annotation**: `skills/sdrf-annotate/SKILL.md` — create an SDRF from a PXD and always have it independently reviewed; review an existing .sdrf.tsv; or plan. The only entry point for annotation and review
- **Planning**: `skills/sdrf-annotate/SKILL.md` — pre-annotation metadata strategy
- **Adversarial review**: `skills/sdrf-adversarial-review/SKILL.md` — isolated evidence-first review with hash-bound approval
- **Contribute**: `skills/sdrf-contribute/SKILL.md` — PR to community repository

## Specification Data

The SDRF specification lives in the `spec/` git submodule:
- **Column definitions**: `spec/sdrf-proteomics/TERMS.tsv` — read this for column names, ontology mappings, allowed values
- **Template manifest**: `spec/sdrf-proteomics/sdrf-templates/templates.yaml` — read this for template inventory
- **Individual templates**: `spec/sdrf-proteomics/sdrf-templates/{name}/{version}/{name}.yaml`

Skills reference these files at runtime. Never hardcode specification data.

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

1. Never guess ontology accessions — verify via OLS (Ontology Lookup Service)
2. Never invent SDRF column names — print the contract (`sdrf-tools contract -t ...`) for the valid columns of the chosen templates; `spec/sdrf-proteomics/TERMS.tsv` is the underlying glossary
3. When given a PXD accession, fetch project + publication context first
4. Select templates before starting annotation — read `spec/sdrf-proteomics/sdrf-templates/templates.yaml`
5. All terms need both label AND accession (e.g., "breast carcinoma" EFO:0000305)
6. Modifications: NT=;AC=UNIMOD:;TA=;MT= format (watch for UNIMOD:1↔21 swap)
7. Reserved words: "not available", "not applicable" — never "N/A", "NA", "unknown"
8. Build the SDRF with `sdrf-tools build` from `samples.tsv` + `technical.tsv`; never hand-write its structure
9. Always validate with `parse_sdrf validate-sdrf -s X -t T1 [-t T2 ...]` (several `-t` validate against the union) before presenting an SDRF, at most two rounds, fixing values in the tables and rebuilding; update the spec first with `git submodule update --remote --recursive`

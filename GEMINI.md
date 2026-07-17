# sdrf-skills — SDRF Annotation Skills

Structured workflows for expert-level SDRF (Sample and Data Relationship Format)
annotation in proteomics.

## Available Workflows

The `skills/` directory contains 20 workflow files (SKILL.md) that encode community
annotation expertise. When working with SDRF files, consult the relevant skill:

- **Setup**: `skills/sdrf-setup/SKILL.md` — install parse_sdrf, techsdrf (conda or pip)
- **Screen**: `skills/sdrf-metascreen/SKILL.md` — shortlist PRIDE/MassIVE/ProteomeXchange studies against user criteria → evidence-backed TSV
- **Autoresearch**: `skills/sdrf-autoresearch/SKILL.md` — autonomous retained-improvement loop over a dataset, manifest, or dataset class
- **Format rules**: `skills/sdrf-knowledge/SKILL.md` — column naming, ontology mappings, modification format
- **Templates**: `skills/sdrf-templates/SKILL.md` — 5-layer template system, selection rules
- **Annotation**: `skills/sdrf-annotate/SKILL.md` — full PXD → SDRF workflow
- **Validation**: `skills/sdrf-validate/SKILL.md` — template + ontology checking
- **Quality**: `skills/sdrf-improve/SKILL.md` — scoring and improvement suggestions
- **Fixes**: `skills/sdrf-fix/SKILL.md` — auto-fix common errors
- **Terms**: `skills/sdrf-terms/SKILL.md` — ontology term lookup
- **Planning**: `skills/sdrf-brainstorm/SKILL.md` — metadata strategy
- **Review**: `skills/sdrf-review/SKILL.md` — cross-reference with publications
- **Adversarial review**: `skills/sdrf-adversarial-review/SKILL.md` — isolated evidence-first review with hash-bound approval
- **Reviewed annotation**: `skills/sdrf-annotate-reviewed/SKILL.md` — producer/reviewer loop with mandatory re-review
- **Education**: `skills/sdrf-explain/SKILL.md` — explain SDRF concepts
- **Pipelines**: `skills/sdrf-convert/SKILL.md` — pipeline configuration
- **Design**: `skills/sdrf-design/SKILL.md` — experimental design analysis
- **Contribute**: `skills/sdrf-contribute/SKILL.md` — PR to community repository
- **Tech Refine**: `skills/sdrf-techrefine/SKILL.md` — verify/refine technical metadata from raw files via techsdrf
- **Cell line**: `skills/sdrf-cellline/SKILL.md` — translate Cellosaurus records into SDRF cell-line columns (organism, disease, sex, sampling site, ancestry, age)

## Specification Data

The SDRF specification lives in the `spec/` git submodule:
- **Column definitions**: `spec/sdrf-proteomics/TERMS.tsv` — read this for column names, ontology mappings, allowed values
- **Template manifest**: `spec/sdrf-proteomics/sdrf-templates/templates.yaml` — read this for template inventory
- **Individual templates**: `spec/sdrf-proteomics/sdrf-templates/{name}/{version}/{name}.yaml`

Skills reference these files at runtime. Never hardcode specification data.

## Key Rules

1. Never guess ontology accessions — verify via OLS (Ontology Lookup Service)
2. Never invent SDRF column names — read `spec/sdrf-proteomics/TERMS.tsv` for valid columns
3. When given a PXD accession, fetch project + publication context first
4. Select templates before starting annotation — read `spec/sdrf-proteomics/sdrf-templates/templates.yaml`
5. All terms need both label AND accession (e.g., "breast carcinoma" EFO:0000305)
6. Modifications: NT=;AC=UNIMOD:;TA=;MT= format (watch for UNIMOD:1↔21 swap)
7. Reserved words: "not available", "not applicable" — never "N/A", "NA", "unknown"
8. Always validate with `parse_sdrf validate-sdrf --sdrf_file X --template Y` before presenting an SDRF; update the spec first with `git submodule update --remote --recursive`

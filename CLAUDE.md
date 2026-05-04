# sdrf-skills — SDRF Annotation Skills

Structured skills that give AI assistants expert-level capabilities for
SDRF (Sample and Data Relationship Format) annotation in proteomics.

## What This Does

16 structured workflows (SKILL.md files) that guide AI assistants through SDRF tasks
using existing MCP tools (OLS, PRIDE, PubMed, bioRxiv, EuropePMC).
Instead of guessing at ontology terms or validation rules, skills encode the
community's annotation expertise as repeatable methodology.

## Specification Data (Dynamic via Submodule)

The SDRF specification lives in the `spec/` git submodule:

- **Column definitions**: `spec/sdrf-proteomics/TERMS.tsv`
- **Template manifest**: `spec/sdrf-proteomics/sdrf-templates/templates.yaml`
- **Individual templates**: `spec/sdrf-proteomics/sdrf-templates/{name}/{version}/{name}.yaml`

Skills read these files at runtime. When the spec changes, run `git submodule update --remote --recursive` to pull the latest.

## Available Skills (all under `sdrf:` namespace)

All 16 skills are user-invocable. Type `/sdrf:` and autocomplete will show them all.

| Command | Purpose |
|---------|---------|
| `/sdrf:setup` | Install dependencies (parse_sdrf, techsdrf) — conda or pip guided setup |
| `/sdrf:autoresearch` | Autonomous retained-improvement loop over one dataset, a manifest, or a dataset class |
| `/sdrf:knowledge` | SDRF format rules, column definitions (from TERMS.tsv), ontology routing, modification format, reserved words |
| `/sdrf:templates` | Template system (from templates.yaml), selection rules, mutual exclusivity, inheritance |
| `/sdrf:annotate` | Full annotation: PXD → PRIDE + paper → select templates → draft SDRF → validate |
| `/sdrf:validate` | Validate against templates (columns from TERMS.tsv) with OLS ontology verification |
| `/sdrf:improve` | Quality scoring (5 dimensions, weighted formula), specificity and completeness analysis |
| `/sdrf:fix` | Auto-fix 10 error patterns (UNIMOD swaps, case, format, artifacts) + re-validate |
| `/sdrf:terms` | Ontology term lookup with column-aware routing (from TERMS.tsv `values` field) |
| `/sdrf:brainstorm` | Plan metadata strategy: templates, columns, design considerations |
| `/sdrf:review` | Quality review with PRIDE + paper cross-reference and conflict resolution |
| `/sdrf:explain` | Explain any SDRF column, error, or concept in plain language |
| `/sdrf:convert` | Pipeline selection (MaxQuant, DIA-NN, OpenMS, quantms) + conversion commands |
| `/sdrf:design` | Experimental design: batch effects, confounders, replication, MSstats contrasts |
| `/sdrf:contribute` | Contribute annotated SDRF back to sdrf-annotated-datasets via PR (automated or guided) |
| `/sdrf:techrefine` | Verify/refine technical metadata (instrument, tolerances, mods, DDA/DIA) from raw files via techsdrf |
| `/sdrf:cellline` | Look up cell lines via Cellosaurus (REST API or bulk file) and translate them into SDRF cell-line columns (organism, disease, sampling site, sex, ancestry, age) |

## MCP Servers Used

These skills expect the following MCP servers to be available:
- **OLS** — Ontology term validation and search (NCBITaxon, UBERON, EFO, MONDO, CL, MS, UNIMOD, HANCESTRO, CHEBI, XLMOD, PRIDE, PATO)
- **PRIDE MCP** — Project metadata, file listings, dataset search, EuropePMC search
- **PubMed** — Publication metadata, full text from PMC, ID conversion (PMID↔PMCID↔DOI)
- **bioRxiv** — Preprint search for recent experimental designs

## Key Rules

1. NEVER guess ontology accessions — always verify via OLS
2. NEVER invent SDRF column names — read TERMS.tsv from `spec/sdrf-proteomics/TERMS.tsv`
3. When a PXD accession is given, ALWAYS fetch PRIDE project + publication before annotating
4. Template selection BEFORE annotation begins — read `spec/sdrf-proteomics/sdrf-templates/templates.yaml`
5. All ontology terms: label + accession (e.g., "breast carcinoma" with MONDO:0007254)
6. Modification format: `NT=name;AC=UNIMOD:id;TA=aa;MT=Fixed|Variable`
7. UNIMOD:1 = Acetyl, UNIMOD:21 = Phospho — the #1 most common swap
8. Reserved words: "not available", "not applicable" — NEVER "N/A", "NA", "unknown"
9. Multiple `comment[modification parameters]` columns are normal (one per modification)
10. Multiple `comment[sdrf template]` columns are normal (one per template)
11. ALWAYS validate with `parse_sdrf validate-sdrf --sdrf_file X --template Y` before presenting any produced SDRF to the user — update spec first with `git submodule update --remote --recursive`
12. When the user asks for autonomous large-scale annotation, use `/sdrf:autoresearch` to resolve the target set, choose an objective, and run retained improvement rounds until the configured stop rule fires
13. For blood-plasma discovery or biomarker campaigns, default to `Homo sapiens` only and require manuscript-backed plasma confirmation before promoting a dataset into annotation

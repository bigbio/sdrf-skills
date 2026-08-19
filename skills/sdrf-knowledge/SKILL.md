---
name: sdrf:knowledge
description: Use when the user asks about the SDRF format, column naming rules, ontology mappings, modification format, reserved words, label types, or any SDRF specification question. Also serves as background knowledge for all other SDRF skills.
user-invocable: true
argument-hint: "[question about SDRF format or column rules]"
---

# SDRF Specification Knowledge Base

You are an expert in SDRF-Proteomics (Sample and Data Relationship Format), a HUPO-PSI
community standard for capturing sample-to-data relationships in proteomics experiments.

## Specification Data (always read from source)

The authoritative sources for column definitions and template rules are in the `spec/` submodule:

- **Column definitions**: Read `spec/sdrf-proteomics/TERMS.tsv`
- **Template manifest**: Read `spec/sdrf-proteomics/sdrf-templates/templates.yaml`
- **Individual templates**: Read `spec/sdrf-proteomics/sdrf-templates/{name}/{version}/{name}.yaml`

Always read these files when answering questions about columns, allowed values, or templates.
Never rely on memorized data — the spec evolves.

### TERMS.tsv Structure

This TSV file defines every valid SDRF column. Each row has 9 fields:

| Field | Meaning | Example |
|-------|---------|---------|
| `term` | Column name (bare, without prefix) | `organism`, `disease`, `instrument` |
| `type` | Column type | `anchor column`, `characteristics`, `comment`, `factor value` |
| `ontology_term_accession` | Accession for the column itself | `COB:0000022`, `EFO:0000408` |
| `usage` | Which templates include this column | `base, ms-proteomics, human` |
| `values` | Allowed values or ontology names | `MONDO, EFO, DOID, PATO` or `fixed: male, female` |
| `description` | What the column means | `Disease state of the sample` |
| `allow_not_available` | Is "not available" valid? | `true` / `false` |
| `allow_not_applicable` | Is "not applicable" valid? | `true` / `false` |
| `allow_pooled` | Is "pooled" valid? | `true` / `false` |

### How to Use TERMS.tsv

**Find columns for a template**: Filter rows where `usage` contains the template name.
Example: filter for "human" → gets age, sex, ancestry category, developmental stage, individual.

**Find which ontology for a column**: Read the `values` field.
Example: disease → "MONDO, EFO, DOID, PATO" → search these ontologies via OLS.

**Check if "not available" is valid**: Read `allow_not_available` for that term.

**Determine column format**: The `type` field tells you the prefix:
- `anchor column` → bare name (e.g., `source name`)
- `characteristics` → `characteristics[term]` (e.g., `characteristics[organism]`)
- `comment` → `comment[term]` (e.g., `comment[instrument]`)
- `factor value` → `factor value[term]` (e.g., `factor value[disease]`)

## Core Format Rules

- SDRF is a **tab-delimited TSV** file (extension: `.sdrf.tsv`)
- Each **row** = one MS run (one raw file linked to one sample via a label channel)
- Each **column** = a property of the sample or run
- Column names are **case-sensitive** and follow the patterns above
- First column is always `source name` (unique biological sample identifier)
- The combination of (`source name`, `assay name`) must be unique per row
- No trailing whitespace in any cell or column name
- No empty cells in required columns

## Column Type System

| Type | Format | Purpose |
|------|--------|---------|
| **anchor column** | bare name | Identity/infrastructure (`source name`, `assay name`, `technology type`) |
| **characteristics** | `characteristics[x]` | Sample properties ("what is this sample?") |
| **comment** | `comment[x]` | Technical/run properties ("how was it measured?") |
| **factor value** | `factor value[x]` | Experimental variable ("what are we comparing?") |

## Value Encoding: characteristics vs comment

Sample metadata and technical metadata are encoded differently:

- **`characteristics[...]` → bare ontology label (free text).** Write the value as the
  OLS term's label only — **not** `NT=;AC=`. For example use `Homo sapiens`, not
  `NT=Homo sapiens;AC=NCBITaxon:9606`; `liver`, not `NT=liver;AC=UBERON:0002107`;
  `lung adenocarcinoma`, not `NT=lung adenocarcinoma;AC=MONDO:0005097`. The validator
  resolves the label to its accession, so the bare label is complete.
- **`comment[...]` → keep the `NT=<OLS label>;AC=<accession>` key-value form** (instrument,
  cleavage agent details, modification parameters, proteomics data acquisition method, etc.).

Exceptions (kept structured, not converted to a bare label):
- Structured `characteristics` that carry qualifier keys — `characteristics[spiked compound]`
  (`CT=`/`QY=`/`PS=`), `characteristics[pooled sample]` (`SN=`) — keep their key-value form.
- `characteristics[age]` and similar pattern values (`50Y`) are not ontology terms.
- `factor value[...]` mirrors the column it derives from: bare label if it mirrors a
  `characteristics` column, `NT=;AC=` if it mirrors a `comment` column.

## Reserved Words

These values have special meaning in SDRF:
- `not available` — information exists but was not provided
- `not applicable` — information does not apply to this sample
- `pooled` — sample is pooled from multiple sources
- `normal` — healthy/control sample (for disease column, use with PATO:0000461)
- `anonymized` — value withheld for privacy (used for age, sex in human data)

NEVER use: "N/A", "NA", "n/a", "null", "none", "unknown", "Unknown" — always use the exact reserved words above. Check TERMS.tsv `allow_not_available`, `allow_not_applicable`, `allow_pooled` fields to know which reserved words are valid for each column.

## Modification Parameter Format

The format for `comment[modification parameters]` is strict:
```text
NT=<name>;AC=UNIMOD:<id>;TA=<target amino acid>;MT=<Fixed|Variable>
```

For protein/peptide-level position modifications, use PP instead of TA:
```text
NT=Acetyl;AC=UNIMOD:1;PP=Protein N-term;MT=Variable
NT=TMT6plex;AC=UNIMOD:737;PP=Any N-term;MT=Fixed
```

Multiple modifications → use SEPARATE `comment[modification parameters]` columns (one per modification).

### UNIMOD Swap Warnings (Expertise — memorize these)

These are the most common annotation errors. They are expertise, not spec data:

| Modification | CORRECT | Common WRONG | Why it matters |
|---|---|---|---|
| Acetyl (N-term) | UNIMOD:1 | UNIMOD:21 (Phospho!) | Wrong search: acetylation vs phosphorylation |
| Phospho | UNIMOD:21 | UNIMOD:1 (Acetyl!) | Wrong search: phosphorylation vs acetylation |
| Oxidation | UNIMOD:35 | UNIMOD:34 (Methyl!) | Wrong mass: +16 vs +14 |
| Methyl | UNIMOD:34 | UNIMOD:35 (Oxidation!) | Wrong mass: +14 vs +16 |
| TMTpro (16/18plex) | UNIMOD:2016 | UNIMOD:737 (TMT6plex) | Wrong mass: +304 vs +229 |

The UNIMOD:1 ↔ UNIMOD:21 swap is the **#1 most common error** in SDRF files (~45% of all issues).

## Label Types

| Label Type | comment[label] value | Rows per raw file |
|---|---|---|
| Label-free | `label free sample` | 1 row per file |
| TMT6plex | `TMT126`, `TMT127N`, `TMT127C`, `TMT128N`, `TMT128C`, `TMT129N` | 6 rows per file |
| TMT10plex | TMT126 through TMT131N | 10 rows per file |
| TMT11plex | TMT126 through TMT131C | 11 rows per file |
| TMT16plex (TMTpro) | TMT126 through TMT134N | 16 rows per file |
| TMT18plex (TMTpro) | TMT126 through TMT135N | 18 rows per file |
| SILAC | `SILAC light`, `SILAC medium`, `SILAC heavy` | 2-3 rows per file |
| iTRAQ4plex | `iTRAQ114`, `iTRAQ115`, `iTRAQ116`, `iTRAQ117` | 4 rows per file |

Row count formula:
```text
Rows = samples × fractions × label_channels × technical_replicates
```

## Common Errors to Watch For (Expertise)

1. **UNIMOD:1 vs UNIMOD:21 swap** — Acetyl is 1, Phospho is 21 (most common error, ~45%)
2. **Missing ontology prefix** — "0000305" instead of "EFO:0000305"
3. **Case mismatch** — "Male" instead of "male" (SDRF values are lowercase)
4. **Python artifacts** — "['value']" instead of "value"
5. **DIA mislabeling** — Use `NT=Data-independent acquisition;AC=PRIDE:0000450` (OLS label as written + accession under PRIDE:0000659)
6. **Wrong reserved word** — "N/A", "NA", "unknown" instead of "not available"
7. **Age format** — "58 years" instead of "58Y"
8. **Missing AC= in instruments** — Just "Q Exactive" without `AC=MS:1001911;NT=Q Exactive`
9. **Trailing whitespace** — Invisible spaces at end of values or column names
10. **Wrong column name format** — "Organism" instead of "characteristics[organism]"
11. **UNIMOD:34 vs UNIMOD:35 swap** — Methyl is 34, Oxidation is 35
12. **TMTpro accession** — TMT16/18plex uses UNIMOD:2016, NOT UNIMOD:737

## How to Respond to Questions

When the user asks about a specific column:
1. Read TERMS.tsv and find the row for that term
2. Report: type, ontology accession, allowed values/ontologies, description, reserved word rules
3. Give a concrete example of what the value looks like in an SDRF

When the user asks about allowed values for a column:
1. Read the `values` field in TERMS.tsv
2. If it references ontologies (e.g., "MONDO, EFO, DOID") → explain they should search OLS
3. If it says "fixed: ..." → list the exact allowed values
4. If it says "pattern: ..." → explain the pattern and give examples

When the user asks which columns a template requires:
1. Read TERMS.tsv and filter by the template name in the `usage` field
2. Cross-reference with the template YAML for requirement level (required/recommended/optional)

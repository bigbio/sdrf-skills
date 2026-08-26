---
name: sdrf:knowledge
description: Use when the user asks about the SDRF format, column naming rules, ontology mappings, modification format, reserved words, label types, or any SDRF specification question, wants a plain-language explanation of a column/error/concept, or needs to find/verify/compare ontology terms and accessions for a column. Also serves as background knowledge for all other SDRF skills.
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
- Row identity: (`source name`, `assay name`, `comment[label]`) MUST be unique (error); (`source name`, `assay name`) SHOULD be unique (warning). In multiplexed (TMT/iTRAQ) data the same `assay name` deliberately repeats across label channels, so `source name`+`assay name` alone is NOT unique.
- De-duplication coordinate: (`source name`, `characteristics[biological replicate]`, `comment[technical replicate]`, `comment[fraction identifier]`) must be unique across rows — never use `technical replicate` or `fraction identifier` as a row counter
- No trailing whitespace in any cell or column name
- No empty cells in required columns
- **Data files are vendor RAW** (`.raw`/`.d`/`.wiff`/`.wiff2`) in `comment[data file]` — never peak lists (`.mgf`/`.mzML`/`.mzXML`); a peak-list reference validates structurally but breaks reprocessing
- **At least one `factor value[...]`** column must be present (the experimental variable)
- **Acquisition method**: `comment[proteomics data acquisition method]` is REQUIRED for MS files and must be a descendant of `PRIDE:0000659` (DDA `PRIDE:0000627`, DIA `PRIDE:0000450`, PRM `PRIDE:0000629`, SRM `PRIDE:0000630`); never `NCIT:C161786`/`MS:1000206`, and there is no `comment[dia method]` column
- **Carrier / reference channels** (single-cell / TMT): `comment[carrier channel]` = `PRIDE:0000901`, `comment[reference channel]` = `PRIDE:0000899` (not `PRIDE:0000941`/`0000942`); values are TMT channel labels (e.g. `TMT131C`)
- **Never write SDRF with pandas `to_csv`** — it renames legitimately repeated headers (`comment[modification parameters].1`); write raw TSV preserving duplicated column names
- **Multiple values = repeat the whole column** with the same header (there is no delimiter-separated list)

## Writing SDRF Safely (writer-side rules)

Every rule here corresponds to a defect class found across the public annotated corpus.
They are cheap to honour when writing and expensive to find later, because each one
**parses into the wrong thing instead of failing loudly** — the file still validates.

1. **An accession always carries its ontology prefix.** `AC=MS:1001251`, never `AC=1001251`.
   A bare number is unresolvable and the intended ontology is only recoverable from context.
2. **Prefix and id are separated by a colon**, never an underscore: `PRIDE:0000568`, not
   `PRIDE_0000568`.
3. **The accession for a term is constant.** If several rows carry the same `NT=`, they carry
   the same `AC=`. An accession that increments down the rows (`MS:1001309`, `MS:1001310`,
   `MS:1001311`, … all labelled `Lys-C`) is a generator bug — it names a different, real,
   wrong term on every row.
4. **Never emit Python repr into a cell.** No `['C']`, `None`, `nan`, `null`, `"['breast cancer']"`.
   Watch key=value fields especially: `TA=['C']` must be `TA=C` — a whole-cell artifact check
   will not catch one nested inside `NT=…;AC=…;TA=…`.
5. **Do not let a CSV writer quote the value.** `"NT=timsTOF HT;AC=MS:1003404"` is a value whose
   first character is a quote, not a quoted value, once it is read as TSV.
6. **Reserved words are written bare**, never wrapped: `not applicable`, not
   `NT=not applicable;AC=not available`.
7. **Never write SDRF with pandas `to_csv`.** It renames legitimately repeated columns
   (`comment[modification parameters].1`), which silently turns one repeated column into several
   distinct ones, so a reader keyed on the name sees only the first. Write raw TSV lines and
   preserve duplicate headers exactly.
8. **Ages carry a unit** from `Y`/`M`/`W`/`D`: `58Y`, not `58` and not `58 years`.
9. **One value per cell.** Several modifications means several
   `comment[modification parameters]` columns — never concatenate them into one cell.

`tools/sdrf_fixer.py` repairs 1, 2, 4, 5, 6, 7 and 8 deterministically; run it before
presenting or contributing any SDRF you generated.

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

---

## Explaining to users (plain language)

_Folded from the former `sdrf:explain` skill: use this when the user wants a concept, column, or error explained simply rather than a spec lookup._

# SDRF Explanation Skill

You are explaining SDRF concepts to users who may be new to the format.
Use the sdrf-knowledge and sdrf-templates background skills for reference.

## When Explaining a Column

1. **Read `spec/sdrf-proteomics/TERMS.tsv`** and find the row for the column
2. **What it is**: Plain-language definition (from `description` field)
3. **Why it matters**: How it's used in analysis/reuse
4. **Format rules**: Type from `type` field, allowed values from `values` field, reserved words from `allow_not_available`/`allow_not_applicable`/`allow_pooled` fields
5. **Examples**: 2-3 real examples from proteomics datasets
6. **Common mistakes**: What people get wrong and how to avoid it

### Example Explanation

```text
User: "What is comment[modification parameters]?"

This column describes the post-translational modifications (PTMs) searched in
your proteomics experiment.

WHY IT MATTERS:
  Every search engine needs to know which modifications to look for.
  Analysis pipelines (MaxQuant, DIA-NN, OpenMS) read this column to
  configure their modification search.

FORMAT:
  NT=<name>;AC=UNIMOD:<id>;TA=<target>;MT=<Fixed|Variable>

  - NT = Name (human-readable)
  - AC = UNIMOD accession (machine-readable)
  - TA = Target amino acid (C, M, K, etc.) or position
  - MT = Modification Type (Fixed = always present, Variable = sometimes present)

EXAMPLES:
  NT=Carbamidomethyl;AC=UNIMOD:4;TA=C;MT=Fixed
    → Cysteine alkylation, present on all cysteines (fixed)

  NT=Oxidation;AC=UNIMOD:35;TA=M;MT=Variable
    → Methionine oxidation, may or may not be present (variable)

  NT=Acetyl;AC=UNIMOD:1;PP=Protein N-term;MT=Variable
    → N-terminal acetylation (PP instead of TA for protein-level positions)

MULTIPLE MODIFICATIONS:
  Use separate columns for each modification (multiple columns allowed).
  Common setup: 1 fixed (Carbamidomethyl) + 1-3 variable (Oxidation, Phospho, etc.)

COMMON MISTAKE:
  ⚠ UNIMOD:1 = Acetyl, UNIMOD:21 = Phospho
  These are the most frequently swapped accessions in SDRF files.
  Always double-check.
```

## When Explaining an Error

1. **What the error means**: Plain-language translation
2. **Why it's wrong**: What rule was violated
3. **How to fix it**: Step-by-step fix with the correct value
4. **How to prevent it**: What to check next time

### Example Error Explanations

```text
Error: "UNIMOD:21 used for Acetyl"

WHAT IT MEANS:
  Your modification parameters column says UNIMOD:21 for a modification
  named "Acetyl", but UNIMOD:21 is actually Phospho (phosphorylation).

WHY IT'S WRONG:
  UNIMOD:21 = Phospho (+79.966 Da on S, T, Y)
  UNIMOD:1 = Acetyl (+42.011 Da on protein N-terminus)
  The wrong accession means analysis pipelines will search for phosphorylation
  instead of acetylation — completely wrong search results.

HOW TO FIX:
  Change: NT=Acetyl;AC=UNIMOD:21;PP=Protein N-term;MT=Variable
  To:     NT=Acetyl;AC=UNIMOD:1;PP=Protein N-term;MT=Variable

HOW TO PREVENT:
  This is the #1 most common SDRF error (~45% of all issues).
  Always verify UNIMOD accessions: Acetyl=1, Phospho=21.
```

```text
Error: "Missing required column: characteristics[biological replicate]"

WHAT IT MEANS:
  Your SDRF doesn't have a column for biological replicate identifiers.

WHY IT MATTERS:
  Analysis pipelines (MSstats, quantms) need to know which runs are
  biological replicates vs technical replicates to correctly model
  variance. Without this, statistical analysis may be invalid.

HOW TO FIX:
  Add a column: characteristics[biological replicate]
  Values: integers starting from 1 (unique per biological sample)
  If pooled: use "pooled"
```

## When Explaining a Concept

### "characteristics vs comment vs factor value"
- **characteristics[x]**: Properties of the biological SAMPLE (organism, disease, tissue)
- **comment[x]**: Properties of the technical RUN (instrument, label, modifications)
- **factor value[x]**: The experimental VARIABLE being compared statistically

Think of it this way:
- characteristics = "what is this sample?"
- comment = "how was it measured?"
- factor value = "what are we testing?"

### "How do I write a value — plain label or NT=;AC=?"
It depends on the column TYPE:
- **characteristics[...]** → the **bare ontology label**: `Homo sapiens`, `liver`, `breast carcinoma`. Not `NT=;AC=` (the validator resolves the label to its accession).
- **comment[...]** → **`NT=<label>;AC=<accession>`**: `NT=Trypsin;AC=MS:1001251`.
- **Structured characteristics** keep key=value: `spiked compound` (`CT=;QY=;PS=;AC=;CN=;CV=`), and modifications in `comment[modification parameters]` (`NT=;AC=;TA=;MT=`).
- **Acquisition method** (`comment[proteomics data acquisition method]`, required for MS) is a descendant of `PRIDE:0000659` — DDA `PRIDE:0000627`, DIA `PRIDE:0000450`, PRM `PRIDE:0000629`, SRM `PRIDE:0000630`.

### "How do I give a column more than one value?"
You **repeat the whole column** with the same header — there is no comma-separated list. Three modifications = three `comment[modification parameters]` columns; two organism parts = two `characteristics[organism part]` columns.

### "Why do I need ontology terms?"
Ontology terms enable:
1. **Machine readability** — software can group samples by disease automatically
2. **Cross-study comparison** — "breast carcinoma" in your study links to the same term in 200 other studies
3. **Hierarchical queries** — searching "carcinoma" finds all cancer subtypes
4. **Unambiguous meaning** — "normal" could mean many things; PATO:0000461 means exactly one thing

### "What are templates and why do I need them?"
Templates define which columns are required for your experiment type.
Without templates, SDRF validation only checks basic format (column names, no empty cells).
With templates, it checks that you've captured the right metadata for your specific experiment.

Read `spec/sdrf-proteomics/sdrf-templates/templates.yaml` for the full list of available templates.
Templates are organized into layers: Technology (required), Sample/Organism (recommended),
Experiment (optional), Clinical (optional), and Metaproteomics (special).

You declare templates via `comment[sdrf template]` columns:
  `NT=ms-proteomics;VV=v1.1.0`

See `/sdrf:templates` for the full selection guide and decision tree.

### "How many rows should my SDRF have?"
```text
Rows = samples × fractions × label_channels × technical_replicates

Label-free:  1 row per file
TMT6plex:    6 rows per file (one per channel)
TMT10plex:   10 rows per file
SILAC:       2-3 rows per file (light/medium/heavy)

Example: 10 samples × 12 fractions × 1 (label-free) = 120 rows
Example: 10 samples × 12 fractions × 10 (TMT10plex) = 1,200 rows
```

## Tone

- Be helpful and encouraging, not condescending
- Assume the user is a scientist who is smart but new to SDRF specifically
- Use concrete proteomics examples, not abstract descriptions
- When in doubt, link back to what the term means for their actual experiment



---

## Looking up ontology terms (OLS)

_Folded from the former `sdrf:terms` skill: the active workflow for finding/verifying an ontology term for a column via OLS._

# SDRF Ontology Term Lookup

You are helping the user find the correct ontology term for an SDRF column.

## Step 1: Identify the Column and Ontology

**Read `spec/sdrf-proteomics/TERMS.tsv`** and find the row for the column the user is asking about.
The `values` field tells you which ontology(ies) to search.

Examples from TERMS.tsv:
- `organism` → values: `NCBITaxon` → search OLS with ontologyId `ncbitaxon`
- `disease` → values: `MONDO, EFO, DOID, PATO` → search these ontologies
- `organism part` → values: `UBERON, BTO` → search UBERON first, BTO as fallback
- `cell type` → values: `CL, BTO` → search CL first, BTO as fallback
- `instrument` → values: `MS` → search MS ontology
- `modification parameters` → values: `UNIMOD` → use UNIMOD accessions
- `cleavage agent details` → values: `MS` → search MS ontology

Always read TERMS.tsv rather than relying on memorized ontology mappings — the spec may add new columns or change ontology sources.

## Step 2: Search OLS

Use the OLS MCP tools to find the term:

```text
Primary search:
  mcp OLS → searchClasses(query="<user term>", ontologyId="<ontology>")

If no results or too many:
  mcp OLS → search(query="<user term>")
  Filter results to the correct ontology manually

For broader semantic search:
  mcp OLS → searchClassesWithEmbeddingModel(query="<description>", model="<model>")
  (Call listEmbeddingModels first to get available models with can_embed=true)
```

## Step 3: Evaluate Specificity

When presenting results, assess specificity:

### Too Generic (suggest more specific)
- "cancer" → suggest "breast carcinoma", "lung adenocarcinoma", etc.
- "tissue" → suggest the actual tissue name
- "cell" → suggest the actual cell type
- "brain" might be OK, but "temporal cortex" is better if known

### Appropriately Specific
- "breast carcinoma" (EFO:0000305) — good for a breast cancer study
- "liver" (UBERON:0002107) — good for tissue-level studies
- "T cell" (CL:0000084) — good if subtype unknown

### Too Specific (might be too narrow)
- "left breast upper inner quadrant" — probably too specific for most studies

To check specificity, use hierarchy navigation:
```text
mcp OLS → getAncestors(ontologyId="<ont>", classIri="<iri>")
mcp OLS → getChildren(ontologyId="<ont>", classIri="<iri>")
```

## Step 4: Cross-Ontology Mapping

When the user has a term from one ontology but needs another:

```text
Example: User has DOID term, needs EFO equivalent
  1. Get the DOID term details: mcp OLS → fetch(id="doid+<iri>")
  2. Search EFO for the same concept: mcp OLS → searchClasses(query="<label>", ontologyId="efo")
  3. Present both options with accessions
```

For disease terms, SDRF accepts MONDO, EFO, or DOID. Recommend (matches TERMS.tsv and sdrf-annotate):
- **MONDO** as first choice (primary; strong cross-references)
- **EFO** as second choice
- **DOID** as third choice

## Step 5: Present Results

For each term found, present:

```text
Term: breast carcinoma
Accession: EFO:0000305
Ontology: Experimental Factor Ontology (EFO)
Definition: A carcinoma that arises in the breast region.
Synonyms: breast cancer, mammary carcinoma
Parent: carcinoma (EFO:0000228)
SDRF format: breast carcinoma
Column: characteristics[disease]

Alternative terms:
  - invasive breast carcinoma (EFO:0010132) — more specific, if applicable
  - breast ductal carcinoma (EFO:0000298) — subtype-specific
```

## Special Cases

### "Normal" / "Healthy" / "Control"
- For disease: use `normal` with accession PATO:0000461
- Do NOT use: "healthy", "control", "none", "N/A"

### "Not Available" vs "Not Applicable"
- `not available` — the information exists but wasn't captured
- `not applicable` — the property doesn't apply (e.g., cell line for a tissue sample)
- Check TERMS.tsv `allow_not_available` and `allow_not_applicable` for the specific column

### Cell Lines
- Use the **Cellosaurus database** (https://www.cellosaurus.org/) for cell line identification
- SDRF uses three columns for cell lines:
  - `characteristics[cell line]` — name from CLO, BTO, or EFO ontology
  - `characteristics[cellosaurus accession]` — format: CVCL_XXXX (e.g., CVCL_0030 for HeLa)
  - `characteristics[cellosaurus name]` — official Cellosaurus name
- Common examples: HeLa (CVCL_0030), HEK293 (CVCL_0045), MCF7 (CVCL_0031), A549 (CVCL_0023)
- To find a Cellosaurus accession: search https://www.cellosaurus.org/search (not OLS)
- Cross-reference Cellosaurus for: species of origin, disease, tissue of origin, STR profile

### Instruments
- Format in SDRF: `AC=MS:1001911;NT=Q Exactive HF`
- Search MS ontology for the instrument model
- Include manufacturer in search if needed

### Modifications
- ALWAYS use UNIMOD accessions, not PSI-MOD
- The format is: `NT=<name>;AC=UNIMOD:<id>;TA=<amino acid>;MT=<Fixed|Variable>`
- Double-check the UNIMOD:1/UNIMOD:21 swap (Acetyl vs Phospho)


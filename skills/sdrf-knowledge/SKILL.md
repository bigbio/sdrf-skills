---
name: sdrf-knowledge
description: Use when the user asks about the SDRF format, column naming rules, ontology mappings, modification format, reserved words, label types, or any SDRF specification question, wants a plain-language explanation of a column/error/concept, or needs to find/verify/compare ontology terms and accessions for a column. Also serves as background knowledge for all other SDRF skills.
user-invocable: true
argument-hint: "[question about SDRF format or column rules]"
---

# SDRF Specification Knowledge Base

> **Bundle paths.** `spec/`, `tools/` and `data/` ship with this skill, not with your working
> directory. Resolve every such path below against the bundle root — `$CLAUDE_PLUGIN_ROOT` under
> Claude Code (`$CLAUDE_PLUGIN_ROOT/spec/sdrf-proteomics/TERMS.tsv`), or your sdrf-skills checkout
> on other platforms. The helpers are the `sdrf-tools` command, installed by `/sdrf-skills:sdrf-setup`; no `PYTHONPATH` or plugin-root variable is needed to run them.
> Files the user is annotating stay relative to the working directory.

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

## Format rules

The rules — core format, safe writing, column types, value encoding, reserved words,
modification syntax, UNIMOD swaps, label types, common errors — are in
[references/format-rules.md](references/format-rules.md). Read that file when answering a
"how do I write X" question; the sections below are about *explaining* them.

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
Use this skill's `references/format-rules.md` and `../sdrf-annotate/references/templates.md` for reference.

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

See ``../sdrf-annotate/references/templates.md`` for the full selection guide and decision tree.

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


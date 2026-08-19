---
name: sdrf:explain
description: Use when the user asks about SDRF concepts, columns, errors, format rules, or wants to understand why something is done a certain way.
user-invocable: true
argument-hint: "[column name, error message, or concept]"
---

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

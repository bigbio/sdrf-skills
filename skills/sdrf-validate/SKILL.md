---
name: sdrf:validate
description: Use when the user wants to validate an SDRF file, check for errors, or verify ontology terms. Triggers on requests to check, validate, or review SDRF content.
user-invocable: true
argument-hint: "[file path or paste SDRF content]"
---

# SDRF Validation Workflow

You are validating an SDRF file. Perform systematic checks in order.

## Step 0: Check parse_sdrf availability

Verify that `parse_sdrf` is available (run `parse_sdrf --version` or `which parse_sdrf`). If it is not installed:
- Inform the user that programmatic validation with parse_sdrf will be skipped
- Suggest `/sdrf:setup` or `conda env create -f environment.yml && conda activate sdrf-skills` (or `pip install -r requirements.txt`)
- Continue with structural and ontology checks; manual validation is still valuable

## Step 1: Parse the SDRF

1. Read the SDRF content (from file path or pasted content)
2. Count rows (samples/runs) and columns
3. Check for SDRF metadata: `comment[sdrf version]`, `comment[sdrf template]`

## Step 2: Detect Templates

1. If `comment[sdrf template]` exists → extract template names and versions
   Format: `NT=ms-proteomics;VV=v1.1.0` or `ms-proteomics v1.1.0`
2. If not → auto-detect from content using these rules:

| Detection Signal | Template |
|-----------------|----------|
| `technology type` = "proteomic profiling by mass spectrometry" | ms-proteomics |
| `technology type` = "protein expression profiling by aptamer array" | somascan |
| `technology type` = "protein expression profiling by antibody array" | olink |
| `characteristics[organism]` = Homo sapiens | human |
| `characteristics[organism]` = Mus musculus / Rattus / Danio | vertebrates |
| `characteristics[organism]` = Drosophila / C. elegans | invertebrates |
| `characteristics[organism]` = Arabidopsis / Oryza | plants |
| DIA acquisition method | dia-acquisition |
| `characteristics[cell line]` present | cell-lines |
| `characteristics[mhc protein complex]` present | immunopeptidomics |
| `comment[cross-linker]` present | crosslinking |
| `characteristics[single cell isolation protocol]` present | single-cell |
| `characteristics[environmental sample type]` present | metaproteomics |
| `characteristics[tumor grading]` or `characteristics[tumor stage]` | oncology-metadata |
| `comment[olink panel]` present | olink |
| `comment[somascan menu]` present | somascan |

3. Report detected templates to user

## Step 3: Structural Validation

Check these rules (report ALL issues, don't stop at first):

### 3.1 Column Name Format
- [ ] First column is `source name`
- [ ] All characteristics columns match `characteristics[<name>]` pattern
- [ ] All comment columns match `comment[<name>]` pattern
- [ ] All factor value columns match `factor value[<name>]` pattern
- [ ] No trailing whitespace in column names
- [ ] `comment[modification parameters]` and `comment[sdrf template]` CAN repeat (multiple columns)
- [ ] Other columns should NOT be duplicated

### 3.2 Required Columns by Template

**Read `spec/sdrf-proteomics/TERMS.tsv`** to determine which columns are required for each detected template.

For each detected template:
1. Filter TERMS.tsv rows where the `usage` column contains that template name
2. These are the columns expected for that template
3. Check that each expected column exists in the SDRF

Additionally, read the individual template YAML at `spec/sdrf-proteomics/sdrf-templates/{name}/{version}/{name}.yaml` to determine requirement levels (required vs recommended vs optional).

**Always required (universal base columns — present in every valid SDRF regardless of template):**

These seven columns are the irreducible minimum required by the base SDRF spec.
They are listed here as a quick-check aid; always cross-verify against TERMS.tsv (`usage` contains `base`) for the authoritative list.
- [ ] `source name`
- [ ] `assay name`
- [ ] `technology type`
- [ ] `comment[data file]`
- [ ] `comment[fraction identifier]`
- [ ] `comment[technical replicate]`
- [ ] `comment[sdrf version]`

For all other template-specific columns, read from TERMS.tsv rather than using a hardcoded list.

### 3.3 Value Format Checks
- [ ] No empty cells in required columns
- [ ] No trailing whitespace in values
- [ ] Age format: `{number}{unit}` where unit is Y/M/W/D (e.g., "58Y", not "58 years")
- [ ] Sex values: lowercase ("male", "female", not "Male", "Female")
- [ ] Reserved words: "not available", "not applicable" (not "N/A", "NA", "unknown", "none")
- [ ] No Python artifacts: "['value']", "nan", "None", "NaN"
- [ ] `technology type` has valid value (one of 3 allowed)
- [ ] `comment[fraction identifier]` is integer
- [ ] `comment[technical replicate]` is integer starting from 1
- [ ] `characteristics[biological replicate]` is integer or "pooled"
- [ ] `comment[sdrf version]` matches semver pattern (vX.Y.Z)
- [ ] Check TERMS.tsv `allow_not_available`, `allow_not_applicable`, `allow_pooled` fields for each column to verify reserved words are valid

## Step 4: Ontology Validation

For EACH unique value in ontology-controlled columns, verify via OLS.
Use TERMS.tsv `values` field to determine which ontology(ies) to search for each column.

### Organism
```text
searchClasses(query="<organism>", ontologyId="ncbitaxon")
Verify: term exists, case is correct (Genus capitalized, species lowercase: "Homo sapiens")
```

### Disease
```text
search(query="<disease>")
Verify: term exists — prefer EFO (primary), MONDO, or DOID
Check specificity: "cancer" too generic → use "breast carcinoma"
Special case: "normal" is valid (PATO:0000461)
```

### Tissue / Organism Part
```text
searchClasses(query="<tissue>", ontologyId="uberon")
Fallback: searchClasses(query="<tissue>", ontologyId="bto")
```

### Cell Type
```text
searchClasses(query="<cell type>", ontologyId="cl")
Fallback: searchClasses(query="<cell type>", ontologyId="bto")
```

### Instrument
```text
Parse NT= and AC= from comment[instrument] value
searchClasses(query="<instrument name>", ontologyId="ms")
Verify: AC= matches the returned MS accession
```

### Modifications — CRITICAL
```text
Parse NT=, AC=, TA=, MT= from each comment[modification parameters]
Verify:
  - AC= is valid UNIMOD accession
  - UNIMOD:1 = Acetyl (NOT Phospho!)
  - UNIMOD:21 = Phospho (NOT Acetyl!)
  - UNIMOD:35 = Oxidation (NOT Methyl!)
  - UNIMOD:34 = Methyl (NOT Oxidation!)
  - MT= is "Fixed" or "Variable"
  - TA= is valid amino acid letter or PP= is valid position
  - TMT6/10/11plex = UNIMOD:737, TMTpro = UNIMOD:2016
```

### Cleavage Agent
```text
Parse NT= and AC= from comment[cleavage agent details]
searchClasses(query="<enzyme>", ontologyId="ms")
Verify: AC= matches
```

### Performance Note
For large SDRF files (100+ rows), validate unique values only — don't make redundant OLS calls for repeated values. Group by unique values first, then validate once per unique value.

## Step 5: Consistency Checks

- [ ] All rows have the same number of columns (no ragged rows)
- [ ] `source name` + `assay name` combination is unique per row
- [ ] `source name` values follow a consistent naming pattern
- [ ] `characteristics[biological replicate]` values are sequential integers
- [ ] `comment[fraction identifier]` values are consistent across samples
- [ ] Factor values match actual characteristics column values
- [ ] If TMT: correct number of rows per raw file (6 for TMT6, 10 for TMT10, 11 for TMT11, 16 for TMT16)
- [ ] If SILAC: 2-3 rows per raw file (light/medium/heavy)
- [ ] File names in `comment[data file]` are unique per assay name
- [ ] `technology type` is the same across all rows
- [ ] All `comment[modification parameters]` columns have the same value across all rows (modifications are experiment-wide, not per-sample)
- [ ] `comment[instrument]` should be consistent (or documented if multiple instruments used)

## Step 6: Report

Present findings organized by severity:

### Errors (must fix before submission)
List each error with: row number(s), column, current value, what's wrong, how to fix.

### Warnings (should fix for quality)
List each warning with: what could be improved and why.

### Suggestions (nice to have)
Missing recommended columns, specificity improvements.

### Summary
```text
Validation Report:
  Templates: [detected templates with versions]
  Rows: X  |  Columns: Y
  Unique organisms: N  |  Diseases: N  |  Tissues: N
  Errors: X  |  Warnings: Y  |  Suggestions: Z
  Assessment: [VALID / NEEDS FIXES / MAJOR ISSUES]
```

## Validation Priority

If the file has many issues, report in this order:
1. Missing required columns (structural — breaks parsing)
2. Wrong UNIMOD accessions (semantic — wrong search results)
3. Invalid ontology terms (semantic — breaks data integration)
4. Format issues: case, whitespace, age format (easy fixes)
5. Missing recommended columns (quality improvement)

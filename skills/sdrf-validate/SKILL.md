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

## Step 0.5: Protect the Machine During Validation

Validation can be expensive because `parse_sdrf` may trigger ontology lookups,
template loading, and large file parsing.

Use these resource guards:

- Default to serial validation for autonomous loops unless there is a clear reason to parallelize
- If validating multiple SDRFs in parallel, keep the concurrency small: at most `2` `parse_sdrf` jobs at a time
- If `techsdrf`, raw-file conversion, or other heavy IO/CPU work is running, validate only `1` SDRF at a time
- Validate changed datasets first, not the whole collection by default
- Prefer batch manifests or representative smoke checks before full-sandbox sweeps
- For large SDRFs, validate unique values once rather than re-checking repeated ontology terms row by row

If the machine looks stressed or validation becomes unresponsive, reduce concurrency before continuing.

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
| `comment[panel name]` or `comment[olink panel]` present | olink |
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

**Always required (base template — verify against TERMS.tsv):**
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

### 3.4 Demographic Evidence Checks
- [ ] If `characteristics[developmental stage]` is filled, verify the paper or metadata supports a single clear stage for the analyzed cohort or for that individual sample
- [ ] Accept cohort-level support for `developmental stage` values such as `adult`, `pediatric`, `juvenile`, or `fetal` when the entire analyzed cohort is unambiguous
- [ ] Do not require `characteristics[age]`, `characteristics[sex]`, or `characteristics[ethnicity]` to be filled just because the paper has cohort summaries
- [ ] If `age`, `sex`, or `ethnicity` are filled per sample, verify that the manuscript or supplementary data maps them to individual source samples rather than only to group-level summaries
- [ ] If only cohort-level summaries exist, prefer omission or `not available` over guessed per-sample demographic values

## Step 4: Ontology Validation

For EACH unique value in ontology-controlled columns, verify via OLS.
Use TERMS.tsv `values` field to determine which ontology(ies) to search for each column.

Use this search order for ambiguous values:
1. Clean the value first (strip Python/list artifacts, trim whitespace, expand abbreviations if known)
2. Run lexical OLS search in the ontology family allowed by `TERMS.tsv`
3. If lexical search fails or is clearly ambiguous, run OLS embedding search on the cleaned phrase
4. If the value looks manuscript-derived free text or lexical and embedding results still disagree, try ZOOMA:
   `https://www.ebi.ac.uk/spot/zooma/v2/api/services/annotate?propertyValue=<clean phrase>&propertyType=<field>`
5. Verify any accepted candidate in OLS before marking it valid

Default behavior by field:
- `organism`, `cell line` → lexical first, fallback methods rarely needed
- `organism part`, `cell type`, `treatment` → lexical first, fallback only if lexical is weak
- `disease`, `phenotype` → lexical first, embeddings and ZOOMA are useful when values are messy or abbreviated

Do NOT mark a term invalid just because embeddings or ZOOMA suggest a more specific descendant than the cell text supports; warn about specificity instead.

### Organism
```text
searchClasses(query="<organism>", ontologyId="ncbitaxon")
Verify: term exists, case is correct (Genus capitalized, species lowercase: "Homo sapiens")
```

When an imported SDRF uses an older NCBITaxon synonym, prefer the current
accepted label before declaring the row invalid. Common cleanup mappings seen in
crosslinking datasets:
- `chaetomium thermophilum` → `thermochaetoides thermophila`
- `chlorobium tepidum` → `chlorobaculum tepidum`
- `canis familiaris` → `canis lupus familiaris`
- `deinococcus radiodurans r1` → `deinococcus radiodurans`

If a crosslinking SDRF still uses `NT=unknown crosslinker;AC=XLMOD:00000`, inspect `comment[data file]` for explicit reagent tokens before accepting the placeholder. Examples validated in sandbox cleanup:
- `DSSO` in file name → `NT=DSSO;AC=XLMOD:02010;CL=yes;TA=K,S,T,Y,nterm;MH=54.01;ML=85.98`
- `BS3` in file name → `NT=BS3;AC=XLMOD:02000`
- `TurboID` in file name → `NT=TurboID;AC=XLMOD:02251`
- `iQPIR`, `BDP`, or `d8BDP` in file name → `NT=PIR;AC=XLMOD:02014`

When a specific cross-linker is recovered, validate whether `characteristics[crosslink distance]` can be backfilled from the crosslinking template:
- `BS3` / `DSS` → `30 Å`
- `DSSO` → `26.4 Å`
- `EDC` → `11.4 Å`
- `formaldehyde` → `2 Å`
- `DSBU` / `DSBSO` → `26.4 Å`
- `SDA` / `sulfo-SDA` → `18 Å`

For missing `comment[crosslink enrichment method]`, inspect `comment[data file]` for explicit enrichment tokens before leaving the field unresolved:
- `SCX` → `strong cation exchange chromatography`
- `SEC` → `size exclusion chromatography`
- `FAIMS` → `FAIMS`
- dataset title containing `streptavidin pull-down` → `streptavidin pull-down`
- dataset title containing `IMAC-enrichable` → `immobilized metal affinity chromatography`
- dataset title containing `CuAAC-enrichable` → `CuAAC enrichment`

When one of those values is recovered and `characteristics[enrichment process]` is still missing, backfill `enrichment of cross-linked peptides`.

### Disease
```text
search(query="<disease>")
Verify: term exists in MONDO, EFO, or DOID
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

If the validator warns on an instrument term but the accession is present in the
official PSI-MS / ProteomeXchange schema, treat it as a review item rather than
an automatic correction. Example: `LTQ Orbitrap Elite` with `MS:1001910` has
been observed to warn in some validation/cache combinations even though the term
is publicly documented.

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

When validating multiple files, prefer small bounded batches. Do not launch large numbers of `parse_sdrf` jobs at once.

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
- [ ] `characteristics[sampling time]` uses the template pattern `number + unit` such as `0 day`, `8 day`, or `12 week` when time-course metadata is present
- [ ] `characteristics[depletion]` uses the controlled values `depletion` or `no depletion` rather than local variants like `depleted` or `yes`

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

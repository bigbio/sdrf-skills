---
name: sdrf:autoresearch
description: Use when the user wants SDRF annotation to run as an autonomous retained-improvement loop over one dataset, a manifest, or a dataset class such as all PRIDE cell line or crosslinking datasets.
user-invocable: true
argument-hint: 'target="<dataset scope>" [profile="<preset>"] [objective="<metric>"] [focus_fields="<field1,field2>"] [evidence="<pride,files,europepmc>"] [stop="<rule>"] [write="<sandbox|branch|report-only>"]'
---

# SDRF Autoresearch Protocol

This workflow is a domain-specific autonomous loop for SDRF annotation.
It is intended to function with minimal user supervision once the target and
optimization goal are clear.

Use it when the user asks for:
- annotation of all datasets in a category
- repeated refine → validate → fix loops
- maximum metadata completion without blind guessing
- autonomous SDRF improvement until no more retained gains are possible

This is a protocol skill, not a dedicated runner script. Execute the loop by
following the steps below and by calling the existing `sdrf:*` skills in order.

## Console Triggers

Claude-style examples:
```text
/sdrf:autoresearch target="all PRIDE cell line datasets"
/sdrf:autoresearch target="all sandbox crosslinking datasets" profile="crosslinking"
/sdrf:autoresearch target="manifest:data/cell_line_manifest.tsv" objective="maximize_valid_field_coverage"
```

Codex-style examples:
```text
$sdrf-autoresearch target="all PRIDE cell line datasets"
$sdrf-autoresearch target="accessions:PXD001234,PXD005678" profile="clinical"
$sdrf-autoresearch target="all sandbox crosslinking datasets" objective="crosslinking_assay_completion" write="sandbox"
```

## Step 1: Parse the Request into a Loop Config

Normalize the user request into these fields:

- `target`
  - What dataset set to operate on
  - Examples:
    - `all PRIDE cell line datasets`
    - `all sandbox crosslinking datasets`
    - `manifest:data/cell_line_manifest.tsv`
    - `accessions:PXD001234,PXD005678`

- `profile`
  - Domain preset that biases which templates, columns, and evidence sources matter most
  - Supported defaults:
    - `general-proteomics`
    - `cell-line`
    - `crosslinking`
    - `clinical`
    - `immunopeptidomics`

- `objective`
  - The optimization target for retained improvements
  - Supported defaults:
    - `maximize_valid_field_coverage`
    - `minimize_unknowns`
    - `crosslinking_assay_completion`
    - `cell_line_sample_completion`
    - `clinical_sample_completion`

- `focus_fields`
  - Optional list of fields to prioritize
  - Examples:
    - `cell line,disease,organism part,treatment`
    - `cross-linker,crosslink enrichment method,collision energy`

- `evidence`
  - Which sources are allowed
  - Defaults to `pride,files,europepmc`
  - Common values:
    - `pride,files`
    - `pride,files,europepmc`
    - `manuscript-first`

- `stop`
  - When the loop should stop
  - Supported defaults:
    - `3_no_improve_rounds`
    - `coverage>=0.95`
    - `only_low_confidence_candidates_left`

- `write`
  - Where edits should land
  - Supported values:
    - `sandbox`
    - `branch`
    - `report-only`

If the user does not specify these explicitly, infer them conservatively and
state the inferred config before the loop begins.

## Step 2: Build the Dataset Target Set

Interpret `target` into a concrete dataset set:

- `accessions:...`
  - Use those accessions directly

- `manifest:...`
  - Read the manifest TSV/CSV and use those datasets

- `all PRIDE <category> datasets`
  - Use PRIDE MCP + local manifests to discover datasets matching the category
  - Examples:
    - `cell line`
    - `crosslinking`
    - `human clinical`
    - `immunopeptidomics`

- `all sandbox <category> datasets`
  - Use local sandbox inventory first

Always resolve the target into a manifest-like working list before annotation begins.

### Plasma Campaign Heuristic

For `blood plasma` or `plasma biomarker` campaigns:

1. Audit the local project collection first
   - enumerate existing SDRFs under the relevant project tree
   - separate true plasma SDRFs from blood-cell / tissue / platelet / serum-only SDRFs
   - extract the current disease coverage before searching PRIDE

2. Treat discovery as two layers
   - `new_dataset`: accession not yet present in the local plasma collection
   - `upgrade_existing_sdrf`: accession already present locally, but disease wording, ontology, or field coverage should be improved

3. Default to human plasma unless the user explicitly says otherwise
   - treat `Homo sapiens` as the default species scope for biomarker-style plasma campaigns
   - use PRIDE `organisms` first to confirm species
   - if PRIDE species is missing or generic, confirm human-only status from the manuscript title, abstract, methods, or supplementary text
   - keep non-human or mixed-species plasma projects as audit rows, not as automatically promoted annotation targets

4. When querying PRIDE, do not trust `plasma` hits blindly
   - expand disease names before PRIDE search:
      - start with lexical OLS disease lookup in `MONDO`, `DOID`, `EFO`, and `NCIT`
      - add useful exact labels and synonyms
      - for broad disease requests like `kidney tumor`, use OLS embedding search to surface likely subtype names such as renal-cancer variants
      - keep useful child-term labels when the study is still clearly in scope, for example `myositis` -> `dermatomyositis`, `sarcoma` -> `Ewing sarcoma`, `myeloma` -> `multiple myeloma`, or `alcohol-related liver disease` -> `alcoholic hepatitis`
      - for influenza-like campaigns, acceptable query widening can include `influenza A`, `IAV`, `H1N1`, `flu`, and, if the user explicitly allows it, broader `viral pneumonia` plus `serum`
      - then query PRIDE and Europe PMC with the expanded disease family, not only the original user wording
     - record whether a promoted hit is an `exact`, `child_term`, `related`, or `surrogate` disease match so downstream ranking does not overstate coverage
   - annotate the candidate workflow class during discovery:
     - use PRIDE `experimentTypes` for acquisition style such as `Data-independent acquisition`, `Data-dependent acquisition`, `Gel-based experiment`, or `Bottom-up proteomics`
     - use PRIDE `quantificationMethods` first for labeling style such as `TMT`, `iTRAQ`, `label-free quantification`, `Dimethyl Labeling`, or `NSAF`
     - if `quantificationMethods` is empty, inspect `sampleProcessingProtocol`, `dataProcessingProtocol`, and keywords for explicit terms like `TMT16plex`, `iTRAQ`, `label-free quantification`, `LFQ`, `MaxQuant`, `DIA`, `SWATH`, or `Spectronaut`
     - store separate `acquisition_mode` and `quant_mode` columns so campaigns can prioritize `DIA-LFQ`, `DDA-TMT`, `DDA-LFQ`, and related workflows explicitly
   - distinguish `blood plasma` / `plasma proteome` / `plasma extracellular vesicles` from false positives such as `plasma cells` or `plasma membrane`
   - for the current plasma-dataset campaigns, keep only accessions hosted by `PRIDE`, `MassIVE`, `jPOST`, or `iProX`; treat `PanoramaPublic` discoveries as audit-only until the campaign policy changes
   - prefer candidates where both the disease and the blood-plasma context are explicit in the title or description
   - for automatic shortlist generation, only promote accessions when plasma context is `positive` or `ambiguous` and the disease context is `explicit`
   - keep disease-only hits with missing plasma context as low-confidence discovery rows, not as prioritized plasma projects
   - do not promote datasets that lack usable raw or acquisition files; keep them as audit-only rows even if the disease and matrix look promising
   - after shortlist generation, run a manuscript-backed plasma review and classify each accession as:
     - `confirmed_plasma`: explicit plasma evidence in title, abstract, methods, results, or supplementary text
     - `mixed_includes_plasma`: plasma is explicit, but other sample matrices are also part of the study
     - `likely_non_plasma`: manuscript shows a different primary matrix such as CSF, urine, platelet releasate, BALF, or cell-line material
     - `unclear`: insufficient manuscript evidence; do not prioritize automatically
   - prefer `confirmed_plasma` first, then `mixed_includes_plasma` if mixed-matrix studies are acceptable for the campaign

5. Search Europe PMC independently when publication links may be missing from PRIDE
   - run disease-focused Europe PMC queries even when PRIDE does not already point to a publication
   - include `PXD`, `PRIDE`, or `ProteomeXchange` in the literature query to favor papers that reference a proteomics dataset
   - when a paper is open access, inspect the full text and extract explicit `PXD...` / `MSV...` mentions
   - use the literature-side accession hits to cross-link back into PRIDE and recover datasets that are weakly linked or unlinked in the archive record

6. Prioritize candidates in this order
   - missing disease coverage with explicit blood-plasma context
   - related-only local coverage where a disease-specific plasma accession exists
   - already covered diseases only when the existing local SDRF is clearly incomplete

## Step 3: Choose the Scoring Objective

Do not optimize for raw field count alone.
Optimize for valid, evidence-supported, template-compliant completion.

Default scoring dimensions:

1. Required-field completion
2. Recommended-field completion
3. Objective-specific completion
4. Validation success
5. Ontology quality
6. Evidence support
7. Placeholder penalty

Recommended derived objectives:

### `maximize_valid_field_coverage`

Use when the user wants the most complete valid SDRF possible.

Reward:
- required columns present and filled
- recommended columns present and filled
- validated ontology terms
- technical metadata recovered from files or manuscript evidence

Penalize:
- `not available`, `not applicable`, `unknown`
- invalid ontology terms
- unsupported guesses

### `minimize_unknowns`

Use when the main problem is placeholders and unresolved values.

Reward:
- replacing `unknown` and `unknown crosslinker`
- resolving generic metadata into validated terms

Penalize:
- replacements that are not evidence-backed

### `crosslinking_assay_completion`

Use for XL-MS datasets.
Focus strongly on:
- `comment[cross-linker]`
- `comment[crosslink enrichment method]`
- `characteristics[enrichment process]`
- `characteristics[crosslink distance]`
- `comment[crosslinker concentration]`
- `characteristics[crosslinking reaction time]`
- `characteristics[crosslinking temperature]`
- `comment[quenching reagent]`
- `comment[collision energy]`

### `cell_line_sample_completion`

Use for cell line datasets.
Focus strongly on:
- `characteristics[cell line]`
- `characteristics[cell type]`
- `characteristics[disease]`
- `characteristics[organism part]`
- `characteristics[treatment]`
- `characteristics[sex]`
- `characteristics[age]`

For human or clinical campaigns, also treat demographic evidence conservatively:
- promote `characteristics[developmental stage]` when the cohort is clearly adult, pediatric, fetal, juvenile, and so on, even if the paper reports only cohort-level age summaries
- do not auto-fill per-sample `characteristics[age]`, `characteristics[sex]`, or `characteristics[ethnicity]` unless the manuscript or supplementary tables map them to individual source samples
- if only cohort summaries exist, record the evidence in notes rather than forcing those values into every SDRF row

## Step 4: Run the Annotation Loop

For each dataset:

1. Discover evidence
   - PRIDE metadata
   - PRIDE files
   - manuscript from Europe PMC when available
   - supplementary and tables for sample metadata
   - methods for technical metadata

   For PRIDE file discovery, prefer the complete Archive REST endpoint when you
   need exact file coverage or file counts:
   ```text
   GET https://www.ebi.ac.uk/pride/ws/archive/v3/projects/PXD######/files/all
   ```
   Use this to avoid partial paged counts when auditing raw files, checking
   whether a candidate accession is tractable, or comparing SDRF `comment[data file]`
   values against the archive.
   If this endpoint returns `0` files for a valid PXD hosted through
   `PanoramaPublic`, `MassIVE`, `iProX`, or `jPOST`, treat that as
   `archive endpoint empty for external repository` rather than `no dataset`.
   Keep the accession in play and note the repository-backed limitation in the
   ranking output.

2. Run `/sdrf:annotate`
   - draft or extend the SDRF using the selected templates

3. Run `/sdrf:terms`
   - normalize ontology-backed fields
   - use lexical OLS first
   - use embeddings for fuzzy manuscript-derived mentions
   - use ZOOMA as slower fallback when useful

4. Run `/sdrf:techrefine`
   - refine technical MS metadata when raw files or techsdrf evidence are available

5. Run `/sdrf:validate`
   - validate template structure, reserved words, and ontology-backed fields
   - keep validation concurrency bounded: default to serial, and never run more than `2` `parse_sdrf` jobs at once
   - if `sdrf-techrefine`, raw-file conversion, or other heavy analysis is active, validate only `1` dataset at a time

6. Run `/sdrf:fix`
   - apply safe corrections to known SDRF error patterns

7. Run `/sdrf:improve`
   - rescore completeness, specificity, consistency, standards, and design

8. Keep or discard
   - keep only if the score improves and validation does not regress
   - discard any refinement that adds unsupported metadata

## Step 5: Repeat Until the Stop Rule Fires

Repeat the full loop until one of these is true:

- no retained improvement for 3 rounds
- objective score crosses the configured threshold
- only low-confidence or unsupported candidates remain
- the remaining work is clearly manual-only

Never keep looping just to replace placeholders with guesses.

## Validation Resource Guard

Autonomous annotation must not compromise the machine.

Use these defaults:

- `validation_mode=serial` unless there is a demonstrated need for limited parallel validation
- `max_validation_jobs=2`
- `max_validation_jobs=1` whenever raw-file analysis, file conversion, or large manuscript processing is already active
- validate changed datasets first
- use representative smoke checks before full collection sweeps

If validation hangs or the system becomes resource-constrained, reduce the number of concurrent validators before continuing.

## Step 6: Refinement Heuristics by Evidence Source

Prioritize evidence as follows:

### Sample metadata

Best sources:
- PRIDE sample description
- manuscript Methods
- manuscript Results
- supplementary sample tables
- figure and table captions

### Technical metadata

Best sources:
- raw-file analysis
- PRIDE protocols
- manuscript Methods
- search-parameter tables

### File mapping and replicate logic

Best sources:
- PRIDE file list
- SDRF row structure
- file names

## Step 7: Output Requirements

At the end of the run, report:

- resolved target set
- inferred or explicit config
- retained vs discarded rounds
- final score or stopping condition
- files changed
- remaining unresolved high-value gaps

If `write=report-only`, produce the same retained-improvement report without writing SDRFs.

## Example Configs

### Cell lines
```text
/sdrf:autoresearch target="all PRIDE cell line datasets" profile="cell-line" objective="maximize_valid_field_coverage" focus_fields="cell line,disease,organism part,treatment" evidence="pride,files,europepmc" stop="3_no_improve_rounds" write="sandbox"
```

### Crosslinking
```text
/sdrf:autoresearch target="all sandbox crosslinking datasets" profile="crosslinking" objective="crosslinking_assay_completion" focus_fields="cross-linker,crosslink enrichment method,collision energy,crosslinking reaction time" evidence="pride,files,europepmc" stop="only_low_confidence_candidates_left" write="sandbox"
```

### Report-only review
```text
/sdrf:autoresearch target="manifest:data/review_set.tsv" objective="minimize_unknowns" write="report-only"
```

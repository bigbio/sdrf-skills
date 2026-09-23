# Reference: reviewing an SDRF against its record (review mode of sdrf-annotate)

Cross-reference with the publication and with PRIDE, conflict resolution, and the design
checks (batch effects, confounders, replication). Read when reviewing an existing SDRF, or
after annotating when the paper is available.

## Step 3: Cross-Reference with Publication

If a publication is available:
- Does the sample count in SDRF match the paper?
- Are all conditions from the paper represented?
- Do the instruments match?
- Are demographics (age, sex) consistent with the paper?
- Is `characteristics[developmental stage]` supported by the cohort description even if age is reported only at group level?
- Are tissue types correctly annotated?

When Europe PMC full text is available, do not inspect raw XML directly. First run:
`python scripts/europepmc_fulltext.py PMC_ID --section methods --section results --section discussion --format text`
or use `--format json` when structured links, captions, or accession detection will help the review.

Flag any discrepancies:
```text
DISCREPANCY: Paper says "24 patients" but SDRF has 20 unique source names.
DISCREPANCY: Paper mentions "hippocampus and temporal cortex" but SDRF only has "brain".
```

For technical metadata (instrument, tolerances, modifications, DDA/DIA), consider
recommending `/sdrf-skills:sdrf-techrefine` — techsdrf can verify these parameters directly from
the raw MS files, which is more reliable than cross-referencing with the publication.

### Conflict Resolution
When SDRF and paper/PRIDE disagree:
- **Sample count mismatch**: Check if some samples were excluded (QC failure, outliers). Paper may report enrolled patients while SDRF has analyzable samples. Check supplementary tables.
- **Instrument mismatch**: PRIDE might say "Q Exactive" while paper says "Q Exactive HF". The paper is usually more specific — update SDRF to match the paper's instrument model.
- **Tissue specificity**: If paper says "hippocampus" but SDRF says "brain", update SDRF to the more specific term from the paper.
- **Demographic mismatch**: If paper has a demographics table, prioritize it. SDRF might have been filled from incomplete metadata.
- **Cohort-only demographics**: If the paper reports only cohort summaries, `developmental stage` may still be supportable, but do not force per-sample `age`, `sex`, or `ethnicity` without an individual-level mapping table.
- **File count mismatch**: Some files in PRIDE may be non-raw (search results, FASTA, etc.). Compare only raw files.

## Step 4: Cross-Reference with PRIDE

If a PXD accession is available:
- Do file names in SDRF match files in PRIDE?
  ```text
  mcp PRIDE → get_project_files(project_accession="PXD######")
  ```
  REST fallback:
  ```text
  GET https://www.ebi.ac.uk/pride/ws/archive/v3/projects/PXD######/files/all
  ```
- Does the organism match?
- Does the instrument match?
- Are all raw files accounted for?

If PRIDE exposes no raw files and the dataset is hosted by MassIVE, use the
deterministic helper:

```bash
sdrf-tools massive-files PXD016117 --mode raw --format tsv
```

Treat this as a fallback for reconstructing defensible `comment[data file]`
values when the repository metadata is incomplete.

## Step 5: Design Analysis

Analyze the experimental design:
- Are factor values properly defined?
- Is the comparison clear?
- Are replicates adequate?
- Are there potential batch effects? (instrument × condition confounding)
- Are there confounders? (age × disease, sex × treatment)

## Step 3: Batch Effect Detection

Cross-tabulate factor values against technical variables:

### Instrument Confounding
```text
Check: Is "condition" confounded with "instrument"?
  Cross-tab factor value × comment[instrument]

  BAD:  All "disease" on Instrument A, all "control" on Instrument B
        → Cannot separate biology from instrument effect

  GOOD: Both conditions measured on both instruments (balanced)
```

### TMT/Label Assignment
```text
Check: Are conditions balanced across TMT sets/channels?
  Cross-tab factor value × TMT set × channel position

  BAD:  All disease in TMT set 1, all control in TMT set 2
        → TMT set is confounded with condition

  GOOD: Each TMT set contains both disease and control samples
```

### Temporal Confounding
```text
Check: Were conditions processed at different times?
  If file names contain dates → check if conditions cluster by date

  BAD:  All disease samples processed Monday, all controls Friday
  GOOD: Randomized processing order
```

## Step 4: Confounder Detection

Check independence of factor values from other characteristics:

```text
For each characteristics column × factor value:
  If perfectly or strongly correlated → FLAG

Examples:
  ⚠ All female samples are disease, all male are control → sex confounds disease
  ⚠ All young (20-30Y) are treatment, all old (60-70Y) are control → age confounds treatment
  ⚠ All HeLa are condition A, all MCF7 are condition B → cell line IS the condition (expected)
```

Use a simple contingency analysis:
- If one cell of the cross-tab is 0 → PERFECT CONFOUND (critical)
- If distribution is very skewed → PARTIAL CONFOUND (warning)
- If roughly balanced → OK

## Step 5: Replication Assessment

```text
Biological replicates per condition:
  n=1:  ⚠ CRITICAL — No statistical testing possible
  n=2:  ⚠ WARNING — Very low power, only extreme effects detectable
  n=3:  ⚠ CAUTION — Minimum for basic statistics, low power
  n≥5:  ✓ Acceptable for many proteomics analyses
  n≥10: ✓ Good statistical power

Technical replicates:
  0: Common for TMT (label channels serve as tech reps)
  1: Standard for label-free (one injection per sample)
  2+: Used for quality assessment or when variability is high
```

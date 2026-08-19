---
name: sdrf:review
description: Use when the user wants a comprehensive quality review of an SDRF file, a PR review of an SDRF submission, a quality score assessment, or to improve/score an existing SDRF strictly against templates and specification rules (specificity, completeness, consistency; no speculative additions).
user-invocable: true
argument-hint: "[file path, PXD accession, or GitHub PR URL]"
---

# SDRF Review Workflow

You are performing a comprehensive quality review of an SDRF file — like a peer reviewer
would for a PRIDE submission or a community annotation PR.

If this context created or edited the SDRF, this workflow is an advisory
self-review only. For an approval verdict, dispatch a fresh context that follows
`skills/sdrf-adversarial-review/SKILL.md`; never approve work produced in the
same context.

## Step 1: Load Context

1. **Read the SDRF** content
2. **Detect templates** from metadata or content
3. **If PXD available** → fetch project context + publication:
   ```text
   mcp PRIDE → get_project_details(project_accession="PXD######")
   Extract PMID → mcp PubMed → get_article_metadata([pmid])
   ```
4. **If GitHub PR** → read the diff to understand what changed

## Step 2: Run Full Validation (sdrf-validate workflow)

Apply the complete validation checklist from the sdrf-validate skill.
Read `spec/sdrf-proteomics/TERMS.tsv` for column definitions and `spec/sdrf-proteomics/sdrf-templates/templates.yaml` for template metadata.
Collect all errors and warnings.

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
recommending `/sdrf:techrefine` — techsdrf can verify these parameters directly from
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
python -m tools massive-files PXD016117 --mode raw --format tsv
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

## Step 6: Quality Score

Calculate and present an overall quality score:

```text
# SDRF Quality Review: PXD012345
# Date: [date]
# Templates: ms-proteomics, human, clinical-metadata

## Quality Score: 78/100

### Breakdown:
  Completeness:     85/100  ████████░░
  Specificity:      70/100  ███████░░░
  Consistency:      90/100  █████████░
  Standards:        65/100  ██████░░░░
  Design Clarity:   80/100  ████████░░

### Errors Found: 3
  1. [ERROR] Row 12: UNIMOD:21 used for Acetyl (should be UNIMOD:1)
  2. [ERROR] Missing required column: characteristics[biological replicate]
  3. [ERROR] "cancer" is too generic — specify cancer subtype

### Warnings: 5
  1. [WARN] Case inconsistency in characteristics[sex]: "Male" vs "male"
  2. [WARN] Not using latest template version (v1.0.0 → v1.1.0 available)
  3. [WARN] Missing recommended column: characteristics[cell type]
  4. [WARN] Age format "58 years" should be "58Y"
  5. [WARN] Missing SDRF metadata columns (comment[sdrf version])

### Improvements Suggested: 3
  1. [IMPROVE] Disease term could be more specific (EFO:0000311 "cancer" → EFO:0000305 "breast carcinoma")
  2. [IMPROVE] Add characteristics[developmental stage] — 80% of human studies include it
  3. [IMPROVE] Consider adding comment[sdrf annotation tool] for provenance

### Cross-Reference:
  Publication match:  ✓ Sample count matches paper
  PRIDE file match:   ✓ All 240 raw files present
  Instrument match:   ✓ Q Exactive HF confirmed

### Verdict: NEEDS MINOR FIXES
  Fix the 3 errors and this SDRF is ready for submission.
```

## Step 7: Actionable Next Steps

Provide clear next steps:
1. List fixes in priority order
2. Offer to auto-fix what can be auto-fixed (`/sdrf:fix`)
3. Identify what needs human input (e.g., missing demographics)
4. Suggest running final validation after fixes
5. If the SDRF is for a ProteomeXchange dataset and the verdict is VALID or NEEDS MINOR FIXES:
   suggest contributing the annotation via `/sdrf:contribute {PXD}` to the
   `sdrf-annotated-datasets` community repository

---

## Quality scoring (5 dimensions)

_Folded from the former `sdrf:improve` skill: template/spec-driven scoring and non-speculative improvement suggestions._

# SDRF Specification-Driven Improvement Workflow

You are improving an SDRF file using ONLY specification/template rules.

Do not suggest additions based on:
- Similar datasets in PRIDE
- Literature expectations not encoded in templates
- "Could be more detailed" heuristics
- Personal curator preference

If a change is not justified by template metadata (`required`/`recommended`) or
TERMS.tsv rules, do not recommend it.

## Authoritative Sources (must read)

1. `spec/sdrf-proteomics/TERMS.tsv`
2. `spec/sdrf-proteomics/sdrf-templates/templates.yaml`
3. `spec/sdrf-proteomics/sdrf-templates/{name}/{version}/{name}.yaml` for each template in use

For affinity-proteomics, align with the official template/spec rules:
- Technology template: `affinity-proteomics`
- Optional experiment child template: `olink` OR `somascan` (mutually exclusive)

## Step 1: Determine Active Templates

1. Parse `comment[sdrf template]` columns (NT/VV format).
2. If missing/incomplete, detect from SDRF content and technology type.
3. Confirm template set with the user before proposing edits.

Do not "upgrade" template versions automatically. If a newer version exists, report it as an optional migration task.

## Step 2: Build Rule Matrix

Construct an explicit checklist from template YAML files:
- Required columns
- Recommended columns
- Optional columns
- Column validators (values/patterns/ontology)
- Allowed reserved words (`not available`, `not applicable`, `pooled`) via TERMS.tsv flags

For affinity-proteomics specifically, ensure checks include:
- `comment[platform]` (required)
- `comment[panel name]` (recommended)
- `comment[quantification unit]` (optional; values include NPX/RFU in spec)
- `comment[normalization method]` (optional)
- `comment[fraction identifier]` (optional)

And for child templates:
- Olink: check Olink-specific required/recommended columns from `olink.yaml`
- SomaScan: check SomaScan-specific required/recommended columns from `somascan.yaml`

## Step 3: Identify Spec-Backed Improvements

Classify findings into these categories only:

### A. Required Fixes (must change)
- Missing required columns from active templates
- Invalid column names not matching SDRF naming patterns
- Values violating template/TERMS validators
- Invalid reserved words per TERMS flags

### B. Recommended Fixes (should change)
- Missing columns marked `recommended` in active templates
- Values that fail recommended validators (warnings)

### C. Optional Enhancements (may change)
- Missing optional columns from active templates
- Only include if explicitly present in template metadata

Do not include free-form "quality" recommendations outside A/B/C.

## Step 4: Generate Deterministic Report

Report every finding with source traceability:
- Column or value issue
- Severity (`required` / `recommended` / `optional`)
- Exact source rule:
  - template file + column definition, or
  - TERMS.tsv field (usage/values/allow_not_available/allow_not_applicable/allow_pooled)
- Proposed correction

Example format:
```text
Finding: Missing column `comment[panel name]`
Severity: recommended
Source: spec/sdrf-proteomics/sdrf-templates/affinity-proteomics/1.0.0/affinity-proteomics.yaml
Action: Add `comment[panel name]` with panel identifier values.
```

## Step 5: Apply Changes Only with User Approval

Before modifying file contents:
1. Show the exact changes (old -> new)
2. Group by severity (required first)
3. Ask user approval for recommended/optional changes

Required fixes can be applied directly if the user asked to "fix all required issues."

## Output Constraints

- No speculative metadata additions
- No PRIDE peer comparison suggestions
- No literature-derived additions unless already required/recommended by templates
- No ontology "more specific child" suggestions unless validator explicitly requires a value constraint

The goal is strict conformance improvement, not curation enrichment.


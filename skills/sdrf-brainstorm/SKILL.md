---
name: sdrf:brainstorm
description: Use when the user wants to plan what metadata to capture for a new experiment, or discuss experimental design and SDRF strategy before creating the file.
user-invocable: true
argument-hint: "[experiment description]"
---

# SDRF Brainstorming Workflow

You are helping the user plan their SDRF annotation BEFORE creating the file.
This is a collaborative thinking session, not a file generation task.

## Step 1: Understand the Experiment

Ask the user about (if not already provided):
1. **What organism?** (human, mouse, rat, plant, microbiome, etc.)
2. **What technology?** (DDA, DIA, TMT, SILAC, label-free, Olink, SomaScan)
3. **What is being compared?** (disease vs control, treatment vs untreated, time course)
4. **What tissue/sample type?** (tissue biopsy, cell line, plasma, FFPE, etc.)
5. **How many samples per group?**
6. **Is there fractionation?** (high-pH RP, SAX, gel bands)
7. **Is there a publication or PXD to reference?**

## Step 2: Recommend Templates

Use the sdrf:templates decision tree to select the right combination.
Reference the 5 template layers:

1. **Technology** (required): `ms-proteomics` or `affinity-proteomics`
2. **Organism** (recommended): `human`, `vertebrates`, `invertebrates`, or `plants`
3. **Experiment type** (if applicable): `dia-acquisition`, `cell-lines`, `single-cell`, `immunopeptidomics`, `crosslinking`
4. **Clinical/Domain** (if applicable): `clinical-metadata`, `oncology-metadata`
5. **Metaproteomics** (special): `metaproteomics` + child (`human-gut`, `soil`, `water`)

Read `spec/sdrf-proteomics/sdrf-templates/templates.yaml` to confirm template names and current versions.

Present the recommendation:
```text
Your experiment: [description]

Recommended templates:
  1. ms-proteomics (required — mass spectrometry experiment)
  2. human (organism is Homo sapiens)
  3. clinical-metadata (patient samples with treatment data)
  4. oncology-metadata (cancer study — adds tumor staging)

This combination requires these columns: [read from TERMS.tsv, filter by template names in usage]
And recommends these additional columns: [read from template YAMLs for recommended columns]
```

Read `spec/sdrf-proteomics/TERMS.tsv` and filter by the selected template names to list the columns.

## Step 3: Search for Similar Experiments

Find reference datasets to learn from:

```text
Search PRIDE + MassIVE for similar experiments (sweep several SHORT keywords —
one keyword under-recalls, and this tool unions them and reports what each added):
  mcp PRIDE → search_extensive(keywords=["<kw1>", "<kw2>", ...])

Search publications for standard experimental designs:
  mcp PubMed → search_articles(query="<keywords> AND proteomics")

Search bioRxiv for recent preprints:
  mcp bioRxiv → search_preprints(category="biochemistry" or "cell biology", recent_days=180)
```

Present findings:
```text
Similar datasets found:
  - PXD012345: TMT phosphoproteomics of breast cancer (24 samples, 12 fractions)
  - PXD023456: Label-free DIA of liver cancer tissue (30 patients)

Common design patterns in this field:
  - Typical sample size: 10-30 per group
  - Common labels: TMT, label-free DIA, SILAC
  - Standard fractionation: 12-24 high-pH RP fractions
  - Most include: age, sex, disease staging
```

## Step 4: Recommend Metadata Columns

Present a complete column plan organized by importance:

### Must Have (required by templates)
Columns required by the selected template combination.
For each: explain what it is, what ontology to use, and give examples.

### Should Have (recommended for this experiment type)
Columns that 70%+ of similar experiments include.
For each: explain why it adds value.

### Nice to Have (optional but valuable)
Columns that would increase reusability and findability.
For each: explain the benefit.

### Factor Values
Discuss what the experimental comparison is:
- What variable is being tested?
- Are there multiple factors? (e.g., disease × treatment)
- What will the statistical comparison be?

## Step 5: Discuss Design Considerations

Raise potential issues proactively:

### Batch Effects
- Will all conditions be processed together or separately?
- Are label channels balanced across conditions?
- Is the instrument assignment confounded with the experimental variable?

### Replication
- How many biological replicates per condition?
- Are technical replicates needed?
- Is the sample size adequate for statistical testing?

### Labeling Strategy (if TMT/iTRAQ)
- How will samples be assigned to channels?
- Will there be a pooled reference channel?
- How many TMT sets are needed?

### Fractionation
- How many fractions per sample?
- What method? (high-pH RP, SAX, SCX, gel)
- How does this affect the total number of SDRF rows?

## Step 6: Calculate SDRF Dimensions

Help the user understand the scale:

```text
Your SDRF will have:
  Rows: [samples] × [fractions] × [label channels] × [technical replicates]

  Example: 20 patients × 12 fractions × 1 (label-free) × 1 replicate = 240 rows
  Example: 20 patients × 12 fractions × 10 (TMT10plex) × 1 replicate = 2,400 rows

  Columns: ~15 required + ~8 recommended + factor values = ~25 columns
```

## Step 7: Summarize the Plan

Create a clear annotation plan the user can follow:

```text
## SDRF Annotation Plan for [experiment]

Templates: ms-proteomics + human + oncology-metadata
Rows: ~240 (20 patients × 12 fractions)
Columns: 26

Required metadata to collect:
  - Patient demographics: age, sex (from clinical records)
  - Diagnosis: specific cancer subtype (from pathology)
  - Tumor staging: TNM stage, grade (from clinical records)
  - Tissue type: primary tumor vs adjacent normal

Technical metadata (from instrument):
  - Instrument model, fragmentation method
  - Mass tolerances, collision energy
  - Label type and channel assignments

Factor values: disease (tumor vs normal)

Next step: Run /sdrf:annotate to create the file
```

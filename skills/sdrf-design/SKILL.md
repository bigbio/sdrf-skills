---
name: sdrf:design
description: Use when the user wants to analyze the experimental design encoded in an SDRF file, check for batch effects, confounders, or replication issues.
user-invocable: true
argument-hint: "[file path or paste SDRF content]"
---

# SDRF Experimental Design Analysis

You are analyzing the experimental design captured in an SDRF file to detect
statistical and methodological issues.

## Step 1: Parse the Design

Extract from the SDRF:
- **Conditions**: Unique values in factor value columns
- **Samples per condition**: Count of unique source names per condition
- **Biological replicates**: From characteristics[biological replicate]
- **Technical replicates**: From comment[technical replicate]
- **Fractions**: From comment[fraction identifier]
- **Labels**: From comment[label]
- **Instruments**: From comment[instrument]
- **Files per sample**: Count of rows per source name

> **Exclude non-biological channels before counting replicates or testing balance.** Drop rows that are
> reference / carrier / bridge / empty / pooled / control — `characteristics[sample type]` in {reference,
> bridge, carrier, empty, pooled, ...-control}, or rows carrying `comment[carrier channel]` (`PRIDE:0000901`) /
> `comment[reference channel]` (`PRIDE:0000899`). Counting them inflates n and corrupts the TMT/label
> cross-tabs. Replication = unique `source name` per condition, not raw row count.

## Step 2: Design Summary

Present a clear summary:

```text
Experimental Design Summary:
  Type: Two-group comparison
  Factor: disease (breast carcinoma vs normal)

  Group 1 "breast carcinoma": 10 biological replicates
  Group 2 "normal": 10 biological replicates

  Technical setup:
    Label: TMT10plex (10 channels per plex)
    Fractions: 12 per TMT set
    Technical replicates: 1 per sample
    Instrument: Q Exactive HF

  File math:
    2 TMT sets × 12 fractions = 24 raw files
    Each file → 10 rows (one per TMT channel)
    Total SDRF rows: 240

  Statistical power:
    n=10 per group — adequate for detecting medium effect sizes
```

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

## Step 6: Comparison Suggestions

Based on the factor values, suggest:
1. The primary comparison (disease vs control)
2. Secondary comparisons (if multiple factors)
3. Whether paired analysis is appropriate (if `characteristics[individual]` IDs match across conditions)
4. MSstats contrast matrix format:

```r
Example for disease (breast carcinoma vs normal):
  comparison <- matrix(c(-1, 1), nrow=1)
  colnames(comparison) <- c("normal", "breast carcinoma")
  rownames(comparison) <- c("breast_carcinoma_vs_normal")

Example for multi-group (A vs B, A vs C):
  comparison <- matrix(c(-1,1,0, -1,0,1), nrow=2, byrow=TRUE)
  colnames(comparison) <- c("groupA", "groupB", "groupC")
  rownames(comparison) <- c("B_vs_A", "C_vs_A")
```

## Step 7: Report

Present findings as an actionable report:

```text
# Experimental Design Analysis

## Summary
  [design summary from Step 2]

## Issues Found

### 🔴 Critical
  [perfect confounds, n=1 replication]

### 🟡 Warnings
  [partial confounds, low replication, unbalanced TMT]

### 🟢 Good
  [balanced design aspects, adequate replication]

## Recommendations
  1. [specific actionable recommendations]
  2. [suggested changes to SDRF or experimental design]
```

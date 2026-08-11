---
name: sdrf:techrefine
description: Use when the user wants to refine or verify SDRF technical metadata (instrument, tolerances, modifications, DDA/DIA) using raw MS file analysis via techsdrf.
user-invocable: true
argument-hint: "[PXD accession or SDRF file path]"
---

# SDRF Technical Metadata Refinement Workflow

You are guiding the user through refining SDRF technical metadata using **techsdrf** —
a CLI tool that downloads raw MS files, analyzes them with pyopenms, and auto-detects
instrument parameters, mass tolerances, PTMs, and DDA/DIA mode.

This workflow verifies and corrects technical columns that are often filled manually
from PRIDE metadata or publications, which may be incomplete or inaccurate.

## Step 1: Check Prerequisites

### 1.1 Verify techsdrf is installed
```bash
techsdrf --version
# If not installed:
pip install techsdrf
```

### 1.2 Verify raw file converters (as needed)
- **Thermo .raw files**: ThermoRawFileParser is required
  ```bash
  conda install -c bioconda thermorawfileparser
  ```
- **Bruker .d / SCIEX .wiff files**: msconvert (ProteoWizard) is required
  ```bash
  # Check availability:
  msconvert --help
  ```

If converters are missing, inform the user which file types cannot be processed
and suggest installation commands. techsdrf will skip files it cannot convert.

## Step 2: Choose Refinement Mode

Present the three modes and help the user choose:

### Mode A — Refine from PRIDE (recommended for PXD datasets)
Downloads raw files from PRIDE, analyzes them, and refines the SDRF.
```bash
techsdrf refine -p PXD###### -s input.sdrf.tsv -o refined.sdrf.tsv -v
```
**Use when**: The user has a PXD accession and an SDRF file to refine.

### Mode B — Refine from local files
Points to a local directory of raw files instead of downloading from PRIDE.
```bash
techsdrf refine -d /path/to/raw/files -s input.sdrf.tsv -o refined.sdrf.tsv -v
```
**Use when**: The user already has raw files locally.

### Mode C — Info only (inspect without refining)
Inspects the current SDRF technical metadata without downloading or analyzing files.
```bash
techsdrf info -s input.sdrf.tsv
```
**Use when**: The user wants a quick check of what technical metadata is declared.

## Step 3: Configure Analysis

Help the user set the right options for their analysis:

### 3.1 Number of files to analyze
- `-n 3` (default): Analyze 3 representative files — fast, usually sufficient
- `-n 5` or `-n 10`: More files for higher confidence
- `-a`: Analyze ALL files — thorough but slow; use for heterogeneous datasets
  where different files may have different instruments or acquisition methods

### 3.2 File type filter
- `-t raw`: Thermo .raw files only
- `-t d`: Bruker .d directories only
- `-t wiff` or `-t wiff2`: SCIEX files only
- If not specified, techsdrf processes all supported file types

### 3.3 Tolerance unit
- `-u ppm` (default): Report mass tolerances in parts per million
- `-u Da`: Report mass tolerances in Daltons

### 3.4 PTM detection
- By default, techsdrf performs three tiers of PTM detection
- `--skip-ptm`: Skip PTM detection (faster, use if only instrument/tolerance info needed)

### 3.5 Keep downloaded files
- `--keep-files`: Retain downloaded raw and converted mzML files after analysis
- By default, files are cleaned up to save disk space

## Step 4: Run techsdrf

### 4.1 Present the full command
Assemble the command with all chosen options and present it to the user:
```bash
techsdrf refine \
  -p PXD###### \
  -s input.sdrf.tsv \
  -n 5 \
  -o refined.sdrf.tsv \
  -v
```

### 4.2 Explain what happens
The techsdrf pipeline runs these stages:
1. **Download** — Fetches N raw files from PRIDE (or reads local files)
2. **Convert** — Converts raw files to mzML using ThermoRawFileParser or msconvert
3. **Analyze** — Parses mzML with pyopenms to extract instrument metadata, scan characteristics, and spectra
4. **Detect** — Determines instrument model, acquisition mode, fragmentation, tolerances, labels, and PTMs
5. **Compare** — Compares detected parameters against declared values in the SDRF
6. **Refine** — Produces a refined SDRF with corrected/added technical metadata

### 4.3 The user runs the command
The user executes the command in their terminal. techsdrf produces:
- Console output with detected parameters and comparison results
- A refined SDRF file (if `-o` was specified)

## Step 5: Interpret Results

Parse the techsdrf output and explain each detected parameter:

### 5.1 Instrument detection
| Detected Field | Source | Example |
|---------------|--------|---------|
| Instrument model | Raw file header | Q Exactive HF-X |
| Serial number | Raw file header | Exactive Series slot #1234 |
| Mass analyzer | Scan metadata | orbitrap |

**What to check**: Does the detected model match what's in the SDRF? PRIDE often
has generic names (e.g., "Q Exactive") while raw files have the specific model
(e.g., "Q Exactive HF-X").

### 5.2 Acquisition mode
| Detected Field | Method | Example |
|---------------|--------|---------|
| DDA vs DIA | Spectrum analysis | `NT=Data-dependent acquisition;AC=PRIDE:0000627` |

**What to check**: Is the acquisition method in the SDRF correct? Misclassification
of DDA as DIA (or vice versa) affects which analysis pipelines can be used.

### 5.3 Fragmentation
| Detected Field | Source | Example |
|---------------|--------|---------|
| Dissociation method | MS2 scan metadata | HCD |
| Collision energy | Scan parameters | 28 NCE |

**What to check**: Does the SDRF declare the correct fragmentation method?
Multiple methods may be used (e.g., HCD + EThcD for different scans).

### 5.4 Mass tolerances
| Detected Field | Method | Example |
|---------------|--------|---------|
| Precursor tolerance | Gaussian fitting (RunAssessor) + param-medic | 10 ppm |
| Fragment tolerance | Gaussian fitting (RunAssessor) + param-medic | 20 ppm |

techsdrf uses two independent methods to estimate tolerances. Both are reported
for comparison. **What to check**: Do the detected tolerances match the SDRF?
Papers often round tolerances or report search engine settings instead of
instrument-level tolerances.

### 5.5 Labels
| Detected Field | Method | Example |
|---------------|--------|---------|
| TMT/iTRAQ | Reporter ion detection (100-140 m/z) | TMT10plex |
| SILAC | Known mass shift patterns | not detected |

**What to check**: Does the labeling in the SDRF match what's actually in the
spectra? This catches cases where TMT is declared but the data is actually
label-free (or vice versa).

### 5.6 PTM detection (three tiers)
| Tier | Method | Example |
|------|--------|---------|
| 1. Reporter/diagnostic ions | Known ion signatures (100-140 m/z) | TMT reporter ions |
| 2. Diagnostic ions + neutral losses | Characteristic fragment patterns | Phospho (H3PO4 loss at 97.98 Da) |
| 3. Open mass shifts | Poisson-tested mass deltas | Oxidation (+15.995 Da) |

**What to check**: Are all detected PTMs declared as `comment[modification parameters]`
in the SDRF? Are there declared modifications that were NOT detected (may indicate
incorrect annotation)?

### 5.7 Comparison summary
techsdrf reports each parameter with a status:
- **MATCH** — SDRF value matches detected value
- **MISMATCH** — SDRF value differs from detected value (flag for correction)
- **MISSING_SDRF** — Detected in raw data but not declared in SDRF (flag for addition)
- **IMPROVED** — Detected value is more specific than SDRF value (e.g., "Q Exactive" → "Q Exactive HF")

List all MISMATCH and MISSING_SDRF items with recommended fixes.

## Step 6: Apply Refinements

### 6.1 If techsdrf produced a refined SDRF file
Present the differences between original and refined SDRF:
```text
CHANGED: comment[instrument] — "Q Exactive" → "Q Exactive HF-X" (AC=MS:1002877;NT=Q Exactive HF-X)
CHANGED: comment[precursor mass tolerance] — "20 ppm" → "10 ppm"
ADDED:   comment[dissociation method] — "HCD" (was empty)
CHANGED: comment[modification parameters] col 3 — REMOVED Phospho (not detected in spectra)
```

### 6.2 Let user approve/reject each change
For each changed column:
- Show the old value and the new value
- Explain WHY techsdrf made this change (what evidence from raw data)
- Let the user approve or reject the individual change

### 6.3 If the user is working on an in-memory SDRF from `/sdrf:annotate`
Instead of a file diff, show the corrected values to paste into the SDRF:
```text
Update these technical columns based on raw file analysis:
  comment[instrument]: AC=MS:1002877;NT=Q Exactive HF-X
  comment[precursor mass tolerance]: 10 ppm
  comment[fragment mass tolerance]: 20 ppm
  comment[dissociation method]: NT=HCD;AC=MS:1000422
```

## Step 7: Post-Refinement

### 7.1 Update spec to latest version
Before validating, ensure the SDRF specification and templates are up to date:
```bash
git submodule update --remote --recursive
```
This pulls the latest column definitions (`spec/sdrf-proteomics/TERMS.tsv`) and
template versions (`spec/sdrf-proteomics/sdrf-templates/templates.yaml`).
Validation against outdated templates may miss new required columns or accept
deprecated formats.

### 7.2 Validate with sdrf-pipelines
**Always** run programmatic validation on the refined SDRF before presenting
results to the user:
```bash
parse_sdrf validate-sdrf \
  --sdrf_file refined.sdrf.tsv \
  --template <template1> \
  --template <template2>
```
Detect templates from `comment[sdrf template]` columns in the SDRF.
If `parse_sdrf` is not installed, tell the user: `pip install sdrf-pipelines`

If validation finds errors introduced by the refinement, fix them and re-run
until validation passes (or only warnings remain).

### 7.3 Contribute
If this is a ProteomeXchange dataset:
```text
Your refined SDRF has verified technical metadata from actual raw file analysis.
Run /sdrf:contribute to submit this annotation to the community repository.
```

## What techsdrf Detects

| Parameter | Detection Method |
|-----------|-----------------|
| Instrument model + serial | Raw file header parsing |
| DDA vs DIA | Spectrum analysis (isolation window patterns) |
| Fragmentation method (HCD/CID/ETD/EThcD) | MS2 scan metadata |
| Precursor mass tolerance | Gaussian fitting (RunAssessor) + param-medic dual estimation |
| Fragment mass tolerance | Gaussian fitting (RunAssessor) + param-medic dual estimation |
| Labels (TMT/iTRAQ) | Reporter ion detection in 100-140 m/z range |
| PTMs (phospho, glyco, etc.) | Diagnostic ions + neutral losses + open mass shifts |
| Variable modifications | Open mass-shift analysis with Poisson statistical testing |

## Important Rules

- techsdrf requires actual raw MS files — it cannot refine from metadata alone
- For Thermo .raw files, ThermoRawFileParser must be installed
- Detected parameters are empirical — they reflect what's IN the raw data, not what was intended
- If techsdrf detects a PTM not declared in the SDRF, confirm with the user before adding it (could be a biological signal or an artifact)
- If techsdrf does NOT detect a declared PTM, it may be at low abundance — do not automatically remove without user confirmation
- Always verify instrument ontology terms via OLS after techsdrf detection:
  ```text
  mcp OLS → searchClasses(query="Q Exactive HF-X", ontologyId="ms")
  ```

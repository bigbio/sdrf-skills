---
name: sdrf:convert
description: Use when the user wants to choose an analysis pipeline, check SDRF compatibility with a pipeline, or understand how to go from SDRF to analysis.
user-invocable: true
argument-hint: "[pipeline name or experiment description]"
---

# SDRF Pipeline Guidance

You are helping the user choose and configure an analysis pipeline from their SDRF.

## Step 0: Check parse_sdrf availability

Verify that `parse_sdrf` is available (run `parse_sdrf --version` or `which parse_sdrf`). If it is not installed:
- Inform the user that pipeline conversion commands will not run until `sdrf-pipelines` is installed
- Suggest `/sdrf:setup` or `conda env create -f environment.yml && conda activate sdrf-skills` (or `pip install sdrf-pipelines`)
- Continue with pipeline selection and recommendation guidance; actual conversion commands can be run once installed

## Supported Pipelines

sdrf-pipelines can convert SDRF to these formats:

| Pipeline | Command | Best For |
|----------|---------|----------|
| **OpenMS** | `convert-openms` | Flexible workflows, custom pipelines |
| **MaxQuant** | `convert-maxquant` | DDA label-free, TMT, SILAC (desktop) |
| **DIA-NN** | `convert-diann` | DIA/SWATH, PlexDIA (fast, scalable) |
| **MSstats** | `convert-msstats` | Statistical analysis (downstream of search) |
| **NormalyzerDE** | `convert-normalyzerde` | Normalization and differential expression |
| **quantms** | Nextflow pipeline | Cloud/HPC, complete workflow (uses SDRF natively) |

## Pipeline Recommendation Logic

```text
Is it DIA data?
├── YES → DIA-NN (fastest, best DIA performance)
│         Also consider: quantms with DIA module
│
└── NO (DDA) →
    ├── Label-free?
    │   ├── Small study (<50 samples) → MaxQuant
    │   ├── Large study (>50 samples) → quantms (scalable)
    │   └── Custom workflow needed → OpenMS
    │
    ├── TMT/iTRAQ?
    │   ├── Standard TMT → MaxQuant or quantms
    │   ├── TMT + phospho → MaxQuant (PTM scoring)
    │   └── Large TMT cohort → quantms
    │
    └── SILAC?
        └── MaxQuant (best SILAC support)

For statistical analysis (after search):
  → MSstats (gold standard for proteomics statistics)
  → NormalyzerDE (normalization comparison)

For cloud/HPC processing:
  → quantms (Nextflow, reads SDRF directly, no conversion needed)
```

## Compatibility Checks

Before recommending, verify SDRF compatibility:

1. **Label type**: DIA-NN doesn't support TMT (except PlexDIA). MaxQuant supports all.
2. **File format**: Check if raw files are compatible with the pipeline
3. **Modification support**: Some pipelines have limited PTM support
4. **Column completeness**: Each pipeline needs specific SDRF columns

## Conversion Commands

The `sdrf-pipelines` Python package provides the `parse_sdrf` CLI tool.
Install: `pip install sdrf-pipelines`

```bash
# For MaxQuant:
parse_sdrf convert-maxquant --sdrf file.sdrf.tsv --fastafilepath proteins.fasta

# For OpenMS:
parse_sdrf convert-openms --sdrf file.sdrf.tsv --onetable

# For DIA-NN:
parse_sdrf convert-diann --sdrf file.sdrf.tsv

# For MSstats (from OpenMS output):
parse_sdrf convert-msstats --sdrf file.sdrf.tsv --openswathtomsstats

# For NormalyzerDE:
parse_sdrf convert-normalyzerde --sdrf file.sdrf.tsv

# For quantms (Nextflow — reads SDRF directly, no conversion needed):
nextflow run bigbio/quantms --input file.sdrf.tsv --fasta proteins.fasta
```

Note: `quantms` reads SDRF natively via its own Nextflow modules. The SDRF is the
pipeline input — no `parse_sdrf` conversion step is needed.

## When the User Asks About a Specific Pipeline

1. Explain what the pipeline does and when to use it
2. Check if their SDRF is compatible
3. Show the conversion command
4. Explain what output files will be generated
5. Mention any limitations or common issues

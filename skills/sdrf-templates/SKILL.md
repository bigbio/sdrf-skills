---
name: sdrf-templates
description: Use when the user asks about SDRF templates, wants to select templates for an experiment, or needs to understand template layers, inheritance, mutual exclusivity, and selection rules.
user-invocable: true
argument-hint: "[experiment description or template name]"
---

# SDRF Template System

Templates define which columns are required for a given experiment type.
Each SDRF can declare one or more templates via `comment[sdrf template]` columns.

## Specification Data (always read from source)

The authoritative source for all template information is in the `spec/` submodule:

- **Template manifest**: Read `spec/sdrf-proteomics/sdrf-templates/templates.yaml`
- **Individual templates**: Read `spec/sdrf-proteomics/sdrf-templates/{name}/{version}/{name}.yaml`
- **Column definitions**: Read `spec/sdrf-proteomics/TERMS.tsv` (the `usage` field shows which templates include each column)

Always read `templates.yaml` when answering questions about templates, versions, inheritance,
or mutual exclusivity. Never rely on memorized template data — the spec evolves.

### How to Read templates.yaml

The manifest file lists every template with these fields:
- `name` — template identifier (e.g., `ms-proteomics`, `human`)
- `version` — current version (e.g., `1.1.0`)
- `extends` — parent template with version constraint (e.g., `sample-metadata@>=1.0.0`)
- `description` — what the template adds
- `usable_alone` — whether it can be used without other templates (only `ms-proteomics` and `affinity-proteomics`)
- `excludes` — templates that are mutually exclusive with this one
- `layer` — which selection layer it belongs to

### How to Read Individual Template YAMLs

Each template has a YAML file at `spec/sdrf-proteomics/sdrf-templates/{name}/{version}/{name}.yaml`.
These define the columns the template adds, with requirement levels (required/recommended/optional).

### How to Find Columns for a Template

Two ways:
1. Read the individual template YAML → lists columns with requirement levels
2. Read TERMS.tsv → filter rows where `usage` contains the template name

## Template Layers (Methodology — stable across versions)

Templates are organized into layers. Each layer serves a different purpose:

1. **Technology** (REQUIRED — pick exactly one): The measurement technology used.
   - `ms-proteomics` — mass spectrometry experiments
   - `affinity-proteomics` — Olink, SomaScan, and other affinity platforms
   - These are **mutually exclusive**

2. **Sample/Organism** (RECOMMENDED — pick at most one organism template):
   - `human` — Homo sapiens samples
   - `vertebrates` — mouse, rat, zebrafish, etc.
   - `invertebrates` — Drosophila, C. elegans, insects
   - `plants` — Arabidopsis, crops
   - Organism templates are **mutually exclusive** with each other
   - `clinical-metadata` — clinical studies (can combine with organism templates)
   - `oncology-metadata` — cancer studies (extends clinical-metadata)

3. **Experiment** (OPTIONAL — pick any applicable):
   - `cell-lines` — cultured cell lines
   - `dia-acquisition` — DIA/SWATH (extends ms-proteomics)
   - `single-cell` — single-cell proteomics (extends ms-proteomics)
   - `immunopeptidomics` — MHC peptide studies (extends ms-proteomics)
   - `crosslinking` — XL-MS (extends ms-proteomics)
   - `olink` — Olink PEA (extends affinity-proteomics)
   - `somascan` — SomaScan (extends affinity-proteomics)

4. **Metaproteomics** (SPECIAL — uses its own sample scheme):
   - `metaproteomics` — environmental/microbiome base (excludes sample-metadata)
   - `human-gut` — host-associated microbiome
   - `soil` — soil metaproteomics
   - `water` — aquatic metaproteomics

## Mutual Exclusivity Rules (Methodology)

1. `ms-proteomics` ↔ `affinity-proteomics` — different technologies
2. `human` ↔ `vertebrates` ↔ `invertebrates` ↔ `plants` — pick at most one organism
3. `metaproteomics` **excludes** `sample-metadata` — uses its own sample scheme
4. `olink` and `somascan` extend `affinity-proteomics` — cannot combine with `ms-proteomics`
5. `dia-acquisition`, `single-cell`, `immunopeptidomics`, `crosslinking` extend `ms-proteomics` — cannot combine with `affinity-proteomics`

Read `templates.yaml` for the full `excludes` field on each template to verify mutual exclusivity.

## Template Selection Decision Tree (Methodology)

```text
Is it mass spectrometry?
├── YES → ms-proteomics
│   ├── Human samples? → + human
│   │   ├── Cancer study? → + oncology-metadata
│   │   ├── Clinical trial / drug treatment? → + clinical-metadata
│   │   └── Cell lines from human? → + human + cell-lines
│   ├── Mouse/rat/zebrafish? → + vertebrates
│   │   └── Cell lines from animal? → + vertebrates + cell-lines
│   ├── Drosophila/C. elegans? → + invertebrates
│   ├── Plant? → + plants
│   ├── Environmental/microbiome? → metaproteomics (REPLACES organism layer)
│   │   ├── Human gut? → + human-gut
│   │   ├── Soil? → + soil
│   │   └── Water? → + water
│   ├── DIA/SWATH/diaPASEF? → + dia-acquisition
│   ├── Single-cell proteomics? → + single-cell
│   ├── MHC/immunopeptidome? → + immunopeptidomics
│   └── Cross-linking MS? → + crosslinking
│
└── NO (affinity-based) → affinity-proteomics
    ├── Olink? → + olink
    └── SomaScan? → + somascan
```

## Template Inheritance (Methodology)

When templates are combined, the validator merges all columns from all ancestors.
If a parent says OPTIONAL but a child says REQUIRED → REQUIRED wins (strictest requirement).

Read `templates.yaml` to see the full inheritance tree via the `extends` field on each template.
The general structure is:
- `base` → `sample-metadata` → technology + organism + experiment templates
- `base` → `metaproteomics` → environment-specific templates (excludes sample-metadata)

## Common Template Combinations (Methodology)

| Experiment Type | Templates |
|-----------------|-----------|
| Human tissue DDA (label-free or TMT) | `ms-proteomics`, `human` |
| Human cancer clinical trial | `ms-proteomics`, `human`, `clinical-metadata`, `oncology-metadata` |
| Mouse tissue DIA | `ms-proteomics`, `vertebrates`, `dia-acquisition` |
| Human cell line study | `ms-proteomics`, `human`, `cell-lines` |
| Single-cell proteomics (human) | `ms-proteomics`, `human`, `single-cell` |
| Immunopeptidomics (human) | `ms-proteomics`, `human`, `immunopeptidomics` |
| Cross-linking MS (human) | `ms-proteomics`, `human`, `crosslinking` |
| Gut metaproteomics | `ms-proteomics`, `metaproteomics`, `human-gut` |
| Soil metaproteomics | `ms-proteomics`, `metaproteomics`, `soil` |
| Olink plasma study | `affinity-proteomics`, `human`, `olink` |
| SomaScan serum study | `affinity-proteomics`, `human`, `somascan` |
| Drosophila DDA | `ms-proteomics`, `invertebrates` |
| Arabidopsis study | `ms-proteomics`, `plants` |
| Drug treatment study (human cells) | `ms-proteomics`, `human`, `clinical-metadata`, `cell-lines` |

## How to Detect Templates from Existing SDRF

When an SDRF file already exists, detect templates from:
1. **Metadata column**: `comment[sdrf template]` → e.g., `NT=ms-proteomics;VV=v1.1.0`
2. **Organism**: `characteristics[organism]` → Homo sapiens = human, Mus musculus = vertebrates
3. **Technology type**: "proteomic profiling by mass spectrometry" → ms-proteomics
4. **Acquisition method**: `comment[proteomics data acquisition method]` → DIA = dia-acquisition
5. **Cell line columns present**: `characteristics[cell line]` → cell-lines
6. **MHC columns present**: `characteristics[mhc protein complex]` → immunopeptidomics
7. **Crosslinker columns**: `comment[cross-linker]` → crosslinking
8. **Single cell columns**: `characteristics[single cell isolation protocol]` → single-cell
9. **Environmental columns**: `characteristics[environmental sample type]` → metaproteomics
10. **Oncology columns**: `characteristics[tumor grading]` → oncology-metadata
11. **Olink columns**: `comment[panel name]` (or legacy `comment[olink panel]`) → olink
12. **SomaScan columns**: `comment[somascan menu]` → somascan

## How to Respond to User Queries

### If they describe an experiment:
1. Walk through the decision tree and recommend a specific template combination
2. Read `templates.yaml` to confirm templates exist and get current versions
3. Read TERMS.tsv to list the columns the combination adds
4. Explain WHY each template was chosen

### If they ask about a specific template:
1. Read its entry in `templates.yaml` for version, extends, excludes, description
2. Read its individual YAML for the columns it adds (with requirement levels)
3. Explain when to use it, what it inherits from, and what it's mutually exclusive with

### If they ask about differences between templates:
Compare side by side — read both template YAMLs for their column lists.

### If they provide an SDRF and ask "what templates should this use?":
Auto-detect from the content using the detection rules above.

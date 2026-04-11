# Annotation Notes: PXD008355
# E. coli K-12 label-free quantitative proteomics across growth media

## Dataset Overview

**PRIDE accession**: PXD008355  
**Title**: Proteome of Escherichia coli K-12 MG1655 under different carbon sources  
**Organism**: *Escherichia coli* K-12 MG1655  
**Technology**: Label-free quantitative mass spectrometry (DDA)  
**Instrument**: Q Exactive HF (Thermo Fisher Scientific)  
**Design**: 3 biological replicates × 4 growth conditions (glucose, acetate, glycerol, LB)  

---

## Workflow Trace (sdrf:annotate steps)

### Step 0 — parse_sdrf check
`parse_sdrf` is available (install: `pip install sdrf-pipelines`).

### Step 1 — PRIDE metadata
```
get_project_details("PXD008355")
→ organism:      Escherichia coli
→ organism part: whole organism (bacteria, no tissue)
→ instrument:    Q Exactive HF
→ modifications: Carbamidomethyl (C) fixed; Oxidation (M) variable
→ publication:   PMID 29167387
```

```
get_project_files("PXD008355")
→ 12 .raw files:
    glucose_rep1.raw  glucose_rep2.raw  glucose_rep3.raw
    acetate_rep1.raw  acetate_rep2.raw  acetate_rep3.raw
    glycerol_rep1.raw glycerol_rep2.raw glycerol_rep3.raw
    lb_rep1.raw       lb_rep2.raw       lb_rep3.raw
```

Publication (PMID 29167387):
> Proteomics shows E. coli K-12 MG1655 grown on minimal media (glucose, acetate,
> glycerol) and rich media (LB). Whole-cell lysate, trypsin digest,
> LC-MS/MS on Q Exactive HF, 75 min gradients.

### Step 2 — Template selection
| Template | Reason |
|----------|--------|
| `ms-proteomics` | Mass spectrometry |
| (no organism-specific template) | Bacteria — no vertebrates/invertebrates/plants template applies |

E. coli is a prokaryote; the organism templates (human, vertebrates, invertebrates, plants) are
eukaryote-specific. Only the base `ms-proteomics` template is required.

### Step 3 — Ontology term lookups

| Column | Value | Accession | Source |
|--------|-------|-----------|--------|
| `characteristics[organism]` | Escherichia coli | NCBITaxon:562 | OLS → ncbitaxon |
| `characteristics[strain]` | K-12 MG1655 | NCBITaxon:511145 | OLS → ncbitaxon (strain level) |
| `characteristics[organism part]` | whole organism | UBERON:0000468 | OLS → uberon |
| `characteristics[disease]` | normal | PATO:0000461 | PATO (no disease, bacteria) |
| `comment[instrument]` | Q Exactive HF | MS:1002523 | OLS → ms |
| `comment[cleavage agent details]` | Trypsin | MS:1001251 | OLS → ms |
| `comment[modification parameters]` col 1 | Carbamidomethyl C fixed | UNIMOD:4 | UNIMOD |
| `comment[modification parameters]` col 2 | Oxidation M variable | UNIMOD:35 | UNIMOD |

### Step 4 — Key annotation decisions

- **No human/animal template** — bacteria don't have age/sex/ancestry columns
- **Disease = "normal"** — bacteria; not a disease study. Use PATO:0000461
- **Strain as characteristic** — E. coli studies should capture strain (K-12 MG1655)
- **Growth condition = factor value** — the variable being compared across samples
- **Label**: `label free sample` (LFQ, no stable-isotope labels)
- **Fractions**: none (1 fraction per sample, `comment[fraction identifier]` = 1)
- **Technical replicates**: none (1 run per biological replicate)

### Step 5 — Validation

```bash
# Structural validation (no OLS network required):
parse_sdrf validate-sdrf \
  --sdrf_file PXD008355.sdrf.tsv \
  --template ms-proteomics \
  --skip-ontology

# → Everything seems to be fine. Well done.

# Full validation (requires network access to EBI OLS):
parse_sdrf validate-sdrf \
  --sdrf_file PXD008355.sdrf.tsv \
  --template ms-proteomics
```

**Annotation decisions for bacteria (prokaryotes):**

- `characteristics[organism part]`: Use `not applicable` for bacteria — they lack anatomical
  tissues, so UBERON/BTO terms do not apply. Do NOT use "whole organism".
- `comment[proteomics data acquisition method]`: Required by `ms-proteomics` template.
  Value: `Data-Dependent Acquisition` for DDA studies.
- `factor value[...]` must be the **last** column group (after SDRF metadata columns).

---

## Files

- `PXD008355.sdrf.tsv` — the annotated SDRF file

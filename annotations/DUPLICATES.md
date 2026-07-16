# Duplicate / overlapping depositions in the SCP corpus

Independent annotator agents verified these by **SHA-1 checksum, file-by-file** — not by filename
or description similarity. Each accession has been annotated on its own terms (an SDRF describes
*that* deposition), but **a consumer concatenating these SDRFs will double-count real cells**.

Whoever assembles the corpus must pick one accession per group.

---

## Group 1 — PXD019515 ⊂ PXD022791

Same paper (PMC8178986, Cong et al., *Chem. Sci.* 2020; nanoPOTS single HeLa + LCM spinal neurons).

| | files | note |
|---|---|---|
| `PXD019515` | 14 | **every entry** (12 `.raw` + both `.msf`) is byte-identical inside PXD022791. Zero files unique to it. |
| `PXD022791` | 24 + | superset; adds 0.5 ng HeLa digest standard runs |

Concatenating both yields **36 rows for 24 distinct runs**, and would turn the paper's
n=3-per-group motor-neuron vs interneuron result into n=6 against duplicated spectra.

**Recommended canonical: `PXD022791`** (superset). The 12 shared rows are byte-identical across
both SDRFs (all 43 columns diffed, zero differences; row order and `run 1`–`12` numbering
preserved so they are `diff`-able).

---

## Group 2 — PXD030607 ⊂ PXD031955

Same paper (PMID:35464213; Xenopus blastomere CE-ESI-MS).

| | files | note |
|---|---|---|
| `PXD030607` | 15 RAW | **all 15 match PXD031955 on SHA-1 and byte size**. Submitted 2021-12-22. |
| `PXD031955` | 18 RAW | superset; submitted 2022-02-28. **The only accession the paper cites.** |

The 3 files unique to PXD031955 are the *actual single mouse neurons*
(`2017-11-*_Single_Neuron_*`), so the abstract's "37 proteins between three different cells" claim
is **not reproducible from PXD030607 at all**.

**Recommended canonical: `PXD031955`** — superset, paper-cited, and the only one containing the
single-neuron runs. `PXD030607` is the earlier superseded deposition.

---

## Group 3 — PXD003121 / PXD003691 / PXD004142 (same study, deposited three times)

Same paper (PMID:27215607; human oocyte SP3).

| | runs | note |
|---|---|---|
| `PXD003121` | 21 | **superset** |
| `PXD003691` | 18 | |
| `PXD004142` | 18 | **the accession the paper's abstract advertises** |

Cross-reading the siblings was load-bearing rather than optional: `130403SL_100oocytes_IVF_1/_2.raw`
do not say which is mature, and a sibling's MaxQuant `summary.txt` names them
`sample1_longer_immature` / `sample2_longer_mature`. Guessing from the `_1`/`_2` suffix had a 50%
chance of inverting two rows.

**Recommendation unresolved:** `PXD003121` is the superset but `PXD004142` is what the paper cites.
Needs a human decision. All three are annotated; do not load more than one.

---

## Why these were annotated anyway

Each SDRF is correct *for its own accession* — that is what an SDRF describes, and a consumer
fetching `PXD030607` should find a faithful annotation of `PXD030607`. Silently skipping the
subsets would leave them un-annotated with no record of why (see
`memory: sdrf-annotation-report-required`). The duplication is recorded here and cross-referenced
from each report instead.

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

## Group 4 — PXD053023 ⊂ PXD057685

Same paper (PMID:39674510; Nemes lab, *X. laevis* blastomere + HeLa-standard Eco-IMS CE-ESI ddaPASEF on
a timsTOF Pro).

| | files | note |
|---|---|---|
| `PXD053023` | 8 | deposited 2025-02. **All 8 files** (6 `.zip` + 2 FASTA) present in PXD057685. |
| `PXD057685` | 9 | deposited 2025-05; superset, adds only `SupplementalSpectra.7z` (annotation spectra, no new runs). |

`files/all` carries **no checksum** for either accession (as in PXD046467). Verified instead by
(a) identical filenames + **byte-exact `fileSizeBytes`** on all 8 shared files (incl. the 18.28 GB
`500pgHeLa_raw.zip` and 11.92 GB `xenopus.zip`), and (b) **HTTP-range SHA-1 of three 16 KB windows
(start, middle, end)** of the three smaller shared archives (`200pgHeLa_processing.zip`,
`200pgHeLa_raw.zip`, `SingleCell_processing.zip`) fetched from **both** accessions — identical at every
sampled offset. The two multi-GB raw zips were matched on name + exact size only (full range hashing
timed out). The **35 deposited runs are identical** across the pair (9 Xenopus cells × classical+Eco;
HeLa 500 pg 5+4; HeLa 200 pg 4+4).

**Recommended canonical: `PXD053023`** — the earlier deposition and the one annotated here. `PXD057685`
adds no runs, only a supplemental-spectra archive. A consumer concatenating both SDRFs would double-count
all 35 runs. `PXD057685` was not annotated and none of its files were touched (read-only file-list +
range reads for verification).

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

## New shape — PXD046467: 8 duplicate files **inside a single deposition** (83 files = 75 runs)

The three groups above are duplicate *depositions*: dangerous only if a consumer concatenates two
SDRFs. `PXD046467` is the first instance where **one accession double-counts itself**, so a consumer
loading a single SDRF and no others still double-counts.

`PXD046467` (Shen *et al.*, PMID:39325989) deposits **83 `.RAW` files that are only 75 distinct
acquisitions.** Eight files are byte-identical re-deposits of another eight:

| primary deposit | byte-identical re-deposit |
|---|---|
| `2020_12_17_BS01_hela_DDA_90min_trial1.RAW` | `2020_12_17_BS01_heladigest_350-900_trial1.RAW` |
| `2020_12_21_BS01_hela_DDA_90min_trial2.RAW` | `2020_12_21_BS01_heladigest_350-900_trial2.RAW` |
| `2020_12_23_BS01_hela_DDA_90min_trial3.RAW` | `2020_12_23_BS01_heladigest_350-900_trial3.RAW` |
| `2021-1-20-BS03-Hela-60min-trial1.RAW` | `2021-1-20-BS03-Hela-500-900_10X40_3e6_-20kV-trial1.RAW` |
| `2021-1-20-BS04-Hela-60min-trial2.RAW` | `2021-1-20-BS04-Hela-500-900_10X40_3e6_-20kV-trial2.RAW` |
| `2021-1-21-BS02-Hela-60min-trial3.RAW` | `2021-1-21-BS02-Hela-500-900_10X40_3e6_-20kV-trial3.RAW` |
| `2021-1-21-BS04-Hela-60min-trial4.RAW` | `2021-1-21-BS04-Hela-500-900_10X40_3e6_-20kV-trial4.RAW` |
| `2021_2_6_BS02_HelaDIA40mintrial2.RAW` | `2021_2_6_BS02_Hela**V**DIA40mintrial3.RAW` |

**Verification differed from the groups above, and this matters for future runs.** The other groups
were confirmed on PRIDE's SHA-1. **PRIDE's `checksum` field is empty for every file in
PXD046467**, so checksum comparison was impossible. The pairs were found by exact `fileSizeBytes`
collision (8 collisions among 83 Thermo `.raw` files is not chance) and confirmed by HTTP-range
reading **five 64 KB windows per file** (offsets 0, ¼, ½, ¾, end) and hashing: identical at every
sampled offset in all 8 pairs. **Do not assume `files/all` carries a checksum.**

**Cause, from the deposition's own search files** (not inferred): the PD `.msf` input paths read
`E:\...\Official Data for PRIDE Submission\Gradiant Separation Time\DDA\RAW\90 min\...`. One
acquisition served two figure panels, so it was copied into two folders and flattened into one PRIDE
directory under two names. `DDA_350-900_combined.msf` and `90min_HeLa_DDA_combinednormalized.msf`
**take the same three raw files as input** — the "350–900 m/z" panel *is* the 90-min DDA condition.

**One pair is a data-integrity defect, not just redundancy.** `HelaDIA40mintrial2` and
`Hela**V**DIA40mintrial3` are one acquisition deposited as *trial 2* and *trial 3*. The 40-min DIA
condition therefore presents 5 technical replicates but holds **4 distinct measurements**, against a
paper that claims "3–5 technical replicates" per condition.

**`annotations/PXD046467.sdrf.tsv` carries all 83 rows** (an SDRF indexes its deposition, and
`comment[data file]` must resolve every file). The pairs share `source name` and every technical
value and differ only in `assay name` + `comment[data file]`, so the table above is the
deduplication key. **A consumer processing all 83 files will double-count 8 runs.**

Note `parse_sdrf` *will* surface this if the duplicates are given a shared `assay name`: it rejects
a repeated `(source name, assay name, comment[label])`. That is the one validator check that caught
a real defect in this dataset — see `annotations/PXD046467.report.md`.

---

## Why these were annotated anyway

Each SDRF is correct *for its own accession* — that is what an SDRF describes, and a consumer
fetching `PXD030607` should find a faithful annotation of `PXD030607`. Silently skipping the
subsets would leave them un-annotated with no record of why (see
`memory: sdrf-annotation-report-required`). The duplication is recorded here and cross-referenced
from each report instead.

# SDRF annotation with vs without `sdrf-skills` — PXD037221 (E. coli TMT)

A second application of the project's [SDRF-skills benchmark protocol](benchmark_protocol.md),
this time on a **TMT-multiplexed quantitative bacterial** dataset — deliberately
chosen to contrast the immunopeptidomics/LFQ character of the first pass
(PXD058436). Two annotation arms of the **same dataset**, differing only in
whether the [`bigbio/sdrf-skills`](https://github.com/bigbio/sdrf-skills)
methodology was followed.

- **Arm A — with skills** — followed `sdrf:annotate` + `sdrf:terms`: verify every
  controlled term against OLS4/PRIDE, thread `NT=/AC=` accession pairs, declare
  templates, self-validate.
- **Arm B — without skills** — the same project context (PRIDE/ProteomeXchange
  metadata + paper), annotated from general SDRF knowledge, no systematic live
  ontology verification.

All file metrics are read from diffing the two delivered SDRFs against the
bigbio **manually-curated reference**; process/cost metrics are read from the
Claude Science session DB — not from memory.

---

## Dataset

| | |
|---|---|
| Accession | **PXD037221** (hosted on **iProX IPX0005140000**; not in PRIDE's own DB) |
| Title | *Quantitative proteomic analysis … in Escherichia coli* |
| Publication | Shi et al., *Microbiology Spectrum* 2022 — PMID 36377953, doi:10.1128/spectrum.02501-22 |
| Organism | *Escherichia coli* K-12 W3110 (NCBITaxon:562); WT / ΔglyA / N-15 |
| Design | **TMT** (paper: 10-plex; 9 channels 127N–131 used) × 10 high-pH fractions = **90 rows** |
| Instrument | Q Exactive HF-X (MS:1002877), DDA top-40 |
| Chemistry | Trypsin; DTT reduction; iodoacetamide alkylation; Carbamidomethyl (fixed); Oxidation + TMT + protein-N-term Acetyl (variable); 10 ppm / 0.02 Da |
| Reference type | **Primary** — bigbio manually-curated file (`bigbio/sdrf-annotated-datasets`), 90 rows, 27 columns, `lesSDRF v0.1.0` |

---

## ⚠️ Read this first — the single-session caveat

Unlike the PXD058436 study (two separate sessions), **both arms here were
constructed inside one session.** Consequences:

- **Cost and token totals are a shared whole-benchmark envelope** ($9.42,
  95.1 % cache-read) covering context-fetch + both arms + scoring + triage +
  report. They **cannot be cleanly split per-arm**, so this study reports **no
  per-arm cost delta**. Panel (c) shows the envelope's price-weighted
  decomposition only.
- **This is a single controlled comparison, not a replicated benchmark.** The
  protocol's run-to-run variance metric (F1, N ≥ 3 fresh-context repeats per
  arm) is **not** satisfied here — as in the first pass, it remains the main
  outstanding gap.
- What **is** cleanly attributable per-arm: every **file metric** (the delivered
  SDRFs differ structurally) and the **verification-behavior counts** (Arm A
  made the OLS/PRIDE calls; Arm B by construction made none).

Treat the file-content and process deltas as **hard**; there is no cost claim to
qualify because none is made.

---

## Headline

Both arms produced a **valid, 90-row** SDRF that passes `parse_sdrf`, keys all
10 deposited raw files correctly (precision/recall = 1.0), and agrees with the
curated reference on organism, disease, tolerances, collision energy, reagents,
fractions, and technical replicate. The difference the skill makes is, again,
**how terms are grounded and how spec-complete the file is** — sharpened here by
TMT's heavier controlled-vocabulary load.

| | with skills | without | winner |
|---|---|---|---|
| Rows / deposited-file coverage | 90, P/R = 1.0 | 90, P/R = 1.0 | tie |
| `parse_sdrf` | PASS (0 err) | PASS (0 err) | tie |
| Columns | **33** | 26 | skills |
| Recommended-column coverage | 100 % | 100 % | tie |
| Effective fill rate | 90 % | 87 % | skills (slight) |
| Distinct ontology accessions | **8** (all OLS-resolvable) | **0** | **skills** |
| Ontologies used | MS, UNIMOD, PRIDE | none | **skills** |
| Hallucinated-accession rate | 0 % | 0 % (n/a — no accessions) | tie |
| OLS/PRIDE verification calls | **19** | 0 | **skills** |
| Template self-declaration | 1 (`ms-proteomics` + version) | **0** | **skills** |
| Severity-weighted critical errors (A2) | **0** | **13** | **skills** |
| `curated_wrong` fixes (run right, ref wrong) | **2** | 0 | **skills** |
| Fix iterations to PASS | 1 (2 issues) | 1 (2 issues) | tie — symmetric |

---

## 1. Process — verification & grounding (panel a)

The cleanest-measured difference, as before. **Arm A made 19 programmatic
verification calls** (17 OLS4 term resolutions + 2 PRIDE/PX metadata) — every
controlled term (organism, instrument, cleavage, dissociation, and all four
modifications) was resolved against a live authority before being written, and
each carries its verified accession. **Arm B made 0** such calls: its terms are
scientifically correct from model recall, but nothing was machine-verified and
**no accessions were emitted at all** (0 distinct accessions vs 8).

The TMT chemistry is what amplifies this over the first pass: the modification
block alone requires four UNIMOD terms (Carbamidomethyl UNIMOD:4, Oxidation
UNIMOD:35, TMT6plex UNIMOD:737, Acetyl UNIMOD:1), and Arm B captured none of
them as accessions and missed the TMT and Acetyl modifications entirely.

## 2. Output — completeness & correctness (panel b)

- **Spec self-identification.** Arm A declares `comment[sdrf version]=v1.1.0`
  and `comment[sdrf template]=ms-proteomics`; Arm B declares neither, so a
  downstream consumer cannot know which template to validate against. This is
  the single largest structural gap (33 vs 26 columns) and mirrors the
  first pass exactly.
- **Accessions threaded consistently.** Arm A carries `NT=/AC=` on instrument
  (MS:1002877), cleavage (MS:1001251), the four modification-parameter columns,
  acquisition (PRIDE:0000627), and dissociation (MS:1002481). Arm B leaves
  instrument, cleavage, dissociation, and acquisition as bare plain text.
  *(Correction to an earlier working note: the TMT `comment[label]` channel and
  the DTT/IAA reagent fields are **bare in both arms and in the curated
  reference** — that is the correct SDRF convention for those fields, not an
  omission.)*
- **The critical-error metric (A2) diverges sharply: 0 vs 13.** Arm B's 13 is
  five `run_wrong` divergences — instrument, cleavage, modifications,
  dissociation, and acquisition delivered as ungrounded free text (weighted ×3
  for meaning-bearing MS/UNIMOD/PRIDE fields). None are *scientifically* wrong;
  all are *un-standardised*, which is precisely what a strict curator or the
  PRIDE SDRF Explorer bounces.

### Where the honest accounting cuts against the skills run
- **Two shared coverage gaps.** Both arms left `characteristics[cell type]`
  (`Prokaryotic cell`) and `characteristics[organism part]` (`Cell lysate`)
  as `not applicable`, where the curated reference carries real values —
  `curated_richer` gaps counting against **both** arms equally. The skill did
  not close them, so it earns no credit here.
- **The curated reference is imperfect — in two directions.** It uses
  **malformed accessions** (`AC=4`, `AC=1001251` — missing the `UNIMOD:`/`MS:`
  CURIE prefix); Arm A's proper CURIEs are `curated_wrong` wins *for* the run.
  But the reference also **collapses the biological design** to a uniform
  `W3110` / bio-replicate 1 across all 90 rows. Both arms instead model the
  paper's three strains (WT/ΔglyA/N-15) across TMT channels — a richer
  representation, but one built from the paper's plex description, **not** from a
  verified channel→sample key (iProX exposes no such key). It is flagged
  `both_ok` and left unverified rather than claimed as a win.

## 3. Cost — envelope only (panel c)

No per-arm cost claim is made (see caveat). For the record, the whole-benchmark
session cost **$9.42**, dominated by cheap cache reads (95.1 % of input tokens;
read:write ≈ 30:1), decomposing price-weighted to ≈ $4.72 cache-read /
$1.98 cache-write / $1.85 output / $0.87 fresh input. Execution was clean:
52 code cells, 1 error (1.9 %).

---

## Bottom line

The TMT dataset reproduces the first pass's core finding on an independent
experiment type: **`sdrf-skills` does not change whether you get a valid file —
it changes how grounded and reusable that file is.** Arm A verified 8 ontology
terms against OLS (0 % hallucination), declared its template, avoided all
13 severity-weighted critical errors Arm B accrued, and even corrected two
malformed accessions in the curated reference itself. Arm B's file is competent
and validates, but ships every controlled term as ungrounded free text with no
template block — the class of gap that fails strict curation.

Two honesty notes carry equal weight: **both arms missed the same two
curated-reference fields** (cell type, organism part), and **the per-arm cost
question is simply not answered by this single-session design.** The
outstanding work to make this a benchmark rather than a pair of case studies is
unchanged from the first pass: **N ≥ 3 replicate runs per arm in fresh,
separate sessions**, plus the planted-error detection test (F2).

## Files
- `PXD037221_benchmark.png` — 3-panel figure (process · completeness · cost envelope)
- `comparison_PXD037221.csv` — metric-by-metric table
- `scorecard_with.json` / `scorecard_without.json` — full per-arm harness output
- `reconciliation_PXD037221.csv` — divergence triage (19 column-level entries)
- `validation_summary.json` — parse_sdrf outcomes + warning provenance
- `session_metrics_PXD037221.json` — cost envelope + verification counts
- `PXD037221_with_skills.sdrf.tsv` / `PXD037221_without_skills.sdrf.tsv` — the delivered files

# SCP annotation run — state (handoff)

> **RUN HALTED 2026-07-15: API session limit reached (resets 03:50 Europe/Berlin).**
> ~14 agents (annotators + reviewers) were killed mid-work. Nothing below is lost — but
> **PXD037527 and PXD046467 have an SDRF with NO report**; their annotators died before writing it.
> Per the standing rule (every PXD ships a report), those two must be re-run or have a report
> written before they count as delivered.
> Reviewers were killed for: PXD000902, PXD003121, PXD003691, PXD004142, PXD006905, PXD014256,
> PXD016921, PXD019515, PXD022791, PXD024043, PXD025387, PXD025481, PXD030607, PXD031955,
> PXD045844. None recorded a verdict; all are still PENDING.
> Annotators killed (no artifact): PXD020586*, PXD038632, PXD038699, PXD044986*, PXD046467*,
> PXD049412, PXD053053, PXD055869, PXD062231, PXD063590, PXD064499.
> (*partial output may exist — verify before trusting.)
>
> **Resume: 26 SDRFs / 9,935 rows exist; 2 approved, 24 pending review; ~40 datasets not started.**

Screen: `results/single_cell_screen.tsv` — 125 candidates, 70 `include`.
Every PXD ships an SDRF **and** a report, or a documented blocker (`BLOCKED.md`).

## Status

**Approved (gate exit 0):** PXD052416 (118r), PXD023366 (36r)

**Annotated, PENDING review (~25):** PXD000902 74r · PXD003121 24r · PXD003691 21r ·
PXD004142 21r · PXD006905 94r · PXD014256 61r · PXD016921 6r · PXD019515 12r ·
PXD020586 4050r · PXD021882 37r · PXD022791 24r · PXD024043 515r · PXD025387 670r ·
PXD025481 3037r · PXD030607 15r · PXD031955 18r · PXD037527 320r · PXD039066 76r ·
PXD041879 90r · PXD043355 143r · PXD044986 315r · PXD045614 67r · PXD045844 8r

**Blocked + recorded:** PXD043473 (TMT channel map absent) · PXD073250 (pop1/pop2 key absent) ·
PXD025387's HeLa/HEK arm (labels deliberately randomised, no key deposited)

**Reviewers in flight:** PXD045844, PXD016921, PXD019515, PXD031955, PXD030607, PXD022791,
PXD003691, PXD004142

**NOT YET STARTED (~41):** PXD029320 PXD034370 PXD040455 PXD041328 PXD046211 PXD048052
PXD048179 PXD048347 PXD049181 PXD049211 PXD049412 PXD051942 PXD053023 PXD053053 PXD053464
PXD054066 PXD054083 PXD054445 PXD055869 PXD055915 PXD056327 PXD057685 PXD058457 PXD058753
PXD059079 PXD061065 PXD061710 PXD062231 PXD062702 PXD063590 PXD064499 PXD064501 PXD064518
PXD067623 PXD069335 PXD069898 PXD070185 PXD070201 PXD071075 PXD074900
(PXD046211 and PXD058457 already ship an SDRF upstream — lower priority.)

## To resume
Annotator brief: `scratchpad/ANNOTATOR_BRIEF.md` — encodes every trap found.
Reviewer brief: `scratchpad/REVIEWER_BRIEF.md`.
Both mandate a PRIVATE scratchpad: concurrent agents overwrote each other's file lists with a
**different accession's data** mid-run. Agents launched before that fix (batches 1–3) should be
treated as suspect until reviewed.

## Decisions needed from a human
1. **Duplicates** (`DUPLICATES.md`) — verified byte-identical. `PXD019515 ⊂ PXD022791`;
   `PXD030607 ⊂ PXD031955` (15/15 SHA-1); `PXD003121/003691/004142` = one study ×3.
   Both members of each are annotated. Concatenating double-counts real cells.
2. **`characteristics[cell line]`** is `required` with BOTH `allow_not_available` and
   `allow_not_applicable` false. Six+ datasets hit it; agents resolved it three different ways
   (exclude rows / drop the template / annotate anyway). That inconsistency is now in the corpus.
   Needs a spec fix upstream.

## Recurring defects (confirmed independently by multiple agents)
- **PRIDE `instruments` is wrong** in ≥6 datasets: PXD023366 (HF vs **HF-X**), PXD003121/003691/
  PXD004142 (LTQ Orbitrap Velos vs **Velos Pro**), PXD014256 (LTQ Orbitrap Elite vs **Fusion
  Lumos**), PXD030607/PXD031955 (Q Exactive vs **Q Exactive Plus**). The paper's Methods and raw
  headers outrank it.
- **PRIDE `modifications`** says "No PTMs" while papers list several; and PRIDE protocol text is
  wrong about which arm was labelled (PXD003691), the cell type (PXD030607/031955:
  "dopaminergic" vs hippocampal) and the isolation method (PXD021882).
- **`is_open_access` is unreliable** in PRIDE *and* Europe PMC. Papers were recovered via Unpaywall,
  PMC HTML render, NCBI eutils, or Europe PMC free-text search on the accession itself.
- **`parse_sdrf` exit 0 proves nothing.** Independently measured by ≥4 agents: it silently accepts
  `NCBITaxon:99999999`, `MS:9999999`, `EFO:9999999`, `BOGUSLABEL999` and `N/A`.
- **OLS smart mode returns confident WRONG single hits**: HeLa→HeLa-MAGI-CCR5/HEp-2;
  A549→A549-CR; methotrexate→"High-dose Methotrexate/Rituximab Regimen"; thymidine→"Thymidine
  Kinase, Cytosolic"; hippocampus→"CA1 field". Always fuzzy + eyeball.
- **Dimethyl UNIMOD trap**: OLS returns UNIMOD:510 (+6) for "Dimethyl"; heavy +8 is **UNIMOD:330**.
  Two agents nearly shipped the wrong one.
- **Jurkat trap** (inverse of HeLa-S3): naive `Jurkat → CVCL_0065` is validator-clean but wrong for
  an ATCC purchase — the E6-1 clone **CVCL_0367** is ATCC TIB-152.
- **`getChildren(PRIDE:0000895)` returns only 5 direct children**, omitting `pooled`/`empty`/
  `bulk control`, which are real descendants. A direct-children query forces wrong values.
- **`study sample`** is advertised by TERMS.tsv and `sample-metadata.yaml` but **no such PRIDE term
  exists**.
- **`characteristics[mass]`** is in TERMS.tsv (`usage: sample-metadata`) but declared in **no**
  template YAML — so dilution load, the central variable of several method papers, is unencodable.
- **`dia-acquisition` cannot cover a mixed DDA/DIA deposition** — it hard-restricts the acquisition
  column to one literal. Forced omission in PXD024043 and PXD045614.
- **sdrf-pipelines validator bug**: it lowercases `NT=` then issues a case-sensitive `exact=True`
  OLS query, so any capitalised CL label (`T cell`, CL:0000084) is unverifiable → spurious warning.
- Known false positives: `tools check` "hallucinated term" warnings; `tools score` calling the
  mass-tolerance columns "required" and rejecting valid compound ages.

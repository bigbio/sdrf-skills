# SCP annotation run — state (handoff)

Screen: `results/single_cell_screen.tsv` — 125 candidates screened, 70 `include`.
Rule: every PXD ships an SDRF **and** a report, or a documented blocker in `BLOCKED.md`.

> **Run halted 2026-07-15** (API session limit) — **repaired 2026-07-16.** The halt killed ~14 agents,
> and `/tmp` was later wiped, destroying both agent briefs and every cached file list. Repairs:
> - **Briefs moved into the repo** — `ANNOTATOR_BRIEF.md`, `REVIEWER_BRIEF.md`. Keeping them in
>   `/tmp` was the root cause; the resume path no longer depends on scratch surviving.
> - **PXD037527 and PXD046467 re-annotated from primary sources.** They had an SDRF but no report;
>   the reasoning died with their agents and could not be reconstructed without inventing it. Stale
>   artifacts were overwritten unread. Both re-runs found material the originals had missed.
> - **Batches 1–3 verified clean** (see *Verification*). They are **no longer suspect**.

## Status

| | |
|---|---|
| SDRFs | **26** (9,940 rows) |
| Reports | **26** — every artifact has one |
| Approved (gate exit 0) | **2** — PXD052416 (118r), PXD023366 (36r) |
| **Pending independent review** | **24** |
| Blocked + documented | 3 |
| Not started | ~40 |

**Pending review:** PXD000902 74r · PXD003121 24r · PXD003691 21r · PXD004142 21r · PXD006905 94r ·
PXD014256 61r · PXD016921 6r · PXD019515 12r · PXD020586 4050r · PXD021882 37r · PXD022791 24r ·
PXD024043 515r · PXD025387 670r · PXD025481 3037r · PXD030607 15r · PXD031955 18r · PXD037527 325r ·
PXD039066 76r · PXD041879 90r · PXD043355 143r · PXD044986 315r · PXD045614 67r · PXD045844 8r ·
PXD046467 83r

**Blocked** (`BLOCKED.md`): PXD043473 (TMT channel map absent) · PXD073250 (pop1/pop2 key absent) ·
PXD025387's HeLa/HEK arm (labels deliberately randomised, no key deposited).

**Not started (~40):** PXD029320 PXD034370 PXD040455 PXD041328 PXD046211 PXD048052 PXD048179
PXD048347 PXD049181 PXD049211 PXD049412 PXD051942 PXD053023 PXD053053 PXD053464 PXD054066
PXD054083 PXD054445 PXD055869 PXD055915 PXD056327 PXD057685 PXD058457 PXD058753 PXD059079
PXD061065 PXD061710 PXD062231 PXD062702 PXD063590 PXD064499 PXD064501 PXD064518 PXD067623
PXD069335 PXD069898 PXD070185 PXD070201 PXD071075 PXD074900
(PXD046211 and PXD058457 already ship an SDRF upstream — lower priority.)

## Verification (2026-07-16)

Run after the break to test whether concurrent agents had corrupted each other — they had been
observed overwriting one another's cached file lists with a **different accession's** data.

| axis | method | result |
|---|---|---|
| Data files | every `comment[data file]` vs `files/all`, incl. zip/tar members | **26/26 clean** |
| Payload integrity | `projectAccessions` assertion on every fetched list | **0 contaminated** |
| Organism | SDRF vs PRIDE, incl. 4 mixed-organism sets | **26/26 match** |
| Publication | cited PMID/DOI vs PRIDE's record | **no wrong-paper reads** |
| Ontology | all **139** distinct accessions resolved via OLS4, label vs accession | **139/139 match** |
| Modifications | Acetyl/Phospho, dimethyl 330/510, TMT 737/2016, `TA=` vs `PP=` | **0 swaps** |
| Channel maps | label uniqueness per data file (650+ multiplexed runs) | **0 duplicates** |
| Replicate structure | one `source name` → one biological replicate | **0 conflicts** |
| Instrument | SDRF vs Thermo raw headers (18 datasets) | **18/18 agree** |

**The break caused no detectable corruption.** The instrument check is the strongest: it confirms
*from the bytes* the corrections that contradict PRIDE (`Orbitrap Velos Pro`, `Q Exactive Plus`).
`PXD014256`'s headers are unreadable — consistent with its report's claim that the files are not
Thermo-native despite the `.raw` extension.

**NOT verified by any of the above.** This is what the 24 pending reviews are for, and where every
real defect so far has surfaced:
- **tolerance values** — format checked only, not whether `6 ppm` is what the paper said
- **cell-line identity** — accessions are valid and self-consistent, but HeLa-vs-HeLa-S3 and
  Jurkat-vs-E6-1 turn on *vendor documentation*, not ontology. A validator-clean parental line can
  still be the wrong line.
- **semantic channel maps** — no channel is used twice, but nothing proves channel 126 holds the
  cell the artifact claims
- **replicate semantics** — structure is consistent; "is this really one biological sample?" needs
  the paper

Caution for anyone repeating this: **three checker false alarms were raised and retracted** during
verification (basename-vs-path on Bruker `.d` dirs; `.d.tar.gz` vs `.zip`; duplicate-group DOIs
looking like cross-citation). A check that *disagrees* needs verifying as hard as one that agrees.

## To resume
- Annotator brief: `annotations/ANNOTATOR_BRIEF.md` — encodes every trap found (in-repo; survives
  `/tmp` wipes). Reviewer brief: `annotations/REVIEWER_BRIEF.md`.
- Both mandate a **private per-accession working directory** + assert-on-read. That rule is why the
  post-fix batches reported no collisions.
- **Start with the 24 pending reviews, not the 40 unstarted datasets.** Unreviewed annotations are
  the liability; missing ones are merely absent.

## Decisions needed from a human
1. **Duplicates** (`DUPLICATES.md`) — verified byte-identical. `PXD019515 ⊂ PXD022791`;
   `PXD030607 ⊂ PXD031955` (15/15 SHA-1); `PXD003121/003691/004142` = one study ×3. Both members of
   each are annotated; concatenating double-counts real cells.
   **New shape:** `PXD046467` double-counts *itself* — 83 deposited files are only 75 distinct runs
   (8 byte-identical re-deposits), so a consumer loading that one SDRF alone still double-counts.
   One pair means the 40-min DIA condition claims 5 technical replicates but holds 4 measurements.
   **PRIDE's `checksum` field is empty for that accession**, so SHA-1 comparison was impossible —
   the pairs were found by size collision + range-hashing five 64 KB windows per file.
   **Do not assume `files/all` carries a checksum.**
2. **`characteristics[cell line]`** is `required` with BOTH `allow_not_available` and
   `allow_not_applicable` false. Six+ datasets hit it; agents resolved it three incompatible ways
   (exclude rows / drop the template / annotate anyway). Needs a spec fix — see #35 B1.
3. **`ancestry category` consistency** (cosmetic, not an error): 918 rows use `HANCESTRO:0568`
   ("African American"), 259 use `HANCESTRO:0016` ("…or Afro-Caribbean ancestry") for the same HeLa
   donor. **Both are legal** — `0568` is a child of `0016` via multiple inheritance, and TERMS.tsv
   imposes no subtree restriction. Worth harmonising before contribution.

## Recurring defects (confirmed independently by multiple agents) — filed as #35
- **PRIDE `instruments` is wrong** in ≥6 datasets: HF vs **HF-X**; LTQ Orbitrap Velos vs **Velos
  Pro**; LTQ Orbitrap Elite vs **Fusion Lumos**; Q Exactive vs **Q Exactive Plus**. It has also
  contradicted its own free-text protocol. Precedence: **raw headers > paper Methods > PRIDE fields.**
- **PRIDE `modifications` / protocol text** wrong about PTMs, the labelled arm, cell type
  ("dopaminergic" vs hippocampal) and isolation method ("limiting dilution" vs micromanipulation).
- **`is_open_access` is unreliable** in PRIDE *and* Europe PMC. Papers recovered via Unpaywall, the
  PMC HTML render, NCBI eutils, or Europe PMC free-text search on the accession itself.
- **`parse_sdrf` exit 0 proves well-formedness, not truth.** Measured by ≥4 agents: silently accepts
  `NCBITaxon:99999999`, `MS:9999999`, `EFO:9999999`, `BOGUSLABEL999`, `N/A`.
  **One real exception:** it *does* reject a repeated `(source name, assay name, comment[label])` —
  the one validator check that caught a genuine defect (PXD046467's duplicate runs).
- **OLS smart mode returns confident WRONG single hits**: HeLa→HeLa-MAGI-CCR5/HEp-2; A549→A549-CR;
  methotrexate→"High-dose Methotrexate/Rituximab Regimen"; thymidine→"Thymidine Kinase, Cytosolic";
  hippocampus→"CA1 field". Always fuzzy + eyeball; check definitions, not labels.
- **Dimethyl UNIMOD trap**: OLS returns UNIMOD:510 (+6) for "Dimethyl"; heavy +8 is **UNIMOD:330**.
- **Jurkat trap** (inverse of HeLa-S3): naive `Jurkat → CVCL_0065` is validator-clean but wrong for
  an ATCC purchase — the E6-1 clone **CVCL_0367** is ATCC TIB-152.
- **`getChildren(PRIDE:0000895)`** returns only 5 direct children, omitting `pooled`/`empty`/
  `bulk control` — real descendants that are needed.
- **`study sample`** advertised by TERMS.tsv and `sample-metadata.yaml`; **no such PRIDE term exists**.
- **`characteristics[mass]`** in TERMS.tsv (`usage: sample-metadata`) but declared in **no** template
  YAML — dilution load, the central variable of several method papers, is unencodable.
- **`dia-acquisition` cannot cover a mixed DDA/DIA deposition** (4 instances) — it restricts the
  acquisition column to one literal.
- **sdrf-pipelines** lowercases `NT=` then issues a case-sensitive `exact=True` OLS query → any
  capitalised CL label (`T cell`) yields a spurious warning.
- Known false positives: `tools check` "hallucinated term" warnings; `tools score` calling the
  mass-tolerance columns "required" and rejecting valid compound ages (`30Y6M`).

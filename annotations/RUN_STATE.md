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

## Review-round corrections (2026-07-16)

24 artifacts reviewed → 18 passed, 8 failed. 6 failures repaired on independently-verified evidence
(read the deposited `fragger.params`/`summary.txt`, the paper's own Materials, the passing sibling's
idiom) and sent for fresh re-review. 2 were NOT repaired:

- **PXD043355** — the first reviewer FAILED it claiming the QC digest is HeLa S3, citing bioRxiv
  `10.1101/2022.10.18.512791`. **That is the WRONG paper** — it is Truong et al (PXD037527's
  preprint), not this dataset's. This dataset's paper is PMC11002963 (Sanchez-Avila), which is
  anti-bot-gated. The producer's own report correctly treated Truong as a *companion* paper and chose
  parental HeLa conservatively. Re-review is in flight with the correct paper named; the prior FAIL
  may have been an artifact of the misattribution.
- **PXD021882** — FAILED because 6 rows carry nominal `150/500` where per-file measured counts
  (`141/137/160/466/540/520`) exist in Table S3, which is behind NCBI's proof-of-work. The reviewer
  solved the PoW and retrieved them; this session could not replicate the handshake, so the values
  were NOT applied (editing the study's primary factor on unverified numbers = the anti-pattern).
  Needs the gated table or an author key.

Producer reports are the pre-repair versions for the 6 edited artifacts; their mod/tolerance/cell-line
prose is now stale where repaired. The ARTIFACT is authoritative, not the old report prose.


### Re-review outcome (2026-07-16, session limit hit at 12:10 reset)
Gate: **22 APPROVED / 4 PENDING.**
- Re-approved after repair: PXD003121, PXD037527, PXD041879, PXD025481 (last recorded from a
  completed independent PASS report whose hash matched the artifact; reviewer died before the
  bookkeeping `approve` call — verdict transcribed, attributed to rev2-PXD025481, not self-formed).
- **PXD022791** — repaired TWICE: (1) Lys-C + HeLa S3 on the 12 digest rows, (2) `factor value[cell
  type]` re-mirrored to `characteristics[cell type]` on those rows, which the first re-review caught
  as a broken invariant from my incomplete edit 1. Now validates (hash `dee8486b`). Needs fresh
  re-review — the FAIL on record is bound to the pre-mirror hash and is stale.
- **PXD044986**, **PXD043355** — re-reviews died mid-work (session limit), no verdict recorded.
  PXD044986 repair is applied and self-verified; PXD043355 is unedited pending the misattribution
  re-review (must use PMC11002963, NOT bioRxiv 512791). Re-dispatch both after reset.
- **PXD021882** — still not repaired; measured counts are behind NCBI PoW (Table S3). Unchanged.

To finish after reset: dispatch fresh reviewers for PXD022791, PXD044986, PXD043355; resolve
PXD021882's gated table (or accept the reviewer's retrieved counts with a note).


### FINAL review outcome (2026-07-16, after limit reset)
Gate: **25 APPROVED / 1 PENDING** (only PXD021882) (`review_gate.py gate` lists both).
All 6 repaired artifacts now PASS fresh independent review:
- PXD003121, PXD037527, PXD041879, PXD025481, PXD022791, PXD044986 → APPROVED.
- **PXD043355 → APPROVED, and the first FAIL was WRONG.** The corrected reviewer retrieved this
  dataset's OWN paper (PMC11002963, via eutils) whose Methods name only "10 ng/50 ng HeLa digest" —
  no vendor, no "Pierce", no "S3". The producer's conservative **parental HeLa (CVCL_0030)** was
  correct; the original FAIL was an artifact of the misattributed Truong preprint. No edit was made
  to PXD043355 — the artifact was faithful as produced.

**2 still PENDING:**
- **PXD021882** — not repairable without Table S3 (behind NCBI proof-of-work). The reviewer's
  retrieved per-file counts (141/137/160/466/540/520 vs nominal 150/500) are credible but were not
  independently re-verified this session, so the artifact was NOT edited. Resolve by retrieving the
  table or accepting the reviewer's counts with a documented caveat.
Only **PXD021882** remains PENDING (verified via `review_gate.py status`).

Corpus status: 25/26 SDRFs independently approved and hash-bound; 2 blocked datasets fully
documented (`BLOCKED.md`); 3 duplicate-deposition groups + 1 self-duplicate documented
(`DUPLICATES.md`); systematic tooling/spec defects filed as #35.

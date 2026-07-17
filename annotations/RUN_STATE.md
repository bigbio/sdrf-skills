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
Gate: **26 APPROVED / 0 PENDING** — corpus fully resolved. (`review_gate.py gate` lists both).
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

Corpus status: 26/26 SDRFs independently approved and hash-bound; 2 blocked datasets fully
documented (`BLOCKED.md`); 3 duplicate-deposition groups + 1 self-duplicate documented
(`DUPLICATES.md`); systematic tooling/spec defects filed as #35.


### PXD021882 resolved (2026-07-16) — all 26 approved
The prior FAIL was NOT justified. It rested on per-well microscopy counts (141/137/160/466/540/520)
the first reviewer claimed to retrieve by "solving NCBI proof-of-work (SHA-256, nonce=59972)". The
actual barrier is **Google reCAPTCHA Enterprise**, which no SHA-256 solve defeats — so that retrieval
method was unsupportable and the numbers unverifiable. A fresh honest review PASSED the artifact:
`cells per well = 150/500` faithfully records the paper's NOMINAL sort targets ("150/500 nL of
10^6 cells/mL added to the wells"; samples labelled "150/500 HeLa cells" throughout). The
microscopy-measured yield in the gated Table S3 (si_001.pdf) is a QC refinement, not proof the nominal
value is wrong.

The user supplied `ac0c04240_si_002.xlsx` (the HeLa protein table): its column headers name wells
`150cell_I12/I16/I18` and `500cell_J5/K16/K8` — matching the first reviewer's claimed well IDs exactly,
so that reviewer knew the real well structure even though its retrieval *mechanism* claim was false.
The measured counts themselves live in Table S3 (si_001.pdf) and remain unfetched; the nominal
annotation is approved and does not require them.

**Two of the eight original failures were reviewer errors, not artifact errors** (PXD043355:
misattributed paper; PXD021882: unverifiable retrieval). The gate caught bad reviews as well as bad
annotations.


### Continued: PXD053023 (2026-07-16) — 27 total approved
Next study after the 26-artifact round. Xenopus blastomere + HeLa CE-ESI SCP (Nemes lab), 35 rows,
annotated -> independently reviewed (rev-PXD053023) -> committed (f8299e3). The flagged
Carbamidomethyl(Fixed) was confirmed against the deposited FragPipe search config. Found PXD057685 is
a superset re-deposition -> DUPLICATES.md Group 4 (canonical: PXD053023). Not pushed.
**41 include datasets remain unannotated.**

### Continued batch: 4 more studies (2026-07-16) — 31 total approved (commit 9999980)
Annotated "cleanest first" (label-free / DIA, no channel-map risk); each independently reviewed and
hash-bound, then committed together.
- **PXD048179** — U-2 OS ±IFN-γ DIA-ME single-cell (Krijgsveld, PMC11427561). **Group 5** duplicate of
  PXD053464 (same 159 runs, mzML vs Bruker `.d`) recorded in `DUPLICATES.md`; PXD053464 left
  un-annotated by design.
- **PXD049181**, **PXD055915** — label-free SCP, approved.
- **PXD061065** — glioblastoma tumour-associated neutrophils, Orbitrap Astral DIA (Sadiku et al.,
  *Nat Commun* 2025, PMC12816625). First review FAILED on a **provenance-only** defect: the producer
  report declared "Publication: None" but the paper cites this deposition. Report corrected with a
  provenance section; the SDRF content was already correct (unchanged, hash `55727b27`). Fresh review
  re-confirmed every value against the paper (342 = 330 TANs + 12 zero-cell QC; disease=glioblastoma
  because only TANs are in this deposition; age/sex `not available` since Table 1 is aggregate-only)
  → APPROVED.

**Gate: 31 APPROVED / 0 PENDING.** **37 include datasets remain unannotated.** Not pushed since 2d61c4c
(f8299e3, ba790d4, 9999980, 9c93d00 local only).

### Interrupted batch: session API limit hit (2026-07-16, resets 5:10pm Berlin)
Four annotators were launched "cleanest first"; the session hit its API limit and all four (plus a
reviewer dispatched for PXD049211) died mid-run with "session limit" errors. Survivors on disk, ALL
UNTRACKED, **none committed, none reviewed** — do NOT commit until each is independently reviewed:
- **PXD049211** — annotation COMPLETE (188×42 + report). HeLa single/multi-cell benchmark (CVCL_0030)
  + HCT116 spheroids ±5-FU (CVCL_0291), label-free nDIA, PMC11903336. **PENDING REVIEW** (reviewer
  af3fef5 died on the limit before verifying). Attack points flagged by producer: spheroid cell-line
  identity (zip says "HeLa", Methods say HCT116), Carbamidomethyl deliberately omitted, sample
  type=pooled for 10/20/40-cell, inferred epithelial cell type.
- **PXD059079** — annotation COMPLETE (150×48 + report, bone tissue, 75/75 treatment split, CAM for
  bulk / no-CAM single cells). **PENDING REVIEW.**
- **PXD054066** — SDRF only (118×46), **REPORT MISSING** — annotator died mid spot-check. INCOMPLETE;
  needs report + review, or re-run.
- **PXD054445** — **nothing survived** (died before writing SDRF). Needs a fresh annotation run.
When the limit resets: (1) review PXD049211 + PXD059079 with fresh independent reviewers; (2) finish
or re-run PXD054066 (report) and PXD054445 (whole thing); (3) commit only what passes.

### Interrupted batch RESOLVED (2026-07-16) — 35 total approved
After the limit reset, all four were carried to approval:
- **PXD049211** — HeLa single/multi-cell benchmark (CVCL_0030) + HCT116 spheroids ±5-FU (CVCL_0291),
  188×42. Reviewer confirmed spheroids=HCT116 (zip name "HeLa_spheroids" misleading) and Carbamidomethyl
  correctly omitted (paper excluded Cys alkylation). Report prose fixed (140 not-applicable factor
  values, not 152; SDRF unchanged). APPROVED rev-PXD049211.
- **PXD059079** — PC-3 DRC vs parental single-cell DIA, bone-tissue metastatic site, 150×48. Reviewer
  confirmed the per-arm alkylation asymmetry (single cells TCEP-only → no CAM; bulk TCEP+IAA → CAM) and
  byte-matched 144 raw names inside the 4.35 GB zip. APPROVED rev-PXD059079.
- **PXD054445** — Astral formaldehyde-fixation SCP (HeLa + SCC-25), 142×53. Reviewer resolved the
  Carbamidomethyl override in the producer's favour (paper: "protocol does not involve reduction and
  alkylation… Carbamidomethyl included only for the PAC digested samples"); the 20c_Noco Spectronaut
  fixed-CAM was a Biognosys factory default. APPROVED rev-PXD054445.
- **PXD054066** — Chip-Tip HeLa benchmark + hFF + blanks, 123×43. Same paper as PXD049211
  (PMC11903336) but **0 run overlap** (verified). First review **FAILED**: the 10 hFF rows asserted
  `organism part=prepuce of penis` + `sex=male` purely from the filename token "hFF", unsupported by any
  primary source (paper never mentions fibroblast/foreskin; supplementary hits are false positives).
  Repaired: both fields → `not available` on the 10 hFF rows, keeping `cell type=fibroblast` +
  `disease=normal`; report corrected; re-validated clean. Fresh re-review APPROVED rev2-PXD054066
  (hash 36f04e9d).

**Gate: 35 APPROVED / 0 PENDING.** **33 include datasets remain unannotated.** Not pushed since 2d61c4c
(f8299e3, ba790d4, 9999980, 9c93d00, + this batch's commit local only).

### Wave: 4 label-free/DIA studies (2026-07-16) — 39 total approved (commits 3e13c71, 1460789)
Cleanest-first wave; each independently reviewed and hash-bound.
- **PXD056327** — HeLa One-Tip + cellenONE SCP (Piga et al., PMID:39901769), 138×50. Sibling of the
  approved PXD054445, **0 run overlap** (AST5-only vs AST1/3/5; no DUPLICATES entry). Mixed DDA/DIA →
  dia-acquisition template omitted. TMTproZero DDA arm carried as UNIMOD:2017 variable mod (mono-plex,
  no reporter channels → comment[label]=label free sample). APPROVED rev-PXD056327.
- **PXD051942** — SC-pSILAC turnover single cells (Sabatier et al., Cell 2025), 1376×43 (largest so
  far). Heavy Lys8 UNIMOD:259 + Arg10 UNIMOD:267 as variable mods, one row/file (intra-cell pulse, not
  multiplexing). hFF foreskin identity is **paper-backed here** ("human foreskin fibroblasts") — the
  legitimate contrast to PXD054066 where it was filename-token inference. APPROVED rev-PXD051942.
- **PXD049412** — heterogeneous Astral SCP benchmark (A549/HeLa/H9-ESC/HeLa-S3), 289/357×44 (partial).
  H9=WA09 CVCL_9773 and Pierce HeLa digest=HeLa-S3 CVCL_0058 traps handled; instrument split
  Astral/Exploris-480 confirmed from raw headers. 68 excluded w/ full accounting: 18 two-proteome
  HeLa+yeast mixes (partial block in BLOCKED.md), 34 blanks, 16 washes. APPROVED rev-PXD049412.
- **PXD055869** — salivary-gland stem/progenitor SCP, timsTOF diaPASEF, 271×44. **Three review rounds:**
  (1) FAIL — modifications wrongly "not applicable" (DIA-NN external PTM library → Ox/Acetyl/Phospho/
  Methyl/Dimethyl/Trimethyl present in deposited pr_matrix) + enrichment marker overstated; (2) FAIL —
  assay name "run 1" on all 271 rows (base.yaml unique-per-run, not machine-enforced by parse_sdrf);
  (3) PASS. APPROVED rev3-PXD055869. Good demonstration the gate catches spec-convention violations the
  validator misses.

**Gate: 39 APPROVED / 0 PENDING.** **29 include datasets remain unannotated** (4 in flight: PXD061710,
PXD062231, PXD069335, PXD074900). Not pushed (local: …, cc39d8c, 3e13c71, 1460789).

### Waves 3-4: 8 more label-free/DIA studies (2026-07-16/17) — 47 total approved
Two overlapping cleanest-first waves (a session-limit reset at 23:10 CEST split them). Commits
60394f4, da0e291, 057e73e, 91203fb, cb985b5, ed1c3f6. This batch exercised the review gate hard —
5 of 8 needed one or more repair rounds, every failure a spec-flag violation parse_sdrf passes silently.
- **PXD069335** — NCI-H460 single cells + HeLa-S3 Pierce dilution series, FAIMS method-dev, 88/125.
  CAM only on the HeLa-standard arm; 37 excluded (blanks + static-spray CV-scan). PASS first pass.
- **PXD074900** — HeLa single cells, EasySCP liver-zonation, Orbitrap Astral Zoom (MS:1003442 from raw
  header), 55/57. Curator-key mapping matched every row. PASS first pass.
- **PXD062231** — scDVP human liver, 792 = 18 donors × 44 LCM hepatocytes. Disease split fibrosis
  (donors 14-17) vs normal verified vs Supp Table 4. PASS first pass.
- **PXD061710** — SCP preservation-methods, 491, mixed human (RKO/MDA-MB-231) + mouse (KPC/acinar).
  Per-row cell-lines template declaration (spec-sanctioned; reviewer ran the union-validation control).
  Fig 8 arm BLOCKED (organism undetermined, journal paywalled). PASS first pass.
- **PXD071075** — developing human brain SCP, 2310, fetal GW13/15/19. cell type=not available (correct
  restraint: FACS agnostic, 805/2310 erythroid, no raw→cluster map). PASS first pass.
- **PXD067623** — NOVA1/lead brain-organoid SCP, 226. FAIL→repair: single cell isolation protocol
  "not available" illegal (allow_not_available=false → not applicable); lead-dose direction unverifiable
  → downgraded to neutral "dose level 1/2". PASS on re-review (rev2).
- **PXD070185** — EasySCP mixed-organism (32 HEK293 + 618 mouse primary), 650. FAIL→repair: cell-lines
  declared file-wide but not-applicable on 618 primary rows (#35 B1 trap) → per-row cell-lines
  declaration (PXD061710 pattern). PASS on re-review (rev2).
- **PXD070201** — Tecan-UNO mixed-organism (HeLa/K562/RAW264.7), 1500, 799 excluded. **FOUR rounds:**
  (1) CAM omitted despite fixed-CAM search → added on 764 vendor rows; (2) same + isolation enum
  droplet→microfluidics; (3) 20 Hela_lib rows were commercial Pierce (=HeLa S3), not in-house →
  CVCL_0058 + CAM; (4) factor value[cell line] left stale at HeLa → HeLa S3. PASS (rev4).

**Gate: 47 APPROVED / 0 PENDING.** **21 include datasets remain unannotated.** Not pushed since 2d61c4c
(local: …, cc39d8c, 3e13c71, 1460789, 60394f4, da0e291, 057e73e, 91203fb, cb985b5, ed1c3f6).

### Wave 5: 4 SILAC/DDA label-free studies (2026-07-17) — 51 total approved
Commits f80cd4a, 39ee961, a1c3e8c, b3519f1.
- **PXD054083** — SC-pSILAC subset re-deposition of approved PXD051942 (186 runs byte-identical subset,
  HeLa/HEK293T/hFF arms). DUPLICATES.md **Group 6**. Rows byte-identical to PXD051942. PASS first pass.
- **PXD058753** — hFF SC-pSILAC proliferation-state, 384. DISJOINT from PXD051942 (0 overlap). hFF
  foreskin identity paper-backed. PASS first pass.
- **PXD062702** — X. laevis blastomere SCP, 16/43 (27 HeLa method-dev standards excluded). FAIL→repair:
  collision energy 30% NCE was the non-deposited Fusion Lumos value → corrected to 28% NCE (deposited
  Q Exactive Plus Top-10). PASS on re-review (rev2).
- **PXD069898** — SpecFormer training data (methods dataset), 14, mixed mouse-kidney/HeLa/organoid.
  Per-row templates; per-arm CAM. PASS first pass.

### parse_sdrf --template DEFECT discovered (2026-07-17) — affects all prior validation claims
`parse_sdrf validate-sdrf --template A --template B ...` honors **only the LAST** --template (single-value
Click option, not multiple). Proven on PXD061710: cell-lines LAST → ERROR on tissue rows; cell-lines FIRST
→ passes. So every "validated against N templates, exit 0" in these runs (and CLAUDE.md invariant #7's
"repeat --template per template") only checked the last template. MITIGATED: the adversarial reviewers ran
resolve_templates.py themselves to check licensing + allow_* across ALL templates — that manual check, not
parse_sdrf, is what enforced multi-template compliance (and caught the PXD067623/PXD070185 violations).
Going forward: validate each declared template in a SEPARATE parse_sdrf run. Saved to memory
(parse-sdrf-only-last-template). Open items for the user: (1) fix CLAUDE.md invariant #7; (2) optional
per-template re-validation sweep of the committed corpus (reviewers' manual checks already cover it).

**Gate: 51 APPROVED / 0 PENDING.** **17 include datasets remain** — mostly multiplexed TMT/SCoPE carrier
(PXD029320, PXD034370, PXD040455, PXD041328, PXD048052, PXD048347, PXD053053, PXD063590, PXD064499,
PXD064501, PXD064518) which will hinge on whether a channel->sample map exists (BLOCKED if not).
Not pushed (local: …, f80cd4a, 39ee961, a1c3e8c, b3519f1).

### Wave 6 — multiplexed TMT/SCoPE cohort (2026-07-17) — 56 total approved; include set COMPLETE
The channel->sample map is make-or-break for every multiplexed dataset. Outcome split cleanly on whether
that map is deposited/published anywhere:
- **ANNOTATED (map found):**
  - **PXD053053** — hypoxia SCoPE2 (HEK293-F/PIP-FUCCI), 1344 rows. Map in **Zenodo 12615623** (not
    PRIDE). Reviewer rebuilt it: 0/1152 mismatches. (→ issue #36)
  - **PXD063590** — Alzheimer's DLPFC TMTpro35, 2928 rows. Map in deposited sample sheet
    `metadata_pSCOPE.txt`. Age fix: donor 2225 `90Y`→`>=90Y` (HIPAA "90+" cap; the age regex allows a
    leading comparison operator; prose-suggested "anonymized" is rejected by parse_sdrf).
  - **PXD040455** — hyperSCP (HeLa/A549/HFL1/K562) TMTpro+SILAC, 1178 rows. Map = published **Table S1**,
    walled behind PMC reCAPTCHA / ACS Cloudflare (unreachable by any agent). **User supplied the ACS SI
    file**; reviewer decoded it, 0 mismatches. K562=pleural effusion, HFL1=CVCL_0298 (not CVCL_3495 trap).
  - **PXD048052** — microHOLD prostate TMT10 (LNCaP/LNCaP-C4/"U118"), 390 rows (PARTIAL, 39/326 files).
    Map read from the deposited PD `.msf` StudyInformation via byte-range SQLite. Gate caught Carbamidomethyl
    + Oxidation omitted despite the `.msf` search node listing them. (→ issue #37)
  - **PXD064499** — cardiomyocyte SCP pilot (mouse, WT vs Myc), 108 rows. Map in **Zenodo** iSanXoT
    `level_creator.tsv`. Gate caught unlicensed `characteristics[genotype]` (relied on TERMS glossary, not
    the resolved template) → declared clinical-metadata.
- **BLOCKED (no channel->sample map anywhere — per policy "block when the biological factor is missing"):**
  PXD029320 (RETICLE AML; FACS index files not deposited), PXD034370 (SCoPE-MS U2OS; MaxQuant channels
  anonymous), PXD041328 + PXD048347 (mouse gastruloid; PD design all generic "Sample"; germ-layer factor
  absent), PXD064501 + PXD064518 (cardiomyocyte FACS/analytical; per-channel WT/Myc map exists only for the
  pilot PXD064499). Each has a report + BLOCKED.md entry documenting sources exhausted.

### Tooling findings this run (saved to memory / opened as issues)
- **parse_sdrf `--template` honors only the LAST flag** (single-value Click option). All "validated against N
  templates" claims only checked the last; reviewers' manual `resolve_templates.py` checks are what enforced
  multi-template compliance. Going forward: validate each template in a separate run. (memory:
  parse-sdrf-only-last-template)
- **parse_sdrf age regex rejects `anonymized`** though human.yaml prose recommends it for protected ages;
  the regex DOES accept a leading `>=`/`<=` operator (used `>=90Y` for a HIPAA "90+" cap in PXD063590).
- **Issue #36** — skill should hunt channel maps in Zenodo/figshare/OSF/GitHub cited in Data Availability
  (PXD053053/PXD064499 maps lived in Zenodo, not PRIDE).
- **Issue #37** — skill should read modifications from deposited search files (PD `.msf` Workflows node,
  MaxQuant/FragPipe/DIA-NN), not just the channel map (PXD048052 Carbamidomethyl miss).

### mDIA closeout (2026-07-17) — the last two dimethyl-multiplex datasets
The two remaining `include` datasets were dimethyl-mDIA (outside the TMT/SCoPE sweep). Both ANNOTATED —
neither had a missing experimental factor (untreated HeLa / normal mouse liver), and the mDIA reference
channel (Δ0 light dimethyl = bulk pool) was correctly modeled as reference, not a single cell.
- **PXD038632** — mDIA HeLa single cells (Thielert et al., Mol Syst Biol 2023), 1359 rows (906 cells +
  453 Δ0 reference). Curator key isolated the one true single-cell arm from 12 dilution/bulk/decoy arms.
- **PXD038699** — scDVP mouse-liver hepatocyte zonation (Rosenberger/Mann, Nat Methods 2023), 1154 rows
  (dimethyl mDIA single hepatocytes + a label-free 5-shape pentagon-pool arm). 45 unmapped m1A runs
  confirmed real by range-reading the 322 GB zip.
Dimethyl channels verified by mass on both: Δ0=UNIMOD:36, Δ4=UNIMOD:199 (+4), Δ8=UNIMOD:330 (+8; the +6
UNIMOD:510 trap avoided). No Carbamidomethyl (mDIA prep not reduced/alkylated).

**FINAL: 58 APPROVED / 0 PENDING. Include set COMPLETE — 0 truly-unhandled.** All 70 screened `include`
datasets accounted for: 58 hash-bound approved SDRFs + documented blockers, plus PXD046211/PXD058457
(already carry an upstream SDRF in PRIDE) and PXD053464/PXD057685 (recorded duplicates in DUPLICATES.md).
Blocked (full, no SDRF): PXD029320, PXD034370, PXD041328, PXD048347, PXD064501, PXD064518 (multiplexed, no
channel->sample map) + PXD043473, PXD073250, PXD020586, PXD025387 (earlier). Partial blocks (annotated +
one blocked arm): PXD049412, PXD061710. Duplicates: Groups 1-6 + PXD046467 self-dup in DUPLICATES.md.
Tooling: parse_sdrf `--template` only-last defect (memory + CLAUDE.md #7 fixed); issues #36 (Zenodo maps)
and #37 (.msf modifications) opened. Pushed through 4aa93bf; the mDIA commits (b2e7d36, 2a18efe + this)
await the next "push".

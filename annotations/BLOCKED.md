# Datasets screened `include` but NOT annotated

These datasets are genuine MS-based single-cell proteomics (see `results/single_cell_screen.tsv`)
but could not be annotated faithfully: the deposited data and publication do not record which
sample each measurement belongs to. Annotating them would require fabricating sample identity.

Recorded per the annotatability gap described in
[#31](https://github.com/bigbio/sdrf-skills/issues/31). Screening decides *relevance*; it does
not decide *annotatability*. These are the cases where the two diverge.

---

## PXD043473 — Toward Single Bacterium Proteomics

**Blocker: TMT channel → sample mapping does not exist.**

| | |
|---|---|
| Screen label | `include` (correct — FACS-sorted single *E. coli*, 48 cells, 250-cell carrier) |
| Publication | PMID:37713396 (open access, full text read) |
| Deposited | 17 raw files (16 × TMT single-cell runs + 1 bulk), 5 result `.xlsx` |
| SDRF would need | 16 files × 10 channels = 160 rows, each with a sample identity |

The paper gives the run *composition* — "three single and three double cells ... with two CP
digests labeled by two different TMT labels", plus "two TMT channels remained unutilized" — but
never states **which channel holds which sample**.

Sources checked, all exhausted:

| source | result |
|---|---|
| Paper Methods | composition only; no channel assignment |
| `..._Percolator_proteins.xlsx` | all channels named **`"Sample, n/a"`** (Proteome Discoverer default) |
| `..._Percolator_peptides.xlsx` | same |
| PRIDE `files/all` | 22 files: 17 RAW + 5 result xlsx. No sample sheet |
| Europe PMC supplementary | 8 files, all figures (.jpg/.gif) |

Annotating would mean inventing the identity of all 160 rows, including which channels are the
carrier — the error `criteria/single_cell_proteomics.md` explicitly calls "a classic annotation
error when omitted".

**Unblocked by:** a channel key from the authors, or a re-deposition with sample names set in
Proteome Discoverer.

**Incidental discrepancies** (recorded for whoever revisits):
- Paper says TMT-**10**plex; single-cell result table reports **11** channels (126→131C); bulk
  result table reports **6** (126, 127C, 128C, 129C, 130C, 131C) and the bulk file is named
  `..._FToP_TM6.raw`.
- Cells are *E. coli* **BL21(DE3)**; the searched database was **K12** (SwissProt, 4465 entries).
- PRIDE `instruments` says `Orbitrap Fusion Lumos`; the paper says `Orbitrap Fusion Eclipse Tribrid`.

---

## PXD073250 — Democratized SCP resolves cell state heterogeneity in skin tumors

**Blocker: the `pop1`/`pop2` → FACS population key does not exist.**

| | |
|---|---|
| Screen label | `include` (correct — FACS-sorted single cells from CCS skin tumor) |
| Publication | PMID:42373542 / doi:10.26508/lsa.202603759 (gold OA, CC-BY, full text read) |
| Deposited | 549 raw `.d.zip` (529 single cells + 20 blanks) + 8 result/FASTA/library files |
| Structure | 6 plates × 2 populations; `plate`+`well` uniquely identifies each cell |

The study sorts **two** populations (paper, Methods):
- `CD45−/CD200+` — tumor keratinocyte population
- `CD45+/CD74+` — immune cell population

Every single-cell filename carries `singlecell_pop1` or `singlecell_pop2`. **The string "pop"
does not appear anywhere in the paper**, and no source maps `pop1`/`pop2` onto the two antibody
phenotypes. Per-cell type (macrophage / dendritic cell / keratinocyte) is *analysis-derived*
(Seurat clustering + FACS cross-reference), not deposited per run.

The mapping is *inferable but not stated*. Deposited `report.pg_matrix.tsv` protein counts:

| group | n | mean | median |
|---|---|---|---|
| pop1 | 263 | 476 | 349 |
| pop2 | 266 | 787 | 709 |
| blanks | 28 | 39 | 0 |

versus the paper (Fig 2C, over the 419 QC-passed cells): `CD45−/CD200+` mean **467**,
`CD45+/CD74+` mean **914**. The ordering matches unambiguously (pop1 < pop2), implying
pop1 = `CD45−/CD200+` and pop2 = `CD45+/CD74+`.

**This was deliberately NOT used.** It is inference from data, not deposited metadata, and it
would silently assert cell identity for 529 rows on the strength of a summary-statistic
comparison. The paper's values are QC-filtered while the deposited set is not, so the exact
values do not correspond; only the ordering does.

**Unblocked by:** a `pop1`/`pop2` key from the authors, or deposition of the per-cell FACS index
data (the paper states cell annotations were validated "by cross referencing with each cell's
FACS markers", so per-cell marker values exist but were not deposited).

**Also inaccessible:** Table S1 (patient demographics — needed for `characteristics[age]` /
`[sex]`, both `required` in the `human` template) is in supplementary material behind the
publisher; `life-science-alliance.org` returns HTTP 403 to programmatic fetch.

**Worth noting for tooling:** PRIDE and Europe PMC both report `is_open_access: false` for this
paper. It is in fact **gold OA, CC-BY**, and Unpaywall resolved the publisher PDF immediately.
Trusting the OA flag would have skipped the Methods entirely.

---

## PXD025387 (partial) — proteoCHIP: the HeLa/HEK arm only

**Blocker: TMT label assignment was deliberately randomised per run, and the key was not deposited.**

Unlike the entries above, this dataset was **annotated in part**: `annotations/PXD025387.sdrf.tsv`
covers 118 of 135 deposited raw files (670 rows). Only the 17-file HeLa/HEK arm is blocked.

| | |
|---|---|
| Screen label | `include` (correct — cellenONE single-cell deposition on proteoCHIP) |
| Publication | PRIDE links **none**; preprint doi:10.1101/2021.04.14.439828 matches the deposit, peer-reviewed version PMID:37839701 / PMC10684380 (both read in full) |
| Deposited | 135 raw + 4 SpectroMine `.psar` + checksum |
| Annotated | 118 raw → 670 rows (582 single HeLa cells, 21 carriers, 67 label-free) |
| **Blocked** | **17 raw** — 11 HeLa/HEK no-carrier + 6 HeLa/HEK 20× carrier = **158 single cells** |

The four HeLa-only arms are annotatable because *every* single-cell channel holds one HeLa cell, so
there is nothing to map. The HeLa/HEK arm is the opposite case — and it is the study's headline
biological result ("158 multiplexed single cells from two highly similar human cell types").

The published Methods state the **composition** of each run but never the assignment:

> "we used five TMT channels per cell line, labeled with all available TMT10 tags and acquired 17
> analytical runs (170 cells)"

and, decisively:

> "To eliminate batch effects of TMT label assignments, all multicell type experiments were performed
> with a **label switch and label randomization** (*i.e.*, opposing label assignment or scrambled)."

So the 5 HeLa / 5 HEK split **differs per run by design**, and no per-run key was deposited. The 20×
carrier runs are structured (carrier in 131, 130N left empty, 8 single cells = 4 HeLa + 4 HEK) but
carry the same randomisation.

Sources checked, all exhausted:

| source | result |
|---|---|
| Preprint Methods | no channel assignment; no layout at all |
| Published Methods + Experimental Design | composition + explicit randomisation statement; no key |
| `..._TMT10-plex_HeLaHEK_final.psar` | UTF-16 strings give the 17 runs, `NewTMTSchema`, and channels `TMT10_126`…`TMT10_131N` — **zero** HeLa/HEK condition strings. The SpectroMine equivalent of PD's `"Sample, n/a"` |
| PRIDE `files/all` | 140 entries: 135 RAW, 4 `.psar`, 1 checksum. No sample sheet |
| Europe PMC supplementary | one PDF of figures |

Annotating would mean inventing the cell type of 158 rows across a randomised design — the exact
error the carrier/identity guidance warns about.

**Unblocked by:** the per-run label assignment from the authors (a 17 × 10 table), or the cellenONE
sort log.

**Second, independent blocker — the HEK line is ambiguous.** The preprint Methods say
"HeLa and **HEK293T** cells were cultured"; the published Methods say "HeLa, S2, and **HEK-293T**";
but the published Experimental Design says "four HeLa and four **HEK-293** cells" and "ten HeLa and
ten **HEK-293** cells". HEK293 (`CVCL_0045`) and HEK293T (`CVCL_0063`) are distinct lines with
distinct Cellosaurus entries, so `characteristics[cell line]` has no determinable value even if the
channel key appeared.

**Incidental discrepancies** (for whoever revisits):
- The published paper reports **17** HeLa/HEK no-carrier runs (170 cells); only **11** (110 cells)
  are deposited here. 110 + 48 = 158 = PRIDE's stated count, so this PXD is the *preprint's* deposit
  and the 2023 revision's 6 extra runs live elsewhere.
- The deposited analysis is **SpectroMine 2.0** (`.psar`, 2021-04-14); the published paper describes
  **CHIMERYS / Proteome Discoverer 3.0**. Sample-prep numbers also differ (trypsin 20 vs 10 ng/µL,
  TMT 22 vs 10 mM). The deposit matches the preprint, not the published paper.

---

## Not a blocker: empty TMT channels in PXD025387

The same `characteristics[cell line]` flag pair cost `PXD025387` **21 rows**. Every 20× carrier run
leaves channel 127C empty on purpose ("leaving the adjacent 127C TMT-channel empty to minimize
isobaric interference") — 7 TMT10 + 14 TMTpro = 21 empty channels, excluded from the SDRF.

This is the fourth dataset hitting the wall, and the sharpest illustration yet, because the two
declared templates **actively disagree**: `single-cell/1.0.0` provides `empty` as a special value of
`characteristics[cell identifier]` *and* `NT=empty;AC=PRIDE:0000903` as a sample type — it is built
to annotate these channels — while `cell-lines/1.1.0` makes `characteristics[cell line]` `required`
with both reserved words `false`, which makes the row inexpressible. An empty channel is not an
absence of information; it is a designed feature of the layout whose position is documented, and
the SDRF cannot say so.

**Unblocked by:** per-row template applicability, or `allow_not_applicable: true` on
`characteristics[cell line]`.

---

## Not a blocker: excluded runs in annotated datasets

For contrast — `PXD052416` was annotated (118 rows) while depositing 132 raw files. The 14 blank
runs were excluded because `characteristics[cell line]` is `required` with **both**
`allow_not_applicable` and `allow_not_available` set to `false` in `cell-lines/1.1.0`, making a
sample-less run inexpressible. That is a spec limitation, not missing evidence, and the
reconciliation (132 deposited → 118 annotated → 14 blanks) is recorded here rather than lost.

`PXD016921` hits the **same wall at minimum scale**: 7 deposited raw files → **6** annotated, with
`Blank.raw` excluded. The blank is cell-free PBS supernatant carried through the identical nanoPOTS
protocol (paper Methods: *"an equivalent volume of cell-free PBS buffer from the cell suspension
supernatant was collected and dispensed into nanowells and processed following the same protocol"*).
It has no cell line, so `characteristics[cell line]` has no legal value; annotating it would mean
asserting `HeLa` for buffer, which `parse_sdrf` accepts and which is false. The blank is not
incidental — it is a reported result (the paper cites it as the specificity control, yielding only
6 protein groups without MBR), so the exclusion loses a run the study deliberately acquired.

`PXD024043` hits the **same wall at the largest scale so far**: 520 deposited raw runs → **515**
annotated. The 5 excluded are 3 × `0cell` (FACS-sorted zero cells,
`20200213_TIMS04_SA_ADB_0cell_{02,03,05}_*.d`) and 2 × `0ng` (no peptide loaded,
`20180921_..._0ng_HeLa_..._{1,2}_D1_01_{3014,3015}.d`). Same cause: `characteristics[cell line]` has
no legal value for a sample-less run, and asserting `HeLa` for buffer passes `parse_sdrf` and is
false. As in `PXD016921`, the blanks are **a reported result, not incidental** — the paper analyses
the zero-cell runs directly ("Protein identifications at zero cells are most likely a result of
minimal contribution from previous runs", Fig EV1A/B), so the exclusion again drops runs the study
deliberately acquired and discussed.

`PXD043355` hits the **same wall**: 148 deposited raw runs → **143** annotated. The 5 excluded are
`200nL__CH1_blank_L6`, `500nL1ng_CH2_blank_M20`, `Jurkat_500nL_1ng_CH1_BLANK_O5`,
`Jurkat_500nL_1ng_CH2_BLANK_N3` and `Jurkat_500nL_1ng_CH2_BLANK_N6` — wells that received the
one-step Trypsin/Lys-C reagent but no dispensed cell. Same cause: `characteristics[cell line]` has no
legal value for a sample-less run, and asserting `HeLa`/`Jurkat` for reagent blank passes
`parse_sdrf` and is false. The blanks are **not incidental**: the paper's central quality claim is
measured against exactly these runs ("nearly 30% of the wells that were expected to contain a single
cell … resulted in zero identified proteins", reduced to "<3%" after the added centrifugation step,
Figure 2C), so the exclusion again drops runs the study deliberately acquired and analysed.

`PXD043355` also **sharpens the `PXD025387` argument to its cleanest form**. That dataset showed
`single-cell` supplying an `empty` vocabulary that `cell-lines` forbids. Here the same contradiction
appears within a single row and is not even about TMT channels: `characteristics[cell identifier]`
(`single-cell/1.0.0`, `required`) explicitly lists `empty` among its `special_values` — a vocabulary
that exists **for precisely these five rows** — while `characteristics[cell line]` (`cell-lines/1.1.0`,
`required`, both `allow_*` flags `false`) makes the row that would use it unwritable. One template
ships the word for the concept; the other forbids the row from existing. Both templates are declared
by the same file, as `single-cell` requires an organism/sample template alongside it.

`PXD037527` hits the **same wall**: 331 deposited raw runs → **325** annotated. The 6 excluded are
4 × `BlankCarryOver02ng_{15m,30m}_{1,2}` and 2 × `..._DIA50_02ng_blk{,2}` — solvent runs acquired to
measure column carry-over. Same cause: `characteristics[cell line]` has no legal value for a
sample-less run, and asserting `HeLa S3` for mobile phase A passes `parse_sdrf` and is false. The
blanks are **not incidental**: the paper quantifies them directly ("Only 171 proteins were identified
on average from blank runs, including those identified by MBR, indicating a low degree of column
carryover"), and the submitters deposited two dedicated Proteome Discoverer result files for them
(`02ng_blank_15m_MBR.msf`, `02ng_blank_30m_MBR.msf`). A run with its own deposited search result and
its own sentence in the paper is not debris — and it is still unwritable.

Nine datasets now (`PXD052416`, `PXD019515`, `PXD016921`, `PXD022791`, `PXD021882`, `PXD025387`,
`PXD024043`, `PXD043355`, `PXD037527`) have lost runs or a whole template to one flag pair on one column. `PXD016921` is the cleanest minimal
reproduction: a 7-file deposit where exactly one row is inexpressible. `PXD022791` (below) is the
most damaging: a deposition that is 63% cell-line material and still cannot declare `cell-lines`.
`PXD025387` (above) and `PXD043355` are the strongest argument that the flags are simply wrong: there, `single-cell`
explicitly supplies an `empty` vocabulary for exactly these rows, which `cell-lines` then forbids
them from using.

---

`PXD016299` (CHIP/STUB1 KO vs WT SH-SY5Y): only the 6 pulse-SILAC Orbitrap Elite runs
(`CHIP_{WT,KO}_1-3.raw`) are annotated. Out of this SILAC campaign's scope, not blocked: 12
label-free SWATH runs on the TripleTOF 5600+ (`SWATH_SH-SY5Y_SY5Y_CHIP_{WT,KO}_biorep{1,2}_techrep{1-3}.wiff`)
and 2 IDA spectral-library runs (`IDA_..._spectral_library_rep{1,2}.wiff`), each with its `.wiff.scan`.
They could go into a separate label-free SDRF (rule 12).

`PXD004880` (Down syndrome twin fibroblasts): 140 deposited vendor raw files → **36** annotated
(the pulsed-SILAC SWATH runs `yanliu_Y151023_002_SW`–`037_SW`). The other 104 are outside this
SILAC campaign, not blocked by a missing channel map: 56 label-free steady-state SWATH runs
(12 twin `Y141216_*_SWa`, 44 unrelated individuals `Y150223_*_SW`), 34 light-only DDA library runs
(including the pSILAC t0 library runs `Y151023_038/039`, `Y151028_001-004`) and 14 dimethyl-labelled
Q Exactive Plus raws. A later separate SDRF for the dimethyl arm would first need its
light/intermediate/heavy assignment documented. Note: the run sheet names the twin steady-state
runs `_SW`, the deposited files are `_SWa`.

## Not a blocker: `cell-lines` undeclarable for a mixed cohort (PXD019515)

`PXD019515` was annotated in full (12 deposited → **12** annotated, nothing excluded), but the
**same** `characteristics[cell line]` flags cost it the whole `cell-lines` template rather than a
few rows.

The deposition is a **mixed cohort**: 3 single HeLa cells (a cell line), 6 LCM-excised primary
spinal neurons, and 3 blanks. Because `characteristics[cell line]` is `required` in
`cell-lines/1.1.0` with **both** `allow_not_applicable` and `allow_not_available` `false`, there is
no legal value for the 9 non-cell-line rows. The template is all-or-nothing per file, so the only
options were:

| option | cost |
|---|---|
| declare `cell-lines` | assert a cell line for 9 rows that have none — fabrication |
| declare `cell-lines`, annotate only the 3 HeLa runs | discard the study's entire biological result (MN vs IN, Fig. 4) |
| **drop `cell-lines`** ← chosen | lose `cell line`, `cellosaurus accession`, `cellosaurus name` for the 3 HeLa rows |

**What is lost:** `CVCL_0030` has no dedicated column in `annotations/PXD019515.sdrf.tsv`. HeLa
identity survives only as `characteristics[cell type]` = `NT=HeLa cell;AC=CLO:0003684` — legal,
since that column's resolved validator allows `clo`, but not the column a consumer would look in.

**The general shape:** the sample-layer templates assume a cohort is homogeneous in *kind*. A
single deposition mixing cell-line and primary-cell material cannot declare `cell-lines` at all,
so a real cell line goes unrecorded because of rows it does not describe. Distinct from the
`PXD052416` case above (sample-less blanks); same root cause — a `required` column with both
reserved words forbidden and no per-row template scoping.

**Unblocked by:** per-row template applicability, or relaxing `allow_not_applicable` to `true` on
`characteristics[cell line]` so non-cell-line rows in a mixed cohort can say so.

### Strongest instance: `PXD022791` — a *majority*-cell-line deposition that cannot say `cell line`

`PXD022791` is a strict superset of `PXD019515` (all 14 of the latter's files are byte-identical
inside it, SHA-1 verified) and was likewise annotated in full: 24 deposited raw → **24** annotated.
It hits the identical wall via the identical 9 rows — the 6 LCM neurons and 3 blanks — but the cost
is now the inverse of the intuition:

| | PXD019515 | PXD022791 |
|---|---|---|
| cell-line rows losing `CVCL_0030` | 3 of 12 (25%) | **15 of 24 (63%)** |
| rows actually forcing the drop | 9 | 9 (the same files) |

The extra 12 rows are the Fig. 2A method-optimisation arm (0.5 ng Pierce HeLa protein digest
standard). So a deposition that is **63% HeLa-derived** still cannot declare `cell-lines`, because a
single-template SDRF must satisfy its strictest row. Nine rows veto fifteen. Splitting the deposition
into two SDRFs was considered and rejected: it would fracture the Fig. 2A → 2B → 4 workflow narrative
that is the point of the paper.

This is the clearest argument for **per-row template applicability** over merely relaxing the flag:
the minority of rows is dictating the metadata vocabulary available to the majority.

### Fifth instance: `PXD021882` — the mix is cell line + primary *blood* cells

`PXD021882` (autoPOTS, PMID:33352054) was annotated in full: 37 deposited raw → **37** annotated,
nothing excluded. It reproduces the `PXD019515` shape with a different primary-cell type, which
matters: this is not a quirk of laser-capture neurons.

| | count |
|---|---|
| HeLa cell rows losing `CVCL_0030` | **21 of 37 (57%)** |
| rows forcing the drop | 16 (10 primary B/T lymphocytes + 6 supernatant blanks) |

The deposition is a HeLa dilution series (0–500 cells, 27 rows incl. 6 blanks) plus a
clinical-feasibility arm of FACS-sorted B and T lymphocytes from one healthy donor (10 rows). The
lymphocytes are the paper's headline application (Fig. 5), so annotating only the HeLa rows was never
an option. Sixteen rows veto twenty-one.

Two details this instance adds:

- **The blanks would be inexpressible even without the lymphocytes.** With `cell-lines` dropped, all
  6 supernatant blanks are annotated normally — the same runs that forced `PXD052416` to exclude 14
  files and `PXD016921` to exclude 1. The template drop that costs `CVCL_0030` is simultaneously what
  *saves* the blanks. The two failure modes above are one failure mode.
- **Primary blood cells are a common mixing partner.** Any low-input/single-cell methods paper that
  benchmarks on a cell line and then demonstrates on primary cells — a near-universal structure in
  this field — lands here. That is the argument that this is structural, not incidental.

**Unblocked by:** the same fix — per-row template applicability, or `allow_not_applicable: true` on
`characteristics[cell line]`.

### Sixth instance: `PXD046467` — the mixing partner is a *whole other phylum*

`PXD046467` (Shen *et al.*, PMID:39325989) was annotated in full: 83 deposited raw → **83**
annotated. It reproduces the shape a sixth time, and closes the "maybe it's always neurons/blood"
escape: here the 30 rows that veto `cell-lines` are **cells inside a live frog embryo**.

| | count |
|---|---|
| HeLa S3 rows losing `CVCL_0058` | **53 of 83 (64%)** |
| rows forcing the drop | 30 (*X. laevis* D11 blastomere aspirates) |

Structurally identical to `PXD022791`: a majority-cell-line deposition (64%) silenced by a minority
of rows. Two details this instance adds:

- **It compounds with the organism templates.** The deposition is human + Xenopus, and
  `human`↔`vertebrates` are mutually exclusive, so `vertebrates` is forced — which *also* un-licenses
  `characteristics[age]` and `[ancestry category]`. HeLa S3's Cellosaurus demographics
  (`AG=30Y6M`, `Population: African American`) are therefore unrecordable on two independent grounds
  at once. The all-or-nothing template model fails twice over the same mixed cohort.
- **The lost accession is the one the brief warns hardest about.** `CVCL_0058` (HeLa **S3**, the
  Pierce 88329 digest standard) versus parental `CVCL_0030` is exactly the distinction that is
  "research, not lookup" — and the column that would record it does not exist in the file. Identity
  survives only as `characteristics[cell type]` = `NT=HeLa S3 cell;AC=CLO:0003696`, which is a
  second-best home made worse by CLO carrying **two indistinguishable S3 terms** (`CLO:0003696`
  "HeLa S3 cell" / `CLO:0003699` "HELA-S3 cell", neither with a definition, xref, or Cellosaurus
  link). The fallback the previous instances relied on is itself ambiguous here.

**Unblocked by:** the same fix. Six datasets now (`PXD019515`, `PXD022791`, `PXD021882`,
`PXD046467`, plus `PXD052416`/`PXD016921` via the sample-less-run variant).

---

## New shape: a real sample whose *identity* is undetermined (PXD041879)

`PXD041879` was annotated (124 deposited raw → **90** annotated; see
`annotations/PXD041879.report.md`). Its 22 blank/empty/solvent runs are the familiar
`characteristics[cell line]` wall. Its **12 QC runs are a different case**, and worth separating
because the two shapes already recorded here do not cover it:

| shape | example | what is missing |
|---|---|---|
| sample-less run | `PXD052416` blanks, `PXD016921` `Blank.raw` | there is **no sample** |
| missing channel key | `PXD043473`, `PXD025387` | the **map** from measurement to sample |
| **undetermined material** ← new | **`PXD041879`** 10 ng QC | the sample **exists** and is unambiguously one specific thing — but nothing records *which* |

The 12 runs (`10ngQC_*`, `10ng_QC_*_channel*`, `Polypropylene_rapid_10ngQC_*`,
`nanoPOTS2_rapid_10ngQC_*`) are injections of a 10 ng peptide digest used as instrument QC. Sources
checked, all exhausted:

| source | result |
|---|---|
| Paper Methods (PMC11017373, full text read) | QC injections are **never mentioned** |
| PRIDE `description` / `sample_processing_protocol` | never mentioned |
| Raw header Xcalibur sequence fields (`Study`, `Client`, `Laboratory`, `Company`, `Phone`) | **empty placeholders** in all 12 |
| Raw header method filename | `..._2x5nguL_Stg_070QC.meth` — gives the **load**, not the provenance |
| Deposited FragPipe tables | QC runs appear as intensity columns only; no sample annotation |

The material is not even confirmed to be **HeLa**. If it is an in-house bulk digest of the study's own
ATCC HeLa it is parental `CVCL_0030`; if it is a commercial Pierce standard it is **HeLa S3**
`CVCL_0058` — a distinct Cellosaurus entry. Both are entirely plausible for this lab, they are mutually
exclusive, and `characteristics[cell line]` is `required` with **both** reserved words `false`, so the
row cannot say "a human peptide digest of unrecorded origin". Annotating requires choosing one — which
`parse_sdrf` would accept and which would be a coin flip asserted as fact.

Note this is the *inverse* of the usual complaint about that flag pair: here the flags are not merely
blocking a row that has nothing to say, they are **forcing a fabrication** on a row that has something
true but insufficiently specific to say.

**Unblocked by:** a QC standard identity from the authors (vendor + catalog number, or "our own bulk
HeLa"), which is one sentence of Methods.

**Worth noting for tooling — the OA flags were wrong in a new way.** PRIDE, Europe PMC *and* NCBI all
report this paper as not open access: `fullTextXML` → **HTTP 404 (not in OA subset)**, NCBI OA service
→ `idIsNotOpenAccess`, and `get_pdf_by_unpaywall` resolved the NIHMS PDF but the download was rejected
as anti-bot HTML. The rendered PMC article page nonetheless served the **complete Methods** (181 KB) to
a plain browser UA. Unlike `PXD073250` above — where the OA flag was simply wrong — here every
*machine-readable* OA route genuinely fails and only the HTML page works. Any annotator trusting the
flags, or trusting `fullTextXML` + Unpaywall alone, would have marked the cell type `unclear`
permanently: **the cell line for all 90 annotated rows exists in no other source.**

---

## Not a blocker: FAIMS compensation voltage has no column (PXD022791)

`PXD022791`'s optimisation arm compares 2-CV (−55 V, −70 V) against 3-CV (−55 V, −70 V, −85 V) FAIMS
methods — the study's own Fig. 2A axis. **No licensed column can express it.** The only candidates in
all 223 TERMS.tsv rows are `comment[ms min im]` / `comment[ms max im]` (PRIDE:0000841/842), and both
fail on two independent grounds:

- **semantics** — `values` is `numeric (1/K0 or Vs/cm2)`, TIMS reduced mobility, not a compensation
  voltage in volts;
- **syntax** — the resolved validator pattern is `^[\d.]+$`, which admits **no minus sign**. −55 is
  literally unrepresentable.

Consequence: rows `FAIMS_2CV_HELA_Point5ng_OTIT_HCD_*` and `FAIMS_3CV_HELA_Point5ng_OTIT_HCD_*` are
identical in all 43 columns except `assay name` and `comment[data file]`. The distinction survives
only inside a filename string. Writing `55`/`85` into the ion-mobility columns would validate cleanly
and be a fabrication — the silent-corruption class — so it was not done.

**Unblocked by:** a `comment[faims compensation voltage]` term (signed, volts, `cardinality:
multiple` so a 2-CV vs 3-CV method is expressible as repeated columns).

---

## Not a blocker: `dia-acquisition` cannot describe a mixed-acquisition deposition (PXD024043)

`PXD024043` deposits **449 diaPASEF runs and 71 ddaPASEF runs in one dataset** — the screen's
`acquisition=both`, true *per run*. The two facts collide:

- `dia-acquisition/1.1.0` defines `comment[proteomics data acquisition method]` as `required`,
  `allow_not_applicable: false`, `allow_not_available: false`, plus a `values` validator restricted to
  the single literal `Data-independent acquisition` at `error_level: error`. **No legal value exists
  for a DDA row**, including both reserved words.
- `comment[dia method]`, `comment[scan window lower limit]`, `comment[scan window upper limit]` and
  `comment[isolation window width]` are licensed by **`dia-acquisition` alone** (`TERMS.tsv`
  `usage=dia-acquisition` for all four).

So one SDRF cannot both cover the deposition and describe its DIA half. The choice is forced:

| option | cost |
|---|---|
| declare `dia-acquisition` | 71 sample-bearing runs become inexpressible and must be dropped |
| omit it (**chosen**) | 449 DIA runs lose 4 columns — all `recommended`, none `required` |

Full coverage was kept: dropping 71 real samples to preserve four recommended columns inverts the
scope rule (exclusion is for *sample-less* runs). Per-row acquisition truth survives in
`comment[proteomics data acquisition method]`, so the file is under-described, never wrong.

**What is lost is measured, not hypothetical.** Extracted from `DIAParameters.txt` inside the
deposited `.d` folders: fixed **25 m/z** isolation windows (400–425, 425–450, …), 400–1200 m/z,
`diaPASEF`. Unlike PXD052416 — where `isolation window width` was unrepresentable because diaPASEF
windows were *variable*-width against a scalar pattern — here the value is a clean scalar that fits
the pattern perfectly and still has nowhere to go.

**Unblocked by:** relaxing `dia-acquisition`'s acquisition-method column to permit DDA rows (the
window columns already allow both reserved words, so mixed rows would degrade gracefully), or
licensing the four DIA columns from `ms-proteomics` so they can be declared without the DIA-only
restriction. Either would make mixed-acquisition depositions — increasingly common in SCP
method-development papers — expressible in one file.

### Second instance: PXD044986 (the prediction above came true)

`PXD044986` (Mun *et al.*, PMID:39030393) reproduces the collision independently: **290 diaPASEF +
25 ddaPASEF runs**, screen `acquisition=both`, again true *per run*. The same option was taken for
the same reason — the 25 DDA runs are **pooled library-generation samples** (20 cells/well for the
four cholangiocarcinoma lines, 50 for Jurkat, 200 nuclei for PEO1), not sample-less blanks, so the
scope rule forbids dropping them. 315 deposited → 315 annotated, and the four DIA columns are lost.

This instance is **strictly worse than PXD024043**, because here the deposited DDA runs are not
incidental: they build the very spectral libraries the DIA half is searched against
(`Spectral_library_CCA.tsv`, `Spectral_library_Jurkat.tsv`, `Spectral_library_PEO1_Nuclei.tsv`, all
deposited). Declaring `dia-acquisition` would drop precisely the runs that make the DIA analysis
reproducible — the template would enforce its own irreproducibility.

What is lost is again measured, not hypothetical, and again a clean scalar: the paper states a fixed
**25 m/z** isolation window over **400–1000 m/z**, 8 PASEF scans/cycle, `diaPASEF` — every one of
which fits its column's pattern and has nowhere to go. Two independent depositions have now paid the
same cost, which is the argument for the fix proposed above.

### Third instance: PXD037527 — and the first where the DDA half *is* the paper

`PXD037527` (Truong *et al.*, PMID:37380610) is the third independent collision: **255 DDA/WWA +
70 DIA runs**, screen `acquisition=both`, again true *per run*. Same option, same reason, same cost:
325 deposited-and-annotated rows, four DIA columns lost.

This instance **retires the "just declare `dia-acquisition` and drop the DDA rows" counter-argument
entirely.** In PXD024043 the DDA runs were a minority arm; in PXD044986 they built the spectral
libraries. Here the paper is *titled* "Data-Dependent Acquisition with Precursor Coisolation…" — DIA
is the **comparator**, present only so the DDA/WWA method can be shown to beat it (Fig. 2A, 4A).
Declaring `dia-acquisition` would drop 255 of 325 rows, including every run of the method the paper
exists to describe, and keep only the arm it argues against.

The lost values are again clean scalars: fixed **50 m/z** windows over **400–800 m/z** (plus SWATH
variants in Table S1), all of which fit their columns' patterns and have nowhere to go.

A fourth option specific to this deposition — split it into two SDRFs, DDA and DIA — was rejected
because the ATG9A-knockout comparison and the HeLa/K562 cell-type comparison **span both acquisition
modes**; splitting would sever the biological factor from half its samples to satisfy a template flag.

### Fourth instance: PXD046467 — a DDA-vs-DIA benchmark, i.e. the exact study the template excludes

`PXD046467` (Shen *et al.*, PMID:39325989) is the fourth independent collision: **62 DIA + 21 DDA**
Q Exactive Plus runs, screen `acquisition=both`, again true *per run*. Same option, same reason:
83 deposited → **83** annotated, four DIA columns lost.

If PXD037527 retired the "drop the DDA rows" counter-argument, this instance retires the template's
premise. The paper is titled *"Data-Independent Acquisition Shortens the Analytical Window of
Single-Cell Proteomics to Fifteen Minutes…"* and its entire claim is a **head-to-head DDA-vs-DIA
comparison on the same material** ("This DIA method identified 1161 proteins vs 401 proteins by the
reference DDA"). The 21 DDA runs *are* the control the result is measured against, and they are
searched with Proteome Discoverer to build the very spectral library the DIA half uses (the
deposited Spectronaut `.sne` files name it `CE 350-900 library 7 runs 20kV`; the paper: "The DIA
spectral library was developed by analyzing the HeLa proteome digest using DDA in 7 technical
replicates").

`dia-acquisition` is therefore undeclarable for **method-development papers about DIA** — the
population most likely to have DIA window metadata worth recording. Declaring it would drop the
control arm and the library-generation runs in one move.

Splitting into two SDRFs was rejected for the same reason as PXD037527: the DDA/DIA axis **is** the
study's `factor value`, so splitting severs the factor from half its rows.

The lost values are again clean scalars, and here they are the study's *independent variable* —
read directly out of the Xcalibur methods embedded in the raw files: **40 windows × 10 m/z** vs
**20 × 20**, over **500–900 m/z** (MS1 490–910). Every one fits its column's pattern and has nowhere
to go; they survive only in `assay name` and `comment[data file]`.

Four depositions have now paid this cost (`PXD024043`, `PXD044986`, `PXD037527`, `PXD046467`).

---

## Not a blocker: `single-cell` has `G2/M` but no `G1/S` (PXD024043)

`single-cell/1.0.0`'s `characteristics[cell cycle phase]` enum is
`[G1, S, G2, G2/M, M, G0, not determined]`. `PXD024043` is *designed* around four stages — the paper:
"to enrich cells in four cell cycle stages—G1, the G1/S transition, G2, and the G2/M transition". The
enum admits three of them. **`G2/M` is present; `G1/S` is not** — an asymmetric gap between the two
classic block points.

41 thymidine-blocked rows carry `G1/S`, which emits
`WARNING: Invalid value 'G1/S' - must be one of the allowed values`. The warning is accepted rather
than "fixed": `S` would be false (a thymidine block arrests *at* the G1/S boundary, not in S phase)
and `not determined` would discard the study's design. `error_level` is `warning`, so the truthful
value validates.

**Unblocked by:** adding `G1/S` to the enum, alongside the `G2/M` that is already there.

---

## PXD020586 (partial) — Schoof et al. scMS: the CV and `celltype_booster` runs only

**Blocker: the channel → sample map exists for 274 of 289 runs, and does not exist for 15.**

This dataset is the **counter-example** to `PXD043473` at the top of this file: same design shape
(FACS single cells + TMTpro + a 500-cell booster), opposite outcome, because the authors deposited
the key. `annotations/PXD020586.sdrf.tsv` covers **274 of 289** deposited raw files (4050 rows;
3432 single cells, 264 carrier, 216 reference, 48 empty, 90 bulk-library).

| | |
|---|---|
| Screen label | `include` (correct — FACS single cells, TMTpro, 500-cell booster, OCI-AML8227) |
| Publication | PMID:34099695 / PMC8185083 (open access, full text read) |
| Deposited | 289 raw + 7 `.pdResult` + `SCeptre_FINAL.zip` |
| Annotated | 274 raw → 4050 rows |
| **Blocked** | **15 raw** — 12 CV / injection-time runs + 3 `celltype_booster` runs |

**Why the other 274 work.** `SCeptre_FINAL.zip` ships `label_layout*.txt` (well → TMTpro channel),
`sort_layout*.txt` (well → FACS population), `sample_layout*.txt` (well → run),
`file_sample_mapping.txt` (raw → plate/run), and `results/*/meta.txt` — one row per
(file × channel) with well, gated population and per-cell FACS index data. Supplementary Table 1 and
Supplementary Fig. 7c then fix the carrier/reference composition per plate. Proteome Discoverer
sample names **were** set (`Abundances Normalized F1 127N Sample BLAST`), so the `"Sample, n/a"`
default that blocks PXD043473 never arises.

**The 12 CV runs** (`..._CVcheck_{150,300,500,1000}ms_{1,2,3}.raw`) are blocked structurally, not
just clerically. Twelve single-cell samples were **pooled into one aliquot**, injected in triplicate
at four injection times — so each channel holds **12 different single cells**. No layout for the CV
plate is deposited (`data/cv/` has only `cv_InputFiles.txt` + `cv_Proteins.txt`, whose headers are
bare `Abundances Grouped F1 126` with no sample names). That a per-channel stage assignment existed
is *implied* — Fig. 2d reports LSC n=15 and blast n=12, i.e. 5 LSC × 3 and 4 blast × 3 replicates —
but which channel held which stage is unrecoverable, and label layouts are randomised per plate
column so it cannot be reconstructed from the sibling plates.

**The 3 `celltype_booster` runs** are blocked by a documentation conflict: Supplementary Fig. 2's
caption says "**The 1:1:1 booster** was measured … without the addition of other channels", while the
filenames say `celltype_booster` (the cell-type-*specific* pools). All three share one
`originalRawFileNameWithoutExtension` (sequence rows 8/22/36 — three injections of one sample), and
`booster_only.ipynb` plots only `F1` with no deposited `F1/F2/F3` → filename table.

**Unblocked by:** the CV plate's label/sort layout, and a statement of which pool the
`celltype_booster` runs contain.

**Worth noting for tooling:**
- `python -m tools cellline lookup OCI-AML8227` returns **OCI-AML2 / CVCL_1619 at 0.82 "confidence"**.
  OCI-AML8227 is a primary patient-derived AML culture with **no Cellosaurus entry at all** (verified
  live; the API works — `OCI-AML3` returns 5 hits). OCI-AML2 is a different immortalised line from a
  different patient. The fuzzy hit would have validated cleanly and been wrong on all 4050 rows.
- CL has **no** leukemic-cell terms. Smart-mode OLS answers "leukemic stem cell" with
  `hematopoietic stem cell (CL:0000037)` and the LSC immunophenotype with `CL:0001024`
  (CD34+CD38− **hematopoietic** stem cell) — both assert a *normal* identity for leukemic cells.
  `BTO:0001545` (`acute myeloid leukemia cell`) is the honest term; the differentiation stage has to
  live in `characteristics[phenotype]` as free text (no PATO/EFO term fits "blast (CD34− CD38+)").
- PRIDE's `modifications` field lists only Oxidation + Carbamidomethyl — it **omits TMTpro**, the
  reagent the entire study is built on.
- The 981 MB `SCeptre_FINAL.zip` never had to be downloaded: PRIDE's HTTPS mirror honours HTTP range
  requests, so the zip central directory plus the few hundred KB of layout/meta members were read
  directly. The same trick resolved the 13 raw files that Proteome Discoverer's `InputFiles` tables
  did not cover.

---

## Not a blocker: the split-carrier channel key in PXD025481

`PXD025481` was annotated **in full** — 325/325 deposited raw files, 3037 rows — because the
submitters named every TMT channel in the deposited Proteome Discoverer tables
(`Abundance: F74: 126, Sample, R1, Control`). It is the direct counter-example to `PXD043473` above:
same lab-style carrier TMT design, opposite outcome, decided entirely by whether the PD sample names
were set before export.

One 48-row attribute is nonetheless unrecoverable. In the 24 `splitCP` runs the carrier proteome
occupies **two** channels, and the paper states the composition but not the assignment:

> "the CP was split into two channels, 131N and 131C, one composed of 100 control cells and the other
> of 100 treated cells"

The deposit contradicts itself on which is which:

| source | 131N | 131C |
|---|---|---|
| `SCP_168SC_MTX_48h_split_CP_peptides.xlsx` **Sheet3** | `CP treated` | `CP treated` |
| same workbook, **Sheet1** | `Control` | `Sample` |

Sheet3 is the curated sheet — it alone marks `130N`/`130C` as `Empty`, which the paper confirms — yet
it labels *both* carriers "treated", which the paper contradicts. Sheet1 is the only source naming a
control carrier, and it is demonstrably wrong in exactly that channel range (it calls the empty
`130N`/`130C` `Control`/`Sample`). Both channels are therefore annotated as carriers with
`characteristics[treatment]` = `not available`, rather than taking a 50/50 guess that would validate
cleanly either way.

**Unblocked by:** a `131N`/`131C` key from the authors.

**Worth noting for tooling:**
- **Three single-cell channels are individually marked `Empty`** inside otherwise-complete TMT10plex
  sets (`MTX_24h` R12 `130C`; `CPT_24h` R19 `128C`, `129C`). A builder trusting the study's documented
  uniform 9-channel layout would have fabricated three cells. Per-set maps must be read, never assumed
  — the layout also *flips* between sets (R1 `126 = Control`, R10 `126 = Treated`).
- **The set↔file link was provable, not assumed.** `SCP_MTX_3h` deposits 23 files skipping `Rxn8`, and
  its table has 23 sets skipping `R8` — the same integer. A relabelled or permuted mapping could not
  reproduce that gap.
- Europe PMC reports `is_open_access: true` for PMC9260713, but the JATS body is **empty** (ACS
  deposits abstract-only XML) and Unpaywall's `url_for_pdf` is null, so `get_pdf_by_unpaywall` 404s.
  The Methods — which carry the entire carrier design — were only reachable from the PMC HTML render.
  The inverse of the PXD073250 lesson: the OA flag was *right* and the full-text tooling still failed.
- Two deposited files are byte-identical: `SCP_168SC_MTX_48h_split_CP_peptides.xlsx` and
  `Inbuilt_bulk_MTX_48h_peptides.xlsx` (MD5 `b042c1d0e5af87d4dbe2cc9cdf5d19a1`).

---

## PXD049412 — Astral single-cell proteomics (PARTIAL block: two-proteome arm only)

**Dataset is ANNOTATED** (289/357 raw files → `PXD049412.sdrf.tsv`). This entry records the **one arm
that is not faithfully representable**, per the "partial annotation is legitimate" rule.

**Blocker: two-proteome (HeLa-S3 + yeast) mixes cannot carry a single `characteristics[organism]`.**

| | |
|---|---|
| Publication | PMID:39820751 / PMC11903296 (open access, full Methods read) |
| Arm | 18 raw files: HeLa-S3 + *S. cerevisiae* peptides mixed in one injection |
| Ratios (stated) | HeLa:yeast = 150:100, 200:50, 240:10 pg (Methods "Two-proteome mixes") |
| Instruments | 9 on Orbitrap Astral (2023-11-23), 9 on Orbitrap Exploris 480 (`E0_NEO6`, 2023-11-27) |

Each file is a **single physical sample containing two organisms**. `characteristics[organism]` is
single-valued per SDRF row; there is no non-fabricating way to state "Homo sapiens + Saccharomyces
cerevisiae" in one row, and splitting one file into two organism rows would misrepresent the run.
The mixes are quantification-benchmark standards, not a biological sample group, so no scientific
information is lost by omitting them from the biological SDRF.

Files excluded:
- `20231123_..._150pg_100pg_H_Y_r1..r3.raw`, `..._200pg_50pg_H_Y_r1..r3.raw`, `..._240pg_10pg_H_Y_r1..r3.raw` (Astral)
- `20231127_E0_NEO6_..._150pgH_100pgY_01..03.raw`, `..._200pgH_50pgY_01..03.raw`, `..._240pgH_10pgY_01..03.raw` (Exploris 480)

Also excluded (non-samples, documented in the report): **34 process blanks** (empty wells —
`characteristics[cell line]` forbids both reserved words) and **16 column washes**.

**Unblocked by:** an SDRF-Proteomics convention for mixed-species reference standards (e.g. an
agreed organism value or a per-organism split), if the community defines one.

---

## PXD061710 — SCP cell/tissue preservation (PARTIAL block: Figure 8 decrosslinking arm only)

**Dataset is ANNOTATED** (491 deposited single cells across Fig 1–5,7 → `PXD061710.sdrf.tsv`).
This entry records the **one arm that cannot be faithfully annotated**, per the "partial annotation is
legitimate" rule.

**Blocker: Figure 8 sample identity (cell line + organism) is undetermined.**

| | |
|---|---|
| Publication | bioRxiv `10.1101/2025.03.10.642380` (CC-BY, read in full) + J. Proteome Res. `10.1021/acs.jproteome.5c00268` (PMID 40534510) |
| Arm | `Decrosslinking_20min_fix_Figure8` — 96 single cells + 1 blank |
| Raw | `Decrosslinking_20min_fix_Figure8.7z` (259 GB) + `20250509_decrosslinking_Figure8.sne` (22 GB) |
| Search results | **none deposited** (Fig 1–5,7 each have a `_search_engine_results.tsv`; Fig 8 does not) |

Run names **were** recovered (LZMA2-decoded `.7z` header, no bulk download): 8 conditions ×12 cells +
1 blank — `Fresh_SC`, `01PFA_SC`, `03PFA_SC`, `1PFA_SC` and their `95C_…` (95 °C decrosslinked)
counterparts. So this is a **formaldehyde de-crosslinking** experiment (± 95 °C heat reversal across
fixation levels).

Why blocked: the **preprint's main text stops at Figure 7** — Figure 8 was added *after* the March-2025
preprint (raw dated `20250509`) for the journal version, which is **paywalled** (ACS returned HTTP 403;
Unpaywall/Europe PMC have no OA PDF). The file names encode fixation state but **not the cell line or
organism**. The Methods describe both human lines (RKO, MDA-MB-231) and a 20-minute-fixation mouse
(Pdx1-Cre;R26-LSL-Cas9-eGFP, 19 wk) — so Fig 8 could be human *or* mouse, cell line *or* tissue.
`characteristics[organism]` is required and I will **not** guess it; no arm-specific evidence resolves it.

**Unblocked by:** the journal Figure 8 legend / Methods (naming the Fig 8 cell line + organism), or a
deposited Fig 8 search-results/sample sheet. Given those, the 96 SC + 1 blank are trivially addable —
run names are already recovered in scratch (`fig8_dnames.txt`).

---

## PXD029320 — RTS-Assisted Acquisition Improves Coverage in Multiplexed Single-Cell Proteomics (RETICLE)

**Blocker: the TMTpro channel → sample (gate / differentiation-stage) map does not exist.**

| | |
|---|---|
| Screen label | `include` (correct — FACS single-cell-sorted OCI-AML8227, TMTpro16plex, 200/100-cell carrier) |
| Publication | PMID:35219906 / PMC8961214 (open access, full text read); PRIDE listed no publication |
| Deposited | 249 files: **97 raw** (39 diluted-standard `TMTpro2` + 58 real scMS `TMTpro5`/`TMTpro7`), 66 RTS `_realtimesearch.csv` logs, 14 `.pdStudy`, 70 PD result DBs (`.msf`/`.pdResult`/`.bak`/views), 1 fasta, 1 checksum.txt |
| SDRF would need | 97 files × 16 channels ≈ 1552 rows, each with a sample identity |

The paper gives the plex *composition* — real scMS: **4 CD34−, 5 CD34+CD38−, 5 CD34+CD38+** single
cells + 200-cell carrier (channel 126) per plex; diluted standard: 9 channels × 250 pg, **3 channels
per stage** (LSC/PROG/BLAST) + carrier — but **never states which channel holds which cell/stage**.
It says outright that identities were assigned **post-hoc in Python**: *"FACS data and sort- and
label layouts were used to create the metadata for each cell"* (SCeptre). Those `FACS.fcs`
index-sort files and sort/label layouts are **not deposited**, and per-plate index sorting means the
layout varies between plexes and cannot be inferred.

Sources checked, all exhausted:

| source | result |
|---|---|
| Paper Methods + Results + Table 1 | composition only (4/5/5; 3-per-stage); **no channel assignment** |
| 14 `.pdStudy` (all run groups) | every channel named **`"<rawfile> - [126…134N]"`, `SampleType="Sample"`** (Proteome Discoverer default) |
| `.msf` / `.pdResult` | same PD DBs, generic channels (GB-scale; `.pdStudy` design already proves it) |
| PRIDE `files/all` (249) | 97 RAW + 66 per-scan RTS `.csv` logs + fasta + checksum. **No sample sheet / FACS / layout file** |
| Europe PMC supplementary | 15 entries, all figures (`gr1–4`, `mmc1–5` = Figs S1–S5, `fx1`) |
| Cellosaurus API (`OCI-AML8227` + variants) | **0 hits** — patient-derived AML hierarchy culture, no CVCL |

Only 9 (standard) or 14 (scMS) of the 15 non-carrier channels are occupied, so even **which
channels are empty** is unrecorded. Annotating would mean inventing the identity of ~1552 rows.

**Unblocked by:** the authors' sort/label layout (channel → gate/stage per plex) or the SCeptre
per-cell metadata table, or a re-deposition with sample names set in Proteome Discoverer. Given a
layout the annotation is mechanical: carrier (126) → `sample type = standard`,
`cells per well = 200`/`100`; each single-cell channel → its gate, `cells per well = 1`; empty
channels omitted; templates `ms-proteomics + human + single-cell` (**not** `cell-lines` — no CVCL).

**Incidental notes** (for whoever revisits):
- The scMS arm was **not** reduced/alkylated ("Carbamidomethyl on cysteine (C) was not set, as
  these samples were not treated with TCEP/CAA") → **do not** annotate Carbamidomethyl for the scMS
  runs; it applies only to the diluted-standard arm.
- PRIDE `instruments` = `Orbitrap Eclipse`; paper = `Orbitrap Eclipse Tribrid` + FAIMS Pro. PRIDE
  `modifications` = `iodoacetamide derivatized residue` only (misses TMTpro / Oxidation / Acetyl /
  Met-loss, and wrongly implies alkylation of the scMS arm).
- One scMS file is flagged faulty in its own name: `…TMTpro7…RETICLE_750ms_10_faulty.raw`.

---

## PXD041328 — Deciphering lineage specification in mouse gastruloids (multilayered proteomics)

**Blocker: TMTpro channel → sample-identity map does not exist in the deposition.**

| | |
|---|---|
| Screen hint | multiplexed TMT proteoCHIP SCP — mouse gastruloid germ-layer cells (correct) |
| Publication | PMID:38754429 · DOI:10.1016/j.stem.2024.04.017 (Cell Stem Cell) — **not OA**, no PMCID |
| Organism | *Mus musculus* (NCBITaxon:10090), verified — not the blocker |
| Deposited | 75 RAW (`..._C{1..6}_S{...}.raw`, 6 proteoCHIPs; 3 named `_empty`) + `SEARCH.zip` (30.8 GB PD output) |
| SDRF would need | 75 files × 18 TMTpro channels = **1350 rows**, each with a sample identity |

Each `.raw` is one TMTpro-**18**plex injection (126→135N). The deposited Proteome Discoverer design is
the authoritative sample layout and carries **no identity**:

| source | result |
|---|---|
| PRIDE `sample_processing_protocol` | templated stub with **unfilled placeholders** ("presorted with **which?** FACS", "**Carrier were printed .**", "**For TMT labeling, .**") |
| `SEARCH.zip → CVG_Exp55.pdStudy` (design XML) | **1350 samples, all `SampleType="Sample"`**; sample names are just `<file> - [TMTtag]`; only Factor = `Experiments` (Exp55/Exp56); grouping only by Quan Channel. No carrier/single-cell/germ-layer |
| `SEARCH.zip → ..._PeptideGroups.txt` header | abundance cols `Abundance F{n} {tag} Sample Exp{55/56}` — generic **Sample** (PD no-map default) |
| PRIDE `files/all` (76, all PXD041328-verified) | no sample sheet / channel key |
| Publication | paywalled (cell.com + ScienceDirect 403; Unpaywall/EuropePMC no PDF); no PMCID → no EuropePMC supplementary |

No channel — not even the carrier — has a recoverable identity, so **no partial annotation is
possible**. Annotating would mean inventing all 1350 identities, including which channels are carrier
vs single germ-layer cells; the brief forbids fabricating channel/germ-layer identities.

`SEARCH.zip` was inspected by **ZIP64 central-directory range reads** (no 30.8 GB download): the
`.pdStudy` and `PeptideGroups.txt` header were the only members inflated (both small). The 50 GB `.msf`
SQLite was not extracted — it shares the same design origin.

**Unblocked by:** a deposited per-(file × channel) proteoCHIP layout table (carrier vs which single
germ-layer cell), a cellenONE isolation sheet, or a re-deposited PD study with real sample names
replacing the generic `Sample` default. Given that, the rows are straightforward (TMTpro-18;
vertebrates + ms-proteomics + single-cell).

---

## PXD034370 — Microscopy-based functional single-cell proteomic profiling (FUNpro / SCoPE-MS)

**Blocker: TMT10plex channel → single-cell identity mapping does not exist.**

| | |
|---|---|
| Screen label | `include` (correct — SCoPE-MS single-cell profiling of U2OS, microscopy-guided FACS) |
| Publication | PMID:35784653 / PMC9243628, Cell Reports Methods 2022, DOI 10.1016/j.crmeth.2022.100237 (OA, STAR Methods read in full). PRIDE `publications` is **empty**; paper found via Europe PMC. |
| Deposited | 44 files: **34 raw + 10 MaxQuant txt** (`evidence.txt`/`proteinGroups.txt` per figure group). No sample sheet. |
| SDRF would need | Fig4 alone = 10 TMT10plex sets × 10 channels = 100 rows, each with a cell identity + DDR group. |

The paper gives run *composition* — some wells "single cells", others "two hundred carrier cells",
plus "blank channels (PBS only)" (Fig S2B) — but never states **which TMT channel holds which cell**,
nor which single cell is DDR **Group 1** vs **Group 2** (the study's only factor).

Sources checked, all exhausted:

| source | result |
|---|---|
| Paper STAR Methods | composition only; no channel assignment; no Group-per-channel table |
| `Fig4_proteinGroups.txt` / `evidence.txt` | MaxQuant `Reporter intensity corrected 1..10` — **numbered only, no identity** (the `mqpar.xml`/experimentalDesign holding channel names was not deposited) |
| PRIDE `files/all` | 44 files: 34 RAW + 10 MaxQuant txt. **No csv/xlsx/mqpar sample sheet** |
| Europe PMC supplementary (PMC9243628) | 2 files, both figure images (`gr3.gif`, `gr5.jpg`) |
| Publisher/PMC `mmc1.pdf`/`mmc2.pdf` | not retrievable (PMC `bin/` → HTTP 404); Fig S2A shows MS settings, not a channel key |

**Forensic finding (insufficient):** per-channel reporter-intensity fractions across all 10 Fig4 sets
reliably identify the **carrier as ch10 / TMT131** (~78–89 % of signal; 59.6 % in the FigS2B set), but
the **blank position flips between runs** (ch8/TMT130N in Fig4; no near-zero channel in FigS2B) and the
remaining 8 single-cell channels are mutually anonymous with **no reference channel**. Only the carrier
is recoverable; the single-cell identities and phenotype groups are not.

**Unblocked by:** a channel key from the authors (M-P. Chien, Erasmus MC), a re-deposited MaxQuant
`mqpar.xml`/experimentalDesign with per-channel names, or a supplementary channel→cell table.

**Incidental discrepancies** (recorded for whoever revisits):
- **Instrument split across two Orbitraps.** PRIDE says only `Orbitrap Fusion Lumos`; the paper says only
  `Orbitrap Eclipse Tribrid`. Raw InstModel fields show BOTH: `Fig4_2206_*`, `FigS2A_2195_*`,
  `FigS2D_2178_*` = **Fusion Lumos**; `Fig4_2227_*`, `Fig4_2236_*`, `FigS2C_2363_*`, `FigS3A_2363_*` =
  **Eclipse**. Neither source is fully right.
- Label is **TMT10plex** (UNIMOD:737), not TMTpro. Static modification left empty → **no Carbamidomethyl**
  (no reduction/alkylation described). Variable mods: Deamidation NQ (UNIMOD:7), Oxidation M (UNIMOD:35).
- `FigS2D_2178_200T/200NT` is a **bulk 200-cell, label-free (LFQ)** control, not single-cell TMT.
- Cell line: U2OS (CVCL_0042) stably transfected with PB-mScarlet-53BP1; CLO returned no `U2OS` hit.

---

## PXD048347 — Deciphering lineage specification in mouse gastruloids (SCP arm, `_GFP` deposition)

**Blocker: no deposited TMTpro channel → single-cell germ-layer identity map.** Same paper as
PXD041328 (PMID:38754429), but a **different deposition** — different runs (2023-09-20 `CVG_0553 ..._GFP`
vs 2022-12-22 `EXP55`), no file overlap. Investigated independently.

| | |
|---|---|
| Screen hint | multiplexed TMTpro proteoCHIP SCP — mouse gastruloid germ-layer cells (correct) |
| Publication | PMID:38754429 · DOI:10.1016/j.stem.2024.04.017 (Cell Stem Cell) — **not OA**, no PMCID (`inPMC=false`) |
| Organism | *Mus musculus* (NCBITaxon:10090), verified — not the blocker |
| Deposited | 28 RAW (`..._C{1,2,3}_S{n}.raw`, 3 proteoCHIPs) + `CVG_0553_SCP_Gastruloids_GFP.zip` (25.5 GB PD 2.4 output) + `checksum.txt` |
| SDRF would need | 28 files × 18 TMTpro channels = **504 rows**, each with a sample identity |

The **channel roles ARE recoverable** from the (here detailed, unlike PXD041328) `sample_processing_protocol`:
**126 = carrier** (20-cell-equivalent pool of endoderm+ectoderm+mesoderm+unsorted+mESC), **127C = empty**
(left blank), **127N…135N (16 ch) = FACS GFP-sorted germ-layer single cells**. What is missing is
**which germ layer each single-cell channel holds** — the study's only factor.

| source (all zip members read via ZIP64 central-directory range reads; no bulk download) | result |
|---|---|
| `..._StudyInformation.txt` (PD design, 504 rows) | **every `Sample Type = "Sample"`** (generic); id = `<file> - [tag]`; no factor/cell-type columns |
| `..._GFP.pdStudy` (PD study XML) | all **504 `<FactorValues/>` empty**; no populated factor; generic sample names |
| `..._ProteinGroups.txt` header | per-channel cols `Found in Sample F{n} {tag} Sample` — generic **Sample** (PD no-map default) |
| `Proteins_..._FilteredImputed.txt` / `PCA_res.ind_coord.txt` (SCP outputs) | cells keyed only as `F{n}Abundance.{channel}`; trailing `TMT`/`Files` cols are tag+file; **no germ-layer label** |
| `..._InputFiles_forSCP.txt` / `ParametersData.txt` | File→channel list; confirm 126=carrier; **no identity** |
| PRIDE `files/all` (30, all PXD048347-verified) / `checksum.txt` | no sample sheet / channel key |
| Publication | paywalled; Unpaywall/EuropePMC no PDF; no PMCID → no EuropePMC supplementary |

The downstream analysis ("ComBat ... accounting for the different **known cell types**") proves the
authors held a channel→germ-layer annotation, but **it is not deposited**. Every single cell in every
file is equally anonymous, so **no partial annotation is possible**: a subset of only the 28 carrier +
28 empty scaffolding rows would identify 0 of the 448 single cells. Consistent with the PXD041328 and
PXD034370 (U2OS "only carrier recoverable") precedents. Assigning germ layers would be fabrication.

**Unblocked by:** a deposited per-(file × channel) proteoCHIP/cellenONE layout table (which channel =
which germ-layer single cell vs carrier vs empty), the authors' SCP `colData`/sampleAnnotation, a Cell
Stem Cell supplementary channel key, or a re-deposited PD study with real sample names. Given that, rows
are straightforward (TMTpro-18 `UNIMOD:2016`; Orbitrap Eclipse `MS:1003029`; ms-proteomics + vertebrates
+ single-cell; **no Carbamidomethyl** — no reduction/alkylation in the protocol).

---

## PXD064518 — Pro-regenerative adult mouse cardiomyocytes (Analytical dataset, control-vs-Myc factor absent)

TMT-10plex single-cell proteomics of adult mouse cardiomyocytes, wild-type vs Myc-overexpressing
(Marín-Vicente et al., *Genome Biology* 2026, PMC13292336, open access). 81 deposited `..._CNIC-KI_TMT{n}`
raw files. **Channel ROLES are known** from Methods + the pilot's iSanXoT map (130N = empty, 131 =
200-cell booster [100 control + 100 Myc], the other 8 channels = single cardiomyocytes), so a 729-row
SDRF of single mouse cardiomyocytes is technically constructible and validates clean.

**Blocker (per project policy — block when the biological factor is missing):** the study's core
variable, **per-channel control-vs-Myc genotype**, is NOT deposited for these 81 analytical files. A
motivated hunt (the annotator produced a draft SDRF) across six sources — PRIDE `files/all`, the open
paper Methods + supplementary (PMC13292336), Zenodo records 19439667 / 18379944 / 19484833, and Europe
PMC supplementary — found a per-channel genotype map only for the **pilot PXD064499** (`20220323_SST_cnic_SCP_*`
files), never for this dataset. The pilot uses two alternating designs (odd batches = Design A, even =
Design B); extrapolating that to the analytical files is forbidden (layouts flip; the brief bars
assuming a fixed layout). Depositing 729 cardiomyocytes with no control/Myc distinction would be an SDRF
whose only distinguishing axis is `not available`.

**Unblocked by:** a per-channel control/Myc map for the `CNIC-KI_TMT{n}` files (e.g. an iSanXoT
`level_creator.tsv` for the analytical batches, or a supplementary design table), supplied by the
authors. See `annotations/PXD064518.report.md` for the recoverable structural facts. Sibling PXD064499
(pilot) IS annotatable; PXD064501 (FACS) uses disjoint TMT84–97 runs (no overlap).

---

## PXD064501 — Pro-regenerative adult mouse cardiomyocytes (FACS dataset, control-vs-Myc factor absent)

TMT-10plex single-cell proteomics of adult mouse cardiomyocytes, wild-type vs Myc-overexpressing
(Marín-Vicente et al., *Genome Biology* 2026, PMC13292336, open access). The **FACS** deposition
("dataset 2"): 14 `20221019_Ec_01_SC_CNIC-KI_TMT{84,85,87,88,89,90,91,92,93,94,95,96,97,98}` runs
(42 files = 14 raw + 14 mzML + 14 mzid). Same study, same blocker, same decision as **PXD064518**
(analytical set) — recorded separately because it is a distinct deposition with disjoint runs.

**Channel ROLES are known** (paper Methods + the pilot's iSanXoT map): per run, 130N = empty,
131 = 200-cell booster [100 control + 100 Myc], and the other 8 channels = single cardiomyocytes
(4 control + 4 Myc). A **140-row SDRF** (112 single + 14 carrier + 14 empty) is technically constructible
and **validates clean** against `ms-proteomics + vertebrates + single-cell + clinical-metadata`
(`parse_sdrf` exit 0, one run per template).

**Blocker (per project policy — block when the biological factor is missing):** the study's core
variable, **per-channel control-vs-Myc genotype**, is NOT deposited for these 14 FACS files. The two
alternating label designs (Fig. 1c) are described but the per-run A/B assignment for TMT84–98 is never
stated. A motivated hunt across eight sources — PRIDE `files/all`; the open paper Methods +
supplementary (PMC13292336); Zenodo records 19439667 (iSanXoT), 18379944 (complementary), 19484833
(Raw_data_1, incl. `Metaboanalyst_Fig3a.txt` and `median_reporter_ion_intensity_per_TMT.csv`); the
paper GitHub (iSanXoT docs only); and Europe PMC supplementary — found a per-channel genotype
`level_creator.tsv` only for the **pilot PXD064499** (`20220323_SST_cnic_SCP_*`), never for this dataset.
`Fig3a` confirms 4 control + 4 Myc per TMT84–98 run but gives only a within-genotype index, not the
physical channel. Extrapolating the pilot's alternating design to these files is forbidden (layouts flip;
the brief bars assuming a fixed layout). Depositing 112 single cardiomyocytes whose only distinguishing
axis (`genotype`/`factor value`) is `not available` would be an SDRF with no biological factor — matching
`PXD025387` (label randomisation) and `PXD029320` (undeposited per-channel condition map).

**Deliberately not used:** a forensic reconstruction matching the deposited per-scan reporter intensities
to the named Z-values in `Fig3a` could infer each channel's cell, but that is inference from data, not
deposited metadata (the `PXD073250` principle), and would silently assert the factor for 112 rows.

**Unblocked by:** a per-channel control/Myc design table for the `CNIC-KI_TMT{84–98}` files (a 14-row A/B
assignment, an iSanXoT `level_creator.tsv` for the FACS batches, or a re-deposited Proteome Discoverer
study with real sample names), supplied by the authors. See `annotations/PXD064501.report.md` for the
full recoverable structural facts (organism/tissue/cell type/instrument/mods/labels all resolved and
OLS-verified). Sibling PXD064499 (pilot) IS annotated (its map was deposited); PXD064518 (analytical) is
likewise BLOCKED. The three depositions use disjoint runs — no duplication.

---

## PXD041679 — Transcription-coupled DPC repair by CSB and CRL4(CSA) (SILAC Pol II / CSB interaction proteomics)

**Blocker: raw file → MaxQuant experiment (and gel slice) map does not exist.**

| | |
|---|---|
| Publication | van Sluis *et al.*, Nat Cell Biol 2024, PMID:38600236, PMC11098752 (open access, full text read) |
| Deposited | 15 RAW (`2300_L_MarjoleinVanSluis_13april2021_{19..33}`), `2300_proteinGroups.txt`, `2300_parameters.txt` |
| SDRF would need | 15 files × 2 SILAC channels = 30 rows, each with IP target / treatment / cell line |

The deposited `proteinGroups.txt` names **8** MaxQuant experiments whose names encode the channel map,
label swaps included (e.g. `Pol2 Ser2 IP Untreated Heavy vs 300uM FA 45min Light` and its swap; Pol2
untreated vs 16 J UV ×2; `CSB IP WT … vs CSB-KI …` under FA and 30 J UV ×4). Each was searched as up to
10 gel-slice fractions (`Fraction 1..10`), so the 15 deposited files are a subset of the search. Nothing
records which experiment or slice any file is. The paper reports only the two Pol2/FA experiments.

Sources checked, all exhausted: PRIDE record + `files/all`; `parameters.txt` (MaxQuant 1.6, no file
map); `proteinGroups.txt` (experiment names only); Thermo `.raw` headers of all 15 files (sample
name/comment fields empty); paper full text (efetch); Supplementary Tables xlsx (Springer; protein
ratios only); Europe PMC supplementary (endpoint error); Data availability (PRIDE only); paper GitHub
(imaging code; not listable from session); sibling Marteijn-lab PRIDE projects.

**Deliberately not used:** assuming the 15 consecutive runs are the two Pol2/FA lanes, and forensic
per-file H/L inference from spectra. Both would assert treatment/IP identity that no deposited
metadata states.

**Unblocked by:** the MaxQuant `experimentalDesignTemplate.txt` / `mqpar.xml` / `summary.txt` for search
"2300", or an author-supplied file → experiment + slice list. The technical values (SILAC light/heavy,
Lys6 UNIMOD:188 / Arg10 UNIMOD:267, Oxidation/Acetyl/GlyGly variable mods, Orbitrap Fusion Lumos, trypsin,
DDA, 20 ppm MS/MS) are already resolved and OLS-verified in `annotations/PXD041679.report.md`.

---

## PXD027268 — Nuclear-capture of endosomes (SILAC surface and nuclear-capture proteomes), lanes A/B only (partial block)

**Blocker: no channel → condition map exists for MaxQuant lanes A and B. Lanes C and D are annotated in `annotations/PXD027268.sdrf.tsv`.**

| | |
|---|---|
| Publication | Marco *et al.*, Nat Commun 2021 12:6829, PMID:34819513, PMC8613289 (open access, full text read via NCBI efetch) |
| Deposited | 56 RAW, `mqpar.xml`, `MaxQuant_txt_folder.zip` (MaxQuant 1.5.5.1, triple SILAC: light / Arg6Lys4 / Arg10Lys8) |
| Annotated | 28 RAW = lanes C and D of Expt1 and Expt2 (70 rows). Channel map from Supplementary Data 1 and its legend in the Description of Supplementary Files, cross-checked against `proteinGroups.txt` |
| Blocked | 28 RAW = lanes A and B: `20170608_…_Sample_A0[1-8]`, `…_Sample_B0[1-8]`, `2018050x/11_…_Lane_A_00[1-6]`, `…_Lane_B_00[1-6]` (MaxQuant experiments Expt1_A, Expt1_B, Expt2_A, Expt2_B) |
| SDRF would need | 28 files × 3 SILAC channels = 84 rows, each with a condition (HGF / internalisation / reduction arm) |

`proteinGroups.txt` shows all three channels quantified in every A/B lane (e.g. Expt2_A: L 6.9e11, M 2.3e11, H 5.3e11), so these are real triple-SILAC samples. The external reviewer measured H/L correlations of 0.21–0.73 among the four lanes, so they are not interchangeable replicates of one design. Nothing records which condition is in which channel.

Sources checked, all exhausted:

| source | result |
|---|---|
| Paper Methods / Results / figure legends | describe only the surface (lane D) and nuclear-capture (lane C) experiments |
| Supplementary Data 1 (`MOESM4_ESM.xlsx`) | columns only for Expt1_C, Expt2_C, Expt1_D |
| Description of Supplementary Files (`MOESM3_ESM.docx`) | legends for sheets 1–2 only (nuclear L/H, surface L/H) |
| Supplementary Data 2 / 3, Source Data, Supplementary Information, Peer Review File | TurboID LFQ, RNA-seq, figure source values; nothing on lanes A/B |
| PRIDE sample/data processing protocols, `files/all` | protocol prose only (2-state), no sample sheet |
| MaxQuant `mqpar.xml`, `parameters.txt`, `summary.txt`, `proteinGroups.txt` | experiment names `Expt1_A`… only |
| Data Availability | "available from the corresponding author on request"; no Zenodo/figshare/GitHub deposit (only GEO GSE179901 and PXD027217, both unrelated to these lanes) |

**Deliberately not used:** inferring A/B conditions from ratio patterns or from the letter codes A/B/C that Supplementary Data 1 uses for *conditions* within lane C. Both would assert condition identities that no source states.

**Unblocked by:** a lane A/B channel → condition map from the corresponding author (J.C. Norman, CRUK Beatson Institute). The technical values (Q Exactive HF, SILAC mods UNIMOD:188/481/267/259, Carbamidomethyl fixed, 4.5/20 ppm) are already resolved in `annotations/PXD027268.report.md`. Adding the lanes means adding rows to `samples.tsv` and rebuilding.

---

## PXD026077 — Mitochondrial retrograde signaling in yeast colonies (label-free, mis-tagged SILAC)

**Blocker: no raw file → sample (strain / cell type / phase / replicate) map exists.**

| | |
|---|---|
| Publication | Plocek *et al.*, Int J Mol Sci 2021 22:5597, PMID:34070491, PMC8198273 (CC BY, full text read via NCBI efetch) |
| Deposited | 60 RAW (`437-1…437-30`, `452-31…452-60`), `mqpar.xml`, `2019_10_03_mqpar.xml`, `txt.7z`, `2019_10_03_txt.7z` (MaxQuant 1.6.3.4) |
| SDRF would need | 60 label-free rows = 5 strains (wt, rtg1Δ, mks1Δ, rtg1Δmks1Δ, rtg2Δmks1Δ) × U/L cells × acidic/alkali phase × 3 replicates |

Not SILAC despite PRIDE `quantificationMethods`: both mqpar.xml have multiplicity 1, no label mods, LFQ on;
`summary.txt` Multiplicity 1; `proteinGroups.txt` has only LFQ columns. The paper never mentions SILAC.

Sources checked, all exhausted:

| source | result |
|---|---|
| PRIDE record + `files/all` | design prose only; no sample sheet |
| `mqpar.xml` ×2 | `<experiments>` all empty |
| `txt.7z` ×2 (stored members range-read) | `summary.txt` Experiment = run number 1…60; `parameters.txt`, mzTab `metadataSection.txt`, `proteinGroups*.txt` (incl. `_palkova`, `_palkova_`) name experiments by number only |
| Thermo `.raw` headers, all 60 | sample name/ID/comment empty; vial + method + folder only |
| Paper Methods / legends | design and counts only |
| Supplementary zip (PMC open-data S3; MDPI 403, Europe PMC endpoint refused) | Tables S1–S3: group-level ratios; S4: primers; Figs S1–S3: blots |
| Data Availability | PRIDE only |

**Deliberately not used:** the period-10 LFQ structure in the 452 search (e.g. Rtg2 = 0 at runs 40/50/60) to
infer strain and U/L per run. Mks1 is never quantified and Rtg1 only at trace, so genotype is not recoverable,
and U/L / phase assignment would rest on the biology the study tests (campaign rules 6–8).

**Unblocked by:** an author list mapping run numbers 1–60 to strain, cell type, phase and replicate
(K. Harant, BIOCEV OMICS core; Z. Palková, Charles University). Technical values (Orbitrap Fusion, HCD/ion-trap
MS2, DDA, trypsin, Carbamidomethyl fixed + Oxidation/Acetyl(Protein N-term) variable, 20/4.5 ppm, 0.5 Da) are
resolved and OLS-verified in `annotations/PXD026077.report.md`.

---

## PXD017487 — DGAT1 phosphoproteome and long-term proteome (SILAC A375), phosphoproteome arm only (partial block)

**Blocker: the deposited phosphoproteome is triple SILAC, but the only stated map is two-channel. The heavy time point conflicts between sources, and the stated orientation fails the data check. The long-term proteome (DMSO vs A922500 72 h) is annotated in `annotations/PXD017487.sdrf.tsv`.**

| | |
|---|---|
| Publications | Wilcock *et al.*, Cell Rep 2022 39:110995, PMID:35732120, PMC9638004 (full text via Europe PMC fullTextXML). bioRxiv preprint doi:10.1101/2020.06.23.166603 v1 (53-page PDF via `get_pdf_by_unpaywall`, read in full) |
| Deposited | 30 RAW, `parameters*.txt`, `experimentalDesignTemplate*.txt`, `proteinGroups*.txt`, `PhosphoSTYSites.txt` (MaxQuant 1.6.2.6) |
| Annotated | 24 RAW `20190618_CF_COLLAB_Dan_A375_SILAC_0_72_PRO_0[1-3]_0[1-8].raw` (48 rows; light = DMSO, heavy = A922500 72 h, stated in preprint Fig. 6A) |
| Blocked | 6 RAW `20190618_CF_COLLAB_Dan_A375_SILAC_0_30_120_STY_0[1-3]_0[1-2].raw` (MaxQuant experiments STY_01..03; the companion `0_30_120_PRO` runs used in that search were never deposited) |
| SDRF would need | 6 files × 3 SILAC channels = 18 rows, each with a treatment and time. Labels per `summary_ST.txt` in the authors' GitHub repo: L = Arg0/Lys0, M = Arg6;Lys4, H = Arg10;Lys8 |

**What is stated.** Preprint lines 229–231: "phosphorylated peptides from SILAC-labelled DGAT1high A375 melanoma cells following 4h treatment with A922500". The preprint Fig. 3A workflow shows a two-dish design: A375 Light = DMSO, Heavy = A922500, 4h → QE-HF → MaxQuant. The Data Availability names PXD017487. So the agent is known: A922500.

**Why the arm is still blocked:**

1. **The medium channel is undocumented.** The deposit is triple SILAC (`summary_ST.txt` Multiplicity 3, Labels1 = Arg6;Lys4). No text or figure in the paper or the preprint mentions a medium channel. Its only trace is the authors' code variable `STY_30m` (`2_PhosphoSTYSites_extraction-QC.R:74`).
2. **The time points conflict.** The file names say `0_30_120` (heavy = 120 min). The preprint text, Fig. 3A and the code (`STY_4h`) say 4 h.
3. **The stated map fails the data check (rule 6).** If heavy = A922500, pS6 should fall: the preprint reports rapid loss of pS6 within 2–4 h of A922500 (lines 235–238, Fig. 3B). Instead `Phospho (STY)Sites.txt` shows RPS6 heavy/light (normalized) rising in all 3 experiments:
   - S235: 1.42 / 1.55 / 1.49
   - S236: 2.17 / 2.29 / 2.02

   Medium/light is 0.88–1.18. Either the orientation is reversed or a different design was run, so the stated map cannot be trusted for these files.

**Deliberately not used:**
- Assigning the medium channel from the code name `STY_30m`.
- Flipping the heavy/light orientation to fit the pS6 data.

Both would assert channel identities that no source states (campaign rules 6–8).

**Unblocked by:** author confirmation of the medium (Arg6/Lys4) channel's condition and of the light/heavy orientation and time points of the STY runs. Contacts: C. Francavilla / M.P. Smith / A. Hurlstone, Manchester. All technical values (Q Exactive HF, variable Phospho (STY) + Gln->pyro-Glu, no Deamidation, labels Arg6/Lys4/Arg10/Lys8) are resolved in `annotations/PXD017487.report.md`.

---

## PXD027138 — RBM20 BioID (qRIC paper), whole dataset (8 RAW)

**Blocker: no reachable source names the SILAC label (L/M/H) of each condition, in either arm or either label-swap orientation. Only the uninduced channel can be anchored, by its low RBM20 bait level, which fixes 1 of 3 channels in experiment 1 and none in experiment 2. No SDRF is deposited.**

| | |
|---|---|
| Publication | Vieira-Vieira *et al.*, Mol Cell 2022 82:2069, PMID:35427468, doi:10.1016/j.molcel.2022.03.024 (not in PMC; bronze OA at the publisher, but unreadable here) |
| Deposited | 8 RAW files (Orbitrap Exploris 480 + FAIMS), plus `txt.zip` (MaxQuant 1.6.0.1: mqpar.xml, parameters.txt, proteinGroups.txt, with Requantify on and off) |
| Blocked | `Elmo_20210223_CV_HS_FAIMS_{Input,BioID}_RBM20ctl_{Forward,Reverse}.raw` (experiment 1: uninduced WT / S635A / induced WT); `..._Input_RBM20mut1_{Forward,Reverse}.raw`, `..._BioID_RBM20mut2_Forward.raw`, `..._BioID_RBM20mut2_Reverse_20210225171853.raw` (experiment 2: WT / A10 / D10) |
| SDRF would need | 8 files × 3 SILAC channels = 24 rows. L = Lys0/Arg0, M = Lys4/Arg6, H = Lys8/Arg10 (per mqpar) |

**What the PRIDE protocol says.** It lists each arm's conditions:
- experiment 1: "uninduced WT, S635A mutant and induced WT";
- experiment 2: "WT, A10 and D10";
- Forward/Reverse is a "label swap".

It never says which label each condition carries.

**What the data show.** Comparing Forward and Reverse ratios across the proteome favours a cyclic shift between the orientations, not a plain L↔H swap:
- the Forward light sample is in Reverse heavy;
- the Forward medium sample is in Reverse light;
- the Forward heavy sample is in Reverse medium.

This is an inference, not a label statement. Only the uninduced channel is anchored: RBM20 is 10–45× lower in Forward light and in Reverse heavy.

Sources checked:

| source | result |
|---|---|
| PRIDE PXD027138 protocol, description, files/all | conditions listed, no label per condition |
| MaxQuant mqpar.xml, parameters.txt, experimentalDesignTemplate.txt, proteinGroups.txt headers | experiment names only, no condition names |
| Paper (Cell Press / ScienceDirect) | HTTP 403 |
| bioRxiv preprint 10.1101/2021.07.12.452044 (direct, WebFetch, MCP get_pdf_by_unpaywall) | HTTP 429 on every attempt (about 25 min) |
| Europe PMC PPR368916 fullTextXML | HTTP 500 |
| Mendeley Data tcggv58kjk, n938bchmv2, d5h73x6xst, sp3xdygfxj, bdx89nn3tp | imaging data only. The method text gives the cell line (Flp-In T-REx HEK293, tetracycline-induced), no SILAC labels |
| Sibling PRIDE projects PXD027137 / PXD030352 | qRIC experiments, no BioID label map |
| MDC edoc eprint 21563 | metadata only, no full text |

**Deliberately not used** (campaign rules 6–7):
- the order of the PRIDE list;
- the cytoplasmic RNP-granule proximity signature;
- the data-derived cyclic map.

The first external review (`annotations/PXD027138.review.md`) failed an earlier SDRF that relied on these. That SDRF has been withdrawn.

**Unblocked by:** the paper's STAR Methods or figure legends (BioID section), or a label sheet from the authors (C.H. Vieira-Vieira, M. Selbach, MDC Berlin), giving the channel map for each orientation. The technical values are resolved in `annotations/PXD027138.report.md`.

## PXD010779 — Metastatic lung adenocarcinoma proteogenomics (super-SILAC + TMT10plex), TMT10plex arm only (partial block)

**Blocker: the TMT10plex channel→sample map is only partly published. Two of ten channels are stated (TMT126 = pool of all nine tumors, TMT128C = PDX). Which of 127N, 127C, 128N, 129N, 129C, 130N, 130C and 131N carries LN1, Lung, LN2 and MET1–5 is not in any source reachable here. The super-SILAC arm (72 RAW) is annotated in `annotations/PXD010779.sdrf.tsv`.**

| | |
|---|---|
| Publication | Zhang *et al.*, Mol Cell Proteomics 2019 18:622, PMID:30617155, PMC6442362, doi:10.1074/mcp.RA118.001266 (full text read from the PMC HTML render) |
| Deposited | 96 RAW: 72 super-SILAC (annotated) + 24 TMT. 26 non-RAW, not runs: 23 MaxQuant search outputs (super-SILAC and 4 TMT searches, patient DB ± mouse DB: mqpar.xml, parameters.txt, proteinGroups/peptides/PhosphoSTYSites, experimentalDesignTemplate); `SupplementaryMRMresults_mutantpeptides.zip` (targeted MRM results behind PRIDE's SRM/MRM experiment type; no MRM RAW deposited); `SupplementarypSTannotatedspectra.zip` and `Supplementary_snvs2_repor-high.zip` (annotated spectra) |
| Blocked | `patient_TMT10plex_protein_F1–F12.raw` (proteome) and `patient_TMT10plex_pST_F1–F12.raw` (TiO2 phosphopeptides): 24 files |
| SDRF would need | 24 files × 10 TMT channels = 240 rows; 126 = pooled reference, 128C = PDX (from a left jugular / right axillary lymph node excision, 9/2014), and the other 8 channels = LN1, Lung, LN2, MET1–5 in an unknown order |

Sources checked:

| source | result |
|---|---|
| Paper text (Methods, Results, Experimental Design, figure legends) | only "labeled with TMT10–126" (pool) and "PDX sample (channel 128C)" |
| PRIDE protocol, description, files/all | same two statements; no sample sheet |
| TMT mqpar.xml ×4 | `<experiments>` empty; isobaric labels only, no sample names |
| TMT proteinGroups.txt header | `Reporter intensity [corrected] 0–9` only |
| TMT RAW headers (`patient_TMT10plex_protein_F1.raw`, `patient_TMT10plex_pST_F1.raw`, HTTP range read) | file paths and method `top15HCD_90min_10uL_TMT_HCD40.meth` only; no channel or sample names |
| bioRxiv preprint 10.1101/398313 (same title, 2018-08-22) | API record resolves; supplementary-material page lists no files; full-text PDF HTTP 429 |
| Supplementary Tables S1–S5 (PMC `bin/142441_1_supp_*.xlsx`) | NCBI proof-of-work bot check, not bypassed |
| Europe PMC supplementaryFiles | "not open access" |
| Publisher (mcponline.org / linkinghub) | HTTP 403 |

**Deliberately not used:** inferring the channel order from correlation with the super-SILAC ratios (that would place only LN1/Lung/LN2, and it is inference, not a label statement; campaign rule 6) or from the heatmap column order in Fig. 5A.

**Unblocked by:** supplementary Table S3 (TMT proteome) or S2/S4 column headers, which very probably name each channel's sample, or a channel sheet from the authors (X. Zhang, U. Guha, NCI). The technical values for the TMT arm (same Orbitrap Elite, MaxQuant isobaric labels TMT10plex-Nter and -Lys 126C–131N, variable Oxidation (M), Acetyl (Protein N-term) and Phospho (STY) per the mqpar files) are already established and would need only the map.

## PXD010683 — Nestin / vemurafenib resistance in A375 melanoma (SILAC + dimethyl FFPE), screen 1 and FFPE arms only (partial block)

**Blockers:**
- **Screen 1 (33 runs):** no explicit channel map exists. The deposited MaxQuant experiment names (all "ML") contradict the deposited ratios.
- **FFPE (2 runs):** the label state of the deposited runs and the per-patient clinical data are undocumented.

The screen-2 duplex (90 RAW) and the Nes-KO/S/R triplex (20 RAW) are annotated in `annotations/PXD010683.sdrf.tsv`.

| | |
|---|---|
| Publication | Schmitt *et al.*, Mol Cell Proteomics 2019 18:1096, PMID:30890564, PMC6553926, doi:10.1074/mcp.RA119.001302 (full text read from the PMC HTML render) |
| Blocked: screen 1 | `20150812_A375SR_Phospho_BR1_01-10`, `20150814_A375SR_Phospho_BR2_01-10`, `20150822_A375SR_Phospho_BR3_01-10`, `20150818_A375SR_Proteome_BR1`, `20150818_A375SR_Proteome_BR2`, `20150822_A375SR_Proteome_BR3` (33 files; A375 S vs R SILAC light/medium) |
| Blocked: FFPE | `20181129_MaS_meltissue_preBRAFi_FFPE_01`, `20181129_MaS_meltissue_postBRAFi_FFPE_01` (2 files; one patient before and after BRAFi; dimethyl light/heavy) |

**Screen 1: what the data show.** Orientation from per-raw-file ratios on 207 marker groups, and from nestin:

| run set | S channel implied by the ratios |
|---|---|
| Proteome_BR1 | medium |
| Proteome_BR2, Proteome_BR3 | light |
| Phospho_BR1 | light |
| Phospho_BR2, Phospho_BR3 | medium |

All six experiments are named "ML" in `txt_A375_S_R/experimentalDesignTemplate.txt`. The paper says only "light, medium and vice versa".

**FFPE: what is deposited.** `txt_FFPE_pre_post_tissue` searched `20181211_MaS_prepostBRAfi_dimethyl_LH_1ug`, a mixed light/heavy run that is not deposited. Patient details are in Supplementary Information S3.

Sources checked:

| source | result |
|---|---|
| Paper text (PMC HTML) | label-swap design stated without per-replicate assignment; FFPE pre/post labelled light/heavy in the mixed run only |
| PRIDE protocol, files/all | no sample sheet |
| MaxQuant zips (experimentalDesignTemplate, summary, mqpar, proteinGroups, evidence) | as above |
| Supplementary Information S1/S3, Supplementary Figures (PMC `bin/142829_1_supp_*`) | NCBI bot check |
| Europe PMC supplementaryFiles | empty archive |
| mcponline / Unpaywall PDF | HTTP 403 |

**Deliberately not used:** the data-derived screen-1 orientation (rules 6/7), and a label-free reading of the FFPE runs.

**Unblocked by:**
- Supplementary Fig. S1A or Information S1, or an author label sheet (M. Schmitt / B. Macek, Proteome Center Tuebingen), giving the screen-1 S/R channel per replicate and per proteome/phospho run.
- Supplementary Information S3 plus the authors' statement of whether the deposited FFPE runs were labelled. Annotating the FFPE runs would also need the `clinical-metadata` template in a separate SDRF part.

---

## PXD064152 — NSD2 / HPV E6/E7 in HPV-associated head and neck cancer (histone super-SILAC), FFPE arm only (partial block)

**Blocker: no source keys the FFPE raw files to HPV status or patient.** The cell-line arm (15 runs) and the keratinocyte arm (6 runs) are annotated in `PXD064152-celllines.sdrf.tsv` and `PXD064152-keratinocytes.sdrf.tsv`. The FFPE arm (22 runs) is not annotated. Its study factor, HPV+ vs HPV− oropharyngeal SCC (Fig. 1A), is also a per-patient clinical value. It needs an individual-level source (rule 18), and none exists.

Blocked runs (22 `.raw`, all present in PRIDE files/all):
- HF220822_RN_Lavinia_FFPE_2T
- HF220822_RN_Lavinia_FFPE_7T
- HF220822_RN_Lavinia_FFPE_9T
- HF220822_RN_Lavinia_FFPE_12T
- HF220822_RN_Lavinia_FFPE_14T
- HF220822_RN_Lavinia_FFPE_15T
- HF220822_RN_Lavinia_FFPE_17T
- HF220822_RN_Lavinia_FFPE_21T
- HF220822_RN_Lavinia_FFPE_22T
- HF220822_RN_Lavinia_FFPE_26T
- QEP230822_RN_Lavinia_2T
- QEP230822_RN_Lavinia_3
- QEP230822_RN_Lavinia_4
- QEP230822_RN_Lavinia_5
- QEP230822_RN_Lavinia_6
- QEP230822_RN_Lavinia_7
- QEP230822_RN_Lavinia_10
- QEP230822_RN_Lavinia_13
- QEP230822_RN_Lavinia_14
- QEP230822_RN_Lavinia_15T
- QEP230822_RN_Lavinia_17
- QEP230822_RN_Lavinia_18T

Sources checked:

| source | result |
|---|---|
| PRIDE project record (v3) | protocol prose only; no per-sample HPV status; `diseases` empty |
| PRIDE files/all (48 files) | `Sample_list.txt` is the only sample sheet |
| `Sample_list.txt` | 29 "FFPE tissue" entries in two unlabelled blocks (#1–#10, then #1–#19); no HPV, patient or clinical field. Only 3 of the 10 block-A entries have a deposited raw |
| Paper PMC12882316 (CC BY, full text) | cohort: 19 HPV+ and 9 HPV− OPSCC; no file or sample key |
| Supplementary Tables (MOESM1, Table S4) | cohort-level counts only (sex, histology, grade, pT, pN, stage per HPV group) |
| Supplementary Data (MOESM2, sheet 1) | L/H ratios with columns HPV− #1–#9 and HPV+ #1–#19; no file names |
| EpiProfile outputs (FFPE2208.zip, FFPE2308.zip: `histone_ratios_SILAC.xls`, `histone_ratios.xls`, `histone_logs.txt`) | keyed by raw file name only; no HPV or patient field |
| MOESM3 (figure legends), MOESM4–9 (figure TIFFs) | no sample key |
| GEO GSE313615 (linked RNA-seq) | not fetched: paper Methods say the RNA-seq covers HKs and HNSCC cell lines only, not the FFPE MS samples |

**Deliberately not used:**
- Matching recomputed L/H %RA ratios against Supplementary Data columns. The producer's map (block A = HPV−, block B = HPV+) was not reproduced by the reviewer's independent recomputation: for example, supp HPV+ #4 best-matches a block-A file, and HPV+ #12 and #13 and HPV− #5 and #7 move between blocks. The method is too sensitive to serve as a documented map.
- FFPE_15T could not be placed in any supp column.
- The sample list's HPV− block has 10 entries against the paper's 9.

**Unblocked by:** an explicit file → HPV-status (and ideally patient-ID) key from the submitters (R. Noberini / T. Bonaldi, IEO), for example an updated `Sample_list.txt` with an HPV column, or the mapping of Supplementary Data sheet 1 columns (HPV± #n) to raw file names. That key must also state whether FFPE_15T is in the published set. The technical values are already settled and are in `PXD064152.report.md`.

## PXD012000 — Breast cancer neoadjuvant treatment proteomics (super-SILAC FFPE), experiments 27C and 32D only (partial block)

**Blocker: 9 of 689 RAW belong to two MaxQuant experiments, `27C` and `32D`, that are not among the paper's 113 samples. Their sample identity is undocumented. The other 680 RAW (113 samples × light/heavy = 1360 rows) are annotated in `annotations/PXD012000.sdrf.tsv`.**

| | |
|---|---|
| Publication | Shenoy *et al.*, Mol Syst Biol 2020 16:e9443, PMID:32960509, PMC7507992, doi:10.15252/msb.20209443 (open access; full text and Datasets EV1–EV5 read) |
| Deposited | 689 RAW + `combined_NAT.zip` (MaxQuant 1.5.5.1 combined folder; `experimentalDesignTemplate.txt`, `txt/summary.txt`, `txt/parameters.txt` were HTTP-range read) |
| Blocked | `20160706_ASK_CS_32D1–32D7.raw` (experiment 32D; searched) and `20160706_ASK_CS_27C6.raw`, `20160706_ASK_CS_27C7.raw` (experiment 27C; in the design but not in summary.txt, so not searched) |
| SDRF would need | 9 files × 2 SILAC channels = 18 rows, with a sample identity for the light channel |

Sources checked:

| source | result |
|---|---|
| Dataset EV2 legend | defines only A = pre-treatment biopsy, B = post-treatment residual tumour, C = post-treatment adjacent normal, and C34–38 = healthy. No D type, no "27C" (patient 27 is split into 27a/27b, bilateral) |
| Dataset EV2–EV5 column headers | 113 samples; no 32D or 27C column |
| Dataset EV1 | patient 32 has only "32A,32B,32C"; patient 27 has "27aA,27aB,27aC" and "27bA,27bB,27bC" |
| Paper text, Appendix, Review Process File | no mention of a fourth sample type or of 27C |
| MaxQuant design / summary | 32D = 7 SCX fractions, searched; 27C = fractions 6–7 only, not searched |

**Deliberately not used:** assigning 27C6/27C7 as the missing fractions 6–7 of 27aC (which has only fractions 1–5). It is plausible, but no source states it, and MaxQuant kept 27C as a separate experiment.

**Unblocked by:** a statement from the submitters (T. Geiger lab, Tel Aviv University) of what 32D is (for example a re-extraction of 32C or a fourth specimen) and which sample 27C belongs to.

## PXD003316 — Tumour matrix stiffness / CCN1 in HUVECs (SILAC), MitoC arm only (partial block)

**Blocker: 36 of 132 RAW belong to two MaxQuant experiments, `C_MitoC_Fwd` and `D_MitoC_Rev`. No source describes them, so their treatment and their SILAC channel→condition map are undocumented. The other 96 RAW (stiffness Prolif Fwd/Rev, siCCN1 spike-in, Matrigel spike-in; 192 rows) are annotated in `annotations/PXD003316.sdrf.tsv`.**

| | |
|---|---|
| Publication | Reid *et al.*, EMBO J 2017 36:2373, PMID:28694244, PMC5556271, doi:10.15252/embj.201694912 (full text via NCBI efetch; Appendix, Datasets EV1–EV3 and Review Process File from the PMC OA bucket) |
| Deposited | 132 RAW + `txtstiffness.zip`, `txtsiCCN1.zip`, `txtMatrigel.zip` (MaxQuant 1.4.1.x; experimentalDesignTemplate, parameters, summary and proteinGroups were HTTP-range read) |
| Blocked | `20140715_Elite_StRe_STIFF_Prot_MitoC_Fwd_C1–C18.raw`, `20140715_Elite_StRe_STIFF_Prot_MitoC_Rev_D1–D18.raw` (18 gel slices each; searched together with the Prolif runs in `txtstiffness.zip`) |
| SDRF would need | 36 files × 2 SILAC channels = 72 rows, with the treatment ("MitoC") and the substrate stiffness of each channel |

Sources checked:

| source | result |
|---|---|
| Paper text and Methods | only one stiffness proteome is described (400 Pa vs 22,000 Pa, forward + reverse); the strings "mitomycin" and "MitoC" do not occur |
| Appendix (Supplementary Methods), Review Process File | no mention of mitomycin or a second stiffness experiment |
| Dataset EV1 "Stiffness proteome" | columns "22/0.4 KPa Fwd/Rev"; their per-channel intensities equal MaxQuant `A_Prolif_Fwd` / `B_Prolif_Rev` exactly (5,804 / 5,791 protein groups). They match `C_MitoC`/`D_MitoC` for 3 or fewer |
| Datasets EV2, EV3 | stiffness values re-used from EV1; siCCN1 only |
| PRIDE project record (protocols, description) | stiffness forward/reverse, siCCN1 and Matrigel only |
| Europe PMC search "PXD003316" | only this paper |
| MaxQuant proteinGroups | CYR61 normalized H/L: Prolif Fwd 2.33 / Rev 0.58; MitoC Fwd 1.36 / Rev 1.00. Ratios exist, but there is no label statement |

**Deliberately not used:** assuming the MitoC runs follow the Prolif layout (Fwd heavy = 22 kPa) and that "MitoC" means mitomycin C treatment. Both are plausible, but neither is stated, and the weaker CYR61 response does not confirm the orientation.

**Unblocked by:** a statement from the submitters (S. Zanivan lab, CRUK Beatson Institute) of what "MitoC" denotes (agent, dose, timing) and the stiffness assigned to the heavy and light channels of the MitoC_Fwd and MitoC_Rev mixtures.

---

## PXD027175 — Mitochondrial one-carbon flux / methotrexate in MDA-MB-468 (SILAC), KO arm only (partial block)

**Blocker: the KO/SCR SILAC design is not described anywhere, and the only stated channel map (light = 50 nM MTX, heavy = control) fails the data check for every KO experiment. The SCR arm (26 RAW, 52 rows) is annotated in `annotations/PXD027175.sdrf.tsv`.**

| | |
|---|---|
| Publication | Kiweler *et al.*, Nat Commun 2022 13:2699, PMID:35577770, PMC9110368 (full text via NCBI efetch; supplementary MOESM1/MOESM3 via PMC OA S3) |
| Deposited | 54 RAW, `proteinGroups.txt`, `peptides.txt` (MaxQuant 1.6.7.0). No summary.txt / mqpar.xml / experimental design |
| Run → sample map | RAW headers (range read): sample names `MDB468_SCR_*`, `MDB468_KO_*`, `KO_*` = MaxQuant experiment names |
| Annotated | 26 RAW `MDB468_SCR_*` (normal, TreatSwap, Ctrl): stated orientation + data agree |
| Blocked | 28 RAW: QHF_00014373-14375, 14378-14383, 14393, 14394, 14397, 14398, 14403-14406, 14411-14414, 14503-14506, 14508-14510 (MaxQuant experiments MB468_KO_{6,24,48,72}h-b-t, MB468_KO_Ctrl-1..3, MB468_KO_TreatSwap_*; KO_48h-1-2 has two raws, 14380 and rerun 14503) |
| SDRF would need | 28 files × 2 SILAC channels = 56 rows, each with treatment, time and genotype |

**What is stated:** the PRIDE protocol and paper Methods give one design only: light = 50 nM MTX for 24 h and 72 h, heavy = control. Neither mentions KO cells, SCR cells, a label swap or a Ctrl mix in the proteomics. The paper's KO lines are an MTHFD2 CRISPR KO (scramble gRNA control) and an MTHFD1L KO (from the Cantley lab).

**Why the arm is blocked.** Data check: median-centred log2 H/L from proteinGroups.txt, using the MTX targets the paper names.

| Experiments | DHFR | TYMS | SOD2 | Reading |
|---|---|---|---|---|
| SCR normal (16) | −0.4..−3.1 | 0..−1.5 | −0.5..−1.8 | light = MTX ✔ stated |
| SCR TreatSwap (8) | +0.9..+2.8 | +0.9..+1.2 | +0.2..+1.7 | heavy = MTX ✔ swap |
| **KO normal (16)** | **+0.1..+2.6** | **+0.2..+1.1** | **+0.4..+1.8** | heavy = MTX ✘ contradicts stated map |
| **KO TreatSwap (8)** | **−0.4..−3.3** | **−1.1..−2.1** | **−0.2..−0.7** | light = MTX ✘ |
| KO Ctrl (3) | n/a / −0.38 | −0.4..−0.6 | +0.4..+0.5 | not flat (TK1 −1.0..−1.8), unlike SCR Ctrl (~0) |

MTHFD2 is lower in the heavy channel in 22 of the 25 quantified KO experiments, whatever the treatment. The channels may therefore differ in genotype as well as treatment.

**Deliberately not used:**
- Flipping the orientation of the KO arm to fit the MTX signature.
- Assigning a genotype (MTHFD2 KO vs SCR/parental) per channel from the MTHFD2 ratios.

Both would assert identities that no source states (rules 6–8).

**Unblocked by:** author confirmation (G. Dittmar / J. Meiser, LIH) of:
- the KO arm's light/heavy orientation;
- the genotype of each channel;
- which gene was knocked out;
- what the KO_Ctrl mix compares;
- whether QHF_00014380 or QHF_00014503 was searched as KO_48h-1-2.

All technical values are already resolved in `annotations/PXD027175.report.md`.

---

## PXD018305 — Amino acid variants / BRAFi resistance in A375 melanoma (label-free + SILAC RUNX1 IP), SILAC IP arm only (partial block)

**Blocker: the SILAC channel map of the RUNX1 immunoprecipitation runs is contradictory across sources and the data.** The deposited third IP run also does not match the published replicate 3.

The label-free S-vs-R screen (114 RAW) and the label-free synthetic-peptide pulldown (12 RAW) are annotated in `annotations/PXD018305.sdrf.tsv`.

| | |
|---|---|
| Publication | Schmitt *et al.*, Mol Cell Proteomics 2021 20:100163, PMID:34673281, PMC8603206, doi:10.1016/j.mcpro.2021.100163 (full text, supplementary methods mmc1 and Table S3 mmc4 read) |
| Blocked | `20190719_MaS_KB_OE_Runx1_R1`, `20190719_MaS_KB_OE_Runx1_R2`, `20190514_MaS_RUNX1_IP_02` (3 files, Q Exactive HF-X; MaxQuant `RUNX1_OE` multiplicity 3: light / Arg6;Lys4 / Arg10;Lys8; experiments IP_RUNX1_01/02/03) |
| Design | Flag-IP in A375 S RUNX1_KO cells transfected with pCMV_Flag_RUNX1 (wt), pCMV_Flag_RUNX1_S276L or empty pCMV_Flag; one mixed triplex per replicate |

**What each source says:**

| source | channel map |
|---|---|
| Paper Experimental Design + PRIDE protocol | wt, S276L, empty listed, then ("light":"medium":"heavy") |
| Supplementary methods (mmc1) | same list, no channel assignment |
| Table S3.1 header block (mmc4) | Flag empty = Light (BR1-3); RUNX1_S276L = Medium / **Heavy** / Medium; RUNX1_wt = Heavy / **Medium** / Heavy (BR1/BR2/BR3) |
| Deposited data: RUNX1 protein | lowest in light (IP_01 L/M/H 0.69/0.89/2.71e9; IP_02 1.06/1.62/2.15e9). This refutes empty = heavy and supports Table S3.1 for light. |
| Deposited data: S276L-only peptide `…HPATPILPGR` | only in IP_RUNX1_02 (= Table BR2), quantified in **Medium** (M 2.29e6, H 0.62e6, L 0; score 39.3, PEP 0.043). Table S3.1 says S276L = Heavy in BR2. |
| HDAC1 (paper: enriched with wt, depleted with S276L), Table BR1 | log2 M/L 1.29 > H/L 0.60, so wt looks like Medium in BR1. Table S3.1 says Heavy. |
| Authors' averaged `wt_emp` column (Table S3.1) | best reproduced by wt = M/H/M (r 0.88), the inverse of the stated block |
| Replicate 3 | Table S3.2 BR3 quantifies 1848 peptides. The deposited `20190514_MaS_RUNX1_IP_02` (5% MS/MS identified) quantifies 377, with 232 shared; BR1/BR2 vs their deposited runs share ~83% (log2 r 0.97/0.94). Table BR3 is most likely an undeposited run. |

The explicit statement (Table S3.1) and every data check disagree on the medium/heavy assignment. The data signals are individually weak but all point the same way, and replicate 3 cannot be tied to the deposit. Annotating would mean choosing the wt vs S276L identity of 6 channel rows against one source or the other (batch rules 6/7).

Sources checked: paper (PMC HTML), PRIDE protocol, `files/all` (no sample sheet), `RUNX1_OE_txt.zip` (summary, parameters, experimentalDesignTemplate, proteinGroups, peptides, evidence), `RUNX1_OE_mqpar_fasta.zip` (mqpar, FASTA with RUNX1 wt / S276L / Flag entries), PMC OA supplementary mmc1-mmc4. Analysis files are in the PXD018305 scratch dir (`runx1_*.txt`).

**Unblocked by:** the authors confirming the per-replicate L/M/H assignment of the three IP runs and which raw file is replicate 3, or a re-deposition of the BR3 run. If they confirm Table S3.1 for `_R1`/`_R2`, those two runs (6 rows) can be added as a separate `PXD018305-silac.sdrf.tsv` (rule 12).

---

## PXD031662 — RAS and SLC3A2 signaling in multiple myeloma (BioID2-SILAC + phospho SILAC/TMT), 8 BioID2 experiments, the mis-named 136_L6 runs (= exp 140) and the TMT arm (partial block)

| | |
|---|---|
| Publication | Yang Y *et al.*, Nat Commun 2022 13:5469, PMID:36115844, PMC9482638, doi:10.1038/s41467-022-33142-x (full text, Supplementary Figures and Source Data xlsx read) |
| Annotated | 85 raws (BioID2-SLC3A2 experiments 139, 983, 984 and phospho SILAC 96/96B) → `PXD031662.sdrf.tsv`, 255 rows |
| Blocked (deposited "136" = exp 140) | 23 raws: `TO_R_Young_190220_110320_HFPlus_136_L6_1-23` (Q Exactive HF). By Thermo RunHeader last-scan number they are MaxQuant_136_139 experiment **140** (e.g. fractions 1/2/7: 32624/33345/33984 = MS+MS/MS of `140_L6_1/2/7`). Experiment 140 is in neither `File_assignment.txt` nor the paper Source Data (it does not reproduce Fig. 3a L363). The L-363 experiment 136 that `File_assignment.txt` and Fig. 3a describe was searched from `TO_R_Young_190220_060320_HFPlus_136_L2_*` (fraction 1 = 33074 scans), and those raws were **never deposited**. |
| Blocked (BioID2-SILAC) | 183 raws: experiments 341 (`TO_R_Young_110618_240818_L6_341_2-23`), 350 (`R_Young_260618_170818_L1_350_1-23`), 366 (`…P18-366_L1_1-23`), 915 (`…Plus_915_L1_1-23`), 540 (`…P20-540_L3_1-23`), 1645 (`…Plus_1645_L1_1-23`), 1647 (`…Plus_1647_L3_1-23`), 1649 (`…Plus_1649_L5_1-23`); Q Exactive HF, MaxQuant multiplicity 3 |
| Blocked (TMT) | 28 raws: `YLJI_260321_070421_Ryan_Young_TMT11_0118_Batch1_phos_MS3_R{1,2}_frac1-14` (Orbitrap Fusion, TMT11 SPS-MS3) |

**What each source says:**

| source | channel map |
|---|---|
| `File_assignment.txt` (deposit) | two labels per BioID2 experiment: light = empty vector, plus heavy = (NB-)NRAS V12 (341, 350, 366) or medium = KRAS/shCTRL / NB-KRAS V12 (915, 540, 1645, 1647, 1649). TMT 118: only 126 = RPMI-8226 shCTRL and 128N = RPMI-8226 shSLC3A2 |
| MaxQuant `summary.txt` | every BioID2 experiment searched Multiplicity 3 (Arg6;Lys4 / Arg10;Lys8) |
| Deposited `proteinGroups.txt` | all three SILAC channels carry signal and bait enrichment in all 8 experiments (third-channel intensity share 13-68%; e.g. 366 medium 68%, NRAS log2 M/L 5.0; 915 heavy KRAS H/L 4.97). TMT 0118: all 11 reporter channels 1.17-1.43e8 |
| Source Data Fig. 1d (paper) | BioID2-RAS/empty-vector values equal log2 **H/L** normalized of 1645, 1647, 1649 (298/408/367 exact gene matches) — the deposit names the RAS bait as **medium** there; for 341 and 366 H/L (agrees with deposit) |
| Paper Fig. 2e / Fig. S3c | SLC3A2-knockdown phosphoproteome in **SKMM1**; deposit says RPMI-8226 for TMT 118 |
| Paper Methods, PRIDE protocol, Supplementary Figures | no per-channel layout for these experiments; no third condition named |

**Annotated arm deviates from the deposit for experiment 983 (XG-2).** `File_assignment.txt` lists medium = SLC3A2 + shCtrl and heavy = SLC3A2 + shKRAS. The SDRF follows the paper Source Data instead: Fig. 3a "XG2 shKRAS" equals log2 Ratio M/L normalized and "XG2 shCTRL" equals log2 Ratio H/L normalized of exp 983 for 2588/2589 genes. So medium = shKRAS.2 and heavy = shCTRL. The same identity test confirms `File_assignment.txt` for 984 and 139. Authors' confirmation of the 983 orientation would remove this override.

**Searched but never deposited** (no raw in `files/all`): MaxQuant_136_139 experiments 135 (`060320_HFPlus_135_L1`), 136 (`060320_HFPlus_136_L2`), 137 and 138; MaxQuant_96_96B R1_95, R2_95, R2_96 and R2_96B. Also MaxQuant_540 538-546 (except 540), MaxQuant_915 916-918, MaxQuant_1645_1647_1649 1646/1648/1650/1651, and MaxQuant_118 0122-batch2.

The third SILAC condition of each blocked BioID2 experiment, the identity of experiment 140, and 9 of 11 TMT channels are documented nowhere. Annotating them with `not available` conditions would pool unrelated samples (rule 7), and dropping a demonstrably used channel would falsely mark it unused.

Sources checked: PRIDE project record and protocol, `files/all` (331 entries), `File_assignment.txt`, all 11 MaxQuant zips (summary, parameters, proteinGroups; Phospho (STY)Sites for 96/96B), paper (PMC efetch), PMC OA supplementary (MOESM1 Supplementary Figures, MOESM2 Reporting Summary not needed, MOESM3 Source Data), ref 67 (Fish *et al.* PNAS 2020) for the phospho method. Analysis scripts and outputs are in the PXD031662 scratch dir (`scripts/ratios.py`, `scripts/fig1d.py`, `analysis/`).

**Unblocked by:** for the 23 `HFPlus_136_L6` raws, the authors identifying experiment 140 (cell line and L/M/H conditions), or depositing the `HFPlus_136_L2` raws of experiment 136, which `File_assignment.txt` and Fig. 3a already document. For the rest: the authors' full L/M/H assignment for experiments 341, 350, 366, 915, 540, 1645, 1647, 1649 (and confirmation of which channel holds the RAS bait in 1645/1647/1649), and the full TMT11 channel layout plus the cell line for experiment 0118. The BioID2 runs could then be added to `PXD031662.sdrf.tsv` (same search, add `NT=Biotin` slot `not applicable` for 350, which was searched without Biotin (K)); the TMT runs would go in a separate `PXD031662-tmt.sdrf.tsv` (rule 12).

## PXD029216 — Proteogenomics of viable leukemic blasts in AML (SWOG; SILAC + TMT10/TMT11), 5 undocumented TMT channels + 6 SILAC raws of unconfirmed identity (partial block)

| | |
|---|---|
| Publication | Naru J *et al.*, eJHaem 2024 5(6):1243-1251, PMID:39691254, PMC11647701, doi:10.1002/jha2.1041 (full text via NCBI efetch, Supplemental Methods s014.docx and Table S13 read) |
| Annotated | 630 of 636 raws → `PXD029216-silac.sdrf.tsv` (222 raws, 444 rows) and `PXD029216-tmt.sdrf.tsv` (408 raws, 4248 rows) |
| Not annotated | 6 SILAC raws `AML1036_Blast_BLD_2D_F01.raw` … `AML1036_Blast_BLD_2D_F06.raw` (12 rows: light + heavy; added after review round 1, see below); 168 TMT (run, channel) pairs: TMT131 of `JK021618_031218_AML_2nd_Discovery_TMT_10plex_GR{A,B,C}_F01-F24` (SWOG27) and TMT131N + TMT131C of `JN092820_101520_TMT11plex_E{2,3}_bRP_Frac_01-24` |

**What each source says:**

| source | channel map |
|---|---|
| `SWOG_NPM1_TMT_label_key.xls` (deposit) | SWOG27 sheet: channel 9 of groups A/B/C has an empty Sample ID and empty attributes; FH UW45 sheet: E2/E3 list channels 1-9 only |
| MaxQuant `AML_SWOG_2nd` proteinGroups | Reporter intensity 9 is 0.86-0.97 of the strongest channel in each group (occupied); RPS4Y1 intermediate between male and female channels (consistent with a mixed pool, not stated) |
| PD `.msf` E2 and E3 (ReporterQuanResults, first 40k rows each) | channels 10 and 11 have mean heights comparable to channels 1-9 in both plexes (occupied) |
| Paper, Supplemental Methods, PRIDE protocol | no reference/pool channel described for SWOG27 or FHCC/UW-HDR3 |

Sources checked: PRIDE record and `files/all` (642 entries), label key (4 sheets), 3 MaxQuant zips (parameters, summary, proteinGroups), both PD `.msf` (WorkflowXML, WorkflowInputFiles, ReporterQuanResults sample), raw headers, paper (PMC efetch), all 15 PMC OA supplementary files, Europe PMC search for the accession (only this paper).

**Unblocked by:** the identity of SWOG27 channel 131 (probably an internal reference pool) and of E2/E3 channels 131N/131C. They would be added as further rows to `PXD029216-tmt.sdrf.tsv` (same search parameters as their plex).

### PXD029216 — SILAC raws `AML1036_Blast_BLD_2D_F01-F06` (added after review round 1)

**Blocker: AML1036 / AML1089 conflict — the deposit names these 6 runs AML1036, the deposited search names the very same files AML1089 (a different patient, different NPM1 genotype), and no sample sheet lists them.**

| source | what it says about `AML1036_Blast_BLD_2D_F01-F06` |
|---|---|
| `SWOG_NPM1_TMT_label_key.xls`, sheet "SILAC" (37 rows) | no AML1036 row; every other deposited SILAC group (37) has one, with its raw pattern |
| `AML_SWOG_1st_MaxQuant_txt.zip` `summary_new.txt` | no AML1036 experiment; it holds a 38th experiment `AML1089_Blast_BLD_2D_F01-F06`; no raw is deposited under that name (but see the scan counts below) |
| label key, sheet "FH UW45" | AML1089 is an FH/UW patient (plex E3 channel 1) in the same plex as AML1037, AML1038 and AML1001-1006, all of which are SILAC-arm patients |
| raw headers | acquisition name `JK033016_AML_RO10001_2D_F01` … `F06`: the RO1000x series of AML1037 (RO10005) and AML1038 (RO10009) |
| label key, sheet "NPM1" | a patient AML1036 exists (Gr07 channel 2) in the TMT arm; nothing ties these SILAC raws to that patient |
| raw RunHeader scan counts vs `summary_new.txt` (review round 2) | the last-scan numbers of the six deposited raws (56695, 55013, 53042, 50719, 53105, 22785) equal MS + MS/MS of `AML1089_Blast_BLD_2D_F01`…`F06` exactly and in order: **these six raws are the files MaxQuant searched as AML1089** |
| genotype in the label key | AML1036: FLT3-ITD Pos, NPM1 **Pos** (NPM1 sheet Gr07 ch2); AML1089: FLT3-ITD Pos, NPM1 **Neg** (FH UW45 sheet, E3 ch1) |

So the same six files carry the patient name AML1036 in the deposit and AML1089 in the deposited search, and the SILAC sheet lists neither. Either the files were deposited under the wrong name, or the search experiment was misnamed. Annotating them under either name would assert a patient identity (and an NPM1 genotype that differs between the two candidates) that no source settles.

**Unblocked by:** a deposited statement tying the 6 raws to one patient (a SILAC-sheet row, or a corrected deposit), or a discriminating data test. Comparing the raws with the AML1089 search proves nothing, because they *are* that search. Either of these would discriminate:
- **NPM1 genotype in the light channel.** Look for NPM1 C-terminal mutant peptides, e.g. from a search of the AML1089 experiment's light peptides (`evidence_new.txt`) against a database with the NPM1 exon-12 mutant C-terminus, or a targeted look for the wild-type C-terminal peptide. Mutant evidence means AML1036 (NPM1-mutant). Wild-type only, with good coverage, means AML1089 (NPM1 wild-type).
- **Proteome correlation with the two patients' TMT channels.** Correlate the AML1089-search light protein profile with the AML1036 channel of NPM1 Gr07 (ch2, TMT127N) and with the AML1089 channel of plex E3 (ch1, TMT126), relative to the other channels of each plex.

Once identity is settled, the raws would be added as 12 rows to `PXD029216-silac.sdrf.tsv`, with light = patient and heavy = reference as for the other 37 groups. Their tolerances would follow the AML_SWOG_1st search: fragment 0.5 Da, precursor not available.

### PXD031662 — identity note for the blocked BioID2 raws (added after review round 3)

Before any of the blocked BioID2 raws are unblocked, confirm their identity against the MaxQuant search, not by file name alone:

- The deposited experiment-915 raws are dated 221119, but MaxQuant searched experiment 915 from files dated 261119; 221119 is experiment 916's date.
- The experiment-350 raw names in the deposit differ from those in the MaxQuant search.
- The same pattern already mislabelled the L-363 files (deposited as `HFPlus_136_L6`, actually search experiment 140; see above).

## PXD023790 — HAX1 controls mitochondrial proteostasis (Fan et al., J Clin Invest 2022), 7 pulse-SILAC raws (partial block)

**Blocker: for 7 triple-SILAC raws, the deposited data contradict the sample label (genotype or pulse time).** All evidence comes from `Fan_et_al_triple_SILAC_txt.7z` → `proteinGroups.txt` (MaxQuant 1.6.1.13). The submitter run sheet `SRDF_metadata_Fan_et_al.txt` marks all 7 runs "ok".

| raw file (MaxQuant experiment) | label | contradicting data |
|---|---|---|
| `20180614_QX0_MaMu_SA_M362_PBL985SILAC_MITO_t6_H1.raw` (2MITO_t6_H1) | HAX1-/- clone H1, mito, 6 h | HAX1 (O00165) identified by MS/MS, 8 peptides, Intensity L/M/H 1.1e9 / 5.2e8 / 1.9e8 (WT level). Clone H1 has HAX1 = 0 in its other 11 runs (count corrected by the independent review) |
| `20180612_QX0_MaMu_SA_M362_PBL985SILAC_CELLS_t24_C1.raw` | CLPB-/- C1, cells, 24 h | median log2 H/M −2.78 (t0 level); same-mix 2MITO_t24_C1 −0.29 |
| `20180612_QX0_MaMu_SA_M362_PBL985SILAC_CELLS_t24_C2.raw` | CLPB-/- C2, cells, 24 h | −2.88; same-mix 2MITO_t24_C2 −0.19 |
| `20180612_QX0_MaMu_SA_M362_PBL985SILAC_CELLS_t24_C3.raw` | CLPB-/- C3, cells, 24 h | −2.52; same-mix 2MITO_t24_C3 −0.74 |
| `20180612_QX0_MaMu_SA_M362_PBL985SILAC_CELLS_t24_H3.raw` | HAX1-/- H3, cells, 24 h | −2.69; same-mix 2MITO_t24_H3 −0.28 |
| `20180614_QX0_MaMu_SA_M362_PBL985SILAC_CELLS_Repeat_t0_W1.raw` | WT W1, cells, 0 h | −0.58 (t24 level); same-mix 2MITO_t0_W1 −2.39 |
| `20180614_QX0_MaMu_SA_M362_PBL985SILAC_CELLS_Repeat_t0_W2.raw` | WT W2, cells, 0 h | −0.67 (t24 level); same-mix 2MITO_t0_W2 −2.45; 2X_CELLS_t0_W2 −2.61 |

**Why H/M identifies the time point.** The supplementary methods take whole cells and mitochondria from the same heavy-pulsed + light mix at each time point, so a whole-cell run must match its same-mix mitochondria run. Across the other 100 annotated runs (52 of them mitochondria runs), H/M is consistent with the labelled time point. H/M separates 24 h from 0/6 h only; the 0 h and 6 h ranges overlap, so this check cannot distinguish 0 h from 6 h (t0 ≈ −2.3 to −2.9; t24 ≈ −0.03 to −1.8). Supporting evidence for the block: Repeat_t0_W1 correlates r = 0.89 with 2CELLS_t24_W1, consistent with a re-injection of a 24 h sample.

**Also not annotatable.** `20180312_QX8_MaMu_SA_PBL985_MITO_t0_H1` (experiment 1MITO_t0_H1) is in the MaxQuant search, but its raw file was never deposited in `Fan_et_al_Triple_SILAC_basis_raw.7z` (107 members).

**Annotated.** The other 100 raws are in `annotations/PXD023790-silac.sdrf.tsv` (300 rows). The 12 HSP27 FLAG-IP raws are in `annotations/PXD023790-hsp27-ip.sdrf.tsv`.

**Unblocked by:** an author statement, or a corrected sample sheet, giving the true sample and time point of these 7 runs (they may be swapped or re-used file names).

## PXD044779 — Trichothiodystrophy MPLKIP interactome (SILAC GFP-Trap IP, MRC-5), UV and MMC experiments only (partial block)

**Blocker: the light/heavy identities of the 'UV Complex' and 'MMC Complex' SILAC pull-downs are undocumented, and the deposited ratios show they do not follow the published map.**

The 'Basal Complex' experiment (16 RAW, `1802_L_AlexPines_{high,low}_01..08`) is annotated in `annotations/PXD044779.sdrf.tsv` (light = MRC-5 parental, heavy = MRC-5 MPLKIP-GFP knock-in). The 12 `2427_*` RAW are label-free DIA, byte-identical to PXD044434, and are out of scope for this SILAC campaign (not blocked).

| | |
|---|---|
| Publication | Theil AF *et al.*, EMBO Mol Med 2023 15(11):e17973, PMID:37800682, PMC10630875, doi:10.15252/emmm.202317973 (PMC OA full text read) |
| Blocked | `1802_L_AlexPines_high_09` … `_high_24` and `1802_L_AlexPines_low_09` … `_low_24` (32 RAW, Orbitrap Fusion Lumos; MaxQuant 1.5.4.1 multiplicity 2, Labels1 Arg10;Lys8; experiments 'UV Complex' = 09-16, 'MMC Complex' = 17-24) |

**What each source says:**

| source | channel map |
|---|---|
| Paper Results, Fig 3A legend, Methods, PRIDE protocol | one SILAC experiment: light = MRC-5 parental (CTR), heavy = MRC-5 MPLKIP-GFP; no UV or MMC (mitomycin C?) treatment of SILAC cells is described anywhere |
| `1802_summary.txt` | experiment names 'UV Complex' / 'MMC Complex' only; no channel or treatment description |
| `1802_proteinGroups.txt`, Ratio H/L normalized | Basal: MPLKIP 21.4, DBR1 22.7, XAB2 21.6, ISY1 23.7 (heavy = bait, matches paper). UV: MPLKIP 0.64, DBR1 0.82, XAB2 0.47, ISY1 0.46. MMC: MPLKIP 0.97, DBR1 0.97, XAB2 7.3, ISY1 8.1. The bait is not enriched in heavy in either, so both channels likely carry MPLKIP-GFP (e.g. treated vs untreated) or a different control; which channel got which treatment, dose and time are unstated. |

Sources checked: paper (full text incl. Methods, figure legends, Data availability), PRIDE v3 record and paginated file list (63 entries; no sample sheet, no mqpar/parameters), `1802_summary.txt`, `1802_proteinGroups.txt`, raw headers (instrument method only).

**Unblocked by:** the authors stating, per experiment, the cell line, treatment (UV dose/time, MMC concentration/time) and SILAC label of each channel. The 32 runs (64 rows) would then be added to `PXD044779.sdrf.tsv` with the same search parameters as the Basal experiment.

## PXD029618 — Podocyte injury in Fabry nephropathy (triple-SILAC GLA-KO vs WT podocytes), 20 raws of mixtures CFP910 / CFP911 (partial block)

**Blocker: channel use and orientation of `20160120_VD_CFP910_sample_1_1..10.RAW` and `20160112_VD_CFP_911_2_01..10.raw` are undocumented.**

| source | what it says |
|---|---|
| `txt.zip` (MaxQuant 1.4.1.2) `summary.txt` / `proteinGroups.txt` | only experiments #867_sample1/2 and #899_sample1/2 (40 raws); CFP910/CFP911 were not searched |
| Paper Fig. 2A | 6 label-swap mixtures (KO vs WT clones, Arg6Lys4 vs Arg10Lys8), not tied to file names; its label identity already conflicts with the data for #899 (light+heavy, not medium+heavy) |
| Paper Fig. 2B | 6 replicate columns; columns 1-4 match the four searched experiments; columns 5/6 presumably CFP910/CFP911, but which label carries KO, and whether light or medium was used, is not stated |
| PRIDE protocol, supplementary PDF/xlsx | no label key or sample sheet |

The 40 searched raws are annotated in `annotations/PXD029618.sdrf.tsv` (80 rows).

**Unblocked by:** a MaxQuant search of the 20 raws (same parameters: Multiplicity 3, Arg6;Lys4 / Arg10;Lys8, Trypsin/P, Carbamidomethyl fixed, Oxidation + Acetyl N-term variable), then: channel intensity shares to find the two used labels, and the Fig. 2B column 5/6 match (scripts in the b5-PXD029618 scratch dir) for the KO/WT orientation. Or an author statement of the label per mixture.

## PXD023136 — TMEM126A / complex I ND4-module (Formosa et al., PNAS 2021), 36 pulse-chase SILAC raws (partial block)

**Blocker: per-run sample identity of the Fig 3F/3G pulse-chase SILAC runs `201119_Daniella_DH-1445_01.raw` … `_36.raw` is undocumented in every retrievable source.**

| source | what it says |
|---|---|
| `Figure_3F_3G_TMEM126A_pulse_chaseSILAC.zip` (MaxQuant 1.6.10.43) `summary.txt` | Multiplicity 2, Labels1 Arg10;Lys8; experiment names are only `01` … `36` (one per raw); no cell line, time point or IP/input label. No mqpar/experimentalDesign in the zip. |
| PRIDE dataProcessingProtocol | heavy intensities "normalised to the maximum value detected in the WT cell line at 4h pulse ... means plotted over time" — names a WT line and a time course, not which run is which |
| bioRxiv v1 preprint (10.1101/2020.09.18.303255) | predates the experiment (raws acquired 2020-11-19; D.H. Hock is not an author of v1); no pulse-chase MS described |
| PNAS 2021 (PMC8092609) full text, Fig 3F/3G legend, SI | not retrievable: PMC body not open access (efetch front matter only), Europe PMC fullTextXML HTTP 500, pnas.org and pmc.ncbi.nlm.nih.gov served bot checks (not bypassed), Unpaywall points only to the preprint |
| raw headers | Orbitrap Eclipse, targeted method `Dani Target.meth` with heavy/light inclusion list of mtDNA-encoded peptides — instrument only |

The other 9 raws are annotated: `annotations/PXD023136-silac.sdrf.tsv` (Fig 1B SILAC, 3 runs × 2 channels) and `annotations/PXD023136-aems-lfq.sdrf.tsv` (Fig 3B label-free Flag AE-MS, 6 runs).

**Unblocked by:** the PNAS Fig 3F/3G legend + SI Methods (or an author sample sheet) mapping run 01–36 to cell line (WT / TMEM126A KO / Flag line), pulse or chase time and replicate (and whether runs are Flag eluates or whole mitochondria). Rows would then be one light (pre-existing) + one heavy (newly synthesised) row per run, as in PXD028934, with MaxQuant 1.6.10.43 search parameters (Carbamidomethyl fixed; Oxidation, Acetyl N-term variable; Arg10/Lys8 labels; FTMS 20 ppm).

## PXD004666 — Accessory subunits of human mitochondrial complex I (HEK293T knockouts, SILAC + FLAG AP-MS), ACPOE runs only (partial block)

**Blocked runs (6 of 489 RAW):** `091QEP120_O-171-ACPOE-LH_T1.raw`, `091QEP120_O-171-ACPOE-LH_T2.raw`, `092QEP120_O-172-ACPOE-LH_T1.raw`, `092QEP120_O-172-ACPOE-LH_T2.raw`, `093QEP120_O-173-ACPOE-LH_T1.raw`, `093QEP120_O-173-ACPOE-LH_T2.raw`. These are mitochondria runs on the Q Exactive Plus, searched in `combined.zip` as experiments O-171/172/173-ACPOE-LH.

**Blocker 1: no available source defines the "ACPOE" cell line.**
- Stroud et al., Nature 2016 (PMID 27626371): the figure and Extended Data legends never mention ACPOE. The Methods are paywalled and were not read.
- Supplementary Data xlsx: Table S5 has a 'Mean Log2 ratio ACPOE' column and 'Log2 Ratio H/L O.171/172/173.ACPOE.LH' columns, but no definition.
- Supplementary Information Table 1: the NDUFAB1 knockout clones are named 'ACP1-1' and 'ACP1-3' ('KO (NDUFAB1)'). Supp Table S2 calls the NDUFAB1-period AP-MS control 'HEK293TACP1'. Ext Data Fig. 3a/3e describe NDUFAB1 knockouts complemented with a FLAG-tagged yeast ACP1 (yACP1Flag) or NDUFAB1Flag. None of these defines ACPOE. Yeast ACP1 is absent from all 15 anti-FLAG AP-MS eluates, so the S2 header does not by itself establish an ACP1-expressing control line.
- Data (combined.zip proteinGroups.txt): human NDUFAB1 H/L is 1.17, 1.13 and 1.12, i.e. unchanged. Yeast ACP1 (P32463) is present in one channel only: O-171 L 3.30e8 / H 0; O-172 L 5.07e8 / H 1.4e7; O-173 H 4.67e8 / L 0. This suggests HEK293T over-expressing yeast ACP1 against plain HEK293T, but that is inference, not a statement.

**Blocker 2: the label orientation of O-173 contradicts its deposited tag (independent review, 2026-11-08).**
- The raw header of `093QEP120_O-173-ACPOE-LH_T1.raw` (and T2) gives the acquisition name `P1DAS20151020-DAS_O-173-ACPOE-HL_T1.raw`.
- In O-173 yeast ACP1 is heavy only (H 4.67e8, L 0), whereas in O-171 it is light only. The acquisition name and the data therefore both contradict the deposited 'LH' tag.
- The HL/LH rule otherwise holds in all 122 annotated knockout experiments that quantify their target. In the two other experiments whose acquisition name disagrees with the deposit (V-227, T-215), the data side with the deposited tag.

**Related, annotated (not blocked):** the NDUFAB1 experiments O-168..170 carry yeast ACP1 in both channels. They are annotated as 'NDUFAB1 knockout; yeast ACP1 expressing' vs 'HEK293T expressing yeast ACP1'.

**Unblocked by:**
- the paper Methods or an author statement defining ACPOE and its partner line;
- the orientation of O-173 settled; the data indicate the ACPOE line is heavy, i.e. HL.

The rows would then go into `PXD004666-knockout.sdrf.tsv`, with the same technical values as the other QEP120 runs.

Also noted (not blocked, no files): `combined.zip` experimentalDesignTemplate.txt lists `124ELITE180_K-117/118/119-NDUFV1` T1/T2 runs that were neither deposited nor searched.

## PXD006015 — SILAC pulse labeling in HGPS fibroblasts, WT samples (Buchwalter & Hetzer, Nat Commun 2017), 2 PEAK-only MP re-runs (partial block)

**Blocked files (2 of 15 WT runs):** `20160302_MHAB-1_MP.mzXML` (121,771 scans) and `20160302_MHAB-2_MP.mzXML` (103,970 scans). Both are Orbitrap Fusion runs (mzXML parentFile `G:\Fusion_data\MHAB\20160302_MHAB-1_MP.raw` / `..._MHAB-2_MP.raw`).

**Probable identity, from the MHAB numbering:** the numbering maps the other 23 runs of PXD006015/PXD006016 consistently. WT is MHAB-1..10 and HGPS is MHAB-11..20, in the order 0D, 1D, 2D, 4D, 6D × extract, pellet. By that scheme, MHAB-1 = WT 0 day nuclear extract and MHAB-2 = WT 0 day nuclear pellet. The annotated WT 0D runs are `MHAB-1_SCXtip` and `MHAB-2_SCXtip` (+ `_2`) of 20160227 = `20160227_WT_0D_extract/pellet[_2].ms2`. The two MP files look like the same samples re-run after the "MP" clean-up on 20160302, the day the HGPS 0D samples (MHAB-11_MP / MHAB-12_MP) were run.

**Why they are not annotated:**
- They are PEAK-only (.mzXML): no RAW-category `.ms2` exists for them, so there is no `comment[data file]` consistent with the other 13 rows.
- No deposited mzIdentML references them. The WT_0D_extract and WT_0D_pellet mzids use only the SCXtip runs, so their search parameters are undocumented.
- Their clean-up (MP) differs from the searched SCXtip runs of the same samples.
- Their identity is inferred from file numbering only. No source states it.

**Annotated:** the 13 RAW-category `.ms2` runs (26 rows) are in `annotations/PXD006015.sdrf.tsv`. All 10 HGPS runs are in `annotations/PXD006016.sdrf.tsv`; no HGPS file is blocked.

**Unblocked by:** an author statement or sample sheet confirming that MHAB-1_MP / MHAB-2_MP are the WT 0D extract / pellet, plus their search parameters (or a re-search). They could then be added as WT 0D technical replicate 3 rows, with the .mzXML as `comment[data file]` in a separate build with identical headers.

---

## PXD003446 — Huntingtin aggregate-stage interactome in N2a cells (Kim et al., Mol Cell 2016; SILAC), all arms except the Q18 IP controls (partial block)

**Blocker: no reachable source states which SILAC label carried which polyQ construct / condition in the total-proteome, soluble-IP or insoluble-inclusion experiments, and the paper is not retrievable. 204 of 213 RAW are left out. The Q18 IP control arm (`Q18IPcontrols.zip`, 9 RAW, light = uninduced, heavy = HttEx1Q18-eGFP; fixed by the eGFP bait, H/L 14–41 in all three experiments) is annotated in `annotations/PXD003446.sdrf.tsv`.**

| | |
|---|---|
| Publication | Kim YE, Hosp F, Frottin F, Ge H, Mann M, Hayer-Hartl M, Hartl FU. Mol Cell 2016 63:951, PMID:27570076, doi:10.1016/j.molcel.2016.07.022 — **not retrieved**: no PMC copy (Europe PMC inEPMC=N), Unpaywall/cell.com PDF 403, cell.com full text = Cloudflare bot check (not bypassed), Elsevier TDM API needs a key, MPG PuRe item_2352983 only links out |
| Deposited | 213 RAW + 4 MaxQuant txt zips (`totalproteome.zip`, `IPs_soluble.zip`, `insoluble.zip`, `Q18IPcontrols.zip`; experimentalDesignTemplate, parameters, summary, proteinGroups HTTP-range read) |
| Blocked (a) total proteome | 72 RAW `2012*_YK_180_015_*` / `2012*_FT_YK_240_015_TP_{24h,48h}_T{1,2,3}_*` (MaxQuant experiments TP_24h/48h_T1–T3; multiplicity 3, Arg6Lys4 / Arg10Lys8) |
| Blocked (b) HttEx1SOL soluble IPs | 36 RAW `20150529_Exactive_YK_140{15..32}`, `20150605_Exactive_YK_rr{13997..14014}` (experiments 24he1–3, 48he1–3, 6 fractions each; multiplicity 3) |
| Blocked (c) insoluble inclusions | 96 RAW `2013*_FaHo_SA_*` (experiments SDS_one, SDS_two_forward/reverse, TX_forward/reverse; multiplicity 2, Arg10Lys8) |
| SDRF would need | (a) 72×3 + (b) 36×3 + (c) 96×2 = 516 rows with the construct (uninduced/Q18/Q64/Q150+), induction time and, for (c), the compared condition of each channel |

Sources checked:

| source | result |
|---|---|
| PRIDE sampleProcessingProtocol | "labeled ... with light (L), medium (M) or heavy (H) arginine and lysine"; Q18, Q64, Q150+ induced 24 or 48 h, mixed 1:1:1 — no construct→label assignment |
| PRIDE dataProcessingProtocol | "Ratios (Q150+/Q18 and Q64/Q18)"; "Q18 interactome ... uninduced cells as the background control" — names ratios, not labels |
| MaxQuant experimentalDesignTemplate / summary / proteinGroups | experiment names only (TP_24h_T1_, 24he1, SDS_two_forward, ...); columns Ratio M/L, H/L, H/M — no condition names |
| Data anchoring, (a)/(b) | every channel expresses an eGFP-HttEx1 construct, so the bait cannot discriminate; in `IPs_soluble` the only Htt peptide (ATLEKLMK) is shared by Htt16Q/Htt60Q/Htt150Q, so Q18 vs Q64 vs Q150 cannot be told apart |
| Data anchoring, (c) | what the second channel is (Q150 vs uninduced? vs Q18? SDS vs Triton extraction?) is undocumented; forward/reverse orientation unknown. In addition 34 deposited RAW names (`HttQ105_formicacid_gel_slice_01–06`, `Q103agg_gel1–6_01/02`, `TX_Rep2_s5/s6`, `TX_gel_Rep3_*`, `TX_Rep3_s5_01`) are not the names used in the deposited search (`..._Q150_gel_SDS_Rep1_s1–6`, `..._gel_SDS_Rep2_*`, `..._gel_TX_Rep2/Rep3_*`), and the deposited names say Q105/Q103 where the search names say Q150 — file identity is unconfirmed |
| Europe PMC search "PXD003446" | 0 hits |

**Deliberately not used:** assuming L/M/H = Q18/Q64/Q150 (the order of the ratio names), or reading the insoluble forward/reverse orientation from biological expectations.

**Unblocked by:** the paper's STAR Methods / figure legends (or the authors, Hartl/Mann labs, MPI Biochemistry) stating the L/M/H construct of each total-proteome and soluble-IP experiment, the two conditions and label orientation of each insoluble experiment, and the mapping of the renamed insoluble RAW files to the searched names.

## PXD014577 — Protein degradation in prion-infected N2a-Cl3 cells (Hutti et al., Sci Rep 2020; dynamic SILAC), 10 whole-proteome raws + 12 NaBu raws (partial block)

Annotated: `PXD014577-proteome.sdrf.tsv` (54 of 64 whole-proteome raws × light/heavy) and `PXD014577-prpsc.sdrf.tsv` (3 PK-isolate raws × light/heavy).

**Blocker 1: the labelling data of 10 RML (-QA) whole-proteome runs contradict the day in their file name and MaxQuant experiment.**
Heavy share of identified MS/MS (msms.txt Labeling State, partial msms.txt of the truncated `txtfor-QAandQA.zip`), compared with the other fractions of the same arm and day:

| raw | recorded | heavy share | same arm/day, other fractions | fits |
|---|---|---|---|---|
| `Hutti_R1-7_18-057.raw` | RML day 1, fr 7 | 0.815 | R1 0.53–0.55 | day 2 |
| `Hutti_R2-7_18-057.raw` | RML day 2, fr 7 | 0.599 | R2 0.77–0.85 | day 1 |
| `Hutti_R3-5..8_18-057.raw` (4) | RML day 3, fr 5–8 | 0.969–0.972 | R3-1..4 0.867–0.884 | day 5 |
| `Hutti_R5-5..8_18-057.raw` (4) | RML day 5, fr 5–8 | 0.909–0.929 | R5-1..4 0.954–0.960 | day 3 |

The +QA (Q) arm rises smoothly with fraction and day; the pattern above looks like swapped R1-7/R2-7 and swapped R3/R5 fractions 5–8, but no source states a swap, so the runs are left out rather than re-labelled. The paper's RML kinetics used them as named (MaxQuant experiments "RML day N"). Check: `scripts/timepoint_check.py` → `timepoint_check.tsv` in the producer scratch `b6-PXD014577/`.

**Blocker 2: the sample type of the 12 sodium-butyrate runs (`Hutti_NB{1..4}P`, `Hutti_NB{1..4}-P`, `Hutti_NB{1..4}-S` `_19-082.raw`; acquisition names NB*+P / NB*-P / NB*-S) is undocumented and contradicted.**
- Paper / PRIDE: one NaBu experiment, "-QA + NaBu + PK digest", lysates "treated with PK and protease-resistant PrPSc was isolated by PTA precipitation"; days 1–4. Nothing defines +P, -P or -S.
- `txtforPrPScduringNaBuisolated.zip` summary.txt: 12 experiments, Multiplicity 2, Arg6;Lys6, no names beyond the numbers.
- Supp Table S2 (MOESM3) sheet "-QA + NaBu + PK digest" Day 1–4 ratios equal MaxQuant experiments 3/6/9/12 exactly (1914/1895/1853/1932 proteins) = the **-S** runs; the natural reading "+P = PK-digested PTA pellet" (fewest IDs, lowest PrP H/L) is therefore not what the authors published as the PK isolate.
- The day (NB1–NB4 = day 1–4) is supported by the median H/L rising 0.40 → 1.8.

**Unblocked by:** an author statement or sample sheet (Ghaemmaghami lab, University of Rochester) giving (1) the true day/fraction of the 10 RML runs, or confirming they are as named; (2) what +P, -P and -S denote (PK yes/no; pellet/supernatant). The rows would then join the existing files with the same technical values (whole proteome: Q Exactive Plus, HCD 27, hpHRP fractions; NaBu: Orbitrap Fusion Lumos, CID 30, ion trap 0.5 Da, MaxQuant 1.6.5.0, Carbamidomethyl fixed, Oxidation/Acetyl N-term variable, Arg6/Lys6).

## PXD034016 — G4C2 RNA pulldown (label-free AP-MS, mis-tagged SILAC), whole dataset (30 RAW)

**Not in scope for this SILAC campaign: the deposit is label-free. No channel map is missing.**

| | |
|---|---|
| Publication | Luteijn *et al.*, Nucleic Acids Res 2025 53(7):gkaf253, PMID:40207633, PMC11983130 (OA; text from PMC OA S3 `PMC11983130.1.txt`) |
| Deposited | 30 RAW (`PXP0486_G4C_1_1…16`, `PXP0486_G4C_3_{1-6,8-12,14-16}`) + `id_placeholder.xlsx` (contains only "placeholder"); no search output |
| SDRF would need | a label-free AP-MS SDRF: (G4C2)4 RNA bio-IP from HeLa nuclear lysate ± compound, 2 lanes × 16 gel slices (fractions) |

Not SILAC despite PRIDE `quantificationMethods` = SILAC:
- PRIDE sample protocol: "Pulldown with G4C2 combined label-free analysis of purified proteins". Data protocol: "Mascot search and Scaffold analysis of label-free data". Software: Mascot. Experiment type: AP-MS (PRIDE:0000433).
- Paper Methods, "Mass spectrometry": affinity-purified samples, 16 gel slices per lane, Trypsin/Lys-C in-gel digestion, Q Exactive, Mascot 2.4 + Scaffold 4.6.4, "Spectral count was used as a proxy for protein abundance". The paper's "SILAC" section covers only the SRSF1/SF3B1 IPs (MaxQuant 1.5.8.3).
- Paper Data Availability: PXD034016 = "G4C2 pulldown (30/32 files)", and PXD034097 = "2 missing files from G4C2 pulldown (2/32 files)". Together they are the label-free arm; `_3_7` and `_3_13` are the 2 runs in PXD034097. The SILAC arms are PXD034093 (SF3B1 SILAC pulldown) and PXD034092 (SRSF1 SILAC pulldowns, 2 subcellular fractions). Both are already curated in sdrf-annotated-datasets (`datasets/PXD034092/`, `datasets/PXD034093/`).

**Unblocked by:** annotating it as a label-free SDRF outside this SILAC campaign, ideally together with PXD034097 (32 runs). That annotation would need the lane → condition (± PlaB pretreatment, oligo) map for `G4C_1` / `G4C_3`, from the paper's Fig. 7D / Supplementary Data S4 or from the authors.

---

## PXD041509 — USP39 deficiency / cryptic splicing (Prieto-Garcia et al., Science 2024; SILAC diGly + TMTpro + label-free IP), SILAC and TMT arms (partial block)

**Blocker: no reachable source says which SILAC channel carries siUSP39 and which carries the control, in any of the three diGly experiments. The TMTpro arm has no channel→sample map either. The 12 label-free IP raws (USP39 vs IgG IP; PRPF4 IP ± siUSP39) are annotated in `annotations/PXD041509.sdrf.tsv`.**

| | |
|---|---|
| Publication | Prieto-Garcia *et al.*, Science 2024, doi:10.1126/science.adi5295, PMID 39541449. Not in PMC; Unpaywall `closed`; science.org article and supplement HTTP 403 (not bypassed); no preprint found in Europe PMC. PRIDE `references` is empty. |
| Deposited | 54 RAW: 18 SILAC diGly (Orbitrap Exploris 480), 24 TMTpro (Orbitrap Fusion Lumos), 12 label-free IP (Q Exactive HF). Other files: `mqpar_siUSP39_digly.xml`, `mqpar.xml`, `mqpar-PRPF4.xml`, PD `.pdStudy` / `.pdResult` / `_Proteins.txt` / `.method`, 3 Perseus xlsx, 2 PD png. |
| Blocked (SILAC) | `20221231_SFB1_PBE_TM_siUSP39_SILAC_exp{1,2,3}_{1..6}.raw`: 18 files, 3 experiments × 6 fractions. |
| Blocked (TMT) | `20220830_LU_LC2_RR_CPG_USP39_PROTAC_F1..F24.raw`: 24 high-pH fractions of one TMTpro mix. |
| SDRF would need | SILAC: 18 × 2 = 36 rows, each light/heavy channel tagged siUSP39 or control. TMT: 24 × 6 = 144 rows for channels 126, 127N, 127C, 128N, 128C and 129N. |

**What the deposit does say (SILAC):**
- `mqpar_siUSP39_digly.xml` (MaxQuant 1.5.2.8) gives multiplicity 2, light = unlabelled and heavy = `Arg10;Lys8`. Experiments 1–3 each have fractions 1–6.
- Experiment 3 uses its own parameter group in which labelMods are reversed (`Arg10;Lys8` listed first). That is a label swap relative to experiments 1 and 2.
- Variable mods: GlyGly (K), Oxidation (M), Acetyl (Protein N-term). Fixed: Carbamidomethyl (C) and `NEM`.
- File names say `siUSP39`, and the MaxQuant folder says `usp39-ko-digly`.
- Nothing names the condition of either channel. No MaxQuant txt output (summary, GlyGly sites, proteinGroups) is deposited, so ratios cannot be checked either.

**Sources checked:**

| source | result |
|---|---|
| PRIDE project record (both protocols, description) | No SILAC or diGly protocol text at all. The sample protocol covers only the TMT workflow; the data protocol covers QE HF / Lumos acquisition and the PD/MaxQuant search. |
| `files/all` (66 entries) | No sample sheet and no MaxQuant txt for the diGly search. |
| `mqpar_siUSP39_digly.xml` | Experiment numbers 1/2/3 and the label definitions only. No condition names. |
| Raw headers (`exp1_1`, `exp2_1`, `exp3_1`; HTTP range read) | Method `NSI_110min_TOP15_..._for_SILAC_DiGly_fractionated.meth`, Exploris 480. Sample name and comment fields are empty. |
| `USP39-proteomic.xlsx` | A PD TMT export (`F2`, 18 channels, all named `Sample`). It contains no SILAC data and does not match the deposited 6-channel `.pdStudy` (`F1`). |
| `.pdStudy` (TMT) | 6 samples named `<file> - [channel]`, PD default sample types (126 = Control), `<Factors />` empty. |
| `PCA.png` / `TMTabund.png` | Channels labelled by number only. The PCA splits {126, 127N, 127C} from {128N, 128C, 129N}, but the groups are not named. |
| Paper, supplement, preprint | Inaccessible (see above). |
| Europe PMC search for PXD041509 | 0 hits. |

**Deliberately not used:**
- the MaxQuant label-swap layout of experiment 3 (it fixes the relative orientation only, not which channel is which condition);
- the PCA grouping of the TMT channels;
- the common convention "heavy = treatment".

None of these states a label (campaign rules 6–7).

**Unblocked by:** the paper's Materials and Methods / supplementary text (diGly SILAC and TMT sections), or an author statement.
- SILAC needs, for each of exp1/exp2/exp3, whether light or heavy (Arg10/Lys8) is siUSP39. HeLa cells are likely but not confirmed for this arm.
- TMT needs a 6-channel condition list (the file name suggests a USP39 PROTAC experiment).

The technical values are already resolved in `annotations/PXD041509.report.md`:
- SILAC arm: Orbitrap Exploris 480 MS:1003028, Arg10 UNIMOD:267, Lys8 UNIMOD:259, GG UNIMOD:121, Nethylmaleimide UNIMOD:108, MaxQuant 4.5 ppm / 20 ppm.
- TMT arm: Orbitrap Fusion Lumos MS:1002732, SPS-MS3, Sequest HT 7 ppm / 0.5 Da.

## PXD024211 — USP32 / LAMTOR1 ubiquitinome (Hertel et al., Cell Rep 2022; SILAC diGly + total proteome, RPE1), 36 "Mila" raws (partial block)

| field | value |
|---|---|
| Deposited | 72 RAW (Q Exactive HF) + `txt_gg_ip.zip`, `txt_global_prot.zip` (MaxQuant txt; Multiplicity 2, light = unlabelled, heavy = Lys8). Both searches contain two series: "AlexK" (experiments A1–A3 / a1–a3) and "Mila" (M1–M3 / m1–m3). |
| Annotated | The 36 AlexK files (USP32 study): `annotations/PXD024211.sdrf.tsv`. Light = RPE1 NHT, heavy = RPE1 USP32KO, from the first author's thesis (doi:10.21248/gups.62688, Fig. 3-4, Methods 6.2.10.1) and cross-checked against the deposited diGly-site ratios. |
| Blocked | `20180320_FB_Mila_GGIP_{1,2,3}_{4,5,6,7,85,12}.raw` (18 diGly SCX fractions) and `20180403_FB_Mila_GGIP_Prot_{1,2,3}_{1..6}.raw` (18 gel slices): 36 files. |
| SDRF would need | 36 × 2 = 72 rows with the cell line, the genotype/treatment of each channel (light, heavy) and the replicate structure. |

**What the deposit does say:**
- "Mila" is Mila Basic (Bremm lab; thesis acknowledgements and publication list). She works on USP11, not USP32.
- Total-proteome `Ratio H/L normalized` for USP11 is m1 0.61 and m2 0.42 (A series about 0.9–1.0). That suggests USP11 depletion in the heavy channel, but no source states it.
- The diGly-site ratios of Rab7/Rab11/TMEM192 are flat in M1–M3, so these runs are not a USP32 replicate.

**Sources checked:**

| source | result |
|---|---|
| PRIDE record (description, both protocols) | Describes only RPE1 NHT vs USP32KO. Nothing about a second series. |
| Cell Rep paper (doi:10.1016/j.celrep.2022.111653) | Abstract only. No PMC copy, cell.com PDF 403 (not bypassed), Elsevier API returns metadata only. |
| Hertel thesis (Goethe University OPUS) | Describes the USP32 diGly experiment only ("one SILAC sample set with three technical replications"). |
| Basic et al., JBC 2021 (USP11; PMC8546420) | Data availability names PXD022143 (USP11 GFP-IP, 6 raws). No SILAC diGly experiment. |
| MaxQuant summary/parameters/proteinGroups | Only the experiment names M1–M3 / m1–m3. No sample names. |

**Unblocked by:** a source (author statement, or a later USP11 paper's methods) naming the cell line and the light/heavy condition of the Mila diGly and total-proteome sets.

## PXD012322 — Matrisome properties of scaffolds direct fibroblasts in IPF (Elowsson Rendin et al., IJMS 2019; SILAC repopulated lung scaffolds), 12 scaffold raws + sampling time of the 47 SILAC raws (partial block)

| field | value |
|---|---|
| Deposited | 59 RAW (Q Exactive Plus) + `SILAC2.resultfiles.zip` (MaxQuant txt.repopulated: Multiplicity 2, Labels1 Arg6;Lys8; txt.scaffold: Multiplicity 2, Labels1 Lys6). |
| Annotated | The 47 `Emma_S1803_*.raw` repopulated-scaffold runs, 2 rows each (light = pre-existing scaffold proteins, heavy = proteins newly made by the heavy-labelled healthy lung fibroblasts): `annotations/PXD012322.sdrf.tsv`. Scaffold donor (FL9, FL10, FL11, Lures18, SAL23–SAL26) comes from each raw header's sample ID; IPF vs healthy comes from the paper's hospital-of-origin statement and is cross-checked by the IPF basement-membrane signature in the light channel. |
| Blocked (whole runs) | `Emma_S1801_{217,218,219,220,222,223,224,225,227,228,229,230}.raw` (decellularized scaffolds, MaxQuant txt.scaffold Experiment 1). They contain no labelled material (H/L 0.15%), so they are label-free in substance. Their raw sample IDs `SILAC_sample_1..12` have no documented link to donors HL 1, HL 2, IPF 1, IPF 2 (paper Fig. S2: 2 donors per group × 3 replicates). |
| Blocked (one attribute) | `characteristics[sampling time]` is `not available` on all 94 rows. Cultures were harvested on day 1, 3 or 9. The runs form three vial blocks of 16 (A1–B4, B5–C8, C9–D12), each holding every donor twice, but no source says which block is which day. The heavy share H/(H+L) does not rise monotonically across the blocks, so the data cannot settle it either. |
| SDRF would need | For S1801: 12 label-free rows with donor/disease per file (a separate label-free SDRF). For S1803: the day of each vial block. Optionally the FL/SAL code → Table 1 HL/IPF ID key (it would also give per-donor age and sex). |

**Sources checked:** PRIDE record and file list (no sample sheet); paper full text (Europe PMC XML) and Tables 1–2; supplementary `ijms-20-04013-s001.pptx` (figure legends, clustered heat-map labels HL 1:1…IPF 2:3, embedded Prism graphs of group means only); MaxQuant summary/parameters/proteinGroups (experiment names are bare numbers 1–55 / 1–3); raw headers of all 59 files (sample ID, vial). The paper has no data or code availability links beyond PXD012322.

**Unblocked by:** an author sample sheet giving the day per S1803 vial (or per MaxQuant experiment 1–48) and the donor/replicate per `SILAC_sample_N`.

## PXD012871 — USP9X substrate NFX1-123 (Chen et al., J Proteome Res 2019; SILAC HeLa shUSP9X vs shGFP + Flag-NFX1 IP-MS in HEK293T), 6 label-free IP runs (partial block)

| field | value |
|---|---|
| Deposited | 84 SILAC RAW `20150422_GJ_U{1..6}_{1..14}.raw` (Q Exactive; `txt_SILAC.rar`: Multiplicity 2, Labels1 Arg10;Lys8) + 6 label-free IP RAW `20181216__Ludayun_293T_Over_{EV,NFX1_1,NFX1_2}_{Up,Down}.raw` (Q Exactive HF; `txt_IP.rar`: Multiplicity 1, experiments EV / NFX1_1 / NFX1_2, fractions Up=1, Down=2). |
| Annotated | All 84 SILAC runs, 2 rows each: `annotations/PXD012871.sdrf.tsv` (168 rows). Forward U1–U3 (light = shUSP9X), reverse U4–U6 (heavy = shUSP9X) from the PRIDE labelling statement + USP9X H/L ratios + ratio correlation. |
| Blocked (whole runs) | The 6 IP runs. Each raw header's original acquisition file name contradicts the deposited name: deposited `EV_Up/Down` = acquired `20181216__HF_ZHW_Ludayun_293T_Over_NFX1_Ub_Up/Down`; deposited `NFX1_1_Up/Down` = acquired `..._Over_NFX1_Up/Down`; deposited `NFX1_2_Up/Down` = acquired `..._Over_EV_Up/Down`. The data do not settle it: NFX1 (Q12986) MaxQuant intensity is 0 in deposited "EV" (acquired "NFX1_Ub"), 1.93e9 in "NFX1_1" and 1.53e8 in "NFX1_2" (acquired "EV"). Which run is the empty-vector pCMV-Flag control, and whether "NFX1_Ub" belongs to this comparison at all, is undocumented. |
| SDRF would need | For each of the 3 IP samples: construct (Flag-NFX1-123 vs empty pCMV-Flag), whether it is a ubiquitination experiment, and replicate status. Then a separate label-free SDRF (`PXD012871-ip`, HEK293T CVCL_0063, Q Exactive HF MS:1002523, 27 NCE, 350–1700 m/z, gel slices Up/Down as fractions 1/2). |

**Sources checked:** PRIDE record and file list (92 files; protocol says only "293T cell transfected with Flag-tag NFX1 or empty vector pCMV-Flag"); paper (closed access, abstract only, Unpaywall closed); MaxQuant `txt_IP.rar` summary/parameters/proteinGroups (experiment names only); raw headers of all 6 IP files.

**Unblocked by:** an author statement or the paper's methods/figure mapping each deposited IP file to its construct, explaining the renaming.

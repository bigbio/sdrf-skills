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

## PXD012871 — USP9X substrate NFX1-123 (Chen et al., J Proteome Res 2019; SILAC HeLa shUSP9X vs shGFP + Flag-NFX1 IP-MS in HEK293T), 2 NFX1_2 IP runs (partial block; EV and NFX1_1 IP runs annotated on deposited names by campaign-owner decision)

| field | value |
|---|---|
| Deposited | 84 SILAC RAW `20150422_GJ_U{1..6}_{1..14}.raw` (Q Exactive; `txt_SILAC.rar`: Multiplicity 2, Labels1 Arg10;Lys8) + 6 label-free IP RAW `20181216__Ludayun_293T_Over_{EV,NFX1_1,NFX1_2}_{Up,Down}.raw` (Q Exactive HF; `txt_IP.rar`: Multiplicity 1, experiments EV / NFX1_1 / NFX1_2, fractions Up=1, Down=2). |
| Annotated | SILAC: all 84 runs in `annotations/PXD012871.sdrf.tsv` (168 rows). IP: the 4 EV and NFX1_1 runs in `annotations/PXD012871-ip.sdrf.tsv` (4 rows, label free; manifest `annotations/PXD012871-ip.evidence.json`). These follow the deposited names by campaign-owner decision. Bait/prey data support that deposited EV has no bait (NFX1 0 vs 1.93e9; co-IP USP9X 0 vs 8.4e7). The authors' own MaxQuant search (txt_IP parameters.txt, 02/21/2019) already used the deposited names. |
| Blocked (whole runs) | `20181216__Ludayun_293T_Over_NFX1_2_Up.raw`, `20181216__Ludayun_293T_Over_NFX1_2_Down.raw`. The raw headers name three distinct samples: deposited `EV_*` was acquired as `..._Over_NFX1_Ub_*`, `NFX1_1_*` as `..._Over_NFX1_*`, and `NFX1_2_*` as `..._Over_EV_*`. Deposited EV has no bait, so NFX1_2 is most likely the `NFX1_Ub` (ubiquitination) sample. Its ubiquitin protein group is 9.03e9 against 6.98e8 in NFX1_1 (about 13×) and 4.06e8 in EV. Ubiquitin is 2.44–2.46% of run intensity in NFX1_2_Up against 0.07–0.12% in the EV and NFX1_1 runs. Its bait NFX1 is 1.53e8, about 12× less than NFX1_1. It is neither a documented control nor a defensible replicate of NFX1_1. |
| SDRF would need | What NFX1_2 is (e.g. Flag-NFX1 IP from a ubiquitination experiment, and its treatment), so that it can be added to `PXD012871-ip.sdrf.tsv` with its own factor value. |

**Sources checked:** PRIDE record and file list (92 files); paper (closed access, abstract only); MaxQuant `txt_IP.rar` summary/parameters/proteinGroups/evidence; raw headers of all 6 IP files; independent reviews `annotations/PXD012871.review.md` and `annotations/PXD012871-ip.review.md`.

**Unblocked by:** an author statement on what the NFX1_2 sample is and why the IP files were renamed.

## PXD022482 — Cell surface proteome of multiple myeloma (Ferguson et al., Nat Commun 2022; SILAC LenR vs WT + label-free CSC), label-free runs excluded (excluded runs, not a blocker)

**Annotated:** the SILAC lenalidomide-resistance arm — 16 raw files (NCI-H929 and OPM-2, LenR vs parental, 4 mixtures × tryptic + PNGase F fractions), 32 rows in `annotations/PXD022482.sdrf.tsv`. The channel map is explicit in the deposited `MMLenalidomideResistantfiledescription.csv` ("Resistent line SILAC label") and was checked against the deposited Skyline ratios (CD33 / PTPRC and Supplementary Data 6).

**Excluded runs (out of scope for the SILAC campaign, not missing evidence):** 47 label-free cell-surface-capture runs searched in MaxQuant 1.6.2.1 (summary Multiplicity 1; `summary_MM_Leukemia.txt`, `summary_PI_resistant.txt`, `summary_Small_Molecule.txt`; sample identities in `MM_surfaceome_sample_list.xlsx`): Q20180308-22, Q20180324-07, Q20180324-09, Q20180410-05, Q20180420-03, Q20180428-11, Q20180430-01, Q20180512-03, Q20180512-05, Q20180512-07, Q20180512-09, Q20180512-11, Q20180512-13, Q20180720-04, Q20180720-06, Q20180720-08, Q20180720-10, Q20180722-15, Q20180801-03, Q20180801-05, Q20180810-10, Q20180810-16, Q20180811-01, Q20180811-03, Q20180811-05, Q20180811-07, Q20180811-09, Q20180811-11, Q20180811-13, Q20180818-06, Q20180818-08, Q20181215-03, Q20181215-04, Q20181215-05, Q20181215-07, Q20181215-09, Q20190113-04, Q20190113-05, Q20190113-07, Q20190113-09, Q20190124-05, Q20190124-07, Q20190124-09, Q20190124-11, Q20190125-03, Q20190125-05, Q20190125-07 (.raw). They would go in a separate label-free SDRF (`PXD022482-lfq.sdrf.tsv`, batch rule 12). Note for whoever annotates them: the sample list calls Q20190124-07 "L363 CarfR rep1" while `summary_PI_resistant.txt` names it "ARH CarfR 0124-07".

**Would be fully settled by:** a label-free annotation pass of the 47 runs.

## PXD018566 — Rewiring of B cell receptor signaling by EBV LMP2A (Fish et al., PNAS 2020; triple-SILAC phospho/proteome, human LCLs + mouse lymphoma B cells), mouse arm only (partial block)

**Annotated:** `annotations/PXD018566.sdrf.tsv` covers the 183 human LCL runs (proteome 5 x 23 gel slices, GPome 4 x 14 hpHRP fractions, two pYome sets of 3 samples x 2 injections). Their channel map is explicit in Fig. 1A (Light = LMP2A-KO, Medium = EBV-WT, Heavy = LMP2A-KO + 5' anti-BCR) and Fig. 1D (second pYome set: Heavy = EBV-WT + 5' BCR), confirmed against the deposited ratio tables.

**Blocked (36 SILAC raws, mouse lambda-MYC / LMP2A-lambda-MYC tumour B-cell lines):**
- Mouse GPome (28): `YLJI_310717_040817_FISH_GP9_TiO2_Phos_frac{5..17,54}{a,b}.raw` — matches `fc180214_gpome_mouse.csv` (M_L_r1-2, H_L_r1-2).
- Mouse pYome (8): `J_Corso_291116_LMP2A_6_pY_1/2.raw`, `J_Corso_291116_LMP2A_7_pY_1/2.raw`, `J_Corso_161317_pY_MYC_8_1_1/2.raw`, `J_Corso_161317_pY_MYC_9_1_1/2.raw` — presumably `fc171021_pyome_mouse.csv` (M_L_r1-4, H_L_r1-4), but 8 runs vs 4 replicate columns are not mapped, and the `LMP2A`/`MYC` run names are not explained.

**Why:** the paper names the three mouse conditions (MYC-expressing cells unstimulated, MYC cells 5-min anti-IgM BCR-stimulated, unstimulated MYC/LMP2A cells; Results and Methods) but no source assigns them to SILAC Light/Medium/Heavy. The mouse figure (SI Appendix Fig. S2) and Datasets S3/S4 are only in the SI, which is behind a PMC proof-of-work bot check (`pmc.ncbi.nlm.nih.gov/articles/instance/7584892/bin/*`) and a pnas.org 403; not bypassed. PRIDE protocol describes only the LCL mixes.

**Data hint for whoever unblocks (not a source):** in the deposited mouse csvs, H/L carries the BCR signature (pYome Syk Y519/Y520 ~13-15x, Cd79a Y204 8.2x; GPome Syk Y623/Y624 13-20x), while M/L shows lower Cd79a Y204 (0.41) and Prkcd pY (0.19-0.35), which the paper attributes to LMP2A. That fits Light = MYC unstimulated, Medium = MYC/LMP2A, Heavy = MYC + BCR (the LCL layout), but needs Fig. S2 / Dataset S3-S4 headers or the authors to confirm, plus the pYome run-to-replicate map.

**Unblock:** SI Appendix (pnas.2007946117.sapp.pdf) Fig. S2 legend/axes and Dataset S3/S4 column headers, or the authors (Oellerich lab / Yanlong Ji, submitter).

## PXD023565 — HIV-1 / NLRX1 / FASTKD5 immunometabolism in Jurkat cells (Guo et al., Nat Immunol 2021; SILAC 3plex + TMT11plex), TMT arm excluded (out of scope, not a block)

| field | value |
|---|---|
| Deposited | 69 files: 41 SILAC 3plex RAW `2017*_Ting_{1,2,3}_*.raw` (Q Exactive; sets 1–3 of sh-Ctr / sh-NLRX1#1 / sh-NLRX1#2 Jurkat, HIV-1 infected vs mock), 24 TMT11plex RAW `20200718_Haitao_TMT_F1–F24.raw` (sh-FASTKD5 vs control, infected/mock; Q Exactive HF-X per paper), MaxQuant `parameters_NLRX1.txt` / `proteinGroups_NLRX1.txt` (SILAC, HIV-only FASTA) and `parameters_FASKD5.txt` / `proteinGroups_FASTKD5.txt` (TMT, Reporter intensity 1–8). |
| Annotated | All 41 SILAC runs × 3 channels = 123 rows: `annotations/PXD023565.sdrf.tsv`. Channel map from Supplementary Table 4 ratio headers, checked against HIV-1 Pol/Gag (light) and NLRX1 knockdown ratios. Raw→set map (`Ting_n` = SILAC set n) is a documented inference (manifest limitation). |
| Excluded runs (out of campaign scope) | The 24 TMT11plex runs `20200718_Haitao_TMT_F1.raw` … `20200718_Haitao_TMT_F24.raw` (24 high-pH fractions of one TMT11plex mixture). Not a SILAC experiment, so not annotated in this SILAC campaign. |
| A TMT SDRF would need | The TMT11 channel→sample map (8 used reporter channels per `proteinGroups_FASTKD5.txt`; Supplementary Table 6 / Fig. 7c give sh-FASTKD5 vs sh-Ctr, infected vs mock, 2 biological replicates, but no channel numbers were checked here). Technical values: MaxQuant 1.6.10.43, Carbamidomethyl fixed, Oxidation (M) + Acetyl (Protein N-term) variable, human UP000005640, 100-min gradient on Q Exactive HF-X (paper Methods). |

**Sources checked:** PRIDE v3 project + files; paper PMC8087183 (PMC OA S3 text) and its supplementary xlsx (Supplementary Tables 4 and 6, Source Data Fig. 4); both MaxQuant parameters/proteinGroups files; HTTP-range headers of all 41 SILAC raws.

## PXD021351 — HSV-1 whole-cell and plasma membrane proteomics / pUL56–GOPC (Soh et al., Cell Rep 2020; triple-SILAC PMP + triple-SILAC GFP-Trap IP + TMT), TMT runs excluded (excluded runs, not a blocker)

**Annotated:** both SILAC experiments (10 raw files, 30 rows). `annotations/PXD021351-pmp.sdrf.tsv` — Experiment 4, HaCaT plasma membrane profiling 6 hpi, light = mock, medium = HSV-1 KOS WT, heavy = HSV-1 KOS ΔUL56 (MOI 10): `SILAC_PMP_UL56_WT_Unfrac.raw` (mixture 1) and `SILAC_PMP_UL56_WT_F1..F6.raw` (mixture 2, tip-SCX fractions). `annotations/PXD021351-ip.sdrf.tsv` — Experiment 2, HEK293T GFP-Trap IP, light = GFP in all replicates; `SILAC_IP_Exp2/Exp3.raw`: medium = pUL56(1-207)-GFP, heavy = GFP-pUL56(1-234); `SILAC_IP_Exp1.raw` is a medium/heavy label swap (medium = GFP-pUL56(1-234), heavy = pUL56(1-207)-GFP). Channel maps: the deposited `Detailsofsamplesandrawfiles.docx` gives one map for all three IP replicates, which is wrong for Exp1; paper Table S4 (PMC7539533 mmc5.xlsx column headers "Exp 1 log2 (H/L)" vs "Exp2/3 log2 (M/L)" for UL56(1-207)-GFP) and the 1-234-only peptide QGCCGVVWR (medium-dominant in Exp1, heavy-dominant in Exp2/3) establish the swap. The PMP map (docx) agrees with the deposited MaxQuant ratios.

**Excluded runs (out of scope for the SILAC campaign, not missing evidence):** 34 TMT raw files searched with MassPike/Sequest (channel maps are in `Detailsofsamplesandrawfiles.docx`):
- Experiment 1 (WCL time course, TMT10): `WCL_HSV_timecourse_Unfrac`, `_F1`..`_F10`, `_F11_1`, `_F11_2`, `_F12_1`, `_F12_2` (.raw, 15 files);
- Experiment 3 (WCL WT vs ΔUL56, 6 TMT channels): `WCL_UL56_WT_F1`..`_F12` (.raw, 12 files);
- Experiment 5 (GOPC-KO PMP, 4 TMT channels): `PMP_GOPC_KO_Unfrac`, `PMP_GOPC_KO_F1`..`_F6` (.raw, 7 files).
They would go in a separate TMT SDRF (batch rule 12).

**Not annotatable:** the combined SILAC MaxQuant search also contains `Exp2_2018_singleshot_SILAC_LMH_Mock_WT_dUL56` (MaxQuant experiment 5, fraction 55), which was not deposited.

---

## PXD038541 — Protein turnover in fibroblasts from T1DM patients with/without diabetic nephropathy (Di Camillo et al., IJMS 2023; dynamic SILAC Lys6) — RESOLVED, nothing blocked

**Status:** resolved after the round-1 review. All 312 RAW files are annotated in `annotations/PXD038541.sdrf.tsv` (624 rows). Factors: `factor value[disease]` and `factor value[sampling time]` (4 / 7.5 / 24 hour).

**What had been blocked:** the per-subject DN vs diabetic-control assignment. The deposit codes subjects as cellNNN; the paper and Tables S1–S5 code them as Diab1–5 / Nephro1–5. No source states the link between the two.

**How it was resolved:** by a data-derived identity match, not an author key.
- Per-subject turnover k was recomputed from the H/L ratios in all 30 deposited msf files (paper eq. 5).
- Each culture matches exactly one per-subject k column of Table S2: best median |ln k ratio| 0.024–0.038, against ≥ 0.077 for every other column.
- The matches form a one-to-one assignment.
- The reviewer and the producer reached the same key with independent implementations.

**Key:**

| group | subjects |
|---|---|
| Diab (diabetic control) | Diab1 = cell268, Diab2 = cell160, Diab3 = cell36, Diab4 = cell42, Diab5 = cell504 |
| Nephro (type 1 diabetes nephropathy, EFO:0004996) | Nephro1 = cell515, Nephro2 = cell325, Nephro3 = cell511, Nephro4 = cell80, Nephro5 = cell304 |

**Would be strengthened by:** an author-confirmed key.

**Also noted (not blocking):** `07Mar2013_Blank_02.RAW` was searched (in `07Mar2013_Prot_turn_cell42_24h_tot_bis.msf`) but not deposited.

---

## PXD035841 — PDE inhibitors / stress resilience in ARPE-19 cells and Abca4-/-Rdh8-/- retina (Luu et al., PNAS 2023; "SILAC" ARPE-19 arm + label-free mouse retina proteome/phosphoproteome), whole dataset (50 RAW)

**Not annotated. The deposited SILAC search is not multiplexed (multiplicity 1), and nothing documents the SILAC channel→condition map. The mouse arms are label-free, so they are out of scope for this SILAC campaign.**

| | |
|---|---|
| Publication | Luu JC *et al.*, Proc Natl Acad Sci USA 2023 120(19):e2221045120, PMID:37126699, PMC10175720 (OA; JATS from Europe PMC, SI Appendix `pnas.2221045120.sapp.pdf` from PMC OA S3 `PMC10175720.1/`) |
| Deposited | 50 RAW + 4 MaxQuant `mqpar` XMLs (`SILAC-proteomics.xml`, `proteomics.xml`, `phosphoproteomics1.xml`, `phosphoproteomics2.xml`) + `checksum.txt`; FTP root `pride/data/archive/2024/01/PXD035841/`. There is no search output (no txt/summary/proteinGroups) and no experimental design file. |
| SILAC arm | 2 RAW: `SILAC_PROTEOMICS_A.raw`, `SILAC_PROTEOMICS_H2O2.raw` (ARPE-19, Arg10/Lys8, Orbitrap Fusion Lumos) |
| Excluded, out of scope (label-free, mouse) | 48 RAW: `retina_Pro_{1d1-3,BC1-3,NB1-3}`, `retina_Phos_{1d1-3,BC1-3,NB1-3}`, `proteomics_{1d4-6,BAY1-3,NB4-6,Roli1-3,Vard1-3}`, `Phos_{1d4-6,Bay1,Bay2,BAY3,NB4-6,Roli1-3,Vard1-3}`. `proteomics.xml` searches the `Pro_*` runs at multiplicity 1, no labelMods, against `uniprot_sp_mouse_20180521.fasta`. |

Why the SILAC arm is blocked:
- **The deposited search is not multiplexed.** In `SILAC-proteomics.xml` (sha1 a310bd53…, which matches `checksum.txt`), both files are in parameter group 0 with `<multiplicity>1</multiplicity>` and `<labelMods><string>Arg10;Lys8</string></labelMods>`. That is a single-state search with heavy Arg/Lys as the only label. The experiments are named `A` and `H2HO`. The fasta is `uniprot-all-human-20207-2015.7.21.fasta`, MaxQuant 1.5.2.8. This conflicts with the PRIDE data protocol and the SI Methods, which say "The multiplicity was set to two for the samples labeled with 13C615N2-L-lysine and 13C615N4-L-arginine". Under campaign rule 14, the deposited mqpar does not show multiplicity > 1. It cannot be confirmed from the raw files here, because no Thermo RAW reader is available (techsdrf cannot be installed).
- **No channel map.** The PRIDE sample protocol and the SI ("Proteomics analyses") say only that cells were grown in "heavy (13C15N) or light lysine and arginine" (Thermo kit A33972) and that "equal protein amounts of each cell lysate were mixed". Neither says which condition (atRAL 60 µM, H2O2 5 mM, or vehicle/DMSO) is heavy or light in either file. The supplement deposits no ratio table: SI Table 1 and SI Fig. S3C are rendered figures/legends, with no H/L column headers.
- **The design does not match the deposit.** The paper and SI Table 1 legend describe five comparisons against vehicle-treated controls: atRAL, H2O2, BAY 60-7550, rolipram and BC11-38 ("unstressed, drug-treated cells relative to unstressed, vehicle-treated controls; and in stressed cells relative to unstressed controls"). Only two SILAC runs are deposited, both stress conditions, and there are no SILAC runs for the PDE-inhibitor treatments. Nothing states the replicate count for the ARPE-19 SILAC arm.

**Unblocked by:** an author statement or deposited design giving (i) which channel is vehicle and which is atRAL / H2O2 in `SILAC_PROTEOMICS_A.raw` and `SILAC_PROTEOMICS_H2O2.raw`, and (ii) the actual MaxQuant multiplicity, or a multiplicity-2 search output (`summary.txt` / `evidence.txt` with H/L ratios). The paper's PDE-inhibitor SILAC runs would also need to be deposited. The mouse retina arms could be annotated as a label-free SDRF outside this campaign. That would need the code map: `1d` = 1 day after bright light? `NB` = no bright light? `BC`/`BAY`/`Roli`/`Vard` = inhibitor-treated? `Vard` (vardenafil?) is not mentioned in the paper. These codes are not defined anywhere in the deposit.

## PXD025781 — LSD1-directed therapy in glioblastoma, histone PTMs (Faletti et al., Sci Transl Med 2021; histone super-SILAC spike-in), mouse-xenograft tissue arm (partial block)

**Annotated:** the 20 `HF*` cell runs (human GBM TIC cultures 605051, BT165, 700142, 906080, 606012 treated with LSD1i DDP_38003 or DMSO; light = sample, heavy = histone super-SILAC internal standard; MaxQuant `txt_cells.zip`) → `annotations/PXD025781.sdrf.tsv`.

**Blocked (sample identity undocumented):** the 18 brain-tissue runs `QEPLus_210305_RN_glio_1.raw` … `QEPLus_210305_RN_glio_18.raw` (PRO-PIC derivatisation, EpiProfile 2.0 SILAC mode, `tissue.zip`; they are SILAC: LightR/HeavyR against the heavy internal standard). The run names carry only a number. Nothing in the deposit (protocol, `tissue.zip` histone_ratios*.xls / histone_logs.txt / rawInfo) or in the accessible author postprint maps a run to normal vs tumour tissue, vehicle vs LSD1i, or mouse; Fig. 1E gives only group sizes (normal and tumour tissue, vehicle n = 12, LSD1i n = 6). The Supplementary Materials at science.org returned HTTP 403 (not bypassed). **Needed to unblock:** a run → (mouse, tissue normal/tumour, treatment) table from the authors or the Supplementary Materials.

---

## PXD013461 — BRAF fusion partners / dox-inducible BRAF constructs in HEK293 (Stangl et al., Mol Cancer Res 2020; SILAC Arg10/Lys8 phosphoproteome), experiments S13–S14 only (partial block)

**Annotated:** experiments S1–S12 (36 RAW, 72 rows) in `annotations/PXD013461.sdrf.tsv`. **Blocked:** the 6 RAW of experiments S13 and S14:
`20181213_F1_RM_CHS_0200_TIO2_RVhPH_S13_F1.raw`, `20181213_F1_RM_CHS_0200_TIO2_RVhPH_S13_F2.raw`, `20181213_F1_RM_CHS_0200_TIO2_RVhPH_S13_F3.raw`, `20181213_F1_RM_CHS_0200_TIO2_RVhPH_S14_F1.raw`, `20181213_F1_RM_CHS_0200_TIO2_RVhPH_S14_F2.raw`, `20181213_F1_RM_CHS_0200_TIO2_RVhPH_S14_F3.raw`.

Why they are blocked:
- No source gives the experiment → construct / orientation map. For S1–S12 it was derived from the data: transgene-product peptides, BRAF N-terminal coverage against the construct start codons in the AACR figshare construct table, and the rank order of phosphosite counts against Supp Fig S3D. The details are in `PXD013461.evidence.json`.
- By elimination, S13/S14 are the 7th line, pInducer20-GFP. No BRAF or partner peptide changes in them; the median log2 H/L of BRAF aa 380–766 is +0.04 / +0.12.
- GFP is not in the searched human FASTA, so no transgene peptide shows which SILAC channel got doxycycline. ERK sites move in the same direction in both experiments (MAPK1 Y175 +1.03 / +1.35), so they do not show the orientation either.
- Rows with treatment `not available` would pool the dox and vehicle cultures (campaign rule 7).

**Recorded source conflict in the annotated part (review F1, round 2):** S7/S8 are annotated BRAF-WT and S9/S10 BRAF-kinase (aa 381–766).
- **Supporting this assignment:**
  - the construct sequence: the kinase construct starts at BRAF aa 381 and cannot yield the N-terminal BRAF S151/S363/S365 peptides that are dox-induced in S7/S8;
  - Supp Fig S6C (pERK);
  - Supp Fig S3C (KSEA).
- **Against it:** the authors' BRAF-Kinase profile in Supp Fig S3B/D matches S7/S8. That profile is 8 sites (37.5% shared), no MAPK rows, and the kinase-only marker RAF1 S465, which is induced only in S7/S8.
- **Decision:** the sequence evidence was given priority (rule 6), and the coordinator decided to keep S7–S10 with the conflict documented in `PXD013461.evidence.json` and the report.

**Unblocked by:** an author statement of the forward/reverse (heavy = +dox) assignment for S13 and S14, or any experiment key. An author-confirmed key for S1–S12 would also firm up the data-derived map. Its weakest link is BRAF-WT (S7/S8) vs BRAF-kinase (S9/S10), so author confirmation of S7–S10 especially is requested. WT vs V600E is supported by the Fig S3B V600E markers CDC27 S364 and MARCKS S101.

## PXD029030 — miR-31-5p metabolic switch in psoriatic keratinocytes (Wang et al., EMBO Mol Med 2023; SILAC Arg10/Lys8, HEK293T + HaCaT), "L125" SCX experiments and the whole Velos search (partial block)

**Annotated (not blocked):** 22 RAW `20161111_F1_RM_RH_SCX_2_1..11` and `20161111_F1_RM_RH_SCX_4_1..11` (MaxQuant experiments b and d of `20161111_F1_RM_RH_SCX_L125_L31.zip`) = HEK293T miR-31-5p mimic vs control mimic, in `PXD029030.sdrf.tsv`. Their cell line and orientation are taken from the match of the deposited ratios to Dataset EV1 HEK 293T (r = -0.95 / +0.96) and from the deposited Perseus lists L31up/L31down.

**Blocked runs (106 of 128 RAW):**
- 22 RAW `20161111_F1_RM_RH_SCX_1_1..11` and `20161111_F1_RM_RH_SCX_3_1..11` (Orbitrap Fusion; MaxQuant experiments a and c of the same search).
- 80 RAW of the LTQ Orbitrap Velos search `20170620_V1_MJW_0083.zip`: `20170609_V1_MJW_0083_C1..C12, D1..D8` (experiment CD), `20170609_V1_MJW_0083_G1..G12, H1..H8` (GH), `20170620_V1_MJW_0083_A1..A12, B1..B8` (AB) and `20170620_V1_MJW_0083_E1..E12, F1..F8` (EF).
- 4 Velos RAW `20170609_V1_MJW_0083_1..4`. They are in no `summary.txt`, so they were never searched.

**Blocker 1: experiments a and c (SCX_1, SCX_3) are named only "L125".**
- The zip is called `SCX_L125_L31`, and the Perseus lists are called `L125up.txt` / `L125down.txt`.
- Neither the paper nor the PRIDE record mentions any miRNA other than miR-31.
- The PRIDE/paper SILAC protocol mentions miR-130a and miR-708. That text is evidently copied from another study.
- So the treatment of these cultures (which miRNA "125" is) is undocumented. The light/heavy orientation could be read from the L125 lists (a negative, c positive), but not what it means.

**Blocker 2: the Velos search (AB, CD, EF, GH) has no documented cell line or conditions.**
- The paper's SILAC Methods name only an Orbitrap Fusion. These runs are Velos CID runs (raw header "LTQ Orbitrap Velos MS", method LC120m_60K/100K_Top15_CID35).
- Their ratios do not reproduce Dataset EV1 HaCaT (best combined r = 0.29, n = 533). GLUL fits miR-31 light in AB/CD and heavy in EF/GH, but ANKRD52 is opposite.
- They correlate with the "L125" experiments (a~AB 0.29, c~GH 0.28) and not with the miR-31 experiments (|r| <= 0.12).
- They may be the HaCaT miR-31 SILAC of Fig EV1E, or the miR-130a/miR-708 mixtures named in the protocol; no source settles which, or which channel is which.

**Unblocked by:**
- an author statement or sample sheet giving, for each MaxQuant experiment (a, c, AB, CD, EF, GH), the cell line, the miRNA mimic and the label orientation;
- for the 4 unsearched Velos RAW, additionally a statement of what they are. They would get tolerances `not applicable` if annotated, since no search output covers them.

**Excluded (not runs):** `20161111_F1_RM_RH_SCX_L125_L31.zip`, `20170620_V1_MJW_0083.zip` (MaxQuant search output).

## PXD016505 + PXD016512 — EGFR network rewiring in KRAS G13D colorectal cancer cells (Kennedy et al., Nat Commun 2020; triple-SILAC FLAG AP-MS, HCT116 vs HKE3), 1 stub raw excluded (excluded runs, not a blocker)

**Annotated:** all 350 RAW of PXD016505 (`annotations/PXD016505.sdrf.tsv`, 1050 rows) and 278 of 279 RAW of PXD016512 (`annotations/PXD016512.sdrf.tsv`, 834 rows). Channel map from the deposited `PRIMESDataSILACLabelExperiemntaldesign.txt` = Supplementary Methods 9 (FOR: H = HCT116 bait, M = HKE3 empty vector, L = HKE3 bait; REV: H = HKE3 bait, M = HCT116 empty vector, L = HCT116 bait).

**Excluded run:**
- PXD016512 `LDY1357-S24-A-PRKCA-R-4_010.raw` — a 39,754-byte stub (FTP Content-Length and PRIDE fileSizeBytes 39754): raw header only, no scans, nothing to search. Its header name is `LDY1357-S24-A-PRKCA-R-4.raw` (vial BE8); the deposited `LDY1357-S24-A-PRKCA-R-4.raw` is the complete acquisition of that slot.

**Annotated but not matched one-to-one to a search experiment** (no mqpar.xml / summary.txt deposited; all carry the search parameters, recorded as manifest limitations):
- PXD016505 HDAC1 FOR: 6 Velos raws vs 5 Velos-scale HDAC1FOR experiments — one Velos run unaccounted for (includes `LDY1098-S23-A-HDAC-F-2-No.raw`, first acquisition of vial BB4 slot S23, now annotated as technical replicate 2 of `HDAC1_LDY1098_FOR_pool1`).
- PXD016512 PRKCA REV: 8 Velos raws vs 7 Velos-scale KCAREV experiments — one Velos run unaccounted for. `ALI1442-S18-A-KCA-R.raw` (Q Exactive Plus) was searched (KCAREV1 summed intensity 4.68e11, QE scale) and is annotated.

**Out of scope, not blocked:** the further AP-MS deposits PXD016461–PXD016465 (and PXD016549, PXD016431) of the same paper. 17 RAC1 raws are deposited in both PXD016505 and PXD016512 and are annotated in both SDRFs.

**Unblocked by:** the MaxQuant `mqpar.xml` / `summary.txt` (experiment → raw file assignment) of the searches.

## PXD020108 — Third-generation EGFR TKI resistance proteome/phosphoproteome (Zhang et al., Cancer Res 2021; triple-SILAC H1975 vs AZR3/AZR4 and COR1/COR10), 14 raws of unresolved sample identity (partial block)

**Annotated:** 652 of 666 deposited raws (`annotations/PXD020108.sdrf.tsv`, 1956 rows). **Blocked (sample identity conflicts between raw name and every deposited MaxQuant file):**

| raw file(s) | name says | deposited `mqpar.xml` + `experimentalDesignTemplate.txt` say |
|---|---|---|
| `R4_F9.raw` | rociletinib replicate BR4 / R4 series | experiment `H1975_COR1_COR10_CO1686_pST_BR3` (search `H1975_COR1_COR10_pST_roci`) |
| `Xu-BR4-1.raw` … `Xu-BR4-12.raw` (12) | BR4 | experiment `H1975_COR1_COR10_CO1686_pST_BR3` (search `H1975_COR1_COR10_pST_roci`) |
| `H1975_COR1_COR10_CO1686_BR3_pY100_2ndbinding_a.raw` | BR3 | experiment `H1975_COR1_COR10_CO1686_0708` (search `H1975_COR1_COR10_pY_roci`) |

Annotating them under either label would assert a biological replicate the deposit does not settle. **Unblock with:** an author statement (or a sample sheet) saying which SILAC mix (BR3 vs BR4; BR3 vs 0708) these runs came from.

**Not deposited:** `H1975_AZR3_AZR4_SILAC_pY_R1/R2/R3.raw` are listed in `H1975_AZR3_AZR4_pY_osi_mqpar.xml` but absent from the archive (no rows; nothing to unblock).

**Open but annotated (recorded in the manifest limitations, not blocked):** the AZR set's 2018 Q Exactive HF `*_Total` proteome mixes and 2018 pY mixes carry no label tying them to the Orbitrap Elite R1-R3 mixes, so they got their own biological-replicate numbers; the paper reports three AZR biological replicates.

## PXD011013 — Tunneling nanotubes / stroma-to-CML protein transfer (Kolba et al., Cell Death Dis 2019; trans-SILAC HS-5 → K-562), 8 single-shot `zar` runs (partial block / excluded runs)

**Annotated:** the trans-SILAC arm — 24 raw files (`20171204_Q1_AWH_ColID_501_PojID_936_Proteomics_sample_1..24`, experiments plus_01/minus_01/plus_02/minus_02 × 6 SDS-PAGE slices), 48 rows in `annotations/PXD011013.sdrf.tsv`. Heavy (Lys8/Arg10) = HS-5 donor-derived proteins, light = acceptor K-562 proteome, per the paper's Methods; plus/minus = DiD+/DiD− sorted acceptor cells (samplenames.xls; checked against heavy content in the deposited proteinGroups).

**Excluded (channel identity undocumented, batch rule 7):** `710072209zar_k562_A.raw`, `710072210zar_k562_B.raw`, `710072211zar_k562IM_A.raw`, `710072212zar_k562IM_B.raw`, `710072213zar_HS5_A.raw`, `710072214zar_HS5_B.raw`, `710072215zar_HS5IM_A.raw`, `710072216zar_HS5IM_B.raw`. These are single-shot in-solution digests of K-562 and HS-5 ± imatinib (raw headers: Q Exactive + nanoAcquity, unlike the trans-SILAC runs on a Q Exactive Plus). `samplenames.xls` marks the four `+IM` runs "not discussed in this manuscript"; the paper never describes the other four. They were searched in the same MaxQuant 1.6.0.1 session (parameter group 0, multiplicity 2, Arg10;Lys8, LFQ on), but no source says whether, or which, cells were SILAC-labelled. The data show no heavy-labelled material: light is 98.1–99.3% of summed L+H protein-group intensity in all eight, the HS-5 runs included. A heavy channel with no documented content cannot be annotated, and declaring them label-free would contradict the deposited search.

**Also recorded:** PXD013504 is a byte-identical (SHA-1) subset of this deposit's 24 trans-SILAC runs; see `annotations/DUPLICATES.md` Group 10.

**Would be settled by:** an author statement of what the eight `zar` samples are (mono-cultures or sorted co-culture populations, labelling state of each), or a label-free annotation pass if they are confirmed unlabelled.

---

## PXD002454 — EV71-infected U251 glioma cells (Zhang et al., Proteomics 2015; triple-SILAC mock / 8 hpi / 20 hpi), whole dataset (15 WIFF runs)

**Not annotated. The dataset is genuine triplex SILAC, but no accessible source says which SILAC channel (light / Lys4-Arg6 medium / Lys8-Arg10 heavy) carries mock, EV71 8 hpi or EV71 20 hpi. Campaign rules 6–7 therefore block every run.**

| | |
|---|---|
| Publication | Zhang LK, Lin T, Zhu SL, Xianyu LZ, Lu SY. *Proteomics* 2015 15(22):3784-3796, doi:10.1002/pmic.201500134, PMID:26350028. **Closed access**: no PMCID, Europe PMC `inEPMC=N`, `hasSuppl=N`; Unpaywall `oa_status=closed`; Semantic Scholar `openAccessPdf` CLOSED; Wiley full text returned a 403 bot check (not bypassed). Only the abstract was read. |
| Deposited | 15 `.wiff` + 15 `.wiff.scan` (`20140418_{A,B,C}N{1-5}`) = 3 biological replicates (A, B, C) × 5 SCX fractions, TripleTOF 5600; 3 ProteinPilot 5.0 FDR reports `20140418_{A,B,C}N1__FDR.xlsx` (one per replicate group, 5 input files each). No experimental-design file, no channel annotation. FTP root `pride/data/archive/2015/09/PXD002454/`. |
| SILAC verified (rule 14) | All three FDR reports: Search Summary `Sample Type = SILAC (Lys+4D, Arg+6)(Lys+8, Arg+10)`; Protein Summary has `M:L` and `H:L` ratio columns (light = denominator). Database `Uniprot_Human(reviewed)_201412.fasta`, 20188 entries, which includes one EV71 entry (`gi|530307006 polyprotein [Enterovirus A71]`). |

Why blocked:
- **No explicit channel map.** PRIDE sample protocol: "Differentially SILAC labeled U251 cells were mock treated or EV71 infected … mixed at 1:1:1 ratio … 5 fractions with SCX … Three independent biological replicates". The abstract names the conditions (8 and 20 hpi vs mock) but not their labels. The paper Methods/figures, which probably hold the map, could not be read (closed access, 403). The WIFF headers hold only `Sample Name:20140418_AN1` etc. The ProteinPilot reports name only the channels (L/M/H) and contain no condition names.
- **The data does not settle it.** EV71 polyprotein peptides in the distinct-peptide sheets are mostly medium-labelled (Lys4/Arg6; 10 of 16 identifications over A/B/C), 4 are heavy, and 2 are an unlabelled-K (light) deamidated peptide. The polyprotein has no protein-level ratio (`no quant - weak signal`). That suggests light = mock, but it is not decisive, and it does not tell 8 hpi from 20 hpi. Rule 6 forbids a data-only map.

**Unblocked by:** the paper's Methods or Fig. 1 workflow (Wiley, subscription), or an author statement, giving the label of mock, 8 hpi and 20 hpi. It should be cross-checked against the viral-peptide labels above and against TRAF2/TRAF6 up-regulation, which the paper reports. With the map, the SDRF would be: 15 runs × 3 channels = 45 rows; human + cell-lines (U251, check the Cellosaurus U-251MG vs U251 problematic-line entries); custom `characteristics[infection]` (Enterovirus A71, NCBITaxon:39054, OLS4-verified) with factor values for infection status and time post infection; fraction 1-5 per replicate; ProteinPilot 5.0 Paragon search (Advanced Metadata: MS1 initial tolerance 0.05 Da, MS2 initial tolerance 0.1 Da; trypsin, iodoacetamide).


---

## PXD008454 — Adaptive resistance to afatinib in PC9 NSCLC cells (Mulder et al., Mol Cancer Res 2018; SILAC Arg6/Lys4 full proteome + label-free kinobead and Fe-IMAC phosphoproteome), label-free runs excluded (excluded runs, not a blocker)

**Annotated:** all 60 SILAC full-proteome raws (`OR13_20161126_TCM_exp19_SILAC-PC9_*`; 12 mixtures 24h/3D/5D/7D x R1-R3, 5 high-pH fractions each; 120 rows) in `annotations/PXD008454.sdrf.tsv`. Channel map heavy = afatinib 10 nM, light = DMSO, stated explicitly in the AACR Supplementary Material and Methods (figshare 22516368, DOI 10.1158/1541-7786.22516368.v1: "Light labelled cells were treated with DMSO, heavy labelled cells were treated with 10 nM Afatinib for 24 hours, 3 days, 5 days or 7 days") and checked against the deposited H/L direction of the proteins the paper names (CAPN2 down; ATP2C1, MARCKS, MARCKSL1, CNN2 up) and the cell-cycle signature. See `PXD008454.evidence.json`.

**Excluded runs (out of scope: not SILAC; PRIDE: "Kinobead data and phospho data was quantified using LFQ"; 39 RAW):**
- Kinobead pull-downs, 15 RAW: `OR13_A2_20161011_TCM_exp15_KBPD_PC9_Afat_24h_R1.raw`, `OR13_A2_20161011_TCM_exp15_KBPD_PC9_Afat_24h_R2.raw`, `OR13_A2_20161011_TCM_exp15_KBPD_PC9_Afat_24h_R3.raw`, `OR13_A2_20161011_TCM_exp15_KBPD_PC9_Afat_48h_R1.raw`, `OR13_A2_20161011_TCM_exp15_KBPD_PC9_Afat_48h_R2.raw`, `OR13_A2_20161011_TCM_exp15_KBPD_PC9_Afat_48h_R3.raw`, `OR13_A2_20161011_TCM_exp15_KBPD_PC9_Afat_72h_R1.raw`, `OR13_A2_20161011_TCM_exp15_KBPD_PC9_Afat_72h_R2.raw`, `OR13_A2_20161011_TCM_exp15_KBPD_PC9_Afat_72h_R3.raw`, `OR13_A2_20161011_TCM_exp15_KBPD_PC9_Afat_7days_R1.raw`, `OR13_A2_20161011_TCM_exp15_KBPD_PC9_Afat_7days_R2.raw`, `OR13_A2_20161011_TCM_exp15_KBPD_PC9_Afat_7days_R3.raw`, `OR13_A2_20161011_TCM_exp15_KBPD_PC9_Afat_DMSO_R1.raw`, `OR13_A2_20161011_TCM_exp15_KBPD_PC9_Afat_DMSO_R2.raw`, `OR13_A2_20161011_TCM_exp15_KBPD_PC9_Afat_DMSO_R3.raw`
- Fe-IMAC phosphoproteome, 24 RAW: `201706011_OR13_A4_NP_TCM_PC9_Af_IMAC_2D-1.raw`, `201706011_OR13_A4_NP_TCM_PC9_Af_IMAC_2D-2.raw`, `201706011_OR13_A4_NP_TCM_PC9_Af_IMAC_30min-2.raw`, `201706011_OR13_A4_NP_TCM_PC9_Af_IMAC_5D-1.raw`, `201706011_OR13_A4_NP_TCM_PC9_Af_IMAC_DMSO-2.raw`, `201706011_OR13_A4_NP_TCM_PC9_Af_IMAC_DMSO-3.raw`, `201706012_OR13_A4_NP_TCM_PC9_Af_IMAC_2D-3.raw`, `201706012_OR13_A4_NP_TCM_PC9_Af_IMAC_30min-3.raw`, `201706012_OR13_A4_NP_TCM_PC9_Af_IMAC_5D-2.raw`, `201706012_OR13_A4_NP_TCM_PC9_Af_IMAC_5D-3.raw`, `201706013_OR13_A4_NP_TCM_PC9_Af_IMAC_2D-2_2_170613191727.raw`, `201706013_OR13_A4_NP_TCM_PC9_Af_IMAC_5D-3_2.raw`, `201706014_OR13_A4_NP_TCM_PC9_Af_IMAC_2D-3_2.raw`, `201706014_OR13_A4_NP_TCM_PC9_Af_IMAC_30min-1_2.raw`, `201706014_OR13_A4_NP_TCM_PC9_Af_IMAC_DMSO-1_2.raw`, `201706015_OR13_A4_NP_TCM_PC9_Af_IMAC_2D-1_2.raw`, `201706015_OR13_A4_NP_TCM_PC9_Af_IMAC_5D-1_2.raw`, `201706015_OR13_A4_NP_TCM_PC9_Af_IMAC_5D-2_2.raw`, `201706015_OR13_A4_NP_TCM_PC9_Af_IMAC_DMSO-2_2.raw`, `201706015_OR13_A4_NP_TCM_PC9_Af_IMAC_DMSO-3_2.raw`, `201706016_OR13_A4_NP_TCM_PC9_Af_IMAC_30min-2_2.raw`, `201706016_OR13_A4_NP_TCM_PC9_Af_IMAC_30min-3_2.raw`, `20170608_OR13_A4_NP_TCM_PC9_Af_IMAC_30min-1.raw`, `20170608_OR13_A4_NP_TCM_PC9_Af_IMAC_DMSO-1.raw`
- Non-run files: SEARCHProteome.zip, SEARCHKinobeads.zip, SEARCHIMAC.zip (MaxQuant output), PEAKProteome.zip, PEAKKinobeads.zip, PEAKIMAC.zip (peak lists).

**Would be annotated by:** a separate label-free SDRF part (`PXD008454-lfq`), outside this SILAC campaign.

**Open points in the annotated part:** whether the 12 DMSO channels are independent cultures is undocumented (Supp M&M: "Per condition, 3 dishes were made for 3 biological replicates"; replicate kept 1-12, sampling time `not available`); precursor tolerance not recorded (MaxQuant 1.5.6.0 txt only, no mqpar.xml).

## PXD002845 — Eutopic vs ectopic endometrial stromal cells, spike-in SILAC standard (Kasvandik et al., J Proteome Res 2016), 45 runs of six undocumented MaxQuant experiments (partial block)

**Annotated:** the 16 study samples named in the PRIDE protocol (healthy EM n=6 `ctrl_euESC_1..6`, endometriotic eutopic EM n=5 `euESC_1..5`, ectopic peritoneal lesions n=5 `ecESC_1..5`), 115 RAW (6 SCX fractions each + 19 re-injections), 230 rows in `annotations/PXD002845.sdrf.tsv`. Light = patient ESC lysate, heavy (Lys8/Arg10) = spike-in standard (2:1 secretory-phase ESC : Ishikawa), per the PRIDE sample protocol.

**Blocked (sample identity undocumented, batch rule 7):** 45 RAW of the MaxQuant experiments `1C8`, `2C2`, `3C2`, `5C8`, `6C2`, `5PEu` — searched in the same MaxQuant 1.4.0.8 session (`kasvandik_et_al_2015_mq_output.zip`, multiplicity 2, Arg10;Lys8) with the same heavy standard, but not mentioned in the PRIDE protocols. The codes (perhaps donor number + a treatment/condition code) are not explained anywhere readable: the paper is closed access, the ACS SI page returned 403 (bot check, not bypassed), and the author's thesis was unreachable. Files: `140623_01_Orbi2_SK_CO_G240_T1275_2C2_1.raw` (2C2 f1), `140623_02_Orbi2_SK_CO_G240_T1275_2C2_2.raw` (2C2 f2), `140623_03_Orbi2_SK_CO_G240_T1275_2C2_3.raw` (2C2 f3), `140623_04_Orbi2_SK_CO_G240_T1275_2C2_4.raw` (2C2 f4), `140623_05_Orbi2_SK_CO_G240_T1275_2C2_5.raw` (2C2 f5), `140623_06_Orbi2_SK_CO_G240_T1275_2C2_6.raw` (2C2 f6), `140628_01_Orbi2_SK_CO_G240_T1275_5C8_1.raw` (5C8 f1), `140628_02_Orbi2_SK_CO_G240_T1275_5C8_2.raw` (5C8 f2), `140628_03_Orbi2_SK_CO_G240_T1275_5C8_3.raw` (5C8 f3), `140628_04_Orbi2_SK_CO_G240_T1275_5C8_4.raw` (5C8 f4), `140628_05_Orbi2_SK_CO_G240_T1275_5C8_5.raw` (5C8 f5), `140628_06_Orbi2_SK_CO_G240_T1275_5C8_6.raw` (5C8 f6), `140701_01_Orbi2_SK_CO_G240_T1275_1C8_1.raw` (1C8 f1), `140701_02_Orbi2_SK_CO_G240_T1275_1C8_2.raw` (1C8 f2), `140701_03_Orbi2_SK_CO_G240_T1275_1C8_3.raw` (1C8 f3), `140701_04_Orbi2_SK_CO_G240_T1275_1C8_4.raw` (1C8 f4), `140701_05_Orbi2_SK_CO_G240_T1275_1C8_5.raw` (1C8 f5), `140701_06_Orbi2_SK_CO_G240_T1275_1C8_6.raw` (1C8 f6), `140703_01_Orbi2_SK_CO_G240_T1275_5PEu_1.raw` (5PEu f1), `140703_02_Orbi2_SK_CO_G240_T1275_5PEu_2.raw` (5PEu f2), `140703_03_Orbi2_SK_CO_G240_T1275_5PEu_3.raw` (5PEu f3), `140703_04_Orbi2_SK_CO_G240_T1275_5PEu_4.raw` (5PEu f4), `140703_05_Orbi2_SK_CO_G240_T1275_5PEu_5.raw` (5PEu f5), `140703_06_Orbi2_SK_CO_G240_T1275_5PEu_6.raw` (5PEu f6), `140707_01_Orbi2_SK_CO_G240_T1275_3C2_1.raw` (3C2 f1), `140707_02_Orbi2_SK_CO_G240_T1275_3C2_2.raw` (3C2 f2), `140707_03_Orbi2_SK_CO_G240_T1275_3C2_3.raw` (3C2 f3), `140707_04_Orbi2_SK_CO_G240_T1275_3C2_4.raw` (3C2 f4), `140707_05_Orbi2_SK_CO_G240_T1275_3C2_5.raw` (3C2 f5), `140707_06_Orbi2_SK_CO_G240_T1275_3C2_6.raw` (3C2 f6), `140709_01_Orbi2_SK_CO_G240_T1275_6C2_1.raw` (6C2 f1), `140709_02_Orbi2_SK_CO_G240_T1275_6C2_2.raw` (6C2 f2), `140709_03_Orbi2_SK_CO_G240_T1275_6C2_3.raw` (6C2 f3), `140709_04_Orbi2_SK_CO_G240_T1275_6C2_4.raw` (6C2 f4), `140709_05_Orbi2_SK_CO_G240_T1275_6C2_5.raw` (6C2 f5), `140709_06_Orbi2_SK_CO_G240_T1275_6C2_6.raw` (6C2 f6), `140815_03_Orbi2_SK_CO_G240_T1275_5C8_2.raw` (5C8 f2), `140815_05_Orbi2_SK_CO_G240_T1275_1C8_2.raw` (1C8 f2), `140815_15_Orbi2_SK_CO_G240_T1275_2C2_2.raw` (2C2 f2), `140815_17_Orbi2_SK_CO_G240_T1275_3C2_2.raw` (3C2 f2), `140815_19_Orbi2_SK_CO_G240_T1275_6C2_2.raw` (6C2 f2), `140820_07_Orbi2_SK_CO_G240_T1275_5PEu_4.raw` (5PEu f4), `140822_09_Orbi2_SK_CO_G240_T1275_1C8_5.raw` (1C8 f5), `140822_13_Orbi2_SK_CO_G240_T1275_2C2_5.raw` (2C2 f5), `140825_05_Orbi2_SK_CO_G240_T1275_5C8_6.raw` (5C8 f6).

**Unblocked by:** the paper's Methods / supplementary sample table (or an author statement) saying what 1C8, 2C2, 3C2, 5C8, 6C2 and 5PEu are (donor, cell type, treatment) and whether they belong to this study. Also missing for the annotated part (recorded as limitations, not blocked): per-patient age / cycle phase / disease stage, and whether euESC_n and ecESC_n come from the same woman.

## PXD006404 — ALK signaling in neuroblastoma NB1 cells (Emdal et al., Sci Signal 2018; triple-SILAC ALK interactome + phosphoproteome, label-free pTyr-peptide pull-downs + proteome), label-free runs excluded (excluded runs, not a blocker)

- Annotated: the 36 triple-SILAC raws (18 `20140128_QE5_UPLC11_DBJ_SA_ALK_IP_*`, 18 `*_ALK_MIX{1,2,3}_{pTYR,TiO2_1st,TiO2_2nd}_*` in two injection series) → `annotations/PXD006404.sdrf.tsv`. Channel map from the PRIDE projectDescription (Experiments 1–3), matched to MaxQuant experiments ALK-IP-E1..E3 / ALK-Phospho-E1..E3 (summary.txt).
- **Excluded runs (out of scope, label-free; summary.txt Multiplicity 1):**
  - 112 `PeptidePulldown` raws (phosphotyrosine interactome, Q Exactive HF): `20150127_QE7_UPLC10_DBJ_SA_PeptidePulldown_A1-1` … `A12-4`, `B1-1` … `B10-4` (88 raws) and `20150205_QE7_UPLC10_DBJ_SA_PeptidePulldown_C3-1` … `C8-4` (24 raws).
  - 28 `NB1proteome` raws (label-free proteome, 2 × 14 high-pH fractions): `20141226_QE3_UPLC9_DBJ_SA_NB1proteome_GndCl1_1` … `_14`, `GndCl2_1` … `_14`.
- They could be annotated as a separate label-free SDRF (`PXD006404-labelfree`): the bait peptide and lysate (DMSO/LDK378, replicate) for each pull-down are given by the PRIDE description (A1–C8 table; -1/-3 DMSO rep 1/2, -2/-4 LDK378 rep 1/2) and the MaxQuant experiment names (`…_C1/_C2/_i1/_i2`).
- Not blocked within the SILAC scope. Open points are in the manifest limitations: inhibitor identity of light vs medium rests on the PRIDE statement (deposited ratios confirm heavy = DMSO only); paper says Q Exactive Plus but raw headers say Q Exactive for 27 of the 36 raws.

## PXD004181 — HSP90 / tonic BCR signaling in Burkitt lymphoma (Walter et al., Blood 2017; triple/double SILAC proteome + pY phosphoproteome, DG75 and Daudi), Daudi `DD` and DG75 `DGI_*` MaxQuant experiments (partial block)

**Annotated:** 14 of 32 RAW → `annotations/PXD004181.sdrf.tsv` (34 rows): MaxQuant experiments `DGII_1`/`DGII_2` (DG75 2-plex, light = DMSO, heavy = HSP90 inhibitor per Methods; compound per experiment not available) and `DG_TelSyk` (DG75 3-plex, light = untreated WT, medium = TEL-SYK-expressing, heavy = BCR-stimulated 5 min per Figure 6B legend). Both maps checked against deposited `proteinGroups.txt` / `Phospho (STY)Sites.txt` ratios.

**Blocked (channel→condition map undocumented, batch rule 7):** 18 RAW.
- `DD` (Daudi, 3-plex Arg0Lys0 / Arg6Lys4 / Arg10Lys8): `KT_Pan_010816_030816_Daudi_hsp90_proteome1.raw`, `KT_Pan_010816_030816_Daudi_hsp90_proteome2.raw`, `KT_Pan_010816_090816_DD_hsp90_pY_1-1.raw`, `KT_Pan_010816_090816_DD_hsp90_pY_1-2.raw`, `KT_Pan_010816_090816_DD_hsp90_pY_2-1.raw`, `KT_Pan_010816_090816_DD_hsp90_pY_2-2.raw`. The text says only "light = DMSO, heavy = AT13387 or STA-9090"; the medium channel and which inhibitor sits in medium vs heavy are in supplemental Figure 1C, which cannot be retrieved. The data show both M and H carry the HSP90-inhibitor heat-shock response (log2 HSPA1A M/L 3.24, H/L 3.45), consistent with AT13387 and STA-9090 in some order.
- `DGI_w` / `DGI_X` / `DGI_Y` (DG75, 3-plex, Jan/Feb 2016, file codes `P-A_w`, `P-A_x`, `P-S_y`): `KT_Pan_260116_090216_proteome_P-A_w-1.raw`, `..._proteome_P-A_w-2.raw`, `..._proteome_P-A_x-1.raw`, `..._proteome_P-A_x-2.raw`, `..._proteome_P-S_y-1.raw`, `..._proteome_P-S_y-2.raw`, `KT_Pan_260116_090216_pY_P-A_w-1.raw`, `..._pY_P-A_w-2.raw`, `..._pY_P-A_x-1.raw`, `..._pY_P-A_x-2.raw`, `..._pY_P-S_y-1.raw`, `..._pY_P-S_y-2.raw`. No retrievable source describes these channels; in each run only one of M/H shows the HSP90-inhibitor response (log2 HSPA1A M/L vs H/L: w 3.23/0.00, X 0.00/3.54, Y −0.21/3.35), so the other channel holds a different, unnamed condition (the codes may stand for PRT062607 / AT13387 / STA-9090, but nothing says so).

**Sources exhausted:** PMC free full text (PMC5290984; no supplement in PMC, `pmc-prop-has-supplement no`), Europe PMC fullTextXML (500) and supplementaryFiles ("not open access"), PMC OA S3 (404), Unpaywall (no OA location), ashpublications.org data supplement (Cloudflare bot check, not bypassed), PRIDE protocols, MaxQuant.zip `summary.txt`/`parameters.txt` (experiment names only), raw headers (no sample descriptions beyond vial positions).

**Unblocked by:** the Blood data supplement (supplemental Materials and methods and supplemental Figure 1C) or an author statement giving the L/M/H condition for experiments DD, DGI_w, DGI_X, DGI_Y (and, for the annotated DGII rows, which of AT13387/STA-9090 each of DGII_1 and DGII_2 received).

**Related deposit:** PXD003492 (Corso et al., PNAS 2016; same lab, 398 RAW `DG75_BCRstim_GP_*`) shares no raw file with PXD004181 (0 name, 0 checksum overlap). Not a duplicate; not annotated here.

## PXD000958 — CELF1 silencing in oral squamous cell carcinoma cells (Palanisamy lab, MUSC; triple-SILAC Arg6/Lys4 + Arg10/Lys8, MaxQuant 1.4.1.2), whole dataset (30 RAW)

**Not annotated. The dataset is genuine triplex SILAC, but no accessible source names the three conditions, let alone which SILAC channel (light / Arg6;Lys4 medium / Arg10;Lys8 heavy) carries which. Campaign rules 6–7 therefore block every run.**

| | |
|---|---|
| Publication | PRIDE `references` is empty and Europe PMC finds no paper citing PXD000958. The matching study is House RP, Talwar S, Hazard ES, Hill EG, Palanisamy V. *Oncotarget* 2015;6(41):43620-34, "RNA-binding protein CELF1 promotes tumor growth and alters gene expression in oral squamous cell carcinoma", PMID 26498364, PMC4791255 (same lab, same submitter, near-identical title). Full text and all 8 supplements (s001.pdf, s002–s008.xlsx, PMC OA S3) were read: **they contain no SILAC, mass spectrometry or proteomics content at all** (only RNA-seq GSE57254, qRT-PCR, splicing, RNP-IP, xenografts). The lab's earlier paper (Talwar et al., *RNA Biol* 2013, PMC3594286) has no proteomics either. Searches for a separate proteomics paper or a dataset descriptor (`CELF1 AND SILAC`, `CUGBP1 AND SILAC`, `"1322 proteins"`, author `Palanisamy V` AND proteomic/SILAC, `House RP` AND CELF1) found nothing. |
| Deposited | 30 Thermo `.raw` (Orbitrap Elite): `090613_Visu_Set_1-{1..10}` (Set_1-8 as `090613_Visu_Set_1-8_130910152909.raw`), `091913_Visu_Set2_{1..10}`, `091913_Visu_Set3_{1..10}` = 3 biological replicates × 10 gel-band fractions; `MaxQuantOutput.zip` (summary.txt, peptides.txt, evidence.txt, allPeptides.txt, proteinGroups.xml [actually a tab-separated proteinGroups table], tables.pdf). No experimental-design file. FTP root `pride/data/archive/2022/02/PXD000958/`. |
| SILAC verified (rule 14) | summary.txt: all 30 raws `Multiplicity 3`, `Labels1 Arg6;Lys4`, `Labels2 Arg10;Lys8`, enzyme Trypsin/P, variable Oxidation (M), no multi modifications; experiments `SILAC1`, `SILAC2`, `SILAC3`. |

Why blocked:
- **No condition names and no channel map anywhere.** PRIDE sample protocol: "Cells labeld with Light, medium, and Heavy Lys/ARg isotopes were lysed and combined 1:1:1. Three biological replicates were processed." The title says "Silencing ... CELF1", which implies a CELF1-knockdown arm, but a triplex needs three conditions and the third (e.g. control siRNA vs mock vs another time point) is never stated. The cell line is not stated in the deposit either (the related paper uses UMSCC-74B for siRNA work, but also UMSCC-11B and SCC-15).
- **Raw headers** (byte-range reads of `090613_Visu_Set_1-1.raw` and `091913_Visu_Set2_5.raw`) give only the file path, the method `120mingrad_FT_onlyCID_TOP20.meth` and instrument `Orbitrap Elite ETD`; Sample name / Comment fields are empty.
- **The data does not settle it.** CELF1 (UniProt Q92879) is not identified in proteinGroups or peptides, so the knockdown channel cannot even be cross-checked. ELAVL1/HuR is strongly lower in heavy (H/L normalized 0.06–0.14 across SILAC1–3). Heavy is globally ~3–6-fold below light in all three experiments even after MaxQuant normalization (median log2 H/L normalized −1.58, −2.64, −1.67; `scratchpad/b11-PXD000958/ratio_medians.txt`), which is inconsistent with a 1:1:1 mix of whole proteomes and suggests the deposited table is a filtered subset or the mixing/labeling was unequal. Rule 6 forbids a data-only map in any case.

**Unblocked by:** an author statement (or a proteomics paper/thesis) naming the three conditions, their SILAC labels, and the cell line. With it the SDRF would be 30 runs × 3 channels = 90 rows; human + cell-lines (+ oncology-metadata if wanted); fractions 1–10 per Set; characteristics[biological replicate] 1–3 = Set1/Set2/Set3 within each condition; MaxQuant 1.4.1.2 search (Trypsin/P rule, Carbamidomethyl C fixed per PRIDE protocol, Oxidation M variable, Arg6/Lys4/Arg10/Lys8 labels; Human IPI v3.72).


---

## PXD008100 — LAD1 / EGF phosphoproteome in MCF10A (Roth et al., Sci Signal 2018; triple-SILAC control / serum / EGF time course), whole dataset (103 RAW)

**Not annotated. The dataset is genuine triplex SILAC, but no accessible source says which SILAC channel (light / Arg6-Lys6 medium / Arg10-Lys8 heavy) carries control, serum or EGF. Campaign rules 6–7 therefore block every run.**

| | |
|---|---|
| Publication | Roth L *et al.*, *Sci Signal* 2018 11(515):eaan0949, doi:10.1126/scisignal.aan0949, PMID:29382783. **Closed access**: no PMCID (`inEPMC=N`); Unpaywall `closed`; Semantic Scholar `openAccessPdf` CLOSED; science.org article and supplement HTTP 403 (not bypassed); no preprint or data descriptor found in Europe PMC. Only the abstract was read. |
| Deposited | 103 `.RAW` (LTQ Orbitrap XL per raw headers; PRIDE says "LTQ Orbitrap") + `Yarden_txt.zip` (MaxQuant 1.2.0.18 txt). FTP root `pride/data/archive/2019/11/PXD008100/`. No experimental-design file deposited (parameters.txt references one). |
| SILAC verified (rule 14) | `summary.txt`: Multiplicity 3, Labels1 `Arg6;Lys6`, Labels2 `Arg10;Lys8`, all 102 searched raws. |
| MaxQuant experiments (evidence.txt) | 5 min Seq27454–71 (18); 10 min Seq28886–99 (14); 20min Seq26792–805 (14, deposited with `_B` suffix); 40 min Seq27531–48 (18); 60 min Seq28238–49,28252,28253 (14) + `Seq28635_SCX_*` salt steps (10); 120 min Seq28097–108,28111,28112 (14). `Seq28635_SCX_load_E2O2.RAW` was not searched (would be an excluded run). |

Why blocked:
- **No explicit channel map.** PRIDE sample protocol: "Cells from control, serum or EGF treatments from the same time point were mixed to a single sample" — conditions named, labels not. MaxQuant output names only L/M/H; raw headers carry no sample description.
- **The data does not settle it.** EGFR T693 and SHC1 Y428 are highest in H, higher in M than L at all time points, suggesting L = control, H = EGF; but serum also activates these pathways (MAPK1 Y187 at 5 min M/L > H/L). Rule 6 forbids a data-only map.
- **Second open point:** the 60-min experiment pools two separately run mixtures (Seq282xx and Seq28635 SCX series); replicate vs re-fractionation is undocumented.

**Unblocked by:** the paper's Methods/Fig. 1/supplement (Science Signaling, subscription) or an author statement giving the control/serum/EGF labels and the relation of the two 60-min mixtures; cross-check against the EGFR/SHC1 ratios (`scratchpad/b11-PXD008100/orientation.txt`). Planned SDRF: 102 runs × 3 channels = 306 rows; human + cell-lines (MCF 10A, CVCL_0598); factors treatment (`untreated` / serum / EGF) and time; Carbamidomethyl fixed, Oxidation / Acetyl (Protein N-term) / Phospho variable, ITMS 0.5 Da.


---

## PXD006395 — Selective insulin resistance in HepG2 cells due to palmitate lipotoxicity (Li, Lai et al., Mol Cell Proteomics 2018; SILAC Arg10/Lys8 phosphoproteome + proteome), whole dataset (65 RAW)

**Not annotated. The dataset is genuine duplex SILAC, but no accessible source says which SILAC channel (light / Arg10;Lys8 heavy) carries which condition in any of the three MaxQuant searches, nor what the run codes (A–H × 1–3, 1_1–3_3) mean. Campaign rules 6–7 therefore block every run.**

| | |
|---|---|
| Publication | Li Z, Lai ZW, Christiano R, Gazos-Lopes F, Walther TC, Farese RV. *Mol Cell Proteomics* 2018;17(5):836-849, doi:10.1074/mcp.RA117.000560, PMID 29414761, PMC5930403. CC-BY hybrid, but **not reachable here**: not in the Europe PMC OA subset (`fullTextXML` HTTP 500, `supplementaryFiles` "not open access"), no PMC OA S3 copy (`PMC5930403.1-3` 404), NCBI efetch returns front matter + abstract only, Unpaywall's PDF (europepmc `?pdf=render`) and mcponline.org return Cloudflare 403, pmc.ncbi.nlm.nih.gov returns a reCAPTCHA page, ScienceDirect 403 — none bypassed. No Data-in-Brief / descriptor or preprint found (Europe PMC search for PXD006395 and title/author). Only the abstract and the PRIDE protocols were read. |
| Deposited | 65 Thermo `.raw` (Q Exactive HF per raw headers; PRIDE says Q Exactive) + 3 MaxQuant 1.5.2.8 zips (`Insulin_20min_Phospho.zip` 35 raws, `Pamitate_20min_Phospho.zip` 21 raws, `Insulin_20min_Proteome.zip` 9 raws; each re-contains its raws, mqpar.xml and combined/txt). FTP root `pride/data/archive/2018/02/PXD006395/`. No experimental-design file; mqpar `fractions` all 32767 (no fractions). |
| SILAC verified (rule 14) | summary.txt of all three searches: Multiplicity 2, Labels0 empty, Labels1 `Arg10;Lys8`; Trypsin/P; fixed Carbamidomethyl (C); variable Acetyl (Protein N-term), Oxidation (M) (+ Phospho (STY) in both phospho searches); no multi modifications; main search 4.5 ppm, first search 20 ppm, FTMS MS/MS 20 ppm. |
| MaxQuant experiments | Insulin phospho: 24 experiments A1–H3 (A1–D3 each with a re-injection `_<timestamp>` raw; anomaly: raw `…_D2` is assigned to experiment D1 and raw `…_D3` to D2, so experiment D1 has 2 raws, D3 has 1). Palmitate phospho: 18 experiments A1–F3 (A2, A3 have 2 raws; spelling `phospohoproteome` for the *1 runs). Proteome: 9 experiments 1A–3C (raws `proteome_<n>_<m>`). |

Why blocked:
- **No explicit channel map.** PRIDE sample protocol: "HepG2 cells were SILAC … labeled … Palmitate treated or untreated cells were stimulated with vehicle … or 100 nM insulin for 20 min"; "equal mixing of proteins at 1:1 ratio (light:heavy labels)". Four conditions are named for a duplex design, and no label is assigned to any of them. Raw headers (byte-range reads of one raw per search) carry only the path and method `2014_08_14_265min.meth`; MaxQuant names only L/H.
- **Run codes undocumented.** A–H (8 letters) might be the eight sequential TiO2 enrichment rounds the protocol mentions and 1–3 biological replicates (site counts fall from ~9–11k in A–C to ~3k in H), but palmitate has only A–F, and the proteome's `<n>_<m>` could be replicate × technical replicate or something else. Nothing states it.
- **The data suggest but do not settle it** (`scratchpad/b11-PXD006395/orientation.txt`, script `scripts/orient.py`): in the Insulin phospho search, canonical insulin sites are higher in H in all 24 experiments (log2 H/L AKT1S1 T246 +1.2…+1.8, GSK3B S9 +0.9…+1.7, TSC2 T1462 +1.0…+1.9, FOXO3 S253 +1.6…+2.3), i.e. heavy ≈ insulin, light ≈ vehicle. In the Palmitate phospho search the same sites are mildly lower in H (AKT1S1 T246 −0.2…−0.4, GSK3B S9 −0.3…−0.7, MAPK1 Y187 −0.7…−1.2), consistent with heavy = palmitate + insulin vs light = untreated + insulin, but whether both channels were insulin-stimulated is not stated. The proteome search shows near-zero ratios (PLIN2, SCD, LDLR |log2| ≤ 0.3), so its contrast cannot be identified from data at all. Rule 6 forbids a data-only map.
- Not a duplicate: absent from `annotations/` and `sdrf-annotated-datasets/datasets/`; Europe PMC links only this paper.

**Unblocked by:** the paper's Experimental Procedures / Fig. 1 / supplementary tables (MCP, CC-BY; fetchable by a human from mcponline.org or PMC) or an author statement giving, per search, the light/heavy conditions (vehicle vs insulin; untreated vs palmitate, with/without insulin) and the meaning of A–H, 1–3 and `<n>_<m>`; then cross-check against `orientation.txt`. Planned SDRF: 65 runs × 2 channels = 130 rows; templates ms-proteomics v1.2.0 + human + cell-lines (Hep-G2, CVCL_0027, male 15Y, hepatoblastoma per Cellosaurus); factors treatment (insulin / palmitate, `untreated` controls) ; modification parameters per search (Phospho only for the two phospho searches); Arg10 UNIMOD:267, Lys8 UNIMOD:259 `MT=Variable`; cleavage agents Lys-C + trypsin for the phospho arms (GdmCl/LysC-then-trypsin protocol) and trypsin for the proteome arm (PRIDE proteome protocol); DDA top-10, Easy-nLC 1000.

---

## PXD009009 — Hypoxia-regulated genes in HCT116 colon cancer cells (Chen et al., J Proteomics 2018; duplex SILAC Lys6/Arg6 proteome + dimethyl secretome), whole SILAC arm (132 RAW) blocked; 44 dimethyl secretome RAW excluded (out of scope)

**Not annotated. The proteome arm is genuine duplex SILAC, but no accessible source says whether the hypoxic or the normoxic cells carried the heavy label in either mixture (Exp1, Exp2). Campaign rules 6–7 therefore block every SILAC run.**

| | |
|---|---|
| Publication | Chen JT, Liu CC, Yu JS, Li HH, Lai MC. *J Proteomics* 2018, doi:10.1016/j.jprot.2018.02.031, PMID 29524648. **Closed access**: no PMCID; Unpaywall `closed`; ScienceDirect not fetched (subscription/bot check, not bypassed). Only the abstract was read. Europe PMC found no Data in Brief or dataset descriptor. The same-lab papers PMC4831676 and PMC6444133 (read in full) and the FEBS J 2025 follow-up (abstract, PMID 39710969) do not give the labels. |
| Deposited | 180 files: `20150318-Exp1-SILAC-33ug-s1..s66.raw` (66) and `20150418-Exp2-SILAC-33ug-s1..s66.raw` (66), which are 2 SILAC mixtures × 66 online-SCX fractions on an Orbitrap Elite (raw header); `20151211-hypoxia-12_5ug-s01..s22.RAW` and `20151214-hypoxia-12_5ug-s01..s22.RAW` (44, secretome, LTQ Orbitrap); 4 PD 1.4 `.msf`. FTP root `pride/data/archive/2018/03/PXD009009/`. |
| SILAC verified (rule 14) | Exp1/Exp2 msf `ProcessingNodeParameters` (read as SQLite over HTTP range): quantification method "SILAC 2plex (Arg6, Lys6)", channels `Light` / `Heavy` (Label:13C(6) on K and R, UNIMOD:188). Mascot: variable Acetyl (Protein N-term), Gln->pyro-Glu, Oxidation (M), Label:13C(6) (K), Label:13C(6) (R); fixed Carbamidomethyl (C); 10 ppm / 0.6 Da; Trypsin, 2 missed cleavages. |

Why blocked:
- **No explicit channel map.** PRIDE sample protocol: media "re-supplemented with either normal ... [12C6]lysine/[12C6]arginine or ... [13C6]lysine/[13C6]arginine", without saying which condition got which. The PD channel names are only Light and Heavy, and `WorkflowInfo` and the raw headers carry no sample description.
- **The data hints at a label swap, but rule 6 forbids a data-only map.** In a sample of high-confidence PSMs (median log2 H/L), PGK1 is +0.68 in Exp1 and −1.23 in Exp2; P4HA1 is +1.80 in Exp1; ERO1A is +0.95 in Exp1 and −1.60 in Exp2. The housekeeping proteins ACTB and HSPA8 are about 0 in both (`scratchpad/b11-PXD009009/orientation.txt`). This suggests hypoxia = heavy in Exp1 and hypoxia = light in Exp2.

Excluded runs (out of scope, not SILAC): the 44 secretome RAWs `20151211-hypoxia-12_5ug-s01..s22.RAW` and `20151214-hypoxia-12_5ug-s01..s22.RAW`, with `20151211-hypoxia-12.5ug_Hypoxia_L.msf` and `20151214-hypoxia-12.5ug_Hypoxia_heavy.msf`. They are reductive-dimethyl labelled (PD "Dimethylation 2plex (C2H4, 13C2D4)"). The msf names state the hypoxic sample's dimethyl label for each mixture, which a non-SILAC pass could use.

**Unblocked by:** the paper's Methods, Fig. 1 or supplement (J Proteomics, subscription), or an author statement giving the SILAC label of the hypoxic and normoxic cells in Exp1 and Exp2. The map should then be cross-checked against the PGK1/P4HA1/ERO1A ratios. Planned SDRF: 264 rows (132 runs × 2 channels); human + cell-lines; HCT 116 (CVCL_0291); factor value[treatment] hypoxia vs normoxia control; biological replicate 1–2 per condition; fraction identifier 1–66.

---

## PXD036363 — Targeting N-linked glycosylation in DLBCL (Scheich et al., Cancer Discov 2023; triple-SILAC BioID2 / SPPLAT / pY + TMTpro glyco/proteome, TMD8 and HBL-1), TMT runs excluded (excluded runs, not a blocker)

**Annotated: `annotations/PXD036363.sdrf.tsv`, 142 SILAC raws × 3 channels = 426 rows.** The channel map is explicit in the deposited `File_assignment.txt` and agrees with the deposited ratios (bait enrichment vs EV/isotype; BTK Y223 down only in the acalabrutinib channel, SYK/LYN/CD79B pY down only in the NGI-1 channel).

Excluded runs:
- **Out of scope (TMT, not SILAC), 74 RAW:** `YLJI_101220_141220_Sebas_Sch_TMTpro_MS3_glyco_R1..R4_frac1..8.raw` (32) and `YLJI_101220_211220_Sebas_Sch_TMTpro_MS3_proteome_R1..R3_frac1..14.raw` (42), TMTpro 16-plex SPS-MS3 on Orbitrap Fusion Lumos, searched with pGlyco/GlycoBinder (`pGlyco_output.zip`) and `MaxQuant_proteome.zip`. Their 16-channel map (HBL1/TMD8/OCI-Ly10/RIVA/OCI-Ly8 DMSO vs NGI-1; HBL1/TMD8 Ctrl KO vs STT3A/B DKO) is in `File_assignment.txt`, so a TMT pass can annotate them.

Note (not excluded): 3 SILAC raws of experiment 505 were never searched: `TO_S_Scheich_180221_220321_HFFR_505_WDH_L5_21.raw`, `_L5_22.raw` and `_L5_23.raw`. They are absent from `MaxQuant_505.zip` summary.txt, which used the undeposited `…110321…_L5_6_WDH` and `…100321…_L5_22/23`. After review round 1 they were added (rows 418–426) with tolerances and search-only modifications `not applicable`. L5_21 (220321) is technical replicate 2 of slice 21; it was injected from the same vial as the searched 190321 file.

**Unblocked by:** nothing needed for the SILAC SDRF. The TMT arm belongs to a TMT annotation pass.

---

## PXD034333 — Englerin A phosphosignaling in A498 renal cancer cells (Neo et al., J Proteome Res 2022; duplex SILAC Arg10/Lys8 proteome + Fe-IMAC phosphoproteome, label swap Fwd/Rev), whole dataset (52 RAW)

**Not annotated. The dataset is genuine duplex SILAC, but no accessible source says which SILAC label the Englerin A-treated cells carried in the "Fwd" mixture and which in the "Rev" mixture. Campaign rules 6–7 therefore block every run.**

| | |
|---|---|
| Publication | Neo SP, Alli-Shaik A, Wee S, Lim Z, Gunaratne J. *J Proteome Res* 2022;21(8):1948-1960, doi:10.1021/acs.jproteome.2c00248, PMID 35838755. **Closed access**: no PMCID (NCBI elink gives only citing PMC records), Unpaywall `closed`, Europe PMC has no supplementary files (404). pubs.acs.org returned 403 (bot check, not bypassed). Only the abstract was read. Europe PMC finds no Data in Brief or dataset descriptor, and no preprint shows up in Crossref. A PRIDE keyword search ("Englerin", "A498 SILAC") returns only PXD034333, so there is no re-deposit. |
| Deposited | 52 RAW + 2 MaxQuant zips, FTP `pride/data/archive/2022/07/PXD034333/`. Proteome (MaxQuant 1.5.0.30, `Proteome_search_MS_Data.zip`): `A_140922_*_IS168_Fwd_IEF1..24*.RAW` (experiment `Fwd`, 24 IEF fractions) and `A_140919_*_IS168_R1..R24*.RAW` (experiment `Rev`, 24 IEF fractions). Phosphoproteome (MaxQuant 1.3.0.5, `Phospho_search_MS_Data.zip`): `QE_141013_06_IS170_A498_PHOSPHO_FWD1.raw`, `QE_141014_01_IS170_A498_PHOSPHO_FWD1.raw` (experiment FWD, duplicate injections) and `QE_141014_12_IS170_A498_PHOSPHO_REV1.raw`, `QE_141018_01_IS170_A498_PHOSPHO_REV1.raw` (experiment REV, duplicate injections). Q Exactive. |
| SILAC verified (rule 14) | Both summary.txt files: Multiplicity 2, Labels0 empty, Labels1 `Arg10;Lys8`. Search: fixed Carbamidomethyl (C); variable Oxidation (M), Acetyl (Protein N-term), plus Phospho (STY) in the phospho search; Trypsin/P, 2 missed cleavages; MS/MS 20 ppm. Digestion was Lys-C followed by trypsin (PRIDE protocol). |

Why blocked:
- **No explicit channel map.** The PRIDE sample protocol says only "mixing equal amount of identically concentrated 'light' and 'heavy' SILAC labeled A498 lysates, with and without 24 hour treatment of 100nM Englerin A". It does not say which label was treated in either mixture. The MaxQuant experiment names are only Fwd/FWD and Rev/REV, and the ratio columns are only H/L.
- **The data suggests heavy = EA in Fwd and light = EA in Rev, but that is a data-only inference from the abstract's direction ("Hsp27 hyperphosphorylated upon EA"), which rule 6 does not accept.** `Phospho (STY)Sites.txt` gives these Ratio H/L normalized values for HSPB1 (FWD / REV): S15 8.86 / 0.098, S65 9.10 / 0.066, S82 3.33 / 0.386, S50 2.76 / 0.128. At protein level (proteome `proteinGroups.txt`) HSPB1 is 0.94 / 1.05 and GAPDH is 1.00 / 0.97 (`scratchpad/b12-PXD034333/orientation.txt`).

**Unblocked by:** the paper's Methods, figure legend or Supporting Information (ACS, subscription), or an author statement that gives the SILAC label of EA-treated and untreated A498 cells in the Fwd and Rev mixtures. The map should then be cross-checked against the HSPB1 site ratios above. Planned SDRF: 104 rows (52 runs × 2 channels). Templates: human + cell-lines. Cell line A-498 (CVCL_1056; check that the Cellosaurus name does not collide with another entry). factor value[treatment] = Englerin A 100 nM 24 h vs `untreated`. Biological replicate 1–2 per condition (Fwd and Rev mixtures, assuming independent cultures). Proteome fractions 1–24 per mixture; phospho technical replicate 1–2. Two `comment[cleavage agent details]` (Lys-C, Trypsin). Two search builds, MaxQuant 1.5.0.30 proteome and 1.3.0.5 phospho with Phospho (STY), with identical headers.

---

## PXD072695 — Leishmania exosomal tRF mimics in THP-1 macrophages (Brar et al., PLoS One 2026; 3-plex SILAC MaxQuant search, Ld-tRF-Asp / Ld-tRF-Leu), SILAC light channel of all 9 runs (partial block)

**Annotated: `annotations/PXD072695.sdrf.tsv`, 9 runs × 2 documented channels = 18 rows (medium = scrambled-oligo control, heavy = Ld-tRF mimic). Blocked: the SILAC light channel of every run. No source says what the light sample is.**

| | |
|---|---|
| Publication | Brar HK et al., *PLoS One* 2026;21(8):e0356144, doi:10.1371/journal.pone.0356144, PMID 42616765. The full text was read from the PLOS JATS XML, along with S1 Table (xlsx) and the S1 Fig legend. Europe PMC returned 503. |
| Deposited | 9 Bruker impact II `.d.1.dar` files plus `Devki_human_Sept12_16txt.zip` (MaxQuant 1.5.3.30 parameters/summary/proteinGroups), `MaxQuant_1.5.3.30.rar` and `HUMAN.fasta` |
| Blocked channel | SILAC light (Lys0/Arg0) in `Devki_THP1silac3plex_1Asp_B11_01_6100`, `_2Asp_B12_01_6101`, `_3Asp_C1_01_6102`, `_1Leu_B8_01_6095`, `_1Leu-redo_C2_01_6104`, `_2Leu_B9_01_6096`, `_2Leu-redo_C3_01_6105`, `_3Leu_B10_01_6097` and `_3Leu-redo_C4_01_6106` (`.d.1.dar`) |
| SDRF would need | 9 more rows (one light row per run), each with a sample identity |

Why blocked:
- summary.txt has Multiplicity 3: Labels0 is light, Labels1 is Arg6;Lys4 and Labels2 is Arg10;Lys8. The light channel carries real signal. Summed protein-group intensity per experiment is L 2.6–4.4e9, M 1.6–2.5e9 and H 1.5–2.6e9. The M/L ratio profiles correlate across all six experiments (r = 0.28–0.57), so the light lysate is a systematically different sample, not empty.
- The paper describes only two populations. S1 Fig says "cultured in medium and heavy SILAC media". The Fig 1 legend says "Mass spectrometry was performed on a mixture of two lysates". The Methods say only "each of 3-plex SILAC labelled set ... were pooled". S1 Table holds only H/M ratios. The PRIDE protocol adds nothing. No Data in Brief or other descriptor was found.

**Unblocked by:** an author statement of what the light-labelled sample in each 3-plex mixture was (for example untransfected or mock-transfected dTHP-1), with its culture/replicate relation to the M/H cultures. Once that is known, add one light row per run to the existing tables (`scratchpad/b12-PXD072695/scripts/make_tables.py`, where the light rows are currently empty source names) and rebuild.

---

## PXD029527 — Dynamic rRNA ribomethylome / FBL and SNORD127 nascent proteomics in Kasumi-1 (Zhou et al., Cancer Discov 2023; pAHA + pulsed SILAC, intermediate Lys4/Arg6 vs heavy Lys8/Arg10), SNORD127 arm (32 RAW) still blocked; FBL arm annotated under owner decision (partial block)

**Annotated: the FBL-knockdown arm, in `annotations/PXD029527.sdrf.tsv` (18 Q Exactive HF RAW × 2 channels = 36 rows), under a campaign-owner decision of 2026-11-10 that applies to this dataset only.** No written source names the labels. The channel map comes from the knock-down target's own deposited ratios. FBL H/M normalized is 9.25 in rep1, so heavy = shCtrl; it is 0.15 in rep2, so heavy = shFBL. The Supplementary Table S4 top hits agree (LGR4, MNDA, CTSG), and log2 H/M of rep1 vs rep2 gives r = −0.72. The two `Feng_int_rep{1,2}_10p` injections are encoded as technical replicate 2 of mixtures 1 and 2; their label pattern matches the parent mixture. `shFBL_int_rep2_fr1/fr2` were acquired as `Feng_int_rep1_fr1/fr2`, but their label pattern is that of rep2, so the deposited names are kept.

| | |
|---|---|
| Publication | Zhou F et al. *Cancer Discov* 2023;13(2):332-347, doi:10.1158/2159-8290.CD-22-0210, PMID 36259929, PMC9900322 (OA). The full text, Supplementary Figures S1–S9 and Tables S1–S4 were read from PMC OA S3. Europe PMC returned 503 throughout. |
| Excluded runs | `20181218_QE1_DF_shFBL_int_rep2_fr1_10p.raw` (1 MB stub, acquired as `..._Feng_int_rep1_fr1_10p.raw`). It is absent from `msmss_shFBL_0712019.txt` and so was never searched. |
| Blocked (whole runs) | The 32 Orbitrap Fusion RAW `20190301_FS1_DF_snoRNA_{1..4}_{1..8}.raw` (search output `proteinGroups.txt`, `msms.txt`; experiments SNOR5D127_KO_C1_rep1/rep2, SNOR5D127_KO_C34_rep1/rep2). |
| SILAC verified (rule 14) | proteinGroups has Intensity and Ratio columns for L, M and H (multiplicity 3). msms mass deltas give M = Lys4/Arg6 and H = Lys8/Arg10. |
| Light channel | Not empty: about 10% of PSMs per raw, and Intensity L sums to 3.8e12 (rep1) and 4.1e12 (rep2). In pAHA-pSILAC this is unpulsed, pre-existing protein from **both** pooled cultures. It cannot be assigned to one sample, so no SILAC light rows are encoded. |

Why the SNORD127 arm stays blocked:
- **No explicit channel map.** The PRIDE protocol and the paper say only that a label swap was made between replicates. Fig. 4F gives only SNORD127+/− vs +/+. The +/+ control clone(s) are not named.
- **The raw-to-experiment map is undocumented.** No source says which of `snoRNA_1..4` is C1_rep1, C1_rep2, C34_rep1 or C34_rep2. msms.txt has no experiment column, and no summary.txt was deposited.
- **The data do not settle it.** Ratio correlations between the four experiments are −0.17…+0.17, so there is no swap pattern. SLC38A10 (the paper's top repressed protein) has H/M 0.47 / 1.66 / 0.88 / 1.08.

**Unblocked by:** an author statement, or a summary.txt plus a label statement, that gives the intermediate and heavy condition of each SNORD127 experiment (+/+ vs +/− clone C1/C34) and the raw-file → experiment mapping. The planned SDRF for that arm is 32 RAW × 2 channels on the Orbitrap Fusion (ion-trap MS2), built separately with headers identical to the FBL file.

## PXD026925 — LCK inhibitor NTRC 0652-0 in cholangiocarcinoma (Conboy et al., J Hepatol 2023; triple-SILAC HuCCT-1 + TMTpro PDX), TMT arm excluded (excluded runs, not a blocker)

The SILAC arm (24 `HuCCT1_Global_FN01..FN24_PepMap_50cm_050620.raw` + `HuCCT1_pY_PepMap_50cm_042820.raw`; light = control, medium = NTRC 0652-0, heavy = sgLCK, from the paper's Methods) is annotated in `PXD026925.sdrf.tsv`.

**Excluded runs (out of scope for the SILAC campaign, not missing evidence):** 25 TMTpro (12-channel) PDX283 tumour runs, searched in `PDX_Global_txt.zip` / `PDX_pTyr_txt.zip` (human + mouse FASTA; 3 vehicle + 3 NTRC mice per PRIDE protocol): `CCAPDX_FGFR_TMT12_Total_FN01.raw` … `CCAPDX_FGFR_TMT12_Total_FN24.raw` (24 fractions) and `CCAPDX_FGFR_pTyr.raw`. TMT channel map not looked up (would be needed for a separate `PXD026925-tmt.sdrf.tsv`; the paper's Supplemental table 4 was behind a PMC bot check).

## PXD012954 — LSD1 scaffolding role / LSD1 interactome in NB4 APL cells (Ravasio et al., Sci Adv 2020; SILAC Arg10/Lys8 anti-LSD1 co-IP, basal + MC_2580 arms, + label-free histone PTMs), label-free histone runs excluded (excluded runs, not a blocker)

**Annotated:** all 83 SILAC raws (basal interactome Rep1-3 IPs and inputs, MC_2580 interactome forward/reverse IPs and inputs) in `annotations/PXD012954.sdrf.tsv`; channel maps from the paper Methods and checked against deposited H/L ratios.

**Excluded runs (out of scope for the SILAC campaign, not missing evidence):** 27 label-free histone-PTM runs (Pro-PIC derivatisation, ArgC search; MaxQuant `txt_HistonesPTM_DDP38003.zip` / `txt_HistonesPTM_WT_KO.zip`, summary Multiplicity 1, no labels): 38003_1_IIIreplica_histones_LN.raw, 38003_1_IIreplica_histones_LN.raw, 38003_1_Ireplica_histones_LN.raw, 38003_2_IIIreplica_histones_LN.raw, 38003_2_IIreplica_histones_LN.raw, 38003_2_Ireplica_histones_LN.raw, 38003_3_IIIreplica_histones_LN.raw, 38003_3_IIreplica_histones_LN.raw, 38003_3_Ireplica_histones_LN.raw, DMSO1_Ireplica_histones_LN.raw, DMSO_1_IIIreplica_histones_LN.raw, DMSO_1_IIreplica_histones_LN.raw, DMSO_2_IIIreplica_histones_LN.raw, DMSO_2_IIreplica_histones_LN.raw, DMSO_2_Ireplica_histones_LN.raw, DMSO_3_IIIreplica_histones_LN.raw, DMSO_3_IIreplica_histones_LN.raw, DMSO_3_Ireplica_histones_LN.raw, KO1_IIIreplica_LNRR.raw, KO1_IIreplica_LNRR.raw, KO1_Ireplica_LNRR.raw, KO2_IIIreplica_LNRR.raw, KO2_IIreplica_LNRR.raw, KO2_Ireplica_LNRR.raw, WT_IIIreplica_LNRR.raw, WT_IIreplica_LNRR.raw, WT_Ireplica_LNRR.raw. They would go in a separate label-free SDRF (batch rule 12). Note for whoever annotates them: PRIDE says KO1 'was also not cited in the publication'; `DMSO1_Ireplica_histones_LN.raw` and `DMSO_1_*` naming differ.

## PXD050961 — SPIED-DIA phosphoproteomics, MEK inhibition in CRC cell lines (van Bentum et al., Nat Commun 2025; SILAC HCT116 dilution + heavy synthetic phosphopeptide spike-in DIA; timsTOF Pro 2, Rev_Benchmark3 runs timsTOF HT), partial: DMSO arm and 20230605 runs of HCT116 individual-GF experiment blocked; library/DDA runs excluded

**Annotated:** `PXD050961-silac-dilution.sdrf.tsv` (Benchmark1, 33 runs: HCT116 heavy lysate diluted 1:1–1:2047 into light reference) and `PXD050961-spied.sdrf.tsv` (Benchmark2 9 DIA runs, cell-line panel GFmix 35 runs, HCT116 individual GFs MEKi arm 15 runs; heavy channel = JPT SpikeMix synthetic phosphopeptide reference) and `PXD050961-benchmark3.sdrf.tsv` (Rev_Benchmark3 targeted dilution series, 18 runs: HEK293 light row with characteristics[mass], separate E. coli 100 ng background light row per SAMPLE-GUIDELINES.adoc:424, JPT heavy spike 50 fmol; added in round 3, previously listed here as excluded; raw analysis.tdf of these runs records InstrumentName timsTOF HT, same serial as the timsTOF Pro 2 runs). Raw data are Bruker .d folders inside 9 RAW zip bundles, read by HTTP range.

**Blocked (channel/condition undocumented, rule 7):** `HCT116GFs_Rawfiles.zip` DMSO arm, 7 runs searched in HCT116GFs_outputDIANN_SPIED/LF: Popeye_20230704_MVB_HStd_SS1_DB1_A1_1_4167.d, DB1_F3_1_4169.d, DB2_G3_1_4182.d, DB3_H3_1_4198.d, DE1_D4_1_4172.d, DE2_E4_1_4190.d, DE3_F4_1_4203.d. Paper, Suppl. Fig. 15/16 and the authors' code (Zenodo 15045498) describe only the MEKi + BSA/EGF/FGF2/HGF/VEGF-C conditions; "D"=DMSO is supported by ERK2 pY187 light intensities (D* 1.2e3–7.6e3 vs M* <500) and B/E by the ligand initials, but no source states the condition. Unblocked by an author file→condition table.

**Also blocked (sample identity undocumented, rule 7; unsearched):** `HCT116GFs_Rawfiles.zip` 9 runs dated 20230605 — 6 MEKi-arm runs Popeye_20230605_MVB_HStd_SS1_MB1_D1_1_3908.d, MB2_E1_1_3919.d, ME1_B2_1_3913.d, MF1_E2_1_3914.d, MH1_C3_1_3917.d, MV1_H2_1_3915.d and 3 DMSO-arm runs DB1_A1_1_3907.d, DB2_B1_1_3918.d, DE1_G1_1_3909.d. Neither HCT116GFs DIA-NN log (SPIED, LF) lists them, and no source says whether they are earlier injections of the 20230704 samples or separate cultures; their analysis.tdf_bin (~0.5 GB vs ~2.5 GB for the 20230704 runs) suggests a different or aborted acquisition. Unblocked by an author statement linking them to samples (they would then be annotated with tolerances `not applicable`, as never searched).

**Excluded runs (out of SILAC scope or not encodable, not missing evidence):**
- `HpHLib_Rawfiles.zip` 50 .d (DDA-PASEF high-pH library fractions of light HCT116, MaxQuant label-free).
- `TargetLibBM2_Rawfiles.zip` 6, `Lib_Benchmark3_Rawfiles.zip` 6, `Lib_BioData_Rawfiles.zip` 3 (DDA-PASEF of the synthetic heavy peptide pool alone, library generation).
- `Benchmark2_Rawfiles.zip` 3 DDA runs Popeye_20240314_MVB_HStd_BM2_250ng_DDA_A4_1_5705/5706/5707.d (DDA benchmark, MaxQuant).

## PXD046502 — Palmitate / CD8+ T-cell histone PTMs (Tiberti et al., Sci Immunol 2026; histone super-SILAC, mouse), whole dataset (25 RAW)

**Blocker: no reachable source states what any deposited sample is.** The channel map itself is documented (PRIDE protocol: each sample's histones = light, "heavy-isotope labelled histones … used as an internal standard (super-SILAC mix)" = heavy; EpiProfile 2.0 `histone with SILAC` outputs give LightR/HeavyR per peptide, so multiplicity 2 is confirmed). What is missing is the identity and condition of the light (study) sample in every run: treatment, cell type vs. whole tissue, tissue of origin, time point and replicate structure are encoded only as file-name abbreviations, and the one deposited design file contradicts the deposited raw set. No SDRF was written.

Blocked runs (25 `.raw`, all in PRIDE files/all, every entry's `projectAccessions` = PXD046502):
- Q Exactive HF (raw header "Q Exactive HF - Orbitrap MS"): HF190619_RN_BSA18, HF190619_RN_BSA19, HF190619_RN_LINO18, HF190619_RN_LINO19 (searched in `19-06.zip`); HF200217_RN_TM_B1, HF200217_RN_TM_B2, HF200217_RN_TM_P1, HF200217_RN_TM_P2 (searched in `02-20.zip`)
- Q Exactive Plus (raw header "Q Exactive Plus - Orbitrap MS"; PRIDE `instruments` lists only Q Exactive HF): QEP250924_RN_spleen_6, _8, _9, _10; QEP260924_RN_PDAC_6, _8, _9, QEP260924_RN_PDAC10 (searched in `Manzo2.zip`, the last as `QEP260924_RN_pdc10`); QEP240804_RN_CD8_2, _6, _7, _8, _9, _10, _12, _13 (**no deposited EpiProfile output covers these 8 runs**)

Sources checked:

| source | result |
|---|---|
| PRIDE v3 project record | protocol prose only ("histone PTM levels in CTLs in response to PA treatment"); `references` empty; no per-sample condition |
| PRIDE files/all (29 files) | 25 RAW, 4 EpiProfile ZIPs, `Exp_des.txt` |
| `Exp_des.txt` | 2 unlabelled columns headed `Spleen` / `PDAC` plus an `early`/`late` column, 12 rows. It pairs spleen_6/8/9/10 with PDAC_1/3/4/5 and CD8_2…13 with QEP240701_RN_TM_PDAC_CD8_2…13. **None of the PDAC-column files has a deposited raw**; the deposited PDAC_6/8/9/10 are absent from it; the CD8_* runs sit under the `Spleen` header with no statement of what they are; `early`/`late` is not defined |
| EpiProfile ZIPs (central directories + `histone_ratios*.xls`, `histone_logs.txt`, read by HTTP range) | keyed by raw file name only. `Manzo.zip` holds 28 QEP240701_RN_TM_PDAC_CD4/CD8 runs, none deposited as raw; `Manzo2.zip` holds spleen_1–10 and PDAC_1–9/pdc10, of which only 8 are deposited |
| Raw file headers (first 1.5 MB, 5 files) | instrument model, method path, original file name only; no sample/comment field |
| Sci Immunol 2026 (doi:10.1126/sciimmunol.aeb1459, PMID:41894555) | not in PMC; Unpaywall closed |
| bioRxiv preprint 10.1101/2025.01.09.631811 (full text, JATS source.xml) | HTTP 429; Unpaywall closed; Europe PMC PPR965614 fullTextXML HTTP 500. bioRxiv API gives abstract only |
| Immunometabolism commentary PMC13390978 (OA) | narrative summary; no proteomics design, no sample key |
| PRIDE keyword search (title, "palmitate CD8", "Manzo histone") | no other/newer deposit |

**Deliberately not used** (campaign rules 6–8): reading `BSA`/`LINO`/`B`/`P` as BSA vehicle / linoleate / palmitate, `spleen`/`PDAC` as organism part or as CD8+ T cells sorted from those tissues, or `early`/`late` as a tumour stage or time point. All are plausible readings of abbreviations and none is stated anywhere reachable.

**Unblocked by:** the paper's Methods/figure legends for the histone MS experiments (Sci Immunol 2026 or the bioRxiv preprint), or a corrected sample sheet from the submitters (T. Manzo / R. Noberini / T. Bonaldi), giving for each deposited raw the sample type (sorted CD8+ T cells vs. tissue), treatment (BSA / PA / linoleate, dose, duration), tissue of origin, the meaning of `early`/`late`, and the mouse/culture replicate identity; and the EpiProfile output for the QEP240804_RN_CD8_* runs (or a statement that they were not analysed). Technical values are settled in `annotations/PXD046502.report.md`.

## PXD060444 — Ipomoeassin F time course / dose response in MDA-MB-231 (Sicairos et al., ACS Omega 2025; triplex SILAC Arg0Lys0/Arg6Lys4/Arg10Lys8, 4 mixtures × 12 SDS-PAGE slices), whole dataset (48 .raw)

**Blocker: which 12 raw files belong to which SILAC mixture is undocumented.** The channel map within each mixture is explicit: the Table S1/S2 headers, e.g. `Ratio M/L normalized 0-4-8h (4h/0h)`, give light = 0 h / 0 nM control, medium = lower time or dose, heavy = higher. File names separate time course (`Du_012318_T01..T24`) from dose (`Du_121917_D01..D12`, `Du_012318_D13..D24`). No source assigns T01–T12 vs T13–T24 to `0-4-8 h` vs `0-12-16 h`, or D01–D12 vs D13–D24 to `0-3-6 nM` vs `0-18-54 nM`, and none gives the gel-slice order.

Sources checked:
- PRIDE record and files: only two proteinGroups files; no summary, mqpar or experimentalDesign.
- Paper (PMC12409539) and SI PDF/xlsx.
- Raw headers of all 48 files: D01–D12 were originally `Du_121917_SILAC_01..12`; vials are consecutive; there is no sample-name field.
- Europe PMC.
- bioRxiv preprint 10.1101/2024.07.28.605505: JATS returned HTTP 429 and Europe PMC fullText returned 500; neither was bypassed.

An MS1 SILAC-ratio cross-check of D06/D18/T06/T18 against the per-experiment ratios was inconclusive: D06 and T06 weakly favour the first-listed mixtures, and D18 and T18 are contradictory. Details are in `annotations/PXD060444.report.md`.

Blocked runs: Du_121917_D01–D12, Du_012318_D13–D24, Du_012318_T01–T24 (.raw). No runs are excluded as out of scope.

**Unblocked by:** the MaxQuant summary.txt / experimentalDesignTemplate / mqpar.xml, or a raw-file → experiment (+ slice) table from the submitter (Y. Du), or the preprint Methods/SI if they list it. A ready generator with the provisional map is at `/tmp/claude-0/-home-user/a98b4c07-45f2-5d08-aa74-0c95b1e5e538/scratchpad/b12-PXD060444/scripts/make_tables.py`.

---

## PXD033337 — KDM5B-NTT overexpression, histone PTMs in MCF7 / MDA-MB-231 (Di Nisio et al., Cancer Gene Ther 2023; histone super-SILAC spike-in, Arg10), whole dataset (36 RAW)

**Blocker: the sample identity of every run is undocumented.** The channel map is documented: the light channel is the study sample and the heavy channel is the super-SILAC histone internal standard (PRIDE protocol; Suppl. Methods: "light (sample) and heavy (internal standard)"; MaxQuant `summary.txt` has Multiplicity 2 and Labels1 `Arg10`). What is missing is the cell line, condition (NT = not transfected, E = empty vector, NTT = KDM5B-NTT overexpression) and replicate (R#1–R#6) of the light sample in each run. The design is 2 cell lines × 3 conditions × 6 biological replicates = 36, which matches the 36 deposited raws, but nothing maps a run to a cell, so no SDRF was written.

Blocked runs (36 `.raw`; PRIDE v3 files (pageSize=100) give 37 entries, all with `projectAccessions` = PXD033337; all 36 raws are in `txt.zip` summary.txt, each as its own MaxQuant experiment):
- QEP211220_RN_GR_Elena_1, _2, _3, _7, _8, _9, _13, _14, _15, _19, _20, _21, _25, _26, _27
- QEP220103_RN_GR_Elena_31, _32, _33
- QEP220209_RN_GR_ELENA_37, _38, _39, _43, _44, _45, _49, _50BIS, _51, _55, _56BIS, _57, _61, _62BIS, _63BIS, _67, _68, _69BIS

Sources checked:

| source | result |
|---|---|
| PRIDE v3 project + files | protocol describes the design (MDA-MB231, MCF7; NT/E/NTT; 6 biological replicates); no per-run key; no SDRF/design file deposited |
| `txt.zip` (central directory + parameters.txt, summary.txt, evidence.txt, read by HTTP range) | experiment names = raw file stems; no sample names; MaxQuant 1.5.2.8, ArgC, fixed PIC, variable Trimethyl (K)/Dimethyl (K)/Propionyl/Pmet, Arg10 |
| Raw headers (bytes 0–20000 of all 36; 0–1.5 MB of Elena_1) | instrument "Q Exactive Plus - Orbitrap MS", method `QEP_histone_PIC_8minB_gradient.meth`, file name, vial, sequence row number; the sample-ID field holds only the batch-constant `H8` (Dec 2021) / `H3` (Jan–Feb 2022); nothing per sample |
| Paper PMC10281864 (PMC OA text) + Suppl. Methods/Tables (MOESM1–3 docx) | Table S2 gives L/H ratios of H3K4un/me1/me2/me3 per cell line × condition × R#1–6, with no raw-file names |
| Europe PMC search "PXD033337" | only the article itself; no Data in Brief or other dataset descriptor |
| GEO GSE218819 | RNA-seq only |

**Deliberately not used:**
- **The run-number pattern.** The runs come in blocks of three (1–3, 7–9, …, 67–69). These could be read as NT/E/NTT triplets, but no source states this.
- **A data-driven cell-line split.** In `evidence.txt`, H3 3–8 (TKQTAR) light/heavy %RA ratios separate Elena_1–15 and 37–51 (MCF7-like: high me1, low me2) from 19–33 and 55–69 (MDA-MB-231-like), consistent with Table S2. The per-run values are too sparse and noisy (many NA) to match Table S2 columns to individual runs, so they could not assign condition or replicate.

Rule 7 forbids keeping rows with `not available` conditions.

**Unblocked by:** a run → (cell line, NT/E/NTT, replicate R#) table from the submitters (G. Robusti / R. Noberini / T. Bonaldi, IEO), or a deposited SDRF / experimentalDesign. Technical values already settled are in `annotations/PXD033337.report.md`.


## PXD046000 — PTP1B substrates by pTyr-IP SILAC phosphoproteomics in Ptp1b-/- vs +/+ MEFs (Villamar-Cruz et al., Mol Cell Biol 2023; duplex SILAC Arg6/Lys6, MaxQuant 1.2.0.18), whole dataset (10 RAW)

**Blocker: which SILAC channel holds which genotype is undocumented for the deposited runs.** The independent review failed the provisional map (+/+ light, −/− heavy) for three reasons:
- **Fig. 1B does not describe these runs.** It states ¹³C₆¹⁵N₄-Arg / ¹³C₆¹⁵N₂-Lys (Arg10/Lys8), the PRIDE protocol and Methods say the same, but the deposited search used `Arg6;Lys6`. Its heavy IDs (K and R) sit at ~0.3 ppm, so the heavy labels really were Arg6/Lys6.
- **The Table 1 check is circular.** Table 1 "KO/wt" equals Supplemental Dataset 2 `Ratio H/L`, but in Supplemental Dataset 1 the combined `Ratio H/L` for exactly the Table 1 sites falls outside that row's own NS and S ratios. Those values cannot be reproduced from any search.
- **The deposited ratios point both ways.** CDK Tyr15 has H/L Normalized 2.04, while EGFR pY1172 is 0.089 (count 15), CTNND1 pY904 0.19 and p38 pY182 0.32. Read in order, the PRIDE protocol sentence ("Ptp1b−/− and Ptp1b+/+ … light … or heavy") gives the opposite map.

Blocked runs: o110826_JC569_02, _03, _04, _06, _08, _10, _12, _13 (.RAW).

Also excluded: o110826_PMn_200_01 and _02 (.RAW). They are in no deposited search, and no source says what they are.

Not deposited: searched runs JC569_01/05/07/09/11, and the NS experiment runs JC569nselu_15..23 that appear in Supplemental Dataset 1.

Sources checked:
- PRIDE record and file list (22 files)
- MaxQuant summary, parameters, evidence, Phospho_STY_Sites and proteinGroups tables
- `search.zip` central directory (MaxQuant index only)
- Raw headers of 4 files: LTQ Orbitrap XL, no sample field
- Paper PMC10761042, its Fig. 1 and the supplementary zip (Datasets 1–2, figure legends)
- Haj 2003 (ref. 26)
- Cellosaurus: no entry for these MEFs

**Unblocked by:** a submitter statement (J. Chernoff / L.E. Arias-Romero) of which SILAC channel (light Arg0/Lys0 or heavy Arg6/Lys6) held Ptp1b+/+ and which held Ptp1b−/− MEFs in the o110826_JC569 runs. A statement of what `PMn_200` is would also settle those two runs. Settled technical values and the withdrawn draft tables are listed in `annotations/PXD046000.report.md`.

## PXD040125 — NF-κB interactome by SEC-PCP-SILAC in MCF-7 (Lapcik et al., Mol Cell Proteomics 2024; triple-SILAC H = ΔN-IκBα / M = empty vector / L = internal-standard pool + label-free SEC and DIA arms), non-SILAC runs excluded (excluded runs, not a blocker)

**Annotated:** the 80 SEC-PCP-SILAC runs `3502_Bouchal_Lumik2_1..80.raw` (Orbitrap Fusion Lumos, MaxQuant 2.0.3.0 Multiplicity 3) in `annotations/PXD040125.sdrf.tsv`.

**Excluded runs (out of scope for the SILAC campaign, not missing evidence; sample identities are in the deposited `Experimental_design.xlsx`):**
- 80 SEC-label-free Impact II QTOF runs `4641_QTOF1-batch1_*`, `4641_QTOF1-batch3_*`, `4641_QTOF1-batch4_*` (`.d.zip`; sheet `SEC_PCP_SILAC_80_label_free_fr`, 40 NF-κB-inhibited + 40 uninhibited SEC fractions; MaxQuant LFQ search `SEC_LFQ_MaxQuant_Search_Results.zip`).
- 34 SEC label-free QTOF runs of untransfected MCF-7 `2494_QTOF1_*` (`.d.zip`; sheet `SEC_label_free_34_fr`; search `SEC_34fr_MaxQuant_Search_Results.zip`).
- 24 RELA / IgG immunoprecipitation DIA runs `4626_Lumos1_134min-IS_HCD-OT_{DN,EM}_{CTRL,RELA}1-6_01.raw` (sheet `Immunoprecipitation_RELA`; Spectronaut `RELAIP_4626_2201.sne`).
- 8 total-proteome DIA runs `4642_Lumos1_134_PB_DIA_win_{DN,EM}1-4_1.raw` (sheet `Total_proteome`; Spectronaut `PCP_LFQ2021_Expr_4642_2201.sne`).

They would go in separate label-free / DIA SDRFs (batch rule 12).

**Open point for the reviewer:** the H/M direction rests on three concordant paper statements (Methods lines 116 and 122, Results line 188) and the MaxQuant label states. The bait NFKBIA is not identified in the SILAC search, so there was no ratio check.

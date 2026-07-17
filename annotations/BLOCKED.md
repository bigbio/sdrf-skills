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

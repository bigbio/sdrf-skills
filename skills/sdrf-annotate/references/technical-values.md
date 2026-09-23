# Reference: finding technical values (Step 5 of sdrf-annotate)

Instrument, modifications (read them out of the deposited search), cleavage agent, labels,
acquisition method, and raw-file verification. The values go into `technical.tsv`.

## Step 5: Fill Technical Metadata

> The values found in this step go into `technical.tsv` (Step 3.3), one row per column.

### 5.1 Instrument
```text
searchClasses(query="Q Exactive", ontologyId="ms")
Format in SDRF: AC=MS:1001911;NT=Q Exactive HF
```

If validation complains about an instrument term that is also documented in the
official PSI-MS / ProteomeXchange schema, verify the accession first instead of
rewriting the instrument blindly. Example: `LTQ Orbitrap Elite` with
`MS:1001910` may warn in some validator/cache combinations even though the term
is publicly documented.

### 5.2 Modifications — CRITICAL
Use EXACT UNIMOD accessions. Common setup:
```text
Column 1: NT=Carbamidomethyl;AC=UNIMOD:4;TA=C;MT=Fixed
Column 2: NT=Oxidation;AC=UNIMOD:35;TA=M;MT=Variable
Column 3: NT=Acetyl;AC=UNIMOD:1;PP=Protein N-term;MT=Variable
```
**Double-check**: UNIMOD:1 = Acetyl, UNIMOD:21 = Phospho. Most common swap!
For TMT: UNIMOD:737 (TMT6/10/11plex) or UNIMOD:2016 (TMTpro 16/18plex)

#### 5.2.1 Read the modifications out of the deposited search — do not infer them
`comment[modification parameters]` describes **what the search actually did**, so derive
it from the deposited search files. Paper Methods, PRIDE's `modifications` field (often
"No PTMs are included in the dataset" while the search used several), and reasoning from
the protocol are all downstream of it. Precedence: **deposited search settings > paper
Methods > PRIDE fields**. Open the search files *before* writing the columns — the same
files you open for the channel→sample map (Step 1.1) carry the modifications, so read
both out in one pass.

**Run the reader, do not write a parser.** Download the small search file (they are KB, not
GB - except PD, below) and run:

```bash
sdrf-tools search-params mqpar.xml        # or summary.txt, fragger.params, report.log.txt, x.msf
```

It prints `column<TAB>value` rows for `comment[modification parameters]` (one ` | `-separated
row, `PP=` for terminal mods), `comment[cleavage agent details]` and both tolerances, then
`# unmapped` (look each up in OLS; never guess the accession) and `# notes` (e.g. MaxQuant's
per-analyzer MS/MS tolerance: pick the instrument's MS2 analyzer). MaxQuant also yields the
file → experiment/fraction map, and TMT/iTRAQ/SILAC labels from `mqpar.xml`. MaxQuant 2.x
`parameters.txt` has **no** modifications - use `summary.txt` or `mqpar.xml`.
The table below is where each engine keeps them, for a file the reader does not cover.

| Search engine | Deposited file | Where the modifications are |
|---|---|---|
| Proteome Discoverer | `.msf`, `.pdStudy`, `.pdResult` (SQLite) | `Workflows` table → processing-node XML |
| MaxQuant | `parameters.txt`, `mqpar.xml` | `Fixed modifications` / `Variable modifications` |
| FragPipe / MSFragger | `fragger.params` | `table.fix-mods` / `table.var-mods` |
| DIA-NN | `report.log.txt` / logged command line | `--fixed-mod`, `--var-mod` (`--unimod4` = fixed Carbamidomethyl) |
| Spectronaut / SpectroMine | `.psar`, exported settings (UTF-16 strings) | modification list in the settings block |

**Proteome Discoverer `.msf` — read it, never download a multi-GB one.** `.msf`/`.pdResult` are SQLite
databases and routinely multi-GB (10.5 GB in the case below). A small one (tens of MB):
download it and run `sdrf-tools search-params`. A large one: read it with HTTP
byte-range requests over the SQLite pages, the same way you range-read a ZIP central
directory. The `Workflows` table stores each processing node's XML, which names every
modification verbatim with its purpose, its UNIMOD id and its target:

| XML `IntendedPurpose` | SDRF |
|---|---|
| `StaticModification` | `MT=Fixed`, residue → `TA=` |
| `DynamicModification` | `MT=Variable`, residue → `TA=` |
| any `…TerminalModification` (e.g. `StaticTerminalModification`) | same `Fixed`/`Variable` split, terminus → `PP=`, **never** `TA=` |

`UnimodAccession="4"` → `AC=UNIMOD:4`. The node XML also carries `CleavageReagent`
(→ `comment[cleavage agent details]`), so one read yields both.

*Worked example (PXD048052)*: the paper was closed (abstract only), and the producer
reasoned that the "microHOLD" single-cell protocol skips reduction/alkylation, so it
omitted Carbamidomethyl and set `comment[reduction reagent]` and
`comment[alkylation reagent]` to `not applicable`. The deposited PD `.msf` said
otherwise — `StaticModification` Carbamidomethyl/+57.021 Da (C), `UnimodAccession="4"`;
`DynamicModification` Oxidation/+15.995 Da (M), `UnimodAccession="35"`;
`StaticModification` + `StaticTerminalModification` TMT6plex (K / Any N-Term),
`UnimodAccession="737"`; `CleavageReagent` Trypsin (Full). Both missing modifications
had to be added and the reagent claims retracted.

**Reserved word for an undocumented reagent.** A fixed Carbamidomethyl in the deposited
search means alkylation was in the search space. If no primary source states which
reagent the prep used, set `comment[reduction reagent]` / `comment[alkylation reagent]`
to `not available` (used, unspecified) — **not** `not applicable`, which asserts the step
did not happen and contradicts the search you just read.

**Domain traps — verify, don't reflex** (each is validator-clean when wrong):
- **Dimethyl**: OLS returns `UNIMOD:510` for "Dimethyl" — that is
  `Dimethyl:2H(4)13C(2)` (+6). The plain light label is `UNIMOD:36`; heavy **+8
  is `UNIMOD:330`**. Match the mass to the labelling scheme; don't take the first hit.
- **Carbamidomethyl cuts both ways — the deposited search decides.** Do NOT
  assert `NT=Carbamidomethyl;AC=UNIMOD:4` when a primary source *explicitly*
  documents that reduction/alkylation was omitted (common in SCP protocols) — it
  is then wrong on every row and passes validation. But the inverse error is just
  as real: do NOT drop a Carbamidomethyl that the deposited search declares
  `Fixed` merely because the wet-lab reagent is unstated (§5.2.1, PXD048052).
  Silence about the prep is not evidence of no alkylation. When the deposited
  search params and the paper's Methods disagree, the search params win
  (precedence: raw > Methods > PRIDE).
- **Cell-line identity is a research task, not a lookup.** Pierce HeLa digest
  standard is **HeLa S3** (`CVCL_0058`), not parental HeLa (`CVCL_0030`);
  ATCC-purchased Jurkat is the **E6-1 clone** (`CVCL_0367`), not the naive
  `CVCL_0065`. Both wrong answers are validator-clean — confirm against the
  vendor's page, not just the name.
- **"Single-cell-equivalent" is a mass, not a count.** `0.5 ng ≈ 2–3 cells` is a
  dilution standard; annotate the mass, not `cells per well = 2`.
- **`developmental stage` is the DONOR's stage**, not a cell's maturation state
  (e.g. not an oocyte's IVM state) — the obvious-looking column is the wrong one.

### 5.3 Cleavage agent
```text
searchClasses(query="Trypsin", ontologyId="ms")
Format: NT=Trypsin;AC=MS:1001251
```

### 5.4 Labels
- Label-free: `label free sample`
- TMT: `TMT126`, `TMT127N`, `TMT127C`, etc. (one row per channel per file)
- SILAC: `SILAC light`, `SILAC heavy`

### 5.5 Acquisition method (PRIDE-first — required)
Column: `comment[proteomics data acquisition method]`

1. Look up terms under parent **`PRIDE:0000659`** (Proteomics data acquisition method)
   in the **PRIDE** ontology (OLS children/descendants of that parent).
2. Prefer PRIDE over PSI-MS for this column whenever a PRIDE child exists.
3. Write the **canonical case-sensitive** `NT=…;AC=…` form (labels must match OLS):

| Mode | Value |
|------|--------|
| DDA | `NT=Data-dependent acquisition;AC=PRIDE:0000627` |
| DIA (incl. SWATH / diaPASEF flavours) | `NT=Data-independent acquisition;AC=PRIDE:0000450` |
| SRM / MRM | `NT=Selected reaction monitoring;AC=PRIDE:0000630` |
| PRM | `NT=Parallel reaction monitoring;AC=PRIDE:0000629` |

Do **not** write plain text, `NT=`-only, or PSI-MS accessions (e.g. `MS:1000206`) for
this column when the PRIDE term above applies.

### 5.6 Verify technical metadata with raw file analysis (recommended)
If the dataset has raw files available (PRIDE or local), recommend using **techsdrf**
to verify and refine the technical metadata filled in Steps 5.1–5.5:
```text
Run `techrefine.md` PXD###### to verify instrument, tolerances, modifications,
and DDA/DIA classification directly from the raw MS files.
```
techsdrf can detect discrepancies between what's declared in the paper/PRIDE and
what's actually in the raw data — especially for instrument model specificity,
mass tolerances, and undeclared or incorrect modifications.

**Bruker timsTOF / diaPASEF — the DIA windows are readable without any of that.**
`analysis.tdf` inside a `.d` archive is a SQLite database, so one member of the ZIP
can be range-fetched (14.7 MB rather than a 2.5 GB download) and read directly:
```bash
sdrf-tools bruker-dia "<url of the .d.zip>"
```
It reports the isolation windows, m/z coverage and CE ramp. Fill
`comment[isolation window width]` from it and **only** from it: diaPASEF windows are
variable-width, the column is a single scalar, and deriving one from the manuscript
("15 windows spanning 400–1000" → 40) yields a width matching no actual window while
passing both the regex and `parse_sdrf`. When the widths vary, the honest value is
`not available` with the measured table in the report — see ``techrefine.md``.

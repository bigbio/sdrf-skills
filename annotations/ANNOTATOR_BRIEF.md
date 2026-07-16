# SDRF annotator brief

Operational brief for an agent annotating ONE PRIDE dataset. Lives in the repo (not `/tmp`) because
an earlier run kept it in the scratchpad, `/tmp` was wiped, and the resume path broke.

Work in `/home/sachsenb/Development/sdrf-skills`. Follow `skills/sdrf-annotate/SKILL.md`.

## Deliverable — BOTH are mandatory
1. `annotations/<PXD>.sdrf.tsv` (if annotatable) — validated
2. `annotations/<PXD>.report.md` — **ALWAYS**, even if you cannot annotate.
   If NOT annotatable: state exactly why, which sources you exhausted, and what would unblock it.
   Then append a section to `annotations/BLOCKED.md` in its existing format.
   **Never finish with only a TSV, and never finish with silence.**

## MANDATORY: private per-accession working directory
Agents run concurrently and have already corrupted each other. Real, observed failures:
- one agent's cached `files/all` payload was **silently overwritten with a different accession's
  data** mid-run — it annotates the wrong dataset unless it notices;
- another's `efetch.xml` was replaced by an unrelated paper;
- another's `build.py` was overwritten by a different dataset's script.

Root cause: a shared directory plus generic filenames (`files_all.json`, `build.py`, `efetch.xml`).

Before anything else:
```
mkdir -p "$CLAUDE_SCRATCH/<PXD>/"      # or <repo>/../scratch/<PXD>/ if no scratch var is set
```
- Write **every** temp file there and nowhere else.
- **Never read a scratch file you did not write in this run.**
- Point `get_pdf_by_unpaywall(output_dir=...)` at your own directory — `mcp/pdf/` is shared by
  default, so two agents fetching different papers collide.
- Touch ONLY your own `annotations/<PXD>.*` files.
- **Assert on read anyway**: after fetching `files/all`, check every entry's `projectAccessions`
  contains YOUR accession. That assertion is what saved the two agents that survived corruption.
  It also catches substitution from *outside*: Europe PMC's `supplementaryFiles` has returned an
  unrelated paper's `mmc*.xlsx`, and `efetch` with `id=PMC…` silently returns a different article
  (only the numeric id works). Verify returned titles/accessions, not just HTTP status.

## Hard-won rules — violating these produces silently wrong output
- **File list**: use `https://www.ebi.ac.uk/pride/ws/archive/v3/projects/<PXD>/files/all`.
  The MCP `get_project_files` **silently truncates at 100 files** (#32). Never use it for counts or
  `comment[data file]`. If PRIDE exposes only ZIP bundles, HTTP-range-read the zip central directory
  and inflate individual members — do not download multi-GB archives.
- **Precedence: raw data > paper Methods > PRIDE fields.** PRIDE's `instruments` was wrong in ≥6
  datasets (HF vs HF-X; LTQ Orbitrap Velos vs Velos Pro; LTQ Orbitrap Elite vs Fusion Lumos;
  Q Exactive vs Q Exactive Plus) and has contradicted its own protocol text. Its `modifications`
  often says "No PTMs are included in the dataset" while the paper lists several. Its protocol text
  has misstated the labelled arm, cell type and isolation method.
  - Thermo `.raw`: HTTP-range the first ~256 KB, decode utf-16-le, grep the model.
  - Bruker `.d`: `analysis.tdf` is SQLite (`DiaFrameMsMsWindows` = DIA windows), ~15 MB inside a
    multi-GB archive (#33).
  - Deposited search outputs beat Methods prose: MaxQuant `summary.txt`/`parameters.txt`,
    FragPipe `fragger.params`, DIA-NN logs, Proteome Discoverer `.msf` (SQLite), SpectroMine
    `.psar` (UTF-16 strings). Often the ONLY source of the channel→sample map.
- **`is_open_access` is unreliable** in PRIDE *and* Europe PMC. A gold-OA CC-BY paper was reported
  `false` by both. Always try `get_pdf_by_unpaywall`; also the PMC HTML render, NCBI eutils, and
  Europe PMC free-text search on the accession itself. Unpaywall has returned anti-bot HTML while
  reporting `oa_status: green`.
- **OLS smart mode returns confident WRONG single hits.** `HeLa`→`HeLa-MAGI-CCR5`/`HEp-2`;
  `A549`→`A549-CR`; `methotrexate`→"High-dose Methotrexate/Rituximab Regimen";
  `thymidine`→"Thymidine Kinase, Cytosolic"; `hippocampus`→"CA1 field". For cell lines, drugs and
  anatomy: always also run `mode="fuzzy"` and eyeball. Verify EVERY accession live. Never guess one.
  Check CL/UBERON **definitions**, not label matches (`macular hair cell` is *auditory*).
- **Cell-line identity is research, not lookup.** Commercial Pierce HeLa digest standard is
  **HeLa S3** (`EFO:0002791` / `CVCL_0058`), stated only on the vendor page — not parental HeLa
  (`EFO:0001185` / `CVCL_0030`). Inversely, ATCC-purchased Jurkat is the **E6-1** clone
  (`CVCL_0367`, ATCC TIB-152); naive `Jurkat → CVCL_0065` is validator-clean and wrong.
- **UNIMOD:1 = Acetyl, UNIMOD:21 = Phospho.** Positional values go in `PP=`, never `TA=`.
  **Dimethyl trap**: OLS returns `UNIMOD:510` for "Dimethyl" — that is `Dimethyl:2H(4)13C(2)` (+6).
  Heavy +8 is **UNIMOD:330**. Derive each channel from the actual stated mass shift.
  **Never assert Carbamidomethyl without an alkylation step** — many SCP protocols eliminate
  reduction/alkylation; the reflex annotation is wrong on every row and passes validation.
- **"Single-cell-equivalent" is a mass, not a count.** `0.5 ng ≈ 2–3 cells` is a dilution standard:
  `sample type = standard`, `cells per well = not applicable` — not 2 or 3.
- **Column licensing**: every `characteristics[...]` you use MUST be licensed by a template you
  declare in `comment[sdrf template]`. Resolve with `spec/scripts/resolve_templates.py`.
  `characteristics[genotype]` and `[phenotype]` are licensed ONLY by `clinical-metadata` (which adds
  no new required columns beyond `disease`). `parse_sdrf` does NOT check licensing.
- **Reserved words**: `not available` ≠ `not applicable`. Check each column's `allow_not_available` /
  `allow_not_applicable` in the **RESOLVED template** — TERMS.tsv disagrees with it (e.g.
  `single cell isolation protocol`). `parse_sdrf` does NOT enforce these. Never N/A, NA, unknown.
- **`developmental stage` means the DONOR's stage**, not an oocyte's maturation state.
- **`parse_sdrf` exit 0 proves well-formedness, never truth.** It silently accepts
  `NCBITaxon:99999999`, `MS:9999999`, `EFO:9999999`, `BOGUSLABEL999` and `N/A` (#35). Mutation-test
  it if you intend to lean on a clean pass.

## Annotatability — decide BEFORE investing
An SDRF needs one row per (file × label channel), each with a sample identity.
- **Label-free, 1 file = 1 cell** → annotatable.
- **Multiplexed** (TMT/plexDIA/dimethyl): you MUST find the channel→sample map. Check the paper +
  supplementary, the deposited result tables (Proteome Discoverer defaults every channel to
  `"Sample, n/a"` = NO map; SpectroMine `.psar` likewise), `files/all` for a sample sheet, and
  `https://www.ebi.ac.uk/europepmc/webservices/rest/<PMCID>/supplementaryFiles`.
  Layouts can **flip between runs** — never assume one fixed layout.
  If no map exists → **BLOCKED**. Do not fabricate channel identities. Write the report +
  BLOCKED.md entry. A partial annotation (one arm annotatable, another not) is legitimate.
- Supplementary per-sample tables are gold — but verify they belong to YOUR paper.

## Scope
Annotate every DEPOSITED run that has a sample. Pools, dilutions, blanks and carriers are not
single cells — classify them by actual `cells per well` and `sample type`. A run may be excluded
ONLY if a required column forbids both reserved words (the known `characteristics[cell line]` trap
under `cell-lines`, #35 B1). Always state the deposited-vs-annotated reconciliation in the report.

## Validate
```
source /home/sachsenb/miniforge3/etc/profile.d/conda.sh && conda activate sdrf-skills
parse_sdrf validate-sdrf --sdrf_file annotations/<PXD>.sdrf.tsv --template <t1> --template <t2> ...
```
Fix every ERROR. Warnings are acceptable if justified — say so in the report. Note `parse_sdrf`
requires factor-value columns **last**, contradicting `sdrf-annotate/SKILL.md` Step 3.

## Known tool defects — do NOT act on these
`tools check` emits false-positive "hallucinated term" warnings from an offline map.
`tools score` wrongly calls the mass-tolerance columns "required" and rejects valid compound ages
(`30Y6M`, which Cellosaurus itself emits).

## Report contents
Study + publication; templates chosen and why; scope (deposited vs annotated, reconciled); key
decisions with evidence; every value left `not available`/`not applicable` and WHY; conflicts found
(e.g. PRIDE vs paper) and how resolved; what was **inferred** vs **stated**; the judgement calls you
want a reviewer to attack hardest.

Do NOT approve your own work — a separate reviewer handles that.
Return a 6-line summary: PXD | ANNOTATED or BLOCKED | rows × cols | templates | validation result |
one-line reason if blocked.

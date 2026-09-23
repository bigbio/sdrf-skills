# Reference: gathering the project record (Step 1 of sdrf-annotate)

PRIDE metadata, the file list, the publication, sample metadata from the paper, BioSamples,
and the plasma guard. Read when the record is not already on disk. In offline mode the
record is in `evidence/`; only 1.4 (reading the paper) and 1.5 (plasma) still apply.

## Step 1: Gather Project Context

If a **PXD accession** is provided:

### 1.1 Get PRIDE project metadata

> **Offline mode (Step 0):** skip this step — the PRIDE record is already in `evidence/pride.json`; read that instead.

```text
Tool: get_project_details(project_accession="PXD######")
Extract: title, description, sample_processing_protocol, data_processing_protocol,
         organism, instruments, modifications, publications, keywords
```
`publications` is a LIST of fully-resolved records — one per PRIDE reference:
```json
{"pmid": "24657495", "pmcid": "PMC4047622", "doi": "10.1016/j.jprot.2014.03.010",
 "is_open_access": true, "reference": "Collins MO et al. J Proteomics 2014..."}
```
PMID → PMCID/DOI/open-access resolution is done **inside this call** via
Europe PMC. You do NOT need a separate identifier-conversion tool.

The sample/data processing protocols are submitter-authored free text and are
often the highest-signal source for enzyme, modifications, tolerances, labeling,
and instrument acquisition — read them BEFORE the publication.

> **PRIDE's structured fields are NOT ground truth — trust them last.**
> Precedence for any disputed value is **raw data > paper Methods > PRIDE fields**.
> Across a 26-dataset audit, `get_project_details` was wrong repeatedly:
> - `instruments` off by model/variant (HF vs **HF-X**; LTQ Orbitrap Velos vs
>   **Velos Pro**; LTQ Orbitrap Elite vs **Fusion Lumos**; Q Exactive vs
>   **Q Exactive Plus**) — and sometimes the structured field contradicted the
>   free-text protocol *in the same record*.
> - `modifications` routinely said "No PTMs are included in the dataset" while the
>   paper listed several.
>
> When a value matters, recover it from the primary sources instead of trusting the field:
> - **Instrument model** — HTTP-range-read the first ~256 KB of a Thermo `.raw`
>   (utf-16-le); the model string is in the header. Bruker `.d` →
>   `analysis.tdf` is a SQLite DB (see the Bruker skill, #33).
> - **Search settings & the channel→sample map** — deposited search outputs beat
>   Methods prose: MaxQuant `summary.txt`/`parameters.txt`, FragPipe
>   `fragger.params`, DIA-NN logs, PD `.msf`/`.pdStudy` (SQLite), SpectroMine
>   `.psar`. These are often the *only* source of the channel map, **and they are
>   the authoritative source of the search modifications** (static/dynamic) that
>   drive `comment[modification parameters]` — see §5.2.1. Read both out of the
>   same file in one pass.
> - **Run names inside huge archives** — read the ZIP central directory via an
>   HTTP range request rather than downloading a multi-GB archive.

### 1.2 Get the file list

> **Offline mode (Step 0):** skip this step — the run's file list is already in `evidence/files.json`; read that instead.

```text
Tool: get_project_files(project_accession="PXD######")
Extract: raw_file_names (for comment[data file]), rawfile_count,
         ftp_root_url   (HTTPS mirror of the PRIDE folder — all files live here),
         aspera_root_url (use for high-throughput bulk transfer)
```

If MCP access is unavailable or incomplete, prefer the PRIDE Archive REST fallback:
```text
GET https://www.ebi.ac.uk/pride/ws/archive/v3/projects/PXD######/files/all
```
Use this endpoint to retrieve the complete file list for the project in one call.
It is the preferred REST path for counting files, checking raw-file coverage, and
building `comment[data file]` values during annotation.
If this endpoint returns `0` files for a valid PXD hosted through
`PanoramaPublic`, `MassIVE`, `iProX`, or `jPOST`, treat that as
`archive endpoint empty for external repository` rather than `no data`.
For MassIVE-backed datasets, use the helper in this repo to recover raw
file names from ProteomeCentral + MassIVE JSON + MassIVE FTP:
```bash
sdrf-tools massive-files PXD016117 --mode raw
sdrf-tools massive-files PXD016117 --mode acquisition --format tsv
```
This is the preferred fallback when you need `comment[data file]` values for a
MassIVE-hosted PXD and PRIDE does not expose the archive file list. The helper
resolves the MassIVE accession through ProteomeCentral, inspects the MassIVE
dataset details, and then walks the MassIVE FTP tree deterministically.
Also inspect companion files under MassIVE `other/` or supplementary dataset
attachments. In practice these often contain the curator key you need for TMT
channel-to-sample mapping, pooled-reference channels, blanks, longitudinal
timepoints, or cohort aliases that are not recoverable from PRIDE metadata
alone.

### 1.3 Find and read the publication

> **Offline mode (Step 0):** skip this step — the paper, if one is available, is already in `evidence/manuscript.txt`; if that file is absent there is no paper to find — do not search for one.


For each record in `publications` (Step 1.1), pick exactly ONE tool:

> **`is_open_access` is unreliable — a `false` means "try harder", not "abstract
> only".** Both PRIDE and Europe PMC reported a gold-OA CC-BY paper as
> `is_open_access: false`; Europe PMC has returned anti-bot HTML while reporting
> `oa_status: green`, and `fullTextXML` sometimes 404s for papers that are in
> fact open. Before falling back to abstract-only (branch b), exhaust the
> recovery routes: Unpaywall (by DOI), the PMC HTML render, NCBI eutils, and a
> Europe PMC free-text search on the **accession itself**. Several datasets'
> entire Methods — hence cell line, channel map, instrument — hung on not
> believing this flag.

```text
a. pmcid is set AND is_open_access == true:
     → get_full_text_article(pmc_ids=["PMC######"])
     Default response is slim: only SDRF-relevant sections (Methods /
     Materials / Experimental procedures / Sample processing) + abstract +
     deduped table and supplementary captions. Results/Discussion are
     EXCLUDED by default to keep context small.

     If raw Europe PMC `fullTextXML` would otherwise be requested, do NOT pass
     that XML directly to the model. Normalize it first with the local helper:
        `python scripts/europepmc_fulltext.py PMC###### --section methods --section results --format text`
        or `python scripts/europepmc_fulltext.py PMC###### --format json`
     Use this helper when MCP full-text tools are unavailable, when you need
     canonical article links, or when accession detection from the manuscript
     will help downstream annotation.

     If you need Results text (rare — sometimes Table 1 sits there):
        get_full_text_article(pmc_ids=["PMC######"], sections=["results"])

     If the paper is very long or the Methods section alone still overflows
     context, use the two-step TOC-first flow:
        1. get_full_text_article(pmc_ids=["PMC######"], mode="toc")
           → returns section titles + char counts, table/suppl captions,
             abstract. ~1-3 KB.
        2. get_full_text_section(pmc_id="PMC######", section="<name>")
           → pulls that ONE section's full body. On miss it returns an
             `available` list so you can retry with a valid name.

b. otherwise (pmid and/or doi set, but no OA full text):
     → get_article_metadata(ids=["<PMID or PMCID or DOI>"])
     This ONE tool accepts any mix of PMID / PMCID / DOI and returns abstract +
     metadata only. Tell the user the full text is not openly available and
     that only the abstract was used.
```

**When `publications` is empty, or every record has null pmid/pmcid/doi**,
do NOT search for a paper. Stop and ask the user:
> "PRIDE does not list a resolvable publication for `PXD######`, and I cannot
> fetch the article automatically. Could you provide a PMID, PMCID, DOI, or
> paste the Methods section so I can continue? Otherwise I will proceed with
> PRIDE metadata only and mark affected columns as `not available`."

Rule: whenever Europe PMC full text XML would otherwise be requested, always use
`scripts/europepmc_fulltext.py` to normalize the article first. Do not pass raw
JATS/XML directly to the model unless the user explicitly asks for raw XML.

### 1.4 Extract sample metadata from the paper
Read the paper systematically and extract:
- How many samples? How many conditions/groups?
- Tissues/cell types per group
- Patient demographics (age, sex, ancestry) if available
- Developmental stage when the cohort is clearly adult, pediatric, fetal, juvenile, etc.
- Experimental conditions (treatment, disease state, time points)
- Labeling strategy (which TMT/iTRAQ channels for which samples)
- **The Data Availability and Code Availability statements** — copy every
  accession, DOI and URL they cite (Zenodo, figshare, OSF, Dryad, GitHub).
  For a multiplexed dataset these links are frequently where the channel→sample
  map actually lives; see Step 6.1.
- Fractionation details (number of fractions, method)
- Instrument and acquisition method details
- Modifications searched — the paper is a cross-check here, not the source;
  the deposited search files decide (§5.2.1)

Demographic evidence rules:
- `characteristics[developmental stage]` can be added from cohort-level evidence when the whole analyzed cohort is clearly in one stage, for example all subjects are adults or the study is explicitly pediatric.
- `characteristics[age]`, `characteristics[sex]`, and `characteristics[ethnicity]` should be added only when they can be mapped to individual source samples or a per-sample supplementary table.
- If the paper reports only group summaries such as median age, percent male, or ethnicity distribution, keep those fields out of per-sample SDRF rows and mention the limitation in the notes.

### 1.4b Map PRIDE source samples to ENA/BioSamples when possible
For datasets with paired ENA/SRA/BioSamples records, especially metaproteomics studies:

- Treat BioSample accessions as **source-sample identifiers**, not raw-file identifiers
- A repeated BioSample accession across many SDRF rows is correct when those rows share the same `source name`
- Do **not** assume one BioSample per raw file, fraction, or technical replicate

Use this mapping order:

1. Prefer **exact study-linked lookups** in ENA or BioSamples:
   - ENA sample search by study/BioProject accession
   - BioSamples exact filters on project/study accessions
2. Compare the returned sample metadata against the paper and PRIDE:
   - collection date
   - geographic location / coordinates
   - isolation source / environmental medium
   - sample title / alias
   - whether the study describes one shared source sample or multiple distinct source samples
3. Add `characteristics[biosample accession number]` only when:
   - the PRIDE `source name` clearly maps to a deposited ENA/BioSamples sample, or
   - there is one well-supported shared source sample that all assay rows derive from

Avoid this failure mode:

- BioSamples UI free-text search can return unrelated accessions through fuzzy matching
- Treat UI text-search hits as **leads only**, not evidence
- Confirm project membership with exact ENA/BioSamples study-linked queries before annotating

Metaproteomics rule of thumb:

- if all rows in one SDRF share one `source name`, one `biological replicate`, and differ only by fraction / technical replicate / workflow, repeating one BioSample accession across those rows is usually the correct representation
- if the paper describes multiple distributed aliquots from one shared environmental source sample, a single repeated BioSample accession may still be appropriate if the external record clearly represents that shared source sample

### 1.5 Guard plasma campaigns against false positives
If the user is targeting blood-plasma projects:
- default to `Homo sapiens` unless the user explicitly requests animal studies
- confirm species with PRIDE `organisms` first
- if PRIDE species is incomplete, use the linked paper to confirm that the plasma cohort is human-only before promotion
- keep mouse, rat, or mixed-species plasma projects as audit-only candidates until the user asks for them
- expand the disease through OLS before PRIDE discovery:
  - lexical OLS first in `MONDO`, `DOID`, `EFO`, and `NCIT`
  - add useful synonyms and preferred labels
  - use OLS embeddings for broad disease names when subtype phrasing is likely in PRIDE, for example `kidney tumor` -> renal cancer variants
  - keep in-scope child terms when biomarker studies use the subtype rather than the parent label, for example `myositis` -> `dermatomyositis`, `sarcoma` -> `Ewing sarcoma`, `myeloma` -> `multiple myeloma`, or `alcohol-related liver disease` -> `alcoholic hepatitis`
  - for influenza-like campaigns, acceptable widening can include `influenza A`, `IAV`, `H1N1`, `flu`, and, if explicitly allowed by the user, broader `viral pneumonia` plus `serum`
  - tag each promoted candidate as an `exact`, `child_term`, `related`, or `surrogate` disease match so later ranking is honest about coverage strength
- classify the project workflow from PRIDE before prioritizing it:
  - read `experimentTypes` for acquisition style like `Data-independent acquisition`, `Data-dependent acquisition`, or `Gel-based experiment`
  - read `quantificationMethods` for explicit quant style like `TMT`, `iTRAQ`, `label-free quantification`, `Dimethyl Labeling`, or `NSAF`
  - if those fields are incomplete, inspect `sampleProcessingProtocol`, `dataProcessingProtocol`, keywords, and the manuscript methods section for explicit `TMT`, `iTRAQ`, `LFQ`, `DIA`, `SWATH`, `MaxQuant`, or `Spectronaut` wording
  - keep separate `acquisition_mode` and `quant_mode` annotations rather than collapsing everything into one label
- treat `blood plasma`, `plasma proteome`, `plasma samples`, and `plasma extracellular vesicles` as valid plasma-sample signals
- do NOT treat `plasma cells` or `plasma membrane` as blood-plasma sample signals
- for the current plasma-dataset campaigns, only promote datasets hosted by `PRIDE`, `MassIVE`, `jPOST`, or `iProX`; keep `PanoramaPublic` hits as audit-only candidates for now
- for automatic discovery or ranking, only shortlist accessions when plasma context is present (`positive` or `ambiguous`) and the disease is explicit in the title, description, or linked paper
- keep `plasma_context=missing` disease hits as audit-only candidates until manuscript or PRIDE evidence confirms a real blood-plasma sample
- if a candidate dataset lacks usable raw or acquisition files, do not promote it into the active annotation set even if the disease and matrix match
- when a manuscript is available, classify the accession before annotation:
  - `confirmed_plasma` if plasma is explicit in title, abstract, methods, results, or supplementary text
  - `mixed_includes_plasma` if plasma is explicit but the study also includes CSF, serum, tissue, urine, or cell-line material
  - `likely_non_plasma` if the manuscript points to a different primary matrix such as CSF, platelet releasate, urine, BALF, or cell-line material
  - `unclear` if the paper cannot confirm plasma; do not auto-promote these datasets into a plasma campaign
- if the accession is already present in the local plasma collection, refine the existing SDRF instead of creating a duplicate target

If **no PXD** but an experiment description, skip to Step 2.

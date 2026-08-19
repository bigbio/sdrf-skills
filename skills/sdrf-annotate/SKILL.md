---
name: sdrf:annotate
description: Use when the user wants to create or annotate an SDRF file for a proteomics dataset. Triggers on PXD accessions, requests to create SDRF, or annotation tasks.
user-invocable: true
argument-hint: "[PXD accession or experiment description]"
---

# SDRF Annotation Workflow

You are performing a complete SDRF annotation. Follow these steps IN ORDER.
Do not skip steps. Do not guess — use MCP tools to verify everything.

## Step 0a: Isolate this dataset's working files (required)

When annotators run concurrently they collide through a **shared scratchpad**:
generic filenames (`files_all.json`, `build.py`, `efetch.xml`) written by several
agents into one directory silently overwrite each other. The failure is silent —
the file still parses, it just describes a *different* dataset — so an agent that
trusts the re-read annotates the wrong PXD. This has happened (a cached PRIDE file
list overwritten mid-run with another accession's data; an `efetch.xml` replaced
by an unrelated paper).

1. Derive your working directory from the accession — `scratchpad/<PXD>/` — and
   write **every** temp file there and nowhere else.
2. Never read a scratch file you did not write in **this** run.
3. Point PDF/full-text fetchers at that directory
   (`get_pdf_by_unpaywall(output_dir="scratchpad/<PXD>/")`); `mcp/pdf/` is shared
   by default and two agents fetching different papers will collide.
4. **Assert on read anyway** (defence in depth — the substitution also comes from
   outside): after fetching the file list, check every entry's `projectAccessions`
   contains your accession; when you pull supplementary files or an `efetch`
   result, verify the returned **title/accession**, not just HTTP 200. (Europe
   PMC `supplementaryFiles` has returned another paper's `mmc*.xlsx`; `efetch`
   with `id=PMC…` silently returns a different article — use the numeric id.)

## Step 0: Check parse_sdrf availability

Before starting, verify that `parse_sdrf` is available (run `parse_sdrf --version` or `which parse_sdrf`). If it is not installed:
- Inform the user that programmatic validation will be skipped
- Suggest `/sdrf:setup` or `conda env create -f environment.yml && conda activate sdrf-skills` (or `pip install -r requirements.txt`)
- Offer to continue with manual checks only, or wait for the user to install and retry

## Step 0.5: Check whether the dataset is ALREADY annotated — STOP GATE

**Do this before any annotation work.** Annotating a dataset that is already
annotated is not free: if the existing file is fine you have wasted the effort and
produced a noisy diff, and if it is wrong you may ship a second annotation beside
it without anyone noticing the first was broken.

### 0.5.1 Look it up in the community repository

**Enumerate the accession directory — do not probe for a single filename.** A PXD
directory may hold several SDRFs distinguished by descriptive suffixes
(`PXD004452-tissues.sdrf.tsv` + `PXD004452-celllines.sdrf.tsv`,
`PXD006430-tmt.sdrf.tsv` + `PXD006430-silac.sdrf.tsv`), and many accessions have
**no** `{PXD}.sdrf.tsv` at all — only a suffixed variant such as
`PXD001064-DIA.sdrf.tsv`. Checking one canonical name reports those as `new` and
skips the gate entirely.

```bash
gh api repos/bigbio/sdrf-annotated-datasets/contents/datasets/{PXD} \
  --jq '.[] | select(.name | endswith(".sdrf.tsv")) | .name' 2>/dev/null
```

Check the **community repository**, which is authoritative. A local
`spec/annotated-projects/` copy may be stale, so do not rely on it alone.

Interpret the listing as an **artifact set**, not a yes/no:

- **No directory, or no `.sdrf.tsv` in it** → new annotation. Continue to Step 1.
- **The file you intend to write already exists** → STOP, go to 0.5.2.
- **Only other SDRFs exist for this PXD** (a different sub-experiment, e.g. you
  are writing `-celllines` and only `-tissues` is present) → this is still a new
  file, but say so explicitly and name the sibling files, since they constrain
  what your file should cover and how it should be named. Audit a sibling only if
  you intend to replace it.

Use the same artifact set in `/sdrf:contribute` rather than recomputing it, so the
two workflows cannot disagree about what "already annotated" means.

### 0.5.2 Audit the existing annotation

Never assume the existing file is right, and never assume it is wrong. Fetch it
and audit it against the deposit:

**The audit must not run on a failed download.** `curl -o` truncates its target
even when the request fails, so an unchecked fetch can leave an empty file or an
HTML error page and the audit will then describe *that* instead of the
annotation. Chain on success, and use `curl -f` so an HTTP error is a failure:

```bash
set -euo pipefail
url=$(gh api "repos/bigbio/sdrf-annotated-datasets/contents/datasets/{PXD}/{FILE}" --jq .download_url)
[ -n "$url" ] || { echo "could not resolve download URL — abort, do NOT audit"; exit 1; }
curl -fsSL "$url" -o existing.sdrf.tsv
[ -s existing.sdrf.tsv ] || { echo "empty download — abort, do NOT audit"; exit 1; }

python -m tools audit-existing existing.sdrf.tsv --accession {PXD} \
  --runs deposited_runs.txt --organism "<each organism PRIDE registers>"
```

If any step fails, report the failure and stop. Never treat a fetch error as
"no existing annotation" — that turns an infrastructure problem into a silent
overwrite.

The audit is mechanical and checks only what the deposit can settle:

| Check | Severity | Catches |
|---|---|---|
| `missing_runs` / `invented_runs` | blocker | annotation does not match the deposited files |
| `organism_mismatch` | blocker | organisms PRIDE registers that never appear in the SDRF |
| `counter_abuse` | major | `technical replicate` / `fraction identifier` used as a row index |
| `cv_term_no_accession` | major | `NT=` with no `AC=` |
| `no_factor_value` | major | no factor value column declared |
| `characteristics_not_bare_label`, `source_name_convention` | minor | convention drift |

Also validate the existing file — it can be structurally valid and still be wrong
about the deposit, so the two checks are complementary. Validate the way the rest
of this repo requires: **once per declared template, against the rows that declare
it, requiring every run to pass.** `--template` is single-valued, so passing
several flags silently validates against only the last one:

```bash
# read the declared templates from the file itself
cut -f"$(head -1 existing.sdrf.tsv | tr '\t' '\n' | grep -n '^comment\[sdrf template\]$' | cut -d: -f1)" \
  existing.sdrf.tsv | tail -n +2 | sort -u

# then, once per declared template
parse_sdrf validate-sdrf --sdrf_file existing.sdrf.tsv --template <one-template>
```

Use `spec/scripts/resolve_templates.py` for the authoritative multi-template
constraint set (column licensing and reserved-word `allow_*`); `parse_sdrf`
enforces neither.

`--runs` and `--organism` are optional, and when omitted the corresponding checks
are **skipped, not passed**. Supply them whenever you have them, and say which
checks were skipped when reporting. If you supply them and the SDRF lacks the
column they check, the audit reports that as a blocker rather than a skip.

### 0.5.3 Report and let the USER decide

Present the finding and stop. Do not pick for them:

```text
{PXD} is already annotated in the community repository ({N} rows).

Audit result: {clean | N issues}
{rendered findings, most severe first}

How would you like to proceed?
  - leave        - the existing annotation is adequate; do nothing
  - fix          - open a PR addressing ONLY the defects above
  - reannotate   - rebuild from scratch and open a PR replacing the file
```

Choose what to *recommend* by defect class, and say why:

- **no findings** → recommend `leave`. Re-annotating a correct file produces
  churn for reviewers and risks regressing curation someone did by hand.
- **only major/minor findings** → recommend `fix`. A targeted diff is far easier
  to review than a wholesale replacement, and it preserves existing work.
- **any blocker** → recommend `reannotate`. When the file misrepresents which
  runs or which organisms the deposit contains, patching individual cells tends
  to leave the underlying structure wrong.

**Never re-annotate silently, and never overwrite an existing annotation without
the user explicitly choosing `reannotate`.** If the user does choose it, continue
to Step 1 and treat the result as an **update** to an existing dataset: the PR must
say what was wrong with the previous annotation and cite the evidence, so a
reviewer can check the claim rather than take it on trust.

## Step 1: Gather Project Context

If a **PXD accession** is provided:

### 1.1 Get PRIDE project metadata
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
python -m tools massive-files PXD016117 --mode raw
python -m tools massive-files PXD016117 --mode acquisition --format tsv
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

## Step 2: Select Templates

Use the sdrf:templates decision tree. Based on the gathered context:

1. **Technology**: MS → `ms-proteomics`. Affinity → `affinity-proteomics`
2. **Organism**: Human → `human`. Mouse/rat → `vertebrates`. Drosophila → `invertebrates`. Plant → `plants`. Microbiome → `metaproteomics` + child
3. **Experiment type**: DIA → `+ dia-acquisition`. Cell lines → `+ cell-lines`. Single-cell → `+ single-cell`. XL-MS → `+ crosslinking`. Immunopeptidome → `+ immunopeptidomics`
4. **Clinical/Oncology**: Patient study → `+ clinical-metadata`. Cancer → `+ oncology-metadata`

Present the template selection to the user for confirmation before proceeding.
Explain WHY each template was chosen and what columns it adds.

## Step 3: Build the SDRF Structure

Determine the columns to include based on the selected templates:

1. **Read `spec/sdrf-proteomics/TERMS.tsv`** — filter rows where `usage` contains each selected template name
2. **Read individual template YAMLs** at `spec/sdrf-proteomics/sdrf-templates/{name}/{version}/{name}.yaml` for requirement levels
3. Merge all columns from all selected templates (union of all template column sets)

Organize columns in this order:

**Anchor columns:**
1. `source name`

**Characteristics columns (sample metadata):**
- All `characteristics[...]` columns from TERMS.tsv for the selected templates
- Order: organism, organism part, disease, cell type, material type, then template-specific (developmental stage, age, sex, cell line, etc.), then biological replicate

**Anchor + technology:**
- `assay name`
- `technology type`

**Comment columns (technical metadata):**
- All `comment[...]` columns from TERMS.tsv for the selected templates
- Order: instrument, label, modification parameters (one per mod), cleavage agent details, acquisition method, dissociation method, collision energy, tolerances, template-specific (scan windows for DIA, etc.), fraction identifier, technical replicate, data file

**Factor values:**
- `factor value[<variable>]`

**SDRF metadata:**
- `comment[sdrf version]` (read the current version from `spec/sdrf-proteomics/sdrf-templates/templates.yaml`)
- `comment[sdrf template]` (one column per template, format: `NT=template_name;VV=vX.Y.Z`)

## Step 4: Fill Sample Metadata

Before filling demographic fields, decide whether the paper supports:
- cohort-level demographic context only
- or true sample-level demographic assignment

Use this rule:
- `developmental stage` may come from cohort-level manuscript evidence if the full analyzed cohort is unambiguously adult, pediatric, fetal, juvenile, and so on
- `age`, `sex`, and `ethnicity` require source-sample or individual-level mapping
- if only cohort summaries exist, leave per-sample demographic fields as missing / omitted rather than guessing

For EACH unique value that goes into a characteristics column:

### 4.1 Normalize a short mention first
- If the value already comes from PRIDE metadata or an existing SDRF cell, clean that value and use it directly.
- If the value comes from a manuscript, first extract the shortest standalone entity phrase and keep the sentence only as evidence.
- Search the expanded form before the abbreviation when both are available.
- Do NOT send full manuscript sentences to OLS or ZOOMA unless you are debugging a failed lookup.

### 4.2 Search OLS lexically first
```text
Use: searchClasses(query="breast carcinoma", ontologyId="mondo")
Or:  search(query="Homo sapiens")       # only when the target ontology is unknown
```
For clean SDRF-like values, lexical exact or synonym matches are the default path and usually outperform embeddings.

**Smart mode is the default** (do NOT pass `mode` unless you need to override):

1. The tool tries an **exact** label/synonym match, probed wide.
   - Exactly one *distinct* term → returns it. Use its accession directly.
   - Several distinct terms match exactly → the response carries
     `ambiguous: true` and lists them. This is NOT a single answer — pick the
     intended entity yourself (see the trap table below), do not grab the first.
2. If there is no exact hit → the tool falls back to **fuzzy top-3**
   and tags the response with `fallback: "fuzzy"`.
   - Pick the best candidate. If none fit, refine the query (correct typos,
     try a synonym, or switch to a more specific ontology) and search again.

> **For controlled identifiers that a query commonly over-matches — cell lines
> (`HeLa`), drugs (`methotrexate`), anatomy (`hippocampus`) — do not trust a
> single smart-mode hit.** In an audit, smart mode returned confident *wrong*
> single hits: `HeLa` → `HeLa-MAGI-CCR5`, `A549` → `A549-CR` (a resistant
> derivative), `methotrexate` → `High-dose Methotrexate/Rituximab Regimen`,
> `hippocampus` → `CA1 field of hippocampus`, and `in vitro maturation` →
> unrelated terms for a concept with *no* OLS term. For these, pass
> `mode="fuzzy"` and eyeball the candidates against the intended entity.

Override only when necessary:
- `mode="exact"` — force exact-only (e.g. strict validation); empty on miss.
- `mode="fuzzy"` — force fuzzy top-N; use for cell lines/drugs/anatomy and when
  exploring close neighbours.

### 4.3 Use embeddings and ZOOMA only when needed
Trigger OLS embedding search when:
- lexical search returns no result
- the mention is abbreviation-like (`HCC`, `PDAC`, `GBM`, `TNBC`)
- the top lexical hits are conflicting or clearly over-specific
- the mention came from noisy manuscript text rather than a curated label

Use the OLS MCP tools in this order:
```text
1. listEmbeddingModels()
2. searchClassesWithEmbeddingModel(query="<clean phrase>", ontologyId="<ontology>", model="<embed model>")
3. If ontology-specific search is unavailable, use searchWithEmbeddingModel() and filter manually
```

Use ZOOMA as a slower fallback for manuscript-derived free text or when lexical and embedding results still disagree:
```text
GET https://www.ebi.ac.uk/spot/zooma/v2/api/services/annotate?propertyValue=<clean phrase>&propertyType=<field>
```
- Accept only `HIGH` or `GOOD` confidence mappings from ZOOMA
- Always verify returned `semanticTags` in OLS and confirm the ontology is allowed by `TERMS.tsv`
- Use ZOOMA mainly for disease, phenotype, treatment, or other curator-style phrases backed by prior curation

Field defaults:
- `organism`, `cell line` → lexical first, fallback methods rarely needed
- `organism part`, `cell type`, `treatment` → lexical first, embeddings/ZOOMA only if lexical is weak
- `disease`, `phenotype` → lexical first, embeddings and ZOOMA are useful fallbacks

### 4.4 Verify the term is from the CORRECT ontology
Read TERMS.tsv `values` field for the column to determine which ontology(ies) to search:
- organism → NCBITaxon
- organism part → UBERON (primary), BTO (fallback)
- disease → MONDO (primary), EFO, DOID
- cell type → CL (primary), BTO, CLO
- cell line → CLO, BTO, EFO (+ Cellosaurus for accession)
- instrument → MS, PRIDE
- modifications → UNIMOD
- biosample accession number → exact BioSample accession from ENA/BioSamples only; do not infer from fuzzy search alone

### 4.5 Cell Line Lookup (if using cell-lines template)

For any `characteristics[cell line]` column, prefer the dedicated
`/sdrf:cellline` workflow or the live Cellosaurus service rather than a bundled
full-database script. The skill owns the decision rules; tools are only helpers.

Use this order:

1. `/sdrf:cellline <name or CVCL_XXXX>` for the full translation workflow
2. `python -m tools cellline lookup <name>` for the curated offline helper
3. https://www.cellosaurus.org/search when you need manual confirmation

The goal is to recover:
- `characteristics[cellosaurus accession]` → CVCL_XXXX (e.g., CVCL_0030)
- `characteristics[cellosaurus name]` → official name (e.g., HeLa)
- `characteristics[organism]`
- `characteristics[organism part]`
- `characteristics[disease]`
- `characteristics[cell type]`
- `characteristics[age]`, `characteristics[sex]`, `characteristics[ancestry category]`

Any CLO, BTO, EFO, MONDO, UBERON, CL, or NCBITaxon accession written into the
SDRF must still be verified via OLS before finalizing the row.

For organisms, prefer the current NCBITaxon label over legacy synonyms when validation fails on an older name.
Crosslinking cleanup examples that should be normalized before final validation:
- `chaetomium thermophilum` → `thermochaetoides thermophila`
- `chlorobium tepidum` → `chlorobaculum tepidum`
- `canis familiaris` → `canis lupus familiaris`
- `deinococcus radiodurans r1` → `deinococcus radiodurans`

For crosslinking-specific assay cleanup, use explicit file-name evidence when the SDRF still says `NT=unknown crosslinker;AC=XLMOD:00000`. Safe examples seen in sandbox cleanup:
- file names containing `DSSO` → `NT=DSSO;AC=XLMOD:02126;CL=yes;TA=K,S,T,Y,nterm;MH=54.01;ML=85.98`
- file names containing `DSS` → `NT=DSS;AC=XLMOD:02001`
- file names containing `BS3` → `NT=BS3;AC=XLMOD:02000`
- file names containing `DSBU` → `NT=DSBU;AC=XLMOD:02120` (XLMOD's preferred label is `BuUrBu`)
- file names containing `iQPIR`, `BDP`, or `d8BDP` → `NT=PIR;AC=XLMOD:02237`
  (the BDP-NHP reagent itself is `XLMOD:02011`)

> **Verify every XLMOD accession against OLS before writing it.** Neighbouring
> XLMOD ids are unrelated reagents, so a wrong accession is validator-clean and
> silently corrupts the annotation. Confirm with:
> `curl -s "https://www.ebi.ac.uk/ols4/api/search?q=XLMOD:02126&ontology=xlmod&fieldList=obo_id,label"`

**`TurboID` is not a cross-linker — do not map it to `comment[cross-linker]`.**
It is a promiscuous biotin ligase used for proximity-dependent labelling
(BioID family), not a chemical cross-linking reagent, and XLMOD has no term for
it. Proximity-labelling experiments are not XL-MS: annotate the biotin
enrichment via `characteristics[enrichment process]` /
`comment[crosslink enrichment method]` and do not apply the `crosslinking`
template on the strength of a `TurboID` filename token alone.

After recovering a known cross-linker, backfill `characteristics[crosslink distance]` when the template guidance is explicit:
- `BS3` / `DSS` → `30 Å`
- `DSSO` → `26.4 Å`
- `EDC` → `11.4 Å`
- `formaldehyde` → `2 Å`
- `DSBU` / `DSBSO` → `26.4 Å`
- `SDA` / `sulfo-SDA` → `18 Å`

For `comment[crosslink enrichment method]`, use explicit separation tokens from `comment[data file]` when the field is still missing:
- `SCX` → `strong cation exchange chromatography`
- `SEC` → `size exclusion chromatography`
- `FAIMS` → `FAIMS`
- dataset title containing `streptavidin pull-down` → `streptavidin pull-down`
- dataset title containing `IMAC-enrichable` → `immobilized metal affinity chromatography`
- dataset title containing `CuAAC-enrichable` → `CuAAC enrichment`

When one of those enrichment-method values is recovered and `characteristics[enrichment process]` is still missing, backfill `enrichment of cross-linked peptides`.

### 4.6 Check specificity
- "cancer" → too generic, use "breast carcinoma" or specific subtype
- "tissue" → too generic, use "liver" or "temporal cortex"
- "cell" → too generic, use "T cell" or "epithelial cell"
- Use getChildren() to see if there's a more specific child term
- If embeddings or ZOOMA suggest a child term that is more specific than the paper text supports, prefer the broader lexical term and note the ambiguity

### 4.7 Use reserved words correctly
- `not available` — information exists but was not provided
- `not applicable` — property doesn't apply to this sample
- `normal` — healthy control (for disease column, use with PATO:0000461)
- NEVER use "N/A", "NA", "unknown", "none"
- Check TERMS.tsv `allow_not_available`, `allow_not_applicable`, `allow_pooled` for each column

## Step 5: Fill Technical Metadata

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

| Search engine | Deposited file | Where the modifications are |
|---|---|---|
| Proteome Discoverer | `.msf`, `.pdStudy`, `.pdResult` (SQLite) | `Workflows` table → processing-node XML |
| MaxQuant | `parameters.txt`, `mqpar.xml` | `Fixed modifications` / `Variable modifications` |
| FragPipe / MSFragger | `fragger.params` | `table.fix-mods` / `table.var-mods` |
| DIA-NN | `report.log.txt` / logged command line | `--fixed-mod`, `--var-mod` (`--unimod4` = fixed Carbamidomethyl) |
| Spectronaut / SpectroMine | `.psar`, exported settings (UTF-16 strings) | modification list in the settings block |

**Proteome Discoverer `.msf` — read it, never download it.** `.msf`/`.pdResult` are SQLite
databases and routinely multi-GB (10.5 GB in the case below). Read them with HTTP
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
Run /sdrf:techrefine PXD###### to verify instrument, tolerances, modifications,
and DDA/DIA classification directly from the raw MS files.
```
techsdrf can detect discrepancies between what's declared in the paper/PRIDE and
what's actually in the raw data — especially for instrument model specificity,
mass tolerances, and undeclared or incorrect modifications.

**Bruker timsTOF / diaPASEF — the DIA windows are readable without any of that.**
`analysis.tdf` inside a `.d` archive is a SQLite database, so one member of the ZIP
can be range-fetched (14.7 MB rather than a 2.5 GB download) and read directly:
```bash
python -m tools bruker-dia "<url of the .d.zip>"
```
It reports the isolation windows, m/z coverage and CE ramp. Fill
`comment[isolation window width]` from it and **only** from it: diaPASEF windows are
variable-width, the column is a single scalar, and deriving one from the manuscript
("15 windows spanning 400–1000" → 40) yields a width matching no actual window while
passing both the regex and `parse_sdrf`. When the widths vary, the honest value is
`not available` with the measured table in the report — see `/sdrf:techrefine`.

## Step 6: Map Files to Samples

- Get file names from Step 1.2 (PRIDE file list)
- Each raw file → 1 row (label-free) or N rows (N = label channels for TMT/SILAC)
- Match files to samples using naming patterns from the paper or PRIDE description
- Set `comment[fraction identifier]` from file naming patterns (1 if not fractionated)
- Set `comment[technical replicate]` starting from 1

**Row count formula:**
```text
Total rows = samples × fractions × label_channels × technical_replicates
```

### 6.1 Multiplexed: exhaust every source of the channel→sample map before BLOCKING
For TMT / TMTpro / plexDIA / dimethyl, each of the N rows per file needs a sample
identity, and inventing one is the worst failure this skill can produce. But a
missing map inside PRIDE is **not** proof that no map exists — for several
SCoPE2-lineage studies the layout files are deposited *outside* PRIDE entirely.
Work the ladder in order, and record in the report which rungs you checked:

1. **The paper + its supplementary** — a per-channel table, often Table S1.
2. **Deposited PRIDE files** (`files/all`) — a sample sheet, or per-channel sample
   names in the result tables. Beware the defaults that look like a map and are
   not: Proteome Discoverer writes every channel as `"Sample, n/a"` (and
   `StudyInformation.txt` as a bare `"Sample"` with empty groups), SpectroMine
   likewise. A generic label in all channels of all files means **no map**.
3. **Europe PMC supplementary** —
   `https://www.ebi.ac.uk/europepmc/webservices/rest/<PMCID>/supplementaryFiles`.
4. **External repositories cited in the Data Availability / Code Availability
   statement** (Step 1.4) — the rung most often skipped:

| Repository | Where to look |
|---|---|
| Zenodo | `https://zenodo.org/api/records/<record_id>` → `files[].links.self` |
| figshare | `https://api.figshare.com/v2/articles/<article_id>` |
| OSF | `https://api.osf.io/v2/nodes/<node_id>/files/` |
| Dryad | `https://datadryad.org/api/v2/datasets/doi%3A<encoded DOI>` |
| GitHub | the analysis repo — `annotation.csv`, layout/design files, the SCeptre/SCoPE2 config |

   Look for layout and sort files by name: `label_layout`, `sort_layout`,
   `sample_layout`, `file_sample_mapping`, `annotation.csv`, FACS exports, or a
   collated result object (`.h5ad`, `.rds`).

5. **Cross-validate what you reconstruct.** Rebuild the (file × channel) → sample
   map deterministically from the layout files, then check it against an
   independent artifact — the collated `.h5ad`/result matrix's cell identifiers,
   or the FACS export's per-cell records. Report the discrepancy count; a
   reconstruction you cannot cross-check is a hypothesis, not a map.

Layouts can **flip between runs** — never assume one layout covers every file.
Only after all five rungs are exhausted is the dataset BLOCKED; say in the report
which sources you checked and what each returned, so the block is auditable
rather than a shrug.

> **Worked example (PXD053053, TMTpro-16).** PRIDE had no usable map — the
> deposited PD `StudyInformation.txt` marked all 16 channels of all 96 files with
> the generic default, and the supplementary `mmc1.xlsx` was a generic-labelled
> abundance matrix. The real map was in the paper's **Zenodo deposit (record
> 12615623)**, cited in Data Availability: SCeptre `label_layout` / `sort_layout` /
> `sample_layout` / `file_sample_mapping`, plus `compiled_FACS_data.txt` (all 1152
> sorted cells with hypoxia time point and FUCCI phase) and
> `scMS_filtered_data.h5ad`. Reconstructed from the layout files and cross-checked
> against the h5ad QC cells: **0 discrepancies**, 1344 annotatable rows instead of
> a false BLOCK. PXD040455's map was likewise in a published Table S1, not in PRIDE.

## Step 7: Set Factor Values

1. Identify what is being compared (disease vs control? treatment vs untreated?)
2. Create `factor value[<variable>]` column (e.g., `factor value[disease]`)
3. Copy values from the corresponding characteristics column
4. If multiple factors → create multiple factor value columns

## Step 8: Add SDRF Metadata

- `comment[sdrf version]` → read latest version from `spec/sdrf-proteomics/sdrf-templates/templates.yaml`
- `comment[sdrf template]` → one column per template: `NT={template_name};VV=v{version}` (versions from templates.yaml)
- `comment[sdrf annotation tool]` → `manual curation` (or tool name if applicable)

## Step 9: Validate with sdrf-pipelines

Before presenting the SDRF to the user, **always** run programmatic validation
with `sdrf-pipelines`. This catches errors that manual review misses.

### 9.1 Update spec to latest version
```bash
git submodule update --remote --recursive
```

### 9.2 Save the SDRF to a temporary file
Write the completed SDRF to a `.sdrf.tsv` file so `parse_sdrf` can validate it.

### 9.3 Run validation with detected templates
```bash
parse_sdrf validate-sdrf \
  --sdrf_file output.sdrf.tsv \
  --template <template1> \
  --template <template2>
```
Use the templates selected in Step 2. For example, a human DIA study:
```bash
parse_sdrf validate-sdrf \
  --sdrf_file output.sdrf.tsv \
  --template ms-proteomics \
  --template human \
  --template dia-acquisition
```

If `parse_sdrf` is not installed, tell the user:
```text
Install sdrf-pipelines to enable automatic validation:
  pip install sdrf-pipelines
```

### 9.4 Fix any validation errors
If `parse_sdrf` reports errors:
1. Fix each error in the SDRF
2. Re-run validation until it passes
3. Only proceed to Step 10 when validation is clean (or only warnings remain)

## Step 10: Present Results

Present the validated SDRF as a TSV code block and explain:
- Total rows and columns
- Sample groups and counts per group
- Templates applied (with version)
- File mapping summary
- Validation result (PASS / warnings)
- Any values marked as `not available` (ask user to fill)
- Any values you're uncertain about (flag for user review)

## Step 11: Recommend Community Contribution

If the annotation was for a **ProteomeXchange dataset** (PXD accession):

1. You already established in **Step 0.5** whether this PXD exists in the
   community repository — reuse that result rather than checking again, and do
   not fall back to `spec/annotated-projects/`, which can be stale.
2. Tell the user their annotation can be contributed to the community:

```text
Your SDRF annotation for {PXD} is ready!

The proteomics-sample-metadata community repository collects annotated SDRF files
for ProteomeXchange datasets. Contributing your annotation means:
  - Other researchers can reuse your metadata
  - Analysis pipelines (quantms) can automatically reprocess the dataset
  - The annotation becomes part of the PRIDE SDRF Explorer

Run /sdrf:contribute {PXD} to create a PR, or see the commands to do it manually.
```

3. If the PXD already existed, this is an **update**. The PR description must
   state what was wrong with the previous annotation and cite the evidence
   (deposited run list, PRIDE-registered organisms, the audit findings), so a
   reviewer can verify the claim instead of trusting it.

This step is a recommendation only — do not force the user to contribute.

## Important Rules

- NEVER re-annotate an already-annotated dataset silently — audit it, report, and
  let the user choose (Step 0.5). Overwriting requires an explicit `reannotate`
- NEVER fabricate ontology accessions — always search OLS
- NEVER guess file names — get them from PRIDE file list
- NEVER invent sample information not found in the paper or PRIDE metadata
- If information is missing from the paper, mark as `not available` and tell the user
- Always clearly distinguish: extracted from paper vs inferred vs assumed
- Present the SDRF as a TSV code block for easy copy-paste
- Multiple `comment[modification parameters]` columns are normal (one per mod)
- Multiple `comment[sdrf template]` columns are normal (one per template)

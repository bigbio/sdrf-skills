---
name: sdrf:metascreen
description: Use before sdrf:autoresearch when the user needs to screen or shortlist proteomics studies from PRIDE, MassIVE, ProteomeXchange accessions, or a manifest using detailed user-defined inclusion/exclusion criteria; extract study-level metadata from repository records and publications; and write an evidence-backed TSV for downstream annotation, review, or meta-analysis.
user-invocable: true
argument-hint: 'target="<all PRIDE ...|accessions:PXD...,MSV...|path/to/accessions.txt|path/to/manifest.tsv>" [criteria="<md|txt|inline>"] [extract="<cols|txt|md>"] [output="results.tsv"]'
---

# SDRF Meta-Analysis Screening Protocol

You are screening proteomics datasets before annotation or autoresearch.
Your job is to resolve a candidate study set, read repository metadata and the
associated publication for each candidate, apply the user's inclusion criteria,
extract requested study-level metadata, and write one TSV row per accession.

Do not guess. Use the MCP tools to verify every field.

This skill is complementary to `sdrf:autoresearch`: run it first when the user
needs a more precise, publication-aware study screen before deciding which
datasets should enter annotation. This skill produces a curation TSV; it does
not create, validate, fix, or improve SDRF files.

## Step 1: Parse the Request

Normalize into these fields:

### `target`
What dataset set to screen. Accepted forms:

- `accessions:PXD001234,MSV000078958` — use the comma- or whitespace-separated
  accession list directly. Do not put file paths after `accessions:`.
- Any file path (`.txt`, `.tsv`, `.csv`) — resolve automatically by extension:
  - `.txt` — one accession per line, strip whitespace, skip blank lines
  - `.tsv` / `.csv` — read the first available accession column from:
    `id`, `accession`, `project_accession`, `project`, or the first column
- `all PRIDE <category> datasets` — use PRIDE MCP search to discover matching
  datasets. Examples:
  - `all PRIDE human gut metaproteomics datasets`
  - `all PRIDE crosslinking datasets`
  - `all PRIDE human plasma proteomics datasets`

If a manifest contains previous labels, scores, or notes, use only the accession
column unless the user explicitly asks to reuse those fields.

When `target` is a free-text PRIDE category, resolve it into a concrete accession
list using PRIDE MCP search before screening begins (see Step 2).

### `criteria`
Inclusion/exclusion rules. Accepted forms:
- Path to a `.md` or `.txt` file — read the file and use its contents as the rules
- Inline text — use directly as the rules
- Omitted — no filtering; label all records `include` and only extract columns

### `extract`
What fields to extract per record. Accepted forms:
- Comma-separated names: `"sex,age,region"`
- Path to a `.txt` file — one field name per line
- Path to a `.md` file — parse field names and any per-field extraction
  instructions from the file. If the file contains instructions for how to fill
  a field (format, source, yes/no semantics), follow those instructions exactly.
- Omitted — no extra fields beyond the required output columns

When `extract` and `criteria` point to the same `.md` file, parse both the
inclusion rules and the extraction instructions from it.

Always include `id`, `label`, `reason`, and `evidence` in the output, even if
they are not listed in `extract`. Append requested extraction columns after
those required columns.

### `output`
Path for the output TSV. Default: `metascreen_results.tsv`

---

State the resolved config before processing begins:
```
Target     : <resolved description>
Criteria   : <source or "none">
Extract    : <resolved column list>
Output     : <path>
```

## Step 2: Resolve the Target Set

### Fixed lists and manifests
For `accessions:...` and file paths, resolve directly into a working list. Keep
the original order. Preserve duplicate accessions only if the user explicitly
asks; otherwise deduplicate and report the number removed.

### PRIDE category discovery
For `all PRIDE <category> datasets`:

1. Translate the category into repository search terms. Use repository metadata
   from a few known examples only if needed to calibrate terminology.

2. Search PRIDE for matching projects. Use relevant keywords from the category
   description (sample type, organism, experiment type, etc.).

3. **Fast pre-filter using PRIDE metadata only** — before fetching any publications,
   discard obvious mismatches using structured PRIDE fields:
   - `organisms` — filter by species if the criteria specify one
   - `experimentTypes` — filter by acquisition mode (DDA, DIA) if specified
   - `quantificationMethods` — filter by quantification strategy if specified
   - `instruments` — filter by instrument family if specified

   This avoids spending publication-fetch calls on clear non-candidates.

4. Report the discovered and pre-filtered candidate list before publication
   screening:
   ```
   Discovered : N datasets matching "<category>"
   Pre-filtered: N remaining after PRIDE metadata check
   ```

## Step 3: Screen Each Candidate

Process each accession in the working list independently.

### 3.1 Fetch repository metadata

```text
Tool: get_project_details(project_accession="PXD######")
```

Read all fields. Pay close attention to free-text protocol fields —
they are often the highest-signal source for instrument, acquisition,
sample type, quantification, and study design information.

### 3.2 Fetch the publication

Use publication identifiers in the repository record first. If no identifier is
available, search by project title and authors.

```text
Tool: get_article_metadata(ids=["PMID:XXXXXXX"])
```

If the paper is open access, fetch the full text:

```text
Tool: get_pdf_by_unpaywall(identifiers=["doi:10.xxxx/xxxxx"])
```

Read the Methods section for any information relevant to the criteria and the
requested extract fields. Use repository protocols, the abstract, and title only
as fallback evidence when full text is unavailable.

If no open-access full text is available, do not infer missing eligibility
details from vague title or keyword matches. Use `uncertain` when the evidence is
not sufficient.

### 3.3 Apply the inclusion criteria

If `criteria` was provided:
- Apply each rule in order
- `include` — all required inclusion rules pass and no exclusion rule applies
- `exclude` — at least one exclusion rule clearly applies; record the decisive
  failed rule as `reason`
- `uncertain` — the study may be relevant, but repository metadata and available
  publication evidence are insufficient to decide; state what is missing

Be conservative: prefer `uncertain` over guessing when evidence is absent.

If `criteria` was omitted, label all records `include`.

Use only these lowercase labels: `include`, `exclude`, `uncertain`.

### 3.4 Extract the requested fields

For each field in the resolved `extract` list:
- If the `extract` source provided instructions for this field, follow them exactly
- Otherwise, infer the extraction approach from the field name and available evidence
- Use `unclear` if the value cannot be determined from PRIDE metadata or the publication
- Keep values short and analysis-ready. Do not paste long abstracts or methods text
  into metadata fields.

### 3.5 Print progress

After each accession:
```
[N/total] PXD###### → LABEL
```

## Step 4: Write the TSV

- First row: column headers, with `id` always first
- Required columns: `id`, `label`, `reason`, `evidence`
- One row per accession in the order processed
- Tab-separated, UTF-8
- Use `unclear` for any field that could not be determined
- In `evidence`, cite the evidence source briefly, e.g. `PRIDE protocol`,
  `paper methods`, `abstract`, or `title/keywords only`

Print a summary:
```
Saved N records to <output>
include:   N
exclude:   N
uncertain: N
```

## Step 5: Report unresolved records

List `uncertain` accessions and state specifically what evidence was missing.

## Example invocations

```text
# Discover from PRIDE and screen
/sdrf:metascreen target="all PRIDE human gut metaproteomics datasets" criteria="criteria/human_gut_metaproteomics.md" extract="criteria/human_gut_metaproteomics.md" output="results/human_gut_screen.tsv"

# Fixed accession list from a txt file
/sdrf:metascreen target="data/accessions.txt" criteria="criteria/eligibility.md" extract="instrument,acquisition,sex,age,region" output="results/screen.tsv"

# Inline accessions
/sdrf:metascreen target="accessions:PXD001234,MSV000078958" criteria="human fecal metaproteomics only; exclude animal-only studies" extract="organism,sample_type,instrument" output="results/screen.tsv"

# From a manifest TSV
/sdrf:metascreen target="data/candidates.tsv" criteria="criteria/eligibility.md" extract="criteria/extract_fields.txt" output="results/screen.tsv"
```

## Notes

- MSV (MassIVE) accessions: PRIDE MCP may return limited metadata; use the
  publication as the primary evidence source.
- Never fill a field with a value not supported by evidence. Use `unclear` instead.
- Process accessions sequentially — do not skip any.
- Do not run `sdrf:annotate`, `sdrf:validate`, `sdrf:fix`, or `sdrf:improve` here.
  Those belong to `sdrf:autoresearch`.

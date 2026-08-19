---
name: sdrf:metascreen
description: Use when the user needs to screen or shortlist proteomics studies from PRIDE, MassIVE, or ProteomeXchange accessions, or from a manifest, using detailed user-defined inclusion/exclusion criteria — run this before sdrf:autoresearch; extract study-level metadata from repository records and publications; and write an evidence-backed, resumable TSV for downstream annotation, review, or meta-analysis.
user-invocable: true
argument-hint: 'target="<all PRIDE|MassIVE ...|accessions:PXD...,MSV...|path/to/accessions.txt|path/to/manifest.tsv>" [criteria="<md|txt|inline>"] [extract="<cols|txt|md>"] [output="results.tsv"] [dig_passes=1]'
---

# SDRF Meta-Analysis Screening Protocol

You are screening datasets before annotation or autoresearch. Your job is to
resolve a candidate study set, read repository metadata and the associated
publication for each candidate, apply the user's inclusion criteria, extract
requested study-level metadata, and write one TSV row per accession.

Do not guess. Use the MCP tools to verify every field.

This skill is complementary to `sdrf:autoresearch`: run it first when the user
needs a more precise, publication-aware study screen before deciding which
datasets should enter annotation. This skill produces a curation TSV; it does
not create, validate, fix, or improve SDRF files.

**The criteria and the extract fields come from the user, not from this file.**
Nothing here is specific to any one research question — the PRIDE fields named
in Step 2 are a worked example of "pre-filter on whatever structured fields the
criteria actually constrain", not a fixed list.

## Step 1: Parse the Request

Normalize into these fields:

### `target`
What dataset set to screen. Accepted forms:

- `accessions:PXD001234,MSV000078958` — use the comma- or whitespace-separated
  accession list directly. Do not put file paths after `accessions:`.
  Both `PXD…` and `MSV…` are supported; `get_project_details` routes to the right
  repository on its own, so no per-accession branching is needed.
- Any file path (`.txt`, `.tsv`, `.csv`) — resolve automatically by extension:
  - `.txt` — one accession per line, strip whitespace, skip blank lines
  - `.tsv` / `.csv` — read the first available accession column from:
    `id`, `accession`, `project_accession`, `project`, or the first column
- `all <category> datasets` — use `search_projects` to discover matching
  datasets. Examples:
  - `all PRIDE human gut metaproteomics datasets`
  - `all crosslinking datasets`
  - `all human plasma proteomics datasets`

  `search_projects` covers **PRIDE and MassIVE together** by default. A
  repository name inside the category phrase ("all PRIDE …") is ordinary habit,
  not a scoping instruction — search both. Pass `repository="pride"` or
  `"massive"` only when the user is unambiguously scoping to one, e.g. "PRIDE
  only", "just MassIVE datasets", "skip MassIVE" — phrasing that names the
  repository *as an exclusion*, not just in the category sentence.

If a manifest contains previous labels, scores, or notes, use only the accession
column unless the user explicitly asks to reuse those fields.

When `target` is a free-text category, resolve it into a concrete accession
list before screening begins (see Step 2).

### `criteria`
Inclusion/exclusion rules. Accepted forms:
- Path to a `.md` or `.txt` file — read the file and use its contents as the rules
- Inline text — use directly as the rules
- Omitted — no filtering; label all records `include` and only extract columns

Number the rules as you read them (rule 1, rule 2, …), in the order they appear.
Those numbers are what `failed_criterion` reports, so they must stay stable for
the whole run. If the criteria file already numbers its rules, reuse its numbers.

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

Always include `id`, `repository`, `label`, `reason`, `failed_criterion`, and
`evidence` in the output, even if they are not listed in `extract`. Append
requested extraction columns after those required columns. **Discard any
`extract` name that collides
with a required column** (case-insensitive) — never emit a duplicate header — and
report each name dropped.

### `output`
Path for the output TSV. Default: `metascreen_results.tsv`

### `dig_passes`
Integer, default `1`. How many extra evidence-gathering rounds (3.5) to spend
on an accession that would otherwise land on `uncertain` or an `unclear`
extract field, before finalizing the row. `0` disables the extra round —
finalize on the first pass, same as always taking the first answer. Negative
values are invalid, treat as `0`. Each round costs a handful of extra tool
calls per accession that needs it, so it multiplies across a large target set
— if the user asks for more than `5`, confirm they want that before running
rather than silently burning calls on a typo.

---

State the resolved config before processing begins:
```text
Target     : <resolved description>
Criteria   : <source or "none">
Extract    : <resolved column list>
Output     : <path>
Dig passes : <N>
Resuming   : <N already screened | fresh run>
```

## Step 2: Resolve the Target Set

### Fixed lists and manifests
For `accessions:...` and file paths, resolve directly into a working list. Keep
the original order. Preserve duplicate accessions only if the user explicitly
asks; otherwise deduplicate and report the number removed.

### Category discovery
For `all <category> datasets`:

1. **Break the category into SHORT keywords and sweep them.** PRIDE ANDs the
   terms in a keyword and then RANKS rather than filters, so a whole category
   sentence collapses recall — measured: `metaproteomics` returns 100+ hits,
   `human gut metaproteomics` returns 2. And no single term covers a field:
   `nanoPOTS` (11) and `proteoCHIP` (11) union to 22 single-cell datasets with
   zero overlap, and neither term is returned by `single-cell proteomics`.

```text
Tool: search_extensive(keywords=["metaproteomics", "gut microbiome proteomics", ...])
```

   `search_extensive` pages every keyword to exhaustion, unions and dedupes on
   `all_accessions`, and reports `per_keyword.new` — what each keyword
   contributed that no earlier one had. A keyword with `new: 0` was redundant
   for this sweep; put the whole `per_keyword` block in the run log, since it is
   the evidence that the sweep was wide enough.

   Use `search_projects` for a single probe or a manual page walk:

```text
Tool: search_projects(keyword="metaproteomics", page_size=100, page=0)
```

2. **Never report a truncated sweep as complete.** Exhaustion is proven ONLY by
   a page shorter than `page_size`. `search_extensive` enforces that: an empty
   page after a full one is ambiguous (PRIDE has historically capped a bare
   keyword and served an empty next page, indistinguishable from the end), so it
   retries partitioned by submission year and reports whatever is still
   unresolved in `truncated`.
   - `truncated` non-empty → the union is a **floor, not the result set**. Say so
     in the run log and in the final report.
   - `errors` non-empty → that page was **lost, not empty**. Retry it, and if it
     still fails, log it rather than reporting the screen as complete.
   If you page manually with `search_projects`, apply the same rule by hand.

3. **Fast pre-filter on the structured fields the criteria constrain** — before
   fetching any publication, discard obvious mismatches. `search_projects`
   returns these on every hit, so this costs no extra calls:

   | Field | Use it to filter on |
   |---|---|
   | `organism` | species |
   | `organism_parts` | tissue / sample type |
   | `instruments` | instrument model or family |
   | `experiment_types` | acquisition mode, e.g. `Data-dependent acquisition` |
   | `quantification_methods` | labelling strategy, e.g. `TIC`, `TMT` |
   | `keywords` | submitter-supplied topic terms |

   Filter only on fields the criteria actually constrain — skip the rest. If the
   criteria constrain something with no structured field, that check belongs in
   Step 3, not here.

   These fields are submitter-supplied and often **empty**. An empty field is not
   a failed check: never exclude on a missing value, carry the candidate forward
   and decide from the publication in Step 3.

   **How much pre-filtering you actually get depends on the repository.** Measured
   over 100 datasets each:

   | Field | PRIDE | MassIVE |
   |---|---|---|
   | `instruments` | 100% | 3% |
   | `experiment_types` (DDA/DIA) | 100% | never published |
   | `quantification_methods` | 14% | never published |
   | `organism` | high | 16% |

   So: instrument and acquisition can be pre-filtered in PRIDE, but **labelling
   strategy almost never can, in either repository**, and for MassIVE the
   structured pre-filter barely applies at all. Expect nearly every MassIVE
   candidate to reach Step 3 and be decided from the publication. That is the
   correct outcome — do not compensate by excluding MassIVE records for having
   thin metadata, and do not treat a MassIVE hit as lower quality because its
   fields are empty.

   **Match these values exactly, never by substring.** `"Data-independent
   acquisition"` contains the substring `"dependent"`, so a substring test for
   DDA silently admits every DIA study — an inclusion error that survives to the
   final table because nothing downstream re-checks it. Compare whole values.

4. Report the counts — this is the title/abstract stage of the screen, and its
   numbers belong in the run log:
   ```text
   Discovered  : N unique datasets across K keyword searches
   Pre-filtered: N remaining after structured-field check (M dropped)
   ```

## Step 3: Screen Each Candidate

Process each accession in the working list independently.

### 3.1 Fetch repository metadata

```text
Tool: get_project_details(project_accession="PXDXXXXXX")
```

Works for `PXD…` and `MSV…` alike. The tool resolves MSV accessions at MassIVE,
and falls back to MassIVE for PXD accessions PRIDE does not hold — MassIVE-hosted
ProteomeXchange datasets 404 in PRIDE (e.g. `PXD003626`), so a PXD is **not**
evidence the record is in PRIDE. Each result reports its `repository`, and
`all_accessions` carries both identifiers when a dataset has an MSV and a PXD.

Record the `repository` value in its own output column, and use `all_accessions`
to avoid screening the same study twice under its two accessions.

Read all fields the tool returns, not just the ones in the pre-filter table
above — that table is scoped to what `search_projects` exposes for Step 2's
purpose, and `get_project_details` returns more. Check the full result against
whatever the `extract` request actually asks for. Structured fields are the
most reliable; `sample_processing_protocol` and `data_processing_protocol` are
free text but are often the highest-signal source for anything the structured
fields omit. **MassIVE records have far fewer structured fields and no protocol
text** — for those, the publication is the only evidence source, so go straight
to 3.2.

If the tool returns an `error` key, the accession is in neither repository. Do
not retry and do not invent metadata — go to 3.2 and screen from the publication
alone; if there is no publication either, label `uncertain` and say the record
was unreachable.

### 3.2 Fetch the publication

`get_project_details` returns `publications`, a list of
`{pmid, pmcid, doi, is_open_access, reference}`. Route on those fields:

**Open access with a PMCID — prefer this path.** It returns section-scoped JATS
text and already defaults to methods/materials/sample-prep, excluding Results
and Discussion:

```text
Tool: get_full_text_article(pmc_ids=["PMC9174028"])
```

To pull one more section by name, or to check what sections exist:

```text
Tool: get_full_text_section(pmc_id="PMC9174028", section="methods")
```

**Otherwise, metadata only** (title, abstract, OA status):

```text
Tool: get_article_metadata(ids=["35695565"])
```

**Identifiers must be BARE.** `get_article_metadata` accepts a bare PMID
(`35695565`), a PMCID (`PMC9174028`), or a bare DOI (`10.1038/s41467-022-30310-x`).
A prefixed form such as `PMID:35695565` or `doi:10.1038/...` is **rejected** and
returns an error record, not an article — which then looks like missing evidence.
The same applies to `get_pdf_by_unpaywall(identifiers=["10.1038/s41467-022-30310-x"])`;
pass the bare DOI, never `doi:`-prefixed.

Fall back to `get_pdf_by_unpaywall` only when there is no PMCID full text and the
abstract is insufficient.

If the repository record carries no publication identifier, search by project
title and authors. If that fails, screen from repository metadata alone and say
so in `evidence`.

Read the Methods for anything relevant to the criteria and the requested extract
fields. Use repository protocols, abstract, and title only as fallback evidence.

If no full text is available, do not infer missing eligibility details from vague
title or keyword matches. Use `uncertain`.

### 3.3 Apply the inclusion criteria

If `criteria` was provided:
- Apply each rule in order, by its Step 1 number
- `include` — all required inclusion rules pass and no exclusion rule applies
- `exclude` — at least one exclusion rule clearly applies. Record the **first**
  failed rule's number in `failed_criterion` and its one-sentence decisive factor
  in `reason`. Stop at the first failure; do not evaluate the rest.
- `uncertain` — the study may be relevant, but repository metadata and available
  publication evidence are insufficient to decide. Put the number of the rule you
  could not settle in `failed_criterion` and state what evidence is missing in
  `reason`.

For `include`, leave `failed_criterion` empty.

Be conservative: prefer `uncertain` over guessing when evidence is absent.

If `criteria` was omitted, label all records `include`.

Use only these lowercase labels: `include`, `exclude`, `uncertain`.

`uncertain` means **needs a human** — it is not a soft include. Do not pass
`uncertain` rows to `sdrf:autoresearch`. Only `include` rows are cleared for
downstream annotation.

### 3.4 Extract the requested fields

For each field in the resolved `extract` list:
- If the `extract` source provided instructions for this field, follow them exactly
- Otherwise, infer the extraction approach from the field name and available evidence
- Use `unclear` if the value cannot be determined from repository metadata or the
  publication
- Keep values short and analysis-ready. Do not paste long abstracts or methods text
  into metadata fields.

Extract fields for `exclude` rows too when the evidence is already in hand — it
costs nothing and makes the exclusion tally analysable. Never fetch extra
publications just to fill fields on an excluded row.

### 3.4b Feasibility fields are not inclusion criteria

Some extract fields describe whether the study **can be used downstream**, not
whether it belongs in the set: whether a multiplexed study records which label
channel held which sample, whether per-sample metadata exists at row resolution,
whether the raw files are actually deposited. Two rules:

- **Never let a feasibility field move `label`.** A study that is squarely in
  scope but impossible to annotate is still `include` — demoting it to `exclude`
  or `uncertain` corrupts what those labels mean and hides it from the tally it
  belongs in. Record the blocker in its own column and let the caller filter.
- **Decide it from evidence already in hand.** These fields are cheap: the
  screen has already opened the repository record and, for multiplexed
  candidates, often the result tables. Do not spend extra fetches on them beyond
  `dig_passes`.

The tells are worth knowing because they *look* like data. For a
channel→sample map, Proteome Discoverer writes every channel as `"Sample, n/a"`
and `StudyInformation.txt` as a bare `"Sample"` with empty groups; SpectroMine
does the same. A generic placeholder repeated across all channels of all files
means **no map**, not a map you failed to read.

### 3.5 Dig deeper before settling for uncertain or unclear

Applies only when the row so far has `label: uncertain` or at least one
`unclear` extract field, and only when the label is not `exclude` — an
excluded row is already decided, and 3.4 already says not to spend extra
fetches filling its fields.

Spend up to `dig_passes` extra rounds per accession before finalizing. One
round means: go back and look harder at evidence you may have skimmed or
never explicitly requested, for example —
- Re-read the full repository record from 3.1, field by field, and the full
  `sample_processing_protocol` / `data_processing_protocol` text — don't skim
  past a field or a sentence because it looked like lab-protocol boilerplate.
- If 3.2 only ever fetched the default methods-filtered sections, call
  `get_full_text_article(pmc_ids=[pmcid], mode="toc")` to see the full section
  list, then `get_full_text_section` on any section name that could plausibly
  hold the missing evidence but didn't match the default keyword filter.
- If there is a DOI or PMID but no PMCID full text was tried yet, try
  `get_pdf_by_unpaywall` (3.2).

Then redo 3.3 and 3.4 with whatever new evidence turned up. After `dig_passes`
rounds (or immediately, if `dig_passes` is `0`), finalize the row as-is —
don't retry a source that has already been exhausted (e.g. a full-text fetch
that already returned an error), since that spends the budget without a
chance of new evidence.

### 3.6 Append the row and print progress

Append the row to the output file **now** (see Step 4) — do not accumulate rows
in memory until the end. Then print:
```text
[N/total] PXD###### → LABEL
```

## Step 4: Write the TSV

Write incrementally, one row per accession, as each is screened.

**On startup**, if the output file already exists and has a header:
- read its `id` column, skip those accessions, and append to the file
- report the count as `Resuming` in the Step 1 config block
- if the existing header does not match the header this run would write, stop and
  ask the user rather than appending mismatched rows

Otherwise write the header first, then append.

Format rules:
- First row: column headers, with `id` always first
- Required columns, in order: `id`, `repository`, `label`, `reason`,
  `failed_criterion`, `evidence`
- `id` is the accession as the user supplied it (or the primary accession from
  discovery); `repository` is `PRIDE`, `MassIVE`, or `unclear` if neither held it
- Tab-separated, UTF-8, one row per accession
- **Sanitize every value**: replace tab, CR, and LF with a single space before
  writing. Free-text `reason`, `evidence`, and extracted fields come from paper
  methods and routinely contain them — one stray tab silently shifts every column
  in that row and nothing errors.
- Use `unclear` for any extract field that could not be determined
- In `evidence`, cite the source briefly: `PRIDE structured fields`,
  `PRIDE protocol`, `paper methods`, `abstract`, or `title/keywords only`

Print a summary:
```text
Saved N records to <output>
include:   N
exclude:   N
uncertain: N
```

## Step 5: Write the run log

Write a sidecar `<output>.log` (plain text, next to the TSV) so the screen is
reproducible and can be reported as a PRISMA-style flow:

```text
run_date        : <ISO 8601>
target          : <verbatim target argument>
criteria_source : <path or "inline">
criteria_sha256 : <sha256 of the criteria file, or "n/a" for inline>
dig_passes      : <configured N>  (recovered: N rows where digging changed
                  an uncertain label or unclear field)
repositories    : <PRIDE+MassIVE | PRIDE | MassIVE>
keywords        : <the keyword searches issued, if discovery was used>
discovered      : N  (PRIDE N, MassIVE N)
pre_filtered    : N  (M dropped: <field=value counts>)
screened        : N
include         : N  (PRIDE N, MassIVE N)
exclude         : N
uncertain       : N
lost_pages      : <none | the search pages that errored and stayed incomplete>
truncated       : <none | the search_extensive `truncated` entries — for each one
                  listed, coverage is a floor, not a complete set>
per_keyword     : <the search_extensive per_keyword block: hits / new per keyword>
exclusions_by_criterion:
  rule 2 (Orbitrap instrument) : N
  rule 3 (DDA acquisition)     : N
```

Build `exclusions_by_criterion` by grouping the `failed_criterion` column. This
is why that column holds a rule number and not prose.

## Step 6: Report unresolved records

List `uncertain` accessions and state specifically what evidence was missing for
each, so a human knows what to go find.

## Example invocations

```text
# Discover across PRIDE + MassIVE and screen
/sdrf:metascreen target="all PRIDE human gut metaproteomics datasets" criteria="criteria/human_gut_metaproteomics.md" extract="criteria/human_gut_metaproteomics.md" output="results/human_gut_screen.tsv"

# Fixed accession list from a txt file
/sdrf:metascreen target="data/accessions.txt" criteria="criteria/eligibility.md" extract="instrument,acquisition,sex,age,region" output="results/screen.tsv"

# Mixed PRIDE + MassIVE accessions
/sdrf:metascreen target="accessions:PXD005969,MSV000078958" criteria="human fecal metaproteomics only; exclude animal-only studies" extract="organism,sample_type,instrument" output="results/screen.tsv"

# From a manifest TSV
/sdrf:metascreen target="data/candidates.tsv" criteria="criteria/eligibility.md" extract="criteria/extract_fields.txt" output="results/screen.tsv"
```

## Notes

- **MassIVE is fully in scope.** `search_projects` and `get_project_details` both
  cover it, and `sdrf:autoresearch` can annotate what this screen includes.
  MassIVE records are metadata-poor, not second-class: screen them from the
  publication and include them on the same criteria as PRIDE records.
- A MassIVE publication usually still resolves to an open-access PMCID, so the
  `get_full_text_article` path in 3.2 works there too — it is the main way a
  MassIVE candidate gets decided.
- A dataset can hold both an `MSV…` and a `PXD…` accession — see 3.1 for
  deduplicating on `all_accessions`.
- Never fill a field with a value not supported by evidence. Use `unclear`.
- Process every unresolved accession — do not skip any. (Accessions already
  present in an existing output file are resumed, not skipped.)
- `unclear` (extract fields) and `uncertain` (label) are not interchangeable, and
  neither is an SDRF reserved word. This skill emits a curation TSV, not an SDRF.
  In particular, never write `not applicable` or `not available` in this TSV, even
  for a field whose question genuinely does not arise for a row — give that case
  its own vocabulary word (see `channel_map` in
  `criteria/single_cell_proteomics.md`, which uses `label free`).
- Do not run `sdrf:annotate`, `sdrf:validate`, `sdrf:fix`, or `sdrf:review` here.
  Those belong to `sdrf:autoresearch`.

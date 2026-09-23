---
name: sdrf-campaign
description: Use when the user wants to run an SDRF annotation campaign over a class of studies rather than one dataset — screen or shortlist proteomics studies from PRIDE, MassIVE or ProteomeXchange against user-defined inclusion criteria and write an evidence-backed resumable TSV, then annotate the included datasets as an autonomous retained-improvement loop. Covers both halves: use stop_after="screen" for screening only, or target a manifest to skip straight to annotation.
user-invocable: true
argument-hint: 'target="<all <category>|accessions:PXD...,MSV...|path/to/list.txt|manifest.tsv>" [criteria="<md|txt|inline>"] [extract="<cols|txt|md>"] [output="screen.tsv"] [dig_passes=1] [stop_after="screen|annotate"] [profile="<preset>"] [objective="<metric>"] [focus_fields="<f1,f2>"] [stop="<rule>"] [write="<sandbox|branch|report-only>"]'
---

# SDRF Campaign Protocol

A campaign has two halves and they are one pipeline: **screen** a candidate set
down to the studies that belong, then **annotate** those studies in a retained-
improvement loop. The screen's TSV is the loop's input.

Run both by default. Use `stop_after="screen"` when the user only wants a
shortlist, and point `target` at an existing manifest to skip straight to the
loop.

Do not guess. Verify every field against a source.

**The criteria and the extract fields come from the user, not from this file.**
Nothing here is specific to any one research question — the PRIDE fields named
in Phase 2 are a worked example of "pre-filter on whatever structured fields the
criteria actually constrain", not a fixed list.

---

# Evidence precedence

This governs both halves and overrides any instinct to prefer structured data
because it is easier to parse:

```
manuscript  >  deposit metadata (PRIDE/MassIVE structured fields + protocols)
```

A value the paper states is never overridden by a repository field. Repository
`instruments`, `organisms`, `diseases` and `organismParts` are submitter-chosen
dropdowns: frequently empty, sometimes wrong, and occasionally not even the
right kind of term. Measured failures from trusting them first:

- `instruments` yielding `liquid chromatography separation` and `co-eluting
  ion` — neither is a mass spectrometer, both are valid MS terms, and both
  passed ontology validation
- a deposit registering one organism while the title and methods describe the
  organism actually analysed
- submitters registering an approximate cell line, or none, where the
  manuscript names the one used

Within the manuscript, Methods outrank Abstract and Results. Within the deposit,
`sampleProcessingProtocol` / `dataProcessingProtocol` free text outranks the
structured fields.

For technical metadata only, deposited search outputs (MaxQuant `parameters.txt`,
FragPipe `fragger.params`, PD `.msf`, DIA-NN logs) outrank the manuscript, since
they record what the search actually did.

---

# Phase 1: Parse the request

Normalize into these fields. State the resolved config before any work begins.

## Screening arguments

### `target`
- `accessions:PXD001234,MSV000078958` — comma/whitespace-separated list. Do not
  put file paths after `accessions:`. `get_project_details` routes PXD and MSV
  to the right repository on its own.
- Any file path (`.txt`, `.tsv`, `.csv`) — resolve by extension:
  - `.txt` — one accession per line, strip whitespace, skip blanks
  - `.tsv`/`.csv` — first available accession column from `id`, `accession`,
    `project_accession`, `project`, or the first column
- `all <category> datasets` — discover via search (Phase 2).

`search_projects` covers **PRIDE and MassIVE together**. A repository name inside
the category phrase ("all PRIDE …") is ordinary habit, not a scoping
instruction — search both. Pass `repository="pride"` or `"massive"` only when the
user names it *as an exclusion*: "PRIDE only", "skip MassIVE".

If a manifest carries previous labels or scores, use only the accession column
unless the user asks to reuse them.

### `criteria`
Path to `.md`/`.txt`, inline text, or omitted (no filtering; label all `include`).

Number the rules as you read them, in order. Those numbers are what
`failed_criterion` reports, so they must stay stable for the whole run. If the
file already numbers its rules, reuse its numbers.

### `extract`
Comma-separated names, a `.txt` (one per line), or a `.md` (field names plus
per-field extraction instructions — follow those instructions exactly). When
`extract` and `criteria` are the same `.md`, parse both from it.

Always include `id`, `repository`, `label`, `reason`, `failed_criterion`,
`evidence`. Append requested columns after those. **Discard any `extract` name
colliding with a required column** (case-insensitive) and report each drop.

### `output`
Screening TSV path. Default `sdrf_campaign_screen.tsv`.

### `dig_passes`
Integer, default `1`. Extra evidence rounds (Phase 3.5) spent on a row heading
for `uncertain` or an `unclear` field. `0` finalizes on the first pass. Negative
is invalid; treat as `0`. Each round costs several tool calls per affected
accession and multiplies across the set — if the user asks for more than `5`,
confirm rather than silently burning calls on a typo.

### `stop_after`
`screen` or `annotate` (default). `screen` writes the TSV and log, then stops.

## Annotation arguments

### `profile`
`general-proteomics` | `cell-line` | `crosslinking` | `clinical` |
`immunopeptidomics`. Biases which templates, columns and evidence sources matter.

### `objective`
There is one: **retained, evidence-backed improvement**. A round is retained only if the file
scores no lower on `sdrf-tools score`, validation does not regress, `sdrf-tools reconcile` adds no
finding, and every changed cell cites its evidence. The former presets
(`maximize_valid_field_coverage`, `minimize_unknowns`, ...) are gone: they rewarded turning an
honest `not available` into a guess, which is the failure the loop exists to prevent.

### `focus_fields`
Optional priority list, e.g. `cell line,disease,organism part,treatment`. The `profile` supplies a
default: `crosslinking` → cross-linker, enrichment method and process, distance, concentration,
reaction time, temperature, quenching reagent, collision energy; `cell-line` → cell line, cell type,
disease, organism part, treatment, sex, age; `clinical` → disease, developmental stage, sex, age,
individual, treatment. A focus says where to look hardest; it never says what to fill.

### `budget`
`<max rounds per dataset>,<max cost or tool calls per dataset>`; default `3,$3`. One annotation
of a large dataset costs about a dollar with the build workflow and a few dollars without it, so
the default allows three rounds. The loop stops on budget even mid-round and reports it.

### `stop`
`no_retained_gain_2_rounds` (default) | `budget` | `manual_only_left`. No coverage threshold:
coverage is not a goal, correctness is.

### `write`
`sandbox` | `branch` | `report-only`.

Infer anything unspecified conservatively and state the inference.

```text
Target      : <resolved description>
Criteria    : <source or "none">
Extract     : <resolved column list>
Output      : <path>
Dig passes  : <N>
Stop after  : <screen|annotate>
Profile     : <preset>      Focus     : <fields>
Budget      : <rounds,cost> Stop rule : <rule>
Write       : <mode>
Resuming    : <N already screened | fresh run>
```

---

# Phase 2: Resolve the target set

## Fixed lists and manifests
Resolve directly, keeping original order. Deduplicate and report the count
removed, unless the user asks to preserve duplicates.

## Category discovery

**1. Break the category into SHORT keywords and sweep them.** PRIDE ANDs the
terms in a keyword then RANKS rather than filters, so a whole category sentence
collapses recall — measured: `metaproteomics` returns 100+ hits, `human gut
metaproteomics` returns 2. And no single term covers a field: `nanoPOTS` (11)
and `proteoCHIP` (11) union to 22 single-cell datasets with zero overlap, and
neither is returned by `single-cell proteomics`.

```text
Tool: search_extensive(keywords=["metaproteomics", "gut microbiome proteomics", ...])
```

`search_extensive` pages every keyword to exhaustion, unions and dedupes on
`all_accessions`, and reports `per_keyword.new` — what each keyword contributed
that no earlier one had. A keyword with `new: 0` was redundant for this sweep.
Put the whole `per_keyword` block in the run log: it is the evidence the sweep
was wide enough.

Use `search_projects(keyword=..., page_size=100, page=0)` for a single probe or
a manual page walk.

**2. Never report a truncated sweep as complete.** Exhaustion is proven ONLY by
a page shorter than `page_size`. An empty page after a full one is ambiguous
(PRIDE has capped a bare keyword and served an empty next page, indistinguishable
from the end), so `search_extensive` retries partitioned by submission year and
reports what remains in `truncated`.
- `truncated` non-empty → the union is a **floor, not the result set**. Say so in
  the log and the final report.
- `errors` non-empty → that page was **lost, not empty**. Retry; if it still
  fails, log it rather than reporting the screen complete.

**3. Fast pre-filter on the structured fields the criteria constrain.** Before
fetching any publication, discard obvious mismatches — `search_projects` returns
these on every hit, so it costs no extra calls:

| Field | Filters on |
|---|---|
| `organism` | species |
| `organism_parts` | tissue / sample type |
| `instruments` | instrument model or family |
| `experiment_types` | acquisition mode |
| `quantification_methods` | labelling strategy |
| `keywords` | submitter topic terms |

Filter only on fields the criteria actually constrain. If the criteria constrain
something with no structured field, that check belongs in Phase 3.

These fields are submitter-supplied and often **empty**. An empty field is not a
failed check: never exclude on a missing value — carry the candidate forward and
decide from the publication.

**How much pre-filtering you get depends on the repository.** Measured over 100
datasets each:

| Field | PRIDE | MassIVE |
|---|---|---|
| `instruments` | 100% | 3% |
| `experiment_types` | 100% | never published |
| `quantification_methods` | 14% | never published |
| `organism` | high | 16% |

Instrument and acquisition pre-filter well in PRIDE; **labelling strategy almost
never does, in either repository**, and for MassIVE the structured pre-filter
barely applies. Expect nearly every MassIVE candidate to reach Phase 3 and be
decided from the publication. That is correct — do not compensate by excluding
MassIVE records for thin metadata.

**Match values exactly, never by substring.** `"Data-independent acquisition"`
contains `"dependent"`, so a substring test for DDA silently admits every DIA
study — an inclusion error that survives to the final table because nothing
downstream re-checks it.

**4. Report the counts** — this is the title/abstract stage of the screen:
```text
Discovered  : N unique datasets across K keyword searches
Pre-filtered: N remaining after structured-field check (M dropped)
```

---

# Phase 3: Screen each candidate

Process each accession independently.

## 3.1 Fetch repository metadata

```text
Tool: get_project_details(project_accession="PXDXXXXXX")
```

Works for `PXD…` and `MSV…`. Falls back to MassIVE for PXD accessions PRIDE does
not hold — MassIVE-hosted ProteomeXchange datasets 404 in PRIDE (e.g.
`PXD003626`), so a PXD is **not** evidence the record is in PRIDE. Each result
reports its `repository`; `all_accessions` carries both identifiers when a
dataset has an MSV and a PXD. Record `repository` in its own column and use
`all_accessions` to avoid screening one study twice.

Read every field returned, not just the pre-filter table above.
`sample_processing_protocol` and `data_processing_protocol` are free text but are
often the highest-signal source for anything the structured fields omit.
**MassIVE records have far fewer structured fields and no protocol text** — go
straight to 3.2 for those.

If the tool returns an `error` key, the accession is in neither repository. Do
not retry and do not invent metadata: screen from the publication alone, and if
there is none, label `uncertain` and say the record was unreachable.

## 3.2 Fetch the publication

`get_project_details` returns `publications` as
`{pmid, pmcid, doi, is_open_access, reference}`.

**Open access with a PMCID — prefer this.** Returns section-scoped JATS text,
defaulting to methods/materials/sample-prep and excluding Results/Discussion:

```text
Tool: get_full_text_article(pmc_ids=["PMC9174028"])
Tool: get_full_text_section(pmc_id="PMC9174028", section="methods")
```

**Otherwise metadata only:** `get_article_metadata(ids=["35695565"])`.

**Identifiers must be BARE.** A prefixed `PMID:35695565` or `doi:10.1038/...` is
rejected and returns an error record, not an article — which then looks like
missing evidence. Same for `get_pdf_by_unpaywall`.

**`is_open_access: false` means "try harder", not "abstract only".** Both PRIDE
and Europe PMC have reported gold-OA CC-BY papers as closed, and `fullTextXML`
sometimes 404s for papers that are in fact open. Before falling back to
abstract-only, exhaust: Unpaywall by DOI, the PMC HTML render, NCBI eutils, and
a Europe PMC free-text search on **the accession itself**.

If the record carries no publication identifier, search by title and authors. If
that fails, screen from repository metadata alone and say so in `evidence`.

A paper that merely *cites* an accession may only be reusing the data. Signals of
reuse: the accession appears in a data-availability list among many; the paper is
a benchmark, meta-analysis or reanalysis; it postdates the deposit by years.
Signals of origin: "data have been deposited"; organism, instrument and sample
counts match; contemporaneous with submission. A dataset attached to the wrong
paper silently corrupts every field derived from it.

If no full text is available, do not infer eligibility from vague title or
keyword matches. Use `uncertain`.

## 3.3 Apply the inclusion criteria

Apply each rule in order by its Phase 1 number:
- `include` — all inclusion rules pass, no exclusion rule applies
- `exclude` — an exclusion rule clearly applies. Record the **first** failed
  rule's number in `failed_criterion` and its one-sentence decisive factor in
  `reason`. Stop at the first failure.
- `uncertain` — may be relevant, but the evidence cannot decide. Put the
  unsettled rule number in `failed_criterion` and state what evidence is missing.

Only these lowercase labels: `include`, `exclude`, `uncertain`. Leave
`failed_criterion` empty for `include`. Prefer `uncertain` over guessing.

`uncertain` means **needs a human** — it is not a soft include. Only `include`
rows proceed to Phase 5.

## 3.4 Extract the requested fields

Follow per-field instructions when the `extract` source gave them; otherwise
infer from the field name and available evidence. Use `unclear` when the value
cannot be determined. Keep values short and analysis-ready — never paste
abstracts or methods text into a metadata field.

Extract fields for `exclude` rows when the evidence is already in hand; it costs
nothing and makes the exclusion tally analysable. Never fetch extra publications
to fill fields on an excluded row.

## 3.4b Feasibility fields are not inclusion criteria

Some fields describe whether a study **can be used downstream** — whether a
multiplexed study records which channel held which sample, whether per-sample
metadata exists at row resolution, whether raw files are deposited.

- **Never let a feasibility field move `label`.** A study squarely in scope but
  impossible to annotate is still `include`; demoting it corrupts what the labels
  mean and hides it from the tally it belongs in. Record the blocker in its own
  column and let the caller filter.
- **Decide it from evidence already in hand.** Do not spend extra fetches beyond
  `dig_passes`.

The tells look like data. For a channel→sample map, Proteome Discoverer writes
every channel as `"Sample, n/a"` and `StudyInformation.txt` as a bare `"Sample"`
with empty groups; SpectroMine does the same. A generic placeholder repeated
across all channels of all files means **no map**, not a map you failed to read.

## 3.5 Dig deeper before settling for uncertain or unclear

Applies only when the row has `label: uncertain` or an `unclear` field, and only
when the label is not `exclude`. Spend up to `dig_passes` rounds:

- Re-read the full repository record field by field, and the complete protocol
  text — do not skim past a sentence because it looked like boilerplate.
- If 3.2 only fetched default methods-filtered sections, call
  `get_full_text_article(pmc_ids=[pmcid], mode="toc")` for the section list, then
  `get_full_text_section` on any section that could hold the missing evidence.
- If there is a DOI or PMID but no PMCID full text was tried, try
  `get_pdf_by_unpaywall`.

Redo 3.3 and 3.4 with whatever turned up. Then finalize — do not retry a source
already exhausted (a full-text fetch that errored), which spends budget with no
chance of new evidence.

## 3.6 Append and report

Append the row **now** (Phase 4) — do not accumulate in memory. Then print:
```text
[N/total] PXD###### → LABEL
```

---

# Phase 4: Write the screening TSV and log

Write incrementally, one row per accession.

**On startup**, if the output exists with a header: read its `id` column, skip
those accessions, append, and report the count as `Resuming`. If the existing
header does not match what this run would write, stop and ask rather than
appending mismatched rows.

Format:
- First row headers, `id` always first
- Required columns in order: `id`, `repository`, `label`, `reason`,
  `failed_criterion`, `evidence`
- `repository` is `PRIDE`, `MassIVE`, or `unclear`
- Tab-separated, UTF-8
- **Sanitize every value**: replace tab, CR and LF with a single space before
  writing. Free text from paper methods routinely contains them, and one stray
  tab silently shifts every column in that row without erroring.
- `unclear` for any undetermined extract field
- In `evidence`, cite the source briefly: `PRIDE structured fields`,
  `PRIDE protocol`, `paper methods`, `abstract`, `title/keywords only`

```text
Saved N records to <output>
include:   N
exclude:   N
uncertain: N
```

Write a sidecar `<output>.log` so the screen is reproducible as a PRISMA-style
flow:

```text
run_date        : <ISO 8601>
target          : <verbatim target argument>
criteria_source : <path or "inline">
criteria_sha256 : <sha256 of the criteria file, or "n/a">
dig_passes      : <N>  (recovered: N rows where digging changed a label or field)
repositories    : <PRIDE+MassIVE | PRIDE | MassIVE>
keywords        : <the keyword searches issued>
discovered      : N  (PRIDE N, MassIVE N)
pre_filtered    : N  (M dropped: <field=value counts>)
screened        : N
include         : N  (PRIDE N, MassIVE N)
exclude         : N
uncertain       : N
lost_pages      : <none | pages that errored and stayed incomplete>
truncated       : <none | search_extensive `truncated` entries — coverage is a floor>
per_keyword     : <hits / new per keyword>
exclusions_by_criterion:
  rule 2 (Orbitrap instrument) : N
  rule 3 (DDA acquisition)     : N
```

Build `exclusions_by_criterion` by grouping `failed_criterion`. That is why the
column holds a rule number and not prose.

Then list every `uncertain` accession with what evidence was missing, so a human
knows what to go find.

**If `stop_after="screen"`, stop here.**

---

# Phase 5: The annotation loop

Operate on the `include` rows only.

## 5.1 What "better" means

Retained, evidence-backed improvement — nothing else. Measured by `sdrf-tools score`, gated by
validation (`parse_sdrf validate-sdrf`, `sdrf-tools structure`) and by `sdrf-tools reconcile`
against the deposit record. A change is retained only when all four hold:

1. the score does not drop and validation does not regress;
2. `reconcile` reports no new finding;
3. every changed cell cites where the value came from (manuscript section, supplementary table,
   deposited search output, run name);
4. the change is not a blank becoming a value without such a citation. `not available` is a valid
   result, and a wrong specific value is worse for reuse than an honest blank.

Demographics stay conservative: `characteristics[developmental stage]` may follow an unambiguous
cohort description; per-sample `age`, `sex` and `ethnicity` need an individual-level mapping.

## 5.2 Run the loop per dataset

1. **Discover evidence** — repository metadata, file list, manuscript from Europe PMC,
   supplementary tables for sample metadata, Methods and deposited search outputs for technical
   metadata. For exact file coverage prefer the complete endpoint:
   ```text
   GET https://www.ebi.ac.uk/pride/ws/archive/v3/projects/PXD######/files/all
   ```
   Paged listings truncate silently. If this returns `0` files for a valid PXD hosted by
   `PanoramaPublic`, `MassIVE`, `iProX` or `jPOST`, that is `archive endpoint empty for external
   repository`, not `no dataset` — keep the accession in play and note the limitation.
2. **First round: `/sdrf-skills:sdrf-annotate <PXD>`.** That workflow already does everything the
   loop used to call separately: the contract, `samples.tsv` + `technical.tsv`, `sdrf-tools build`,
   cell-line lookup, raw-file verification with `techsdrf`, validation (at most two rounds),
   `reconcile`, and — always — the fresh-context `sdrf-adversarial-review` with a hash-bound
   receipt (its Step 9.5). The result of round one is a reviewed file, or a report saying why not.
3. **Later rounds edit the tables, never the SDRF.** A refinement is a change to `samples.tsv` or
   `technical.tsv` followed by `sdrf-tools build`, validation and `reconcile`. Editing
   `output.sdrf.tsv` directly is the structure-breaking path the build step exists to prevent.
4. **Keep or discard** by 5.1. Record every discarded round and its reason.
5. **Re-review when something was retained.** A retained round changed the file, so its receipt is
   void: dispatch a new fresh-context `sdrf-adversarial-review` as annotate's Step 9.5 describes.
   Never ask a previous reviewer to reuse its verdict. If the platform cannot isolate a reviewer,
   say the gate is unavailable and do not mark the dataset done.

## 5.3 Repeat until the stop rule fires

- no retained improvement for two consecutive rounds (default), or
- the per-dataset budget is spent (rounds or cost), or
- what remains needs a human (scientific judgement the evidence does not contain).

Never loop to replace placeholders with guesses. Ten datasets left honestly incomplete beat one
polished by invention.

## 5.4 Refinement heuristics by evidence source

Ordered by the precedence rule at the top of this file.

**Sample metadata** — manuscript Methods; manuscript Results; supplementary
sample tables; figure and table captions; then the repository sample description.
A cell line, disease or tissue must be **named in the evidence** before it is
looked up in an ontology: a correct Cellosaurus lookup attached to a deposit
whose record never mentions that line is still a fabrication.

**Technical metadata** — deposited search outputs; raw-file analysis; manuscript
Methods; then repository protocols.

**File mapping and replicate logic** — the repository file list; SDRF row
structure; file names.

## 5.5 Resource guard

Autonomous annotation must not compromise the machine.

- `validation_mode=serial` unless limited parallelism is demonstrably needed
- `max_validation_jobs=2`
- `max_validation_jobs=1` whenever raw-file analysis, conversion, or large
  manuscript processing is active
- validate changed datasets first; smoke-check before full sweeps

If validation hangs or the system becomes constrained, reduce concurrency before
continuing.

---

# Phase 6: Report

- resolved target set and config
- screening counts (include / exclude / uncertain) and the log path
- per dataset: rounds retained and discarded with the reason for each, `reconcile` findings, the
  final score, the review-gate status (hash approved / pending / gate unavailable)
- the stopping condition per dataset (no gain, budget, manual)
- files changed
- remaining unresolved high-value gaps

With `write=report-only`, produce the same retained-improvement report without
writing SDRFs.

---

# Example invocations

```text
# Full campaign: discover, screen, then annotate
/sdrf-skills:sdrf-campaign target="all human gut metaproteomics datasets" criteria="criteria/gut.md" extract="criteria/gut.md" output="results/gut_screen.tsv" profile="general-proteomics" write="sandbox"

# Screening only
/sdrf-skills:sdrf-campaign target="data/accessions.txt" criteria="criteria/eligibility.md" extract="instrument,acquisition,sex,age" output="results/screen.tsv" stop_after="screen"

# Annotation only, from an existing manifest
/sdrf-skills:sdrf-campaign target="data/cell_line_manifest.tsv" profile="cell-line" focus_fields="cell line,disease,organism part,treatment" budget="3,$3" write="sandbox"

# Crosslinking campaign
/sdrf-skills:sdrf-campaign target="all crosslinking datasets" profile="crosslinking" objective="crosslinking_assay_completion" stop="only_low_confidence_candidates_left"

# Mixed PRIDE + MassIVE accessions, report only
/sdrf-skills:sdrf-campaign target="accessions:PXD005969,MSV000078958" criteria="human fecal metaproteomics only" write="report-only"
```

---

# Notes

- **MassIVE is fully in scope.** `search_projects` and `get_project_details`
  both cover it. MassIVE records are metadata-poor, not second-class: screen them
  from the publication on the same criteria as PRIDE records. Their publications
  usually still resolve to an open-access PMCID, which is the main way a MassIVE
  candidate gets decided.
- A dataset can hold both an `MSV…` and a `PXD…` accession — deduplicate on
  `all_accessions` (3.1).
- Never fill a field with a value not supported by evidence.
- `unclear` (extract fields) and `uncertain` (label) are not interchangeable, and
  neither is an SDRF reserved word. Phase 4 emits a curation TSV, not an SDRF:
  never write `not applicable` or `not available` there, even for a question that
  genuinely does not arise — give that case its own vocabulary word.
- Screening does not create, validate, fix or improve SDRF files. That is Phase 5.

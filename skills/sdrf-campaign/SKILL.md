---
name: sdrf-campaign
description: Use when the user wants to run an SDRF annotation campaign over a class of studies rather than one dataset — screen or shortlist proteomics studies from PRIDE, MassIVE or ProteomeXchange against user-defined inclusion criteria and write an evidence-backed resumable TSV, then annotate the included datasets as an autonomous retained-improvement loop. Covers both halves: use stop_after="screen" for screening only, or target a manifest to skip straight to annotation.
user-invocable: true
argument-hint: 'target="<all <category>|accessions:PXD...,MSV...|path/to/list.txt|manifest.tsv>" [criteria="<md|txt|inline>"] [stop_after="screen|annotate"] [profile="<preset>"] [objective="<metric>"] [focus_fields="<f1,f2>"] [stop="<rule>"] [write="<sandbox|branch|report-only>"]'
---

# SDRF Campaign Protocol

A campaign has two halves and they are one pipeline: **screen** a candidate set
down to the studies that belong, then **annotate** those studies in a retained-
improvement loop. The screen's TSV is the loop's input.

Run both by default. Use `stop_after="screen"` when the user only wants a
shortlist, and point `target` at an existing manifest to skip straight to the
loop.

Do not guess. Verify every field against a source.

**The criteria come from the user, not from this file.** Nothing here is specific
to any one research question.

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

The screen reads curated SDRFs from `bigbio/sdrf-annotated-datasets` first
because they are fast, not because they outrank anything: a curated SDRF is
someone's reading of these same sources, and where it disagrees with them, the
order above decides.

---

# Phase 1: Parse the request

Normalize into these fields. State the resolved config before any work begins.

## Screening arguments

### `target`
- `accessions:PXD001234,MSV000078958` — comma/whitespace-separated list.
  `get_project_details` routes PXD and MSV to the right repository on its own.
- `.txt` — one accession per line; strip whitespace, skip blanks.
- `.tsv`/`.csv` — if the header is exactly the screen TSV's (Phase 4), the file
  *is* a finished screen: skip Phases 2–4 and annotate its `include` rows.
  Otherwise take the first available column of `id`, `accession`,
  `project_accession`, `project`, or the first column, and ignore the rest.
- `all <category> datasets` — discover via search (Phase 2).

Search covers **PRIDE and MassIVE together**. A repository name inside the
category phrase ("all PRIDE …") is ordinary habit, not a scoping instruction —
search both. Pass `repository="pride"` or `"massive"` only when the user names it
*as an exclusion*: "PRIDE only", "skip MassIVE".

### `criteria`
Path to `.md`/`.txt`, or inline text. Number the rules as you read them, in
order; `failed_criterion` reports these numbers, so they must stay stable for the
whole run and be unique across inclusion and exclusion rules. If the file already
numbers its rules that way, reuse its numbers.

Omitted → no filtering: every accession is `include`. Skip the curated lookup;
Phase 3 fetches only the repository record (3.2).

### `stop_after`
`screen` or `annotate` (default). `screen` writes the TSV and its summary, then
stops.

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
Screen TSV  : <path>
Stop after  : <screen|annotate>
Profile     : <preset>      Focus     : <fields>
Budget      : <rounds,cost> Stop rule : <rule>
Write       : <mode>
Resuming    : <N already screened | fresh run>
```

---

# Phase 2: Resolve the target set

## Fixed lists
Keep the original order; deduplicate and report the count removed.

## Category discovery

**1. Sweep SHORT keywords.** PRIDE ANDs the terms in a keyword then RANKS rather
than filters, so a whole category sentence collapses recall — `metaproteomics`
returns 100+ hits, `human gut metaproteomics` 2 — and no single term covers a
field: `nanoPOTS` (11) and `proteoCHIP` (11) union to 22 single-cell datasets
with zero overlap, and `single-cell proteomics` returns neither.

```text
Tool: search_extensive(keywords=["metaproteomics", "gut microbiome proteomics", ...])
```

It pages every keyword to exhaustion, unions and dedupes on `all_accessions`,
and reports `per_keyword.new` — what each keyword added that no earlier one had.
A keyword with `new: 0` was redundant.

**2. Never report a truncated sweep as complete.** A non-empty `truncated` means
the union is a floor, not the result set. A non-empty `errors` means a page was
lost, not empty — retry, and if it still fails, say so. Both go in the report.

**3. Pre-filter on the structured fields the criteria constrain.** Every hit
already carries `organism`, `organism_parts`, `instruments`, `experiment_types`,
`quantification_methods` and `keywords`, so this costs no calls. Write each clear
mismatch as an `exclude` row (Phase 4) with evidence `repository structured
fields`; a criterion no structured field covers waits for Phase 3.

- These fields are submitter-supplied and often empty. **An empty field is not a
  failed check** — carry the candidate forward. MassIVE publishes almost none of
  them, so nearly every MassIVE candidate is decided in Phase 3; never exclude
  one for thin metadata.
- **Match values exactly, never by substring.** `"Data-independent acquisition"`
  contains `"dependent"`, so a substring test for DDA silently admits every DIA
  study.

## Curated SDRFs

Look up every accession not yet in the screen TSV, with each hit's
`all_accessions`, in one call:

```bash
sdrf-tools curated PXD001234 MSV000078958 ... > <scratch>/curated.json
```

Each accession maps to its curated files, each with a row count and the distinct
values of every `characteristics[…]`, `comment[…]` and `factor value[…]` column;
`[]` means nothing is curated. Read one accession's entry when you screen it
(`jq '.["PXD001234"]' <scratch>/curated.json`). Exit 2 means the lookup failed,
not that nothing is curated: say so in the report and screen without it.

```text
Discovered  : N unique datasets across K keyword searches
Pre-filtered: N remaining (M excluded on structured fields)
Curated     : N of M have a curated SDRF
```

---

# Phase 3: Screen each candidate

Process each accession not yet in the screen TSV, independently. Read the
sources in this order and stop as soon as every rule is settled: the curated
SDRF is fast and the publication is slow. Reading order is not authority — on a
conflict, the evidence precedence above decides.

## 3.1 Curated SDRF

If the accession has curated files, check each rule against their summary,
taking all of its files together. A rule is **settled** when the values decide
it, and **open** when no column covers it or the column holds only `not
available` / `not applicable`.

## 3.2 Repository record

```text
Tool: get_project_details(project_accession="PXDXXXXXX")
```

Always fetch it: it gives the `repository` column and `all_accessions`.

- PXD accessions PRIDE does not hold fall back to MassIVE (e.g. `PXD003626`), so
  a PXD is **not** evidence the record is in PRIDE.
- Use `all_accessions` to avoid screening one study twice. If it names an
  accession the curated lookup did not cover, run `sdrf-tools curated` for it.
- Read every field, not just the pre-filter ones. `sample_processing_protocol`
  and `data_processing_protocol` are free text and often the highest-signal
  source. MassIVE records have no protocol text.
- A field that contradicts the curated SDRF on a rule reopens that rule.
- An `error` key means the accession is in neither repository. Do not retry and
  do not invent metadata: go to 3.3, and if there is no publication either, label
  `uncertain` and say the record was unreachable.

Settle open rules the record decides unambiguously. Once a rule clearly fails or
every rule is settled, with nothing in conflict, go to 3.4.

## 3.3 Publication

Only for rules still open. `publications` lists `{pmid, pmcid, doi,
is_open_access, reference}`; every article tool accepts any of those ids.

```text
Tool: get_full_text_article(pmc_ids=["PMC9174028"])                    # Methods and sample prep
Tool: get_full_text_article(pmc_ids=["PMC9174028"], mode="toc")        # long paper: list sections
Tool: get_full_text_section(pmc_id="PMC9174028", section="<name>")     # then fetch one
Tool: get_article_metadata(ids=["35695565"])                           # abstract only
```

**`is_open_access: false` means "try harder", not "abstract only".** PRIDE and
Europe PMC have both reported gold-OA CC-BY papers as closed, and the full-text
fetch sometimes 404s for papers that are open. Before settling for the abstract,
exhaust `get_pdf_by_unpaywall`, the PMC HTML render, NCBI eutils, and a Europe
PMC search on **the accession itself**. If the record lists no publication,
search by title and authors; if that fails, decide from the repository record
alone and say so in `evidence`.

A paper that merely *cites* an accession may only be reusing the data. Signals of
reuse: the accession appears in a data-availability list among many; the paper
is a benchmark, meta-analysis or reanalysis; it postdates the deposit by years.
Signals of origin: "data have been deposited"; organism, instrument and sample
counts match; contemporaneous with submission. A dataset attached to the wrong
paper silently corrupts every decision derived from it.

Never infer eligibility from vague title or keyword matches.

## 3.4 Label and append

Apply each rule in order by its number:
- `include` — all inclusion rules pass and no exclusion rule applies.
- `exclude` — a rule clearly fails. Record the **first** failed rule's number in
  `failed_criterion` and its one-sentence decisive factor in `reason`.
- `uncertain` — a rule is still open after 3.3. Record its number in
  `failed_criterion` and the missing evidence in `reason`.

Prefer `uncertain` over guessing. `uncertain` means **needs a human** — it is not
a soft include. Only `include` rows proceed to Phase 5.

Append the row **now** (Phase 4) — do not accumulate in memory — then print
`[N/total] PXD###### → LABEL`.

---

# Phase 4: The screen TSV

The screen TSV is a **decision record, not a metadata export**: one row per
accession, six fixed columns, in this order. Never add columns for organism,
instrument, sample counts or anything else — read those from the SDRF or the
repository when they are needed.

| Column | Value |
|---|---|
| `id` | the accession |
| `repository` | `PRIDE`, `MassIVE`, or `unclear` |
| `label` | `include`, `exclude` or `uncertain` — nothing else |
| `failed_criterion` | the rule number; empty for `include` |
| `reason` | one sentence: the decisive factor, or the missing evidence |
| `evidence` | the deciding sources, briefly: `curated SDRF <file>`, `repository structured fields`, `PRIDE protocol`, `paper methods`, `abstract`, `title/keywords only` |

**Path:** `screen_<criteria file stem>_<first 8 hex of the criteria's SHA-256>.tsv`
in the working directory — stem `inline` for inline criteria, and
`screen_all.tsv` with no criteria. Re-running the same criteria resumes the same
file; edited criteria start a new one, because their rule numbers may have moved.

- Tab-separated, UTF-8, header first.
- **Sanitize every value**: replace tab, CR and LF with a single space. Free text
  from paper methods routinely contains them, and one stray tab silently shifts
  every column in that row.
- **Resume**: if the file exists, its header must be exactly these six columns —
  otherwise stop and ask. Skip every `id` already in it.

When the set is done, report:

```text
Saved N records to <path>
include:   N
exclude:   N
uncertain: N
```

- exclusions by rule: `awk -F'\t' 'NR>1 && $3=="exclude" {print $4}' <path> | sort | uniq -c`
  — that is why `failed_criterion` holds a number, not prose
- for category discovery: the keywords swept, `per_keyword`, and any `truncated`
  or lost pages
- whether the curated lookup ran
- every `uncertain` accession with the evidence that was missing, so a human knows
  what to go find

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
- screening counts (include / exclude / uncertain) and the screen TSV path
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
/sdrf-skills:sdrf-campaign target="all human gut metaproteomics datasets" criteria="criteria/gut.md" profile="general-proteomics" write="sandbox"

# Screening only
/sdrf-skills:sdrf-campaign target="data/accessions.txt" criteria="criteria/eligibility.md" stop_after="screen"

# Annotation only, from an existing manifest
/sdrf-skills:sdrf-campaign target="data/cell_line_manifest.tsv" profile="cell-line" focus_fields="cell line,disease,organism part,treatment" budget="3,$3" write="sandbox"

# Crosslinking campaign
/sdrf-skills:sdrf-campaign target="all crosslinking datasets" profile="crosslinking" objective="crosslinking_assay_completion" stop="only_low_confidence_candidates_left"

# Mixed PRIDE + MassIVE accessions, report only
/sdrf-skills:sdrf-campaign target="accessions:PXD005969,MSV000078958" criteria="human fecal metaproteomics only" write="report-only"
```

---

# Notes

- Never fill a field with a value not supported by evidence.
- Screening does not create, validate, fix or improve SDRF files. That is Phase 5.

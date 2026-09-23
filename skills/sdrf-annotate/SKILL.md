---
name: sdrf-annotate
description: Use when the user wants to create or annotate an SDRF file for a proteomics dataset. Also use to plan what metadata to capture and discuss experimental design/strategy before creating the file. Triggers on PXD accessions, requests to create SDRF, planning/strategy questions, or annotation tasks.
user-invocable: true
argument-hint: "[PXD accession or experiment description]"
---

# SDRF Annotation Workflow

> **Bundle paths.** `spec/`, `tools/` and `data/` ship with this skill, not with your working
> directory. Resolve every such path below against the bundle root — `$CLAUDE_PLUGIN_ROOT` under
> Claude Code (`$CLAUDE_PLUGIN_ROOT/spec/sdrf-proteomics/TERMS.tsv`), or your sdrf-skills checkout
> on other platforms. The helpers are the `sdrf-tools` command, installed by `/sdrf-skills:sdrf-setup`; no `PYTHONPATH` or plugin-root variable is needed to run them.
> Files the user is annotating stay relative to the working directory.

You are performing a complete SDRF annotation. Work through the steps in order, but
settle **Step 0 first**: it decides which of the later steps apply at all. Do not guess a
value — verify it, against the record when you have network tools and against the files in
front of you when you do not.

## Step 0: Settle the operating mode, then stop looking around

Answer both questions below **before any other tool call**. Getting them wrong is what turns
a ten-turn annotation into a fifty-turn one, because the workflow below assumes lookups that
may not exist here and you will spend turns discovering that one failed call at a time.

**1. Is the record already on disk?** If the working directory holds an `evidence/`
directory, or the user handed you the PRIDE record, file list and paper as files, then the
gathering is already done. You are in **offline mode**:

- Read those files, and treat them as the whole of the available record.
- **Skip Steps 0.5, 1.1, 1.2 and 1.3 entirely.** There is nothing to fetch, and no
  community repository to consult.
- Do not call MCP tools, do not search the web, and do not ask the user a question. Where
  the evidence is silent, write an explicit reserved word (below) rather than inferring a
  value from what is typical.

**2. Which lookups do you actually have?** Check once, in a single turn, and remember the
answer: MCP tools for PRIDE/Europe PMC/OLS, and `parse_sdrf` on the PATH. Do not re-probe
later. If a class of lookup is missing, use the offline substitute named below instead of
retrying it.

If `parse_sdrf` is missing and you can reach the user, point them at
`/sdrf-skills:sdrf-setup` (or `pip install sdrf-pipelines`) and ask whether to wait or
continue with structural checks only. If you cannot ask, continue and say plainly in your
final report that the file was not machine-validated.

### Facts you do not need to go looking for

These are fixed. Do **not** grep the installed `sdrf_pipelines` package, glob for its
source, or re-derive them from a template file:

- **Validate with:** `parse_sdrf validate-sdrf -s <file> -t <template> [-t <template> ...]`
  (`-s`/`-t` are the short forms of `--sdrf_file`/`--template`). Add `--use_ols_cache_only`
  when you have no network, and `--skip-ontology` only for a fast structural check. A full
  ontology run peaks near 1.9GB of RSS, so run one at a time.
- **Column order:** `source name` first; all `characteristics[...]` next; then `assay name`
  and `technology type`; then all `comment[...]`; and every `factor value[...]` **last**,
  closing the file. Repeated column names are legal and meaningful — never de-duplicate them
  by appending a suffix.
- **Controlled terms without a network:** `$CLAUDE_PLUGIN_ROOT/spec/sdrf-proteomics/TERMS.tsv`
  is the authoritative offline table. It gives each term's type, the templates that use it,
  the permitted values, and — per term — whether `not available` and `not applicable` are
  allowed. Consult it instead of OLS when OLS is unreachable.
- **Reserved words:** exactly `not available` and `not applicable`, and only for terms whose
  `allow_not_available` / `allow_not_applicable` column in TERMS.tsv is true.
- **Sample properties carry the bare value.** Write `characteristics[...]` as the value
  alone (`HeLa`, `Homo sapiens`); do not wrap it as `NT=<name>;AC=<accession>`. Accession-
  shaped values such as a Cellosaurus `CVCL_0030` are written as they are. `comment[...]`
  columns do take `NT=;AC=` where the term is ontology-backed.

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

## Step 0.5: Is the dataset already annotated? — STOP GATE

> **Offline mode (Step 0):** skip — the community repository is not reachable.

Before annotating a PXD, enumerate its directory in the community repository (it may hold
several suffixed SDRFs), audit any existing file against the deposit, and **let the user decide**
whether to re-annotate. Never re-annotate silently or overwrite without an explicit `reannotate`.
Read [references/existing-annotation.md](references/existing-annotation.md) for the lookup, the
audit and the report format.

## Step 1: Gather the project record

> **Offline mode (Step 0):** the record is already in `evidence/` (`pride.json`, `files.json`,
> `manuscript.txt` when a paper exists). Read those; do not fetch anything.

Otherwise gather, in this order: the PRIDE project record; the run list (raw files only — a
deposited SDRF is never consulted); the publication and its Methods; sample metadata from the
paper; BioSamples where the deposit maps sources; and the plasma guard when the study is plasma.
The archive's structured fields (`instruments`, `diseases`, `organismParts`) are submitter
dropdowns, not the record — the title, the protocol prose and the run names outrank them.
Read [references/gather-context.md](references/gather-context.md) for each source's endpoint,
what to extract, and the traps.

## Step 2: Select Templates

Use the sdrf:templates decision tree. Based on the gathered context:

1. **Technology**: MS → `ms-proteomics`. Affinity → `affinity-proteomics`
2. **Organism**: Human → `human`. Mouse/rat → `vertebrates`. Drosophila → `invertebrates`. Plant → `plants`. Microbiome → `metaproteomics` + child
3. **Experiment type**: DIA → `+ dia-acquisition`. Cell lines → `+ cell-lines`. Single-cell → `+ single-cell`. XL-MS → `+ crosslinking`. Immunopeptidome → `+ immunopeptidomics`
4. **Clinical/Oncology**: Patient study → `+ clinical-metadata`. Cancer → `+ oncology-metadata`

Present the template selection to the user for confirmation before proceeding.
Explain WHY each template was chosen and what columns it adds.

## Step 3: Get the contract, then author two tables — do not write the SDRF by hand

You will not build SDRF structure yourself. Column order, fraction and replicate numbering,
channel rows and repeated columns are produced by `build` from two small tables you write.
This is what keeps the file structurally valid on the first try and what keeps this
annotation short: no spec reading beyond one command, no editing the SDRF, no re-reading it.

### 3.1 Print the contract (once)

```bash
sdrf-tools contract -t <template1> [-t <template2> ...]
```

It lists every column of the template union in order, whether it is required, whether it
takes multiple values, the value form (`bare value`, `NT=<name>;AC=<accession>`,
`<number> ppm|Da`, `integer`), and which reserved words it permits. Keep it in context; do
**not** read `TERMS.tsv`, the template YAMLs or the spec README to learn the same thing.

`contract` and `build` need `sdrf-pipelines`; if the `python3` on your PATH cannot import it
but `parse_sdrf` is installed, they re-run themselves under `parse_sdrf`'s interpreter. Do not
go looking for another Python yourself.

### 3.2 Write `samples.tsv` — one row per source *and replicate*

Tab-separated. Three structural columns, then the sample properties you can support from
the evidence:

| column | required | content |
|---|---|---|
| `source name` | yes | the sample identifier you choose; never generated for you |
| `files` | yes | the **fractions of one injection**, comma-separated, in fraction order (one file if unfractionated) |
| `label` | yes | `label free sample`, or one channel (`TMT126`, `TMT127N`, `iTRAQ114`, `SILAC heavy`) — never a plex name like `TMT10` |
| `assay name` | no | only to override the default (file stem; `<stem>-<channel>` when multiplexed) |
| `technical replicate` | no | integer; default 1 |
| `characteristics[...]` | as evidenced | bare values; `not available` only where the contract allows it |
| `factor value[...]` | as designed | the variable(s) the study compares |

**Replicates are separate rows, not a longer `files` list.** A source measured in three
runs is three rows that differ in `characteristics[biological replicate]` or
`technical replicate`; a comma list means fractions of a single injection. `build` refuses
two rows that share (source, biological replicate, technical replicate, fraction) — that is
the row coordinate the community review gate checks — rather than renumber them for you.

Multiplexed runs: one row per (source, channel), each listing the run file(s) in `files`. A
channel the run does not use gets a row with an **empty** `source name`; `build` emits
nothing for it. `build` refuses a run whose channel set is incomplete — it will not fill a
channel in, and neither may you: see 6.1 for where the map is found.

### 3.3 Write `technical.tsv` — run-level settings shared by every row

Two columns, `column` and `value`, one row per comment column that is constant across the
file: `comment[instrument]`, `comment[cleavage agent details]`, tolerances,
`comment[proteomics data acquisition method]`, `comment[sdrf version]`, and so on. A
`multiple` column such as `comment[modification parameters]` takes its values separated by
`|` — one column per value is emitted:

```text
column	value
comment[instrument]	NT=Orbitrap Fusion Lumos;AC=MS:1002732
comment[modification parameters]	NT=Carbamidomethyl;AC=UNIMOD:4;TA=C;MT=Fixed|NT=Oxidation;AC=UNIMOD:35;TA=M;MT=Variable
```

`comment[sdrf template]` and `technology type` are filled by `build` from the templates you
pass; do not add them.

Steps 4 and 5 tell you how to find the *values* for these two tables. Step 6 builds.

## Step 4: Find the sample values → `samples.tsv`

`characteristics[...]` carry the **bare value** (`Homo sapiens`, `liver`, `HeLa`), never
`NT=;AC=`; structured exceptions keep their keys (`spiked compound` `CT=/QY=`, `pooled sample`
`SN=`). Demographics are per-sample facts: `age`, `sex`, `ethnicity` need source-level
evidence, `developmental stage` may come from an unambiguous cohort description; when only a
cohort summary exists, leave the per-sample field out rather than guess. Verify every term in
the ontology the contract names for its column; use `not available` only where the contract
allows it. Cell lines: `sdrf-tools cellline lookup <name>` or `/sdrf-skills:sdrf-cellline`.
Read [references/sample-values.md](references/sample-values.md) for the OLS procedure,
embeddings/ZOOMA fallbacks, and the specificity and reserved-word rules.

## Step 5: Find the technical values → `technical.tsv`

Instrument, cleavage agent, modifications, labels, acquisition method, tolerances, and the
run-level settings, each as `NT=<name>;AC=<accession>` where the contract says so. Read the
modifications **out of the deposited search results** (MaxQuant `parameters.txt`, `.msf`,
mzIdentML), never infer them from the paper; the acquisition method is a descendant of
`PRIDE:0000659`, PRIDE-first. Read
[references/technical-values.md](references/technical-values.md) for where each value lives
in the deposit and how to verify it from the raw files.

## Step 6: Build the SDRF

```bash
sdrf-tools build \
  --samples samples.tsv --technical technical.tsv --files evidence/files.json \
  -t <template1> [-t <template2> ...] -o output.sdrf.tsv
```

`build` assigns one row per (source, file); `comment[fraction identifier]` from the position
in `files` (1 for a single file); `comment[technical replicate]` from the column or 1;
`assay name` from the file stem unless you set it; the contract's column order with factor
values last. Every file in `files.json` should be claimed by exactly one source (or, when
multiplexed, by one row per channel).

If `build` refuses, it names the table and row. Fix that row and run it again. It refuses,
rather than guesses, an incomplete channel map (6.1). **If `build` cannot be run at all** — the
command is denied or the tools are missing — stop, keep `samples.tsv` and `technical.tsv`, and say
so in the report. Do not write `output.sdrf.tsv` by hand: a hand-written file is exactly what
this step exists to prevent, and on a large dataset it will not even fit in one response.

### 6.1 Multiplexed: exhaust every source of the channel→sample map before BLOCKING

Inventing a channel identity is the worst failure this skill can produce, and a missing map in
PRIDE is not proof that none exists. Read [references/channel-map.md](references/channel-map.md)
and work its ladder (paper and supplementary → deposited PRIDE files → Europe PMC supplementary →
repositories cited in Data Availability → cross-validation) before declaring the dataset BLOCKED.

## Step 7: Set Factor Values

1. Identify what is being compared (disease vs control? treatment vs untreated?)
2. Add a `factor value[<variable>]` column to `samples.tsv` (e.g., `factor value[disease]`);
   `build` places it last
3. Copy values from the corresponding characteristics column
4. If multiple factors → one `factor value[...]` column per factor

**Do not invent a factor value column for sample composition.** A quantity that describes
what was added to the sample during preparation — a spiked protein/peptide/mixture and how
much of it, a carrier amount, a dilution — is sample metadata, not the compared variable. It
belongs in `characteristics[spiked compound]` (`CT=`/`QY=`/`PS=`/`AC=`/`CN=`/`CV=`, repeated
once per spiked component; see SAMPLE-GUIDELINES.adoc §Spiked-in Samples), even when no other
factor exists. A reference/benchmark dataset with no real experimental comparison correctly
has no `factor value[...]` column at all — that is an expected `no_factor_value` advisory, not
a gap to fill with an unrelated column.

## Step 8: Add SDRF Metadata

Two rows in `technical.tsv`; the third column is `build`'s:

- `comment[sdrf version]` → the technology template's version as the contract header prints
  it (e.g. `v1.1.0` for `ms-proteomics v1.1.0`); do not read `templates.yaml` for it
- `comment[sdrf annotation tool]` → `manual curation` (or the tool name if applicable)
- `comment[sdrf template]` → filled by `build`, one column per template you passed with `-t`

## Step 8.5: Reconcile every value against the record — REQUIRED

`parse_sdrf` checks that a value is well-formed; it cannot check that it is **true of this
deposit**. Before validating, run

```bash
sdrf-tools reconcile <file.sdrf.tsv> --record <project.json> --accession <PXD>
```

and treat each finding as a question to answer from the record. The usual right answer to a
contradiction is a sentinel: a wrong specific value is worse for reuse than an honest blank.
Read the title and the run names, never broadcast a project-level disease onto control rows,
and check the file format against the instrument vendor.
Read [references/reconcile.md](references/reconcile.md) for the reasoning and the four checks.

## Step 9: Validate — at most two rounds, fixes go to the tables

```bash
parse_sdrf validate-sdrf -s output.sdrf.tsv -t <template1> [-t <template2> ...]
```
Add `--use_ols_cache_only` when there is no network. Use the templates from Step 2; several
`-t` flags validate against their union.

If it reports errors:
1. Change the offending **value in `samples.tsv` or `technical.tsv`** — never `Edit`
   `output.sdrf.tsv`, and do not read it back; the tables are the source, the SDRF is output.
2. Run `build` again (Step 6), then validate again.
3. **Stop after the second validation.** If errors remain, list them verbatim in the report
   (Step 10) with what you tried. Two rounds is the budget; a third rarely converges and the
   remaining errors are more useful to the reader than another guess.

If `parse_sdrf` is not installed, say so in the report and point at
`/sdrf-skills:sdrf-setup` (or `pip install sdrf-pipelines`).

## Step 10: Present Results

Present the validated SDRF as a TSV code block and explain:
- Total rows and columns
- Sample groups and counts per group
- Templates applied (with version)
- File mapping summary
- Validation result (PASS / warnings)
- Any values marked as `not available` (ask user to fill)
- Any values you're uncertain about (flag for user review)

## Step 11: Recommend community contribution

For a ProteomeXchange dataset, tell the user the annotation can be contributed with
`/sdrf-skills:sdrf-contribute {PXD}` (reuse the Step 0.5 result to say whether this is new or an
update; an update's PR must state what was wrong before, with evidence). A recommendation only.

## Rules that do not bend

The format rules — value encoding, reserved words, modification syntax, UNIMOD swaps, label
types, row identity — live in one place:
[../sdrf-knowledge/references/format-rules.md](../sdrf-knowledge/references/format-rules.md).
Read it once per annotation. On top of them:

- NEVER re-annotate an already-annotated dataset silently (Step 0.5)
- NEVER take the archive's structured fields as the record; reconcile (Step 8.5) and write a
  sentinel on disagreement
- NEVER assert a project-level disease on every row — check for a control arm first
- NEVER match an ontology term on a keyword without checking the matched word's ROLE
  ("chymotrypsin-like activity" is an assay, not a digest; `icat` matches inside "quantifi(cat)ion")
- NEVER fabricate accessions, guess file names, or invent sample information
- Always distinguish: extracted from the paper vs inferred vs assumed

## Planning instead of annotating

When the user wants to discuss what to capture before there is a file — templates, columns,
design considerations, expected row count — read
[references/planning.md](references/planning.md) and follow it instead of the steps above.

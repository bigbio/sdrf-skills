# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A **skills-first** repo: the product is `skills/*/SKILL.md` — markdown workflows that teach an AI
assistant to annotate proteomics SDRF files. Supporting Python lives in `tools/`. Specification data
is **not** stored here; it is read at runtime from the `spec/` git submodule.

Skills are auto-discovered — `.claude-plugin/plugin.json` carries no `skills` key, so Claude Code
scans the `skills/` directory automatically. Each SKILL.md declares its own name and routing
description in frontmatter. Currently 20: 18 domain skills
named `sdrf-*` (invoked as `/sdrf-skills:sdrf-annotate` etc. once installed as a marketplace plugin) plus 2 review-gate skills named `sdrf-adversarial-review`
and `sdrf-annotate-reviewed`, deliberately platform-portable rather than plugin-namespaced.
Run `ls skills/` for the current set — **do not trust a hardcoded skill count anywhere in this repo**;
README.md alone carries three contradictory numbers, and commit `d5c4c70` exists only to repair drift.

## Commands

```bash
# Tests (126, ~2s, no network). CI runs: python -m pytest tests/ -v --tb=short
python -m pytest tests/ -q
python -m pytest tests/test_parser.py -q                                # single file
python -m pytest tests/test_services.py::TestPRIDEClient::test_get_project_mock -q  # single test (tests use classes)
python -m pytest tests/ -q -k unimod                                    # by keyword

# Lint — NOT in CI, and currently RED: 32 errors (28 F401, 4 F541), all auto-fixable.
# tools/review_gate.py is clean; the rest predates it. Run `ruff check --fix` before gating on it.
ruff check tools/ tests/

# Submodule: TWO levels deep (spec/ -> spec/sdrf-proteomics/sdrf-templates).
# `--recursive` is mandatory or templates.yaml is silently MISSING.
git submodule update --init --recursive     # restore pinned state (what you usually want)
git submodule update --remote --recursive   # advance to upstream tip; leaves a dirty gitlink

# tools CLI (no console_scripts; requires cwd == repo root)
python -m tools --help   # check, score, fix, benchmark, massive-files, verify, cellline,
                         # review-gate, audit-existing, bruker-dia
```

`python` is an alias to `python3` here, not a binary — skills invoke bare `python`, assuming an
activated env. Supported: Python 3.10/3.11/3.12 (CI matrix); `environment.yml` pins only
`python>=3.10` with no upper bound. **conda is not installed on this machine**, so the README's
"recommended" conda path does not work here; `uv` is available and `requirements.txt` already assumes it.

## Architecture

**Three layers, loosely coupled — the coupling gaps matter more than the layers:**

1. `skills/` — 16 SKILL.md workflows. Most are single-file; only the two review-gate skills ship
   supporting files (`references/review-contract.md`, `agents/openai.yaml`). Everything else reaches
   shared machinery at repo root by relative path.
2. `tools/` — offline-first Python. Only `massive-files` (annotate, review) and `cellline lookup`
   (annotate) are ever called by a skill. `check`, `score`, `fix`, `benchmark`, and `verify` are called
   by **no skill** — reachable only by hand or from CI, which smoke-tests all subcommands.
   `massive-files` asks MassIVE's PROXI record for the dataset's FTP root and tries it first
   (`proxi_ftp_url`): a bare MSV yielded no root at all, and the ProteomeCentral route yields one with
   the version directory missing, so both fell through to guessing `/v02/` and timed out on the many
   datasets that live under `/v01/`. `fetch_json` honours the response charset for the same
   ISO-8859-1 reason as the MCP client.
3. `spec/` — the runtime data contract (below).

**Skill dependency graph — two orchestrators.** `sdrf-autoresearch` chains
annotate → terms → techrefine → validate → fix → improve in a keep/discard loop, then dispatches a
fresh-context `sdrf-adversarial-review` at Step 9. `sdrf-annotate-reviewed` runs the producer/reviewer
loop: annotate (or fix/improve/techrefine) → adversarial review → repair → mandatory re-review.

The review gate is routed from exactly three places, all deliberate: `sdrf-contribute` runs
`review_gate.py gate` before publishing, `sdrf-autoresearch` gates completion, and `sdrf-review`
declares itself **advisory-only** when it produced the artifact, pointing at the real reviewer rather
than laundering a self-assessment into a verdict. Contribute and autoresearch are the only paths by
which an SDRF escapes, so gating elsewhere would be ceremony. None of this routing is covered by CI
(`tools-tests.yml` ignores `skills/**`), so all three call sites could be deleted and CI stays green.

**Six** skills (design, convert, brainstorm, explain, metascreen, annotate-reviewed) are referenced by
no other skill and reachable only via frontmatter routing — for metascreen and annotate-reviewed that
is by design; they are entry points. `knowledge` is referenced exactly once (by `explain`), which is
itself unreferenced, so it is only transitively reachable despite its description claiming it is
background for all skills.

**Everything is relative-path fragile.** The 28 spec references in `skills/` (across 27 lines in 12
files) are all repo-root-relative — 11 to `TERMS.tsv`, 9 to `templates.yaml`, 8 to individual template
YAMLs. None is absolute or variable-prefixed, and `CLAUDE_PLUGIN_ROOT` appears **zero** times
repo-wide. Installed as a real plugin these resolve against the *user's* cwd and silently miss; the
supported local-dev flow is `claude --plugin-dir <path>`, which loads skills from the repo root.

### Frontmatter schema (uniform across the 18 domain skills — match it exactly)

```yaml
---
name: sdrf-annotate           # matches the directory (skills/sdrf-annotate/); invoked as /sdrf-skills:sdrf-annotate once installed as a marketplace plugin
description: Use when the user wants to ... Triggers on ...   # always starts "Use when the user"
user-invocable: true
argument-hint: "[PXD accession or experiment description]"
---
```

No skill uses `allowed-tools`, `model`, or `version`. The two review-gate skills are the exception to
the schema above: they declare only `name` + `description` and are **not** `user-invocable` — they are
dispatched by other skills into a fresh context, never typed as a slash command.

### Adding/renaming a skill: the 6-file lockstep

Nothing in CI or the tests checks this, which is why the copies have already rotted. Update **all** of:
`CLAUDE.md`, `README.md` (badge, prose, table, tree), `GEMINI.md`, `.opencode/AGENTS.md`,
`.cursor/rules/sdrf-skills.mdc`, `.codex/INSTALL.md`. `.claude-plugin/plugin.json` needs **no** edit —
it points at the directory.

Domain policy is likewise duplicated: the UNIMOD table, reserved words, and row-count formula appear
verbatim in both `sdrf-knowledge` and `sdrf-annotate` (error patterns a third time in `sdrf-fix`); the
plasma heuristic is ~40 near-identical lines in both `sdrf-annotate` and `sdrf-autoresearch`. Edit one
copy and the others desync silently.

## MCP

`.mcp.json` wires the bundled `mcp/server.py` (FastMCP, name `sdrf-pride-pmc`) as a project MCP server,
launched via `./.venv/bin/python`. It exposes 11 tools: `search_projects`, `search_extensive`,
`get_project_details`, `get_project_files`, `get_article_metadata`, `get_pdf_by_unpaywall`, `search`,
`searchClasses`, `getChildren`, `get_full_text_article`, `get_full_text_section`. `fastmcp`/`httpx` are in `requirements.txt` and
`environment.yml`. **The server depends on `.venv/` existing** (`uv venv .venv && uv pip install
--python .venv/bin/python -r requirements.txt`); conda users must repoint `command` in `.mcp.json`.

Skills still call **five tools that exist in no bundled server** — `searchClassesWithEmbeddingModel`,
`listEmbeddingModels`, `searchWithEmbeddingModel` (in `sdrf-knowledge` and `sdrf-annotate`), and
`search_articles` / `search_preprints` (in `sdrf-annotate`). Those paths need an external OLS/PubMed/
bioRxiv MCP or a rewrite onto `searchClasses`/`getChildren`.

**`search_projects` is one page; `search_extensive` is the whole sweep.** The latter takes a LIST of
keywords, pages each to a short page, unions and dedupes on `all_accessions`, and reports what each
keyword contributed (`per_keyword.new` = 0 means that keyword was redundant). PRIDE ANDs the terms in
a keyword and then RANKS rather than filters, so recall — not pagination — is the binding limit: a
16-keyword single-cell sweep unions to more datasets than `single-cell proteomics` returns alone
(measured today: `nanoPOTS` 11 + `proteoCHIP` 11 = 22 unique, zero overlap). Exhaustion is proven
ONLY by a short page; an empty page after a full one is ambiguous, so it triggers a year-partitioned
(`filter=submissionDate==YYYY`) retry and anything still unresolved lands in `truncated` rather than
being reported as complete. PRIDE's historical bare-keyword 100-cap (#28) no longer reproduces —
verified 2026-08-19, v2 and v3 both paginate — which is why the partitioning is a detector, not an
unconditional workaround.

**Article identifiers must be BARE — silent-corruption class.** `get_article_metadata` and
`get_pdf_by_unpaywall` classify with `_classify_article_id` / `_parse_identifier`, which accept a bare
PMID (`35695565`), `PMC…`, or a bare DOI matching `^10\.\d{4,9}/…`. A prefixed `PMID:35695565` or
`doi:10.…` is rejected and yields an **error record, not an exception** — so a skill that documents the
prefixed form degrades every lookup to "no evidence" and reports it as low confidence. Pinned by
`tests/test_mcp_pride.py`.

**`get_project_details` / `search_projects` span PRIDE *and* MassIVE.** `MSV…` routes to MassIVE's
PROXI API; `PXD…` tries PRIDE then falls back to MassIVE, because MassIVE-hosted ProteomeXchange
datasets **404 in PRIDE** (`PXD003626` is a live example) — a PXD prefix is not evidence of PRIDE
residency. Results carry `repository` and `all_accessions` (a dataset may hold both an MSV and a PXD;
dedupe on it). MassIVE metadata is far thinner — measured over 100 datasets each: instruments
PRIDE 100% / MassIVE 3%, `experiment_types` and `quantification_methods` never published by MassIVE
(PRIDE 100% / 14%). Screen MassIVE candidates from the publication; empty ≠ excluded.

**PROXI parsing has three traps, all silent** — payload is in `value` not `name`; species /
publications / contacts nest one list deeper; and a missing value is often the literal string
`"null"`. `_proxi_values()` is the single place all three are handled — do not hand-roll PROXI parsing
elsewhere.

**MassIVE serves `charset=ISO-8859-1`.** `httpx.Response.json()` decodes raw bytes as UTF-8, so one
accented character (author names, European affiliations) raised `UnicodeDecodeError` and silently
dropped a whole result page — 29% recall loss on a measured query. `_cached_get_json` now falls back
to `json.loads(resp.text)`, which honours the declared charset. It also takes `not_found_ok=True` to
map a 404 to `[]`, because MassIVE 404s when you page past the end and that is exhaustion, not failure.

**PRIDE keyword search ANDs its terms.** `search_projects(keyword=…)` narrows hard on multi-word input
(`metaproteomics` → 100+, `human gut metaproteomics` → 2). Issue several short keywords and union the
accessions. PRIDE hits return the structured fields as **plain strings**, where `get_project_details`
returns **CvParam dicts** for the same logical fields; `_names()` handles both. On MassIVE's PROXI,
`resultType` is required, `pageNumber` is 1-based, and **`keywords=` is silently ignored** — it returns
the unfiltered listing, so only `search=` actually filters.

## Spec data contract (`spec/`, read at runtime — never hardcode)

- **Columns**: `spec/sdrf-proteomics/TERMS.tsv`
- **Manifest**: `spec/sdrf-proteomics/sdrf-templates/templates.yaml`
- **Templates**: `spec/sdrf-proteomics/sdrf-templates/{name}/{version}/{name}.yaml`

**TERMS.tsv is a glossary, not a column index.** 223 rows vs 345 distinct template columns, overlapping
only 204. For "is this column valid for template X?", **the resolved template YAML is authoritative**.
9 tab-separated columns (`term/type/ontology_term_accession/usage/values/description/allow_not_available/allow_not_applicable/allow_pooled`),
**CRLF-terminated** with one blank row — parse with
`csv.DictReader(open(p, newline='', encoding='utf-8-sig'), delimiter='\t')` and filter empty terms, or
`allow_pooled == 'false'` fails against `'false\r'`. Header is `type[term]`
(`characteristics[organism]`) **except** `type == 'anchor column'` (source name, assay name,
technology type), which is the bare term — `anchor column[source name]` is invalid SDRF.

**The `values` field drives ontology routing, but it is prose, not a closed grammar.** Common shapes:
comma-separated prefixes in preference order (`disease` → `MONDO, EFO, DOID, PATO`) → OLS;
`fixed: a, b, c` → closed enum, **no** OLS call; `pattern:`/`integer`/`numeric`/`free text` → no OLS;
prefix + subtree restriction (`MS, PRIDE (children of MS:1000044)`). **~26 of 223 rows fit none of
these** — do not write a parser that assumes total coverage, and never split on `,` without handling
the parenthetical, or you get the bogus ontology `PRIDE (children of MS:1000044)`.

**Templates**: `mutually_exclusive_with` appears **0 times** in `templates.yaml` — exclusivity lives in
the individual YAMLs and the graph is **asymmetric**, so compute the symmetric closure or you will
propose `human` + `plants`. Only `ms-proteomics`, `affinity-proteomics`, and `ms-metabolomics` are
`usable_alone: true`; `base` and `sample-metadata` are construction artifacts — never offer them.
`excludes` is **inert**: `resolve_templates.py` surfaces it as metadata only, and `merge_columns` never
consults it. The version in `extends: sample-metadata@>=1.0.0` is likewise decorative — the resolver
splits on `@` and always loads `latest`. Read `spec/scripts/resolve_templates.py` rather than
reimplementing merge semantics.

## SDRF invariants (silent-corruption class — wrong output, no exception)

1. **NEVER guess ontology accessions** — always verify via OLS. This is *not* self-enforcing: only
   `annotate` and `cellline` state it about accessions specifically, and `knowledge` — despite being
   the "background" skill — contains no such language at all. This file is the only global home for it.
2. **UNIMOD:1 = Acetyl, UNIMOD:21 = Phospho** — the #1 swap. (`tools/column_ontology_map.py` maps both
   UNIMOD:354 and UNIMOD:737 to `TMT6plex`, so swaps between *those* are never detected.)
3. **Reserved words**: `not available` / `not applicable` — never `N/A`, `NA`, `unknown`. Gated
   per-column by TERMS.tsv's `allow_*` booleans. Exception: `sdrf-metascreen` emits a curation TSV, not
   an SDRF, and uses **neither** reserved word — it mandates `unclear` for any undetermined `extract`
   field and `uncertain` in the `label` column (legal values: `include`/`exclude`/`uncertain`). The two
   tokens are not interchangeable, and neither belongs in an SDRF.
4. **Modification format**: `NT=name;AC=UNIMOD:id;TA=aa;MT=Fixed|Variable`. A positional value
   (`Protein N-term`) belongs in `PP=`, not `TA=`.
5. **All ontology terms carry label + accession** (e.g. "breast carcinoma" / MONDO:0007254). This file
   is the correct copy — `GEMINI.md:45`, `.cursor/rules/sdrf-skills.mdc:44`, and
   `.opencode/AGENTS.md:50` all say EFO:0000305; fix those toward this file, not the reverse.
6. **Duplicate columns are legal and load-bearing**: multiple `comment[modification parameters]` (one
   per mod) and multiple `comment[sdrf template]` (one per template) — both `cardinality: multiple`.
   `tools/sdrf_parser.py` disambiguates with `__N` keys; keying rows by raw name silently reads only
   the first occurrence.
7. **Validate before presenting any SDRF**: `parse_sdrf validate-sdrf --sdrf_file X --template Y`,
   after refreshing the submodule. **`--template` is a single-value option, so a call with several
   `--template` flags validates against only the LAST one** (verified 2026-07-17 on PXD061710:
   `cell-lines` last → ERROR on the tissue rows, `cell-lines` first → passes). Run `parse_sdrf`
   **once per declared template** (each against the rows that declare it) and require every run to
   pass; do not trust a single multi-`--template` invocation. For the authoritative multi-template
   constraint set (column licensing + reserved-word `allow_*`), resolve with
   `spec/scripts/resolve_templates.py` — parse_sdrf enforces neither. `parse_sdrf` ships in
   `sdrf-pipelines` and is **not installed by default** (CI installs only `requests`, `pytest`,
   `fastmcp`, `httpx` — not `sdrf-pipelines[ontology]`, which is heavy) — run `/sdrf-skills:sdrf-setup`. Keep
   concurrent `parse_sdrf` jobs ≤ 2.
8. **A producer must never approve its own SDRF.** For changed SDRFs, require a passing receipt from
   `sdrf-adversarial-review`; any edit invalidates the receipt and requires a fresh reviewer.
   Enforced by `python -m tools review-gate` (`track`, `pending`, `status`, `gate`, `approve`), which
   discovers changed artifacts from git and binds each receipt to the artifact's SHA-256, so an
   approval cannot outlive the content it describes. `gate` exits 1 while review is pending.
   Enforcement lives in the CLI, not the Stop hook, because four of the five platforms this repo
   supports cannot run Claude Code hooks at all.
9. **Vendor RAW only in `comment[data file]`** — `.raw`/`.d`/`.wiff`/`.wiff2`, never peak lists
   (`.mgf`/`.mzML`/`.mzXML`). A peak-list reference validates structurally but breaks reprocessing.
10. **Row-uniqueness coordinate**: (`source name`, `characteristics[biological replicate]`,
    `comment[technical replicate]`, `comment[fraction identifier]`) must be unique; the spec MUST-unique
    key is `source name`+`assay name`+`comment[label]`. The `sdrf-annotated-datasets` review gate rejects
    collisions, so annotate/fix/contribute must produce it.
11. **Value encoding by column type**: `characteristics[...]` = the bare ontology label (never
    `NT=;AC=`); `comment[...]` = `NT=<OLS label>;AC=<accession>`; structured characteristics
    (`spiked compound` `CT=/QY=`, `pooled sample` `SN=`) keep key-value.
12. **Acquisition method** (`comment[proteomics data acquisition method]`, required for MS) is a
    descendant of `PRIDE:0000659` — DDA `PRIDE:0000627`, DIA `PRIDE:0000450`, PRM `PRIDE:0000629`,
    SRM `PRIDE:0000630`; never `MS:1000206`/`NCIT:C161786`; `comment[dia method]` was removed.
13. **Contribution hygiene**: a `datasets/` PR adds exactly one new `{ACC}/` folder —
    `git diff --cached --name-status` must show 0 deletions/modifications to other datasets;
    unresolved datasets go to CI-exempt `sandbox/` with a `BLOCKED:` note; no AI/assistant attribution
    in public commits or PRs. Never invent sample->file/channel maps, demographics, or runs.

## Landmines

- **CI runs no tests on the product.** `tools-tests.yml` is path-filtered to `tools/**`, `tests/**`,
  `requirements.txt`. A PR touching **only** `skills/**` — the actual product — plus `hooks/`, `mcp/`,
  `plugin.json`, or docs runs **zero** tests. `check-spec.yml` has no path filter so it runs on every
  PR, but only warns when the spec is stale; it never fails the build.
- **Fixture path-filter gap**: `tests/conftest.py` reads `examples/PXD_synthetic.sdrf.tsv` and
  `tools/cellline_db.py` defaults to `data/*.tsv`, but neither `examples/**` nor `data/**` is in the CI
  filter. Editing them can break main with CI never running — run pytest locally.
- **`tests/test_services.py` mocks fail open**: it pre-seeds the private `_cache` with a key that must
  byte-for-byte equal `f"{base_url}{endpoint}|{params}"`. Any mismatch issues a **live** request to
  Cellosaurus/UniProt/EBI instead of failing. Prefer `MagicMock(spec=OLSClient)` injection, as
  `tests/test_hallucination.py` does.
- **Dead code**: `tools/services.py` is imported only by its own test; `hooks/check-deps.sh` is dead —
  `hooks/hooks.json` inlines the same logic, so both must be edited in lockstep.
- `tools/sdrf_fixer.py` implements **7** fix patterns, not the 10 its own docstring and the README
  claim (comments number them 1,3,4,5,6,7,9).

# sdrf-skills benchmark

A repeatable way to measure what the `sdrf-skills` methodology actually changes,
by annotating the **same** public proteomics dataset twice — once **with** the
skills (verify every term against OLS/PRIDE, thread ontology accessions, declare
templates, self-validate) and once **without** (annotate from general knowledge,
no systematic verification) — and scoring both files against a manually-curated
reference.

This folder (`examples/benchmark/`) contains the scorer
(`sdrf_skills_benchmark.py`), cross-agent pricing profiles, and two worked
benchmarks (`results/`).

## Quick start

```bash
# 1. install the validator (brings pandas + parse_sdrf + the bundled templates)
pip install sdrf-pipelines

# 2. score one arm against the curated reference
python sdrf_skills_benchmark.py \
    --sdrf results/PXD037221_TMT/PXD037221_with_skills.sdrf.tsv \
    --templates ms-proteomics \
    --template-dir "$(python -c 'import sdrf_pipelines,os;print(os.path.join(os.path.dirname(sdrf_pipelines.__file__),"sdrf","sdrf-templates"))')" \
    --reference results/PXD037221_TMT/PXD037221_reference.sdrf.tsv \
    --deposited-files pride_files.json \
    --key 'comment[data file]' 'comment[label]' \
    --out scorecard_with.json

# 3. do the same for the without-skills arm, then compare the two scorecards
python sdrf_skills_benchmark.py --compare scorecard_with.json scorecard_without.json \
    --out comparison.csv
```

### Key CLI flags

| flag | meaning |
|---|---|
| `--sdrf` | the SDRF file to score |
| `--templates` | template name(s) to validate/coverage against (e.g. `ms-proteomics`) |
| `--template-dir` | path to the `sdrf-templates` YAMLs (bundled inside `sdrf-pipelines`) |
| `--reference` | manually-curated SDRF for the agreement/triage metrics (optional) |
| `--deposited-files` | JSON list of repository raw files for the row-structure check (optional) |
| `--key` | row-match key for the curated diff. **For TMT/iTRAQ pass a composite key** `--key 'comment[data file]' 'comment[label]'` so reporter channels are not cross-joined |
| `--compare A.json B.json` | emit a two-arm comparison CSV |
| `--out` | output path |

## What comes out

- **Per-arm scorecard JSON** — one block per metric (see below): coverage,
  fill rate, reserved-word discipline, ontology breadth, accession inventory,
  `parse_sdrf` validation, template self-declaration, and (if `--reference` is
  given) the curated diff.
- **A comparison CSV** — the headline metrics side by side for the two arms.
- **Session/cost metrics** are computed separately (see *Cost & cross-agent*
  below) because they come from the agent platform's usage log, not the file.

## The metrics, briefly

Metrics fall into five groups. **Completeness** asks whether the file is fully
filled in; **richness**, how much verified detail it carries; **correctness**,
whether the values are right and self-describing; **effort/rigor**, how hard the
run worked to verify; **cost**, what it spent. A good annotation scores high on
the first four without spending heavily on the fifth. Higher is better unless
noted.

| metric | group | what it measures | lower=better? |
|---|---|---|---|
| Column coverage (required/recommended/optional) | completeness | share of each template tier's columns present | |
| Effective fill rate | completeness | cells with a real value vs `not available` | |
| SDRF columns | richness | total columns delivered | |
| Ontologies used | richness | distinct controlled vocabularies (MS, UNIMOD, PRIDE, …) | |
| Ontology accessions | richness | cells carrying a resolvable ID (`MS:1002877`) vs free text | |
| Template self-declaration | correctness | does the file state its `comment[sdrf template]`? A `parse_sdrf` pass can't detect this gap — it silently assumes a default | |
| Hallucinated-accession rate | correctness | fraction of accessions that fail to resolve in OLS4 | ✓ |
| Field agreement vs curated reference | correctness | per-column cell match against a trusted SDRF (each disagreement **triaged**, not auto-scored) | |
| Critical-error count (severity-weighted) | correctness | meaning-changing disagreements (wrong instrument/mod/organism/cleavage), weighted ×3 over cosmetic | ✓ |
| Row-structure fidelity | correctness | precision/recall of the file's rows vs the repository's deposited runs | |
| Verification calls | effort/rigor | live OLS/PRIDE lookups during the run | |
| Code cells / errored cells | effort/rigor | execution steps and failures | ✓ (errors) |
| Cost by token type | cost | dollar cost split by cache-read / fresh / cache-write / output | ✓ |

**Triage classes** for a reference disagreement: `run_wrong` (counts against the
run) · `curated_wrong` (run right, reference stale — counts *for* the run) ·
`curated_richer` (reference has what the run left blank — a coverage gap) ·
`run_richer` (run adds a correct value the reference lacks) · `both_ok`
(different but equally valid — neutral). The curated reference is itself
imperfect, so disagreements are classified rather than assumed to be run errors.

## Cost & cross-agent portability

The **file metrics above are fully portable** — they take a dataframe and a
reference and run in any Python environment. Two layers are agent-specific:

1. **Verification counting** — reads the agent's own tool/MCP call log.
2. **Cost (Family E)** — `session_metrics()` takes a **pricing profile**
   (`profiles/*.json`, or a name / dict) that maps the four token concepts
   (read, write, input_total, output) to the field names in *that* platform's
   usage record and supplies the price weights. `anthropic` is the default;
   `openai` is a stub to fill from current pricing; `generic` is unweighted.

```python
from sdrf_skills_benchmark import session_metrics
m = session_metrics(usage_row, pricing_profile="anthropic")   # or "openai", or "profiles/mine.json"
```

> **Cost is comparable only *within* one platform.** Different models, cache
> semantics, and price tables mean Family E is never a cross-agent leaderboard.
> The file-quality metrics are the apples-to-apples signal.

## Worked benchmarks (`results/`)

Both were run as paired arms of one dataset. Each results folder holds the two
delivered SDRFs, both scorecards, the comparison CSV, a figure, and a written
report.

### `PXD058436_MHCquant2` — immunopeptidomics / LFQ (633 rows)

Both arms produced a valid 633-row file. The with-skills arm carried **36 vs 28
columns** (every recommended one), **declared its 3 templates vs 0**, ran **36
live verifications vs 0**, and avoided a real cleavage-term error
(`unspecific cleavage` MS:1001956 vs the no-skills `no cleavage` MS:1001955). It
cost ~20–25% more, tracing to the longer guided workflow rather than token
volume.

### `PXD037221_TMT` — TMT-multiplexed E. coli quantitative (90 rows)

An independent experiment type. With-skills: **33 vs 26 columns**, **8 ontology
accessions (all OLS-resolvable, 0% hallucination) vs 0**, **self-declared
template vs none**, and **0 vs 13 severity-weighted critical errors** — Arm B
shipped every controlled term as ungrounded free text. Arm A's proper CURIEs
even corrected two malformed accessions (`AC=4`, `AC=1001251`) in the curated
reference itself. Both arms shared two coverage gaps (`cell type`,
`organism part`), an honest miss.

## Caveats

- Each benchmark is **one run per arm** — a rigorous single comparison, not a
  replicated study. The two reproducibility metrics the protocol calls for
  (run-to-run variance over N≥3 fresh sessions; planted-error detection rate)
  are **not yet satisfied**.
- The `PXD037221_TMT` arms were built in a single session, so its cost is a
  shared whole-benchmark envelope and is **not** reported per-arm.

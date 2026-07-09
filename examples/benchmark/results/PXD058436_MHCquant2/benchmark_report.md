# SDRF annotation with vs without `sdrf-skills` — PXD058436 (MHCquant2)

A head-to-head of two annotation runs of the **same dataset** by the **same model
under the same settings** (`claude-opus-4-8`, `high` effort), differing only in
whether the [`bigbio/sdrf-skills`](https://github.com/bigbio/sdrf-skills)
methodology was loaded.

- **With skills** — this session (`3bc85b5c…`)
- **Without skills** — prior session (`ce26187c…`, "MHCquant2")

All numbers below are read from the Claude Science session database
(`frames`, `execution_log`, `host_call_log`, `artifact_versions`) and from
diffing the two delivered SDRF files — not from memory.

---

## Headline

Both runs are good work: each independently identified the correct repository
(**PXD058436**), produced a **633-row** SDRF over the same three templates, and
passed `parse_sdrf`. The difference `sdrf-skills` makes is **not** whether you
get an answer — it is **how the answer is verified and how spec-complete it is**,
at a measurable cost premium.

| | with sdrf-skills | without | winner |
|---|---|---|---|
| Dataset & row count | PXD058436, 633 rows | PXD058436, 633 rows | tie |
| Programmatic ontology/PRIDE verification | **36 tool calls** (OLS + PRIDE) | **0** | **skills** |
| Output columns | 36 | 28 | skills (completeness) |
| SDRF template self-declaration | 3 `comment[sdrf template]` cols | none | **skills** |
| Ontology label+accession pairs | 6 columns | 4 columns | skills |
| Cleavage-agent term correctness | `unspecific cleavage` ✓ | `no cleavage` ✗ | **skills** |
| MHC-allele filtering by class | full genotype on every row | split I vs II | **without** |
| Synthetic-peptide QC runs handled | worked from 633 biological runs | explicitly excluded, documented | tie |
| Code cells executed | 58 | 89 | skills (fewer) |
| Cells that errored | 2 | 5 | skills |
| Cost (see caveat) | ~$14 annotation snapshot | $11.4 | without (cheaper) |
| `parse_sdrf` | PASS | PASS | tie |

---

## 1. Process — how each run reached the answer

The clearest, cleanest-measured difference is **verification behaviour**.

- **With skills** made **36 programmatic verification calls** during annotation
  (`host_call_log`, `method=mcp`): every ontology term (23 UBERON tissues,
  organism, instrument, cleavage, modifications, dissociation, MHC complex) was
  resolved against **OLS4**, and PRIDE metadata/file lists were pulled via the
  archive connector. The skill's rule *"NEVER guess ontology accessions — always
  verify via OLS"* is what drove this.
- **Without skills** made **0** such calls. It still produced correct ontology
  IDs for most fields (the model knows many common accessions), but nothing was
  machine-verified against a live ontology service — verification was the model's
  own recall.

Despite doing more verification, the skills run used **fewer code cells (58 vs
89)** and had a **lower error rate (2 vs 5 failed cells)**. The methodology
front-loads a clear plan (fetch → verify → restructure → validate), so there is
less exploratory thrashing.

## 2. Output — what landed in the file

Both files are 633 rows keyed to the same deposited mzML runs. Diffing them:

- **Spec self-identification.** The skills file carries the SDRF metadata block
  the spec expects — `comment[sdrf version]=v1.1.0` and **three
  `comment[sdrf template]` columns** (`ms-proteomics`, `human`,
  `immunopeptidomics`). The no-skills file omits all of these, so the file cannot
  declare which templates/versions it targets. This is the single biggest
  completeness gap (36 vs 28 columns).
- **Ontology accessions are threaded more consistently.** `comment[label]` and
  `comment[proteomics data acquisition method]` carry their `AC=` accessions in
  the skills file (`NT=label free sample;AC=MS:1002038`,
  `…;AC=PRIDE:0000627`) but are bare plain-text in the no-skills file.
- **A genuine accuracy difference in cleavage agent.** The skills file uses
  **`unspecific cleavage` (MS:1001956)**; the no-skills file uses **`no cleavage`
  (MS:1001955)**. These are different PSI-MS terms. The paper describes an
  in-silico digest *"without enzymatic restriction"* / a *"Non-specific HLA
  workflow"*, and the **submitter's own deposited draft used `unspecific
  cleavage`** — so the skills value is correct and the no-skills value
  misrepresents the search as no-digestion.
- **Organism label casing.** `Homo sapiens` (skills, the canonical NCBITaxon
  label) vs `homo sapiens` (no-skills). The validator tolerates the latter.

### Where the no-skills run was actually better
Honesty cuts both ways. The no-skills run made one **more precise** modelling
choice: it **filtered the HLA genotype by MHC class** — class I rows list only
A/B/C alleles, class II rows only DR/DQ/DP — whereas the skills run put the full
genotype on every row. Both are defensible; the class-split is arguably a
truer representation of what each IP enriched. It also **explicitly excluded** the
6 synthetic-peptide QC `.raw` runs with a documented rationale.

## 3. Cost & tokens — the overhead, honestly caveated

**Caveat first:** cost and token counts are only stored **cumulatively at the
frame level**. This (with-skills) session is still open and now also contains
*this comparison analysis*, so its live totals ($16.4, 13.6 M input tokens)
overstate the annotation itself. The fair figure is the **annotation-phase
snapshot** captured when this analysis began: **~$14.06** and **~10.5 M** input
tokens. The no-skills session is closed, so its **$11.41 / 13.29 M** is its true
end-to-end cost.

On that basis the skills run cost **~20–25 % more in dollars** — the price of 36
live verification round-trips and a longer guided workflow — while using
**comparable or slightly fewer input tokens**. So the overhead is real but
modest, and it buys machine-verified terms and a spec-complete file.

Neither number is a controlled benchmark: user think-time, a denied
environment-setup step (re-routed to an existing `sdrf` env), and the auditor
round-trip all touch these totals. Treat the cost delta as *indicative*, the
process and output-content deltas as *hard*.

---

## Bottom line

- **Use `sdrf-skills` when correctness and reusability matter** — community
  submission, reprocessing pipelines (quantms), or any file that must self-declare
  its templates and survive strict validation. It caught a real cleavage-term
  error, verified every ontology ID against OLS, and produced a spec-complete
  file, for ~20–25 % more spend.
- **The un-guided model is capable** — it got the dataset, the row structure, and
  most terms right, and even out-reasoned the skills run on class-specific HLA
  filtering. But it skipped live verification, omitted the SDRF template block,
  and picked a wrong cleavage term — the kinds of gaps that a strict curator or
  the PRIDE SDRF Explorer would bounce.

## Files
- `skills_comparison.png` — 3-panel figure (process, output, cost)
- `skills_comparison_scorecard.csv` — dimension-by-dimension correctness table
- `skills_comparison_metrics.csv` — raw measured metrics with provenance notes

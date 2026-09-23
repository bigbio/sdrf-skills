# Reference: validating an SDRF (review mode and Step 9 of sdrf-annotate)

## The command

```bash
parse_sdrf validate-sdrf -s <file.sdrf.tsv> -t <template1> [-t <template2> ...] [--use_ols_cache_only]
```

Several `-t` flags validate against their union. Add `--use_ols_cache_only` when offline;
`--skip-ontology` only for a fast structural pass. Collect every ERROR and WARNING.

## Step 0.5: Protect the Machine During Validation

Validation can be expensive because `parse_sdrf` may trigger ontology lookups,
template loading, and large file parsing. **Measured cost**: a single
`parse_sdrf validate-sdrf` run with full ontology validation peaks at **~1.9GB
RSS** (each `-t` template loads its own ontology data into memory). On a
16GB-class laptop, `xargs -P 16` (or any double-digit concurrency) demands
30GB+ of RAM and *will* thrash swap and hang the machine — this has caused
multiple full-machine restarts in practice. Do not guess at a safe
concurrency; measure it:

```bash
# Before any batch validation over more than ~10 files, check headroom:
sysctl hw.memsize                 # total RAM (macOS)
vm_stat | head -5                 # free pages (macOS); `free -h` on Linux
df -h / 2>&1                      # free disk — swap needs room too
```

Use these resource guards:

- Default to serial validation for autonomous loops unless there is a clear reason to parallelize
- If validating multiple SDRFs in parallel with full ontology checks, keep concurrency small: at most `2` `parse_sdrf` jobs at a time (≈3.8GB peak — leave the rest of RAM for the OS, IDE, browser)
- **Two-pass strategy for large batches (tens to thousands of files)**: first run every file with `--skip-ontology` (≈130MB RSS, ~15x lighter — safe at concurrency 8-16) to catch structural/required-column errors fast and cheap; fix those; only then run the full ontology pass, and only at concurrency ≤2. If the files will be validated by CI anyway (a repo's GitHub Actions workflow), consider skipping the local full-ontology pass entirely — push after the cheap structural pass and read the CI logs for the authoritative ontology-level result instead of reproducing that cost locally.
- If `techsdrf`, raw-file conversion, or other heavy IO/CPU work is running, validate only `1` SDRF at a time
- Validate changed datasets first, not the whole collection by default
- Prefer batch manifests or representative smoke checks before full-sandbox sweeps
- For large SDRFs, validate unique values once rather than re-checking repeated ontology terms row by row

If the machine looks stressed or validation becomes unresponsive, reduce concurrency before continuing. If disk free space is under ~10-20GB, treat any large download or batch-write operation (dataset downloads, raw-file conversion, bulk SDRF generation) as high-risk until space is freed — low disk space also constrains how much the OS can grow swap, which turns a memory spike into a full hang instead of graceful slowdown.

## Structural and consistency checks

Run the deterministic structural checks first — they decide from the file alone, so do not
re-reason about what they cover:

```bash
sdrf-tools structure <file.sdrf.tsv>
```

Exit 0 means clean; exit 1 lists one line per violated invariant. It catches things `parse_sdrf`
validates as correct: DDA and DIA rows in the same file, a `comment[sdrf template]` value that
changes from row to row, several templates packed into one cell instead of repeated columns, a
declared `dia-acquisition` template contradicted by a DDA acquisition value, factor value columns
that are not last, `not available` / `not applicable` in a column whose TERMS.tsv row forbids it
(omit the column instead), and the row-coordinate rules: technical replicates numbered 1..n within
a sample, a sample having as many data files as it claims replicates, and
(`source name`, biological replicate, technical replicate, fraction identifier) unique across rows.
It also flags `characteristics[...]` values written as an `NT=<label>;AC=<accession>` pair: a sample
property is the bare label (`colon`), or the identifier alone where the column is an accession
(`CVCL_0030`). The NT/AC form belongs to `comment[...]`. Structured sample properties keep their own
keys (`SN=` pooled sample, `CT=`/`QY=` spiked compound) and are not affected.
Fix every line it reports before working through the list below.

- [ ] All rows have the same number of columns (no ragged rows)
- [ ] Uniqueness: (`source name` + `assay name` + `comment[label]`) is unique (ERROR); (`source name` + `assay name`) unique (WARN); coordinate (`source name`, `characteristics[biological replicate]`, `comment[technical replicate]`, `comment[fraction identifier]`) unique across rows — no duplicate coordinates
- [ ] Value encoding by column type: `characteristics[...]` ontology values are the BARE label (flag a pure `NT=;AC=` pair); `comment[...]` CV values are `NT=<label>;AC=<accession>`; structured characteristics (`spiked compound` CT=/QY=, `pooled sample` SN=) keep key-value
- [ ] `comment[proteomics data acquisition method]` resolves to a descendant of `PRIDE:0000659`; reject `MS:1000206`/`MS:1003221`/`NCIT:C161786` and any `comment[dia method]` column
- [ ] NT/AC agreement: for each `NT=…;AC=…`, the accession's OLS label matches NT= (catches label/accession swaps beyond UNIMOD)
- [ ] `source name` values follow a consistent naming pattern
- [ ] `characteristics[biological replicate]` values are sequential integers
- [ ] `comment[fraction identifier]` values are consistent across samples
- [ ] Factor values match actual characteristics column values
- [ ] If TMT: correct number of rows per raw file (6 for TMT6, 10 for TMT10, 11 for TMT11, 16 for TMT16)
- [ ] If SILAC: 2-3 rows per raw file (light/medium/heavy)
- [ ] File names in `comment[data file]` are unique per assay name
- [ ] `technology type` is the same across all rows
- [ ] All `comment[modification parameters]` columns have the same value across all rows (modifications are experiment-wide, not per-sample)
- [ ] `comment[instrument]` should be consistent (or documented if multiple instruments used)
- [ ] `characteristics[sampling time]` uses the template pattern `number + unit` such as `0 day`, `8 day`, or `12 week` when time-course metadata is present
- [ ] `characteristics[depletion]` uses the controlled values `depletion` or `no depletion` rather than local variants like `depleted` or `yes`

## Reporting

Errors first, then warnings, then the checklist items that failed, each with row and column. Say
what ``sdrf-tools fix` (patterns: `fix-patterns.md`)` can repair deterministically and what needs the record. Do not fix
here. If the file is for a ProteomeXchange dataset and validates clean, the next step is review:
`/sdrf-skills:sdrf-annotate <file.sdrf.tsv>`.

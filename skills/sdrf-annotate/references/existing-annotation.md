# Reference: is the dataset already annotated? (Step 0.5 of sdrf-annotate)

Read when you have network access and a PXD accession. Skipped in offline mode.

## Step 0.5: Check whether the dataset is ALREADY annotated — STOP GATE

> **Offline mode (Step 0):** skip this step — the community repository is not reachable, so there is nothing to check against.


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

Use the same artifact set in `/sdrf-skills:sdrf-contribute` rather than recomputing it, so the
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

sdrf-tools audit-existing existing.sdrf.tsv --accession {PXD} \
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

> **Value encoding.** `characteristics[...]` values are written as the **bare ontology label**
> (e.g. `Homo sapiens`, not `NT=Homo sapiens;AC=NCBITaxon:9606`); only `comment[...]` values keep
> the `NT=;AC=` form. Structured characteristics (`spiked compound`, `pooled sample`) keep their
> key-value form. See [format-rules.md](format-rules.md) → *Value Encoding: characteristics vs comment*.

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

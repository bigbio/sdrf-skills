---
name: sdrf:contribute
description: Use when the user has a completed SDRF annotation for a ProteomeXchange dataset and wants to contribute it back to the community via a PR to sdrf-annotated-datasets.
user-invocable: true
argument-hint: "[PXD accession and SDRF file path]"
---

# SDRF Contribution Workflow

You are helping the user contribute an annotated SDRF file back to the community repository
(`bigbio/sdrf-annotated-datasets`). This is the final step after annotation, validation,
and review — closing the loop from "I annotated a dataset" to "the community can reuse it."

## Step 1: Check Prerequisites

### 1.1 Verify the PXD accession
- A ProteomeXchange accession (PXD######) must be provided
- If not provided, ask the user for it

### 1.2 Verify the SDRF content
- The SDRF must be available as a file on disk or from a previous annotation step
- If the user just finished `/sdrf:annotate`, the content is in the conversation
- Ask the user to confirm the file path or provide the content

### 1.3 Check if this is a new annotation or an update
Check if the PXD already exists in the community repository
(`bigbio/sdrf-annotated-datasets`):
```text
Look for: datasets/{PXD}/{PXD}.sdrf.tsv
```

You can check via the GitHub API without cloning:
```bash
gh api repos/bigbio/sdrf-annotated-datasets/contents/datasets/{PXD} \
  --silent && echo "exists" || echo "new"
```

Classify at the level of the **file you are about to write**, not the directory.
A PXD folder may legitimately hold several SDRFs with descriptive suffixes
(`PXD006430-tmt.sdrf.tsv` + `PXD006430-silac.sdrf.tsv`), so an existing folder
does not mean you are replacing anything:

```bash
gh api repos/bigbio/sdrf-annotated-datasets/contents/datasets/{PXD} \
  --jq '.[] | select(.name | endswith(".sdrf.tsv")) | .name' 2>/dev/null
```

- **New annotation**: your target filename is not in that listing → new
  contribution, even if the folder already exists. Name any sibling files in the
  PR so a reviewer can see how the sub-experiments divide.
- **Update**: your target filename IS in the listing → this **replaces a file
  someone else curated**, so it needs justification, not just a report.

For the update case, do not open the PR yet. Audit the file you are about to
replace, so the PR can say what was actually wrong with it. Abort on a failed
fetch rather than auditing a truncated or error-page file:

```bash
set -euo pipefail
url=$(gh api "repos/bigbio/sdrf-annotated-datasets/contents/datasets/{PXD}/{FILE}" --jq .download_url)
[ -n "$url" ] || { echo "could not resolve download URL — abort"; exit 1; }
curl -fsSL "$url" -o existing.sdrf.tsv
[ -s existing.sdrf.tsv ] || { echo "empty download — abort"; exit 1; }

python -m tools audit-existing existing.sdrf.tsv --accession {PXD} \
  --runs deposited_runs.txt --organism "<each organism PRIDE registers>"
```

Then:

- **The audit is clean and your version is merely different** → say so and ask the
  user whether to proceed. Replacing a correct annotation with an equivalent one
  costs reviewer time and can regress hand curation. Style-only changes are rarely
  worth a PR on their own.
- **The audit found defects** → proceed, and make the PR body lead with them:
  each defect, the evidence from the deposit, and what the new file does instead.
  A reviewer must be able to check the claim rather than trust it.

If `/sdrf:annotate` already ran its Step 0.5 gate for this accession, reuse that
audit instead of repeating it, and confirm the user chose `fix` or `reannotate`.
**Never open a PR that silently overwrites an existing annotation.**

## Step 2: Validate Before Contributing

Before contributing, the SDRF must pass validation:

1. **Suggest programmatic validation**:
   ```bash
   pip install sdrf-pipelines
   parse_sdrf validate-sdrf --sdrf_file {PXD}.sdrf.tsv
   ```

2. **Run `/sdrf:validate`** for a thorough check including ontology verification

3. **Require independent adversarial approval**:
   ```bash
   python3 <sdrf-skills-root>/tools/review_gate.py gate
   ```
   If the artifact is pending, dispatch a fresh reviewer using
   `skills/sdrf-adversarial-review/SKILL.md`. The contributing/producer context
   must not create its own approval receipt. Any edit after approval requires a
   new review.

4. **Check file structure**:
   - All rows have the same number of columns (no ragged rows)
   - No trailing whitespace in column names or values
   - File is valid TSV (tab-delimited)
   - File extension is `.sdrf.tsv`

Do NOT proceed to contribution if there are validation errors.
Warnings are acceptable — mention them but allow the user to proceed.

## Step 3: Prepare the File

### 3.1 File naming convention
The community repository (`bigbio/sdrf-annotated-datasets`) uses this structure:
```text
datasets/
└── {PXD}/
    └── {PXD}.sdrf.tsv
```

For datasets with multiple sub-experiments:
```text
datasets/
└── {PXD}/
    ├── {PXD}-celllines.sdrf.tsv
    └── {PXD}-tissues.sdrf.tsv
```

### 3.2 Save the file
Save the SDRF content to the correct path:
```text
{PXD}/{PXD}.sdrf.tsv
```

Ensure the file:
- Uses tab delimiters (not spaces or commas)
- Has a single trailing newline at the end
- Has no BOM (byte order mark)
- Uses Unix line endings (LF, not CRLF)

## Step 4: Contribute

Ask the user which mode they prefer:

### Mode A — Automated (recommended if `gh` CLI is available)

Execute the full contribution flow:

```bash
# 1. Fork the repository (if not already forked)
gh repo fork bigbio/sdrf-annotated-datasets --clone=false

# 2. Clone the user's fork
gh repo clone {username}/sdrf-annotated-datasets /tmp/sdrf-annotated-datasets
cd /tmp/sdrf-annotated-datasets

# 3. Create a branch
git checkout -b annotation/{PXD}

# 4. Create the directory and copy the file
mkdir -p datasets/{PXD}
cp {source_path}/{PXD}.sdrf.tsv datasets/{PXD}/

# 5. Commit
git add datasets/{PXD}/
git commit -m "Add SDRF annotation for {PXD}"

# 6. Push
git push -u origin annotation/{PXD}

# 7. Create the PR
gh pr create \
  --repo bigbio/sdrf-annotated-datasets \
  --title "Add SDRF annotation for {PXD}" \
  --body "$(cat <<'EOF'
## Add SDRF annotation for {PXD}

**Dataset**: [{PXD}](https://www.ebi.ac.uk/pride/archive/projects/{PXD})
**Organism**: {organism}
**Templates**: {template_list}
**Rows**: {row_count} | **Columns**: {col_count}
**Factor values**: {factor_description}

### Validation
- [x] Validated with `sdrf-pipelines validate-sdrf`
- [x] Ontology terms verified via OLS

### Annotation source
Annotated using [sdrf-skills](https://github.com/bigbio/sdrf-skills).
EOF
)"
```

Before executing, present the full plan to the user and ask for confirmation.
Fill in the template variables from the SDRF content:
- `{organism}`: from `characteristics[organism]` unique values
- `{template_list}`: from `comment[sdrf template]` columns
- `{row_count}`: number of data rows (excluding header)
- `{col_count}`: number of columns
- `{factor_description}`: from `factor value[...]` column names and unique values

### Mode B — Guided (show commands for the user to run)

Present the same sequence of commands as Mode A, but as a copyable code block
with all variables already filled in. The user copies and executes them.

Preface with:
```text
Here are the commands to contribute your SDRF annotation to the community repository.
Copy and run them in your terminal:
```

### For updates to existing annotations

If the PXD already exists, adjust:
- PR title: `Update SDRF annotation for {PXD}`
- Commit message: `Update SDRF annotation for {PXD}`
- PR body: add a "Changes" section explaining what was updated
- Branch name: `annotation/{PXD}-update`

## Step 5: Post-Contribution

After the PR is created:

1. **Show the PR URL** so the user can track it
2. **Explain the review process**:
   - Community reviewers will check the annotation for correctness
   - Automated CI will run `sdrf-pipelines validate-sdrf` on the PR
   - Reviewers may request changes (more specific ontology terms, missing columns, etc.)
   - Once approved, the annotation is merged and available to the community
3. **Thank the user** for contributing to the community annotation effort
4. **Mention impact**: The annotation will be available in PRIDE's SDRF Explorer and
   usable by analysis pipelines (quantms, sdrf-pipelines) for automated reprocessing

## Important Rules

- NEVER create a PR without user confirmation
- NEVER skip validation before contributing
- NEVER modify the SDRF content during the contribution step (that's what `/sdrf:fix` and `/sdrf:improve` are for)
- If the user doesn't have `gh` CLI installed, always fall back to Mode B (guided commands)
- If the user doesn't have a GitHub account, explain that one is needed and point to https://github.com/signup
- For non-PXD accessions (MSV, PMID), the same workflow applies — just use the accession as the folder name

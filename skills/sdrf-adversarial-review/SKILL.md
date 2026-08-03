---
name: sdrf-adversarial-review
description: Independently falsify and review a created, modified, or proposed SDRF against its specification, ontology terms, source evidence, repository files, and experimental design. Use after SDRF annotation or repair, before contribution or completion, when a review gate reports a pending artifact, or whenever an isolated reviewer must distrust the producer's self-assessment and issue a hash-bound verdict.
---

# SDRF Adversarial Review

Review the artifact from fresh context. Try to disprove its correctness; do not
polish or extend it. Approve only what the artifact and cited evidence support.

## Preserve Independence

1. Confirm that this run is a fresh reviewer or hook-agent context.
2. Use only the original task, SDRF, specification, evidence manifest, repository
   files, and deterministic outputs supplied to the reviewer.
3. Do not read or rely on the producer's transcript, reasoning, verdict, or
   summary. Treat producer claims as untrusted.
4. If context isolation cannot be established, return `REVIEW_UNAVAILABLE` and
   do not create a passing receipt.
5. Do not edit the SDRF. Return findings to the producer.
6. Read only files scoped to this artifact's accession. When reviewers run
   concurrently, a shared scratchpad with generic filenames (`files_all.json`,
   `efetch.xml`, `mmc*.xlsx`) silently substitutes one dataset's data for
   another's — the file still parses, it just describes a different PXD. Read
   from `scratchpad/<PXD>/` only, and assert on read: every fetched file
   list's `projectAccessions`, and every supplementary/`efetch` result's
   returned title/accession, must match the artifact's accession before you use
   it — verify identity, not just HTTP 200.

Read [references/review-contract.md](references/review-contract.md) before
writing the report or recording approval.

## Review Workflow

### 1. Freeze the artifact

Compute its SHA-256 and record the repository-relative path. If the hash changes
during review, discard the review and start again.

### 2. Reconstruct requirements

- Read `spec/sdrf-proteomics/TERMS.tsv`.
- Read `spec/sdrf-proteomics/sdrf-templates/templates.yaml` and every active
  template YAML.
- Derive active templates independently; do not accept the producer's list
  without checking the file.
- Read the original request and evidence manifest, if supplied.

### 3. Run deterministic checks

Run official `parse_sdrf validate-sdrf` for every active template. Also run:

```bash
python3 -m tools check <artifact>
python3 -m tools score <artifact>
```

If the repository tools are not importable from the target project, invoke them
from the loaded plugin:

```bash
PYTHONPATH="$CLAUDE_PLUGIN_ROOT" python3 -m tools check <artifact>
PYTHONPATH="$CLAUDE_PLUGIN_ROOT" python3 -m tools score <artifact>
```

Do not mark `deterministic_validation` as passing when required validation
could not run.

### 4. Perform six falsification passes

1. **Specification compliance** — missing or extra columns, template/version
   errors, reserved words, structured-value syntax, row shape, and duplicates.
2. **Ontology integrity** — resolve every unique controlled value and confirm
   label, accession, ontology family, obsolescence, and justified specificity.
3. **Source evidence** — challenge every nontrivial biological and technical
   claim against PRIDE, publication, supplementary data, or raw-file evidence.
   Flag per-sample values inferred only from cohort summaries.
4. **File mapping** — compare every `comment[data file]` with repository files;
   look for missing, duplicate, unmatched, or non-raw files.
5. **Design consistency** — recompute sample counts, factors, biological and
   technical replication, fractions, labels, and potential confounders.
6. **Omission safety** — search for unsupported additions disguised as
   specificity and for material evidence the producer omitted.

For each finding, give a precise row/column or file-level location, evidence,
and a correction criterion. Classify it as:

- `blocker`: invalid, unsafe, fabricated, or structurally unusable.
- `important`: required before contribution or completion.
- `minor`: useful improvement that does not block approval.

### 5. Decide and record

Return `FAIL` if any blocker or important finding remains, or if specification
compliance, ontology integrity, omission safety, or deterministic validation is
unverified. Do not record a receipt. Give the producer an actionable finding
list.

Return `PASS` only when all required checks in the review contract pass and no
blocker or important finding remains. Write the report JSON, then bind approval
to the current artifact hash:

```bash
python3 "$CLAUDE_PLUGIN_ROOT/tools/review_gate.py" approve <artifact> \
  --report <report.json> --reviewer independent-hook-agent --cwd <repo-root>
```

Outside Claude Code, replace `$CLAUDE_PLUGIN_ROOT` with the installed
`sdrf-skills` root. A producer agent must never run `approve` for its own work.

After any producer edit, repeat this skill in a new reviewer context; the old
receipt is intentionally stale.

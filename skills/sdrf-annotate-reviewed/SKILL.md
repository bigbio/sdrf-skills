---
name: sdrf-annotate-reviewed
description: Create or improve an SDRF through a producer-reviewer workflow with deterministic validation, an evidence manifest, fresh-context adversarial review, repair, and mandatory re-review. Use when an SDRF must be independently verified before completion or contribution, when the user requests adversarial review, or when automated review hooks require a passing hash-bound receipt.
---

# Reviewed SDRF Annotation

Orchestrate annotation and independent review. Keep producer and reviewer
contexts separate; validation by the producer is not review.

## 1. Produce the SDRF

Run the `sdrf:annotate` workflow in the current producer context. For an
existing artifact, run the applicable `sdrf:fix`, `sdrf:review`, or
`sdrf:techrefine` workflows first.

Create an evidence manifest using the schema in
`../sdrf-adversarial-review/references/review-contract.md`. Include exact source
URLs or local paths and map claims to SDRF columns or rows. Mark unavailable
evidence explicitly; do not invent citations.

## 2. Validate and mark pending

Run official template validation plus the repository's check and score tools.
Fix deterministic errors before requesting review. Track the final artifact:

```bash
python3 <sdrf-skills-root>/tools/review_gate.py track <artifact> --cwd <repo-root>
```

## 3. Dispatch an isolated reviewer

Use a fresh subagent, hook agent, or equivalent isolated context. Pass only:

- the original request and acceptance criteria;
- the repository-relative SDRF path;
- the evidence-manifest path;
- the specification root and pinned revision;
- deterministic validation outputs; and
- the path to `sdrf-adversarial-review/SKILL.md`.

Do not pass the producer transcript, reasoning, suspected issues, or proposed
verdict. Instruct the reviewer to use `sdrf-adversarial-review`, inspect raw
artifacts, and distrust producer assertions.

If the platform cannot create an isolated reviewer context, report that the
adversarial gate is unavailable. Do not substitute producer self-review and do
not claim a passing adversarial review.

## 4. Repair and re-review

When the reviewer returns blocker or important findings:

1. Let the producer evaluate each finding against code, specification, and
   evidence; push back only with concrete counter-evidence.
2. Apply accepted corrections.
3. Re-run deterministic validation.
4. Dispatch a new fresh reviewer. Never ask the original reviewer to rely on
   its previous verdict.

Escalate to the user after two failed review rounds or when resolution requires
scientific judgment not present in the evidence. Minor findings may remain only
when the review report explains why they do not block use or contribution.

## 5. Enforce the gate

Before completion, contribution, commit, or PR publication, run:

```bash
python3 <sdrf-skills-root>/tools/review_gate.py gate --cwd <repo-root>
```

Proceed only when it exits successfully and reports the current artifact hash
as approved. Report the reviewer identity, hash, validation commands, remaining
minor findings, and evidence limitations to the user.

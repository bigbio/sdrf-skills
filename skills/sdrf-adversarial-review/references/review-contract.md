# Adversarial Review Contract

Use one JSON report per SDRF. Store temporary reports outside the worktree when
possible; the gate copies the passing report into git-local state.

## Evidence manifest

```json
{
  "schema_version": 1,
  "artifact": "path/PXD000001.sdrf.tsv",
  "dataset": "PXD000001",
  "sources": [
    {"id": "pride", "kind": "repository", "location": "https://..."},
    {"id": "paper", "kind": "publication", "location": "PMC..."}
  ],
  "claims": [
    {
      "location": "characteristics[organism] rows 1-12",
      "value": "Homo sapiens",
      "source_ids": ["pride", "paper"],
      "evidence": "Exact organism in project record and Methods"
    }
  ],
  "limitations": ["No sample-level age table was available"]
}
```

The manifest is provenance, not proof. Re-open cited sources and check that
they support the stated granularity.

## Passing report

```json
{
  "schema_version": 1,
  "artifact": "path/PXD000001.sdrf.tsv",
  "artifact_sha256": "sha256-of-the-content-you-reviewed",
  "verdict": "PASS",
  "summary": "Independent review found no blocking or important issues.",
  "reviewer_context": {
    "independent": true,
    "context": "fresh hook agent without producer transcript"
  },
  "evidence_manifest": "path/PXD000001.evidence.json",
  "checks": {
    "spec_compliance": {"status": "pass", "evidence": "Template validator passed ..."},
    "ontology_integrity": {"status": "pass", "evidence": "Unique controlled terms resolved ..."},
    "source_evidence": {"status": "pass", "evidence": "Claims checked against ..."},
    "file_mapping": {"status": "pass", "evidence": "All 24 raw files matched ..."},
    "design_consistency": {"status": "pass", "evidence": "Counts and factors recomputed ..."},
    "omission_safety": {"status": "pass", "evidence": "Every value traced to a cited source ..."},
    "deterministic_validation": {"status": "pass", "evidence": "Commands and exit codes ..."}
  },
  "findings": [
    {
      "severity": "minor",
      "category": "provenance",
      "location": "file",
      "message": "Optional annotation-tool provenance is absent.",
      "evidence": "The active template marks this column optional."
    }
  ]
}
```

`artifact_sha256` is required and must be the hash you froze in step 1 of the
review, not a hash recomputed at approval time. The gate rejects the report when
it does not match the artifact on disk: that mismatch means the content changed
after you read it, so the review no longer describes what would be approved.

Allowed finding severities are `blocker`, `important`, and `minor`. A passing
report may contain minor findings only. Every required check needs concrete
evidence; `source_evidence`, `file_mapping`, and `design_consistency` may use
`not_applicable` with an explanation. Specification compliance, ontology
integrity, omission safety, and deterministic validation must pass.

`omission_safety` has no `not_applicable` status: an SDRF can always be checked
for values that assert more than the cited evidence supports. If you could not
perform that pass, the verdict is `FAIL`, not a passing report with the check
left out.

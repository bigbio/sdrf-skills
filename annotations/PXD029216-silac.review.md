# PXD029216 — independent adversarial review of `PXD029216-silac.sdrf.tsv`

- Artifact: `annotations/PXD029216-silac.sdrf.tsv`
- artifact_sha256: `e8261f172b968b90753374802a00d7f24569318b6184bc68938d23bb8ef11c20` (frozen at start and re-checked at the end)
- Manifest: `annotations/PXD029216-silac.evidence.json` (sha256 ccc1361e…)
- **Verdict: FAIL** (1 important, 0 blocker, 3 minor)
- Context: a fresh reviewer. I did not read `PXD029216.report.md`, the earlier SILAC review sections or the producer's reasoning. The TMT file is out of scope.

## What I verified independently

- **Deterministic checks**
  - `parse_sdrf validate-sdrf` exits 0 for all four templates. The only warnings are free-text phenotype values.
  - `sdrf-tools check` reports CLEAN (15/15). Score is 100. `structure` passes. Manifest `schema-check` and `manifest-coverage` pass.
  - `reconcile` exits 1 on two items, and both are false positives:
    - Trypsin is the MaxQuant search enzyme (Specific).
    - The flagged "untreated" refers to treatment-naive patients. It is not a control arm.
- **File mapping:** I re-fetched PRIDE `files/all` (642 entries, all PXD029216).
  - Of the 228 SILAC raws, 222 are annotated. The 6 left out are `AML1036_*`, which BLOCKED.md documents.
  - All 216 searched files are in `summary_new.txt` (Multiplicity 2, Labels1 Arg10;Lys8). The 6 `AML1027_R2` files are not in the search and correctly carry tolerance `not applicable`.
- **Values from the label key:** I re-downloaded the label key (byte-identical to the producer's copy) and checked all 444 rows by script against its SILAC sheet. These columns all match, with 0 mismatches:
  - source name, individual, organism part, phenotype (Blast IP), genotype and factor value, raw pattern and fraction.
  - Developmental stage `adult` appears only on the 10 individuals whose NPM1-sheet Age_Group is Adult.
- **Label direction:** confirmed from `proteinGroups_new.txt`. Light holds the patient and heavy holds the reference.
  - HBB intensity is much higher in light than in heavy in all 38 experiments.
  - Light CD34 follows the Blast IP: it is low for CD117+ and double-negative patients and high for CD34+ patients.
  - Heavy CD34 is roughly constant across mixes.
- **Instrument settings:** 3 raw headers checked: Orbitrap Fusion, HCD 27%, ion-trap MS2, data-dependent acquisition.
- **Ontology terms:** all resolved in OLS4, none obsolete. UNIMOD 267 and 259 match Arg10 and Lys8.
- **Heavy reference composition:** Europe PMC finds only one paper citing the dataset. Its references 14 and 19 do not describe the SILAC standard, so the composition really is unreported.

## Findings

### IMPORTANT 1: biological replicate collapses independent patients
- **Location:** `characteristics[biological replicate]`, all 222 light rows (37 patient sources).
- **Evidence:** every patient has the value `1`. The factor value[genotype] groups contain 19, 8, 5, 4 and 1 different patients, all numbered 1.
  - spec `sdrf-proteomics/README.adoc:330`: "Numbering restarts per experimental condition (factor value group)". Its example numbers patient_001 = 1 and patient_002 = 2.
  - Campaign rule 3 requires unique numbers per independent sample within a group.
  - The curated precedent the producer cites, `PXD003822-freshfrozen-silac`, numbers its patients 1..4.
- **Fix:** in the build tables, number the light sources 1..n within each `factor value[genotype]` group in a deterministic order (for example by patient ID). Then rebuild and log the change in validation.txt.
- **Note for the caller:** `PXD029216-tmt.sdrf.tsv` uses the same all-1 pattern. That file is outside this review's scope.

### Minor findings
1. Heavy rows use one source per mix (37 sources), an assumption the manifest states. The precedent PXD003822 uses a single `super-SILAC spike-in standard` source with biological replicate `pooled`. Consider using one shared reference source.
2. `characteristics[treatment status]` is `not available` on the light rows. The PRIDE protocol says all specimens come from previously untreated de novo patients, which is an inclusion criterion, so `untreated` would be defensible. This change is optional.
3. The manifest's `artifact` field is an absolute path, not a repository-relative one.

## Report JSON (schema-checked: valid review-report)

```json
{
  "schema_version": 1,
  "artifact": "annotations/PXD029216-silac.sdrf.tsv",
  "artifact_sha256": "e8261f172b968b90753374802a00d7f24569318b6184bc68938d23bb8ef11c20",
  "verdict": "FAIL",
  "summary": "Fresh independent review of the SILAC SDRF (222 raws x light/heavy = 444 rows, 37 patients). Validators, structure, ontology, file mapping, label direction and every label-key-derived value re-verified and correct. One IMPORTANT design defect: characteristics[biological replicate] = 1 for all 37 independent patients, so every genotype group of 4-19 patients collapses to a single replicate, contrary to spec README.adoc:330 (numbering per factor-value group, patient_001=1, patient_002=2), campaign rule 3 and the cited curated precedent PXD003822.",
  "reviewer_context": {
    "independent": true,
    "context": "fresh subagent; did not read PXD029216.report.md, the SILAC sections of PXD029216.review.md, producer transcripts or scratch reasoning; re-fetched PRIDE files/all, label key .xls and AML_SWOG_1st MaxQuant tables (byte-identical to producer copies) and 3 raw headers"
  },
  "evidence_manifest": "annotations/PXD029216-silac.evidence.json",
  "checks": {
    "spec_compliance": {"status": "pass", "evidence": "parse_sdrf validate-sdrf: ms-proteomics exit 0, human exit 0, clinical-metadata and oncology-metadata exit 0 with only free-text characteristics[phenotype] warnings (TERMS.tsv allows free text). sdrf-tools structure OK. Template versions match upstream 7da1747 templates.yaml (ms-proteomics 1.2.0 l.150, human 1.1.0, clinical-metadata 1.0.0, oncology-metadata 1.0.0); sdrf version v1.1.0; annotation tool per rule 10. 74 sources, each internally consistent; no duplicate (file,label) pair."},
    "ontology_integrity": {"status": "pass", "evidence": "sdrf-tools check 15/15 verified CLEAN; OLS4 re-resolved CL:0001064 malignant cell, MONDO:0018874, EFO:0001272 adult, UBERON:0002371 bone marrow, UBERON:0000178 blood, CL:0000000 cell, MS:1002416, MS:1000291, MS:1000422 (none obsolete). UNIMOD 4/35/267 (Arg10)/259 (Lys8) match MaxQuant Labels1 Arg10;Lys8."},
    "source_evidence": {"status": "pass", "evidence": "Label key SILAC sheet (fresh download, byte-identical) vs every row by script: source name, individual, organism part (BM->bone marrow, PB/Apheresis->blood, AML1027 conflict BM vs BLD -> not available), phenotype (Blast IP), genotype and factor value (FLT3-ITD/NPM1), raw pattern and fraction: 0 mismatches. Developmental stage adult only on the 10 individuals with NPM1-sheet Age_Group Adult (verified). No SILAC patient in Table S13 per manifest; no age/sex asserted. Label direction independently confirmed in proteinGroups_new.txt: HBB L>>H in all 38 experiments and light CD34 tracks Blast IP (low in CD117+/DN patients, high in CD34+), heavy CD34 roughly constant -> patient=light, reference=heavy. Raw headers (3 spot-checked) Orbitrap Fusion, HCD 27%, IT MS2. Europe PMC: only one paper cites PXD029216; refs 14/19 do not describe the SILAC standard -> heavy composition genuinely unreported."},
    "file_mapping": {"status": "pass", "evidence": "PRIDE files/all (642 entries, all PXD029216): 228 _2D_ SILAC raws; SDRF covers 222, the 6 omitted are AML1036_Blast_BLD_2D_F01-F06 documented in BLOCKED.md. No SDRF file absent from PRIDE. All 216 searched files are in summary_new.txt with tolerances not available/0.5 Da; the 6 AML1027_R2 files are not in the search and carry not applicable (rule 5)."},
    "design_consistency": {"status": "fail", "evidence": "characteristics[biological replicate] = 1 for all 37 patient sources: factor value[genotype] groups hold 19/8/5/4/1 different patients each numbered 1 (script count). Spec README.adoc:327-341 and rule 3 require distinct numbers per independent sample within a factor-value group."},
    "omission_safety": {"status": "pass", "evidence": "No clinical value copied from cohort summaries; heavy rows assert no cell line, disease or individual; AML1036 and AML1027 organism-part conflicts left out / not available; limitations disclose heavy-source encoding assumption, renamed raws and AML1019 F06 empty run."},
    "deterministic_validation": {"status": "pass", "evidence": "validate-sdrf x4 exit 0; sdrf-tools check exit 0 CLEAN; score 100/100; structure exit 0; schema-check manifest valid; manifest-coverage 25/25. reconcile exit 1: cleavage_agent_unsupported and disease_with_control_arm_in_record, both refuted (search Enzyme Trypsin/Specific; 'untreated' = treatment-naive patients, not a control arm)."}
  },
  "findings": [
    {"severity": "important", "category": "design", "location": "characteristics[biological replicate], all 222 SILAC light rows (37 patient sources)", "message": "Every patient is biological replicate 1, so each genotype group (19, 8, 5, 4, 1 patients) is encoded as a single replicate.", "evidence": "spec/sdrf-proteomics/README.adoc:330 'Numbering restarts per experimental condition (factor value group)' with example patient_001=1, patient_002=2; campaign rule 3 'must be unique per independent culture within the group'; cited curated precedent PXD003822-freshfrozen-silac numbers patients 1..4. Fix: in the build tables, number light sources 1..n within each factor value[genotype] group (deterministic order, e.g. patient ID), rebuild, record in validation.txt."},
    {"severity": "minor", "category": "design", "location": "SILAC heavy rows (37 sources 'SILAC heavy reference standard (spiked into ...)')", "message": "One heavy source per mix is an acknowledged assumption; curated precedent PXD003822 uses one 'super-SILAC spike-in standard' source with biological replicate 'pooled'.", "evidence": "Manifest limitation; heavy CD34 intensity roughly constant across mixes. Consider one shared reference source, or keep with the limitation."},
    {"severity": "minor", "category": "source-evidence", "location": "characteristics[treatment status] light rows", "message": "'not available' is conservative; PRIDE protocol states all specimens are from previously untreated de novo patients (inclusion criterion), which could license 'untreated'.", "evidence": "PRIDE sampleProcessingProtocol. Optional."},
    {"severity": "minor", "category": "provenance", "location": "PXD029216-silac.evidence.json artifact", "message": "Manifest artifact path is absolute rather than repository-relative.", "evidence": "\"artifact\": \"/home/user/bigbio/sdrf-skills/annotations/PXD029216-silac.sdrf.tsv\""}
  ]
}
```

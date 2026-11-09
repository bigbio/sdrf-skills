# Independent adversarial review — annotations/PXD029216-silac.sdrf.tsv

- **Verdict:** PASS
- **artifact_sha256:** `4a1eb51359176f21a75987e17b4e9c37f6a343ffe97c70644a5ef07e3ca0d449` (frozen at start; unchanged at end)
- **Evidence manifest:** `annotations/PXD029216-silac.evidence.json`
- **Reviewer context:** fresh subagent reviewer; did not read PXD029216.report.md, any prior PXD029216*.review.md, producer transcripts or scratch dirs; all sources re-fetched into scratchpad/rev-PXD029216
- **Reviewer scratch:** `/tmp/claude-0/-home-user/a98b4c07-45f2-5d08-aa74-0c95b1e5e538/scratchpad/rev-PXD029216/` (label key, Table S13, Supplemental Methods, PRIDE record/files, MaxQuant parameters/summary, raw-header ranges all re-fetched; check scripts `silac_check.py`, `tmt_check.py`, `tmt_dump.py`; logs in `val/`)

## Summary

SILAC arm (222 of 228 deposited raws, 37 patients, light = patient blasts, heavy Arg10/Lys8 = spike-in reference) re-derived from the deposited label key, MaxQuant AML_SWOG_1st output and raw headers; every light-row value matches the SILAC sheet, biological replicate numbering restarts per factor value[genotype] group and is unique per patient. Only minor findings.

## Checks

| check | status | evidence |
|---|---|---|
| spec_compliance | pass | parse_sdrf validate-sdrf -t ms-proteomics -t human -t clinical-metadata -t oncology-metadata exit 0 (warnings only: free-text characteristics[phenotype], allowed by TERMS.tsv 'PATO, EFO, free text'); sdrf-tools structure OK; 444 rows x 47 cols; no duplicate rows, (data file,label) unique; sdrf version v1.1.0, ms-proteomics v1.2.0 = upstream 7da1747 latest. |
| ontology_integrity | pass | OLS4 resolved live, none obsolete: MONDO:0018874, CL:0001064, EFO:0001272, UBERON:0002371/0000178, MS:1002416, MS:1000422, MS:1000291, MS:1001251, PRIDE:0000627; UNIMOD:267 = Label:13C(6)15N(4) (Arg10), UNIMOD:259 = Label:13C(6)15N(2) (Lys8), UNIMOD:4, UNIMOD:35. sdrf-tools check: 15/15 verified, CLEAN. |
| source_evidence | pass | Label key sheet SILAC (re-downloaded from PRIDE FTP): all 37 Sample IDs -> files, Blast IP -> phenotype, Source -> organism part (AML1027 BM vs BLD conflict -> not available, justified), FLT3-ITD/NPM1 -> genotype checked programmatically, 0 mismatches. MaxQuant AML_SWOG_1st summary_new.txt: Multiplicity 2, Labels1 Arg10;Lys8 (rule 14), Trypsin/Specific, Oxidation (M) variable; parameters.txt v1.5.3.30, Carbamidomethyl (C) fixed, ITMS 0.5 Da, no precursor tolerance -> not available is correct. Raw header AML1001 F01: Orbitrap Fusion, HCD 27%, MS2 IonTrap. Developmental stage adult only for the 10 individuals with NPM1-sheet Age_Group Adult (individual-level); no cohort values copied onto rows. |
| file_mapping | pass | PRIDE files/all (642 entries, all PXD029216): 228 SILAC raws; 222 annotated, each with one light and one heavy row; the 6 missing are AML1036_Blast_BLD_2D_F01-F06, listed in BLOCKED.md and manifest scope note. SDRF vs MaxQuant: only AML1027_R2 F01-F06 unsearched (tolerances not applicable, rule 5); fraction identifier = Fxx for every file. |
| design_consistency | pass | Light rows: factor value[genotype] groups of 19/8/5/4/1 patients numbered 1..19, 1..8, 1..5, 1..4, 1 with no duplicates and one number per patient (README.adoc:330, rule 3). Heavy rows: one 'not applicable' factor group, all 1 under the documented single-standard assumption (see minor finding). Technical replicate 1, fractions 1-6. |
| omission_safety | pass | No age/sex/treatment/clinical values asserted (none individual-level for SILAC patients); heavy composition not invented (not available, no cell lines named); AML1036 runs with conflicting identity left out rather than filled; precursor tolerance not available rather than borrowed 20 ppm. |
| deterministic_validation | pass | Reviewer re-ran: parse_sdrf validate-sdrf exit 0; sdrf-tools check exit 0 CLEAN; structure exit 0; score 100/100; schema-check + manifest-coverage OK; reconcile exit 1 with 2 false positives (Trypsin not named in PRIDE record - PRIDE says 'tryptic enzyme constraint', MaxQuant Enzyme Trypsin; 'untreated' matched 'previously untreated de novo AML patients', not a control arm). |

## Findings

1. **minor** (design) — rows with characteristics[sample type]=reference (222 heavy rows), source name / characteristics[biological replicate]: The heavy standard is encoded as 37 distinct source names ('SILAC heavy reference standard (spiked into <Sample ID>)') that all carry biological replicate 1 in the same factor group. Under the producer's own stated assumption (one standard material), 37 source names over-split one sample; if each mix had its own standard, 1 would be wrong.  
   Evidence: Manifest limitation 'Heavy reference encoding is an assumption'; curated precedent PXD003822-freshfrozen-silac uses a single source 'super-SILAC spike-in standard' (biological replicate pooled). No PXD029216 source states the standard's composition or batching.  
   Fix: Optional: use one source name (e.g. 'SILAC heavy reference standard') on all heavy rows so source identity agrees with biological replicate 1; keep the limitation.

2. **minor** (provenance) — rows of AML1019_Blast_BM_2D_F06.raw: File contributed no spectra (MaxQuant MS = 0, MS/MS = 0) but keeps fragment tolerance 0.5 Da as a searched file.  
   Evidence: AML_SWOG_1st summary_new.txt AML1019_Blast_BM_2D_F06 MS 0 MS/MS 0; documented in manifest limitations.  
   Fix: None required; documented.

## Biological replicate numbering (spec README.adoc:330, rule 3)

Recomputed from the file: light rows grouped by `factor value[genotype]` → FLT3-ITD−/NPM1− 19 patients (1..19), FLT3-ITD−/NPM1+ 8 (1..8), FLT3-ITD+/NPM1− 5 (1..5), FLT3-ITD+/NPM1+ 4 (1..4), FLT3-ITD not determined/NPM1− 1 (1). Every patient has exactly one number, no number repeats within a group, numbering restarts per group. Genotype per patient equals the label-key SILAC sheet for all 37. Heavy rows: single factor group (`not applicable`), all `1` — consistent with the documented one-standard assumption (minor finding 1).

## Deterministic outputs (reviewer re-run)

See `val/` in the reviewer scratch: validate-sdrf, check, structure, score, reconcile (2 false positives refuted in the checks table), schema-check, manifest-coverage.

## Report JSON (schema-checked: valid review-report)

```json
{
  "schema_version": 1,
  "artifact": "annotations/PXD029216-silac.sdrf.tsv",
  "artifact_sha256": "4a1eb51359176f21a75987e17b4e9c37f6a343ffe97c70644a5ef07e3ca0d449",
  "verdict": "PASS",
  "summary": "SILAC arm (222 of 228 deposited raws, 37 patients, light = patient blasts, heavy Arg10/Lys8 = spike-in reference) re-derived from the deposited label key, MaxQuant AML_SWOG_1st output and raw headers; every light-row value matches the SILAC sheet, biological replicate numbering restarts per factor value[genotype] group and is unique per patient. Only minor findings.",
  "reviewer_context": {
    "independent": true,
    "context": "fresh subagent reviewer; did not read PXD029216.report.md, any prior PXD029216*.review.md, producer transcripts or scratch dirs; all sources re-fetched into scratchpad/rev-PXD029216"
  },
  "evidence_manifest": "annotations/PXD029216-silac.evidence.json",
  "checks": {
    "spec_compliance": {
      "status": "pass",
      "evidence": "parse_sdrf validate-sdrf -t ms-proteomics -t human -t clinical-metadata -t oncology-metadata exit 0 (warnings only: free-text characteristics[phenotype], allowed by TERMS.tsv 'PATO, EFO, free text'); sdrf-tools structure OK; 444 rows x 47 cols; no duplicate rows, (data file,label) unique; sdrf version v1.1.0, ms-proteomics v1.2.0 = upstream 7da1747 latest."
    },
    "ontology_integrity": {
      "status": "pass",
      "evidence": "OLS4 resolved live, none obsolete: MONDO:0018874, CL:0001064, EFO:0001272, UBERON:0002371/0000178, MS:1002416, MS:1000422, MS:1000291, MS:1001251, PRIDE:0000627; UNIMOD:267 = Label:13C(6)15N(4) (Arg10), UNIMOD:259 = Label:13C(6)15N(2) (Lys8), UNIMOD:4, UNIMOD:35. sdrf-tools check: 15/15 verified, CLEAN."
    },
    "source_evidence": {
      "status": "pass",
      "evidence": "Label key sheet SILAC (re-downloaded from PRIDE FTP): all 37 Sample IDs -> files, Blast IP -> phenotype, Source -> organism part (AML1027 BM vs BLD conflict -> not available, justified), FLT3-ITD/NPM1 -> genotype checked programmatically, 0 mismatches. MaxQuant AML_SWOG_1st summary_new.txt: Multiplicity 2, Labels1 Arg10;Lys8 (rule 14), Trypsin/Specific, Oxidation (M) variable; parameters.txt v1.5.3.30, Carbamidomethyl (C) fixed, ITMS 0.5 Da, no precursor tolerance -> not available is correct. Raw header AML1001 F01: Orbitrap Fusion, HCD 27%, MS2 IonTrap. Developmental stage adult only for the 10 individuals with NPM1-sheet Age_Group Adult (individual-level); no cohort values copied onto rows."
    },
    "file_mapping": {
      "status": "pass",
      "evidence": "PRIDE files/all (642 entries, all PXD029216): 228 SILAC raws; 222 annotated, each with one light and one heavy row; the 6 missing are AML1036_Blast_BLD_2D_F01-F06, listed in BLOCKED.md and manifest scope note. SDRF vs MaxQuant: only AML1027_R2 F01-F06 unsearched (tolerances not applicable, rule 5); fraction identifier = Fxx for every file."
    },
    "design_consistency": {
      "status": "pass",
      "evidence": "Light rows: factor value[genotype] groups of 19/8/5/4/1 patients numbered 1..19, 1..8, 1..5, 1..4, 1 with no duplicates and one number per patient (README.adoc:330, rule 3). Heavy rows: one 'not applicable' factor group, all 1 under the documented single-standard assumption (see minor finding). Technical replicate 1, fractions 1-6."
    },
    "omission_safety": {
      "status": "pass",
      "evidence": "No age/sex/treatment/clinical values asserted (none individual-level for SILAC patients); heavy composition not invented (not available, no cell lines named); AML1036 runs with conflicting identity left out rather than filled; precursor tolerance not available rather than borrowed 20 ppm."
    },
    "deterministic_validation": {
      "status": "pass",
      "evidence": "Reviewer re-ran: parse_sdrf validate-sdrf exit 0; sdrf-tools check exit 0 CLEAN; structure exit 0; score 100/100; schema-check + manifest-coverage OK; reconcile exit 1 with 2 false positives (Trypsin not named in PRIDE record - PRIDE says 'tryptic enzyme constraint', MaxQuant Enzyme Trypsin; 'untreated' matched 'previously untreated de novo AML patients', not a control arm)."
    }
  },
  "findings": [
    {
      "severity": "minor",
      "category": "design",
      "location": "rows with characteristics[sample type]=reference (222 heavy rows), source name / characteristics[biological replicate]",
      "message": "The heavy standard is encoded as 37 distinct source names ('SILAC heavy reference standard (spiked into <Sample ID>)') that all carry biological replicate 1 in the same factor group. Under the producer's own stated assumption (one standard material), 37 source names over-split one sample; if each mix had its own standard, 1 would be wrong.",
      "evidence": "Manifest limitation 'Heavy reference encoding is an assumption'; curated precedent PXD003822-freshfrozen-silac uses a single source 'super-SILAC spike-in standard' (biological replicate pooled). No PXD029216 source states the standard's composition or batching.",
      "fix": "Optional: use one source name (e.g. 'SILAC heavy reference standard') on all heavy rows so source identity agrees with biological replicate 1; keep the limitation."
    },
    {
      "severity": "minor",
      "category": "provenance",
      "location": "rows of AML1019_Blast_BM_2D_F06.raw",
      "message": "File contributed no spectra (MaxQuant MS = 0, MS/MS = 0) but keeps fragment tolerance 0.5 Da as a searched file.",
      "evidence": "AML_SWOG_1st summary_new.txt AML1019_Blast_BM_2D_F06 MS 0 MS/MS 0; documented in manifest limitations.",
      "fix": "None required; documented."
    }
  ]
}
```

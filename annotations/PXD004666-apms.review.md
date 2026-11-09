# PXD004666 — independent adversarial review: PXD004666-apms.sdrf.tsv

- **Artifact:** `annotations/PXD004666-apms.sdrf.tsv` (HEK293T anti-FLAG AP-MS, SILAC Arg10/Lys8; Stroud et al., Nature 2016; search `combined-AP-MS.zip`)
- **artifact_sha256:** `c306b2963715a46df508a9c5237ee5b00f8b769e7088d0af0ab5a5db3148c962` (frozen at the start of the review, unchanged at the end)
- **Verdict: PASS** (3 minor findings, no blocker or important finding)
- **Scope:** only the AP-MS SDRF. The knockout SDRF already passed review and is out of scope.
- **Reviewer context:** a fresh subagent. It did not read the producer transcript, PXD004666.report.md or PXD004666.review.md. Sources were re-fetched into `scratchpad/rev-PXD004666/`.
- **Approval:** `review-gate approve` was not run, as the caller instructed.

## Deterministic checks (re-run by the reviewer)
| Command | Result |
|---|---|
| `parse_sdrf validate-sdrf -t ms-proteomics -t human -t cell-lines` (combined and per template) | exit 0. One warning: 'fetal stage' not in EFO. The value is HsapDv:0000037, a licensed ontology. |
| `sdrf-tools check` | exit 0, 14/14 verified, CLEAN |
| `sdrf-tools score` | 100/100 |
| `sdrf-tools structure` | OK |
| `sdrf-tools reconcile --record pride.json` | exit 0. One MINOR (cleavage agent not in PRIDE), refuted by summary.txt Enzyme Trypsin/P (batch rule 2). |
| `schema-check` manifest / `manifest-coverage` | valid / covers all 32 columns |

## Falsification passes
1. **Spec:** v1.1.0, with templates ms-proteomics v1.2.0, human v1.1.0 and cell-lines v1.1.0 (the latest at upstream 7da1747). affinity-proteomics is correctly not declared, since its scope is Olink/SomaScan. There are 30 rows = 15 files × 2 channels and no duplicates.
2. **Ontology:** every controlled term was resolved in OLS4, and none is obsolete. The UNIMOD accessions match Arg10 (267) and Lys8 (259). Cellosaurus CVCL_0063 was re-fetched: Female, Fetus, no population line.
3. **Source evidence:** combined-AP-MS.zip was re-read by HTTP range.
   - summary.txt and parameters.txt: Multiplicity 2, Arg10;Lys8, Trypsin/P, Carbamidomethyl fixed, Oxidation and Acetyl N-term variable, FTMS 20 ppm.
   - The raw headers of D, M and 27 give QE Plus, 375–1800 m/z, HCD NCE 27.
   - The paper legends were re-read: Ext Data 3a/3b/3d (NDUFAB1*-2, DOX-treated HEK293T, Triton X-100), 4d (NDUFV3 KO + NDUFV3Flag, TX/digitonin) and Fig. 4e (DMAC1Flag/ATP5SLFlag cells, background not stated).
   - The Supp Data headers S2–S4, S10 and S11 were re-read.
4. **File mapping:** the PRIDE v3 file list was re-fetched (491 entries, all PXD004666). It holds exactly 15 AP-MS RAW files, and all 15 are mapped. They match the experimentalDesignTemplate and summary.txt one-to-one, and none appears in the knockout SDRF.
5. **Design:** the channel map was checked three ways in all 15 runs, and the three agree every time:
   - the deposited tag;
   - the raw-header acquisition name (the tags are identical in all 15);
   - the bait log2 H/L (+3.12…+6.07 in the 10 HL runs, −3.61…−4.99 in the 5 LH runs).

   There are 8 conditions (genotype × detergent). Biological replicates are unique per culture within each group. Yeast ACP1 has 0 protein groups and 0 evidences in the anti-FLAG eluates, which supports the wild type (DOX-treated HEK293T) control for NDUFAB1-FLAG per the Ext Data 3d legend. The S2 'HEK293TACP1' header conflict is recorded in the manifest.
6. **Omission safety:** no knockout background is claimed for DMAC1 or ATP5SL. Detergent is 'not available' where no source states it, and DOX appears only where stated. Media and reagents are not guessed. The 4.5 ppm precursor tolerance is consistent with the data: the maximum non-MBR |mass error| is 4.485 ppm.

## Findings (minor only)
1. **Manifest, precursor claim:** the "max 5.56 ppm" for the 51 MULTI-MATCH evidences above 4.5 ppm should read **7.02 ppm** (evidence.txt `Mass Error [ppm]`). The conclusion is unchanged.
2. **characteristics[enrichment process]:** 'sample enrichment' is generic for anti-FLAG affinity purification. It matches curated precedent PXD023136.
3. **Manifest provenance:** the manifest could note that all 15 AP-MS raw-header acquisition names carry the same HL/LH tag as the deposited file names.

## Report JSON (schema-valid: `sdrf-tools schema-check` → valid review-report)
```json
{
  "schema_version": 1,
  "artifact": "annotations/PXD004666-apms.sdrf.tsv",
  "artifact_sha256": "c306b2963715a46df508a9c5237ee5b00f8b769e7088d0af0ab5a5db3148c962",
  "verdict": "PASS",
  "summary": "Independent review of the AP-MS SDRF (15 FLAG affinity-enrichment SILAC runs from combined-AP-MS.zip, 30 rows) found no blocker or important issues. Validators pass. Every channel->sample map agrees with the deposited tag, the raw-header acquisition name and the bait H/L sign. The only findings are minor manifest and specificity points.",
  "reviewer_context": {
    "independent": true,
    "context": "Fresh subagent context without the producer transcript, report or earlier review (PXD004666.report.md and PXD004666.review.md not read). Sources re-fetched independently into scratchpad/rev-PXD004666/."
  },
  "evidence_manifest": "annotations/PXD004666-apms.evidence.json",
  "checks": {
    "spec_compliance": {"status": "pass", "evidence": "parse_sdrf validate-sdrf -t ms-proteomics -t human -t cell-lines exit 0, and each template on its own exit 0. The only warning is 'fetal stage' not in EFO; it is HsapDv:0000037, which the cell-lines/human templates license. sdrf-tools structure OK. sdrf version v1.1.0; templates ms-proteomics v1.2.0, human v1.1.0, cell-lines v1.1.0, the latest in upstream 7da1747 templates.yaml. affinity-proteomics correctly not declared (scope Olink/SomaScan). 30 rows = 15 files x 2 channels, no duplicate (file, label) pairs. bait and detergent are custom characteristics."},
    "ontology_integrity": {"status": "pass", "evidence": "sdrf-tools check: 14/14 verified. Independent OLS4 lookups, none obsolete: BTO:0002181 HEK-293T cell, HsapDv:0000037 fetal stage, GO:0005739 mitochondrion, NCIT:C457 Doxycycline, UBERON:0002113 kidney, PATO:0000461 normal, EFO:0009106 sample enrichment, PRIDE:0000627, MS:1002634 Q Exactive Plus, MS:1000422 beam-type CID, MS:1000484 orbitrap, MS:1001251 Trypsin. UNIMOD 4/35/1/267 (Arg10)/259 (Lys8) match the stated mass shifts. Cellosaurus CVCL_0063 re-fetched: Female, AG Fetus, no population line (so ancestry is correctly 'not available')."},
    "source_evidence": {"status": "pass", "evidence": "Re-fetched combined-AP-MS.zip members by HTTP range. summary.txt: 15 files, Multiplicity 2, Labels0 empty, Labels1 Arg10;Lys8, Trypsin/P Specific, 2 missed cleavages, variable Oxidation (M);Acetyl (Protein N-term). parameters.txt: MaxQuant 1.5.4.1, fixed Carbamidomethyl (C), FTMS MS/MS tol 20 ppm, ACP1.fasta + HUMAN.fasta. evidence.txt: every non-MBR evidence has |mass error| <= 4.485 ppm, consistent with the 4.5 ppm default. Raw headers of 3 files (D, M, 27): Q Exactive Plus, scan range 375-1800 m/z, HCD NCE 27, Top12. Article page legends re-read: Ext Data Fig. 3d 'DOX-treated HEK293T or NDUFAB1Flag (NDUFAB1*-2) cells ... Triton X-100'; 3a/3b NDUFAB1*-2 = NDUFAB1 knockout complemented with NDUFAB1*Flag; 4d 'NDUFV3-knockout cells complemented with NDUFV3Flag ... Triton X-100 or digitonin'; Fig. 4e 'DMAC1Flag or ATP5SLFlag cells' (no background stated). Supplementary Data re-downloaded: S3/S4/S10/S11 headers '<bait>FLAG/HEK293T' with Expt.1-2 H/L and Expt.3 L/H; S2 'NDUFAB1FLAG/HEK293TACP1'."},
    "file_mapping": {"status": "pass", "evidence": "PRIDE v3 file list re-fetched (491 entries, all projectAccessions contain PXD004666): exactly 15 FLAG/P1DAS AP-MS RAW files. Each appears in the SDRF twice (heavy and light), matches the experimentalDesignTemplate and summary.txt of combined-AP-MS.zip one-to-one, and none appears in PXD004666-knockout.sdrf.tsv. All 15 returned HTTP 206 on range read."},
    "design_consistency": {"status": "pass", "evidence": "Channel map checked three ways for all 15 runs. (1) The deposited HL/LH tag. (2) The raw-header acquisition names (e.g. P1DAS20160419_7_NDUFV3-FLAG_DIG_HL for M, ..._HL_A for D): the tags are identical in all 15. (3) proteinGroups bait log2 H/L normalized: +3.12 to +6.07 in all 10 HL runs and -3.61 to -4.99 in all 5 LH runs (TMEM261/DMAC1, ATP5SL, NDUFV3, NDUFAB1). FLAG cells = heavy for HL, as encoded. Factors genotype x detergent give 8 conditions. Biological replicates are unique per culture within each (genotype, detergent) group: the wild type / not available group is 1-6 (DMAC1 then ATP5SL controls), wild type / Triton X-100 is 1-6 (NDUFV3-TX then NDUFAB1 controls), and the bait groups are 1-3. Yeast ACP1 P32463 has 0 rows in proteinGroups and 0 in evidence of the anti-FLAG eluates, which supports encoding the NDUFAB1 control as DOX-treated wild type (per the Ext Data 3d legend) despite the S2 header; the conflict is recorded in the manifest limitations."},
    "omission_safety": {"status": "pass", "evidence": "No knockout background is asserted for DMAC1-FLAG/ATP5SL-FLAG, because Fig. 4e does not state one. Detergent is 'not available' where no file name or legend states it. Doxycycline is applied only to the NDUFAB1 experiment, whose legend states it. Culture medium, cell type, age, passage and storage temperature are 'not available', with no guessed reagent. Lys-C is not asserted. The 4.5 ppm precursor tolerance rests on the PRIDE 'default parameters' statement and is consistent with the evidence.txt mass errors. Out-of-scope ACPOE runs belong to the knockout search, not to this file."},
    "deterministic_validation": {"status": "pass", "evidence": "Re-run by the reviewer: parse_sdrf validate-sdrf (combined + per template) exit 0; sdrf-tools check exit 0 CLEAN; score 100/100 exit 0; structure exit 0; reconcile exit 0 (one MINOR cleavage_agent_unsupported, refuted by summary.txt Enzyme Trypsin/P per batch rule 2); schema-check of the manifest valid; manifest-coverage covers all 32 columns."}
  },
  "findings": [
    {"severity": "minor", "category": "provenance", "location": "PXD004666-apms.evidence.json claim comment[precursor mass tolerance]", "message": "The manifest gives the maximum |Mass Error| of the 51 MULTI-MATCH evidences above 4.5 ppm as 5.56 ppm. The reviewer recomputes 7.02 ppm from combined-AP-MS.zip txt/evidence.txt.", "evidence": "evidence.txt 'Mass Error [ppm]': 88,983 rows, 51 above 4.5 ppm (all MULTI-MATCH), max 7.0235. The maximum for non-MBR evidences is 4.4848. The conclusion is unchanged; correct the number."},
    {"severity": "minor", "category": "specificity", "location": "characteristics[enrichment process] all rows", "message": "'sample enrichment' (EFO:0009106) is generic for anti-FLAG affinity purification. A more specific term could be used if one exists, with the method kept in the custom bait column.", "evidence": "Curated precedent PXD023136 uses the same generic term, so this does not block."},
    {"severity": "minor", "category": "provenance", "location": "raw-file evidence", "message": "The manifest could record that all 15 AP-MS acquisition names (raw headers) carry the same HL/LH tag as the deposited names. In this archive the acquisition tag has contradicted the deposited one elsewhere (V-227, T-215, O-173).", "evidence": "Reviewer read the first 400 kB of all 15 RAW files: e.g. D -> P1DAS20151006-TMEM261-FLAG_HL_A.raw, G -> P1DAS20160419_1_ATP5SL-FLAG_HL.raw, O -> P1DAS20160419_9_NDUFV3-FLAG_DIG_LH_...raw. All tags match."}
  ]
}
```

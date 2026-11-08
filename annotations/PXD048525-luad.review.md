# PXD048525-luad — independent adversarial review (round 2)

Reviewer: a separate subagent with fresh context, following `skills/sdrf-adversarial-review` and `references/review-contract.md`.

What I did not use:
- the producer transcript;
- `PXD048525.report.md`;
- the producer's scratch evidence;
- the round-1 review, except to check whether its L1 finding was resolved.

Every source was fetched again into `scratchpad/review2-PXD048525/` and checked for identity: PRIDE `projectAccessions` = PXD048525, and the PMC titles of PMC11750707 and PMC9808373.

Spec: `spec` dc9be283. Templates: bigbio/sdrf-templates 7da1747.

I modified no SDRF and no manifest, and I ran no `review-gate approve`.

| Artifact | sha256 (frozen; unchanged at end) | Verdict |
|---|---|---|
| `annotations/PXD048525-luad.sdrf.tsv` | `50a5bceb55d00f4119e0cc58b1a814574be17caea74e78bb79890300a0c1176c` | **PASS** (minor findings only) |

## Deterministic checks (re-run by the reviewer)

| Check | Result |
|---|---|
| `parse_sdrf validate-sdrf` (0.1.7, live OLS), all four templates together | exit 0; 1 warning ¹ |
| `parse_sdrf validate-sdrf`, each template alone (ms-proteomics, human, clinical-metadata, oncology-metadata) | exit 0 each; same warning |
| `sdrf-tools check` | 15/15 terms verified, CLEAN |
| `sdrf-tools score` | 96/100 ² |
| `sdrf-tools structure` | OK |
| `sdrf-tools reconcile` | 2 MAJOR disagreements, both refuted ³ |
| `sdrf-tools schema-check` (manifest) | valid |
| `sdrf-tools manifest-coverage` | 26/26 columns covered |

¹ The warning is the pooled-sample "values" validator rejecting `SN=HCC827;SN=NCI-H520;SN=NCI-H460`. The same column's SN= pattern validator accepts it.

² The score lost points for the missing `developmental stage` column and for age `pooled`. Neither is a defect: no per-patient age is available, and `pooled` is the spec's reserved word for reference rows.

³ Both disagreements come from the project-wide PRIDE record, which also covers the BM arm:
- **timsTOF Pro.** The PRIDE protocol for primary tumours names the Orbitrap Elite, and so do the paper Methods.
- **Trypsin/Lys-C.** The primary-tumour protocol says "After overnight digestion by trypsin". The Lys-C mix belongs to the BM arm.

## Verified

**Templates.** I derived them myself from `templates.yaml` at 7da1747: ms-proteomics 1.2.0 (latest), human 1.1.0, clinical-metadata 1.0.0 and oncology-metadata 1.0.0. They match the four `comment[sdrf template]` columns. Every column required by base, sample-metadata and these templates is present. There are 98 rows × 42 columns, and every source name + assay name pair is unique.

**Files.** I listed the 7z archive myself (py7zr over HTTP range reads). `UHN_Lung_Tissue_IMPACT_Samples_Raw_Data.7z` has 49 `.raw` members, with timestamps from May to October 2015. Three sets are identical:
- the 49 archive members;
- the 49 `comment[data file]` values (each on one light row and one heavy row);
- the 49 `Ratio H/L <experiment>` columns of `UHN_Lung_Tissue_IMPACT_proteinGroups.txt`.

**Patient values.** All come from the deposited individual-level sample list, which I checked row by row:
- source name = sample-list `label`;
- `individual` = `PHLC` + the zero-padded `ID`;
- `disease` = lung adenocarcinoma for all 49;
- `histologic subtype` = Mucinous Adenocarcinoma exactly for the four "ADC, mucinous" rows (PHLC137, 054, 155, 264).

**No invented demographics.** Age, sex, ancestry, stage and BM outcome are all `not available`. I independently confirmed that no individual-level source exists for them:
- **Paper.** PMC open-access file list: the only supplement is MOESM1, the reporting summary PDF. There are no supplementary tables or source data.
- **GEO GSE220838.** 196 GSMs, titled `GZLBM2022tissueNNN`, with no PHLC IDs.
- **Ref. 45 (Mirhadi 2023).** Supplementary Data 1, sheet "Clinical Info", has per-patient sex and smoking status for 52 PHLC IDs, but none of them overlaps the 49 IDs here.
- **Ref. 46 (Zhang 2014, PXD000438).** It covers xenografts, not these tumours.

**Super-SILAC channels.** The heavy channel is encoded as the spiked reference: `sample type` = reference, `material type` = cell line, the pooled cell lines named in `SN=`, and `pooled` for individual-level fields. The light channel is the patient tissue.
- **Composition.** Ref. 45 (title verified) gives HCC827 + H520 + H460, Lys-8/Arg-10, 1:1:1, "served as an internal reference".
- **Data check.** I recomputed the ratios in the deposited proteinGroups myself. Tissue-only proteins are light-dominant: Ratio H/L is HBB 0.069, ALB 0.109, SFTPB 0.0019, SFTPC 0.149, AGER 0.019 and PTPRC 0.090. EGFR is heavy-dominant at 4.25, as expected from the EGFR-amplified HCC827.

**Technical values.** All match the paper's Methods (PMC11750707), the PRIDE protocol and ref. 45: Orbitrap Elite, DDA, trypsin, DTT, IAA, CID at 30 NCE with ion-trap MS2, MS1 400–1200 m/z, Oxidation (M) (proteinGroups site column), Lys8 = UNIMOD:259 and Arg10 = UNIMOD:267.

**Acetyl (Protein N-term) is correctly left out.** PRIDE's MOD:00394 (acetylated residue) is explained by the BM-arm search.

**Round-1 L1 is resolved.** `factor value[histologic subtype]` has been removed. `factor value[disease]` now mirrors `characteristics[disease]`, and the manifest states that the true study factor cannot be annotated per sample.

## Findings

There are no blocker or important findings.

| # | Severity | Location | Issue | Evidence | Fix |
|---|---|---|---|---|---|
| M1 | minor | `characteristics[organism part]` heavy rows; manifest claim | `lung` is acceptable as tissue of origin, but the manifest says all three lines are lung-derived. | Cellosaurus CVCL_0459 (NCI-H460): "Derived from site: Metastatic; Pleural effusion". | Reword the manifest claim, or use `not applicable` (precedent PXD000690/PXD001963). |
| M2 | minor | `characteristics[histologic subtype]` = Mucinous Adenocarcinoma (4 rows); manifest | The manifest calls NCIT:C26712 "the generic term" chosen to avoid asserting invasiveness. Its NCIT definition says "An invasive adenocarcinoma…", and it is not lung-specific. | OLS4 NCIT_C26712 definition. | Correct the rationale. The value itself can stay. |
| M3 | minor | `comment[modification parameters]` 1 (Carbamidomethyl, Fixed); manifest | PRIDE's MOD:00397 is cited as evidence specific to this arm. Chloroacetamide in the BM arm also yields carbamidomethyl, and both BM SDRFs declare it, so the PTM list does not single out this search. | PRIDE `identifiedPTMStrings`; the BM SDRFs. | Drop that argument and rely on IAA alkylation plus the MaxQuant default. |
| M4 | minor | `characteristics[disease]` heavy rows | `not applicable` follows precedent, but all three lines are non-small cell lung carcinoma (NSCLC). | Cellosaurus DI fields; ref. 45 "NSCLC cell lines". | Optional: `non-small cell lung carcinoma` (MONDO:0005233). |
| M5 | minor | `characteristics[pooled sample]` heavy rows | The `SN=` entries are cell-line names, not source names in this SDRF (spec README, pooled samples), so validate-sdrf warns. | README.adoc lines 348–356. | None required; this is super-SILAC precedent. |
| M6 | minor | `comment[data file]` | The listed files are members of a 7z archive, not top-level PRIDE files. | PRIDE files/all: 3 `.7z` RAW archives. | None required; already documented as a limitation. |
| M7 | minor | precursor/fragment mass tolerance | `not available` is honest, but `convert-openms` fails on it (round-1 L2). | No search-parameter files are deposited. | None required. |

## Review report (JSON; passes `sdrf-tools schema-check` as a valid review-report)

```json
{
 "schema_version": 1,
 "artifact": "annotations/PXD048525-luad.sdrf.tsv",
 "artifact_sha256": "50a5bceb55d00f4119e0cc58b1a814574be17caea74e78bb79890300a0c1176c",
 "verdict": "PASS",
 "summary": "Round-2 independent review of the LUAD (UHN super-SILAC, Orbitrap Elite) part. All 49 deposited .raw members map to one light (patient tissue) and one heavy (super-SILAC reference) row. Per-patient values (individual, disease, histologic subtype) come only from the deposited individual-level sample list. The heavy channel is encoded as a non-study pooled reference. The round-1 important finding (L1, factor value[histologic subtype]) is resolved. Only minor findings remain.",
 "reviewer_context": {
  "independent": true,
  "context": "Separate reviewer subagent with fresh context, dispatched by the caller. I did not read the producer transcript, PXD048525.report.md or the producer's scratch evidence. I re-fetched every source into scratchpad/review2-PXD048525/ and checked its identity: projectAccessions = PXD048525 and the PMC titles. I read the round-1 review only for its L1 finding."
 },
 "evidence_manifest": "annotations/PXD048525-luad.evidence.json",
 "checks": {
  "spec_compliance": {"status": "pass", "evidence": "Active templates derived from templates.yaml at bigbio/sdrf-templates 7da1747: ms-proteomics 1.2.0 (latest), human 1.1.0, clinical-metadata 1.0.0, oncology-metadata 1.0.0. These match the comment[sdrf template] columns. I read all required columns from base 1.1.0, sample-metadata 1.0.0 and the 4 declared templates; all are present. 98 rows x 42 columns. source name + assay name pairs are unique. sdrf-tools structure: column order OK. Reserved words are used legally ('pooled' for age, sex, individual and biological replicate in the reference rows, per spec README pooled-samples TIP)."},
  "ontology_integrity": {"status": "pass", "evidence": "sdrf-tools check: 15/15 terms verified, 0 hallucinated, 0 mismatches. Checked by hand in OLS4 (live; none obsolete): MONDO:0005061 lung adenocarcinoma; NCIT:C3512 Lung Adenocarcinoma; NCIT:C26712 Mucinous Adenocarcinoma; PRIDE:0001013 study sample; PRIDE:0000899 reference; MS:1001910 Orbitrap Elite; MS:1000291 linear ion trap; MS:1000133 collision-induced dissociation; PRIDE:0000627; PRIDE:0000608 DTT; PRIDE:0000599 IAA. The UNIMOD accessions match their mass shifts (259 = Lys8, 267 = Arg10). validate-sdrf (live OLS) raised no ontology errors."},
  "source_evidence": {"status": "pass", "evidence": "Paper PMC11750707 (title verified), Methods 'Tissue proteomic profiling': 49 LUAD tumours mixed 1:1 with super-SILAC standard; DTT 4.5 mM at 60 C; IAA 10 mM; overnight trypsin; Easy-nLC 1000 + Orbitrap Elite; MS1 400-1,200 m/z; top-10 DDA; NCE 30 in the ion trap. These match the PRIDE sampleProcessingProtocol for primary tumours. Ref45 PMC9808373 (title verified): standard = HCC827 + H520 + H460, Lys-8/Arg-10, 1:1:1, used as internal reference. Light/heavy assignment checked independently against the deposited proteinGroups.txt (Ratio H/L): HBB 0.069, ALB 0.109, SFTPB 0.0019, SFTPC 0.149, AGER 0.019, PTPRC 0.090 (tissue = light); EGFR 4.25 (heavy; HCC827 is EGFR-amplified). Sample list (UHN_Lung_Tissue_IMPACT_SampleList.xlsx, 49 rows) checked row by row: source name = label, individual = PHLC + zero-padded ID, histologic subtype mucinous for exactly PHLC137/054/155/264. Cellosaurus: CVCL_2063, CVCL_1566, CVCL_0459. Reconcile disagreements (timsTOF Pro, Trypsin/Lys-C) come from the BM arm of the project-wide record and are refuted by the primary-tumour protocol text."},
  "file_mapping": {"status": "pass", "evidence": "I listed UHN_Lung_Tissue_IMPACT_Samples_Raw_Data.7z independently (py7zr over HTTP range reads): 49 .raw members, mtimes May-Oct 2015. The member set equals the 49 distinct comment[data file] values (each on one light and one heavy row) and equals the 49 'Ratio H/L <exp>' experiments in proteinGroups.txt. None are missing, extra or duplicated, and no non-raw file is listed."},
  "design_consistency": {"status": "pass", "evidence": "49 patient tissues x 2 SILAC channels = 98 rows; 49 unique individuals; biological replicate 1 (light) / pooled (heavy); technical replicate 1; fraction 1 (single-shot, 240-min gradient). factor value[disease] mirrors characteristics[disease] (lung adenocarcinoma / not applicable for the reference). It carries no comparison among patients, and the manifest documents why: 5-year BM outcome is not available per sample. I re-checked this: the PMC OA file list shows no supplementary tables beyond the image-only reporting summary; GEO GSE220838 has 196 GSMs with no PHLC IDs; ref45 Supplementary Data 1 'Clinical Info' (52 PHLC IDs with sex/smoking) has zero overlap with the 49 IDs here."},
  "omission_safety": {"status": "pass", "evidence": "No per-patient age, sex, ancestry, stage, smoking or BM outcome is asserted; all are 'not available'. I confirmed that no individual-level source for them exists among the paper, its ESM, GEO, ref45 SD1 and ref46/PXD000438 (xenografts). Histologic subtype comes only from the deposited per-sample list. Heavy rows carry no patient-derived values. Carbamidomethyl (C) fixed is flagged INFERRED in the manifest and is consistent with the IAA alkylation. Acetyl (Protein N-term) is not asserted. That is correct: PRIDE's MOD:00394 is explained by the BM-arm FragPipe search. Minor wording/specificity issues are listed as findings."},
  "deterministic_validation": {"status": "pass", "evidence": "parse_sdrf (sdrf_pipelines 0.1.7) validate-sdrf -t ms-proteomics -t human -t clinical-metadata -t oncology-metadata: exit 0 with one warning, the pooled-sample values validator on 'SN=HCC827;SN=NCI-H520;SN=NCI-H460'. The value matches the same column's SN= pattern validator. Each template run alone: exit 0, same single warning. sdrf-tools check exit 0 (CLEAN). sdrf-tools score 96/100. sdrf-tools structure exit 0. sdrf-tools reconcile: 2 cross-arm false positives, refuted. sdrf-tools schema-check on the evidence manifest: valid. manifest-coverage: 26/26 columns covered. The artifact hash was unchanged at the end of the review."}
 },
 "findings": [
  {"severity": "minor", "category": "provenance", "location": "characteristics[organism part], heavy rows 2-98 (even); manifest claim 'characteristics[organism part]'", "message": "Heavy-row organism part 'lung' is acceptable as the tissue of origin (SAMPLE-GUIDELINES line 76). However, the manifest says all three reference lines are 'lung-derived (Cellosaurus tissue Lung)'. Cellosaurus records NCI-H460 as derived from a metastatic pleural effusion (UBERON:0000175). Fix: reword the manifest to 'tumour of origin: lung; NCI-H460 sampled from pleural effusion', or use 'not applicable' as the precedents PXD000690/PXD001963 do.", "evidence": "api.cellosaurus.org CVCL_0459: 'Derived from site: Metastatic; Pleural effusion'. CVCL_2063 and CVCL_1566: 'In situ; Lung'."},
  {"severity": "minor", "category": "ontology", "location": "characteristics[histologic subtype] = Mucinous Adenocarcinoma (rows of PHLC137-1_2, PHLC054-1_2, PHLC155-1, PHLC264-1); manifest claim", "message": "The manifest picks NCIT:C26712 as 'the generic term' so as not to assert invasiveness. The NCIT definition of C26712 itself begins 'An invasive adenocarcinoma...', and the term is not lung-specific. The value is acceptable as-is. Fix: correct the manifest rationale, or document why a site-agnostic term was preferred over the lung-specific NCIT terms (C136709 / C7268 / C136717), none of which the list supports.", "evidence": "OLS4 NCIT_C26712 description: 'An invasive adenocarcinoma composed of malignant glandular cells that contain intracytoplasmic mucin.'"},
  {"severity": "minor", "category": "provenance", "location": "comment[modification parameters] 1 (Carbamidomethyl, Fixed); manifest claim", "message": "The manifest cites PRIDE's MOD:00397 'iodoacetamide derivatized residue' as arm-specific evidence because 'the BM arm used chloroacetamide'. Chloroacetamide also yields carbamidomethyl, and both BM SDRFs declare Carbamidomethyl C Fixed, so the project-wide PTM entry does not single out this search. The value is still well supported by IAA alkylation plus the MaxQuant default. Fix: drop the PRIDE-PTM argument from this claim.", "evidence": "PRIDE identifiedPTMStrings = MOD:00425, MOD:00394, MOD:00397 (project-wide). PXD048525-bm-library/bm-dia SDRFs: 'NT=Carbamidomethyl;AC=UNIMOD:4;TA=C;MT=Fixed'."},
  {"severity": "minor", "category": "specificity", "location": "characteristics[disease] heavy rows", "message": "'not applicable' follows curated precedent, but the disease concept does apply to the reference: all three lines are non-small cell lung carcinoma (LUAD, LUSC, large cell). Optional fix: 'non-small cell lung carcinoma' (MONDO:0005233), which covers all three lines. Keep factor value[disease] = 'not applicable' on the reference rows.", "evidence": "Cellosaurus DI lines: NCIt C3512, C3493, C4450. Ref45 calls them 'NSCLC cell lines'. Precedents PXD000690/PXD001963 use 'not applicable'."},
  {"severity": "minor", "category": "spec", "location": "characteristics[pooled sample] heavy rows", "message": "Spec README (pooled samples) defines SN= entries as source names of pooled samples. HCC827/NCI-H520/NCI-H460 are cell-line names with no rows of their own, and validate-sdrf warns on the value. This is accepted precedent for super-SILAC (PXD000690, PXD001963, PXD003138), so no change is required.", "evidence": "spec/sdrf-proteomics/README.adoc lines 348-356; validate-sdrf warning."},
  {"severity": "minor", "category": "file_mapping", "location": "comment[data file], all rows", "message": "The data files are members of the deposited archive UHN_Lung_Tissue_IMPACT_Samples_Raw_Data.7z, not top-level repository files. The manifest limitation records this. No change is required, but consumers that resolve files against the PRIDE file list will not find them.", "evidence": "PRIDE files/all lists 9 entries, of which 3 are .7z RAW archives. The 7z listing shows the 49 member names."},
  {"severity": "minor", "category": "provenance", "location": "comment[precursor mass tolerance], comment[fragment mass tolerance]", "message": "'not available' is correct because nothing deposited states the tolerances. As a result, parse_sdrf convert-openms fails on these columns. This is carried over from round 1 (L2) and no action is required.", "evidence": "No mqpar.xml/parameters.txt in the PRIDE file list. Ref45 states no tolerances."}
 ]
}
```

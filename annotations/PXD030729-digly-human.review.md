# Independent review — PXD030729-digly-human.sdrf.tsv

- Artifact: `annotations/PXD030729-digly-human.sdrf.tsv`
- artifact_sha256: `d00fc005079a453fc3873869c6b3616c036b204bf3cc0f42991b1e448e1c489f` (frozen at start, unchanged at end)
- Evidence manifest: `annotations/PXD030729-digly-human.evidence.json`
- Scope: only this SDRF (CCNF diGly SILAC, SH-SY5Y WT vs CCNF-KO cl.2 and ALS patient/control LCLs). The other three PXD030729 SDRFs are out of scope.
- Reviewer context: fresh subagent. I did not read PXD030729.report.md, PXD030729.review.md, producer transcripts or producer scratch. I re-fetched every source into `scratchpad/rev2-PXD030729/`.

## Verdict: PASS (minor findings only)

## What was checked
- **Deterministic checks.** Each of these exited 0:
  - `parse_sdrf validate-sdrf` with `-t ms-proteomics`, `-t human` and `-t cell-lines`. The cell-lines run gave 6 warnings, all for LCL names not found in clo/bto/efo.
  - The same validator with auto-detected templates.
  - `sdrf-tools structure`.
  - `score`, which gave 100/100.
  - `reconcile --record <PRIDE project JSON>`.
  - The evidence-manifest schema check.

  `sdrf-tools check` (online) exits 1 only for the six study LCL names ("LCL V3656" … "LCL V7163"). I refute these hits as false positives. The names are study donor/line codes. They come from the deposited `LCL_diGly_summary.txt` experiment names and the Table S1 Legend key (ctrl1=V3656, ctrl2=V549, ctrl3=V79, ctrl4=V6719, V335M=V6604, D628V=V7163), and the producer does not present them as ontology terms. The template sets this to warning level, and the "LCL " prefix avoids a collision with the hamster V79 line.
- **Channel map (SH-SY5Y).** The MaxQuant experiments are named `(WT=L/KO=H)_IP1..4` and the Legend says "WT (light) vs. KO (heavy)" and "KO / cl.2". The deposited Sites table gives these log2 H/L values, which matches the paper's sites decreased in KO:
  - RPS20 K49: −2.5 to −3.3
  - RPL12 K48: −1.4 to −2.0
  - FANCD2 K561: −1.6
- **Channel map (LCL).** Experiment names follow the pattern `<ctrl>(light)/<mutant>(K8/R10)-IPn`, and the Legend says "controls (light) vs. mutant cells (heavy)". The ratios agree:
  - PCBP2 K265 is −4.6 to −6.9 in both V6604 (V335M) pairings.
  - MSN K60, FSCN1 K241 and WDR1 K104 are −1.6 to −3.3 only in the V7163 (D628V) pairings.
  - This matches the paper's Fig 1F text.
- **Values for each patient and donor.** Each one comes from a source that describes that individual:
  - Sex comes from the reagent table (ctrl1, ctrl2 and V335M female; ctrl3, ctrl4 and D628V male).
  - Familial vs sporadic ALS comes from the Methods text for each patient.
  - "adult" for the patients comes from their stated onset ages (47 y and 62 y).
  - Age, ancestry and passage are `not available`. No cohort summary was copied onto rows.
- **Search and protocol.** The SH and LCL `mqpar.xml`/`summary.txt` files give:
  - 4.5 ppm main-search tolerance and FTMS 20 ppm.
  - Trypsin/P.
  - Carbamidomethyl C as a fixed mod; Oxidation M, Acetyl Protein N-term and stringent GlyGly K (encoded as UNIMOD:121) as variable mods.
  - Lys8 only (encoded as UNIMOD:259), Multiplicity 2.
  - The human UP000005640 FASTA.

  The paper confirms lys-C followed by trypsin, DTT, chloroacetamide, lys/arg-free DMEM and K8 only. Range reads of the raw files AS389 and AS441 show "Method of Q Exactive HF".
- **Ontology.** I re-resolved every controlled value in OLS4 by exact search. All labels and accessions match and none is obsolete.
- **Files.** PRIDE lists 117 files (projectAccessions = PXD030729), of which 72 are .raw. This SDRF's 40 raws are exactly the SH_diGly (8) and LCL_diGly (32) runs. Across the four PXD030729 SDRFs all 72 raws are used once each.
- **Design.** There are 8 cell line × genotype groups, and replicate numbers restart within each group:
  - SH-SY5Y WT and KO: 4 each.
  - Each control LCL: 4.
  - V6604 and V7163: 8 each, consistent with Fig 1E's "eight biological replicates".

  There are no duplicate (file, label) pairs, and each source name is consistent across its rows.

## Findings (all minor)
1. **Control developmental stage.** In the `characteristics[developmental stage]` column, the control LCL rows say "adult". This is inferred from the pairwise statement "gender- and age-matched" to the patients (onset at 47 and 62 y); no control donor age is published. The manifest documents it as an inference, and I accept it. A stricter choice would be `not available`.
2. **Fraction order.** For `comment[fraction identifier]`, the order of the two sequential IPs (1 vs 2) is inferred from acquisition order. This is documented.
3. **Mutant replicate numbering.** Numbering the mutants' biological replicates 1–8 assumes independent heavy cultures for each pairing. This is documented and supported by "eight biological replicates".
4. **Age at onset not encoded.** The patients' ages at onset (62 y and 47 y) are published for each individual but not encoded. A custom characteristics column could hold them; no active template requires it.
5. **Manifest presentation.** The manifest `artifact` is an absolute path, and two claim locations say "rows none" instead of row ranges. This is cosmetic.

I made no edits to the SDRF or manifest and did not run `review-gate approve`.

## Report JSON (validated with `sdrf-tools schema-check`: valid review-report)

```json
{
  "schema_version": 1,
  "artifact": "annotations/PXD030729-digly-human.sdrf.tsv",
  "artifact_sha256": "d00fc005079a453fc3873869c6b3616c036b204bf3cc0f42991b1e448e1c489f",
  "verdict": "PASS",
  "summary": "Independent fresh-context review of the 80-row (40 raw files x 2 SILAC channels) CCNF diGly SILAC SDRF for SH-SY5Y WT/CCNF-KO and six patient/control LCLs. Channel map, donor sex/disease/genotype, search parameters, instrument and file mapping were re-derived from the deposited MaxQuant files, raw headers, the paper and Table S1 legend; no blocker or important finding. Minor findings only.",
  "reviewer_context": {
    "independent": true,
    "context": "fresh subagent; did not read PXD030729.report.md, PXD030729.review.md, producer transcripts or producer scratch dirs; all sources re-fetched into scratchpad/rev2-PXD030729"
  },
  "evidence_manifest": "annotations/PXD030729-digly-human.evidence.json",
  "checks": {
    "spec_compliance": {"status": "pass", "evidence": "47 columns, 80 rows; templates ms-proteomics v1.2.0 + human v1.1.0 + cell-lines v1.1.0 fit the samples (all cultured human cell lines); sdrf version v1.1.0; sdrf-tools structure OK; no duplicate (data file, label) pairs; each source name maps to one cell line/label/replicate; reserved words only where templates allow (cellosaurus accession allow_not_available true)."},
    "ontology_integrity": {"status": "pass", "evidence": "OLS4 exact search re-resolved UBERON:0000178 blood, UBERON:0002371 bone marrow, BTO:0002062 B-lymphoblastoid cell line, MONDO:0005144 familial ALS, MONDO:0005145 sporadic ALS, MONDO:0005072 neuroblastoma, PATO:0000461 normal, PATO:0000383/0000384, HANCESTRO:0005, EFO:0001272 adult, NCIT:C185409 DMEM, EFO:0009106, MS:1001309 Lys-C, MS:1000422, MS:1002523, MS:1000484, NCBITaxon:9606 (none obsolete). sdrf-tools check online: 24 verified, 0 label mismatches, 0 UNIMOD swaps; its 12 'hallucinated' hits are the six study LCL names, which are non-ontology study codes (warning-level in cell-lines template), refuted below."},
    "source_evidence": {"status": "pass", "evidence": "SH: SH_diGly_summary.txt experiments '(WT=L/KO=H)_IP1..4' (2 raws each); Table S1 Legend 'SH-SY5Y cells, WT (light) vs. KO (heavy)', 'SH-SY5Y CCNF KO = KO / cl.2'; Sites table log2 H/L RPS20 K49 -2.5..-3.3, RPL12 K48 -1.4..-2.0, FANCD2 K561 -1.6 (paper: decreased in SH-SY5Y KO) => heavy=KO. LCL: summary experiments 'V3656(light)/V6604(K8/R10)', 'V549(light)/V6604', 'V79(light)/V7163', 'V6719(light)/V7163'; Legend key ctrl1=V3656, ctrl2=V549, ctrl3=V79, ctrl4=V6719, V335M=V6604, D628V=V7163; PCBP2 K265 -4.6..-6.9 in both V6604 pairs (paper: PCBP2 decreased in V335M); MSN K60/FSCN1 K241/WDR1 K104 -1.6..-3.3 in V7163 pairs only. Sex per donor from paper reagent table (ctrl1/ctrl2/V335M female, ctrl3/ctrl4/D628V male); familial vs sporadic ALS from per-patient Methods text; adult for patients from per-patient onset ages 47 y / 62 y. mqpar.xml: mainSearchTol 4.5 ppm, FTMS MS/MS 20 ppm, Trypsin/P, Carbamidomethyl fixed, Oxidation/Acetyl(Protein N-term)/stringent GlyGly(K) variable, labelMods Lys8, human UP000005640 FASTA. Paper: lys-C 1 h then trypsin, DTT, chloroacetamide, lysine/arginine-free DMEM, K8 only. Raw headers (AS389, AS441 range-read) 'Method of Q Exactive HF'."},
    "file_mapping": {"status": "pass", "evidence": "PRIDE file list (117 entries, projectAccessions = PXD030729) has 72 .raw; this SDRF's 40 raws equal exactly the raws of SH_diGly (8) and LCL_diGly (32) summary.txt; across the four PXD030729 SDRFs all 72 raws are used once, none missing/extra/duplicated."},
    "design_consistency": {"status": "pass", "evidence": "8 factor groups (cell line x genotype): SH WT/KO 4 sources each, control LCLs 4 each, V6604 and V7163 8 each (heavy in 4 mixtures with each of two controls), replicate numbers unique within group and restarting per group; paper Fig 1E 'four respective eight biological replicates ... LCLs' and 'four biological replicates for each of the two controls'. Two sequential diGly IPs per mixture as fraction 1/2 (MaxQuant gives both raws one Experiment). convert-openms in validation log: 8 conditions."},
    "omission_safety": {"status": "pass", "evidence": "No per-patient value comes from a cohort summary: age = not available (no age at sampling published), ancestry/passage = not available, cellosaurus accession/name = not available for LCLs, SH-SY5Y individual/developmental stage = not available. Only inference carried into cells: control LCL developmental stage 'adult' from the pairwise 'gender- and age-matched' statement (documented in manifest; minor). No bait/genotype asserted without evidence; K8/R10 in MaxQuant names vs Lys8-only search resolved in favour of search + Methods."},
    "deterministic_validation": {"status": "pass", "evidence": "parse_sdrf validate-sdrf -t ms-proteomics exit 0; -t human exit 0; -t cell-lines exit 0 (6 warnings: LCL names not in clo/bto/efo); auto-detected templates exit 0; sdrf-tools structure exit 0; sdrf-tools score 100/100; sdrf-tools reconcile --record PRIDE project JSON exit 0 ('every annotated value agrees'); sdrf-tools check (online) exit 1 solely for the six study LCL names (refuted: deposited MaxQuant experiment names + Table S1 key; not Cellosaurus lines); evidence manifest schema-check valid."}
  },
  "findings": [
    {"severity": "minor", "category": "source_evidence", "location": "characteristics[developmental stage], control LCL rows (V3656, V549, V79, V6719)", "message": "'adult' is inferred from 'gender- and age-matched control LCLs' to patients with onset at 47/62 y, not from a stated donor age.", "evidence": "Paper Results; manifest marks it as INFERENCE. Pairwise matching makes adulthood near-certain; acceptable. Stricter alternative: not available."},
    {"severity": "minor", "category": "design", "location": "comment[fraction identifier] rows 1-80", "message": "Which raw is the first vs second sequential diGly IP is inferred from acquisition order (lower AS number = IP 1).", "evidence": "Paper: 'immunoprecipitated sequentially two times'; summary.txt pairs e.g. AS434/AS438 under one Experiment; order not stated. Documented in limitations."},
    {"severity": "minor", "category": "design", "location": "characteristics[biological replicate] V6604/V7163 rows", "message": "Numbering 1-8 assumes eight independent heavy cultures; the paper reports 'eight biological replicates' for LCLs but not whether one heavy lysate was shared between two control pairings.", "evidence": "Fig 1E legend; documented in limitations."},
    {"severity": "minor", "category": "completeness", "location": "patient LCL rows (V6604, V7163)", "message": "Individual-level age at disease onset (62 y V335M, 47 y D628V) is published but not encoded; could go in a custom characteristics column.", "evidence": "Methods 'CCNF ALS patient cells'. Not required by any active template."},
    {"severity": "minor", "category": "provenance", "location": "PXD030729-digly-human.evidence.json", "message": "Manifest 'artifact' is an absolute path, and two claim locations read 'rows none' instead of row ranges (disease; developmental stage).", "evidence": "Cosmetic; values and sources in those claims are correct."}
  ]
}
```

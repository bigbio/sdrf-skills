# PXD023790-silac — independent adversarial review

- **Artifact:** `annotations/PXD023790-silac.sdrf.tsv` (300 rows × 52 columns; 100 raws × L/M/H)
- **artifact_sha256:** `a1606d401bdb05d4906fcdedfc6f130891a0c57fecc541ff2fd000137b2505df` (frozen at start, re-checked at end)
- **Verdict: PASS** (minor findings only)
- **Scope:** the pulse-SILAC SDRF only. The HSP27-IP SDRF already passed and is out of scope. The previous `PXD023790.review.md` and `PXD023790.report.md` were not read.
- **Reviewer context:** a fresh subagent. I used the producer's scratch only for the three MaxQuant files the manifest cites (`parameters.txt`, `summary.txt`, `proteinGroups.txt`). Their CRC32 values match the CRC in the `Fan_et_al_triple_SILAC_txt.7z` header, which I read myself by HTTP range with py7zr.

## What was independently re-derived
| Check | Result |
|---|---|
| validate-sdrf (ms-proteomics, human, cell-lines) | exit 0, no warnings |
| sdrf-tools check / score / structure | CLEAN 19/19 terms; 100/100; OK |
| schema-check manifest / manifest-coverage | valid; 33/33 columns covered |
| reconcile | exit 1, `cleavage_agent_unsupported`. This is a **false positive**: the PRIDE protocol never describes the digestion; its only "incubated with" is the heavy-amino-acid pulse. Supp. Methods: "digested in LYSE with 1 μg of endoproteinase LysC and 1 μg of trypsin" |
| Templates | ms-proteomics v1.2.0 / human v1.1.0 / cell-lines v1.1.0 = upstream 7da1747 `latest`; all of their required and recommended columns are present |
| File mapping | Raw 7z header has 107 .raw members. 100 are annotated. The 7 unannotated are exactly the 7 BLOCKED runs. summary.txt has 108 runs; the extra `20180312_QX8_MaMu_SA_PBL985_MITO_t0_H1` was never deposited |
| Is it SILAC? | summary.txt: Multiplicity 3, Labels1 Arg6;Lys4, Labels2 Arg10;Lys8 for all 108 runs |
| Channel map | Paper: L = light, M = Arg6/Lys-2H4 pre-labelled, H = pulse. Data agree: median log2 H/M is t0 −1.85..−2.88 and t24 −0.10..−1.82 |
| Genotype letters | proteinGroups: every annotated H run has HAX1 L/M/H = 0 (trace only in 1MITO_t6_H2 and 1MITO_t24_H2). Every C run has CLPB M = H = 0. The light channel carries the KO, so the light reference has the same genotype |
| 2CELLS_t6_W1-3 → CLPB KO | The submitter sheet says "CLPB ko, not wt", and CLPB = 0 in all channels |
| Round of the 2X_ runs | 7z member times are 2018-06-13 10:02–14:04, inside the round-2 QX0 cells-t0 sequence (W2, W3, H1, H2, H, C1–C3) |
| Technical replicates | Repeat_t0_W3's best M/L partner is 2X_CELLS_t0_W3 (r = 0.79). Repeat_t24_H2's best partner is 2CELLS_t24_H2 (M/L 0.75, H/L 0.80) |
| Blocked runs | Confirmed. 2CELLS_t24_C1/C2/C3/H3 H/M −2.78/−2.88/−2.52/−2.69 vs same-mix mito −0.29/−0.19/−0.74/−0.28. Repeat_t0_W1/W2 −0.58/−0.67, and Repeat_t0_W1 correlates r = 0.89 with 2CELLS_t24_W1. 2MITO_t6_H1: HAX1 8 peptides, L/M/H 1.07e9/5.2e8/1.9e8 |
| Instrument and method | 3 more raw headers read by HTTP range (QX8 round-1 CELLS_t6_C2 and MITO_t24_W2; QX0 round-2 MITO_t24_W2): Q Exactive HF-X, Full MS 300–1650 m/z at 60k, TopN 15, NCE 27 |
| Search parameters | Carbamidomethyl fixed; Oxidation and Acetyl (Protein N-term) variable; FTMS MS/MS tolerance 20 ppm; Trypsin/P with 2 missed cleavages. These match the SDRF |
| Cell line | Cellosaurus CVCL_2162: Caucasian, 36Y, female, peripheral blood, AML with maturation, HL-60 derivative. These match the SDRF |
| Ontology | OLS4 resolves all terms. GO:0005623 "cell" is obsolete, but the label resolves to CL:0000000 |

## BLOCKED.md (PXD023790 section)
Correct in substance: the 7 runs and the undeposited 1MITO_t0_H1 are right, and the unblock condition is sensible. Two wording fixes are needed (findings 1–2).

## Findings (all minor)
1. **BLOCKED.md, 2MITO_t6_H1 row.** It says "Clone H1 has HAX1 = 0 in its other 17 runs". The correct number is **11**: 10 deposited runs plus the search-only 1MITO_t0_H1, all with HAX1 = 0.
2. **BLOCKED.md "Why H/M…" and the manifest data-file claim.** H/M only tells 24 h apart from 0/6 h. The 0 h and 6 h ranges overlap (round-1 cells t0 −1.85..−2.58 vs t6 −1.74..−2.45). "All other 100 runs agree with their time point" overstates what the check shows. "100 runs, including all 54 mitochondria runs" mixes counts: 52 mitochondria runs are annotated and 54 were searched.
3. **`characteristics[sample type]` is absent.** base 1.1.0 (line 55) recommends it, with default "study sample". Adding it is optional.
4. **2CELLS_t24_W1.** The data cannot confirm WT: HAX1 has 0 peptides and CLPB 1 peptide in a low-depth run. Nothing contradicts WT either. Consider a limitation note.
5. **Optional evidence to record.** Repeat_t0_W1 correlates r = 0.89 (M/L) and 0.88 (H/L) with 2CELLS_t24_W1, so it is likely a re-injection of a 24 h sample. This supports the block.

## Review report JSON
```json
{
  "schema_version": 1,
  "artifact": "annotations/PXD023790-silac.sdrf.tsv",
  "artifact_sha256": "a1606d401bdb05d4906fcdedfc6f130891a0c57fecc541ff2fd000137b2505df",
  "verdict": "PASS",
  "summary": "Independent fresh-context review of the PXD023790 pulse-SILAC SDRF (300 rows = 100 raws x L/M/H). Deterministic validation passes; every controlled term resolves; the channel map (L = light reference, M = pre-existing, H = newly synthesised), genotype letters, round/clone numbering and the 7 BLOCKED runs were re-derived from the deposited MaxQuant output (CRC-verified against the 7z header) and the 7z member list. No blocker or important findings; minor wording/omission items only.",
  "reviewer_context": {"independent": true, "context": "fresh subagent without producer transcript; PXD023790.report.md and PXD023790.review.md not read; producer scratch used only for the three MaxQuant files the manifest cites, after CRC32 match to the archive header"},
  "evidence_manifest": "annotations/PXD023790-silac.evidence.json",
  "checks": {
    "spec_compliance": {"status": "pass", "evidence": "parse_sdrf validate-sdrf -t ms-proteomics -t human -t cell-lines: 'Everything seems to be fine', exit 0; sdrf-tools structure OK. 52 columns, 300 rows, no characteristics/factor mismatch, sdrf version v1.1.0, templates ms-proteomics v1.2.0 / human v1.1.0 / cell-lines v1.1.0 match upstream templates.yaml at 7da1747 (lines 28, 79, 150). All required/recommended columns of those three templates present; only base 1.1.0's recommended characteristics[sample type] is absent (minor)."},
    "ontology_integrity": {"status": "pass", "evidence": "sdrf-tools check: 19/19 terms verified, 0 hallucinated/mismatched/UNIMOD swaps. OLS4 re-resolved MONDO:0020320, EFO:0002313 PLB985, NCIT:C178973, HANCESTRO:0005, EFO:0001272, UBERON:0000178, GO:0005739, CL:0000000 'cell' (GO:0005623 obsolete; label 'cell' still resolves via CL). UNIMOD 481/188/259/267 match Lys4(2H4)/Arg6/Lys8/Arg10 mass shifts. MS:1002877, MS:1000422, MS:1000484, MS:1001251, MS:1001309, PRIDE:0000627 correct."},
    "source_evidence": {"status": "pass", "evidence": "PRIDE record/protocol, PMC9057593 text and JCI153153DS1 supplement re-downloaded. Channel map explicit in paper ('light [L] ... medium [M] ... heavy H to initiate pulse labeling') and summary.txt (Multiplicity 3, Labels1 Arg6;Lys4, Labels2 Arg10;Lys8, all 108 runs); data agree: median log2 H/M rises at 24 h (t0 -1.85..-2.88, t24 -0.1..-1.8). Genotype letters verified on proteinGroups: all 34 annotated HAX1-KO runs have HAX1 L/M/H = 0 or trace; all CLPB-KO runs CLPB M=H=0; light channels carry the KO. Submitter sheet confirms '2CELLS_t6_W1-3: CLPB ko, not wt'. Cellosaurus CVCL_2162 confirms ancestry/age/sex/site/disease/HL-60 hierarchy. Raw headers of 3 further runs (QX8 round 1 CELLS_t6_C2, MITO_t24_W2; QX0 round 2 MITO_t24_W2) read by HTTP range: Q Exactive HF-X, Full MS 300-1650 m/z, TopN 15, NCE 27."},
    "file_mapping": {"status": "pass", "evidence": "7z header of Fan_et_al_Triple_SILAC_basis_raw.7z read by HTTP range (py7zr): 107 .raw members. 100 unique comment[data file] all present; the 7 unannotated members are exactly the 7 listed in BLOCKED.md; summary.txt has 108 raw files, the extra one (20180312_QX8_MaMu_SA_PBL985_MITO_t0_H1) is not deposited. assay name = file stem, one per file."},
    "design_consistency": {"status": "pass", "evidence": "Per (genotype, compartment, time, label) each biological replicate maps to one source; technical replicate 2 only for Repeat_t0_W3 (best M/L correlation partner 2X_CELLS_t0_W3, r=0.79) and Repeat_t24_H2 (partner 2CELLS_t24_H2, M/L r=0.75, H/L 0.80). Round-2 assignment of 2X_ runs confirmed by 7z member times (2018-06-13 10:02-14:04 inside the round-2 QX0 cells-t0 sequence). Blocked runs re-verified: 2CELLS_t24_C1/C2/C3/H3 H/M -2.78/-2.88/-2.52/-2.69 vs same-mix mito -0.29/-0.19/-0.74/-0.28; Repeat_t0_W1/W2 -0.58/-0.67 (and Repeat_t0_W1 correlates r=0.89 with 2CELLS_t24_W1); 2MITO_t6_H1 HAX1 8 peptides, L/M/H 1.07e9/5.2e8/1.9e8."},
    "omission_safety": {"status": "pass", "evidence": "Inferred values are disclosed and marked in source names (clone-unconfirmed-fileWn, clone3-inferred-fileH); light-reference clone identity disclosed as inferred; precursor tolerance left 'not available' rather than taking the contradicted '7 ppm' sentence; cell type/passage/storage 'not available'. No value found that asserts more than the cited evidence except the minor over-statements listed below (BLOCKED.md wording)."},
    "deterministic_validation": {"status": "pass", "evidence": "validate-sdrf exit 0; sdrf-tools check CLEAN exit 0; sdrf-tools score 100/100; structure OK; schema-check evidence manifest valid; manifest-coverage 33/33 columns. reconcile exit 1 with one BLOCKER cleavage_agent_unsupported: false positive confirmed — the PRIDE protocol never describes the digestion (its only 'incubated with' is the heavy-amino-acid pulse); supplement states 'digested in LYSE with 1 ug of endoproteinase LysC and 1 ug of trypsin'. convert-openms exit 1 on precursor tolerance 'not available' (documented, campaign precedent)."}
  },
  "findings": [
    {"severity": "minor", "category": "provenance", "location": "annotations/BLOCKED.md, PXD023790 section, row 2MITO_t6_H1", "message": "'Clone H1 has HAX1 = 0 in its other 17 runs' is wrong: clone H1 has 11 other searched experiments (10 deposited + search-only 1MITO_t0_H1), all with HAX1 L/M/H = 0.", "evidence": "proteinGroups.txt O00165 Intensity L/M/H for the 12 *_H1 experiments. Fix: change 17 to 11."},
    {"severity": "minor", "category": "provenance", "location": "annotations/BLOCKED.md 'Why H/M identifies the time point'; manifest comment[data file] claim", "message": "H/M only separates 24 h from 0/6 h; 0 h and 6 h overlap (round-1 cells t0 -1.85..-2.58 vs t6 -1.74..-2.45). 'all other 100 runs agree with their time point' over-states the check; also '100 runs, including all 54 mitochondria runs' mixes counts (52 annotated mito runs; 54 searched).", "evidence": "Median log2 Ratio H/M per experiment recomputed from proteinGroups.txt. Fix: say the check verifies 24 h vs earlier only; correct the counts."},
    {"severity": "minor", "category": "completeness", "location": "column characteristics[sample type] (absent)", "message": "base 1.1.0 (upstream 7da1747) recommends characteristics[sample type] with default 'study sample'; it is not present.", "evidence": "tpl/t/base/1.1.0/base.yaml line 55; inherited via sample-metadata extends base@>=1.1.0. Optional fix: add 'study sample' (light rows could arguably be a reference, but the paper also analyses light LFQ as study data)."},
    {"severity": "minor", "category": "evidence", "location": "rows of 2CELLS_t24_W1 (20180612_..._CELLS_t24_W1.raw)", "message": "WT genotype not confirmable on data: HAX1 0 peptides, CLPB 1 peptide (low-depth run, 2058 H/M ratios). Not contradicted (WT whole-cell HAX1 is often at detection limit), label kept from file name.", "evidence": "proteinGroups.txt; could be added to manifest limitations."},
    {"severity": "minor", "category": "evidence", "location": "manifest limitations / BLOCKED.md unblock path", "message": "Extra evidence for the Repeat_t0_W1/W2 block: Repeat_t0_W1 correlates r=0.89 (M/L) and 0.88 (H/L) with 2CELLS_t24_W1, i.e. it is likely a re-injection of a 24 h sample; worth recording.", "evidence": "Pearson r of protein log2 ratios, round-2 whole-cell runs."}
  ]
}
```

# Adversarial reviewer brief

Operational brief for a fresh-context reviewer. Lives in the repo (not `/tmp`) because an earlier
run kept it in the scratchpad, `/tmp` was wiped, and the resume path broke.

You are an INDEPENDENT reviewer with no prior context. Distrust whoever produced the artifact.
**FALSIFY it; do not confirm it.** Form conclusions from primary sources only.

Working dir: `/home/sachsenb/Development/sdrf-skills`
Follow: `skills/sdrf-adversarial-review/SKILL.md` and
`skills/sdrf-adversarial-review/references/review-contract.md`

## MANDATORY: private per-accession working directory
Concurrent agents have overwritten each other's cached data with a **different accession's** file
list mid-run. Write only to `<scratch>/rev_<PXD>/`; never read a scratch file you did not write in
this run; touch no other artifact's files.

## Evidence sources
- **Authoritative file list**: `https://www.ebi.ac.uk/pride/ws/archive/v3/projects/<PXD>/files/all`.
  The MCP `get_project_files` **silently truncates at 100 files** (#32) — never use it for counts.
- Spec: `spec/sdrf-proteomics/TERMS.tsv`, `spec/sdrf-proteomics/sdrf-templates/{name}/{version}/{name}.yaml`.
  Use `spec/scripts/resolve_templates.py`; do not reimplement merge semantics.
- Validator (activate env first), using **exactly** the templates the artifact declares in
  `comment[sdrf template]`:
  ```
  source /home/sachsenb/miniforge3/etc/profile.d/conda.sh && conda activate sdrf-skills
  parse_sdrf validate-sdrf --sdrf_file <artifact> --template <t1> --template <t2> ...
  ```
- MCP: `ToolSearch "select:mcp__sdrf-pride-pmc__get_project_details,mcp__sdrf-pride-pmc__get_article_metadata,mcp__sdrf-pride-pmc__get_full_text_article,mcp__sdrf-pride-pmc__get_full_text_section,mcp__sdrf-pride-pmc__get_pdf_by_unpaywall,mcp__sdrf-pride-pmc__searchClasses,mcp__sdrf-pride-pmc__getChildren"`

## Attack list — guilty until proven innocent
1. **Ontology**: every label+accession pair — exists, label EXACT, non-obsolete, from a family
   TERMS.tsv permits for that column. Cell lines especially: derivatives get substituted for parents
   (`HeLa`→`HeLa-MAGI-CCR5`/`HEp-2`; `A549`→`A549-CR`). Check CL/UBERON **definitions**, not labels.
2. **File mapping**: every `comment[data file]` real, unique, present. Any exclusion justified, not
   silent. If PRIDE exposes only ZIPs, an invented filename is otherwise undetectable — verify.
3. **Sample classification**: single cells vs pools vs dilutions vs blanks vs carrier. Does any row
   assert biological metadata for material with no cells? "Single-cell-equivalent" is a **mass**,
   not a count.
4. **Replicate structure**: one vial injected N times = 1 biological replicate, N technical.
5. **Modifications**: UNIMOD vs the paper's stated search settings. `UNIMOD:1`=Acetyl,
   `:21`=Phospho. Positional values in `PP=`, never `TA=`. Dimethyl: OLS returns `UNIMOD:510` (+6);
   heavy +8 is `UNIMOD:330`. Carbamidomethyl must NOT appear without an alkylation step.
6. **Cleavage agent** vs the paper's digestion AND search settings.
7. **Reserved words**: per each column's `allow_*` flags in the **RESOLVED** template — `parse_sdrf`
   does NOT enforce them, and TERMS.tsv disagrees with the resolved template on some columns.
8. **Column licensing**: every `characteristics[...]` must be licensed by a declared template.
   `genotype`/`phenotype` are licensed ONLY by `clinical-metadata`. Not checked by the validator —
   three reviewers missed this before a fourth caught it.
9. **Unsupported specificity**: values asserted where the paper is silent or the data lives only in
   a figure. **But** do not manufacture a finding if the producer went to a primary source you
   haven't checked (vendor pages, raw headers, deposited search outputs) — verify first. Producers
   have been RIGHT to contradict PRIDE.
10. **PRIDE fields are unreliable**: `instruments` and `modifications` are submitter-entered and
    wrong across this corpus; `is_open_access` is wrong in PRIDE *and* Europe PMC. Paper Methods
    outrank PRIDE; raw data outranks both.

**`parse_sdrf` exiting 0 proves well-formedness, never truth.** Independently measured: it silently
accepts `NCBITaxon:99999999`, `MS:9999999`, `EFO:9999999`, `BOGUSLABEL999`, `N/A` (#35). Treat a
clean pass as necessary, never sufficient. Mutation-test it if you rely on it.

## Known tool defects — do NOT report as artifact faults
`tools check` emits false-positive "hallucinated term" warnings from an offline map.
`tools score` wrongly calls the mass-tolerance columns "required" and rejects valid compound ages.
`sdrf-pipelines` lowercases `NT=` then issues a case-sensitive `exact=True` OLS query, so any
capitalised CL label (`T cell`) yields a spurious warning.

## Rules
Verify against primary sources yourself. Each finding cites column, row(s), claimed value, and
contradicting evidence. Do not soften findings. Do not manufacture them. Read the producer's report
— but treat it as **claims to test**, not evidence.

Record a passing verdict ONLY if it genuinely passes:
```
python3 tools/review_gate.py approve annotations/<PXD>.sdrf.tsv \
  --report <report.json> --reviewer rev-<PXD> --cwd /home/sachsenb/Development/sdrf-skills
```
If it fails, do NOT approve — report the blocking findings.

# sdrf-skills for Codex

## Installation

First, ensure submodules are initialized and install dependencies:

```bash
git submodule update --init --recursive
conda env create -f environment.yml && conda activate sdrf-skills
# Or: pip install -r requirements.txt
```

Symlink the skills and spec directories into your Codex agents skills path:

```bash
ln -s "$(pwd)/skills" ~/.agents/skills/sdrf-skills
ln -s "$(pwd)/spec" ~/.agents/skills/sdrf-skills/spec
```

Or copy both directories:

```bash
cp -r skills/ ~/.agents/skills/sdrf-skills/
cp -r spec/ ~/.agents/skills/sdrf-skills/spec/
```

## What it provides

15 structured workflows (SKILL.md files) that encode expert-level SDRF annotation methodology:

| Skill | Purpose |
|-------|---------|
| sdrf-setup | Install dependencies (parse_sdrf, techsdrf) — conda or pip setup |
| sdrf-knowledge | SDRF format rules, column names, ontology mappings |
| sdrf-templates | Template system, layer selection, mutual exclusivity |
| sdrf-annotate | Full annotation: PXD → PRIDE + paper → draft SDRF |
| sdrf-validate | Validation against templates + OLS checking |
| sdrf-improve | Quality scoring: specificity, completeness, consistency |
| sdrf-fix | Auto-fix UNIMOD swaps, case, format, artifacts |
| sdrf-terms | Ontology term lookup for any SDRF column |
| sdrf-brainstorm | Pre-annotation metadata planning |
| sdrf-review | Quality review with paper + PRIDE cross-reference |
| sdrf-explain | Plain-language SDRF education |
| sdrf-convert | Pipeline selection (MaxQuant, DIA-NN, quantms) |
| sdrf-design | Experimental design analysis |
| sdrf-contribute | Contribute annotation via PR to community repo |
| sdrf-techrefine | Verify/refine technical metadata from raw files via techsdrf |

## Usage

Each SKILL.md file contains a complete workflow. Reference them from your Codex instructions:

```text
When annotating SDRF files, follow the workflow in skills/sdrf-annotate/SKILL.md
```

## Required Annotation Behavior

When using these skills in Codex agents, enforce the following:

- Before article reading, scan PRIDE/FTP project files for sample metadata files (`.csv`, `.tsv`, `.txt`, sample sheets) and use them as primary mapping inputs.
- Reconcile full PRIDE file inventory (including paginated results) before mapping runs.
- Include `comment[file uri]` whenever PRIDE file URLs are available.
- Perform a strict full-paper pass (main text + supplementary tables/data) before finalizing annotation.
- Extract variable modifications explicitly from Methods/search settings and map to UNIMOD (e.g., Deamidation -> UNIMOD:7, Oxidation -> UNIMOD:35, Acetylation -> UNIMOD:1 when applicable).
- Build a sample-count model from article evidence first (`N_individuals`, pooled/control, timepoints/sample types).
- Infer "fractionated runs per individual" only under explicit conditions:
  - individuals are explicitly stated in article tables/text,
  - no additional sampling dimensions are reported,
  - raw file count mismatches implied sample count,
  - Methods/supplementary support fractionation (and/or technical replicate) evidence.
- Ensure fraction groups from the same sample keep identical sample-level metadata.
- If article/supplement evidence is insufficient for a field, use `not available` and document the gap instead of inferring from filenames alone.
- Use normalized filename matching for sidecar tables (treat `.`, `-`, `_` variants as equivalent before declaring no match).
- When consuming sidecar sample sheets, trim whitespace and support common column synonyms:
  - `Condition`/`Group` -> `characteristics[disease]` when it encodes disease/clinical group
  - `BioReplicate` -> `characteristics[biological replicate]`
  - `Run` -> `comment[technical replicate]` only if the sheet indicates replicate injections
- Disease normalization rule (applies to all datasets): if `characteristics[disease]` indicates healthy/normal control (e.g., "healthy", "healthy control", "normal control", "healthy patient"), normalize the value to exactly `normal`.
- Age inference rule (applies to all datasets): if the paper reports age as group summaries by disease/condition (e.g., Table 1: mean ± SD per group), infer per-sample `characteristics[age]` as a conservative range per group (e.g., 68 ± 8 → `60Y-76Y`) and apply it to all samples in that disease group; do not invent ages when no group age stats are reported.
- If full-text article/PDF or supplementary materials cannot be retrieved due to bot protection (e.g., HTTP 403, JS challenge, repeated timeouts), STOP and ask the user to download the files manually and provide a local path; proceed using the user-provided local files as the primary evidence source.
- Replicate semantics (applies to all datasets):
  - `characteristics[individual]` identifies the biological individual/sample origin. If evidence indicates each raw file is a unique participant/sample, assign a unique individual identifier per file. Prefer numeric identifiers (1..N) for stability.
  - `characteristics[biological replicate]` groups different individuals under the same condition as biological replicates. Only copy values from sidecars if they truly represent biological replicate numbering; do not confuse row index / run index with biological replicates.
  - `comment[technical replicate]` is ONLY for repeat measurements of the SAME sample (same individual) such as repeat injections/runs. Default to 1 unless the paper/supplement/sidecar explicitly indicates technical replicates.
  - Never set technical replicate >1 solely because there are many files. Decide using explicit evidence (terms like "technical replicate", "repeat injection", "duplicate runs", "replicate injections", "fractions").
- Sex inference guardrail (applies to all datasets): if cohort is explicitly sex-specific in the paper context (e.g., prostate cancer study) or the sidecar sample labels encode sex (e.g., "for male"), populate `characteristics[sex]` accordingly; otherwise use `not available`.
- Longitudinal/repeated-measure semantics (applies to all datasets):
  - If sidecar/paper maps multiple files to the same `Patient_ID` (or equivalent subject identifier), assign the same `characteristics[individual]` to all those rows.
  - Set `comment[technical replicate]` >1 ONLY for repeated measurements of the same individual at the same sampling time / same biological sample; keep timepoint-followup samples as separate non-technical measurements.
  - Set `characteristics[biological replicate]` by grouping different individuals sharing the same biological condition context (minimum: same `characteristics[disease]` and same `characteristics[sampling time]` when time is modeled).
- Always include mass tolerance columns:
  - Include both `comment[precursor mass tolerance]` and `comment[fragment mass tolerance]` in annotated SDRFs.
  - If Methods provide values, populate them directly (example: `20 ppm`, `50 ppm`); otherwise set `not available` for later refinement.
- Always include at least one factor column in final SDRF. Unless another experimental factor is explicit, include `factor value[organism part]` and mirror `characteristics[organism part]`.

## Prerequisites

These skills reference external APIs (OLS, PRIDE, PubMed) for ontology validation
and metadata retrieval. Configure appropriate API access in your Codex environment.

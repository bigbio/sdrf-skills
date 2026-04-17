## sdrf-skills Claude Plugin Notes

This plugin points to `skills/` workflows. Apply these annotation constraints when invoking `sdrf:annotate` and `sdrf:validate`:

- Before article/supplementary pass, scan PRIDE/FTP files for metadata sidecars (`.csv`, `.tsv`, `.txt`, sample sheets) and use them as primary sample-mapping evidence.
- Reconcile full PRIDE file inventory (including pagination/truncation checks).
- Include `comment[file uri]` when PRIDE URLs exist.
- Perform a strict full-paper pass (main text + supplementary tables/data) before finalizing SDRF.
- Extract variable modifications from Methods/search settings and include mapped UNIMOD terms in `comment[modification parameters]` (e.g., Deamidation/Acetylation when reported).
- Infer sample model from article evidence first (`N_individuals`, pooled/control, sampling dimensions).
- Only infer "fractionated runs per individual" if:
  - individuals are explicit in article text/tables,
  - no additional sampling dimensions are reported,
  - raw-file count mismatches implied sample count,
  - Methods/supplementary indicate fractionation and/or technical replicate evidence.
- For rows that are fractions of one sample, keep sample-level metadata consistent and vary only run-level fields.
- If supplementary mapping is unavailable/ambiguous, set uncertain fields to `not available` and report missing evidence.
- Normalize sample/file identifiers (`.`, `-`, `_`) for metadata-table matching before marking rows unmatched.
- When parsing metadata sidecars, trim whitespace and map common columns like `Condition` and `BioReplicate` to SDRF fields (disease/biological replicate) when applicable.
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
  - Set `comment[technical replicate]` >1 ONLY for repeated measurements of the same individual at the same sampling time / same biological sample; keep follow-up timepoint samples as separate non-technical measurements.
  - Set `characteristics[biological replicate]` by grouping different individuals sharing the same biological context (minimum: same `characteristics[disease]` and same `characteristics[sampling time]` when time is modeled).
- Always include mass tolerance columns:
  - Include `comment[precursor mass tolerance]` and `comment[fragment mass tolerance]`.
  - If Methods provide values, write them directly (example: `20 ppm`, `50 ppm`); otherwise use `not available`.
- Always include at least one factor column in final SDRF. Unless another explicit factor exists, include `factor value[organism part]` mirroring `characteristics[organism part]`.

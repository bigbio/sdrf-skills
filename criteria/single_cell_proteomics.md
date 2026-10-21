# Single-Cell Proteomics (SCP) — Screening Criteria

Screen PRIDE and MassIVE studies for **MS-based single-cell proteomics**, to shortlist
datasets for SDRF annotation with `/sdrf-skills:sdrf-campaign`.

## Inclusion rules

A study is `include` when **all** of the following hold:

1. **MS-based bottom-up proteomics.** The proteome is measured by mass spectrometry.
2. **Individual cells are the unit of measurement.** Single cells are physically
   isolated and acquired as distinct samples/runs — each quantitative observation
   traces to one identified cell.
3. **Raw MS files are deposited** for the single-cell runs (not only search results
   or processed matrices).

Recognised SCP methods (any one satisfies rule 2 when per-cell isolation is stated):
nanoPOTS / nanoPOTS-DIA, SCoPE-MS, SCoPE2, pSCoPE, plexDIA / mTRAQ,
CellenONE / proteoCHIP, cellenChip, N2 / OAD chip, microfluidic or FACS
one-cell-per-well sorting, laser-capture of single cells, iBASIL, T-SCP, SciProChip.

## Exclusion rules

Mark `exclude` when any of these clearly applies, and name the decisive rule.
Numbering continues from the inclusion rules, so every rule number is unique:

4. **Bulk proteomics** — many cells lysed together as one sample.
5. **Low-input but not single-cell** — sorted populations, tissue punches, or
   defined-N inputs (10/100/500 cells) with no single-cell condition. Note: many
   SCP papers include low-input *benchmarking* alongside true single cells — such a
   study is `include`, since the single-cell condition exists.
6. **Dilution mimics only** — bulk digest diluted to "single-cell-equivalent" load
   with no real cells isolated. This is a method-development artifact, not SCP.
7. **Not MS-based** — CyTOF, flow/mass cytometry, antibody arrays, Olink, CODEX.
8. **Single-cell transcriptomics only** — scRNA-seq with no single-cell proteome.
9. **Non-proteome MS** — metabolomics or lipidomics only.

## Uncertainty rule

Use `uncertain` — never guess — when the evidence cannot settle inclusion, e.g.:
- The abstract says "single-cell" but no full text is available to confirm real
  per-cell isolation rather than single-cell-equivalent loading.
- Cell counts per run are never stated.
- The PRIDE record is a partial/umbrella submission and the SCP portion is unclear.

State specifically what evidence was missing.

## Notes

- Prefer full-text Methods over abstract/title. Title/keyword matches alone are
  weak evidence for `include` — prefer `uncertain`.
- SCP is a young field: most datasets are post-2019. Do not exclude on date alone.

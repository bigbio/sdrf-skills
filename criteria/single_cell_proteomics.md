# Single-Cell Proteomics (SCP) — Screening Criteria

Screen PRIDE studies for **MS-based single-cell proteomics**, to shortlist datasets
for downstream SDRF annotation via `sdrf:autoresearch`.

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

Mark `exclude` when any of these clearly applies, and name the decisive rule:

1. **Bulk proteomics** — many cells lysed together as one sample.
2. **Low-input but not single-cell** — sorted populations, tissue punches, or
   defined-N inputs (10/100/500 cells) with no single-cell condition. Note: many
   SCP papers include low-input *benchmarking* alongside true single cells — such a
   study is `include`, since the single-cell condition exists.
3. **Dilution mimics only** — bulk digest diluted to "single-cell-equivalent" load
   with no real cells isolated. This is a method-development artifact, not SCP.
4. **Not MS-based** — CyTOF, flow/mass cytometry, antibody arrays, Olink, CODEX.
5. **Single-cell transcriptomics only** — scRNA-seq with no single-cell proteome.
6. **Non-proteome MS** — metabolomics or lipidomics only.

## Uncertainty rule

Use `uncertain` — never guess — when the evidence cannot settle inclusion, e.g.:
- The abstract says "single-cell" but no full text is available to confirm real
  per-cell isolation rather than single-cell-equivalent loading.
- Cell counts per run are never stated.
- The PRIDE record is a partial/umbrella submission and the SCP portion is unclear.

State specifically what evidence was missing.

## Fields to extract

Fill each field from PRIDE metadata or the publication. Use `unclear` if unsupported
by evidence. Keep values short and analysis-ready.

- `organism` — scientific name as reported (e.g. `Homo sapiens`, `Mus musculus`).
  Do NOT map to an NCBITaxon accession here; that happens during annotation.
- `cell_type` — cell line or primary cell type (e.g. `HeLa`, `U-937`, `CD4+ T cell`).
  Prefer the cell line name verbatim; `/sdrf:cellline` resolves Cellosaurus later.
- `isolation_method` — how single cells were isolated (`CellenONE`, `FACS`,
  `nanoPOTS`, `laser capture`, `microfluidic`, `manual picking`).
- `scp_method` — the named method/platform (`SCoPE2`, `plexDIA`, `nanoPOTS-DIA`, ...).
- `n_single_cells` — approximate number of single cells measured, as an integer if
  stated (`~1500`), else `unclear`. This drives the SDRF row count.
- `labelling` — `label free`, `TMT`, `TMTpro`, `mTRAQ`. Isobaric labelling implies
  multiplexed channels, which changes the SDRF row formula.
- `carrier_channel` — `yes` / `no` / `unclear`. Whether a booster/carrier proteome
  channel is used (characteristic of SCoPE-MS/SCoPE2). Load-bearing: the carrier is
  a distinct sample in SDRF and is a classic annotation error when omitted.
- `acquisition` — `DDA`, `DIA`, or both. Determines the acquisition-method template.
- `instrument` — instrument as reported (e.g. `Orbitrap Eclipse`, `timsTOF SCP`).
  Verbatim; OLS/MS-ontology mapping happens during annotation.
- `has_sdrf` — `yes` / `no`. Whether the PRIDE record already ships an `.sdrf.tsv`.
  Studies that already have one are lower priority for annotation.
- `publication` — `PMID:########` or `doi:10.xxxx/...`; `unclear` if none.

## Notes

- Prefer full-text Methods over abstract/title. Title/keyword matches alone are
  weak evidence for `include` — prefer `uncertain`.
- SCP is a young field: most datasets are post-2019. Do not exclude on date alone.
- `carrier_channel` and `n_single_cells` are the two fields most often wrong when
  inferred from the abstract. Take them from Methods or mark `unclear`.

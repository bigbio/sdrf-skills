# Reference: finding the channel-to-sample map (Step 6.1 of sdrf-annotate)

Read when the study is multiplexed (TMT, TMTpro, iTRAQ, plexDIA, dimethyl) and the
channel-to-sample map is not in the paper. Work the ladder in order; `build` refuses an
incomplete map and never fills a channel in.

### 6.1 Multiplexed: exhaust every source of the channel→sample map before BLOCKING
For TMT / TMTpro / plexDIA / dimethyl, each of the N rows per file needs a sample
identity, and inventing one is the worst failure this skill can produce. But a
missing map inside PRIDE is **not** proof that no map exists — for several
SCoPE2-lineage studies the layout files are deposited *outside* PRIDE entirely.
Work the ladder in order, and record in the report which rungs you checked:

1. **The paper + its supplementary** — a per-channel table, often Table S1.
2. **Deposited PRIDE files** (`files/all`) — a sample sheet, or per-channel sample
   names in the result tables. Beware the defaults that look like a map and are
   not: Proteome Discoverer writes every channel as `"Sample, n/a"` (and
   `StudyInformation.txt` as a bare `"Sample"` with empty groups), SpectroMine
   likewise. A generic label in all channels of all files means **no map**.
3. **Europe PMC supplementary** —
   `https://www.ebi.ac.uk/europepmc/webservices/rest/<PMCID>/supplementaryFiles`.
4. **External repositories cited in the Data Availability / Code Availability
   statement** (Step 1.4) — the rung most often skipped:

| Repository | Where to look |
|---|---|
| Zenodo | `https://zenodo.org/api/records/<record_id>` → `files[].links.self` |
| figshare | `https://api.figshare.com/v2/articles/<article_id>` |
| OSF | `https://api.osf.io/v2/nodes/<node_id>/files/` |
| Dryad | `https://datadryad.org/api/v2/datasets/doi%3A<encoded DOI>` |
| GitHub | the analysis repo — `annotation.csv`, layout/design files, the SCeptre/SCoPE2 config |

   Look for layout and sort files by name: `label_layout`, `sort_layout`,
   `sample_layout`, `file_sample_mapping`, `annotation.csv`, FACS exports, or a
   collated result object (`.h5ad`, `.rds`).

5. **Cross-validate what you reconstruct.** Rebuild the (file × channel) → sample
   map deterministically from the layout files, then check it against an
   independent artifact — the collated `.h5ad`/result matrix's cell identifiers,
   or the FACS export's per-cell records. Report the discrepancy count; a
   reconstruction you cannot cross-check is a hypothesis, not a map.

Layouts can **flip between runs** — never assume one layout covers every file.
Only after all five rungs are exhausted is the dataset BLOCKED; say in the report
which sources you checked and what each returned, so the block is auditable
rather than a shrug.

> **Worked example (PXD053053, TMTpro-16).** PRIDE had no usable map — the
> deposited PD `StudyInformation.txt` marked all 16 channels of all 96 files with
> the generic default, and the supplementary `mmc1.xlsx` was a generic-labelled
> abundance matrix. The real map was in the paper's **Zenodo deposit (record
> 12615623)**, cited in Data Availability: SCeptre `label_layout` / `sort_layout` /
> `sample_layout` / `file_sample_mapping`, plus `compiled_FACS_data.txt` (all 1152
> sorted cells with hypoxia time point and FUCCI phase) and
> `scMS_filtered_data.h5ad`. Reconstructed from the layout files and cross-checked
> against the h5ad QC cells: **0 discrepancies**, 1344 annotatable rows instead of
> a false BLOCK. PXD040455's map was likewise in a published Table S1, not in PRIDE.

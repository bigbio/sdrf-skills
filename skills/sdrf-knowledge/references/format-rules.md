# SDRF format rules — the one canonical copy

Every skill that writes or checks an SDRF points here. Edit this file, not a copy of it:
the same rules used to live in `sdrf-annotate`, `sdrf-fix` and `sdrf-knowledge` and drifted.
`sdrf-tools contract` prints the per-column consequences (value form, reserved words) for a
template union; this file is the reasoning behind them.

## Core Format Rules

- SDRF is a **tab-delimited TSV** file (extension: `.sdrf.tsv`)
- Each **row** = one MS run (one raw file linked to one sample via a label channel)
- Each **column** = a property of the sample or run
- Column names are **case-sensitive** and follow the patterns above
- First column is always `source name` (unique biological sample identifier)
- Row identity: (`source name`, `assay name`, `comment[label]`) MUST be unique (error); (`source name`, `assay name`) SHOULD be unique (warning). In multiplexed (TMT/iTRAQ) data the same `assay name` deliberately repeats across label channels, so `source name`+`assay name` alone is NOT unique.
- De-duplication coordinate: (`source name`, `characteristics[biological replicate]`, `comment[technical replicate]`, `comment[fraction identifier]`) must be unique across rows — never use `technical replicate` or `fraction identifier` as a row counter
- No trailing whitespace in any cell or column name
- No empty cells in required columns
- **Data files are vendor RAW** (`.raw`/`.d`/`.wiff`/`.wiff2`) in `comment[data file]` — never peak lists (`.mgf`/`.mzML`/`.mzXML`); a peak-list reference validates structurally but breaks reprocessing
- **At least one `factor value[...]`** column must be present (the experimental variable)
- **Acquisition method**: `comment[proteomics data acquisition method]` is REQUIRED for MS files and must be a descendant of `PRIDE:0000659` (DDA `PRIDE:0000627`, DIA `PRIDE:0000450`, PRM `PRIDE:0000629`, SRM `PRIDE:0000630`); never `NCIT:C161786`/`MS:1000206`, and there is no `comment[dia method]` column
- **Carrier / reference channels** (single-cell / TMT): `comment[carrier channel]` = `PRIDE:0000901`, `comment[reference channel]` = `PRIDE:0000899` (not `PRIDE:0000941`/`0000942`); values are TMT channel labels (e.g. `TMT131C`)
- **Never write SDRF with pandas `to_csv`** — it renames legitimately repeated headers (`comment[modification parameters].1`); write raw TSV preserving duplicated column names
- **Multiple values = repeat the whole column** with the same header (there is no delimiter-separated list)

## Writing SDRF Safely (writer-side rules)

Every rule here corresponds to a defect class found across the public annotated corpus.
They are cheap to honour when writing and expensive to find later, because each one
**parses into the wrong thing instead of failing loudly** — the file still validates.

1. **An accession always carries its ontology prefix.** `AC=MS:1001251`, never `AC=1001251`.
   A bare number is unresolvable and the intended ontology is only recoverable from context.
2. **Prefix and id are separated by a colon**, never an underscore: `PRIDE:0000568`, not
   `PRIDE_0000568`.
3. **The accession for a term is constant.** If several rows carry the same `NT=`, they carry
   the same `AC=`. An accession that increments down the rows (`MS:1001309`, `MS:1001310`,
   `MS:1001311`, … all labelled `Lys-C`) is a generator bug — it names a different, real,
   wrong term on every row.
4. **Never emit Python repr into a cell.** No `['C']`, `None`, `nan`, `null`, `"['breast cancer']"`.
   Watch key=value fields especially: `TA=['C']` must be `TA=C` — a whole-cell artifact check
   will not catch one nested inside `NT=…;AC=…;TA=…`.
5. **Do not let a CSV writer quote the value.** `"NT=timsTOF HT;AC=MS:1003404"` is a value whose
   first character is a quote, not a quoted value, once it is read as TSV.
6. **Reserved words are written bare**, never wrapped: `not applicable`, not
   `NT=not applicable;AC=not available`.
7. **Never write SDRF with pandas `to_csv`.** It renames legitimately repeated columns
   (`comment[modification parameters].1`), which silently turns one repeated column into several
   distinct ones, so a reader keyed on the name sees only the first. Write raw TSV lines and
   preserve duplicate headers exactly.
8. **Ages carry a unit** from `Y`/`M`/`W`/`D`: `58Y`, not `58` and not `58 years`.
9. **One value per cell.** Several modifications means several
   `comment[modification parameters]` columns — never concatenate them into one cell.

`tools/sdrf_fixer.py` repairs 1, 2, 4, 5, 6, 7 and 8 deterministically; run it before
presenting or contributing any SDRF you generated.

## Column Type System

| Type | Format | Purpose |
|------|--------|---------|
| **anchor column** | bare name | Identity/infrastructure (`source name`, `assay name`, `technology type`) |
| **characteristics** | `characteristics[x]` | Sample properties ("what is this sample?") |
| **comment** | `comment[x]` | Technical/run properties ("how was it measured?") |
| **factor value** | `factor value[x]` | Experimental variable ("what are we comparing?") |

## Value Encoding: characteristics vs comment

Sample metadata and technical metadata are encoded differently:

- **`characteristics[...]` → bare ontology label (free text).** Write the value as the
  OLS term's label only — **not** `NT=;AC=`. For example use `Homo sapiens`, not
  `NT=Homo sapiens;AC=NCBITaxon:9606`; `liver`, not `NT=liver;AC=UBERON:0002107`;
  `lung adenocarcinoma`, not `NT=lung adenocarcinoma;AC=MONDO:0005097`. The validator
  resolves the label to its accession, so the bare label is complete.
- **`comment[...]` → keep the `NT=<OLS label>;AC=<accession>` key-value form** (instrument,
  cleavage agent details, modification parameters, proteomics data acquisition method, etc.).

Exceptions (kept structured, not converted to a bare label):
- Structured `characteristics` that carry qualifier keys — `characteristics[spiked compound]`
  (`CT=`/`QY=`/`PS=`), `characteristics[pooled sample]` (`SN=`) — keep their key-value form.
- `characteristics[age]` and similar pattern values (`50Y`) are not ontology terms.
- `factor value[...]` mirrors the column it derives from: bare label if it mirrors a
  `characteristics` column, `NT=;AC=` if it mirrors a `comment` column.

## Reserved Words

These values have special meaning in SDRF:
- `not available` — information exists but was not provided
- `not applicable` — information does not apply to this sample
- `pooled` — sample is pooled from multiple sources
- `normal` — healthy/control sample (for disease column, use with PATO:0000461)
- `anonymized` — value withheld for privacy (used for age, sex in human data)

NEVER use: "N/A", "NA", "n/a", "null", "none", "unknown", "Unknown" — always use the exact reserved words above. Check TERMS.tsv `allow_not_available`, `allow_not_applicable`, `allow_pooled` fields to know which reserved words are valid for each column.

## Modification Parameter Format

The format for `comment[modification parameters]` is strict:
```text
NT=<name>;AC=UNIMOD:<id>;TA=<target amino acid>;MT=<Fixed|Variable>
```

For protein/peptide-level position modifications, use PP instead of TA:
```text
NT=Acetyl;AC=UNIMOD:1;PP=Protein N-term;MT=Variable
NT=TMT6plex;AC=UNIMOD:737;PP=Any N-term;MT=Fixed
```

Multiple modifications → use SEPARATE `comment[modification parameters]` columns (one per modification).

### UNIMOD Swap Warnings (Expertise — memorize these)

These are the most common annotation errors. They are expertise, not spec data:

| Modification | CORRECT | Common WRONG | Why it matters |
|---|---|---|---|
| Acetyl (N-term) | UNIMOD:1 | UNIMOD:21 (Phospho!) | Wrong search: acetylation vs phosphorylation |
| Phospho | UNIMOD:21 | UNIMOD:1 (Acetyl!) | Wrong search: phosphorylation vs acetylation |
| Oxidation | UNIMOD:35 | UNIMOD:34 (Methyl!) | Wrong mass: +16 vs +14 |
| Methyl | UNIMOD:34 | UNIMOD:35 (Oxidation!) | Wrong mass: +14 vs +16 |
| TMTpro (16/18plex) | UNIMOD:2016 | UNIMOD:737 (TMT6plex) | Wrong mass: +304 vs +229 |

The UNIMOD:1 ↔ UNIMOD:21 swap is the **#1 most common error** in SDRF files (~45% of all issues).

## Label Types

| Label Type | comment[label] value | Rows per raw file |
|---|---|---|
| Label-free | `label free sample` | 1 row per file |
| TMT6plex | `TMT126`, `TMT127N`, `TMT127C`, `TMT128N`, `TMT128C`, `TMT129N` | 6 rows per file |
| TMT10plex | TMT126 through TMT131N | 10 rows per file |
| TMT11plex | TMT126 through TMT131C | 11 rows per file |
| TMT16plex (TMTpro) | TMT126 through TMT134N | 16 rows per file |
| TMT18plex (TMTpro) | TMT126 through TMT135N | 18 rows per file |
| SILAC | `SILAC light`, `SILAC medium`, `SILAC heavy` | 2-3 rows per file |
| iTRAQ4plex | `iTRAQ114`, `iTRAQ115`, `iTRAQ116`, `iTRAQ117` | 4 rows per file |

Row count formula:
```text
Rows = samples × fractions × label_channels × technical_replicates
```

## Common Errors to Watch For (Expertise)

1. **UNIMOD:1 vs UNIMOD:21 swap** — Acetyl is 1, Phospho is 21 (most common error, ~45%)
2. **Missing ontology prefix** — "0000305" instead of "EFO:0000305"
3. **Case mismatch** — "Male" instead of "male" (SDRF values are lowercase)
4. **Python artifacts** — "['value']" instead of "value"
5. **DIA mislabeling** — Use `NT=Data-independent acquisition;AC=PRIDE:0000450` (OLS label as written + accession under PRIDE:0000659)
6. **Wrong reserved word** — "N/A", "NA", "unknown" instead of "not available"
7. **Age format** — "58 years" instead of "58Y"
8. **Missing AC= in instruments** — Just "Q Exactive" without `AC=MS:1001911;NT=Q Exactive`
9. **Trailing whitespace** — Invisible spaces at end of values or column names
10. **Wrong column name format** — "Organism" instead of "characteristics[organism]"
11. **UNIMOD:34 vs UNIMOD:35 swap** — Methyl is 34, Oxidation is 35
12. **TMTpro accession** — TMT16/18plex uses UNIMOD:2016, NOT UNIMOD:737

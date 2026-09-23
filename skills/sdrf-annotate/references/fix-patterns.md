# Reference: error patterns and their fixes (review mode of sdrf-annotate)

`sdrf-tools fix <file> -o <out>` repairs the deterministic ones and writes a changelog; the rest need
judgement and evidence. Fix values in `samples.tsv` / `technical.tsv` and rebuild when the file came
from `build`; edit the SDRF only when it did not.

## Common Error Patterns and Their Fixes

> The rules these patterns violate are stated once in
> [format-rules.md](format-rules.md);
> this list is the diagnostic side.

### 1. UNIMOD Accession Swaps (45% of all errors)
| Wrong | Correct | Modification |
|-------|---------|-------------|
| UNIMOD:21 for Acetyl | UNIMOD:1 | Acetyl |
| UNIMOD:1 for Phospho | UNIMOD:21 | Phospho |
| UNIMOD:34 for Oxidation | UNIMOD:35 | Oxidation |
| UNIMOD:35 for Methyl | UNIMOD:34 | Methyl |

**Fix**: Parse NT= field, look up correct UNIMOD accession, replace AC= field.

### 2. Missing Ontology Prefix (30%)
| Wrong | Correct |
|-------|---------|
| `0000305` | `EFO:0000305` |
| `9606` | `NCBITaxon:9606` |
| `0002107` | `UBERON:0002107` |

**Fix**: Detect bare numbers, infer ontology from column type, add prefix.

### 3. Case Normalization (25%)
| Wrong | Correct |
|-------|---------|
| `Male` | `male` |
| `Female` | `female` |
| `Homo Sapiens` | `Homo sapiens` |
| `Not Available` | `not available` |

**Fix**: Lowercase sex values and reserved words. Organism names follow binomial rules (capital genus, lowercase species).

### 4. Python/Programming Artifacts (15%)
| Wrong | Correct |
|-------|---------|
| `['breast cancer']` | `breast cancer` |
| `nan` | `not available` |
| `None` | `not available` |
| `""` | (empty or `not available`) |

**Fix**: Strip brackets, quotes; replace nan/None with reserved words.

### 5. Reserved Word Standardization
| Wrong | Correct |
|-------|---------|
| `N/A` | `not applicable` |
| `NA` | `not available` |
| `n/a` | `not applicable` |
| `unknown` | `not available` |
| `null` | `not available` |
| `-` | `not available` |

**Fix**: Replace with correct SDRF reserved words.

### 6. DIA/DDA Terminology
| Wrong | Correct |
|-------|---------|
| `data-dependent acquisition` / `DDA` | `NT=Data-dependent acquisition;AC=PRIDE:0000627` |
| `data-independent acquisition` / `DIA` | `NT=Data-independent acquisition;AC=PRIDE:0000450` |
| `PRM` | `NT=Parallel reaction monitoring;AC=PRIDE:0000629` |
| `SRM` / `MRM` | `NT=Selected reaction monitoring;AC=PRIDE:0000630` |

**Fix**: Use `NT=<OLS label>;AC=<accession>` — the OLS label written as-is (e.g. `Data-dependent acquisition`, sentence case, not Title Case) with its accession, a descendant of `PRIDE:0000659`. DIA variants (diaPASEF, SWATH) map to `PRIDE:0000450`.

### 7. Age Format
| Wrong | Correct |
|-------|---------|
| `58 years` | `58Y` |
| `58` | `58Y` |
| `6 months` | `6M` |
| `14 days` | `14D` |
| `58yo` | `58Y` |

**Fix**: Extract number, map unit to Y/M/D suffix.

### 8. Modification Parameter Format
| Wrong | Correct |
|-------|---------|
| `Carbamidomethyl (C)` | `NT=Carbamidomethyl;AC=UNIMOD:4;TA=C;MT=Fixed` |
| `Oxidation (M)` | `NT=Oxidation;AC=UNIMOD:35;TA=M;MT=Variable` |
| `NT=Acetyl;AC=UNIMOD:1;TA=Protein N-term` | `NT=Acetyl;AC=UNIMOD:1;PP=Protein N-term;MT=Variable` |

**Fix**: Parse free-text mods, construct proper NT/AC/TA/MT format.

### 9. Trailing Whitespace
**Fix**: Trim all cell values and column names.

### 10. Instrument Format
| Wrong | Correct |
|-------|---------|
| `Q Exactive` | `AC=MS:1001911;NT=Q Exactive` |
| `Orbitrap Fusion Lumos` | `AC=MS:1002732;NT=Orbitrap Fusion Lumos` |

**Fix**: If missing AC= format, search OLS MS ontology and construct proper format.
```text
mcp OLS → searchClasses(query="<instrument>", ontologyId="ms")
```

### 11. Characteristics as bare ontology label
Sample metadata uses the plain label; only `comment[...]` keeps `NT=;AC=`.

| Column | Wrong | Correct |
|--------|-------|---------|
| `characteristics[organism]` | `NT=Homo sapiens;AC=NCBITaxon:9606` | `Homo sapiens` |
| `characteristics[disease]` | `NT=lung adenocarcinoma;AC=MONDO:0005097` | `lung adenocarcinoma` |
| `comment[cleavage agent details]` | — | `NT=Trypsin;AC=MS:1001251` *(unchanged — comment keeps NT/AC)* |

**Fix**: For a `characteristics[...]` value that is a pure `NT=<label>;AC=<accession>` pair,
replace it with `<label>`. Leave structured characteristics (`spiked compound` `CT=`/`QY=`,
`pooled sample` `SN=`) and every `comment[...]` value untouched.

### 12. Writer artifacts (accession syntax, Python repr, CSV quoting)
Faults that survive validation because they parse into something wrong rather than failing.

| Wrong | Correct | Why |
|-------|---------|-----|
| `AC=1001251` | `AC=MS:1001251` | a bare number is unresolvable |
| `AC=PRIDE_0000568` | `AC=PRIDE:0000568` | colon separates prefix and id |
| `TA=['C']` | `TA=C` | Python list left inside a key=value field |
| `"NT=Trypsin;AC=MS:1001251"` | `NT=Trypsin;AC=MS:1001251` | CSV writer quoted the value |
| `NT=not applicable;AC=not available` | `not applicable` | reserved words are written bare |
| `comment[modification parameters].1` | `comment[modification parameters]` | pandas suffix splits a repeated column |
| `NT=Lys-C;AC=MS:1001309`, `…1310`, `…1311` | all `AC=MS:1001309` | an accession must not increment per row |

**Fix**: `sdrf-tools fix <file>` handles all of these. The bare-accession prefix is only
restored when the column maps to exactly one ontology, so an ambiguous column is left alone;
an incrementing accession needs the correct term confirmed before collapsing the run.

### 13. Spike-in amounts modeled as factor value

A quantity that was added to the sample during preparation (a spiked protein/peptide/mixture
and how much of it) describes what the sample *is*, not a studied experimental variable — it
belongs in sample metadata, not `factor value[...]`.

| Wrong | Correct |
|-------|---------|
| `factor value[enolase spike ratio]` = `10` | `characteristics[spiked compound]` = `CT=protein;AC=P00924;CN=Enolase spike;QY=10` |
| `factor value[spike protein]` = `Enolase spike` (one label per row) | one `characteristics[spiked compound]` column per spiked component, repeated across rows |

**Fix**: Use `characteristics[spiked compound]` (see SAMPLE-GUIDELINES.adoc §Spiked-in Samples)
with `CT=`/`QY=`/`PS=`/`AC=`/`CN=`/`CV=` key-value pairs — repeat the column once per spiked
component when a row has more than one. Reserve `factor value[...]` for the variable the
experiment is actually comparing (genotype, treatment, dose group, timepoint); a reference/
benchmark dataset with no such comparison correctly has no factor value at all (the
`no_factor_value` advisory is expected, not a defect to paper over with an unrelated column).

## When NOT to Auto-Fix

- Values that might be intentionally different (ask the user)
- Ontology terms where the "correct" version is ambiguous
- Missing columns (suggest but don't add without user approval)
- Factor values (design decisions — always ask). This does not cover miscategorization: a
  `factor value[...]` column holding a sample property (spike-in amount, concentration, etc.)
  instead of the compared variable is fixable per rule 13, not a design decision to preserve.
- Cell line names (need Cellosaurus verification)
- Organism names that might be intentional (e.g., hybrid organisms)

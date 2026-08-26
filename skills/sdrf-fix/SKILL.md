---
name: sdrf:fix
description: Use when the user has an SDRF file with known errors and wants them fixed automatically. Triggers on requests to fix, correct, or repair SDRF errors.
user-invocable: true
argument-hint: "[file path or paste SDRF content]"
---

# SDRF Auto-Fix Workflow

You are fixing known common errors in an SDRF file. Apply fixes systematically.

## Step 0: Check parse_sdrf availability

Verify that `parse_sdrf` is available (run `parse_sdrf --version` or `which parse_sdrf`). If it is not installed:
- Inform the user that re-validation after fixes will need to be done manually
- Suggest `/sdrf:setup` or `conda env create -f environment.yml && conda activate sdrf-skills` (or `pip install -r requirements.txt`)
- Continue with the fixes; the user can validate later once dependencies are installed

## Common Error Patterns and Their Fixes

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

**Fix**: `python -m tools fix <file>` handles all of these. The bare-accession prefix is only
restored when the column maps to exactly one ontology, so an ambiguous column is left alone;
an incrementing accession needs the correct term confirmed before collapsing the run.

## Fix Procedure

1. **Parse** the SDRF into a structured table
2. **Scan** every cell for each error pattern above
3. **Apply fixes** — for ontology-dependent fixes, verify via OLS before changing
4. **Log changes** — track every change made (row, column, old value, new value, reason)
5. **Present changelog** to user before outputting the fixed SDRF
6. **Output** the corrected SDRF as a TSV code block

## Changelog Format

```text
Changes Applied:
  Row 3, comment[modification parameters]:
    OLD: NT=Acetyl;AC=UNIMOD:21;TA=Protein N-term;MT=Variable
    NEW: NT=Acetyl;AC=UNIMOD:1;PP=Protein N-term;MT=Variable
    FIX: UNIMOD:21 is Phospho, not Acetyl. Correct accession is UNIMOD:1. Also TA→PP for position.

  Row 5, characteristics[sex]:
    OLD: Male
    NEW: male
    FIX: Sex values must be lowercase per SDRF specification.

  All rows, comment[data file]:
    FIX: Trimmed trailing whitespace from 12 values.

Summary: 15 fixes applied (3 UNIMOD corrections, 5 case fixes, 7 whitespace trims)
```

## Step After Fixes: Re-Validate with sdrf-pipelines

After applying all fixes, **always** run programmatic validation before presenting
results to the user.

### 1. Update spec to latest version
```bash
git submodule update --remote --recursive
```

### 2. Run sdrf-pipelines validation
Save the fixed SDRF to a file and validate with the detected templates:
```bash
parse_sdrf validate-sdrf \
  --sdrf_file fixed.sdrf.tsv \
  --template <template1> \
  --template <template2>
```
Detect templates from `comment[sdrf template]` columns in the SDRF.
If `parse_sdrf` is not installed, tell the user: `pip install sdrf-pipelines`

### 3. Interpret results
1. If validation passes → present the changelog + fixed SDRF to the user
2. If validation finds new errors → fix them and re-run until clean
3. Verify fixed UNIMOD accessions match the NT= modification names
4. Read `spec/sdrf-proteomics/TERMS.tsv` and check `allow_not_available`/`allow_not_applicable` fields
5. Count: total fixes applied, remaining issues not auto-fixable

Present the re-validation summary alongside the changelog.

If all errors are fixed and the SDRF is for a ProteomeXchange dataset (PXD accession),
suggest contributing the corrected annotation via `/sdrf:contribute {PXD}` to the
`sdrf-annotated-datasets` community repository.

## When NOT to Auto-Fix

- Values that might be intentionally different (ask the user)
- Ontology terms where the "correct" version is ambiguous
- Missing columns (suggest but don't add without user approval)
- Factor values (design decisions — always ask)
- Cell line names (need Cellosaurus verification)
- Organism names that might be intentional (e.g., hybrid organisms)

---
name: sdrf:cellline
description: Use when the user needs to look up cell line metadata or enrich an SDRF with cell-line-derived characteristics (organism, disease, sex, sampling site, ancestry, age). Triggers on cell line names (HeLa, MCF-7, A549, …), Cellosaurus accessions (CVCL_XXXX), or "annotate cell line" requests.
user-invocable: true
argument-hint: "[cell line name | CVCL_XXXX | path/to/file.sdrf.tsv]"
---

# SDRF Cell Line Annotation

You are translating cell line identity into the SDRF columns required by the
`cell-lines` template. The source of truth is **Cellosaurus** (SIB / Expasy) —
it is *not* hosted on EBI OLS, so this skill queries Cellosaurus directly. OLS
is still used for the *target* ontologies the SDRF columns reference
(NCBITaxon, MONDO, UBERON, HANCESTRO, CLO/BTO/EFO). This skill encodes the
*rules* for the translation — it does not ship a local database.

## Cellosaurus access

| Mode | Endpoint / file | Notes |
|---|---|---|
| Web (browse) | `https://www.cellosaurus.org/<CVCL_id>` | Human-readable record. |
| REST API (JSON) | `https://api.cellosaurus.org/cell-line/<CVCL_id>?format=json` | Single-entry fetch; preferred for accession lookups. |
| REST search | `https://api.cellosaurus.org/search/cell-line?q=<query>&format=json` | Free-text / field-qualified search (`id:HeLa`, `sy:HeLa-S3`). |
| Bulk download | `https://ftp.expasy.org/databases/cellosaurus/cellosaurus.txt` (flat) <br> `https://ftp.expasy.org/databases/cellosaurus/cellosaurus.obo` (OBO) <br> `https://ftp.expasy.org/databases/cellosaurus/cellosaurus.xml` (XML) | Offline / batch use only. Re-download monthly to stay current. |

Use the REST API by default. Drop to the bulk file only when the user asks for
offline mode or needs to enrich many SDRFs in one pass.

## When to Use

- A single cell line lookup ("What is HeLa?" / "Look up CVCL_0030").
- Enriching an SDRF where `characteristics[cell line]` is filled but the
  Cellosaurus-derivable columns (organism, disease, sampling site, sex,
  ancestry, age, developmental stage, cellosaurus accession/name) are blank,
  generic, or inconsistent.
- Resolving ambiguous cell line names raised by `/sdrf:annotate`,
  `/sdrf:validate`, or `/sdrf:fix`.

For pure ontology-term lookup unrelated to cell lines, use `/sdrf:terms`.

## Step 0: Identify the cell-lines template requirements

**Always read the template first** — column names, requirement levels, and
target ontologies must come from the spec, never from memory.

```text
Read: spec/sdrf-proteomics/sdrf-templates/cell-lines/{version}/cell-lines.yaml
```

Required columns supplied by Cellosaurus (most current spec):

Flat-file field codes are the two-letter codes in `cellosaurus.txt` (`ID`, `AC`,
`SY`, `OX`, `DI`, `DR`, `SX`, `AG`, …); JSON field names from the REST API are
listed in Step 2a.

| SDRF column | Source field in Cellosaurus (flat / JSON) | Target ontology |
|---|---|---|
| `characteristics[cell line]` | `ID` / `identifier` | CLO / BTO / EFO |
| `characteristics[cellosaurus accession]` | `AC` / `accession` | Cellosaurus (`CVCL_XXXX`) |
| `characteristics[cellosaurus name]` | `ID` / `identifier` | Cellosaurus |
| `characteristics[disease]` | `DI` / `disease-list` (NCIt / ORDO) | MONDO / EFO / DOID — translate via OLS xrefs |
| `characteristics[sampling site]` | `DR` (derived-from-site) / `derived-from` | UBERON / BTO |
| `characteristics[ancestry category]` | `OX` / `species-list` population annotation | HANCESTRO |
| `characteristics[developmental stage]` | `AG` / `age` (donor age class) | EFO |

The `cell-lines` template **also requires** an organism layer
(`human` / `vertebrates` / `invertebrates`), which contributes
`characteristics[organism]`. Take the species from Cellosaurus's `OX` line
(taxon ID) and verify against the organism template's NCBITaxon column.

## Step 1: Normalize the input

Cell line names in the wild are messy. Apply this pipeline before any lookup:

1. **Strip enclosing punctuation/quotes/brackets.**
   `"['HeLa']"` → `HeLa`. (The `/sdrf:fix` artifact rule handles this; rerun if dirty.)
2. **Trim whitespace** at both ends.
3. **Recognize an accession directly.**
   Pattern `^CVCL_[A-Z0-9]{4,}$` → skip name lookup, fetch the accession.
4. **Build a normalized key** for matching only (do not store this):
   `lower(input)` with `[\s\-_]+` collapsed away.
   So `HeLa-S3`, `hela s3`, `HELA_S3`, `hela.s3` all key to `helas3`.
5. **Reject obvious non-cell-lines.** Reserved words (`not available`,
   `not applicable`), tissue names without a clonal identifier, and primary
   tissue codes are not cell lines — return early and tell the user.

## Step 2: Look up Cellosaurus

### 2a. Online (default)

```text
By accession (CVCL_XXXX):
  GET https://api.cellosaurus.org/cell-line/<CVCL_id>?format=json

By name (exact, then synonyms):
  GET https://api.cellosaurus.org/search/cell-line?q=id:<name>&format=json
  GET https://api.cellosaurus.org/search/cell-line?q=sy:<name>&format=json

By normalized key (last resort, broad search):
  GET https://api.cellosaurus.org/search/cell-line?q=<normalized>&format=json
```

A JSON response carries a `Cellosaurus.cell-line-list` array. For each hit, read
`identifier` (recommended name), `accession`, `name-list` (synonyms with
`type=synonym`), `species-list` (NCBI taxon), `disease-list` (NCIt / ORDO
xrefs), `derived-from`, `category`, `sex`, `age`, and `xref-list` (which
includes CLO / BTO / EFO cross-references — see Step 4.1).

If the API is unreachable (network blocked, rate-limited), fall back to 2b.

### 2b. Offline (bulk file)

If the user has downloaded the bulk release, point them to one of:

```text
~/cellosaurus.txt   # flat-file format, grep-friendly
~/cellosaurus.obo   # OBO, parsable with standard tools
~/cellosaurus.xml   # XML, machine-readable
```

Download command (only suggest if the user has no copy):
```bash
curl -sSLO https://ftp.expasy.org/databases/cellosaurus/cellosaurus.txt
```

For ad-hoc lookups in the flat file:
```bash
# By accession
awk -v RS='//' '/AC   CVCL_0030/' cellosaurus.txt
# By name (case-insensitive, exact line match on ID or SY)
awk -v RS='//' 'BEGIN{IGNORECASE=1} /^ID   HeLa$|^SY[^\n]*\bHeLa\b/' cellosaurus.txt
```

Never paste large excerpts of the file into the SDRF — extract only the fields
needed for Step 4.

## Step 3: Disambiguation rules

When Step 2 yields more than one candidate, pick in this order:

1. **Exact accession match** wins outright.
2. **Exact recommended-name match** on `identifier` (case-sensitive).
3. **Exact synonym match** in `name-list` entries with `type=synonym`.
4. **Parent-line preference**: if both a parent (`HeLa`, CVCL_0030) and a
   subclone (`HeLa-S3`, CVCL_0058) match, prefer the parent only when the
   user input has no qualifier. If the input contains a digit, letter suffix,
   or `-` segment (e.g. `HeLa-S3`, `K562/ADR`), prefer the subclone.
5. **Hybrid / hybridoma / patient-derived** lines (Cellosaurus category
   `Hybridoma`, `Patient-derived xenograft cell line`) are valid hits — flag
   them in the report so reviewers know the donor metadata semantics differ.
6. **Multiple plausible canonical hits** → do not guess. Present the top 3 to
   the user with accession + species + disease and ask which one. Common
   ambiguous queries: `293`, `SK`, `HCT`, `HEK`, `T-47`.

If nothing matches:
- Suggest the user check spelling, then offer `/sdrf:terms cell line "<name>"`
  for a broader CLO/BTO/EFO search.
- Set `characteristics[cell line]` to the user's input verbatim and the rest of
  the cell-line columns to `not available` (never `N/A`, never `unknown`).

## Step 4: Translate Cellosaurus → SDRF

For each matched cell line, fill columns from these rules. CVCL accessions are
verified against Cellosaurus (Step 2). Every other accession written to the
SDRF (`NCBITaxon:*`, `MONDO:*`, `UBERON:*`, `HANCESTRO:*`, `EFO:*`) must be
verified via OLS before writing.

### 4.1 Direct fields

| SDRF column | Rule |
|---|---|
| `characteristics[cellosaurus accession]` | `CVCL_XXXX` from the primary accession. |
| `characteristics[cellosaurus name]` | Recommended name (`identifier` field) exactly as Cellosaurus returns it. |
| `characteristics[cell line]` | Same as recommended name unless Cellosaurus's `xref-list` has a CLO / BTO / EFO cross-reference whose label is preferred by the lab. Verify any such alias resolves in OLS (`searchClasses(query="<alias>", ontologyId="clo")` etc.) before writing it. |

### 4.2 Organism (cross-template)

Cellosaurus `OX` gives `NCBI_TaxID=<n>; ! <species>`. Translate:

- Look up `NCBITaxon:<n>` via OLS. Use the canonical label
  (e.g. `Homo sapiens`, not `human`) for `characteristics[organism]`.
- If species ≠ what the chosen organism layer template covers
  (`human` = 9606, `vertebrates` = non-human vertebrates, `invertebrates` =
  the rest), warn: the user picked the wrong organism template.

### 4.3 Disease (NCIt → MONDO/EFO)

Cellosaurus `DI` lines reference NCIt (e.g. `NCIt; C27677; …`). The SDRF
`disease` column wants MONDO / EFO / DOID / PATO (per TERMS.tsv).

Translation steps:

1. Get the NCIt term via OLS: `searchClasses(query="<NCIt id>", ontologyId="ncit")`.
2. Read its `cross_references`. Prefer in this order: MONDO > EFO > DOID.
3. If no cross-reference exists, search the NCIt label text in MONDO:
   `searchClasses(query="<label>", ontologyId="mondo")`. Choose the closest
   match by exact label, then by synonym.
4. If the donor was healthy (Cellosaurus `DI` absent or "Normal tissue"), set
   `characteristics[disease]` to `normal` (per the `cell-lines` template
   guidance), not "not applicable".
5. Multiple `DI` lines → use the most specific one; record the others in
   `comment[disease history]` only if the template extends that column.

### 4.4 Sampling site / cell type

Cellosaurus `DR` and `SX` describe origin tissue/cell type.

- `characteristics[sampling site]` ← UBERON term for the tissue. Use OLS
  `searchClasses(query="<site>", ontologyId="uberon")`. Fall back to BTO if
  UBERON has no exact match.
- If the source is a fluid (blood, plasma, ascites), use the UBERON term for
  the fluid; do not invent a tissue.
- If origin is "embryonic kidney" or "fetal liver", set
  `characteristics[developmental stage]` to `embryonic` / `fetal` (EFO terms)
  alongside the sampling site.

### 4.5 Sex

Cellosaurus `SX` field (`Sex: Female | Male | Mixed sex | Sex unspecified`):

- `Female` → `female`
- `Male` → `male`
- `Mixed sex` → `not applicable` (or `pooled` for a deliberate pool — `characteristics[sex]` has no `mixed` value)
- `Sex unspecified` / absent → `not available`

Lowercase always. Never `M`/`F`. The `cell-lines` template inherits
`characteristics[sex]` from the organism layer.

### 4.6 Ancestry

Cellosaurus `OX` may include population annotations (e.g. `! European`).

- Map to HANCESTRO via OLS. Common: `European` → HANCESTRO:0005,
  `African` → HANCESTRO:0010, `East Asian` → HANCESTRO:0009.
- If absent, set `characteristics[ancestry category]` to `not available`.
  Do not infer ancestry from the disease or organism part.

### 4.7 Age / developmental stage

Cellosaurus `AG` (donor age) and category give:

- Numeric age (e.g. `31Y`) → `characteristics[age]` formatted as
  `<n>Y` / `<n>M` / `<n>W` / `<n>D` (SDRF rule). Reject free text like
  `31 years` — fix it.
- Age range (`30Y-35Y`) → keep the range, hyphen only.
- `Adult`, `Embryo`, `Fetus`, `Newborn` → `characteristics[developmental stage]`
  using the EFO term, not `characteristics[age]`.

### 4.8 Columns Cellosaurus does NOT provide

The cell-lines template also defines `passage number`, `biorepository`,
`cell line authentication`, `culture medium`, and `sample storage temperature`.
Cellosaurus has no values for these — they are study-specific. Either:

- Take them from the paper / PRIDE submission via `/sdrf:annotate`, or
- Set them to `not available` if the paper does not state them.

## Step 5: Bulk enrichment of an SDRF

When the input is a `.sdrf.tsv` file:

1. Read the file. Detect the cell-line column (header
   `characteristics[cell line]`, case-insensitive trim).
2. Build the unique set of cell-line values (skip reserved words).
3. Run Steps 1–4 *once per unique value* — do not re-query for duplicates.
4. For each row, fill empty / `not available` Cellosaurus-derivable columns.
   **Do not overwrite** existing values that disagree with Cellosaurus —
   instead, surface them as conflicts and ask the user, exactly the way
   `/sdrf:review` does.
5. If the SDRF lacks a needed column entirely (e.g.
   `characteristics[cellosaurus accession]`), insert it adjacent to
   `characteristics[cell line]` and re-emit the full TSV.
6. Produce a short report:

```text
Cell line annotation report
  Unique cell lines: 4
    HeLa            → CVCL_0030  (matched: exact)
    MCF-7           → CVCL_0031  (matched: synonym "MCF7")
    HEK 293T        → CVCL_0063  (matched: normalized "hek293t")
    in-house ABC-1  → unmatched  (kept verbatim, others = not available)
  Conflicts: 0
  Filled cells: 18 across 12 rows
```

## Step 6: Validate

After enrichment, validate against the combined templates:

```bash
parse_sdrf validate-sdrf \
  --sdrf_file <enriched>.sdrf.tsv \
  --template cell-lines
```

Then run `/sdrf:validate` for ontology-level checks. Round-trip rules:

- `CVCL_*` accessions must resolve via the Cellosaurus REST API
  (`/cell-line/<CVCL_id>`).
- `NCBITaxon:*`, `MONDO:*`, `UBERON:*`, `HANCESTRO:*`, `EFO:*` must resolve via
  OLS.

## Important rules

- **Never invent accessions.** Every accession written must come from a real
  Cellosaurus or OLS hit in this session. If unsure, write `not available`.
- **Never overwrite curator-supplied values silently.** Conflicts are flagged.
- **Never commit a local cell-line database** to this repo. Cell-line metadata
  is fetched live from Cellosaurus (REST or freshly downloaded bulk file) so it
  tracks upstream updates — the bulk file, if used, is treated as a transient
  cache, not source code.
- **Reserved words**: `not available` for unknown, `not applicable` for
  inapplicable. Never `N/A`, `NA`, `unknown`, blank.
- **Preserve case in `cellosaurus name`** exactly as Cellosaurus returns it
  (it is a proper noun). Free-text `cell line` may be the lab's preferred
  alias.

# Reference: finding sample values (Step 4 of sdrf-annotate)

How to find and verify each `characteristics[...]` value: normalisation, OLS lexical search,
embeddings and ZOOMA, ontology check, cell-line lookup, specificity, reserved words. The values
go into `samples.tsv`.

## Step 4: Fill Sample Metadata

> The values found in this step go into `samples.tsv` (Step 3.2), one row per source and replicate.

Before filling demographic fields, decide whether the paper supports:
- cohort-level demographic context only
- or true sample-level demographic assignment

Use this rule:
- `developmental stage` may come from cohort-level manuscript evidence if the full analyzed cohort is unambiguously adult, pediatric, fetal, juvenile, and so on
- `age`, `sex`, and `ethnicity` require source-sample or individual-level mapping
- if only cohort summaries exist, leave per-sample demographic fields as missing / omitted rather than guessing

For EACH unique value that goes into a characteristics column:

### 4.1 Normalize a short mention first
- If the value already comes from PRIDE metadata or an existing SDRF cell, clean that value and use it directly.
- If the value comes from a manuscript, first extract the shortest standalone entity phrase and keep the sentence only as evidence.
- Search the expanded form before the abbreviation when both are available.
- Do NOT send full manuscript sentences to OLS or ZOOMA unless you are debugging a failed lookup.

### 4.2 Search OLS lexically first

> **Offline mode (Step 0):** skip this step — use `spec/sdrf-proteomics/TERMS.tsv` for permitted values instead of OLS.

```text
Use: searchClasses(query="breast carcinoma", ontologyId="mondo")
Or:  search(query="Homo sapiens")       # only when the target ontology is unknown
```
For clean SDRF-like values, lexical exact or synonym matches are the default path and usually outperform embeddings.

**Smart mode is the default** (do NOT pass `mode` unless you need to override):

1. The tool tries an **exact** label/synonym match, probed wide.
   - Exactly one *distinct* term → returns it. Use its accession directly.
   - Several distinct terms match exactly → the response carries
     `ambiguous: true` and lists them. This is NOT a single answer — pick the
     intended entity yourself (see the trap table below), do not grab the first.
2. If there is no exact hit → the tool falls back to **fuzzy top-3**
   and tags the response with `fallback: "fuzzy"`.
   - Pick the best candidate. If none fit, refine the query (correct typos,
     try a synonym, or switch to a more specific ontology) and search again.

> **For controlled identifiers that a query commonly over-matches — cell lines
> (`HeLa`), drugs (`methotrexate`), anatomy (`hippocampus`) — do not trust a
> single smart-mode hit.** In an audit, smart mode returned confident *wrong*
> single hits: `HeLa` → `HeLa-MAGI-CCR5`, `A549` → `A549-CR` (a resistant
> derivative), `methotrexate` → `High-dose Methotrexate/Rituximab Regimen`,
> `hippocampus` → `CA1 field of hippocampus`, and `in vitro maturation` →
> unrelated terms for a concept with *no* OLS term. For these, pass
> `mode="fuzzy"` and eyeball the candidates against the intended entity.

Override only when necessary:
- `mode="exact"` — force exact-only (e.g. strict validation); empty on miss.
- `mode="fuzzy"` — force fuzzy top-N; use for cell lines/drugs/anatomy and when
  exploring close neighbours.

### 4.3 Use embeddings and ZOOMA only when needed

> **Offline mode (Step 0):** skip this step — there is no embedding or ZOOMA service offline.

Trigger OLS embedding search when:
- lexical search returns no result
- the mention is abbreviation-like (`HCC`, `PDAC`, `GBM`, `TNBC`)
- the top lexical hits are conflicting or clearly over-specific
- the mention came from noisy manuscript text rather than a curated label

Use the OLS MCP tools in this order:
```text
1. listEmbeddingModels()
2. searchClassesWithEmbeddingModel(query="<clean phrase>", ontologyId="<ontology>", model="<embed model>")
3. If ontology-specific search is unavailable, use searchWithEmbeddingModel() and filter manually
```

Use ZOOMA as a slower fallback for manuscript-derived free text or when lexical and embedding results still disagree:
```text
GET https://www.ebi.ac.uk/spot/zooma/v2/api/services/annotate?propertyValue=<clean phrase>&propertyType=<field>
```
- Accept only `HIGH` or `GOOD` confidence mappings from ZOOMA
- Always verify returned `semanticTags` in OLS and confirm the ontology is allowed by `TERMS.tsv`
- Use ZOOMA mainly for disease, phenotype, treatment, or other curator-style phrases backed by prior curation

Field defaults:
- `organism`, `cell line` → lexical first, fallback methods rarely needed
- `organism part`, `cell type`, `treatment` → lexical first, embeddings/ZOOMA only if lexical is weak
- `disease`, `phenotype` → lexical first, embeddings and ZOOMA are useful fallbacks

### 4.4 Verify the term is from the CORRECT ontology
The contract (Step 3.1) names, per column, which ontology(ies) to search (`<- NCBITaxon`,
`<- UBERON, BTO`, ...); do not read TERMS.tsv for it. The usual routing:
- organism → NCBITaxon
- organism part → UBERON (primary), BTO (fallback)
- disease → MONDO (primary), EFO, DOID
- cell type → CL (primary), BTO, CLO
- cell line → CLO, BTO, EFO (+ Cellosaurus for accession)
- instrument → MS, PRIDE
- modifications → UNIMOD
- biosample accession number → exact BioSample accession from ENA/BioSamples only; do not infer from fuzzy search alone

### 4.5 Cell Line Lookup (if using cell-lines template)

For any `characteristics[cell line]` column, prefer the dedicated
``cellline.md`` workflow or the live Cellosaurus service rather than a bundled
full-database script. The skill owns the decision rules; tools are only helpers.

Use this order:

1. ``cellline.md` <name or CVCL_XXXX>` for the full translation workflow
2. `sdrf-tools cellline lookup <name>` for the curated offline helper
3. https://www.cellosaurus.org/search when you need manual confirmation

The goal is to recover:
- `characteristics[cellosaurus accession]` → CVCL_XXXX (e.g., CVCL_0030)
- `characteristics[cellosaurus name]` → official name (e.g., HeLa)
- `characteristics[organism]`
- `characteristics[organism part]`
- `characteristics[disease]`
- `characteristics[cell type]`
- `characteristics[age]`, `characteristics[sex]`, `characteristics[ancestry category]`

Any CLO, BTO, EFO, MONDO, UBERON, CL, or NCBITaxon accession written into the
SDRF must still be verified via OLS before finalizing the row.

For organisms, prefer the current NCBITaxon label over legacy synonyms when validation fails on an older name.
Crosslinking cleanup examples that should be normalized before final validation:
- `chaetomium thermophilum` → `thermochaetoides thermophila`
- `chlorobium tepidum` → `chlorobaculum tepidum`
- `canis familiaris` → `canis lupus familiaris`
- `deinococcus radiodurans r1` → `deinococcus radiodurans`

For crosslinking-specific assay cleanup, use explicit file-name evidence when the SDRF still says `NT=unknown crosslinker;AC=XLMOD:00000`. Safe examples seen in sandbox cleanup:
- file names containing `DSSO` → `NT=DSSO;AC=XLMOD:02126;CL=yes;TA=K,S,T,Y,nterm;MH=54.01;ML=85.98`
- file names containing `DSS` → `NT=DSS;AC=XLMOD:02001`
- file names containing `BS3` → `NT=BS3;AC=XLMOD:02000`
- file names containing `DSBU` → `NT=DSBU;AC=XLMOD:02120` (XLMOD's preferred label is `BuUrBu`)
- file names containing `iQPIR`, `BDP`, or `d8BDP` → `NT=PIR;AC=XLMOD:02237`
  (the BDP-NHP reagent itself is `XLMOD:02011`)

> **Verify every XLMOD accession against OLS before writing it.** Neighbouring
> XLMOD ids are unrelated reagents, so a wrong accession is validator-clean and
> silently corrupts the annotation. Confirm with:
> `curl -s "https://www.ebi.ac.uk/ols4/api/search?q=XLMOD:02126&ontology=xlmod&fieldList=obo_id,label"`

**`TurboID` is not a cross-linker — do not map it to `comment[cross-linker]`.**
It is a promiscuous biotin ligase used for proximity-dependent labelling
(BioID family), not a chemical cross-linking reagent, and XLMOD has no term for
it. Proximity-labelling experiments are not XL-MS: annotate the biotin
enrichment via `characteristics[enrichment process]` /
`comment[crosslink enrichment method]` and do not apply the `crosslinking`
template on the strength of a `TurboID` filename token alone.

After recovering a known cross-linker, backfill `characteristics[crosslink distance]` when the template guidance is explicit:
- `BS3` / `DSS` → `30 Å`
- `DSSO` → `26.4 Å`
- `EDC` → `11.4 Å`
- `formaldehyde` → `2 Å`
- `DSBU` / `DSBSO` → `26.4 Å`
- `SDA` / `sulfo-SDA` → `18 Å`

For `comment[crosslink enrichment method]`, use explicit separation tokens from `comment[data file]` when the field is still missing:
- `SCX` → `strong cation exchange chromatography`
- `SEC` → `size exclusion chromatography`
- `FAIMS` → `FAIMS`
- dataset title containing `streptavidin pull-down` → `streptavidin pull-down`
- dataset title containing `IMAC-enrichable` → `immobilized metal affinity chromatography`
- dataset title containing `CuAAC-enrichable` → `CuAAC enrichment`

When one of those enrichment-method values is recovered and `characteristics[enrichment process]` is still missing, backfill `enrichment of cross-linked peptides`.

### 4.6 Check specificity
- "cancer" → too generic, use "breast carcinoma" or specific subtype
- "tissue" → too generic, use "liver" or "temporal cortex"
- "cell" → too generic, use "T cell" or "epithelial cell"
- Use getChildren() to see if there's a more specific child term
- If embeddings or ZOOMA suggest a child term that is more specific than the paper text supports, prefer the broader lexical term and note the ambiguity

### 4.7 Use reserved words correctly
- `not available` — information exists but was not provided
- `not applicable` — property doesn't apply to this sample
- `normal` — healthy control (for disease column, use with PATO:0000461)
- NEVER use "N/A", "NA", "unknown", "none"
- Check TERMS.tsv `allow_not_available`, `allow_not_applicable`, `allow_pooled` for each column

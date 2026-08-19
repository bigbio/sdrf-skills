---
name: sdrf:terms
description: Use when the user needs to find, verify, or compare ontology terms for SDRF columns. Triggers on questions about ontology terms, accessions, or which term to use.
user-invocable: true
argument-hint: "[column name] [search term]"
---

# SDRF Ontology Term Lookup

You are helping the user find the correct ontology term for an SDRF column.

## Step 1: Identify the Column and Ontology

**Read `spec/sdrf-proteomics/TERMS.tsv`** and find the row for the column the user is asking about.
The `values` field tells you which ontology(ies) to search.

Examples from TERMS.tsv:
- `organism` → values: `NCBITaxon` → search OLS with ontologyId `ncbitaxon`
- `disease` → values: `MONDO, EFO, DOID, PATO` → search these ontologies
- `organism part` → values: `UBERON, BTO` → search UBERON first, BTO as fallback
- `cell type` → values: `CL, BTO` → search CL first, BTO as fallback
- `instrument` → values: `MS` → search MS ontology
- `modification parameters` → values: `UNIMOD` → use UNIMOD accessions
- `cleavage agent details` → values: `MS` → search MS ontology

Always read TERMS.tsv rather than relying on memorized ontology mappings — the spec may add new columns or change ontology sources.

## Step 2: Search OLS

Use the OLS MCP tools to find the term:

```text
Primary search:
  mcp OLS → searchClasses(query="<user term>", ontologyId="<ontology>")

If no results or too many:
  mcp OLS → search(query="<user term>")
  Filter results to the correct ontology manually

For broader semantic search:
  mcp OLS → searchClassesWithEmbeddingModel(query="<description>", model="<model>")
  (Call listEmbeddingModels first to get available models with can_embed=true)
```

## Step 3: Evaluate Specificity

When presenting results, assess specificity:

### Too Generic (suggest more specific)
- "cancer" → suggest "breast carcinoma", "lung adenocarcinoma", etc.
- "tissue" → suggest the actual tissue name
- "cell" → suggest the actual cell type
- "brain" might be OK, but "temporal cortex" is better if known

### Appropriately Specific
- "breast carcinoma" (EFO:0000305) — good for a breast cancer study
- "liver" (UBERON:0002107) — good for tissue-level studies
- "T cell" (CL:0000084) — good if subtype unknown

### Too Specific (might be too narrow)
- "left breast upper inner quadrant" — probably too specific for most studies

To check specificity, use hierarchy navigation:
```text
mcp OLS → getAncestors(ontologyId="<ont>", classIri="<iri>")
mcp OLS → getChildren(ontologyId="<ont>", classIri="<iri>")
```

## Step 4: Cross-Ontology Mapping

When the user has a term from one ontology but needs another:

```text
Example: User has DOID term, needs EFO equivalent
  1. Get the DOID term details: mcp OLS → fetch(id="doid+<iri>")
  2. Search EFO for the same concept: mcp OLS → searchClasses(query="<label>", ontologyId="efo")
  3. Present both options with accessions
```

For disease terms, SDRF accepts MONDO, EFO, or DOID. Recommend (matches TERMS.tsv and sdrf-annotate):
- **MONDO** as first choice (primary; strong cross-references)
- **EFO** as second choice
- **DOID** as third choice

## Step 5: Present Results

For each term found, present:

```text
Term: breast carcinoma
Accession: EFO:0000305
Ontology: Experimental Factor Ontology (EFO)
Definition: A carcinoma that arises in the breast region.
Synonyms: breast cancer, mammary carcinoma
Parent: carcinoma (EFO:0000228)
SDRF format: breast carcinoma
Column: characteristics[disease]

Alternative terms:
  - invasive breast carcinoma (EFO:0010132) — more specific, if applicable
  - breast ductal carcinoma (EFO:0000298) — subtype-specific
```

## Special Cases

### "Normal" / "Healthy" / "Control"
- For disease: use `normal` with accession PATO:0000461
- Do NOT use: "healthy", "control", "none", "N/A"

### "Not Available" vs "Not Applicable"
- `not available` — the information exists but wasn't captured
- `not applicable` — the property doesn't apply (e.g., cell line for a tissue sample)
- Check TERMS.tsv `allow_not_available` and `allow_not_applicable` for the specific column

### Cell Lines
- Use the **Cellosaurus database** (https://www.cellosaurus.org/) for cell line identification
- SDRF uses three columns for cell lines:
  - `characteristics[cell line]` — name from CLO, BTO, or EFO ontology
  - `characteristics[cellosaurus accession]` — format: CVCL_XXXX (e.g., CVCL_0030 for HeLa)
  - `characteristics[cellosaurus name]` — official Cellosaurus name
- Common examples: HeLa (CVCL_0030), HEK293 (CVCL_0045), MCF7 (CVCL_0031), A549 (CVCL_0023)
- To find a Cellosaurus accession: search https://www.cellosaurus.org/search (not OLS)
- Cross-reference Cellosaurus for: species of origin, disease, tissue of origin, STR profile

### Instruments
- Format in SDRF: `AC=MS:1001911;NT=Q Exactive HF`
- Search MS ontology for the instrument model
- Include manufacturer in search if needed

### Modifications
- ALWAYS use UNIMOD accessions, not PSI-MOD
- The format is: `NT=<name>;AC=UNIMOD:<id>;TA=<amino acid>;MT=<Fixed|Variable>`
- Double-check the UNIMOD:1/UNIMOD:21 swap (Acetyl vs Phospho)

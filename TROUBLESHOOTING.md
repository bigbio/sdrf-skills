# Troubleshooting

Common setup and runtime issues with sdrf-skills.

---

## Setup Issues

### "parse_sdrf not found" after installation

**Symptom:** `parse_sdrf --version` returns "command not found" even after `pip install sdrf-pipelines`.

**Cause:** The `parse_sdrf` CLI entry-point is not on your `PATH` — usually because the package was installed
into a user directory (`~/.local/bin`) that isn't in your shell's PATH, or you installed into a different
Python environment than the one that's active.

**Fixes:**
```bash
# Check where it was installed
pip show sdrf-pipelines | grep Location

# Add user site to PATH (add to ~/.bashrc or ~/.zshrc for persistence):
export PATH="$HOME/.local/bin:$PATH"

# Or use the full Python module path:
python -m sdrf_pipelines.sdrf.sdrf validate-sdrf --help

# Or use conda (recommended — avoids PATH issues entirely):
conda env create -f environment.yml
conda activate sdrf-skills
parse_sdrf --version
```

---

### Submodule not initialized — spec files missing

**Symptom:** Skills report missing files like `spec/sdrf-proteomics/TERMS.tsv` or `spec/sdrf-proteomics/sdrf-templates/templates.yaml`.

**Cause:** The repository was cloned without `--recurse-submodules`, so the `spec/` directory is empty.

**Fix:**
```bash
# Initialize and fetch all submodules:
git submodule update --init --recursive

# Verify:
ls spec/sdrf-proteomics/TERMS.tsv
```

To keep the spec current as it evolves:
```bash
git submodule update --remote --recursive
git add spec
git commit -m "Update SDRF spec to latest version"
```

---

### thermorawfileparser not available

**Symptom:** `techsdrf` skips `.raw` files or reports that `thermorawfileparser` is not installed.

**Cause:** `thermorawfileparser` is not on PyPI and cannot be installed with `pip install`.
It is only available via bioconda.

**Fix:**
```bash
# Install via conda (recommended):
conda install -c bioconda thermorawfileparser

# Verify:
thermorawfileparser --version
```

If you are on a platform without conda (e.g., a CI environment), you can download a standalone binary
from the [ThermoRawFileParser releases page](https://github.com/compomics/ThermoRawFileParser/releases)
and put it on your PATH.

---

### conda solver hangs or takes very long

**Symptom:** `conda env create -f environment.yml` runs for 10+ minutes or hangs at "Solving environment".

**Cause:** The classic conda solver can be slow with complex dependency trees.

**Fix:**
```bash
# Use the libmamba solver (much faster):
conda install -n base conda-libmamba-solver
conda config --set solver libmamba

# Then retry:
conda env create -f environment.yml
```

---

## OLS / MCP Server Issues

### OLS MCP returns no results

**Symptom:** A term search via OLS returns empty results for a term that should exist.

**Possible causes and fixes:**

1. **Typo in ontology ID** — OLS ontology IDs are lowercase (e.g., `ncbitaxon`, `efo`, `uberon`).
   Check the ID you're passing against [OLS ontology list](https://www.ebi.ac.uk/ols4/ontologies).

2. **Term not in the specific ontology** — Try a cross-ontology search:
   ```text
   mcp OLS → search(query="<term>")  # searches all ontologies
   ```

3. **OLS is temporarily unavailable** — Check [EBI service status](https://www.ebi.ac.uk/about/news/).
   As a fallback, search [OLS4 web interface](https://www.ebi.ac.uk/ols4/search) manually.

---

### PRIDE MCP returns no data for a PXD accession

**Symptom:** `get_project_details(project_accession="PXD######")` returns nothing or an error.

**Fixes:**

1. Verify the accession exists at `https://www.ebi.ac.uk/pride/archive/projects/PXD######`
2. Confirm the PRIDE MCP server is configured correctly in your AI platform's MCP settings.
3. For private/embargoed datasets, PRIDE may not return metadata until the dataset is public.

---

## Validation Issues

### parse_sdrf reports many unexpected errors after spec update

**Symptom:** After running `git submodule update --remote --recursive`, previously passing files now fail validation.

**Cause:** The SDRF spec may have added new required columns or tightened rules in a new template version.

**Fix:**
1. Check what changed in the spec by looking at the submodule diff:
   ```bash
   git diff HEAD~1 spec/
   git -C spec log --oneline -10
   ```
2. Read `spec/sdrf-proteomics/TERMS.tsv` for the new columns and add them to your SDRF.
3. Update `comment[sdrf template]` version numbers to match the new template versions in `templates.yaml`.
4. If you need to pin to an older spec version:
   ```bash
   git -C spec checkout <commit_sha>
   ```

---

### "technology type" validation error

**Symptom:** `parse_sdrf` reports that `technology type` has an invalid value.

**Allowed values:**
```text
proteomic profiling by mass spectrometry
protein expression profiling by aptamer array
protein expression profiling by antibody array
```

**Common wrong values and fixes:**
| Wrong | Correct |
|-------|---------|
| `mass spectrometry` | `proteomic profiling by mass spectrometry` |
| `MS` | `proteomic profiling by mass spectrometry` |
| `Proteomics` | `proteomic profiling by mass spectrometry` |
| `Olink` | `protein expression profiling by antibody array` |
| `SomaScan` | `protein expression profiling by aptamer array` |

---

## Getting Help

- **SDRF specification questions**: See [SDRF-Proteomics spec](https://github.com/bigbio/proteomics-metadata-standard)
- **sdrf-pipelines bugs**: See [sdrf-pipelines issues](https://github.com/bigbio/sdrf-pipelines/issues)
- **techsdrf bugs**: See the techsdrf repository on GitHub
- **This repo**: Open an issue at [bigbio/sdrf-skills](https://github.com/bigbio/sdrf-skills/issues)

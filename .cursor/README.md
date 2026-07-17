# SDRF Skills — Cursor Setup

This project includes SDRF annotation rules that activate when you work with SDRF files (`*.sdrf.tsv`, paths under `spec/sdrf-proteomics/`, etc.).

## How It Works in Cursor

- **Rules**: `.cursor/rules/sdrf-skills.mdc` loads when you have SDRF-related files open or in context.
- **Skills**: The rule references markdown workflows in `skills/`. The AI reads these when you ask for annotation, validation, setup, etc.
- **No SessionStart hook**: Unlike Claude Code, Cursor does not run hooks on session start. You will not see an automatic "install dependencies" message.
- **Manual review gate**: Cursor cannot run the bundled Claude Stop hook. Ask it to follow `skills/sdrf-annotate-reviewed/SKILL.md`, then enforce the receipt with `python3 <sdrf-skills-root>/tools/review_gate.py gate --cwd <repo-root>` (exit 1 means review is still pending).

## First-Time Setup

1. **Clone with submodules** (if not already):
   ```bash
   git submodule update --init --recursive
   ```

2. **Install dependencies**:
   ```bash
   conda env create -f environment.yml && conda activate sdrf-skills
   # Or: pip install -r requirements.txt
   ```

3. **Trigger setup help**: Open any `.sdrf.tsv` file or a file under `spec/sdrf-proteomics/`, then ask:
   - *"Install SDRF dependencies"*
   - *"Follow the sdrf setup workflow"*
   - *"Set up my environment for SDRF"*

## What to Ask

| Task | Example prompt |
|------|----------------|
| Setup | "Install SDRF dependencies" |
| Annotate | "Annotate PXD012345" or "Create SDRF for this dataset" |
| Validate | "Validate this SDRF file" |
| Fix errors | "Fix common errors in this SDRF" |
| Find terms | "Find ontology term for disease: breast cancer" |

## MCP Servers

For full functionality (PRIDE, OLS, ontology lookup), configure the PRIDE MCP server and optionally PubMed in your Cursor MCP settings.

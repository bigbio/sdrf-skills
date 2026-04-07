# SDRF Skills — Cursor Setup

This project includes SDRF annotation rules that activate when you work with SDRF files (`*.sdrf.tsv`, paths under `spec/sdrf-proteomics/`, etc.).

## How It Works in Cursor

- **Rules**: `.cursor/rules/sdrf-skills.mdc` loads when you have SDRF-related files open or in context.
- **Skills**: The rule references markdown workflows in `skills/`. The AI reads these when you ask for annotation, validation, setup, etc.
- **No SessionStart hook**: Unlike Claude Code, Cursor does not run hooks on session start. You will not see an automatic "install dependencies" message.

## Quick Start (recommended)

1. Open this repository in Cursor.
2. Open any `*.sdrf.tsv` file (or anything under `spec/sdrf-proteomics/`) so the rule activates.
3. In chat, attach the SDRF file (or paste the relevant portion) and ask in plain English.

## First-Time Setup

If you cloned without submodules, initialize them:

   ```bash
   git submodule update --init --recursive
   ```

Install dependencies:

   ```bash
   conda env create -f environment.yml && conda activate sdrf-skills
   # Or: pip install -r requirements.txt
   ```

If you want the assistant to guide you, open a relevant file and ask:
   - *"Install SDRF dependencies"*
   - *"Follow the sdrf setup workflow"*
   - *"Set up my environment for SDRF"*

## Using this in *another* Cursor project

Cursor does not install Claude Code plugins. To use these workflows in your own project, copy:

- `.cursor/rules/sdrf-skills.mdc`
- `skills/`
- `spec/` (and run `git submodule update --init --recursive` if `spec/` is a submodule)

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

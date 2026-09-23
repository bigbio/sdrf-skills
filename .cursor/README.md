# SDRF Skills — Cursor Setup

This project includes SDRF annotation rules that activate when you work with SDRF files (`*.sdrf.tsv`, paths under `spec/sdrf-proteomics/`, etc.).

## How It Works in Cursor

- **Rules**: `.cursor/rules/sdrf-skills.mdc` loads when you have SDRF-related files open or in context.
- **Skills**: The rule references markdown workflows in `skills/`. The AI reads these when you ask for annotation, review, or a question about the format.
- **No SessionStart hook**: Unlike Claude Code, Cursor does not run hooks on session start. You will not see an automatic "install dependencies" message.
- **Manual review gate**: Cursor cannot run the bundled Claude Stop hook. Ask it to follow `skills/sdrf-annotate/SKILL.md` (Step 9.5, the independent review), then enforce the receipt with `python3 <sdrf-skills-root>/tools/review_gate.py gate --cwd <repo-root>` (exit 1 means review is still pending).

## First-Time Setup

1. **Clone with submodules** (if not already):
   ```bash
   git submodule update --init --recursive
   ```

2. **Install dependencies**:
   ```bash
   conda env create -f environment.yml && conda activate sdrf-skills
   # Or: pip install -r requirements.txt
   pip install -e .        # the sdrf-tools console script
   sdrf-tools doctor       # reports anything still missing
   ```

3. **Check the setup**: run `sdrf-tools doctor`; if something is missing, `skills/sdrf-annotate/references/setup.md` has the install steps per platform.

## What to Ask

| Task | Example prompt |
|------|----------------|
| Setup | run `sdrf-tools doctor` |
| Annotate | "Annotate PXD012345" or "Create SDRF for this dataset" |
| Review / validate | "Review this SDRF file" (validates, checks, reconciles, scores, then the independent review) |
| Fix errors | `sdrf-tools fix file.sdrf.tsv -o out.tsv`, or ask the review what it can repair |
| Find terms | "Find ontology term for disease: breast cancer" |

## MCP Servers

For full functionality (PRIDE, OLS, ontology lookup), configure the PRIDE MCP server and optionally PubMed in your Cursor MCP settings.

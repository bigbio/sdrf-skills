#!/usr/bin/env python3
"""
run_opencode_annotation.py — Run OpenCode with DeepInfra models for SDRF annotation.

This script invokes OpenCode with specialized SDRF annotation prompts and workflows
from the sdrf-skills repository, using the specified conda environment and DeepInfra
model, while accurately tracking token usage, costs, and execution statistics.

Usage:
    python scripts/run_opencode_annotation.py --study PXD045678 --model deepinfra/deepseek-ai/DeepSeek-V4.1-Flash
    python scripts/run_opencode_annotation.py --study PXD019515 -m qwen3-coder --score
    python scripts/run_opencode_annotation.py --list-models
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Default DeepInfra models and convenient short aliases
MODEL_ALIASES = {
    "deepseek-v4-flash": "deepinfra/deepseek-ai/DeepSeek-V4.1-Flash",
    "deepseek-v4.1-flash": "deepinfra/deepseek-ai/DeepSeek-V4.1-Flash",
    "deepseek-r1": "deepinfra/deepseek-ai/DeepSeek-R1",
    "deepseek-v3": "deepinfra/deepseek-ai/DeepSeek-V3",
    "qwen2.5-coder": "deepinfra/Qwen/Qwen2.5-Coder-32B-Instruct",
    "qwen3-coder": "deepinfra/Qwen/Qwen3-Coder-480B-A35B-Instruct-Turbo",
    "qwen3.5-35b": "deepinfra/Qwen/Qwen3.5-35B-A3B",
    "llama-3.3-70b": "deepinfra/meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "llama-4-scout": "deepinfra/meta-llama/Llama-4-Scout-17B-16E-Instruct",
    "gemma-3-27b": "deepinfra/google/gemma-3-27b-it",
    "glm-5.3": "deepinfra/zai-org/GLM-5.3",
    "glm-5.3-flash": "deepinfra/zai-org/GLM-5.3-Flash",
}

# DeepInfra published pricing ($ per 1 Million tokens)
DEEPINFRA_PRICING = {
    "deepinfra/deepseek-ai/DeepSeek-V4.1-Flash": {"input": 0.14, "cache_read": 0.028, "output": 0.28},
    "deepinfra/deepseek-ai/DeepSeek-V3": {"input": 0.14, "cache_read": 0.028, "output": 0.28},
    "deepinfra/deepseek-ai/DeepSeek-V3.2": {"input": 0.26, "cache_read": 0.052, "output": 0.38},
    "deepinfra/deepseek-ai/DeepSeek-R1": {"input": 0.55, "cache_read": 0.14, "output": 2.19},
    "deepinfra/Qwen/Qwen2.5-Coder-32B-Instruct": {"input": 0.06, "cache_read": 0.02, "output": 0.18},
    "deepinfra/Qwen/Qwen3-Coder-480B-A35B-Instruct-Turbo": {"input": 0.30, "cache_read": 0.06, "output": 1.20},
    "deepinfra/meta-llama/Llama-3.3-70B-Instruct-Turbo": {"input": 0.10, "cache_read": 0.10, "output": 0.32},
    "deepinfra/zai-org/GLM-5.3": {"input": 0.95, "cache_read": 0.19, "output": 3.00},
    "deepinfra/zai-org/GLM-5.3-Flash": {"input": 0.20, "cache_read": 0.04, "output": 0.80},
    "deepinfra/google/gemma-3-27b-it": {"input": 0.10, "cache_read": 0.03, "output": 0.30},
}

DEFAULT_MODEL = "deepinfra/deepseek-ai/DeepSeek-V4.1-Flash"
DEFAULT_CONDA_ENV = "sdrf-skills"


def calculate_deepinfra_cost(
    model_id: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    reasoning_tokens: int = 0,
) -> Optional[float]:
    """Calculate exact DeepInfra cost using published per-1M token rates."""
    if not model_id or not model_id.strip():
        return None

    norm_model = model_id.strip()
    rates = DEEPINFRA_PRICING.get(norm_model)
    if not rates:
        # Exact match (case-insensitive)
        for k, v in DEEPINFRA_PRICING.items():
            if k.lower() == norm_model.lower():
                rates = v
                break
    if not rates:
        # Match with deepinfra/ prefix added if missing
        cand = f"deepinfra/{norm_model}" if not norm_model.lower().startswith("deepinfra/") else norm_model
        for k, v in DEEPINFRA_PRICING.items():
            if k.lower() == cand.lower():
                rates = v
                break
    if not rates:
        # Match by model name suffix requiring path separator boundary
        for k, v in DEEPINFRA_PRICING.items():
            if k.lower().endswith("/" + norm_model.lower()):
                rates = v
                break
    if not rates:
        return None

    cost = (
        (input_tokens / 1_000_000.0) * rates.get("input", 0.0)
        + (cache_read_tokens / 1_000_000.0) * rates.get("cache_read", rates.get("input", 0.0) * 0.2)
        + ((output_tokens + reasoning_tokens) / 1_000_000.0) * rates.get("output", 0.0)
    )
    return round(cost, 6)



def resolve_model_name(model_arg: str) -> str:
    """Resolve model alias or prefix with deepinfra/ if needed."""
    if not model_arg:
        return DEFAULT_MODEL
    key = model_arg.strip().lower()
    if key in MODEL_ALIASES:
        return MODEL_ALIASES[key]
    if model_arg.startswith("deepinfra/"):
        return model_arg
    return f"deepinfra/{model_arg}"


def list_deepinfra_models(opencode_bin: str = "opencode") -> List[str]:
    """Fetch all DeepInfra models registered with OpenCode."""
    try:
        proc = subprocess.run(
            [opencode_bin, "models"],
            capture_output=True,
            text=True,
            check=True,
        )
        models = [line.strip() for line in proc.stdout.splitlines() if "deepinfra/" in line]
        return sorted(models)
    except Exception as e:
        print(f"Warning: Could not fetch models via '{opencode_bin} models': {e}", file=sys.stderr)
        return sorted(list(set(MODEL_ALIASES.values())))


def find_conda_env_path(env_name: str) -> Optional[Path]:
    """Find the absolute path of a conda environment."""
    # Check if env_name is already a path
    p = Path(env_name).expanduser()
    if p.is_dir() and (p / "bin" / "python").exists():
        return p.resolve()

    # Try conda info --json
    try:
        proc = subprocess.run(
            ["conda", "info", "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(proc.stdout)
        envs = data.get("envs", [])
        for env_path_str in envs:
            ep = Path(env_path_str)
            if ep.name == env_name:
                return ep.resolve()
    except Exception:
        pass

    # Common default locations
    home = Path.home()
    for base in [home / "miniforge3", home / "miniconda3", home / "anaconda3", Path("/opt/conda")]:
        candidate = base / "envs" / env_name
        if candidate.is_dir():
            return candidate.resolve()

    return None


def get_environment_with_conda(conda_env_name: Optional[str] = DEFAULT_CONDA_ENV) -> Dict[str, str]:
    """Prepare environment dictionary with the conda environment and Homebrew on PATH."""
    env = os.environ.copy()
    current_path = env.get("PATH", "")
    path_parts = current_path.split(":") if current_path else []

    # Ensure Homebrew binary paths are always present (opencode is often in /opt/homebrew/bin or /usr/local/bin)
    for brew_bin in ["/opt/homebrew/bin", "/opt/homebrew/sbin", "/usr/local/bin"]:
        if os.path.isdir(brew_bin) and brew_bin not in path_parts:
            path_parts.append(brew_bin)

    if conda_env_name:
        # Check if already running inside the desired active conda environment
        active_conda_prefix = env.get("CONDA_PREFIX")
        if active_conda_prefix and Path(active_conda_prefix).name == conda_env_name:
            bin_dir = str(Path(active_conda_prefix) / "bin")
            if bin_dir not in path_parts:
                path_parts.insert(0, bin_dir)
        else:
            env_path = find_conda_env_path(conda_env_name)
            if env_path:
                bin_dir = str(env_path / "bin")
                if bin_dir in path_parts:
                    path_parts.remove(bin_dir)
                path_parts.insert(0, bin_dir)
                env["CONDA_PREFIX"] = str(env_path)
                env["CONDA_DEFAULT_ENV"] = env_path.name
            else:
                print(f"Warning: Conda environment '{conda_env_name}' not found. Using current PATH.", file=sys.stderr)

    env["PATH"] = ":".join(path_parts)
    return env


def resolve_opencode_binary(custom_bin: str = "opencode", env: Optional[Dict[str, str]] = None) -> str:
    """Resolve the path to the opencode binary, checking system PATH and Homebrew."""
    search_path = env.get("PATH") if env else os.environ.get("PATH")
    found = shutil.which(custom_bin, path=search_path)
    if found:
        return found

    # Check common Homebrew locations explicitly
    for brew_loc in ["/opt/homebrew/bin/opencode", "/usr/local/bin/opencode"]:
        if os.path.isfile(brew_loc) and os.access(brew_loc, os.X_OK):
            return brew_loc

    return custom_bin



def build_annotation_prompt(
    study_id: str,
    extra_instructions: Optional[str] = None,
    output_file: Optional[str] = None,
    model_slug: Optional[str] = None,
) -> str:
    """Build a structured, expert-level prompt for SDRF annotation."""
    scratch_dir = f"scratchpad/{study_id}_{model_slug}/" if model_slug else f"scratchpad/{study_id}/"
    out_target = output_file if output_file else (f"annotations/{study_id}_{model_slug}.sdrf.tsv" if model_slug else f"annotations/{study_id}.sdrf.tsv")
    
    prompt = f"""You are an expert proteomics metadata annotator using the workflows in this repository.

Task: Annotate study {study_id} into a fully valid, standards-compliant SDRF file.
(Note: Re-annotation is authorized; proceed autonomously through the full workflow to produce and validate the SDRF without pausing for interactive confirmation at Step 0.5).

Follow the step-by-step SDRF annotation workflow in `skills/sdrf-annotate/SKILL.md` and `.opencode/AGENTS.md`:
1. **Working Isolation**: Create and use `{scratch_dir}` for all temporary files and downloads.
2. **Context Gathering**: Fetch PRIDE project metadata and publication context for accession `{study_id}`.
3. **Template Selection**: Select the appropriate SDRF templates from `spec/sdrf-proteomics/sdrf-templates/templates.yaml` (e.g., `ms-proteomics`, organism template such as `human` or `vertebrates`, acquisition mode like `dia-acquisition` or label free, etc.).
4. **Contract Verification**: Run `sdrf-tools contract -t <template1> [-t <template2> ...]` to inspect the required columns and ontologies.
5. **Table Authoring**: Create `samples.tsv` and `technical.tsv` in `{scratch_dir}` based strictly on verified evidence (using OLS for ontology accessions, never guessing).
6. **Build SDRF**: Run `sdrf-tools build --samples {scratch_dir}samples.tsv --technical {scratch_dir}technical.tsv --files {scratch_dir}files.json -t <templates> -o {out_target}`.
7. **Reconciliation & Validation**:
   - Run `sdrf-tools reconcile {out_target} --accession {study_id}`.
   - Run `parse_sdrf validate-sdrf -s {out_target} -t <templates>`.
   - If validation errors occur, adjust `samples.tsv` / `technical.tsv` and rebuild (max 2 iterations).
8. **Final Report**: Present the templates used, number of samples/runs, factor values, and validation result.

Never hand-edit the final SDRF structure; always generate it through `sdrf-tools build`.
"""
    if extra_instructions:
        prompt += f"\nAdditional Instructions:\n{extra_instructions.strip()}\n"

    return prompt


def parse_opencode_event_stream(process: subprocess.Popen, quiet: bool = False) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """Parse real-time JSON stream from OpenCode run, returning sessionID and event log."""
    session_id = None
    events = []

    for raw_line in iter(process.stdout.readline, ""):
        line = raw_line.strip()
        if not line:
            continue

        try:
            event = json.loads(line)
            events.append(event)
            
            # Extract sessionID
            if not session_id:
                session_id = event.get("sessionID")

            if not quiet:
                ev_type = event.get("type")
                if ev_type == "text":
                    part = event.get("part", {})
                    text_chunk = part.get("text", "")
                    if text_chunk:
                        sys.stdout.write(text_chunk)
                        sys.stdout.flush()
                elif ev_type == "tool_use":
                    part = event.get("part", {})
                    tool = part.get("tool", "")
                    tool_input = part.get("state", {}).get("input", "")
                    print(f"\n[Tool] {tool}: {json.dumps(tool_input) if isinstance(tool_input, (dict, list)) else tool_input}", flush=True)
                elif ev_type in ("tool_call", "tool_result"):
                    part = event.get("part", {})
                    tool = part.get("tool", "")
                    tool_input = part.get("input", "")
                    print(f"\n[{ev_type}] {tool}: {json.dumps(tool_input) if isinstance(tool_input, (dict, list)) else tool_input}", flush=True)
                elif ev_type == "error":
                    err_msg = event.get("error", {}).get("message", str(event))
                    print(f"\n[Error] {err_msg}", file=sys.stderr, flush=True)

        except json.JSONDecodeError:
            if not quiet:
                # Raw text fallback
                sys.stdout.write(raw_line)
                sys.stdout.flush()

    return session_id, events


def get_session_export(session_id: str, opencode_bin: str = "opencode", env: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
    """Export complete session information via `opencode session export <session_id>`."""
    try:
        proc = subprocess.run(
            [opencode_bin, "session", "export", session_id],
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
        return json.loads(proc.stdout)
    except Exception as e:
        print(f"Warning: Failed to export session '{session_id}': {e}", file=sys.stderr)
        return None


def extract_usage_and_costs(session_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract structured token counts, costs, tool stats, and execution metadata."""
    info = session_data.get("info", {})
    tokens = info.get("tokens", {})
    cache_tokens = tokens.get("cache", {})
    
    input_tokens = tokens.get("input", 0)
    output_tokens = tokens.get("output", 0)
    reasoning_tokens = tokens.get("reasoning", 0)
    cache_read_tokens = cache_tokens.get("read", 0)
    cache_write_tokens = cache_tokens.get("write", 0)
    total_tokens = input_tokens + output_tokens + reasoning_tokens + cache_read_tokens + cache_write_tokens

    cost_usd = info.get("cost", 0.0)
    outcome = info.get("outcome", "unknown")
    model_info = info.get("model", {})
    
    time_info = info.get("time", {})
    t_created = time_info.get("created")
    t_updated = time_info.get("updated")
    duration_s = None
    if t_created and t_updated:
        duration_s = round((t_updated - t_created) / 1000.0, 2)

    # Tool invocation statistics
    tool_counts: Dict[str, int] = {}
    total_tool_calls = 0
    messages = session_data.get("messages", [])
    for msg in messages:
        # Check both content and parts
        items = msg.get("content", []) or msg.get("parts", [])
        for item in items:
            if isinstance(item, dict) and item.get("type") == "tool":
                t_name = item.get("name") or item.get("tool") or "unknown"
                tool_counts[t_name] = tool_counts.get(t_name, 0) + 1
                total_tool_calls += 1

    model_full_id = f"{model_info.get('providerID')}/{model_info.get('id')}" if model_info.get('providerID') else model_info.get('id', '')
    deepinfra_cost = calculate_deepinfra_cost(
        model_id=model_full_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=cache_read_tokens,
        reasoning_tokens=reasoning_tokens,
    )

    return {
        "session_id": info.get("id"),
        "model": model_info.get("id", "unknown"),
        "provider": model_info.get("providerID", "unknown"),
        "outcome": outcome,
        "duration_seconds": duration_s,
        "cost_usd": cost_usd,
        "deepinfra_cost_usd": deepinfra_cost,
        "tokens": {
            "input": input_tokens,
            "output": output_tokens,
            "reasoning": reasoning_tokens,
            "cache_read": cache_read_tokens,
            "cache_write": cache_write_tokens,
            "total": total_tokens,
        },
        "tool_calls": {
            "total": total_tool_calls,
            "by_tool": tool_counts,
        },
        "steps_count": len(messages),
    }


def print_usage_summary(summary: Dict[str, Any]) -> None:
    """Print formatted terminal report of token usage and costs."""
    tokens = summary.get("tokens", {})
    tool_calls = summary.get("tool_calls", {})
    
    print("\n" + "=" * 65)
    print(f"  OPENCODE EXECUTION & USAGE REPORT")
    print("=" * 65)
    print(f"  Session ID    : {summary.get('session_id')}")
    print(f"  Model         : {summary.get('model')} ({summary.get('provider')})")
    print(f"  Outcome       : {summary.get('outcome')}")
    if summary.get('duration_seconds') is not None:
        print(f"  Duration      : {summary.get('duration_seconds')} seconds")
    print("-" * 65)
    print(f"  Input Tokens  : {tokens.get('input', 0):,}")
    print(f"  Output Tokens : {tokens.get('output', 0):,}")
    if tokens.get('reasoning', 0) > 0:
        print(f"  Reasoning     : {tokens.get('reasoning', 0):,}")
    if tokens.get('cache_read', 0) > 0:
        print(f"  Cache Read    : {tokens.get('cache_read', 0):,}")
    if tokens.get('cache_write', 0) > 0:
        print(f"  Cache Write   : {tokens.get('cache_write', 0):,}")
    print(f"  Total Tokens  : {tokens.get('total', 0):,}")
    print("-" * 65)
    print(f"  OpenCode Est. : ${summary.get('cost_usd', 0.0):.6f} USD")
    if summary.get('deepinfra_cost_usd') is not None:
        print(f"  DeepInfra Rate: ${summary.get('deepinfra_cost_usd', 0.0):.6f} USD (per official pricing)")
    print("-" * 65)
    print(f"  Tool Calls    : {tool_calls.get('total', 0)}")
    for t_name, count in tool_calls.get("by_tool", {}).items():
        print(f"    - {t_name:<18}: {count} calls")

    print("=" * 65 + "\n")


def evaluate_sdrf_quality(sdrf_path: str, env: Dict[str, str]) -> Dict[str, Any]:
    """Optionally run sdrf-tools score and check on the generated SDRF file."""
    results: Dict[str, Any] = {"file": sdrf_path, "exists": os.path.exists(sdrf_path)}
    if not os.path.exists(sdrf_path):
        return results

    try:
        proc = subprocess.run(
            ["sdrf-tools", "score", sdrf_path],
            capture_output=True,
            text=True,
            env=env,
        )
        results["score_returncode"] = proc.returncode
        results["score_output"] = proc.stdout.strip()
        results["score_stderr"] = proc.stderr.strip()
    except Exception as e:
        results["score_returncode"] = -1
        results["score_error"] = str(e)

    try:
        proc = subprocess.run(
            ["sdrf-tools", "check", sdrf_path, "--offline"],
            capture_output=True,
            text=True,
            env=env,
        )
        results["check_returncode"] = proc.returncode
        results["check_output"] = proc.stdout.strip()
        results["check_stderr"] = proc.stderr.strip()
    except Exception as e:
        results["check_returncode"] = -1
        results["check_error"] = str(e)

    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run OpenCode with DeepInfra models for SDRF annotation and retrieve token usage/costs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Annotate a PXD accession with default DeepSeek-V4.1-Flash:
  python scripts/run_opencode_annotation.py --study PXD045678

  # Run with Qwen 2.5 Coder 32B:
  python scripts/run_opencode_annotation.py --study PXD019515 --model qwen2.5-coder

  # Run with LLaMA 3.3 70B and score the resulting SDRF:
  python scripts/run_opencode_annotation.py --study PXD019515 -m llama-3.3-70b --score

  # List all available DeepInfra models:
  python scripts/run_opencode_annotation.py --list-models
        """,
    )

    parser.add_argument(
        "--study", "-s",
        type=str,
        help="Study / dataset accession (e.g., PXD045678, PXD019515).",
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Model identifier or alias (default: {DEFAULT_MODEL}). Aliases: {', '.join(MODEL_ALIASES.keys())}",
    )
    parser.add_argument(
        "--prompt", "-p",
        type=str,
        help="Custom prompt string. If omitted, an adequate SDRF annotation prompt is generated.",
    )
    parser.add_argument(
        "--prompt-file",
        type=Path,
        help="Path to a file containing a custom prompt template.",
    )
    parser.add_argument(
        "--extra-instructions",
        type=str,
        help="Additional instructions to append to the default prompt.",
    )
    parser.add_argument(
        "--conda-env", "-e",
        type=str,
        default=DEFAULT_CONDA_ENV,
        help=f"Name or path of the conda environment (default: '{DEFAULT_CONDA_ENV}').",
    )
    parser.add_argument(
        "--output-sdrf",
        type=str,
        help="Path where the final SDRF file should be written (default: annotations/<study>.sdrf.tsv).",
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=Path,
        help="Directory to save run logs, exported session JSON, and usage scorecard.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Path to save the extracted usage metrics JSON.",
    )
    parser.add_argument(
        "--thinking",
        action="store_true",
        help="Enable model thinking / reasoning output in OpenCode.",
    )
    parser.add_argument(
        "--score",
        action="store_true",
        help="Automatically run `sdrf-tools score` and `sdrf-tools check` on the generated SDRF.",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Do not stream agent output in real-time.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Display the command, environment, and prompt without executing.",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List available DeepInfra models recognized by OpenCode and exit.",
    )
    parser.add_argument(
        "--opencode-bin",
        type=str,
        default="opencode",
        help="Path to opencode executable (default: 'opencode').",
    )

    args = parser.parse_args()

    # Handle --list-models
    if args.list_models:
        print("Available DeepInfra models for OpenCode:")
        models = list_deepinfra_models(args.opencode_bin)
        for m in models:
            print(f"  - {m}")
        print("\nCommon aliases:")
        for alias, full in MODEL_ALIASES.items():
            print(f"  - {alias:<20} -> {full}")
        return 0

    if not args.study and not args.prompt and not args.prompt_file:
        parser.error("Either --study (e.g. PXD045678) or --prompt/--prompt-file is required.")

    # Resolve model
    resolved_model = resolve_model_name(args.model)
    study_name = args.study if args.study else "custom_run"
    model_slug = re.sub(r"[^A-Za-z0-9_.-]", "_", resolved_model.replace("deepinfra/", ""))

    # Resolve Prompt
    if args.prompt_file:
        with open(args.prompt_file, "r") as f:
            final_prompt = f.read()
        if args.extra_instructions:
            final_prompt += f"\n\n{args.extra_instructions.strip()}\n"
    elif args.prompt:
        final_prompt = args.prompt
        if args.extra_instructions:
            final_prompt += f"\n\n{args.extra_instructions.strip()}\n"
    else:
        final_prompt = build_annotation_prompt(
            study_id=args.study,
            extra_instructions=args.extra_instructions,
            output_file=args.output_sdrf,
            model_slug=model_slug,
        )

    # Configure Environment
    env = get_environment_with_conda(args.conda_env)

    # Prepare Output Directories
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if args.output_dir:
        run_dir = args.output_dir
    else:
        run_dir = Path("results") / "opencode_runs" / f"{study_name}_{model_slug}_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    # Resolve OpenCode binary (including brew path)
    opencode_path = resolve_opencode_binary(args.opencode_bin, env=env)

    # Build OpenCode Command
    cmd = [
        opencode_path,
        "run",
        "--format", "json",
        "--model", resolved_model,
        "--auto",
    ]
    if args.thinking:
        cmd.append("--thinking")
    cmd.append(final_prompt)

    # Dry-run handling
    if args.dry_run:
        print("\n=== DRY RUN MODE ===")
        print(f"Command        : {' '.join(cmd[:-1])} '<prompt>'")
        print(f"Model          : {resolved_model}")
        print(f"Conda Env      : {args.conda_env} (Prefix: {env.get('CONDA_PREFIX', 'N/A')})")
        print(f"Output Dir     : {run_dir.resolve()}")
        print("\n=== GENERATED PROMPT ===")
        print(final_prompt)
        print("========================\n")
        return 0

    print(f"\n[OpenCode] Starting SDRF annotation for {study_name}")
    print(f"[OpenCode] Model       : {resolved_model}")
    print(f"[OpenCode] Conda Env   : {args.conda_env}")
    print(f"[OpenCode] Output Dir  : {run_dir}")
    print("-" * 65)

    start_time = time.time()
    session_id = None
    events = []
    opencode_exit_code = 0
    stderr_content = ""

    stderr_path = run_dir / "opencode_stderr.log"
    try:
        with open(stderr_path, "w+") as stderr_fh:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=stderr_fh,
                text=True,
                bufsize=1,
                env=env,
            )

            session_id, events = parse_opencode_event_stream(proc, quiet=args.quiet)
            proc.wait()
            elapsed_time = time.time() - start_time
            opencode_exit_code = proc.returncode

            stderr_fh.seek(0)
            stderr_content = stderr_fh.read()

        if proc.stdout:
            proc.stdout.close()

        if opencode_exit_code != 0:
            print(f"\n[Warning] OpenCode process exited with code {opencode_exit_code}. Stderr: {stderr_content}", file=sys.stderr)

    except KeyboardInterrupt:
        print("\n[OpenCode] Interrupted by user.", file=sys.stderr)
        if 'proc' in locals() and proc.poll() is None:
            proc.terminate()
        return 130
    except Exception as e:
        print(f"\n[OpenCode] Error during execution: {e}", file=sys.stderr)
        return 1

    # Save raw event stream
    events_file = run_dir / "opencode_events.jsonl"
    with open(events_file, "w") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")

    # Retrieve usage and costs
    summary_data: Dict[str, Any] = {}
    if session_id:
        print(f"\n[OpenCode] Retrieving session metrics for session: {session_id}")
        session_export = get_session_export(session_id, opencode_bin=opencode_path, env=env)
        if session_export:
            # Save full exported session
            export_file = run_dir / "session_export.json"
            with open(export_file, "w") as f:
                json.dump(session_export, f, indent=2)

            summary_data = extract_usage_and_costs(session_export)
        else:
            summary_data = {
                "session_id": session_id,
                "model": resolved_model,
                "error": "Failed to export session data",
                "duration_seconds": round(elapsed_time, 2),
            }
    else:
        print("[Warning] No sessionID was detected in the OpenCode stream.", file=sys.stderr)
        summary_data = {
            "session_id": None,
            "model": resolved_model,
            "duration_seconds": round(elapsed_time, 2),
        }

    summary_data["exit_code"] = opencode_exit_code
    if opencode_exit_code != 0 and stderr_content:
        summary_data["stderr"] = stderr_content

    # Print summary
    print_usage_summary(summary_data)

    # Optional SDRF quality evaluation
    if args.output_sdrf:
        expected_sdrf = args.output_sdrf
    else:
        candidate_model_sdrf = f"annotations/{study_name}_{model_slug}.sdrf.tsv"
        candidate_generic_sdrf = f"annotations/{study_name}.sdrf.tsv"
        expected_sdrf = candidate_model_sdrf if os.path.exists(candidate_model_sdrf) else candidate_generic_sdrf
    if args.score:
        print(f"[Score] Evaluating generated SDRF: {expected_sdrf}")
        eval_results = evaluate_sdrf_quality(expected_sdrf, env=env)
        summary_data["sdrf_evaluation"] = eval_results
        if eval_results.get("score_output"):
            print(f"\n--- SDRF Quality Score ---\n{eval_results['score_output']}\n")
        if eval_results.get("score_stderr"):
            print(f"\n--- SDRF Score Stderr ---\n{eval_results['score_stderr']}\n", file=sys.stderr)
        if eval_results.get("check_output"):
            print(f"\n--- SDRF Checks ---\n{eval_results['check_output']}\n")
        if eval_results.get("check_stderr"):
            print(f"\n--- SDRF Check Stderr ---\n{eval_results['check_stderr']}\n", file=sys.stderr)

    # Write summary JSON
    summary_json_path = args.output_json if args.output_json else (run_dir / "usage_summary.json")
    with open(summary_json_path, "w") as f:
        json.dump(summary_data, f, indent=2)

    print(f"[OpenCode] Complete report saved to: {summary_json_path.resolve()}")
    if opencode_exit_code != 0:
        return opencode_exit_code
    return 0


if __name__ == "__main__":
    sys.exit(main())

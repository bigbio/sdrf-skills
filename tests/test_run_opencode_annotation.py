"""Tests for scripts.run_opencode_annotation."""

from __future__ import annotations

import io
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from scripts.run_opencode_annotation import (
    calculate_deepinfra_cost,
    evaluate_sdrf_quality,
    parse_opencode_event_stream,
    resolve_model_name,
)


def test_calculate_deepinfra_cost_empty():
    assert calculate_deepinfra_cost("", 1000, 1000) is None
    assert calculate_deepinfra_cost("   ", 1000, 1000) is None


def test_calculate_deepinfra_cost_exact_and_boundary():
    # Exact full model ID
    cost = calculate_deepinfra_cost("deepinfra/deepseek-ai/DeepSeek-V3", 1_000_000, 1_000_000)
    assert cost == 0.42

    # Model without deepinfra/ prefix
    cost = calculate_deepinfra_cost("deepseek-ai/DeepSeek-V3", 1_000_000, 1_000_000)
    assert cost == 0.42

    # Model name suffix with boundary
    cost = calculate_deepinfra_cost("DeepSeek-V3", 1_000_000, 1_000_000)
    assert cost == 0.42

    # Similar model name without matching boundary should NOT match
    assert calculate_deepinfra_cost("DeepSeek-V3.1", 1_000_000, 1_000_000) is None


def test_resolve_model_name():
    # Empty
    assert resolve_model_name("").startswith("deepinfra/")

    # Alias
    resolved = resolve_model_name("qwen3-coder")
    assert resolved == "deepinfra/Qwen/Qwen3-Coder-480B-A35B-Instruct-Turbo"

    # Already has deepinfra/ prefix
    assert resolve_model_name("deepinfra/deepseek-ai/DeepSeek-R1") == "deepinfra/deepseek-ai/DeepSeek-R1"

    # Has slash but no deepinfra prefix
    assert resolve_model_name("deepseek-ai/DeepSeek-R1") == "deepinfra/deepseek-ai/DeepSeek-R1"
    assert resolve_model_name("Qwen/Qwen3-Coder-480B-A35B-Instruct-Turbo") == "deepinfra/Qwen/Qwen3-Coder-480B-A35B-Instruct-Turbo"


def test_parse_opencode_event_stream():
    events = [
        {"type": "step_start", "sessionID": "ses_test_abc"},
        {"type": "tool_use", "part": {"tool": "bash", "state": {"input": {"command": "ls"}}}},
        {"type": "text", "part": {"text": "Running command..."}},
        {"type": "step_finish"},
    ]
    lines = "".join(json.dumps(ev) + "\n" for ev in events)

    proc = MagicMock()
    proc.stdout = io.StringIO(lines)

    session_id, parsed_events = parse_opencode_event_stream(proc, quiet=True)
    assert session_id == "ses_test_abc"
    assert len(parsed_events) == 4
    assert parsed_events[1]["type"] == "tool_use"


def test_evaluate_sdrf_quality_missing():
    res = evaluate_sdrf_quality("/path/does/not/exist.sdrf.tsv", {})
    assert res["exists"] is False
    assert res["file"] == "/path/does/not/exist.sdrf.tsv"

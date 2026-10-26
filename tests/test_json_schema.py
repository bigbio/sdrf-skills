"""Tests for the evidence-manifest and review-report JSON Schemas and their stdlib validator."""

from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tools import json_schema, review_gate
from tools.json_schema import (
    SCHEMAS,
    check_supported,
    load_schema,
    manifest_errors,
    schema_errors,
)
from tools.review_gate import (
    REQUIRED_CHECKS,
    ReviewGateError,
    artifact_digest,
    report_schema_errors,
    run_cli,
    validate_report,
)

REPO = Path(__file__).resolve().parent.parent
CONTRACT = REPO / "skills" / "sdrf-adversarial-review" / "references" / "review-contract.md"


def _contract_examples() -> list[tuple[str, dict]]:
    blocks = re.findall(r"```json\n(.*?)```", CONTRACT.read_text(encoding="utf-8"), flags=re.DOTALL)
    examples = [json.loads(block) for block in blocks]
    return [("review-report" if "verdict" in e else "evidence-manifest", e) for e in examples]


CONTRACT_EXAMPLES = _contract_examples()
EXAMPLES = {
    "evidence-manifest": next(e for kind, e in CONTRACT_EXAMPLES if kind == "evidence-manifest"),
    "review-report": next(e for kind, e in CONTRACT_EXAMPLES if e.get("verdict") == "PASS"),
}


def _manifest() -> dict:
    return copy.deepcopy(EXAMPLES["evidence-manifest"])


def _report() -> dict:
    return copy.deepcopy(EXAMPLES["review-report"])


def _failing_report() -> dict:
    report = _report()
    report["verdict"] = "FAIL"
    report["checks"]["omission_safety"]["status"] = "fail"
    report["findings"][0]["severity"] = "blocker"
    return report


def _without(doc: dict, *path: str) -> dict:
    target = doc
    for key in path[:-1]:
        target = target[key]
    del target[path[-1]]
    return doc


def _with(doc: dict, value, *path) -> dict:
    target = doc
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return doc


BAD_MANIFESTS = {
    "no sources": lambda: _without(_manifest(), "sources"),
    "empty sources": lambda: _with(_manifest(), [], "sources"),
    "no claims": lambda: _without(_manifest(), "claims"),
    "blank dataset": lambda: _with(_manifest(), "  ", "dataset"),
    "wrong schema version": lambda: _with(_manifest(), 2, "schema_version"),
    "boolean schema version": lambda: _with(_manifest(), True, "schema_version"),
    "source without location": lambda: _without(_manifest(), "sources", 0, "location"),
    "claim without evidence": lambda: _without(_manifest(), "claims", 0, "evidence"),
    "source_ids not a list": lambda: _with(_manifest(), "pride", "claims", 0, "source_ids"),
    "claim without sources": lambda: _with(_manifest(), [], "claims", 0, "source_ids"),
    "limitation not a string": lambda: _with(_manifest(), [None], "limitations"),
}

BAD_REPORTS = {
    "unknown verdict": lambda: _with(_report(), "MAYBE", "verdict"),
    "PASS with a failed check": lambda: _with(_report(), "fail", "checks", "spec_compliance", "status"),
    "unknown check status": lambda: _with(_report(), "skipped", "checks", "file_mapping", "status"),
    "no digest": lambda: _without(_report(), "artifact_sha256"),
    "blank summary": lambda: _with(_report(), "", "summary"),
    "not independent": lambda: _with(_report(), False, "reviewer_context", "independent"),
    "omission safety missing": lambda: _without(_report(), "checks", "omission_safety"),
    "omission safety waived": lambda: _with(
        _report(), "not_applicable", "checks", "omission_safety", "status"
    ),
    "check without evidence": lambda: _without(_report(), "checks", "file_mapping", "evidence"),
    "important finding": lambda: _with(_report(), "important", "findings", 0, "severity"),
    "finding without location": lambda: _without(_report(), "findings", 0, "location"),
    "findings not a list": lambda: _with(_report(), {}, "findings"),
    "blank evidence manifest path": lambda: _with(_report(), " ", "evidence_manifest"),
    "null evidence manifest path": lambda: _with(_report(), None, "evidence_manifest"),
    "confidence above 1": lambda: _with(_report(), 1.5, "confidence"),
    "boolean confidence": lambda: _with(_report(), True, "confidence"),
    "coverage without deposited runs": lambda: _with(_report(), {"matched_runs": 3}, "coverage"),
    "negative matched runs": lambda: _with(_report(), {"deposited_runs": 3, "matched_runs": -1}, "coverage"),
}


@pytest.mark.parametrize("name", sorted(SCHEMAS))
def test_schema_is_valid_draft_2020_12(name):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.Draft202012Validator.check_schema(load_schema(name))


@pytest.mark.parametrize("name,example", CONTRACT_EXAMPLES)
def test_contract_example_is_valid(name, example):
    assert schema_errors(load_schema(name), example) == []


def test_failing_report_is_valid_but_never_approved():
    report = _failing_report()
    assert report_schema_errors(report) == []
    with pytest.raises(ReviewGateError, match="verdict must be PASS"):
        validate_report(report, report["artifact"], report["artifact_sha256"])


@pytest.mark.parametrize("case", sorted(BAD_MANIFESTS))
def test_bad_manifest_is_rejected(case):
    assert schema_errors(load_schema("evidence-manifest"), BAD_MANIFESTS[case]())


@pytest.mark.parametrize("case", sorted(BAD_REPORTS))
def test_bad_report_is_rejected(case):
    assert report_schema_errors(BAD_REPORTS[case]())


@pytest.mark.parametrize(
    "name,factory",
    [("evidence-manifest", f) for f in BAD_MANIFESTS.values()]
    + [("review-report", f) for f in BAD_REPORTS.values()]
    + [(name, lambda name=name: copy.deepcopy(EXAMPLES[name])) for name in sorted(SCHEMAS)]
    + [("review-report", _failing_report)],
)
def test_validator_agrees_with_reference_implementation(name, factory):
    jsonschema = pytest.importorskip("jsonschema")
    document = factory()
    reference = jsonschema.Draft202012Validator(load_schema(name)).is_valid(document)
    assert (schema_errors(load_schema(name), document) == []) == reference


def test_report_severity_is_case_insensitive():
    report = _with(_report(), "Minor", "findings", 0, "severity")
    assert report_schema_errors(report) == []


def test_required_checks_come_from_the_schema():
    assert REQUIRED_CHECKS["omission_safety"] == {"pass"}
    assert REQUIRED_CHECKS["file_mapping"] == {"pass", "not_applicable"}
    assert set(REQUIRED_CHECKS) == set(EXAMPLES["review-report"]["checks"])


def test_unsupported_keyword_is_refused_at_any_depth():
    schema = {"type": "object", "properties": {"a": {"type": "array", "items": {"format": "uri"}}}}
    with pytest.raises(ValueError, match=r"properties\.a\.items: format"):
        check_supported(schema)


@pytest.mark.parametrize(
    "schema,message",
    [({"then": {"type": "string"}}, "'then' without 'if'"), ({"type": "date"}, "Unsupported type")],
)
def test_schema_shapes_the_validator_cannot_honour_are_refused(schema, message):
    with pytest.raises(ValueError, match=message):
        check_supported(schema)


def test_manifest_claim_must_cite_a_defined_source():
    manifest = _with(_manifest(), ["pride", "supplement"], "claims", 0, "source_ids")
    assert schema_errors(load_schema("evidence-manifest"), manifest) == []
    assert manifest_errors(manifest) == [
        "claims[0].source_ids cites 'supplement', which is not in sources[].id"
    ]


def test_float_schema_version_equals_integer():
    assert schema_errors({"const": 1}, 1.0) == []
    assert schema_errors({"const": 1}, True)


def test_review_gate_runs_as_a_plain_script(tmp_path):
    # The Stop hook runs the file directly; -S keeps an editable install off sys.path.
    proc = subprocess.run(
        [sys.executable, "-S", str(REPO / "tools" / "review_gate.py"), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr


def _git_repo_with_sdrf(root: Path) -> Path:
    for args in (["init", "-q"], ["config", "user.email", "t@example.org"], ["config", "user.name", "T"]):
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
    artifact = root / "PXD000001.sdrf.tsv"
    artifact.write_text("source name\tassay name\ns1\trun1\n", encoding="utf-8")
    return artifact


def test_script_mode_never_loads_a_shadowing_tools_package(tmp_path):
    shadow = tmp_path / "shadow" / "tools"
    shadow.mkdir(parents=True)
    (shadow / "__init__.py").write_text("", encoding="utf-8")
    (shadow / "json_schema.py").write_text(
        "def load_schema(name):\n    return {}\n\n"
        "def schema_errors(schema, instance, path=''):\n    return []\n",
        encoding="utf-8",
    )
    repo = tmp_path / "repo"
    repo.mkdir()
    artifact = _git_repo_with_sdrf(repo)
    report = _with(_report(), False, "reviewer_context", "independent")
    report.update(artifact=artifact.name, artifact_sha256=artifact_digest(artifact))
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, "-S", str(REPO / "tools" / "review_gate.py"), "approve", artifact.name,
         "--report", str(report_path), "--reviewer", "r", "--cwd", str(repo)],
        cwd=tmp_path,
        env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(shadow.parent), "HOME": str(tmp_path)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "independent must be true" in proc.stderr


@pytest.fixture
def missing_report_schema(tmp_path, monkeypatch):
    monkeypatch.setitem(json_schema.SCHEMAS, "review-report", tmp_path / "missing.schema.json")
    review_gate.report_schema.cache_clear()
    yield
    review_gate.report_schema.cache_clear()


def test_missing_schema_fails_approval_but_not_the_gate(tmp_path, missing_report_schema):
    artifact = _git_repo_with_sdrf(tmp_path)
    report = _report()
    report.update(artifact=artifact.name, artifact_sha256=artifact_digest(artifact))
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    assert run_cli(["gate", "--cwd", str(tmp_path)]) == 1
    assert run_cli(["approve", artifact.name, "--report", str(report_path),
                    "--reviewer", "r", "--cwd", str(tmp_path)]) == 2
    with pytest.raises(ReviewGateError, match="Cannot load the review report schema"):
        validate_report(report, report["artifact"], report["artifact_sha256"])


def _cli(monkeypatch, *argv: str) -> int:
    from tools.cli import main

    monkeypatch.setattr(sys, "argv", ["tools", "schema-check", *argv])
    with pytest.raises(SystemExit) as exit_info:
        main()
    return exit_info.value.code


def test_cli_schema_check_accepts_valid_manifest(tmp_path, monkeypatch, capsys):
    path = tmp_path / "PXD000001.evidence.json"
    path.write_text(json.dumps(_manifest()), encoding="utf-8")
    assert _cli(monkeypatch, str(path)) == 0
    assert "valid evidence-manifest" in capsys.readouterr().out


def test_cli_schema_check_lists_problems(tmp_path, monkeypatch, capsys):
    path = tmp_path / "report.json"
    path.write_text(json.dumps(BAD_REPORTS["not independent"]()), encoding="utf-8")
    assert _cli(monkeypatch, str(path)) == 1
    out = capsys.readouterr().out
    assert "against the review-report schema" in out
    assert "reviewer_context.independent must be true" in out


def test_cli_schema_check_reports_unknown_source_ids(tmp_path, monkeypatch, capsys):
    path = tmp_path / "PXD000001.evidence.json"
    path.write_text(json.dumps(_with(_manifest(), ["nope"], "claims", 0, "source_ids")), encoding="utf-8")
    assert _cli(monkeypatch, str(path), "--schema", "evidence-manifest") == 1
    assert "cites 'nope'" in capsys.readouterr().out


@pytest.mark.parametrize("name", sorted(SCHEMAS))
def test_cli_schema_check_prints_schema(name, monkeypatch, capsys):
    assert _cli(monkeypatch, "--print-schema", name) == 0
    assert json.loads(capsys.readouterr().out) == load_schema(name)


def test_cli_print_schema_refuses_a_file_argument(monkeypatch):
    assert _cli(monkeypatch, "--print-schema", "evidence-manifest", "x.json") == 2


def test_optional_confidence_and_coverage_are_valid():
    report = _with(_report(), 0.9, "confidence")
    report = _with(report, {"deposited_runs": 4, "matched_runs": 4, "fraction": 1.0, "missing": []}, "coverage")
    assert schema_errors(load_schema("review-report"), report) == []

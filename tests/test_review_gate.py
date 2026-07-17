"""Tests for hash-bound independent SDRF review receipts."""

from __future__ import annotations

import io
import json
import os
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from tools.review_gate import (
    REQUIRED_CHECKS,
    REVIEWER_SKILL,
    ReviewGateError,
    _state_lock,
    approve_artifact,
    artifact_digest,
    handle_stop_hook,
    review_status,
    run_cli,
    state_path,
    track_artifacts,
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def review_repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "review@example.org")
    _git(tmp_path, "config", "user.name", "Review Test")
    (tmp_path / "README.md").write_text("fixture\n", encoding="utf-8")
    _git(tmp_path, "add", "README.md")
    _git(tmp_path, "commit", "-qm", "initial")
    return tmp_path


def _write_sdrf(repo: Path, value: str = "Homo sapiens") -> Path:
    artifact = repo / "data" / "PXD000001.sdrf.tsv"
    artifact.parent.mkdir(exist_ok=True)
    artifact.write_text(
        "source name\tcharacteristics[organism]\tassay name\n"
        f"sample-1\t{value}\trun-1\n",
        encoding="utf-8",
    )
    return artifact


def _passing_report(artifact: str, digest: str) -> dict:
    return {
        "schema_version": 1,
        "artifact": artifact,
        "artifact_sha256": digest,
        "verdict": "PASS",
        "summary": "Independent review found no blocking or important issues.",
        "reviewer_context": {
            "independent": True,
            "context": "fresh test reviewer without producer transcript",
        },
        "checks": {
            name: {"status": "pass", "evidence": f"{name} checked independently"}
            for name in REQUIRED_CHECKS
        },
        "findings": [],
    }


def test_changed_sdrf_is_pending_and_gate_blocks(review_repo: Path):
    artifact = _write_sdrf(review_repo)

    status = review_status(review_repo)

    assert status["pending"][0]["artifact"] == artifact.relative_to(review_repo).as_posix()
    assert status["pending"][0]["reason"] == "missing-review-receipt"
    assert run_cli(["gate", "--cwd", str(review_repo), "--json"]) == 1


def test_passing_receipt_is_bound_to_current_hash(review_repo: Path, tmp_path: Path):
    artifact = _write_sdrf(review_repo)
    rel = artifact.relative_to(review_repo).as_posix()
    track_artifacts([artifact], cwd=review_repo)
    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps(_passing_report(rel, artifact_digest(artifact))), encoding="utf-8"
    )

    result = approve_artifact(
        artifact,
        report_path,
        reviewer="independent-test-agent",
        cwd=review_repo,
    )

    assert result["verdict"] == "PASS"
    assert review_status(review_repo)["pending"] == []
    artifact.write_text(artifact.read_text().replace("Homo sapiens", "Mus musculus"))
    pending = review_status(review_repo)["pending"]
    assert pending[0]["reason"] == "artifact-changed-after-review"


def test_report_with_important_finding_cannot_approve(review_repo: Path, tmp_path: Path):
    artifact = _write_sdrf(review_repo)
    rel = artifact.relative_to(review_repo).as_posix()
    report = _passing_report(rel, artifact_digest(artifact))
    report["findings"] = [
        {
            "severity": "important",
            "category": "source_evidence",
            "location": "characteristics[organism] row 1",
            "message": "Organism evidence is missing.",
            "evidence": "No evidence-manifest claim covers this value.",
        }
    ]
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    with pytest.raises(ReviewGateError, match="unresolved important"):
        approve_artifact(artifact, report_path, "independent-test-agent", cwd=review_repo)


def test_stale_report_cannot_approve_content_it_never_reviewed(review_repo: Path, tmp_path: Path):
    artifact = _write_sdrf(review_repo)
    rel = artifact.relative_to(review_repo).as_posix()
    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps(_passing_report(rel, artifact_digest(artifact))), encoding="utf-8"
    )

    artifact.write_text(artifact.read_text().replace("Homo sapiens", "Fabricated organism"))

    with pytest.raises(ReviewGateError, match="must be re-reviewed"):
        approve_artifact(artifact, report_path, "independent-test-agent", cwd=review_repo)
    assert review_status(review_repo)["approved"] == []


def test_report_without_reviewed_hash_cannot_approve(review_repo: Path, tmp_path: Path):
    artifact = _write_sdrf(review_repo)
    rel = artifact.relative_to(review_repo).as_posix()
    report = _passing_report(rel, artifact_digest(artifact))
    del report["artifact_sha256"]
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    with pytest.raises(ReviewGateError, match="artifact_sha256 is required"):
        approve_artifact(artifact, report_path, "independent-test-agent", cwd=review_repo)


def test_omission_safety_check_is_required(review_repo: Path, tmp_path: Path):
    artifact = _write_sdrf(review_repo)
    rel = artifact.relative_to(review_repo).as_posix()
    report = _passing_report(rel, artifact_digest(artifact))
    del report["checks"]["omission_safety"]
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    with pytest.raises(ReviewGateError, match="checks.omission_safety is required"):
        approve_artifact(artifact, report_path, "independent-test-agent", cwd=review_repo)


def test_omission_safety_cannot_be_waived_as_not_applicable(review_repo: Path, tmp_path: Path):
    artifact = _write_sdrf(review_repo)
    rel = artifact.relative_to(review_repo).as_posix()
    report = _passing_report(rel, artifact_digest(artifact))
    report["checks"]["omission_safety"] = {
        "status": "not_applicable",
        "evidence": "Reviewer skipped the unsupported-addition sweep.",
    }
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    with pytest.raises(ReviewGateError, match="checks.omission_safety.status must be one of: pass"):
        approve_artifact(artifact, report_path, "independent-test-agent", cwd=review_repo)


#: Falsification passes named in sdrf-adversarial-review/SKILL.md → the check key
#: that makes each one reportable. Every pass needs an entry: a pass with no
#: enforced check can be silently skipped and still yield a PASS verdict.
PASS_TO_CHECK = {
    "Specification compliance": "spec_compliance",
    "Ontology integrity": "ontology_integrity",
    "Source evidence": "source_evidence",
    "File mapping": "file_mapping",
    "Design consistency": "design_consistency",
    "Omission safety": "omission_safety",
}


def test_every_falsification_pass_in_the_skill_has_an_enforced_check():
    skill = (
        Path(__file__).parent.parent / "skills" / "sdrf-adversarial-review" / "SKILL.md"
    ).read_text(encoding="utf-8")
    passes = re.findall(r"^\d+\. \*\*(.+?)\*\*", skill, flags=re.MULTILINE)

    assert passes, "falsification passes should be discoverable in SKILL.md"
    for name in passes:
        assert name in PASS_TO_CHECK, f"SKILL.md mandates '{name}' but no check enforces it"
        assert PASS_TO_CHECK[name] in REQUIRED_CHECKS


def test_concurrent_tracking_keeps_every_artifact(review_repo: Path):
    """Reviewer subagents run in parallel; an unlocked update would drop receipts."""
    artifacts = []
    for index in range(12):
        path = review_repo / "data" / f"PXD{index:06d}.sdrf.tsv"
        path.parent.mkdir(exist_ok=True)
        path.write_text(f"source name\tassay name\nsample-{index}\trun-{index}\n", encoding="utf-8")
        artifacts.append(path)

    with ThreadPoolExecutor(max_workers=12) as pool:
        list(pool.map(lambda a: track_artifacts([a], cwd=review_repo), artifacts))

    tracked = json.loads(state_path(review_repo).read_text(encoding="utf-8"))["artifacts"]
    assert len(tracked) == 12


def test_state_lock_is_exclusive(review_repo: Path, monkeypatch):
    monkeypatch.setattr("tools.review_gate.LOCK_TIMEOUT_SECONDS", 0.2)

    with _state_lock(review_repo):
        with pytest.raises(ReviewGateError, match="Timed out waiting for the review state lock"):
            with _state_lock(review_repo):
                pass


def test_stale_lock_is_broken_rather_than_wedging_the_gate(review_repo: Path):
    lock = state_path(review_repo).with_suffix(".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.touch()
    os.utime(lock, (time.time() - 3600, time.time() - 3600))

    with _state_lock(review_repo):
        pass  # A crashed holder must not block the gate forever.

    assert not lock.exists()


def test_corrupt_state_is_rebuilt_instead_of_raising(review_repo: Path):
    artifact = _write_sdrf(review_repo)
    track_artifacts([artifact], cwd=review_repo)
    state_file = state_path(review_repo)
    state_file.write_text('{"schema_version":1,"artifacts":', encoding="utf-8")

    tracked = track_artifacts([artifact], cwd=review_repo)

    assert tracked == ["data/PXD000001.sdrf.tsv"]
    assert state_file.with_name(state_file.name + ".corrupt").exists()
    # Losing state reopens artifacts for review -- the safe direction.
    assert review_status(review_repo)["pending"][0]["reason"] == "missing-review-receipt"


def test_report_requires_independent_context(review_repo: Path, tmp_path: Path):
    artifact = _write_sdrf(review_repo)
    rel = artifact.relative_to(review_repo).as_posix()
    report = _passing_report(rel, artifact_digest(artifact))
    report["reviewer_context"]["independent"] = False
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    with pytest.raises(ReviewGateError, match="independent must be true"):
        approve_artifact(artifact, report_path, "producer", cwd=review_repo)


def test_reverted_artifact_no_longer_requires_review(review_repo: Path):
    artifact = _write_sdrf(review_repo)
    _git(review_repo, "add", "data/PXD000001.sdrf.tsv")
    _git(review_repo, "commit", "-qm", "add SDRF")
    track_artifacts([artifact], cwd=review_repo)
    artifact.write_text(artifact.read_text().replace("Homo sapiens", "Mus musculus"))
    track_artifacts([artifact], cwd=review_repo)

    artifact.write_text(artifact.read_text().replace("Mus musculus", "Homo sapiens"))

    assert review_status(review_repo)["pending"] == []


def test_discovery_needs_no_hook_to_have_observed_the_edit(review_repo: Path):
    """The gate reads git directly, so no editor or harness hook is required."""
    _write_sdrf(review_repo)

    pending = review_status(review_repo)["pending"]

    assert pending[0]["artifact"] == "data/PXD000001.sdrf.tsv"


def test_sdrf_committed_on_a_branch_is_caught_without_session_state(review_repo: Path):
    """The merge-base baseline replaces the session-start hook.

    An SDRF created *and* committed is invisible to `git diff HEAD`. This used to
    need a SessionStart hook to record the starting commit, which meant a hook
    that never fired silently let unreviewed content through.
    """
    _git(review_repo, "branch", "-M", "main")
    _git(review_repo, "checkout", "-q", "-b", "annotate")
    _write_sdrf(review_repo)
    _git(review_repo, "add", "data/PXD000001.sdrf.tsv")
    _git(review_repo, "commit", "-qm", "add SDRF in one shell command")

    pending = review_status(review_repo)["pending"]

    assert pending[0]["artifact"] == "data/PXD000001.sdrf.tsv"
    assert pending[0]["reason"] == "missing-review-receipt"


def test_explicit_baseline_override(review_repo: Path):
    _git(review_repo, "branch", "-M", "main")
    base = subprocess.run(
        ["git", "-C", str(review_repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    _git(review_repo, "checkout", "-q", "-b", "annotate")
    _write_sdrf(review_repo)
    _git(review_repo, "add", "data/PXD000001.sdrf.tsv")
    _git(review_repo, "commit", "-qm", "add SDRF")

    pending = review_status(review_repo, baseline=base)["pending"]

    assert pending[0]["artifact"] == "data/PXD000001.sdrf.tsv"


def test_stop_hook_blocks_with_actionable_reason(review_repo: Path):
    _write_sdrf(review_repo)

    response = handle_stop_hook({"cwd": str(review_repo)})

    assert response["decision"] == "block"
    assert "data/PXD000001.sdrf.tsv" in response["reason"]
    # Absolute, derived from __file__ -- $CLAUDE_PLUGIN_ROOT is not available here.
    assert str(REVIEWER_SKILL) in response["reason"]
    assert "$CLAUDE_PLUGIN_ROOT" not in response["reason"]


def test_stop_hook_allows_when_nothing_is_pending(review_repo: Path):
    assert handle_stop_hook({"cwd": str(review_repo)}) == {}


def test_stop_hook_is_noop_outside_git(tmp_path: Path):
    assert handle_stop_hook({"cwd": str(tmp_path)}) == {}


def test_stop_hook_still_blocks_while_stop_hook_active(review_repo: Path):
    """Allowing on stop_hook_active would wave through the first blocked stop."""
    _write_sdrf(review_repo)

    response = handle_stop_hook({"cwd": str(review_repo), "stop_hook_active": True})

    assert response["decision"] == "block"


def test_stop_hook_cli_emits_block_json_and_exits_zero(review_repo: Path, monkeypatch, capsys):
    _write_sdrf(review_repo)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"cwd": str(review_repo)})))

    exit_code = run_cli(["stop-hook"])

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out)["decision"] == "block"


def test_stop_hook_cli_never_wedges_the_session_on_internal_error(
    review_repo: Path, monkeypatch, capsys
):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"cwd": str(review_repo)})))
    monkeypatch.setattr(
        "tools.review_gate.review_status", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    )

    exit_code = run_cli(["stop-hook"])

    out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert "decision" not in out
    assert "boom" in out["systemMessage"]


def test_plugin_config_uses_only_command_hooks():
    config_path = Path(__file__).parent.parent / "hooks" / "hooks.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    events = config["hooks"]

    # Tracking hooks were redundant: discovery reads git on every call.
    assert "PostToolUse" not in events
    stop_hooks = events["Stop"][0]["hooks"]
    assert len(stop_hooks) == 1
    assert stop_hooks[0]["type"] == "command"
    assert "stop-hook" in stop_hooks[0]["command"]
    assert "${CLAUDE_PLUGIN_ROOT}" in stop_hooks[0]["command"]
    # agent-type hooks no-op outside the REPL and never interpolate the plugin root.
    for groups in events.values():
        for group in groups:
            for hook in group["hooks"]:
                assert hook["type"] == "command"

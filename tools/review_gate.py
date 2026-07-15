"""Hash-bound review receipts for independently reviewed SDRF artifacts.

The gate finds SDRFs that differ from the review baseline and requires a passing
structured review report for each one's current SHA-256. Any later edit
invalidates the receipt automatically. State lives under the git directory by
default, keeping review bookkeeping out of the worktree.

Changed artifacts are discovered from git on every call, so the gate does not
depend on any editor, agent harness, or hook having observed the edit. That
keeps it usable from Claude Code, other assistants, CI, and a plain shell alike.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator


SCHEMA_VERSION = 1
DELETED_DIGEST = "deleted"
SDRF_SUFFIXES = (".sdrf.tsv", ".sdrf")
PLUGIN_ROOT = Path(__file__).resolve().parent.parent
REVIEWER_SKILL = PLUGIN_ROOT / "skills" / "sdrf-adversarial-review" / "SKILL.md"
#: Refs tried, in order, when resolving what counts as already-reviewed content.
BASELINE_CANDIDATES = ("@{upstream}", "origin/HEAD", "origin/main", "origin/master", "main", "master")
REQUIRED_CHECKS = {
    "spec_compliance": {"pass"},
    "ontology_integrity": {"pass"},
    "source_evidence": {"pass", "not_applicable"},
    "file_mapping": {"pass", "not_applicable"},
    "design_consistency": {"pass", "not_applicable"},
    "omission_safety": {"pass"},
    "deterministic_validation": {"pass"},
}
BLOCKING_SEVERITIES = {"blocker", "important"}
LOCK_TIMEOUT_SECONDS = 10
STALE_LOCK_SECONDS = 60


class ReviewGateError(ValueError):
    """Raised when an artifact path or a submitted report is invalid."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _run_git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def repository_root(cwd: str | Path | None = None) -> Path:
    start = Path(cwd or os.getcwd()).resolve()
    proc = _run_git(start, "rev-parse", "--show-toplevel", check=False)
    if proc.returncode != 0:
        raise ReviewGateError(f"Not inside a git repository: {start}")
    return Path(proc.stdout.decode().strip()).resolve()


def state_path(root: Path) -> Path:
    override = os.environ.get("SDRF_REVIEW_STATE_DIR")
    if override:
        base = Path(override).expanduser().resolve()
    else:
        proc = _run_git(root, "rev-parse", "--absolute-git-dir", check=False)
        base = Path(proc.stdout.decode().strip()).resolve() if proc.returncode == 0 else root / ".git"
        base = base / "sdrf-adversarial-review"
    return base / "state.json"


def _empty_state() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "artifacts": {}, "session": {}}


def _quarantine_state(path: Path, reason: str) -> None:
    """Move an unusable state file aside so the gate rebuilds instead of blocking every edit.

    Discarding state only ever loses receipts and force-review flags, which makes
    affected artifacts pending again — the safe direction. Discovery via
    changed_artifacts rebuilds the tracking set on the next call.
    """
    backup = path.with_name(path.name + ".corrupt")
    try:
        os.replace(path, backup)
    except OSError:
        return
    print(
        f"sdrf review gate: {reason}; moved aside to {backup} and rebuilt review state. "
        "Artifacts already approved will require a fresh independent review.",
        file=sys.stderr,
    )


def _lock_is_stale(lock: Path) -> bool:
    try:
        return time.time() - lock.stat().st_mtime > STALE_LOCK_SECONDS
    except OSError:
        return False


@contextmanager
def _state_lock(root: Path) -> Iterator[None]:
    """Serialize read-modify-write of the state file across processes.

    Reviewer subagents approve artifacts in parallel, and a Stop hook can run
    while one is still writing. Without this, two updates that read the same
    snapshot would silently drop one of the receipts.

    Uses an O_EXCL lock file rather than fcntl so this behaves the same on
    Windows, where the plugin is also expected to run.
    """
    lock = state_path(root).with_suffix(".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
    fd: int | None = None
    while fd is None:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if _lock_is_stale(lock):
                # A crashed holder must not wedge the gate permanently.
                lock.unlink(missing_ok=True)
                continue
            if time.monotonic() >= deadline:
                raise ReviewGateError(
                    f"Timed out waiting for the review state lock at {lock}. "
                    "Remove it if no other sdrf review is running."
                ) from None
            time.sleep(0.05)
    try:
        yield
    finally:
        os.close(fd)
        lock.unlink(missing_ok=True)


def _load_state(root: Path) -> dict[str, Any]:
    path = state_path(root)
    if not path.exists():
        return _empty_state()
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _quarantine_state(path, f"unreadable review state at {path} ({exc})")
        return _empty_state()
    if state.get("schema_version") != SCHEMA_VERSION or not isinstance(state.get("artifacts"), dict):
        _quarantine_state(path, f"unsupported review state schema at {path}")
        return _empty_state()
    return state


def _save_state(root: Path, state: dict[str, Any]) -> None:
    path = state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(state, indent=2, sort_keys=True) + "\n"
    fd, tmp_name = tempfile.mkstemp(prefix="state-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def _is_sdrf(path: Path) -> bool:
    name = path.name.lower()
    return any(name.endswith(suffix) for suffix in SDRF_SUFFIXES)


def _resolve_artifact(raw_path: str | Path, root: Path, cwd: str | Path | None = None) -> tuple[Path, str]:
    path = Path(raw_path)
    if not path.is_absolute():
        path = Path(cwd or root) / path
    path = path.resolve()
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError as exc:
        raise ReviewGateError(f"Artifact is outside repository {root}: {path}") from exc
    if not _is_sdrf(path):
        raise ReviewGateError(f"Not an SDRF artifact: {rel}")
    return path, rel


def artifact_digest(path: Path) -> str:
    if not path.exists():
        return DELETED_DIGEST
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _head_digest(root: Path, rel: str) -> str:
    return _ref_digest(root, rel, "HEAD")


def _ref_digest(root: Path, rel: str, ref: str) -> str:
    proc = _run_git(root, "show", f"{ref}:{rel}", check=False)
    if proc.returncode != 0:
        return DELETED_DIGEST
    return hashlib.sha256(proc.stdout).hexdigest()


def _decode_paths(payload: bytes) -> list[str]:
    return [item.decode("utf-8", errors="surrogateescape") for item in payload.split(b"\0") if item]


def changed_artifacts(root: Path, baseline_ref: str | None = None) -> list[str]:
    """Return changed, staged, deleted, and untracked SDRF paths."""
    pathspec = ("--", "*.sdrf.tsv", "*.sdrf", "**/*.sdrf.tsv", "**/*.sdrf")
    changed: set[str] = set()
    diff = _run_git(root, "diff", "--name-only", "-z", "HEAD", *pathspec, check=False)
    if diff.returncode == 0:
        changed.update(_decode_paths(diff.stdout))
    if baseline_ref:
        committed = _run_git(
            root, "diff", "--name-only", "-z", baseline_ref, "HEAD", *pathspec, check=False
        )
        if committed.returncode == 0:
            changed.update(_decode_paths(committed.stdout))
    untracked = _run_git(
        root, "ls-files", "--others", "--exclude-standard", "-z", *pathspec, check=False
    )
    if untracked.returncode == 0:
        changed.update(_decode_paths(untracked.stdout))
    return sorted(path for path in changed if _is_sdrf(Path(path)))


def track_artifacts(
    artifacts: Iterable[str | Path],
    cwd: str | Path | None = None,
    *,
    baseline_ref: str | None = None,
    force_review: bool = False,
) -> list[str]:
    root = repository_root(cwd)
    resolved = [_resolve_artifact(raw_path, root, cwd) for raw_path in artifacts]
    tracked: list[str] = []
    with _state_lock(root):
        state = _load_state(root)
        for path, rel in resolved:
            entry = state["artifacts"].setdefault(rel, {})
            digest = artifact_digest(path)
            if force_review:
                entry.pop("receipt", None)
                entry["force_review"] = True
            receipt = entry.get("receipt")
            if "baseline_sha256" not in entry:
                entry["baseline_sha256"] = (
                    _ref_digest(root, rel, baseline_ref) if baseline_ref else _head_digest(root, rel)
                )
            elif isinstance(receipt, dict) and receipt.get("artifact_sha256") != digest:
                entry["baseline_sha256"] = receipt.get("artifact_sha256")
            entry["last_seen_sha256"] = digest
            entry["tracked_at"] = _utc_now()
            tracked.append(rel)
        if tracked:
            _save_state(root, state)
    return tracked


def baseline_ref(root: Path, override: str | None = None) -> str | None:
    """Resolve the commit that changed SDRFs are measured against.

    Prefers the branch's upstream, then origin's default branch, then a local
    default branch, and returns its merge base with HEAD so only work done on
    this branch counts as unreviewed. This is what lets an SDRF that was created
    *and committed* still be caught, without depending on a session-start hook
    having recorded where the work began.

    Returns None when no candidate resolves (a fresh repo with no remote and no
    other branch), leaving only working-tree changes detectable.
    """
    if override:
        return override
    for candidate in BASELINE_CANDIDATES:
        exists = _run_git(root, "rev-parse", "--verify", "--quiet", f"{candidate}^{{commit}}", check=False)
        if exists.returncode != 0:
            continue
        merge_base = _run_git(root, "merge-base", candidate, "HEAD", check=False)
        if merge_base.returncode != 0:
            continue
        base = merge_base.stdout.decode().strip()
        if base:
            return base
    return None


def track_changed(cwd: str | Path | None = None, *, baseline: str | None = None) -> list[str]:
    root = repository_root(cwd)
    base = baseline_ref(root, baseline)
    return track_artifacts(
        changed_artifacts(root, baseline_ref=base),
        cwd=root,
        baseline_ref=base,
    )


def review_status(cwd: str | Path | None = None, *, baseline: str | None = None) -> dict[str, Any]:
    root = repository_root(cwd)
    track_changed(root, baseline=baseline)
    state = _load_state(root)
    pending: list[dict[str, str]] = []
    approved: list[dict[str, str]] = []
    for rel, entry in sorted(state["artifacts"].items()):
        digest = artifact_digest(root / rel)
        receipt = entry.get("receipt")
        if not entry.get("force_review") and digest == entry.get("baseline_sha256") and not (
            isinstance(receipt, dict) and receipt.get("artifact_sha256") == digest
        ):
            continue
        if not isinstance(receipt, dict):
            pending.append({"artifact": rel, "sha256": digest, "reason": "missing-review-receipt"})
            continue
        if receipt.get("artifact_sha256") != digest:
            pending.append({"artifact": rel, "sha256": digest, "reason": "artifact-changed-after-review"})
            continue
        report = receipt.get("report")
        if not isinstance(report, dict) or report.get("verdict") != "PASS":
            pending.append({"artifact": rel, "sha256": digest, "reason": "review-did-not-pass"})
            continue
        approved.append(
            {
                "artifact": rel,
                "sha256": digest,
                "reviewed_at": str(receipt.get("reviewed_at", "")),
                "reviewer": str(receipt.get("reviewer", "")),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "repo_root": str(root),
        "state_file": str(state_path(root)),
        "pending": pending,
        "approved": approved,
    }


def validate_report(report: dict[str, Any], artifact: str, digest: str) -> None:
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if report.get("artifact") != artifact:
        errors.append(f"artifact must be '{artifact}'")
    report_digest = str(report.get("artifact_sha256", "")).strip()
    if not report_digest:
        errors.append("artifact_sha256 is required and must be the digest of the reviewed content")
    elif report_digest != digest:
        errors.append(
            f"artifact_sha256 {report_digest} is not the current artifact {digest}; "
            "the artifact changed after review and must be re-reviewed"
        )
    if report.get("verdict") != "PASS":
        errors.append("verdict must be PASS")
    if not str(report.get("summary", "")).strip():
        errors.append("summary is required")

    reviewer_context = report.get("reviewer_context")
    if not isinstance(reviewer_context, dict):
        errors.append("reviewer_context is required")
    else:
        if reviewer_context.get("independent") is not True:
            errors.append("reviewer_context.independent must be true")
        if not str(reviewer_context.get("context", "")).strip():
            errors.append("reviewer_context.context is required")

    findings = report.get("findings")
    if not isinstance(findings, list):
        errors.append("findings must be a list")
    else:
        for index, finding in enumerate(findings):
            if not isinstance(finding, dict):
                errors.append(f"findings[{index}] must be an object")
                continue
            severity = str(finding.get("severity", "")).lower()
            if severity not in {"blocker", "important", "minor"}:
                errors.append(f"findings[{index}].severity is invalid")
            if severity in BLOCKING_SEVERITIES:
                errors.append(f"findings[{index}] is unresolved {severity}")
            for field in ("category", "location", "message", "evidence"):
                if not str(finding.get(field, "")).strip():
                    errors.append(f"findings[{index}].{field} is required")

    checks = report.get("checks")
    if not isinstance(checks, dict):
        errors.append("checks must be an object")
    else:
        for name, allowed_statuses in REQUIRED_CHECKS.items():
            check = checks.get(name)
            if not isinstance(check, dict):
                errors.append(f"checks.{name} is required")
                continue
            status = str(check.get("status", ""))
            if status not in allowed_statuses:
                allowed = ", ".join(sorted(allowed_statuses))
                errors.append(f"checks.{name}.status must be one of: {allowed}")
            if not str(check.get("evidence", "")).strip():
                errors.append(f"checks.{name}.evidence is required")
    if errors:
        raise ReviewGateError("Invalid review report:\n- " + "\n- ".join(errors))


def approve_artifact(
    artifact: str | Path,
    report_path: str | Path,
    reviewer: str,
    cwd: str | Path | None = None,
) -> dict[str, Any]:
    if not reviewer.strip():
        raise ReviewGateError("reviewer is required")
    root = repository_root(cwd)
    path, rel = _resolve_artifact(artifact, root, cwd)
    digest = artifact_digest(path)
    try:
        report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReviewGateError(f"Cannot read review report {report_path}: {exc}") from exc
    if not isinstance(report, dict):
        raise ReviewGateError("Review report must be a JSON object")
    validate_report(report, rel, digest)
    with _state_lock(root):
        state = _load_state(root)
        entry = state["artifacts"].setdefault(rel, {})
        entry["last_seen_sha256"] = digest
        entry["tracked_at"] = entry.get("tracked_at") or _utc_now()
        entry["receipt"] = {
            "artifact_sha256": digest,
            "reviewed_at": _utc_now(),
            "reviewer": reviewer,
            "report": report,
        }
        entry["force_review"] = False
        _save_state(root, state)
    return {"artifact": rel, "artifact_sha256": digest, "reviewer": reviewer, "verdict": "PASS"}


def handle_stop_hook(payload: dict[str, Any]) -> dict[str, Any]:
    """Block completion while any changed SDRF lacks a passing review receipt.

    Deliberately does not return success on `stop_hook_active`. That is the
    usual advice for Stop hooks, but for a gate it would wave through the very
    first blocked stop regardless of whether a review happened. Claude Code's
    own block cap bounds the loop instead, as it does for the ralph-loop hook.

    Emits paths derived from this file's location rather than
    $CLAUDE_PLUGIN_ROOT, which is not interpolated into an agent prompt and is
    not exported to a hook agent's shell.
    """
    cwd = payload.get("cwd") or os.getcwd()
    try:
        status = review_status(cwd)
    except ReviewGateError:
        return {}  # Not a git repository: there is nothing to gate.
    pending = status["pending"]
    if not pending:
        return {}
    listing = "\n".join(f"  - {item['artifact']} ({item['reason']})" for item in pending)
    gate_cmd = f"python3 {PLUGIN_ROOT / 'tools' / 'review_gate.py'}"
    return {
        "decision": "block",
        "reason": (
            f"{len(pending)} SDRF artifact(s) have no passing independent review:\n{listing}\n\n"
            f"For each, dispatch a fresh reviewer subagent following {REVIEWER_SKILL}. Pass it the "
            "artifact path and evidence, but not your reasoning or conclusions. You must not review "
            "or approve your own work in this context. The reviewer records a passing verdict with:\n"
            f"  {gate_cmd} approve <artifact> --report <report.json> --reviewer <name> "
            f"--cwd {status['repo_root']}\n"
            f"Re-check with: {gate_cmd} gate --cwd {status['repo_root']}\n"
            "If an artifact cannot pass review, report the findings to the user rather than retrying."
        ),
        "systemMessage": f"SDRF review gate: {len(pending)} artifact(s) pending independent review",
    }


def _print_status(status: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(status, indent=2, sort_keys=True))
        return
    for item in status["pending"]:
        print(f"PENDING\t{item['artifact']}\t{item['reason']}\t{item['sha256']}")
    for item in status["approved"]:
        print(f"APPROVED\t{item['artifact']}\t{item['reviewer']}\t{item['sha256']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    p = subparsers.add_parser("track", help="Mark one or more SDRFs as requiring review")
    p.add_argument("artifacts", nargs="+")
    p.add_argument("--cwd", default=None)
    p = subparsers.add_parser("track-changed", help="Track changed and untracked SDRFs")
    p.add_argument("--cwd", default=None)
    p.add_argument("--baseline", default=None, help="Ref to measure changes against (default: auto)")
    subparsers.add_parser("stop-hook", help="Consume a Claude Stop event from stdin and gate on it")
    for name in ("pending", "status", "gate"):
        p = subparsers.add_parser(name, help=f"Show {name} review state")
        p.add_argument("--cwd", default=None)
        p.add_argument("--json", action="store_true")
        p.add_argument("--baseline", default=None, help="Ref to measure changes against (default: auto)")
    p = subparsers.add_parser("approve", help="Record a passing independent review")
    p.add_argument("artifact")
    p.add_argument("--report", required=True)
    p.add_argument("--reviewer", required=True)
    p.add_argument("--cwd", default=None)
    return parser


def run_cli(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "track":
            for rel in track_artifacts(args.artifacts, cwd=args.cwd, force_review=True):
                print(rel)
            return 0
        if args.command == "track-changed":
            for rel in track_changed(cwd=args.cwd, baseline=args.baseline):
                print(rel)
            return 0
        if args.command == "stop-hook":
            # A hook must never wedge the session: report internal faults and let
            # the stop proceed. The `gate` command stays fail-closed, and the
            # skills call it before contributing, so enforcement is not lost here.
            try:
                response = handle_stop_hook(json.load(sys.stdin))
            except Exception as exc:  # noqa: BLE001
                print(json.dumps({"systemMessage": f"SDRF review gate error: {exc}"}))
                return 0
            if response:
                print(json.dumps(response))
            return 0
        if args.command in {"pending", "status", "gate"}:
            status = review_status(cwd=args.cwd, baseline=args.baseline)
            _print_status(status, args.json)
            return 1 if args.command == "gate" and status["pending"] else 0
        if args.command == "approve":
            result = approve_artifact(args.artifact, args.report, args.reviewer, cwd=args.cwd)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
    except (ReviewGateError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 2


def main() -> None:
    raise SystemExit(run_cli())


if __name__ == "__main__":
    main()

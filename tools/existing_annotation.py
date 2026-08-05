"""Detect and audit an SDRF annotation that already exists for a dataset.

Annotating a dataset that is already annotated is not a no-op: the existing file
may be complete and correct (in which case re-annotating wastes effort and
produces a noisy diff), or it may be silently wrong (in which case shipping a
"new" annotation alongside it hides the defect). This module answers both
questions mechanically so the skill can stop and ask the user with evidence
rather than guessing.

The audit deliberately only reports defects that can be established from the
deposit itself — run coverage, organism agreement, structural misuse of the
replicate/fraction columns, malformed CV terms. It never judges biological
interpretation, which needs a human.

Typical use, once the skill has established that an annotation exists and has
fetched its text:

    report = audit(existing_sdrf_text, deposited_runs, pride_organisms, accession)
    print(report.render())
    # report.recommendation is a SUGGESTION - the user still chooses.
"""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

# Severity drives the recommendation, not the wording of the message.
BLOCKER = "blocker"   # the annotation misrepresents the deposit
MAJOR = "major"       # real defect, but the file still describes the right data
MINOR = "minor"       # convention drift


@dataclass
class Finding:
    code: str
    severity: str
    summary: str
    evidence: str = ""

    def __str__(self) -> str:
        tail = f"  [{self.evidence}]" if self.evidence else ""
        return f"{self.severity.upper():8s} {self.code}: {self.summary}{tail}"


@dataclass
class AuditReport:
    accession: str
    n_rows: int = 0
    findings: list[Finding] = field(default_factory=list)

    @property
    def blockers(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == BLOCKER]

    @property
    def clean(self) -> bool:
        return not self.findings

    @property
    def recommendation(self) -> str:
        """What to suggest to the user. The user still decides."""
        if self.clean:
            return "leave"
        if self.blockers:
            return "reannotate"
        return "fix"

    def render(self) -> str:
        if self.clean:
            return (
                f"{self.accession} is already annotated ({self.n_rows} rows) and the "
                f"automated audit found no defects."
            )
        headline = (f"{self.accession} is already annotated ({self.n_rows} rows), "
                    f"but the audit found {len(self.findings)} issue(s):")
        lines = [headline, ""]
        order = {BLOCKER: 0, MAJOR: 1, MINOR: 2}
        lines += [f"  {f}" for f in sorted(self.findings, key=lambda f: order[f.severity])]
        return "\n".join(lines)


def _read(sdrf_text: str) -> tuple[list[str], list[list[str]]]:
    # An SDRF saved from Excel commonly carries a UTF-8 BOM. Left in place it
    # turns the first header cell into "﻿source name", every column lookup
    # misses, and the audit reports a clean file — the worst possible failure
    # mode for a gate.
    sdrf_text = sdrf_text.lstrip("﻿")
    rows = list(csv.reader(io.StringIO(sdrf_text), delimiter="\t"))
    if not rows:
        return [], []
    return rows[0], [r for r in rows[1:] if r]


def _cols(header: Sequence[str], name: str) -> list[int]:
    """All indices for a column name — SDRF legitimately repeats some columns."""
    return [i for i, c in enumerate(header) if c.strip() == name]


def _values(rows: Iterable[Sequence[str]], idx: Sequence[int]) -> set[str]:
    return {r[i] for r in rows for i in idx if i < len(r)}


def audit(
    sdrf_text: str,
    deposited_runs: Iterable[str] | None = None,
    pride_organisms: Iterable[str] | None = None,
    accession: str = "",
) -> AuditReport:
    """Audit an existing SDRF against what the deposit actually contains.

    `deposited_runs` and `pride_organisms` are optional: when they are not
    supplied the corresponding checks are skipped rather than guessed at.
    """
    header, rows = _read(sdrf_text)
    report = AuditReport(accession=accession, n_rows=len(rows))
    if not header:
        report.findings.append(Finding("empty", BLOCKER, "the existing SDRF is empty"))
        return report

    # ---- run coverage -----------------------------------------------------
    file_ix = _cols(header, "comment[data file]")
    if deposited_runs is not None and not file_ix:
        # Evidence WAS supplied, so this is not a skipped check - the SDRF
        # cannot support it. Staying silent here would return "leave" for a
        # file that has no run mapping at all.
        report.findings.append(Finding(
            "no_data_file_column", BLOCKER,
            "the SDRF has no comment[data file] column, so no row can be tied "
            "to a deposited run"))
    if deposited_runs is not None and file_ix:
        deposited = {r.strip() for r in deposited_runs if r.strip()}
        raw = _values(rows, file_ix)
        annotated = {v.strip() for v in raw if v.strip()}
        # A blank cell is a real defect, but calling it an "invented run" is
        # confusing, so it is reported on its own.
        if any(not v.strip() for v in raw):
            report.findings.append(Finding(
                "blank_data_file", MAJOR,
                "comment[data file] has blank cell(s), so some rows name no run"))
        missing = deposited - annotated
        invented = annotated - deposited
        if missing:
            report.findings.append(Finding(
                "missing_runs", BLOCKER,
                f"{len(missing)} deposited run(s) are not annotated",
                ", ".join(sorted(missing)[:3]) + ("..." if len(missing) > 3 else "")))
        if invented:
            report.findings.append(Finding(
                "invented_runs", BLOCKER,
                f"{len(invented)} annotated run(s) do not exist in the deposit",
                ", ".join(sorted(invented)[:3]) + ("..." if len(invented) > 3 else "")))

    # ---- organism agreement ----------------------------------------------
    org_ix = _cols(header, "characteristics[organism]")
    if pride_organisms and not org_ix:
        report.findings.append(Finding(
            "no_organism_column", BLOCKER,
            "the SDRF has no characteristics[organism] column, so the organisms "
            "PRIDE registers cannot be checked"))
    if pride_organisms and org_ix:
        def norm(s: str) -> str:
            s = re.sub(r"NT=([^;]*).*", r"\1", s)
            s = re.sub(r"\(.*?\)", "", s)
            return re.sub(r"\s+", " ", s).strip().lower()

        declared = {norm(o) for o in pride_organisms} - {""}
        used = {norm(v) for v in _values(rows, org_ix)} - {"", "not available", "not applicable"}
        unrepresented = {d for d in declared if not any(d in u or u in d for u in used)}
        if unrepresented:
            report.findings.append(Finding(
                "organism_mismatch", BLOCKER,
                (f"PRIDE registers {len(declared)} organism(s) but "
                 f"{len(unrepresented)} never appear in the SDRF"),
                "missing: " + ", ".join(sorted(unrepresented))))

    # ---- replicate / fraction columns used as row counters ----------------
    for col in ("comment[technical replicate]", "comment[fraction identifier]",
                "characteristics[biological replicate]"):
        ix = _cols(header, col)
        if not ix or len(rows) < 3:
            continue
        vals = [r[ix[0]] for r in rows if ix[0] < len(r)]
        if len(set(vals)) == len(vals) and set(vals) == {str(i) for i in range(1, len(vals) + 1)}:
            report.findings.append(Finding(
                "counter_abuse", MAJOR,
                f"{col} runs 1..{len(vals)} with every row distinct — it is being used "
                f"as a row index, not a replicate/fraction number"))

    # ---- malformed CV terms ----------------------------------------------
    # Provenance columns legitimately use NT=<name>;VV=<version> and carry no
    # ontology accession. They are excluded BY NAME: exempting every value that
    # merely contains "VV=" would also excuse a real CV column written that way,
    # and an empty "AC=" is not an accession either.
    provenance = {"comment[sdrf template]", "comment[sdrf annotation tool]"}
    has_accession = re.compile(r"AC=\s*\S")
    malformed = set()
    for i, col in enumerate(header):
        if not col.startswith("comment[") or col in provenance:
            continue
        for r in rows:
            if i >= len(r):
                continue
            v = r[i]
            if v.startswith("NT=") and not has_accession.search(v):
                malformed.add(f"{col}={v}")
    if malformed:
        report.findings.append(Finding(
            "cv_term_no_accession", MAJOR,
            f"{len(malformed)} CV term(s) carry NT= with no AC= accession",
            "; ".join(sorted(malformed)[:2])))

    # ---- factor value ------------------------------------------------------
    if not any(c.startswith("factor value[") for c in header):
        report.findings.append(Finding(
            "no_factor_value", MAJOR,
            "the SDRF declares no factor value column"))

    # ---- convention drift --------------------------------------------------
    char_ntac = sorted({
        c for i, c in enumerate(header) if c.startswith("characteristics[")
        for r in rows if i < len(r) and ("NT=" in r[i] or "AC=" in r[i])
    })
    if char_ntac:
        report.findings.append(Finding(
            "characteristics_not_bare_label", MINOR,
            f"{len(char_ntac)} characteristics column(s) use NT=..;AC=.. instead of a bare label",
            ", ".join(char_ntac[:3])))

    if accession:
        src_ix = _cols(header, "source name")
        if src_ix:
            srcs = _values(rows, src_ix)
            expected = re.compile(rf"{re.escape(accession)}-Sample-\d+")
            if srcs and not all(expected.fullmatch(s.strip()) for s in srcs):
                report.findings.append(Finding(
                    "source_name_convention", MINOR,
                    "source name does not follow <ACCESSION>-Sample-<n>",
                    min(srcs)))

    return report

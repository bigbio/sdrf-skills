"""Unified CLI entry point for sdrf-skills tools.

Usage:
  python -m tools check <file.sdrf.tsv>          # hallucination check
  python -m tools structure <file.sdrf.tsv>       # structural invariants
  python -m tools score <file.sdrf.tsv>           # quality scoring
  python -m tools fix <file.sdrf.tsv> [-o out]    # auto-fix
  python -m tools benchmark <PXD1> <file2> ...    # benchmark suite
  python -m tools verify <ACCESSION> [--label L]   # verify single term
  python -m tools ols <query> [--ontology ONT]      # search OLS for a term
  python -m tools fetch <PXD> [--out evidence]      # PRIDE record, file list, paper -> evidence/
  python -m tools cellline lookup <name>           # curated cell line lookup
  python -m tools massive-files <PXD|MSV|task>     # MassIVE raw/acquisition file resolver
  python -m tools iprox-files <PXD|IPX>            # iProX raw file resolver
  python -m tools review-gate <command>             # independent-review receipt gate
  python -m tools schema-check <file.json>          # evidence manifest / review report vs. its JSON Schema
  python -m tools manifest-coverage <sdrf> <manifest> # columns with values but no evidence claim
  python -m tools audit-existing <file.sdrf.tsv>    # audit an already-annotated dataset
  python -m tools bruker-dia <url|path>             # DIA windows from Bruker analysis.tdf
  python -m tools search-params <path> [--json]     # extract search parameters from engine config
  python -m tools npx-to-sdrf <file.parquet>        # Olink NPX parquet → SDRF AP
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def cmd_check(args: argparse.Namespace) -> int:
    from tools.hallucination import detect_hallucinations
    report = detect_hallucinations(
        args.sdrf_file,
        verify_online=not args.offline,
        spec_path=args.spec,
    )
    print(report.summary())

    if report.unimod_swaps:
        print("\nUNIMOD Swaps:")
        for s in report.unimod_swaps:
            print(f"  Row(s) {s.rows}: {s.wrong_accession} -> {s.correct_accession} ({s.correct_name})")

    if report.hallucinated:
        print("\nHallucinated:")
        for h in report.hallucinated:
            print(f"  Row(s) {h.rows}: '{h.label}' in {h.column}")

    if report.mismatched:
        print("\nMismatched:")
        for m in report.mismatched:
            print(f"  Row(s) {m.rows}: expected '{m.expected_label}', got '{m.actual_label}'")

    return 0 if report.is_clean else 1


def cmd_structure(args: argparse.Namespace) -> int:
    from tools.structure import check_structure
    findings = check_structure(args.sdrf_file)
    if not findings:
        print("Structure OK: acquisition, template declaration and column order are consistent.")
        return 0
    print(f"{len(findings)} structural problem(s):")
    for finding in findings:
        print(f"  {finding}")
    return 1


def cmd_contract(args: argparse.Namespace) -> int:
    from tools.contract import render_json, render_text, template_contract
    try:
        c = template_contract(args.templates, args.terms)
    except ValueError as e:
        print(f"error: {e}")
        return 2
    print(render_json(c) if args.json else render_text(c))
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    from tools.build import BuildError, build
    try:
        return build(args.samples, args.technical, args.files, args.templates, args.output)
    except (BuildError, ValueError) as e:
        print(f"build refused: {e}")
        return 2


def cmd_doctor(args: argparse.Namespace) -> int:
    """Is everything the skills need installed? One line per dependency, exit 1 if the validator is missing."""
    import importlib.util
    import shutil

    from tools.column_ontology_map import resolve_terms_tsv
    rows = []
    ok = shutil.which("parse_sdrf") is not None
    rows.append((ok, "parse_sdrf (sdrf-pipelines)", "pip install 'sdrf-pipelines[ontology]'"))
    rows.append((importlib.util.find_spec("sdrf_pipelines") is not None, "sdrf_pipelines importable by this interpreter",
                 "install sdrf-pipelines into the interpreter that runs sdrf-tools"))
    rows.append((shutil.which("sdrf-tools") is not None, "sdrf-tools on PATH", "pip install -e <sdrf-skills checkout>"))
    rows.append((resolve_terms_tsv(args.terms) is not None, "spec TERMS.tsv", "git submodule update --init --recursive"))
    rows.append((shutil.which("techsdrf") is not None, "techsdrf (optional: raw-file verification)",
                 "pip install git+https://github.com/bigbio/techsdrf.git"))
    for good, what, fix in rows:
        print(f"  {'ok ' if good else 'MISSING'}  {what}" + ("" if good else f"  ->  {fix}"))
    return 0 if rows[0][0] else 1


def cmd_score(args: argparse.Namespace) -> int:
    from tools.completeness import score_sdrf
    report = score_sdrf(args.sdrf_file)
    print(report.summary())
    return 0


def cmd_fix(args: argparse.Namespace) -> int:
    from pathlib import Path

    from tools.sdrf_fixer import fix_sdrf
    fixed, report = fix_sdrf(args.sdrf_file)
    print(report.changelog())
    if args.output:
        Path(args.output).write_text(fixed)
        print(f"\nFixed SDRF written to: {args.output}")
    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    from tools.benchmark import BenchmarkSuite
    pxd = [s for s in args.sources if s.upper().startswith("PXD")]
    local = [s for s in args.sources if not s.upper().startswith("PXD")]
    suite = BenchmarkSuite(verify_online=args.online)
    report = suite.run(pxd_accessions=pxd, local_files=local)
    print(report.summary())
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    import requests
    try:
        return _verify(args)
    except requests.RequestException as e:
        print(f"OLS lookup failed: {e}", file=sys.stderr)
        return 2


def _verify(args: argparse.Namespace) -> int:
    from tools.ols_client import OLSClient
    client = OLSClient()
    if args.label:
        result = client.verify_accession(args.accession, args.label)
        print(f"Accession: {result.accession}")
        print(f"Exists: {result.exists}")
        print(f"Label match: {result.label_match}")
        if result.resolved_term:
            print(f"OLS label: {result.resolved_term.label}")
            print(f"Ontology: {result.resolved_term.ontology_name}")
        if result.message:
            print(f"Message: {result.message}")
        return 0 if result.exists and result.label_match else 1
    else:
        term = client.resolve_accession(args.accession)
        if term:
            print(f"Accession: {term.short_form}")
            print(f"Label: {term.label}")
            print(f"Ontology: {term.ontology_name}")
            print(f"Description: {term.description}")
            if term.synonyms:
                print(f"Synonyms: {', '.join(term.synonyms[:5])}")
        else:
            print(f"Accession {args.accession} not found in OLS")
            return 1
    return 0


def cmd_ols(args: argparse.Namespace) -> int:
    import requests

    from tools.ols_client import OLSClient
    ontology = ",".join(args.ontology) if args.ontology else None
    try:
        terms = OLSClient().search_term(args.query, ontology_id=ontology, exact=args.exact, rows=args.rows)
    except requests.RequestException as e:
        print(f"OLS search failed: {e}", file=sys.stderr)
        return 2
    if not terms:
        print(f"no OLS match for '{args.query}'" + (f" in {ontology}" if ontology else ""))
        return 1
    for t in terms:
        obsolete = "\tOBSOLETE" if t.is_obsolete else ""
        print(f"{t.short_form.replace('_', ':', 1)}\t{t.label}\t{t.ontology_name}{obsolete}")
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    from tools.fetch_record import run
    return run(args.accession, args.out, force=args.force)


def cmd_massive_files(args: argparse.Namespace) -> int:
    from tools.massive_raw_files import run_cli

    argv = [args.accession]
    if args.mode:
        argv.extend(["--mode", args.mode])
    if args.format:
        argv.extend(["--format", args.format])
    if args.ftp_url:
        argv.extend(["--ftp-url", args.ftp_url])
    if args.summary_only:
        argv.append("--summary-only")
    return run_cli(argv)


def cmd_schema_check(args: argparse.Namespace) -> int:
    import json

    from tools.json_schema import SCHEMAS, manifest_errors
    if args.print_schema:
        if args.file:
            print("error: --print-schema takes no file; run it on its own")
            return 2
        print(SCHEMAS[args.print_schema].read_text(encoding="utf-8"), end="")
        return 0
    if not args.file:
        print("error: give a JSON file to check, or --print-schema <name>")
        return 2
    try:
        document = json.loads(Path(args.file).read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"error: cannot read {args.file}: {e}")
        return 2
    schema = args.schema or (
        "review-report" if isinstance(document, dict) and "verdict" in document else "evidence-manifest"
    )
    if schema == "review-report":
        from tools.review_gate import ReviewGateError, report_schema_errors
        try:
            errors = report_schema_errors(document)
        except ReviewGateError as e:
            print(f"error: {e}")
            return 2
    else:
        errors = manifest_errors(document)
    if not errors:
        print(f"{args.file}: valid {schema}")
        return 0
    print(f"{args.file}: {len(errors)} problem(s) against the {schema} schema:")
    for error in errors:
        print(f"  - {error}")
    return 1


def cmd_iprox_files(args: argparse.Namespace) -> int:
    from tools.iprox_raw_files import run_cli

    argv = [args.accession]
    if args.mode:
        argv.extend(["--mode", args.mode])
    if args.format:
        argv.extend(["--format", args.format])
    if args.subproject:
        for sub in args.subproject:
            argv.extend(["--subproject", sub])
    if args.record:
        argv.extend(["--record", args.record])
    if args.px_xml:
        argv.extend(["--px-xml", args.px_xml])
    if args.timeout:
        argv.extend(["--timeout", str(args.timeout)])
    return run_cli(argv)


def cmd_cellline(args: argparse.Namespace) -> int:
    from pathlib import Path

    from tools.cellline_db import CellLineDatabase, annotate_sdrf_celllines

    if args.cellline_command == "lookup":
        db = CellLineDatabase()
        db.load(args.db)
        result = db.find(args.name)
        if result.entry:
            e = result.entry
            print(f"Cell line: {e.cell_line}")
            print(f"Match: {result.match_type} (confidence: {result.confidence:.2f})")
            print(f"Cellosaurus: {e.cellosaurus_name} ({e.cellosaurus_accession})")
            print(f"Organism: {e.organism}")
            print(f"Disease: {e.disease}")
            print(f"Tissue: {e.organism_part}")
            print(f"Cell type: {e.cell_type}")
            print(f"Age: {e.age}, Sex: {e.sex}")
            if e.synonyms:
                print(f"Synonyms: {'; '.join(e.synonyms[:10])}")
        else:
            print(f"'{args.name}' not found in database")
            return 1

    elif args.cellline_command == "annotate":
        enriched, report = annotate_sdrf_celllines(args.sdrf_file, db_path=args.db)
        print(report.summary())
        if args.output:
            Path(args.output).write_text(enriched)
            print(f"\nEnriched SDRF written to: {args.output}")

    elif args.cellline_command == "stats":
        db = CellLineDatabase()
        db.load(args.db)
        print(f"Cell Line Database: {db.size} entries, {len(db._index)} indexed names")

    return 0

def cmd_review_gate(args: argparse.Namespace) -> int:
    from tools.review_gate import run_cli

    return run_cli(args.review_gate_args)


def cmd_manifest_coverage(args: argparse.Namespace) -> int:
    import json

    from tools.manifest_coverage import check_coverage

    try:
        report = check_coverage(args.sdrf_file, args.manifest)
    except (OSError, ValueError) as e:
        print(f"error: {e}")
        return 2
    print(json.dumps(report.to_dict(), indent=2) if args.json else report.render())
    return 0 if report.is_covered else 1


def cmd_audit_existing(args: argparse.Namespace) -> int:
    """Audit an SDRF that already exists for a dataset, before re-annotating it."""
    import json
    from pathlib import Path

    from tools.existing_annotation import audit

    runs = None
    if args.runs:
        runs_text = Path(args.runs).read_text(encoding="utf-8-sig")
        if runs_text.lstrip().startswith("{"):
            # files.json from `sdrf-tools fetch`: the run names are under "files"
            runs = list(json.loads(runs_text)["files"])
        else:
            runs = [ln.strip() for ln in runs_text.splitlines() if ln.strip()]
    organisms = args.organism or None

    report = audit(
        Path(args.sdrf_file).read_text(encoding="utf-8-sig"),
        deposited_runs=runs,
        pride_organisms=organisms,
        accession=args.accession or "",
    )
    if args.json:
        print(json.dumps(report.to_dict(), indent=1))
        return 1 if report.blockers else 0
    print(report.render())
    print(f"\nsuggested action: {report.recommendation}")
    if not args.runs or not organisms:
        skipped = [n for n, v in (("--runs", args.runs), ("--organism", organisms)) if not v]
        print(f"note: {', '.join(skipped)} not supplied, so those checks were SKIPPED (not passed)")
    # Exit non-zero only for blockers, so this can gate a workflow without
    # blocking on convention drift.
    return 1 if report.blockers else 0


def cmd_curated(args: argparse.Namespace) -> int:
    """Summarise the community-curated SDRFs for accessions, as JSON."""
    import json

    from tools.existing_annotation import curated_files, fetch_curated, summarize

    try:
        found = curated_files(args.accessions)
        out = {acc: [{"file": p, **summarize(fetch_curated(p))} for p in paths]
               for acc, paths in found.items()}
    except Exception as e:  # noqa: BLE001 — any failure means "unknown", never "not curated"
        print(f"curated lookup failed: {e}", file=sys.stderr)
        return 2
    print(json.dumps(out, indent=1))
    return 0


def cmd_bruker_dia(args: argparse.Namespace) -> int:
    """Read DIA isolation windows out of a Bruker .d archive without downloading it."""
    import json

    from tools.bruker_tdf import (
        ZipRangeError,
        analyze,
        describe_isolation_window,
        render,
    )

    try:
        acq = analyze(args.source)
    except ZipRangeError as exc:
        print(f"error: {exc}")
        return 2
    if args.json:
        print(json.dumps({
            "source": acq.source,
            "instrument": acq.properties.get("InstrumentName"),
            "windows": [vars(w) for w in acq.windows],
            "isolation_window": describe_isolation_window(acq),
        }, indent=2))
    else:
        print(render(acq))
    return 0


def cmd_reconcile(args: argparse.Namespace) -> int:
    """Reconcile an SDRF's values against the archive record they came from."""
    import json
    from pathlib import Path

    from tools.record_reconcile import reconcile

    record = json.loads(Path(args.record).read_text(encoding="utf-8-sig"))
    # PRIDE's /projects/{acc} endpoint nests the fields under a "project" key; the search
    # endpoint returns them flat. Accept either.
    if "project" in record and isinstance(record["project"], dict):
        record = record["project"]

    text = Path(args.sdrf_file).read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    if not lines:
        print("empty SDRF")
        return 1
    header = [h.strip() for h in lines[0].split("\t")]
    rows = []
    for line in lines[1:]:
        if not line.strip():
            continue
        cells = line.split("\t")
        row: dict[str, str] = {}
        for name, value in zip(header, cells):
            # A repeated column (cleavage agent, modification parameters) must not be
            # collapsed to its last value the way csv.DictReader would.
            row[name] = value if name not in row else f"{row[name]}|{value}"
        rows.append(row)

    report = reconcile(record, rows, accession=args.accession or "")
    print(report.render())
    return 1 if report.blockers else 0


def cmd_search_params(args: argparse.Namespace) -> int:
    """Extract search parameters from a deposited search-engine config file."""
    import sqlite3

    from tools.search_params import extract, render_json, render_text

    try:
        params = extract(args.path)
    except (OSError, ValueError, SyntaxError, sqlite3.DatabaseError) as e:  # SyntaxError: XML ParseError
        print(f"error: {e}")
        return 2
    print(render_json(params) if args.json else render_text(params))
    return 0


def cmd_npx_to_sdrf(args: argparse.Namespace) -> int:
    from tools.NPXtoSDRF import run_cli

    argv = [args.npx_file]
    if args.output:
        argv.extend(["-o", args.output])
    for template in args.template or []:
        argv.extend(["--template", template])
    if args.organism:
        argv.extend(["--organism", args.organism])
    if args.organism_part:
        argv.extend(["--organism-part", args.organism_part])
    if args.disease:
        argv.extend(["--disease", args.disease])
    if args.sample_matrix:
        argv.extend(["--sample-matrix", args.sample_matrix])
    if args.age:
        argv.extend(["--age", args.age])
    if args.sex:
        argv.extend(["--sex", args.sex])
    if args.platform:
        argv.extend(["--platform", args.platform])
    if args.data_file:
        argv.extend(["--data-file", args.data_file])
    if args.sample_metadata:
        argv.extend(["--sample-metadata", args.sample_metadata])
    if args.templates_dir:
        argv.extend(["--templates-dir", str(args.templates_dir)])
    if args.inspect:
        argv.append("--inspect")
    if args.no_clinical:
        argv.append("--no-clinical")
    if args.quiet:
        argv.append("-q")
    return run_cli(argv)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m tools",
        description="SDRF annotation tools — hallucination detection, quality scoring, auto-fixing",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # check
    p = subparsers.add_parser("check", help="Check SDRF for ontology hallucinations")
    p.add_argument("sdrf_file")
    p.add_argument("--offline", action="store_true")
    p.add_argument("--spec", default=None)

    # structure
    p = subparsers.add_parser(
        "structure", help="Check SDRF structural invariants (acquisition, templates, column order)"
    )
    p.add_argument("sdrf_file")

    # contract
    p = subparsers.add_parser(
        "contract",
        help="Print the column contract (order, requirement, value form, reserved words) for a template union",
    )
    p.add_argument("-t", "--template", dest="templates", action="append", required=True,
                   help="Template name; repeat for a union (e.g. -t ms-proteomics -t human)")
    p.add_argument("--terms", default=None, help="Path to TERMS.tsv (default: bundled spec)")
    p.add_argument("--json", action="store_true", help="Machine-readable output")

    # build
    p = subparsers.add_parser(
        "build",
        help="Expand samples.tsv + technical.tsv into a structurally valid SDRF (never guesses a channel map)",
    )
    p.add_argument("--samples", required=True, help="One row per source: source name, files, label, characteristics...")
    p.add_argument("--technical", default=None, help="Two columns 'column','value'; '|' separates multiple values")
    p.add_argument("--files", required=True, help="files.json: the raw file names in scope")
    p.add_argument("-t", "--template", dest="templates", action="append", required=True)
    p.add_argument("-o", "--output", required=True)

    # doctor
    p = subparsers.add_parser("doctor", help="Check that parse_sdrf, sdrf-tools, the spec and techsdrf are available")
    p.add_argument("--terms", default=None, help="Path to TERMS.tsv (default: bundled spec)")

    # score
    p = subparsers.add_parser("score", help="Score SDRF quality (0-100)")
    p.add_argument("sdrf_file")

    # fix
    p = subparsers.add_parser("fix", help="Auto-fix common SDRF errors")
    p.add_argument("sdrf_file")
    p.add_argument("-o", "--output")

    # benchmark
    p = subparsers.add_parser("benchmark", help="Benchmark SDRF quality across datasets")
    p.add_argument("sources", nargs="+")
    p.add_argument("--online", action="store_true")

    # massive-files
    p = subparsers.add_parser(
        "massive-files",
        help="Resolve/list MassIVE raw or acquisition files for a PXD/MSV accession",
    )
    p.add_argument("accession", help="PXD accession, MassIVE MSV accession, or MassIVE task id")
    p.add_argument(
        "--mode",
        choices=("raw", "acquisition", "all"),
        default="raw",
    )
    p.add_argument(
        "--format",
        choices=("text", "tsv", "json"),
        default="text",
    )
    p.add_argument("--ftp-url")
    p.add_argument("--summary-only", action="store_true")

    # iprox-files
    p = subparsers.add_parser(
        "iprox-files",
        help="Resolve/list iProX raw or deposited files for an IPX project or PXD accession",
    )
    p.add_argument("accession", help="iProX project/subproject id (IPX##########) or PXD accession")
    p.add_argument(
        "--mode",
        choices=("raw", "all"),
        default="raw",
    )
    p.add_argument(
        "--format",
        choices=("text", "tsv", "json"),
        default="text",
    )
    p.add_argument("--subproject", action="append", default=None,
                   help="only emit files of this subproject id (repeatable)")
    p.add_argument("--record", default=None,
                   help="also write a reconcile-compatible record JSON to this path")
    p.add_argument("--px-xml", default=None,
                   help="PX XML to parse (path, URL, or 'auto' for the canonical location)")
    p.add_argument("--timeout", type=int, default=None)

    # verify
    p = subparsers.add_parser("verify", help="Verify a single ontology accession")
    p.add_argument("accession", help="e.g. UNIMOD:1, MS:1001911")
    p.add_argument("--label", help="Expected label to verify against")

    # ols
    p = subparsers.add_parser("ols", help="Search OLS for an ontology term (label -> accession)")
    p.add_argument("query", help="e.g. 'breast carcinoma', 'Q Exactive HF-X'")
    p.add_argument("--ontology", action="append", default=None,
                   help="Restrict to an ontology id (repeatable), e.g. --ontology mondo --ontology efo")
    p.add_argument("--exact", action="store_true", help="Exact label/synonym match only")
    p.add_argument("--rows", type=int, default=10)

    # fetch
    p = subparsers.add_parser(
        "fetch",
        help="Fetch a PRIDE project record, raw file list and linked paper into evidence/ "
             "(exit 2 = refused or a lookup failed; nothing was written)",
    )
    p.add_argument("accession", help="PXD accession")
    p.add_argument("--out", default="evidence", help="Output directory (default: evidence)")
    p.add_argument("--force", action="store_true", help="Replace an existing non-empty output directory")

    # cellline
    p = subparsers.add_parser("cellline", help="Cell line metadata lookup and annotation (curated subset)")
    cl_sub = p.add_subparsers(dest="cellline_command", required=True)
    cl_lookup = cl_sub.add_parser("lookup", help="Look up a cell line")
    cl_lookup.add_argument("name", help="Cell line name (e.g. HeLa, MCF-7)")
    cl_lookup.add_argument("--db", default=None)
    cl_annotate = cl_sub.add_parser("annotate", help="Annotate SDRF with cell line metadata")
    cl_annotate.add_argument("sdrf_file")
    cl_annotate.add_argument("-o", "--output")
    cl_annotate.add_argument("--db", default=None)
    cl_stats = cl_sub.add_parser("stats", help="Database statistics")
    cl_stats.add_argument("--db", default=None)

    # review-gate
    p = subparsers.add_parser(
        "review-gate",
        help="Track hash-bound independent review receipts for changed SDRFs",
        add_help=False,
    )
    p.add_argument("review_gate_args", nargs=argparse.REMAINDER)

    # schema-check
    p = subparsers.add_parser(
        "schema-check",
        help="Check an evidence manifest or a review report against its JSON Schema (tools/schemas/)",
    )
    p.add_argument("file", nargs="?", help="JSON file to check")
    p.add_argument("--schema", choices=["evidence-manifest", "review-report"], default=None,
                   help="Schema to check against (default: review-report if the file has a verdict)")
    p.add_argument("--print-schema", choices=["evidence-manifest", "review-report"], default=None,
                   help="Print this schema instead of checking a file")

    # manifest-coverage
    p = subparsers.add_parser(
        "manifest-coverage",
        help="List SDRF columns with non-reserved values that no evidence-manifest claim covers",
    )
    p.add_argument("sdrf_file")
    p.add_argument("manifest", help="Evidence manifest JSON (sdrf-adversarial-review contract)")
    p.add_argument("--json", action="store_true", help="Machine-readable output")

    # reconcile
    p = subparsers.add_parser(
        "reconcile",
        help="Check an SDRF's values against the deposit record's prose and run names",
    )
    p.add_argument("sdrf_file")
    p.add_argument("--record", required=True,
                   help="JSON project record from the archive (PRIDE /projects/{acc} or search)")
    p.add_argument("--accession", default=None)

    # audit-existing
    p = subparsers.add_parser(
        "audit-existing",
        help="Audit an SDRF that already exists for a dataset, before re-annotating",
    )
    p.add_argument("sdrf_file", help="the EXISTING SDRF (e.g. from the community repo)")
    p.add_argument("--accession", default=None, help="PXD accession, enables convention checks")
    p.add_argument("--runs", default=None,
                   help="file with one deposited run filename per line, or the files.json that "
                        "`sdrf-tools fetch` writes; omitted = coverage check skipped")
    p.add_argument("--organism", action="append", default=None,
                   help="organism registered in PRIDE (repeatable); omitted = organism check skipped")
    p.add_argument("--json", action="store_true",
                   help="print the report as JSON, with run coverage counts")

    # curated
    p = subparsers.add_parser(
        "curated",
        help="Summarise the SDRFs bigbio/sdrf-annotated-datasets holds for accessions "
             "(JSON; exit 2 = lookup failed, which is NOT 'not curated')",
    )
    p.add_argument("accessions", nargs="+", help="PXD / MSV accessions")

    # bruker-dia
    p = subparsers.add_parser(
        "bruker-dia",
        help="Read DIA isolation windows from a Bruker analysis.tdf (HTTP-range, no download)",
    )
    p.add_argument(
        "source",
        help="URL or path of a .d.zip archive, or a path to an extracted analysis.tdf",
    )
    p.add_argument("--json", action="store_true", help="machine-readable output")

    # search-params
    p = subparsers.add_parser(
        "search-params",
        help="Extract search parameters from a deposited search-engine config file",
    )
    p.add_argument("path", help="File path: mqpar.xml, parameters.txt, fragger.params, .msf, or DIA-NN log")
    p.add_argument("--json", action="store_true", help="Machine-readable output")

    # npx-to-sdrf
    p = subparsers.add_parser(
        "npx-to-sdrf",
        help="Convert Olink NPX parquet exports to SDRF affinity-proteomics format",
    )
    p.add_argument("npx_file", help="Path to Olink NPX parquet file")
    p.add_argument("-o", "--output", help="Output SDRF TSV path")
    p.add_argument(
        "--template",
        action="append",
        default=["human"],
        help="Organism/add-on template (repeatable; use 'none' for technology only)",
    )
    p.add_argument("--organism", default="not available")
    p.add_argument("--organism-part", default="not available")
    p.add_argument("--disease", default="not available")
    p.add_argument("--sample-matrix", default="not available")
    p.add_argument("--age", default="not available")
    p.add_argument("--sex", default="not available")
    p.add_argument("--platform", default=None)
    p.add_argument("--data-file", default=None)
    p.add_argument("--sample-metadata", default=None)
    p.add_argument("--templates-dir", default=None, type=Path)
    p.add_argument("--inspect", action="store_true")
    p.add_argument("--no-clinical", action="store_true")
    p.add_argument("-q", "--quiet", action="store_true")

    args = parser.parse_args()

    # Set default db path for cellline commands
    if args.command == "cellline" and hasattr(args, "db") and args.db is None:
        from tools.cellline_db import DEFAULT_DB_PATH
        args.db = str(DEFAULT_DB_PATH)

    commands = {
        "check": cmd_check,
        "structure": cmd_structure,
        "contract": cmd_contract,
        "build": cmd_build,
        "doctor": cmd_doctor,
        "score": cmd_score,
        "fix": cmd_fix,
        "benchmark": cmd_benchmark,
        "massive-files": cmd_massive_files,
        "iprox-files": cmd_iprox_files,
        "cellline": cmd_cellline,
        "verify": cmd_verify,
        "ols": cmd_ols,
        "fetch": cmd_fetch,
        "review-gate": cmd_review_gate,
        "schema-check": cmd_schema_check,
        "manifest-coverage": cmd_manifest_coverage,
        "audit-existing": cmd_audit_existing,
        "curated": cmd_curated,
        "bruker-dia": cmd_bruker_dia,
        "reconcile": cmd_reconcile,
        "search-params": cmd_search_params,
        "npx-to-sdrf": cmd_npx_to_sdrf,
    }

    sys.exit(commands[args.command](args))


if __name__ == "__main__":
    main()

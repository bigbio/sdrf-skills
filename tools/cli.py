"""Unified CLI entry point for sdrf-skills tools.

Usage:
  python -m tools check <file.sdrf.tsv>          # hallucination check
  python -m tools score <file.sdrf.tsv>           # quality scoring
  python -m tools fix <file.sdrf.tsv> [-o out]    # auto-fix
  python -m tools benchmark <PXD1> <file2> ...    # benchmark suite
  python -m tools verify <ACCESSION> [--label L]   # verify single term
  python -m tools cellline lookup <name>           # curated cell line lookup
  python -m tools massive-files <PXD|MSV|task>     # MassIVE raw/acquisition file resolver
"""

from __future__ import annotations

import argparse
import sys


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


def cmd_cellline(args: argparse.Namespace) -> int:
    from tools.cellline_db import CellLineDatabase, annotate_sdrf_celllines
    from pathlib import Path

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

    # verify
    p = subparsers.add_parser("verify", help="Verify a single ontology accession")
    p.add_argument("accession", help="e.g. UNIMOD:1, MS:1001911")
    p.add_argument("--label", help="Expected label to verify against")

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

    args = parser.parse_args()

    # Set default db path for cellline commands
    if args.command == "cellline" and hasattr(args, "db") and args.db is None:
        from tools.cellline_db import DEFAULT_DB_PATH
        args.db = str(DEFAULT_DB_PATH)

    commands = {
        "check": cmd_check,
        "score": cmd_score,
        "fix": cmd_fix,
        "benchmark": cmd_benchmark,
        "massive-files": cmd_massive_files,
        "cellline": cmd_cellline,
        "verify": cmd_verify,
    }

    sys.exit(commands[args.command](args))


if __name__ == "__main__":
    main()

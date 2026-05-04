"""Cell line metadata database and annotation enrichment.

Provides offline cell line lookup from the curated cl-annotations-db.tsv
database, plus fuzzy matching for unrecognized cell line names. Integrates
with the Cellosaurus REST API for live verification.

Ported from bigbio/sdrf-cellline-metadata-db (annotator.py + cl_db.py),
rewritten to use stdlib only (no pandas, spacy, or sklearn).
"""

from __future__ import annotations

import csv
import difflib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Database schema
# ---------------------------------------------------------------------------

DB_COLUMNS = [
    "cell line",
    "cellosaurus name",
    "cellosaurus accession",
    "bto cell line",
    "organism",
    "organism part",
    "sampling site",
    "age",
    "developmental stage",
    "sex",
    "ancestry category",
    "disease",
    "cell type",
    "Material type",
    "synonyms",
    "curated",
]

# Columns we enrich into an SDRF row
ENRICHMENT_COLUMNS = [
    "cellosaurus name",
    "cellosaurus accession",
    "bto cell line",
    "organism",
    "organism part",
    "sampling site",
    "age",
    "developmental stage",
    "sex",
    "ancestry category",
    "disease",
    "cell type",
]

# Default data directory
_DATA_DIR = Path(__file__).parent.parent / "data"
DEFAULT_DB_PATH = _DATA_DIR / "cl-annotations-db.tsv"
DEFAULT_SYNONYMS_PATH = _DATA_DIR / "ai-synonyms.tsv"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class CellLineEntry:
    """A single cell line record from the database."""
    cell_line: str
    cellosaurus_name: str = "not available"
    cellosaurus_accession: str = "not available"
    bto_cell_line: str = "not available"
    organism: str = "not available"
    organism_part: str = "not available"
    sampling_site: str = "not available"
    age: str = "not available"
    developmental_stage: str = "not available"
    sex: str = "not available"
    ancestry_category: str = "not available"
    disease: str = "not available"
    cell_type: str = "not available"
    material_type: str = "cell"
    synonyms: list[str] = field(default_factory=list)
    curated: str = "not curated"

    @classmethod
    def from_row(cls, row: dict[str, str]) -> CellLineEntry:
        """Create from a TSV row dict."""
        syns = row.get("synonyms", "")
        syn_list = [s.strip() for s in syns.split(";") if s.strip()] if syns else []
        return cls(
            cell_line=row.get("cell line", "").strip(),
            cellosaurus_name=row.get("cellosaurus name", "not available").strip(),
            cellosaurus_accession=row.get("cellosaurus accession", "not available").strip(),
            bto_cell_line=row.get("bto cell line", "not available").strip(),
            organism=row.get("organism", "not available").strip(),
            organism_part=row.get("organism part", "not available").strip(),
            sampling_site=row.get("sampling site", "not available").strip(),
            age=row.get("age", "not available").strip(),
            developmental_stage=row.get("developmental stage", "not available").strip(),
            sex=row.get("sex", "not available").strip(),
            ancestry_category=row.get("ancestry category", "not available").strip(),
            disease=row.get("disease", "not available").strip(),
            cell_type=row.get("cell type", "not available").strip(),
            material_type=row.get("Material type", "cell").strip(),
            synonyms=syn_list,
            curated=row.get("curated", "not curated").strip(),
        )

    def all_names(self) -> list[str]:
        """Return all known names for this cell line (for matching)."""
        names = [self.cell_line]
        if self.cellosaurus_name != "not available":
            names.append(self.cellosaurus_name)
        if self.cellosaurus_accession != "not available":
            names.append(self.cellosaurus_accession)
        names.extend(self.synonyms)
        return names

    def to_enrichment_dict(self) -> dict[str, str]:
        """Return metadata columns suitable for SDRF enrichment."""
        return {
            "cellosaurus name": self.cellosaurus_name,
            "cellosaurus accession": self.cellosaurus_accession,
            "bto cell line": self.bto_cell_line,
            "organism": self.organism,
            "organism part": self.organism_part,
            "sampling site": self.sampling_site,
            "age": self.age,
            "developmental stage": self.developmental_stage,
            "sex": self.sex,
            "ancestry category": self.ancestry_category,
            "disease": self.disease,
            "cell type": self.cell_type,
        }


@dataclass
class MatchResult:
    """Result of looking up a cell line."""
    query: str
    entry: CellLineEntry | None
    match_type: str = ""  # "exact", "synonym", "fuzzy", "api", "none"
    confidence: float = 0.0
    matched_name: str = ""


@dataclass
class AnnotationReport:
    """Report from annotating an SDRF with cell line metadata."""
    total_rows: int = 0
    matched: int = 0
    unmatched: int = 0
    match_details: list[MatchResult] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            "Cell Line Annotation Report",
            f"  Total rows: {self.total_rows}",
            f"  Matched: {self.matched}",
            f"  Unmatched: {self.unmatched}",
        ]
        if self.match_details:
            by_type: dict[str, int] = {}
            for m in self.match_details:
                by_type[m.match_type] = by_type.get(m.match_type, 0) + 1
            lines.append("  Match types:")
            for t, c in sorted(by_type.items()):
                lines.append(f"    {t}: {c}")

        unmatched = [m for m in self.match_details if m.match_type == "none"]
        if unmatched:
            lines.append(f"  Unmatched cell lines:")
            for m in unmatched[:10]:
                lines.append(f"    - {m.query}")
            if len(unmatched) > 10:
                lines.append(f"    ... and {len(unmatched) - 10} more")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Database loading
# ---------------------------------------------------------------------------

class CellLineDatabase:
    """In-memory cell line metadata database."""

    def __init__(self):
        self.entries: dict[str, CellLineEntry] = {}  # keyed by cell_line name
        self._index: dict[str, str] = {}  # normalized_name -> cell_line key
        self._synonyms: dict[str, str] = {}  # AI synonym -> canonical name

    def load(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
        synonyms_path: str | Path | None = DEFAULT_SYNONYMS_PATH,
        curated_only: bool = True,
    ) -> None:
        """Load the cell line database from TSV files."""
        db_path = Path(db_path)
        if not db_path.exists():
            raise FileNotFoundError(
                f"Cell line database not found: {db_path}\n"
                "Download from: https://github.com/bigbio/sdrf-cellline-metadata-db"
            )

        with db_path.open(encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter="\t")
            # Validate required columns
            required = {"cell line", "organism"}
            if reader.fieldnames and not required.issubset(set(reader.fieldnames)):
                missing = required - set(reader.fieldnames)
                raise ValueError(f"Cell line DB missing required columns: {missing}")
            for row in reader:
                if curated_only and row.get("curated", "").strip() != "curated":
                    continue
                entry = CellLineEntry.from_row(row)
                if entry.cell_line:
                    self.entries[entry.cell_line] = entry
                    # Build search index
                    for name in entry.all_names():
                        self._index[self._normalize(name)] = entry.cell_line

        # Load AI synonyms
        if synonyms_path:
            syn_path = Path(synonyms_path)
            if syn_path.exists():
                with syn_path.open(encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f, delimiter="\t")
                    for row in reader:
                        canonical = row.get("cell line", "").strip()
                        syns = row.get("synonyms", "")
                        if canonical and syns:
                            for syn in syns.split(";"):
                                syn = syn.strip()
                                if syn:
                                    self._synonyms[self._normalize(syn)] = canonical

    @staticmethod
    def _normalize(name: str) -> str:
        """Normalize a cell line name for matching."""
        return re.sub(r"[\s\-_]+", "", name.strip().lower())

    @property
    def size(self) -> int:
        return len(self.entries)

    # ------------------------------------------------------------------
    # Lookup methods
    # ------------------------------------------------------------------

    def find(self, query: str) -> MatchResult:
        """Look up a cell line by name, accession, or synonym.

        Tries in order: exact match, synonym match, AI synonym, fuzzy match.
        """
        if not query or query.lower() in ("not available", "not applicable"):
            return MatchResult(query=query, entry=None, match_type="none")

        norm = self._normalize(query)

        # 1. Exact match via index
        if norm in self._index:
            key = self._index[norm]
            return MatchResult(
                query=query,
                entry=self.entries[key],
                match_type="exact",
                confidence=1.0,
                matched_name=key,
            )

        # 2. AI synonym match
        if norm in self._synonyms:
            canonical = self._synonyms[norm]
            norm_canonical = self._normalize(canonical)
            if norm_canonical in self._index:
                key = self._index[norm_canonical]
                return MatchResult(
                    query=query,
                    entry=self.entries[key],
                    match_type="synonym",
                    confidence=0.95,
                    matched_name=key,
                )

        # 3. Substring match in synonyms (only if query is long enough)
        if len(norm) >= 4:
            for key, entry in self.entries.items():
                for syn in entry.synonyms:
                    norm_syn = self._normalize(syn)
                    # Only match if the query contains the full synonym or vice versa
                    # and the shorter string is at least 4 chars
                    if len(norm_syn) >= 4 and (norm == norm_syn or norm.startswith(norm_syn) or norm_syn.startswith(norm)):
                        return MatchResult(
                            query=query,
                            entry=entry,
                            match_type="synonym",
                            confidence=0.9,
                            matched_name=key,
                        )

        # 4. Fuzzy match using difflib
        all_names = list(self._index.keys())
        close = difflib.get_close_matches(norm, all_names, n=1, cutoff=0.8)
        if close:
            key = self._index[close[0]]
            ratio = difflib.SequenceMatcher(None, norm, close[0]).ratio()
            return MatchResult(
                query=query,
                entry=self.entries[key],
                match_type="fuzzy",
                confidence=ratio,
                matched_name=key,
            )

        return MatchResult(query=query, entry=None, match_type="none")

    def find_all(self, queries: list[str]) -> list[MatchResult]:
        """Look up multiple cell lines. Caches results for repeated queries."""
        cache: dict[str, MatchResult] = {}
        results = []
        for q in queries:
            norm = self._normalize(q)
            if norm not in cache:
                cache[norm] = self.find(q)
            cached = cache[norm]
            # Preserve the original query text for each result
            results.append(MatchResult(
                query=q,
                entry=cached.entry,
                match_type=cached.match_type,
                confidence=cached.confidence,
                matched_name=cached.matched_name,
            ))
        return results


# ---------------------------------------------------------------------------
# SDRF annotation enrichment
# ---------------------------------------------------------------------------

def annotate_sdrf_celllines(
    sdrf_source: str | Path,
    db_path: str | Path = DEFAULT_DB_PATH,
    synonyms_path: str | Path | None = DEFAULT_SYNONYMS_PATH,
) -> tuple[str, AnnotationReport]:
    """Annotate an SDRF file with cell line metadata from the database.

    For each row with a characteristics[cell line] value, looks up the cell
    line in the database and produces an enriched output TSV with suggested
    metadata columns.

    Args:
        sdrf_source: Path to SDRF file or raw TSV content.
        db_path: Path to cl-annotations-db.tsv.
        synonyms_path: Path to ai-synonyms.tsv.

    Returns:
        Tuple of (enriched TSV content, AnnotationReport).
    """
    import io
    from tools.sdrf_parser import parse_sdrf

    sdrf = parse_sdrf(sdrf_source)
    report = AnnotationReport(total_rows=sdrf.n_rows)

    # Find the cell line column
    cl_col_key = None
    for i, col in enumerate(sdrf.columns):
        if col.col_type == "characteristics" and col.inner_name.lower() == "cell line":
            cl_col_key = sdrf.key_for_column(i)
            break

    if cl_col_key is None:
        report.unmatched = report.total_rows
        # No cell line column — return original content unchanged
        if isinstance(sdrf_source, Path) or (isinstance(sdrf_source, str) and Path(sdrf_source).is_file()):
            return Path(sdrf_source).read_text(encoding="utf-8-sig"), report
        return str(sdrf_source), report

    # Load database
    db = CellLineDatabase()
    db.load(db_path, synonyms_path)

    # Build output
    output = io.StringIO()
    writer = csv.writer(output, delimiter="\t", lineterminator="\n")

    # Header: original columns + enrichment columns
    enrichment_headers = [f"suggested[{col}]" for col in ENRICHMENT_COLUMNS]
    enrichment_headers.append("match_type")
    enrichment_headers.append("match_confidence")

    original_headers = [col.raw_name for col in sdrf.columns]
    writer.writerow(original_headers + enrichment_headers)

    # Process each row
    for row in sdrf.rows:
        cl_name = row.get(cl_col_key, "").strip()
        match = db.find(cl_name)
        report.match_details.append(match)

        if match.entry:
            report.matched += 1
            enrichment = match.entry.to_enrichment_dict()
        else:
            report.unmatched += 1
            enrichment = {col: "not available" for col in ENRICHMENT_COLUMNS}

        # Write original values
        row_values = [row.get(sdrf.key_for_column(i), "") for i in range(len(sdrf.columns))]
        # Add enrichment values
        row_values.extend([enrichment.get(col, "not available") for col in ENRICHMENT_COLUMNS])
        row_values.append(match.match_type)
        row_values.append(f"{match.confidence:.2f}")

        writer.writerow(row_values)

    return output.getvalue(), report


# ---------------------------------------------------------------------------
# Developmental stage estimation (from upstream)
# ---------------------------------------------------------------------------

def estimate_developmental_stage(age_string: str) -> str:
    """Estimate developmental stage from age string (e.g. '58Y' -> 'Adult')."""
    age_str = age_string.replace("Y", "").replace("y", "")
    if age_str.isdigit():
        age = int(age_str)
        if 0 <= age <= 2:
            return "Infant"
        elif 3 <= age < 12:
            return "Children"
        elif 12 <= age < 18:
            return "Juvenile"
        elif 18 <= age < 65:
            return "Adult"
        elif age >= 65:
            return "Elderly"
    return "not available"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """CLI entry point for cell line database tools."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Cell line metadata lookup and SDRF annotation enrichment"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # lookup
    p = sub.add_parser("lookup", help="Look up a cell line in the database")
    p.add_argument("name", help="Cell line name (e.g. HeLa, MCF-7, CVCL_0030)")
    p.add_argument("--db", default=str(DEFAULT_DB_PATH))

    # annotate
    p = sub.add_parser("annotate", help="Annotate SDRF with cell line metadata")
    p.add_argument("sdrf_file", help="Path to .sdrf.tsv file")
    p.add_argument("-o", "--output", help="Output path for enriched TSV")
    p.add_argument("--db", default=str(DEFAULT_DB_PATH))

    # stats
    p = sub.add_parser("stats", help="Show database statistics")
    p.add_argument("--db", default=str(DEFAULT_DB_PATH))

    args = parser.parse_args(argv)

    if args.command == "lookup":
        db = CellLineDatabase()
        db.load(args.db)
        result = db.find(args.name)
        if result.entry:
            print(f"Cell line: {result.entry.cell_line}")
            print(f"Match type: {result.match_type} (confidence: {result.confidence:.2f})")
            print(f"Cellosaurus: {result.entry.cellosaurus_name} ({result.entry.cellosaurus_accession})")
            print(f"Organism: {result.entry.organism}")
            print(f"Disease: {result.entry.disease}")
            print(f"Tissue: {result.entry.organism_part}")
            print(f"Cell type: {result.entry.cell_type}")
            print(f"Age: {result.entry.age}")
            print(f"Sex: {result.entry.sex}")
            print(f"Synonyms: {'; '.join(result.entry.synonyms[:10])}")
        else:
            print(f"Cell line '{args.name}' not found in database")
            return 1

    elif args.command == "annotate":
        enriched, report = annotate_sdrf_celllines(args.sdrf_file, db_path=args.db)
        print(report.summary())
        if args.output:
            Path(args.output).write_text(enriched)
            print(f"\nEnriched SDRF written to: {args.output}")

    elif args.command == "stats":
        db = CellLineDatabase()
        db.load(args.db)
        organisms: dict[str, int] = {}
        diseases: dict[str, int] = {}
        for entry in db.entries.values():
            org = entry.organism
            organisms[org] = organisms.get(org, 0) + 1
            dis = entry.disease
            diseases[dis] = diseases.get(dis, 0) + 1

        print("Cell Line Database Statistics")
        print(f"  Total entries: {db.size}")
        print(f"  Index size: {len(db._index)} names")
        print(f"  AI synonyms: {len(db._synonyms)}")
        print("\n  Top organisms:")
        for org, count in sorted(organisms.items(), key=lambda x: -x[1])[:5]:
            print(f"    {org}: {count}")
        print("\n  Top diseases:")
        for dis, count in sorted(diseases.items(), key=lambda x: -x[1])[:5]:
            print(f"    {dis}: {count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Mapping from SDRF column names to expected ontology sources.

Derived from TERMS.tsv `values` field and the sdrf-knowledge SKILL.md (formerly sdrf-terms).
Used as a fallback when the spec submodule is not initialized.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# Maps characteristics/comment inner names -> list of valid ontology prefixes.
# Order matters: first is preferred.
COLUMN_ONTOLOGY_MAP: dict[str, list[str]] = {
    # Biological characteristics
    "organism": ["NCBITaxon"],
    "disease": ["MONDO", "EFO", "DOID", "PATO"],
    "organism part": ["UBERON", "BTO"],
    "cell type": ["CL", "BTO"],
    "cell line": ["CLO", "BTO", "EFO"],
    "developmental stage": ["UBERON", "HsapDv"],
    "ancestry category": ["HANCESTRO"],
    "sex": [],  # controlled vocabulary, not ontology
    "age": [],  # free format (e.g. 58Y)

    # Technical metadata (comment columns)
    "instrument": ["MS"],
    "modification parameters": ["UNIMOD"],
    "cleavage agent details": ["MS"],
    "label": ["MS"],
    "dissociation method": ["MS"],
    "precursor mass tolerance": [],
    "fragment mass tolerance": [],
}

# Known UNIMOD accession -> name mappings for swap detection.
# Every entry was verified against the UNIMOD ontology (OLS4, cross-checked
# against the unimod release shipped with sdrf-pipelines) on 2026-09-21. A wrong
# entry here is invisible by construction: `python -m tools check` would endorse
# the exact mismatch it exists to catch. Re-verify against OLS before adding a
# row -- never copy an accession from memory.
UNIMOD_KNOWN: dict[str, str] = {
    "UNIMOD:1": "Acetyl",
    "UNIMOD:4": "Carbamidomethyl",
    "UNIMOD:5": "Carbamyl",
    "UNIMOD:7": "Deamidated",
    "UNIMOD:21": "Phospho",
    "UNIMOD:24": "Propionamide",
    "UNIMOD:30": "Cation:Na",
    "UNIMOD:34": "Methyl",
    "UNIMOD:35": "Oxidation",
    "UNIMOD:36": "Dimethyl",
    "UNIMOD:37": "Trimethyl",
    "UNIMOD:122": "Formyl",
    "UNIMOD:188": "Label:13C(6)",
    "UNIMOD:199": "Dimethyl:2H(4)",
    "UNIMOD:214": "iTRAQ4plex",
    "UNIMOD:259": "Label:13C(6)15N(2)",
    "UNIMOD:267": "Label:13C(6)15N(4)",
    "UNIMOD:268": "Label:13C(5)15N(1)",
    "UNIMOD:312": "Cysteinyl",
    "UNIMOD:354": "Nitro",
    "UNIMOD:374": "Dehydro",
    "UNIMOD:481": "Label:2H(4)",
    "UNIMOD:730": "iTRAQ8plex",
    "UNIMOD:737": "TMT6plex",
    "UNIMOD:738": "TMT2plex",
    "UNIMOD:2016": "TMTpro",
}

# Reverse lookup: lowercased UNIMOD name -> accession. Labels in UNIMOD_KNOWN
# are unique, so this is well defined (guarded by tests/test_hallucination.py).
# Used to decide which half of a mismatched NT=/AC= pair is the typo: if the
# name is itself a known UNIMOD label, the accession is what is wrong.
UNIMOD_BY_NAME: dict[str, str] = {name.lower(): acc for acc, name in UNIMOD_KNOWN.items()}

# Common UNIMOD swap pairs (wrong -> correct)
UNIMOD_SWAPS: dict[tuple[str, str], tuple[str, str]] = {
    # (wrong_accession, wrong_name) -> (correct_accession, correct_name)
    ("UNIMOD:21", "Acetyl"): ("UNIMOD:1", "Acetyl"),
    ("UNIMOD:1", "Phospho"): ("UNIMOD:21", "Phospho"),
    ("UNIMOD:34", "Oxidation"): ("UNIMOD:35", "Oxidation"),
    ("UNIMOD:35", "Methyl"): ("UNIMOD:34", "Methyl"),
}

# Reserved words in SDRF
RESERVED_WORDS = {
    "not available",
    "not applicable",
}

# Common wrong reserved words -> correct.
# All ambiguous tokens map to "not available" since the intent is usually
# "information not captured". Users who mean "not applicable" should write
# the full phrase.
WRONG_RESERVED: dict[str, str] = {
    "n/a": "not available",
    "na": "not available",
    "N/A": "not available",
    "NA": "not available",
    "unknown": "not available",
    "null": "not available",
    "none": "not available",
    "None": "not available",
    "-": "not available",
}


def get_ontologies_for_column(inner_name: str) -> list[str]:
    """Return expected ontology prefixes for a column name."""
    return COLUMN_ONTOLOGY_MAP.get(inner_name.lower(), [])


def try_load_terms_tsv(spec_path: str | Path = "spec/sdrf-proteomics/TERMS.tsv") -> dict[str, list[str]] | None:
    """Try to load column-ontology mappings from TERMS.tsv.

    Handles both the current spec header (``term``) and legacy (``name``).

    Returns a dict mapping column inner name -> list of ontology prefixes,
    or None if the file is not available.
    """
    path = Path(spec_path)
    if not path.exists():
        return None

    import csv
    result: dict[str, list[str]] = {}
    with path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            # Support both "term" (current spec) and "name" (legacy)
            name = (row.get("term") or row.get("name") or "").strip()
            values = (row.get("values") or row.get("ontology") or "").strip()
            if name and values:
                ontologies = [v.strip() for v in values.split(",") if v.strip()]
                result[name.lower()] = ontologies
    return result

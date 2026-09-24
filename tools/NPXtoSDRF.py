"""Convert Olink NPX parquet exports to SDRF affinity-proteomics format.

Reads long-format NPX data (one row per sample × assay) and emits one SDRF row
per unique sample, using the affinity-proteomics template (optionally combined
with an organism template such as ``human``).

Large Explore HT exports (millions of assay rows) are handled via batched parquet
reads — only sample-level columns are loaded, not full protein matrices.

Usage:
  python tools/NPXtoSDRF.py data.parquet -o PXD000000.sdrf.tsv
  python -m tools npx-to-sdrf data.parquet -o out.sdrf.tsv --template human
  python tools/NPXtoSDRF.py data.parquet --inspect

NPX columns consumed when present (case/spacing insensitive):
  SampleID, SampleType/Sample Type, Panel, PlateID, WellID, Normalization,
  Panel_Lot_Nr, InstrumentType, ExploreVersion

Embedded clinical columns (common in Olink Explore HT + LIMS exports) are mapped
when ``--map-clinical`` is enabled (default):
  Gender → characteristics[sex]
  Patient.Age.At.Collection → characteristics[age]
  Primary.Diagnosis → characteristics[disease]
  Patient → characteristics[individual]
  Race → characteristics[ancestry category]

Sample-level metadata can also be supplied with ``--sample-metadata`` (TSV keyed
by SampleID) or global defaults via ``--organism``, ``--sample-matrix``, etc.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = REPO_ROOT / "spec" / "sdrf-proteomics" / "sdrf-templates"

TECHNOLOGY_TYPE = "protein expression profiling by antibody array"
QUANTIFICATION_UNIT = "NPX"
SDRF_VERSION = "v1.1.0"
ANNOTATION_TOOL = "NT=NPXtoSDRF;VV=v0.2.0"
DEFAULT_BATCH_SIZE = 131_072

# Olink NPX / NPX Map sample-type strings → SDRF characteristics[sample type] labels.
SAMPLE_TYPE_MAP: dict[str, str] = {
    "SAMPLE": "study sample",
    "STUDY SAMPLE": "study sample",
    "PLATE_CONTROL": "plate control",
    "PLATE CONTROL": "plate control",
    "NEGATIVE_CONTROL": "negative control",
    "NEGATIVE CONTROL": "negative control",
    "CONTROL": "quality control sample",
    "SAMPLE_CONTROL": "quality control sample",
    "POSITIVE_CONTROL": "positive control",
    "POSITIVE CONTROL": "positive control",
    "CALIBRATOR": "calibrator",
    "REFERENCE": "reference",
    "BRIDGE": "bridge",
}

# Common matrix shorthand → UBERON/BTO labels for characteristics[sample matrix].
SAMPLE_MATRIX_MAP: dict[str, str] = {
    "plasma": "blood plasma",
    "blood plasma": "blood plasma",
    "serum": "serum",
    "csf": "cerebrospinal fluid",
    "cerebrospinal fluid": "cerebrospinal fluid",
    "urine": "urine",
    "saliva": "saliva",
}

# Substrings in Panel names → comment[platform] when --platform is not set.
PANEL_PLATFORM_HINTS: tuple[tuple[str, str], ...] = (
    ("explore ht", "Olink Explore HT"),
    ("explore_ht", "Olink Explore HT"),
    ("explore 384", "Olink Explore 384"),
    ("explore 1536", "Olink Explore HT"),
    ("explore", "Olink Explore HT"),
    ("target 48", "Olink Target 48"),
    ("target 96", "Olink Target 96"),
    ("reveal", "Olink Reveal"),
    ("focus", "Olink Focus"),
)

# Canonical NPX column aliases after normalisation.
COLUMN_ALIASES: dict[str, str] = {
    "sampleid": "SampleID",
    "sampletype": "Sample Type",
    "panel": "Panel",
    "plateid": "PlateID",
    "wellid": "WellID",
    "normalization": "Normalization",
    "panel_lot_nr": "Panel_Lot_Nr",
    "panellotnr": "Panel_Lot_Nr",
    "npx": "NPX",
    "olinkid": "OlinkID",
    "instrumenttype": "InstrumentType",
    "exploreversion": "ExploreVersion",
    "gender": "Gender",
    "patient.age.at.collection": "Patient.Age.At.Collection",
    "primary.diagnosis": "Primary.Diagnosis",
    "patient": "Patient",
    "race": "Race",
    "samplegroup": "SampleGroup",
}

# Parquet column names to read, grouped by canonical field.
PARQUET_FIELD_CANDIDATES: dict[str, tuple[str, ...]] = {
    "SampleID": ("SampleID", "Sample ID", "sample_id"),
    "Sample Type": ("SampleType", "Sample Type", "sample_type"),
    "Panel": ("Panel", "panel"),
    "PlateID": ("PlateID", "Plate ID", "plate_id"),
    "WellID": ("WellID", "Well ID", "well_id"),
    "Normalization": ("Normalization", "normalization"),
    "Panel_Lot_Nr": ("Panel_Lot_Nr", "Panel Lot Nr", "PanelLotNr"),
    "InstrumentType": ("InstrumentType", "Instrument Type", "instrument_type"),
    "ExploreVersion": ("ExploreVersion", "Explore Version"),
    "Gender": ("Gender", "gender", "Sex", "sex"),
    "Patient.Age.At.Collection": (
        "Patient.Age.At.Collection",
        "Patient Age At Collection",
        "Age",
        "age",
    ),
    "Primary.Diagnosis": ("Primary.Diagnosis", "Primary Diagnosis", "Diagnosis"),
    "Patient": ("Patient", "patient", "Individual", "individual"),
    "Race": ("Race", "race", "Ancestry", "ancestry"),
    "SampleGroup": ("SampleGroup", "Sample Group", "sample_group"),
    "OlinkID": ("OlinkID", "Olink ID", "olink_id"),
}


@dataclass
class NpxSample:
    """Aggregated metadata for one Olink sample."""

    sample_id: str
    sample_type: str | None = None
    panel: str | None = None
    plate_id: str | None = None
    well_id: str | None = None
    normalization: str | None = None
    lot_number: str | None = None
    instrument_type: str | None = None
    explore_version: str | None = None
    clinical: dict[str, str] = field(default_factory=dict)
    assay_count: int = 0


@dataclass
class NpxInspectReport:
    """Schema summary for an NPX parquet file."""

    path: str
    n_rows: int
    parquet_columns: list[str] = field(default_factory=list)
    mapped_columns: dict[str, str] = field(default_factory=dict)
    n_samples: int = 0
    sample_types: list[str] = field(default_factory=list)
    panels: list[str] = field(default_factory=list)
    plates: list[str] = field(default_factory=list)
    normalizations: list[str] = field(default_factory=list)
    clinical_columns: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"NPX file: {self.path}",
            f"Rows: {self.n_rows:,}",
            f"Columns ({len(self.parquet_columns)}): {', '.join(self.parquet_columns)}",
        ]
        if self.mapped_columns:
            lines.append("Mapped fields:")
            for canonical, actual in sorted(self.mapped_columns.items()):
                lines.append(f"  {canonical} ← {actual}")
        if self.n_samples:
            lines.append(f"Unique samples: {self.n_samples}")
        if self.sample_types:
            lines.append(f"Sample types: {', '.join(self.sample_types)}")
        if self.panels:
            lines.append(f"Panels: {', '.join(self.panels)}")
        if self.plates:
            lines.append(f"Plates: {', '.join(self.plates)}")
        if self.normalizations:
            lines.append(f"Normalization: {', '.join(self.normalizations)}")
        if self.clinical_columns:
            lines.append(f"Clinical columns detected: {', '.join(self.clinical_columns)}")
        return "\n".join(lines)


@dataclass
class ConversionDefaults:
    """Global defaults applied when sample metadata does not override."""

    organism: str = "not available"
    organism_part: str = "not available"
    disease: str = "not available"
    sample_matrix: str = "not available"
    age: str = "not available"
    sex: str = "not available"
    platform: str | None = None
    data_file: str | None = None


@dataclass
class ConversionReport:
    """Summary of an NPX → SDRF conversion."""

    npx_path: str
    n_samples: int = 0
    n_assay_rows: int = 0
    panels: list[str] = field(default_factory=list)
    plates: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    templates: list[str] = field(default_factory=list)
    output_columns: list[str] = field(default_factory=list)
    clinical_mapped: int = 0

    def summary(self) -> str:
        lines = [
            f"NPX file: {self.npx_path}",
            f"Assay rows read: {self.n_assay_rows:,}",
            f"SDRF sample rows: {self.n_samples}",
            f"Templates: {', '.join(self.templates) or 'affinity-proteomics'}",
            f"Columns: {len(self.output_columns)}",
        ]
        if self.clinical_mapped:
            lines.append(f"Samples with auto-mapped clinical metadata: {self.clinical_mapped}")
        if self.panels:
            lines.append(f"Panels: {', '.join(self.panels)}")
        if self.plates:
            lines.append(f"Plates: {', '.join(self.plates)}")
        if self.warnings:
            lines.append("Warnings:")
            lines.extend(f"  - {w}" for w in self.warnings)
        return "\n".join(lines)


def _normalize_column_name(name: str) -> str:
    key = re.sub(r"[\s_]+", "", name.strip().lower())
    if key in COLUMN_ALIASES:
        return COLUMN_ALIASES[key]
    # Preserve dotted clinical names such as Patient.Age.At.Collection.
    if "." in name:
        return name.strip()
    return name.strip()


def _normalize_key(name: str) -> str:
    return re.sub(r"[\s_]+", "", name.strip().lower())


def _resolve_parquet_columns(schema_names: Sequence[str]) -> dict[str, str]:
    """Map canonical NPX field names to actual parquet column names."""
    by_key = {_normalize_key(name): name for name in schema_names}
    resolved: dict[str, str] = {}
    for canonical, candidates in PARQUET_FIELD_CANDIDATES.items():
        for candidate in candidates:
            actual = by_key.get(_normalize_key(candidate))
            if actual is not None:
                resolved[canonical] = actual
                break
    return resolved


def _readable_columns(resolved: Mapping[str, str]) -> list[str]:
    cols = list(dict.fromkeys(resolved.values()))
    if "SampleID" not in resolved:
        raise ValueError(
            "NPX file is missing a SampleID column. "
            f"Columns found: {', '.join(sorted(set(resolved.values())))}"
        )
    return cols


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _first_present(row: Mapping[str, Any], *keys: str) -> Any | None:
    for key in keys:
        if key in row:
            value = row[key]
            if value is not None and str(value).strip() != "":
                return value
    return None


def _normalize_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalised: list[dict[str, Any]] = []
    for row in rows:
        mapped: dict[str, Any] = {}
        for raw_key, value in row.items():
            mapped[_normalize_column_name(str(raw_key))] = value
        normalised.append(mapped)
    return normalised


def _parquet_file(path: str | Path):
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover - environment specific
        raise ImportError(
            "pyarrow is required to read NPX parquet files. "
            "Install with: pip install pyarrow"
        ) from exc
    return pq.ParquetFile(str(path))


def inspect_npx_parquet(path: str | Path) -> NpxInspectReport:
    """Summarise an NPX parquet schema without loading all assay rows."""
    fp = Path(path)
    pf = _parquet_file(fp)
    schema_names = pf.schema.names
    resolved = _resolve_parquet_columns(schema_names)
    read_cols = _readable_columns(resolved)

    samples, n_rows = _aggregate_batches(
        pf,
        read_cols,
        resolved,
        batch_size=DEFAULT_BATCH_SIZE,
    )

    clinical_cols = [
        canonical
        for canonical in (
            "Gender",
            "Patient.Age.At.Collection",
            "Primary.Diagnosis",
            "Patient",
            "Race",
            "SampleGroup",
        )
        if canonical in resolved
    ]

    return NpxInspectReport(
        path=str(fp),
        n_rows=n_rows,
        parquet_columns=list(schema_names),
        mapped_columns=resolved,
        n_samples=len(samples),
        sample_types=sorted({s.sample_type for s in samples if s.sample_type}),
        panels=sorted({s.panel for s in samples if s.panel}),
        plates=sorted({s.plate_id for s in samples if s.plate_id}),
        normalizations=sorted({s.normalization for s in samples if s.normalization}),
        clinical_columns=clinical_cols,
    )


def _value_from_batch(batch_dict: dict[str, list[Any]], actual_col: str, index: int) -> Any:
    return batch_dict[actual_col][index]


def _aggregate_batches(
    pf: Any,
    read_cols: Sequence[str],
    resolved: Mapping[str, str],
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> tuple[list[NpxSample], int]:
    """Scan parquet in batches and aggregate to one NpxSample per SampleID."""
    sample_id_col = resolved["SampleID"]
    by_id: dict[str, NpxSample] = {}
    n_rows = 0

    clinical_fields = [
        key
        for key in (
            "Gender",
            "Patient.Age.At.Collection",
            "Primary.Diagnosis",
            "Patient",
            "Race",
            "SampleGroup",
        )
        if key in resolved
    ]

    for batch in pf.iter_batches(batch_size=batch_size, columns=list(read_cols)):
        batch_dict = batch.to_pydict()
        sample_ids = batch_dict[sample_id_col]
        batch_len = len(sample_ids)
        n_rows += batch_len

        for idx in range(batch_len):
            sample_id = _clean_text(sample_ids[idx])
            if not sample_id:
                continue

            sample = by_id.get(sample_id)
            if sample is None:
                sample = NpxSample(sample_id=sample_id)
                by_id[sample_id] = sample

                for field, canonical in (
                    ("Sample Type", "sample_type"),
                    ("Panel", "panel"),
                    ("PlateID", "plate_id"),
                    ("WellID", "well_id"),
                    ("Normalization", "normalization"),
                    ("Panel_Lot_Nr", "lot_number"),
                    ("InstrumentType", "instrument_type"),
                    ("ExploreVersion", "explore_version"),
                ):
                    if canonical_field := resolved.get(field):
                        value = _clean_text(
                            _value_from_batch(batch_dict, canonical_field, idx),
                        )
                        if value is not None:
                            setattr(sample, canonical, value)

                for clinical in clinical_fields:
                    actual = resolved[clinical]
                    value = _clean_text(_value_from_batch(batch_dict, actual, idx))
                    if value is not None:
                        sample.clinical[clinical] = value

            sample.assay_count += 1

    return [by_id[key] for key in sorted(by_id)], n_rows


def read_npx_parquet(path: str | Path) -> list[dict[str, Any]]:
    """Read an Olink NPX parquet file into normalised row dicts (small files/tests)."""
    import pyarrow.parquet as pq

    table = pq.read_table(str(path))
    rows = table.to_pylist()
    return _normalize_rows(rows)


def aggregate_samples(rows: Sequence[Mapping[str, Any]]) -> list[NpxSample]:
    """Collapse long-format NPX rows to one record per SampleID (in-memory path)."""
    by_id: dict[str, NpxSample] = {}

    for raw_row in rows:
        row = {
            _normalize_column_name(str(key)): value
            for key, value in raw_row.items()
        }
        sample_id_raw = _first_present(row, "SampleID")
        if sample_id_raw is None:
            continue
        sample_id = str(sample_id_raw).strip()
        if not sample_id:
            continue

        sample = by_id.get(sample_id)
        if sample is None:
            sample = NpxSample(sample_id=sample_id)
            by_id[sample_id] = sample

        sample.assay_count += 1

        sample_type = _first_present(row, "Sample Type")
        if sample_type is not None and sample.sample_type is None:
            sample.sample_type = str(sample_type).strip()

        panel = _first_present(row, "Panel")
        if panel is not None and sample.panel is None:
            sample.panel = str(panel).strip()

        plate_id = _first_present(row, "PlateID")
        if plate_id is not None and sample.plate_id is None:
            sample.plate_id = str(plate_id).strip()

        well_id = _first_present(row, "WellID")
        if well_id is not None and sample.well_id is None:
            sample.well_id = str(well_id).strip()

        normalization = _first_present(row, "Normalization")
        if normalization is not None and sample.normalization is None:
            sample.normalization = str(normalization).strip()

        lot_number = _first_present(row, "Panel_Lot_Nr")
        if lot_number is not None and sample.lot_number is None:
            sample.lot_number = str(lot_number).strip()

        instrument = _first_present(row, "InstrumentType")
        if instrument is not None and sample.instrument_type is None:
            sample.instrument_type = str(instrument).strip()

        for clinical_key in (
            "Gender",
            "Patient.Age.At.Collection",
            "Primary.Diagnosis",
            "Patient",
            "Race",
            "SampleGroup",
        ):
            value = _first_present(row, clinical_key)
            if value is not None and clinical_key not in sample.clinical:
                sample.clinical[clinical_key] = str(value).strip()

    return [by_id[k] for k in sorted(by_id)]


def load_npx_samples(path: str | Path) -> tuple[list[NpxSample], int]:
    """Load and aggregate sample metadata from an NPX parquet file."""
    pf = _parquet_file(path)
    resolved = _resolve_parquet_columns(pf.schema.names)
    read_cols = _readable_columns(resolved)
    return _aggregate_batches(pf, read_cols, resolved)


def normalize_panel_name(panel: str | None) -> str | None:
    if not panel:
        return None
    return panel.replace("_", " ").strip()


def infer_platform(panel: str | None, instrument_type: str | None = None) -> str | None:
    candidates: list[str] = []
    if panel:
        candidates.append(panel.replace("_", " ").lower())
        candidates.append(panel.lower())
    if instrument_type:
        lowered = instrument_type.lower()
        if "novaseq" in lowered or "nextseq" in lowered:
            candidates.append("explore ht")
    for candidate in candidates:
        for needle, platform in PANEL_PLATFORM_HINTS:
            if needle in candidate:
                return platform
    return None


def map_sample_type(raw: str | None, *, is_control: bool = False) -> str:
    if not raw:
        return "plate control" if is_control else "study sample"
    normalized = re.sub(r"[\s_]+", " ", raw.strip().upper())
    underscored = normalized.replace(" ", "_")
    return SAMPLE_TYPE_MAP.get(normalized, SAMPLE_TYPE_MAP.get(underscored, "study sample"))


def _is_control_sample_type(label: str) -> bool:
    return label not in {"study sample"}


def normalize_sample_matrix(raw: str | None) -> str | None:
    """Map common matrix shorthand to UBERON/BTO-compatible SDRF labels."""
    if raw is None:
        return None
    text = raw.strip()
    if not text or text in {"not available", "not applicable"}:
        return text
    return SAMPLE_MATRIX_MAP.get(text.lower(), text)


def _transform_sex(raw: str) -> str | None:
    lowered = raw.strip().lower()
    if lowered in {"female", "f"}:
        return "female"
    if lowered in {"male", "m"}:
        return "male"
    if lowered in {"intersex"}:
        return "intersex"
    return None


def _transform_age(raw: str) -> str | None:
    text = raw.strip()
    if not text:
        return None
    if re.fullmatch(r"\d+[YyMmWwDd](?:\d+[MmWwDd])*", text):
        return text
    if text.isdigit():
        return f"{text}Y"
    return text


def _transform_disease(raw: str) -> str | None:
    text = raw.strip()
    if not text:
        return None
    if text.lower() in {"normal", "healthy", "control"}:
        return "normal"
    return text


def _transform_ancestry(raw: str) -> str | None:
    mapping = {
        "white": "European",
        "caucasian": "European",
        "black": "African",
        "african american": "African",
        "asian": "Asian",
        "hispanic": "Hispanic or Latin American",
        "latino": "Hispanic or Latin American",
        "latin american": "Hispanic or Latin American",
    }
    return mapping.get(raw.strip().lower(), raw.strip())


CLINICAL_TO_SDRF: dict[str, tuple[str, Callable[[str], str | None]]] = {
    "Gender": ("characteristics[sex]", _transform_sex),
    "Patient.Age.At.Collection": ("characteristics[age]", _transform_age),
    "Primary.Diagnosis": ("characteristics[disease]", _transform_disease),
    "Patient": ("characteristics[individual]", lambda x: x.strip()),
    "Race": ("characteristics[ancestry category]", _transform_ancestry),
}


def clinical_to_sdrf(clinical: Mapping[str, str]) -> dict[str, str]:
    """Map embedded Olink clinical columns to SDRF human metadata fields."""
    mapped: dict[str, str] = {}
    for npx_col, (sdrf_col, transform) in CLINICAL_TO_SDRF.items():
        raw = clinical.get(npx_col)
        if not raw:
            continue
        value = transform(raw)
        if value:
            mapped[sdrf_col] = value
    return mapped


def load_sample_metadata(path: str | Path) -> dict[str, dict[str, str]]:
    """Load per-sample overrides from a TSV (first column must be SampleID)."""
    metadata: dict[str, dict[str, str]] = {}
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            return metadata
        id_col = reader.fieldnames[0]
        for row in reader:
            sample_id = (row.get(id_col) or "").strip()
            if not sample_id:
                continue
            overrides = {
                k: v.strip()
                for k, v in row.items()
                if k and k != id_col and v and v.strip()
            }
            metadata[sample_id] = overrides
            metadata[sample_id.lower()] = overrides
    return metadata


def _resolve_templates_dir(templates_dir: Path | None) -> Path:
    path = templates_dir or TEMPLATES_DIR
    if not path.is_dir():
        raise FileNotFoundError(
            f"SDRF templates directory not found: {path}. "
            "Run: git submodule update --init --recursive"
        )
    return path


def merged_template_columns(
    template_names: Sequence[str],
    *,
    templates_dir: Path | None = None,
) -> list[str]:
    """Return ordered column names for one or more SDRF templates."""
    sys.path.insert(0, str(REPO_ROOT / "spec" / "scripts"))
    from resolve_templates import load_manifest, resolve_template

    td = _resolve_templates_dir(templates_dir)
    manifest = load_manifest(td)
    order: list[str] = []
    seen: set[str] = set()
    for name in template_names:
        resolved = resolve_template(name, td, manifest)
        for col in resolved["all_columns"]:
            col_name = col["name"]
            if col_name not in seen:
                order.append(col_name)
                seen.add(col_name)
    return order


def _template_comment(name: str, version: str | None = None) -> str:
    if version is None:
        sys.path.insert(0, str(REPO_ROOT / "spec" / "scripts"))
        from resolve_templates import load_manifest

        manifest = load_manifest(_resolve_templates_dir(None))
        version = manifest[name]["latest"]
    return f"NT={name};VV=v{version}"


def _build_row(
    sample: NpxSample,
    *,
    defaults: ConversionDefaults,
    metadata: Mapping[str, str],
    templates: Sequence[str],
    data_file: str,
    bio_rep: int,
    map_clinical: bool,
) -> dict[str, str]:
    auto_clinical = clinical_to_sdrf(sample.clinical) if map_clinical else {}
    merged_meta = {**auto_clinical, **metadata}

    sample_type_label = merged_meta.get("characteristics[sample type]") or map_sample_type(
        sample.sample_type,
    )
    is_control = _is_control_sample_type(sample_type_label)

    platform = (
        merged_meta.get("comment[platform]")
        or defaults.platform
        or infer_platform(sample.panel, sample.instrument_type)
        or "not available"
    )

    assay_suffix = sample.plate_id or "1"
    assay_name = merged_meta.get("assay name") or f"{sample.sample_id}_plate_{assay_suffix}"

    row: dict[str, str] = {
        "source name": merged_meta.get("source name") or sample.sample_id,
        "assay name": assay_name,
        "technology type": TECHNOLOGY_TYPE,
        "comment[technical replicate]": merged_meta.get("comment[technical replicate]", "1"),
        "comment[data file]": merged_meta.get("comment[data file]") or data_file,
        "comment[sdrf version]": SDRF_VERSION,
        "comment[sdrf annotation tool]": ANNOTATION_TOOL,
        "characteristics[organism]": merged_meta.get(
            "characteristics[organism]",
            "not applicable" if is_control else defaults.organism,
        ),
        "characteristics[organism part]": merged_meta.get(
            "characteristics[organism part]",
            "not applicable" if is_control else defaults.organism_part,
        ),
        "characteristics[biological replicate]": merged_meta.get(
            "characteristics[biological replicate]",
            str(bio_rep),
        ),
        "characteristics[sample type]": sample_type_label,
        "characteristics[disease]": merged_meta.get(
            "characteristics[disease]",
            "not applicable" if is_control else defaults.disease,
        ),
        "comment[platform]": platform,
        "comment[quantification unit]": merged_meta.get(
            "comment[quantification unit]",
            QUANTIFICATION_UNIT,
        ),
    }

    panel_name = merged_meta.get("comment[panel name]") or normalize_panel_name(sample.panel)
    if panel_name:
        row["comment[panel name]"] = panel_name
    if sample.plate_id:
        row["comment[plate]"] = merged_meta.get("comment[plate]", sample.plate_id)
    if sample.normalization:
        row["comment[normalization method]"] = merged_meta.get(
            "comment[normalization method]",
            sample.normalization,
        )
    if sample.lot_number:
        row["comment[lot number]"] = merged_meta.get("comment[lot number]", sample.lot_number)

    matrix = normalize_sample_matrix(merged_meta.get("characteristics[sample matrix]"))
    if matrix:
        row["characteristics[sample matrix]"] = matrix
    elif defaults.sample_matrix != "not available" and not is_control:
        row["characteristics[sample matrix]"] = normalize_sample_matrix(
            defaults.sample_matrix,
        ) or defaults.sample_matrix

    if "human" in templates:
        row["characteristics[age]"] = merged_meta.get(
            "characteristics[age]",
            "not available" if is_control else defaults.age,
        )
        row["characteristics[sex]"] = merged_meta.get(
            "characteristics[sex]",
            "not available" if is_control else defaults.sex,
        )
        if ancestry := merged_meta.get("characteristics[ancestry category]"):
            row["characteristics[ancestry category]"] = ancestry
        if individual := merged_meta.get("characteristics[individual]"):
            row["characteristics[individual]"] = individual

    for key, value in merged_meta.items():
        if key not in row and value:
            row[key] = value

    return row


def _build_logical_columns(
    all_columns: Sequence[str],
    used_keys: set[str],
    template_names: Sequence[str],
) -> list[str | tuple[str, int]]:
    """Order columns per SDRF spec: source → characteristics → assay → comments.

    Within each section, column order follows the merged template definition
    (``all_columns``), not alphabetical sorting.
    """
    characteristics = [
        col for col in all_columns
        if col.startswith("characteristics[") and col in used_keys
    ]

    comments: list[str | tuple[str, int]] = []
    for col in all_columns:
        if col == "comment[sdrf template]":
            for idx in range(len(template_names)):
                comments.append(("comment[sdrf template]", idx))
        elif col.startswith("comment[") and col in used_keys:
            comments.append(col)

    factors = [
        col for col in all_columns
        if col.startswith("factor value[") and col in used_keys
    ]

    logical: list[str | tuple[str, int]] = []
    if "source name" in used_keys:
        logical.append("source name")
    logical.extend(characteristics)
    if "assay name" in used_keys:
        logical.append("assay name")
    if "technology type" in used_keys:
        logical.append("technology type")
    logical.extend(comments)
    logical.extend(factors)

    known = {item[0] if isinstance(item, tuple) else item for item in logical}
    extras = [col for col in all_columns if col in used_keys and col not in known]
    logical.extend(extras)
    remaining = sorted(used_keys - known - set(extras))
    logical.extend(remaining)
    return logical


def render_sdrf(
    rows: Sequence[Mapping[str, str]],
    *,
    templates: Sequence[str],
    templates_dir: Path | None = None,
) -> tuple[str, list[str]]:
    """Render SDRF TSV text and return (content, column_order)."""
    template_names = ["affinity-proteomics", *templates]
    all_columns = merged_template_columns(template_names, templates_dir=templates_dir)

    used_keys: set[str] = set()
    for row in rows:
        used_keys.update(row.keys())
    used_keys.update({"comment[sdrf version]", "comment[sdrf annotation tool]"})

    template_values = [_template_comment(name) for name in template_names]

    logical_columns = _build_logical_columns(all_columns, used_keys, template_names)

    out_columns: list[str] = []
    for item in logical_columns:
        if isinstance(item, tuple):
            out_columns.append(item[0])
        else:
            out_columns.append(item)

    out_rows: list[list[str]] = []
    for row in rows:
        values: list[str] = []
        for item in logical_columns:
            if isinstance(item, tuple):
                _, idx = item
                values.append(template_values[idx])
            else:
                values.append(row.get(item, ""))
        out_rows.append(values)

    lines = ["\t".join(out_columns)]
    lines.extend("\t".join(values) for values in out_rows)
    return "\n".join(lines) + "\n", out_columns


def convert_npx_to_sdrf(
    npx_path: str | Path,
    *,
    templates: Sequence[str] = ("human",),
    defaults: ConversionDefaults | None = None,
    sample_metadata: Mapping[str, Mapping[str, str]] | None = None,
    templates_dir: Path | None = None,
    map_clinical: bool = True,
) -> tuple[str, ConversionReport]:
    """Convert an Olink NPX parquet file to SDRF TSV text."""
    path = Path(npx_path)
    defaults = defaults or ConversionDefaults()
    if defaults.data_file is None:
        defaults.data_file = path.name

    samples, n_rows = load_npx_samples(path)
    if not samples:
        raise ValueError(f"No samples with SampleID found in {path}")

    metadata_lookup = sample_metadata or {}
    sdrf_rows: list[dict[str, str]] = []
    bio_rep_counter = 0
    warnings: list[str] = []
    clinical_mapped = 0

    for sample in samples:
        meta = metadata_lookup.get(sample.sample_id) or metadata_lookup.get(
            sample.sample_id.lower(), {},
        )
        sample_type_label = meta.get("characteristics[sample type]") or map_sample_type(
            sample.sample_type,
        )
        if not _is_control_sample_type(sample_type_label):
            bio_rep_counter += 1
            bio_rep = int(meta.get("characteristics[biological replicate]", bio_rep_counter))
        else:
            bio_rep = int(meta.get("characteristics[biological replicate]", 1))

        platform = (
            meta.get("comment[platform]")
            or defaults.platform
            or infer_platform(sample.panel, sample.instrument_type)
        )
        if platform is None:
            warnings.append(
                f"Sample {sample.sample_id}: could not infer comment[platform] "
                f"from panel {sample.panel!r}; using 'not available'"
            )

        if map_clinical and clinical_to_sdrf(sample.clinical):
            clinical_mapped += 1

        sdrf_rows.append(
            _build_row(
                sample,
                defaults=defaults,
                metadata=meta,
                templates=templates,
                data_file=defaults.data_file or path.name,
                bio_rep=bio_rep,
                map_clinical=map_clinical,
            )
        )

    template_names = ["affinity-proteomics", *templates]
    content, columns = render_sdrf(
        sdrf_rows,
        templates=templates,
        templates_dir=templates_dir,
    )

    report = ConversionReport(
        npx_path=str(path),
        n_samples=len(sdrf_rows),
        n_assay_rows=n_rows,
        panels=sorted({normalize_panel_name(s.panel) or s.panel for s in samples if s.panel}),
        plates=sorted({s.plate_id for s in samples if s.plate_id}),
        warnings=warnings,
        templates=template_names,
        output_columns=columns,
        clinical_mapped=clinical_mapped,
    )
    return content, report


def run_cli(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="NPXtoSDRF",
        description="Convert Olink NPX parquet exports to SDRF affinity-proteomics format",
    )
    parser.add_argument("npx_file", help="Path to Olink NPX parquet file")
    parser.add_argument("-o", "--output", help="Output SDRF TSV path (default: stdout)")
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="Print parquet schema/sample summary and exit (no SDRF written)",
    )
    parser.add_argument(
        "--template",
        action="append",
        default=["human"],
        help="Organism/add-on template to combine with affinity-proteomics (repeatable). "
        "Use --template none to emit technology columns only.",
    )
    parser.add_argument("--organism", default="not available")
    parser.add_argument("--organism-part", default="not available")
    parser.add_argument("--disease", default="not available")
    parser.add_argument(
        "--sample-matrix",
        default="not available",
        help="characteristics[sample matrix] (e.g. 'blood plasma'; 'plasma' is normalized automatically)",
    )
    parser.add_argument("--age", default="not available")
    parser.add_argument("--sex", default="not available")
    parser.add_argument(
        "--platform",
        help="Olink platform (e.g. 'Olink Explore HT'). Inferred from Panel when omitted.",
    )
    parser.add_argument(
        "--data-file",
        help="Value for comment[data file] (default: NPX parquet basename)",
    )
    parser.add_argument(
        "--sample-metadata",
        help="TSV with SampleID plus SDRF column overrides (tab-separated)",
    )
    parser.add_argument(
        "--no-clinical",
        action="store_true",
        help="Do not auto-map embedded clinical columns (Gender, Primary.Diagnosis, etc.)",
    )
    parser.add_argument(
        "--templates-dir",
        type=Path,
        default=None,
        help="Override path to spec/sdrf-proteomics/sdrf-templates",
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress summary on stderr")

    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.inspect:
        try:
            report = inspect_npx_parquet(args.npx_file)
        except (FileNotFoundError, ImportError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(report.summary())
        return 0

    templates = [t for t in args.template if t.lower() != "none"]
    defaults = ConversionDefaults(
        organism=args.organism,
        organism_part=args.organism_part,
        disease=args.disease,
        sample_matrix=normalize_sample_matrix(args.sample_matrix) or args.sample_matrix,
        age=args.age,
        sex=args.sex,
        platform=args.platform,
        data_file=args.data_file,
    )
    metadata = load_sample_metadata(args.sample_metadata) if args.sample_metadata else None

    try:
        content, report = convert_npx_to_sdrf(
            args.npx_file,
            templates=templates,
            defaults=defaults,
            sample_metadata=metadata,
            templates_dir=args.templates_dir,
            map_clinical=not args.no_clinical,
        )
    except (FileNotFoundError, ImportError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.output:
        Path(args.output).write_text(content, encoding="utf-8")
        if not args.quiet:
            print(f"Wrote {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(content)

    if not args.quiet:
        print(report.summary(), file=sys.stderr)

    return 1 if report.warnings else 0


if __name__ == "__main__":
    raise SystemExit(run_cli())

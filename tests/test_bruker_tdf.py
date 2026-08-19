"""Tests for tools.bruker_tdf — DIA windows out of a Bruker .d without downloading it.

Offline: a real ZIP holding a real SQLite `analysis.tdf` is built in a tmpdir and
read through the same Fetcher interface the HTTP path uses, so the central
directory parse, the local-header offset arithmetic, the inflate and the SQLite
read are all exercised for real — only the socket is absent.
"""

from __future__ import annotations

import os
import sqlite3
import struct
import zipfile

import pytest

from tools.bruker_tdf import (
    TdfAcquisition,
    ZipRangeError,
    describe_isolation_window,
    fetch_tdf,
    file_fetcher,
    list_zip_entries,
    read_tdf,
    render,
)

# The DIA windows #33 quotes VERBATIM from PXD052416 (timsTOF Ultra, diaPASEF).
# Only these seven rows are reproduced in the issue, so only these are used as
# real data; nothing here is back-filled with invented m/z values.
_PXD052416_QUOTED = [
    (1, 34, 580, 744.83, 45.10, 45.9),
    (1, 580, 724, 572.33, 29.99, 32.8),
    (1, 724, 944, 417.29, 34.58, 25.8),
    (2, 34, 557, 792.64, 52.52, 46.4),
    (5, 34, 423, 977.74, 44.53, 48.9),
    (5, 423, 596, 703.34, 39.89, 38.2),
    (5, 596, 944, 543.57, 29.52, 28.2),
]

# The issue also lists all 15 widths of that file. Here the widths are the real
# measurement; the m/z and CE columns are placeholders, since the issue does not
# quote them — this fixture exists only to exercise the 15-distinct-widths case.
_ALL_15_WIDTHS = [
    29.52, 29.55, 29.99, 31.49, 31.67, 33.51, 34.58, 35.07,
    37.01, 39.89, 44.53, 45.10, 52.52, 65.06, 74.51,
]
_WIDTHS_ONLY = [
    (1 + i // 3, 34, 944, 400.0 + 40 * i, w, 25.0 + i)
    for i, w in enumerate(_ALL_15_WIDTHS)
]


def _make_tdf(path, windows=_PXD052416_QUOTED, with_metadata=True):
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE DiaFrameMsMsWindows (WindowGroup INTEGER, ScanNumBegin INTEGER,"
        " ScanNumEnd INTEGER, IsolationMz REAL, IsolationWidth REAL, CollisionEnergy REAL)"
    )
    conn.executemany("INSERT INTO DiaFrameMsMsWindows VALUES (?,?,?,?,?,?)", windows)
    if with_metadata:
        conn.execute("CREATE TABLE GlobalMetadata (Key TEXT, Value TEXT)")
        conn.execute("INSERT INTO GlobalMetadata VALUES ('InstrumentName','timsTOF Ultra')")
    conn.commit()
    conn.close()
    return path


@pytest.fixture
def d_zip(tmp_path):
    """A .d.zip shaped like the real thing: the big binary first, the tdf inside."""
    tdf = _make_tdf(tmp_path / "analysis.tdf")
    z = tmp_path / "Blank_BK1_1_1799.d.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        # incompressible, so the archive really is larger than the member
        zf.writestr("Blank_BK1_1_1799.d/analysis.tdf_bin", os.urandom(200_000))
        zf.write(tdf, "Blank_BK1_1_1799.d/analysis.tdf")
        zf.writestr("Blank_BK1_1_1799.d/SampleInfo.xml", "<sample/>")
    return z


# --- ZIP reading --------------------------------------------------------

def test_central_directory_lists_members_from_the_tail(d_zip):
    entries = list_zip_entries(file_fetcher(d_zip), d_zip.stat().st_size)
    assert {e.name.split("/")[-1] for e in entries} == {
        "analysis.tdf_bin", "analysis.tdf", "SampleInfo.xml"}


def test_extracts_only_the_tdf_member(d_zip):
    blob = fetch_tdf(str(d_zip))
    # SQLite's file magic — proves we inflated the right member, not the padding.
    assert blob.startswith(b"SQLite format 3\x00")
    assert len(blob) < d_zip.stat().st_size


def _zip_with_divergent_extra(path, name: str, payload: bytes) -> None:
    """Hand-roll a ZIP whose LOCAL extra field is longer than the central one.

    Real writers do this (alignment padding, UT timestamps), and it is the trap
    a range reader must not fall into: the member's data offset is
    local_header + 30 + local_name_len + LOCAL_extra_len, and using the central
    directory's extra length instead lands short of the stream.
    """
    import zlib as _zlib
    raw_name = name.encode()
    local_extra = struct.pack("<HH", 0xFFFF, 4) + b"pad!"     # 8 bytes, local only
    crc = _zlib.crc32(payload)
    local = (
        b"PK\x03\x04" + struct.pack("<HHHHHIIIHH", 20, 0, 0, 0, 0, crc,
                                    len(payload), len(payload),
                                    len(raw_name), len(local_extra))
        + raw_name + local_extra + payload
    )
    central = (
        b"PK\x01\x02" + struct.pack("<HHHHHHIIIHHHHHII", 20, 20, 0, 0, 0, 0, crc,
                                    len(payload), len(payload), len(raw_name),
                                    0, 0, 0, 0, 0, 0)
        + raw_name
    )
    eocd = b"PK\x05\x06" + struct.pack("<HHHHIIH", 0, 0, 1, 1,
                                       len(central), len(local), 0)
    path.write_bytes(local + central + eocd)


def test_member_offset_comes_from_the_local_header(tmp_path):
    """A local extra field the central directory does not know about.

    If the data offset were computed from the central entry, the read would
    start 8 bytes early and return garbage instead of the SQLite header.
    """
    tdf = _make_tdf(tmp_path / "analysis.tdf")
    z = tmp_path / "divergent.zip"
    _zip_with_divergent_extra(z, "analysis.tdf", tdf.read_bytes())
    blob = fetch_tdf(str(z))
    assert blob.startswith(b"SQLite format 3\x00")
    assert read_tdf(blob).is_dia


def test_stored_member_needs_no_inflate(tmp_path):
    tdf = _make_tdf(tmp_path / "analysis.tdf")
    z = tmp_path / "stored.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_STORED) as zf:
        zf.write(tdf, "analysis.tdf")
    assert fetch_tdf(str(z)).startswith(b"SQLite format 3\x00")


def test_missing_member_names_what_the_archive_holds(tmp_path):
    z = tmp_path / "nope.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("analysis.tdf_bin", b"x")
    with pytest.raises(ZipRangeError, match="analysis.tdf_bin"):
        fetch_tdf(str(z))


def test_not_a_zip_is_reported_not_guessed(tmp_path):
    p = tmp_path / "junk.zip"
    p.write_bytes(b"not a zip at all")
    with pytest.raises(ZipRangeError, match="end-of-central-directory"):
        fetch_tdf(str(p))


def test_an_extracted_tdf_is_read_directly(tmp_path):
    tdf = _make_tdf(tmp_path / "analysis.tdf")
    assert fetch_tdf(str(tdf)).startswith(b"SQLite format 3\x00")


# --- the tables ---------------------------------------------------------

def test_reads_the_quoted_windows(d_zip):
    acq = read_tdf(fetch_tdf(str(d_zip)), source=str(d_zip))
    assert acq.is_dia
    assert len(acq.windows) == len(_PXD052416_QUOTED)
    assert {w.window_group for w in acq.windows} == {1, 2, 5}
    assert acq.properties["InstrumentName"] == "timsTOF Ultra"


def test_edges_are_measured_not_taken_from_the_prose(d_zip):
    """The paper (PMID:39536954) says "400 to 1000 m/z" and a CE ramp.

    The window table gives both as numbers: the edges are computed from
    IsolationMz +/- IsolationWidth/2, and the CE range comes straight out of the
    rows — no reading of a supplementary figure required.
    """
    acq = read_tdf(fetch_tdf(str(d_zip)))
    lo, hi = acq.mz_range
    assert (round(lo, 2), round(hi, 2)) == (400.0, 1000.0)
    assert acq.ce_range == (25.8, 48.9)


def test_a_tdf_without_the_window_table_is_not_dia(tmp_path):
    p = tmp_path / "analysis.tdf"
    conn = sqlite3.connect(p)
    conn.execute("CREATE TABLE Frames (Id INTEGER)")
    conn.commit()
    conn.close()
    acq = read_tdf(p)
    assert not acq.is_dia
    assert describe_isolation_window(acq)["sdrf_value"] is None


# --- what goes in the SDRF ---------------------------------------------

def test_variable_windows_refuse_a_scalar(d_zip):
    """The whole point of #33: distinct widths, so no single number is right."""
    d = describe_isolation_window(read_tdf(fetch_tdf(str(d_zip))))
    assert d["sdrf_value"] == "not available"
    assert len(d["widths"]) == len(_PXD052416_QUOTED)


def test_all_fifteen_widths_of_the_reported_file(tmp_path):
    d = describe_isolation_window(
        read_tdf(_make_tdf(tmp_path / "analysis.tdf", windows=_WIDTHS_ONLY)))
    assert d["widths"] == sorted(_ALL_15_WIDTHS)
    assert d["sdrf_value"] == "not available"


def test_the_tempting_wrong_derivation_is_named(tmp_path):
    """(1000-400)/15 = 40 m/z matches no actual window, passes the regex, and

    passes parse_sdrf. The rationale has to warn about it explicitly, or the
    next annotator just recomputes it.
    """
    d = describe_isolation_window(
        read_tdf(_make_tdf(tmp_path / "analysis.tdf", windows=_WIDTHS_ONLY)))
    assert 40.0 not in d["widths"]
    assert "mean" in d["rationale"]


def test_uniform_windows_do_carry_a_scalar(tmp_path):
    """SWATH-style acquisitions are exactly what the scalar column was made for."""
    rows = [(1, 0, 100, 400.0 + 25 * i, 25.0, 30.0) for i in range(8)]
    tdf = _make_tdf(tmp_path / "analysis.tdf", windows=rows)
    d = describe_isolation_window(read_tdf(tdf))
    assert d["sdrf_value"] == "25"
    assert d["widths"] == [25.0]


def test_render_shows_the_table_and_the_verdict(d_zip):
    out = render(read_tdf(fetch_tdf(str(d_zip)), source="x.d.zip"))
    assert "7 in 3 group(s)" in out
    assert "comment[isolation window width] -> not available" in out
    assert "744.83" in out          # a real window row, for the report


def test_render_handles_a_non_dia_run():
    assert "not DIA" in render(TdfAcquisition(source="s"))

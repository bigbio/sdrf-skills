"""Read Bruker timsTOF acquisition metadata out of `analysis.tdf` — over HTTP.

A `.d` archive is 2.5–9.2 GB, well past any sane download budget, but the table
that answers "what were the DIA isolation windows" is `analysis.tdf`, a plain
SQLite database of ~15 MB sitting inside it. PRIDE's HTTPS mirror sends
`Accept-Ranges: bytes`, so the ZIP central directory can be read from the tail
and that one member range-fetched: 14.7 MB instead of 2502 MB on the measured
case (PXD052416), a ~170x reduction, with no dependency beyond the stdlib.

The windows matter because they are otherwise unknowable. diaPASEF windows are
variable-width by design — 15 distinct widths from 29.52 to 74.51 m/z in that
dataset — and the intuitive derivation from a manuscript ("15 windows spanning
400-1000" -> 600/15 = 40) yields a number that is not one of them, passes the
`comment[isolation window width]` regex, and passes parse_sdrf. Silent
corruption. See `describe_isolation_window()` for what to write instead.
"""

from __future__ import annotations

import sqlite3
import struct
import tempfile
import urllib.request
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

USER_AGENT = "sdrf-skills/0.1 (+https://github.com/bigbio/sdrf-skills)"
DEFAULT_TIMEOUT = 60

# The member we want, and how much of the archive tail to read to find it.
TDF_MEMBER = "analysis.tdf"
_EOCD_SIG = b"PK\x05\x06"
_EOCD64_LOCATOR_SIG = b"PK\x06\x07"
_EOCD64_SIG = b"PK\x06\x06"
_CEN_SIG = b"PK\x01\x02"
_TAIL_BYTES = 128 * 1024

# A .tdf over this size is not what we think it is; refuse rather than stream
# gigabytes into a temp file.
MAX_MEMBER_BYTES = 512 * 1024 * 1024


class ZipRangeError(RuntimeError):
    """The archive could not be read by range requests."""


# ---------------------------------------------------------------------------
# HTTP range reading
# ---------------------------------------------------------------------------

Fetcher = Callable[[int, int | None], bytes]
"""fetch(start, end) -> bytes. `end` is inclusive, as in the HTTP Range header;
`end=None` means "to the end of the file"."""


def http_fetcher(url: str, timeout: int = DEFAULT_TIMEOUT) -> Fetcher:
    """A Fetcher backed by HTTP range requests."""

    def fetch(start: int, end: int | None = None) -> bytes:
        rng = f"bytes={start}-" if end is None else f"bytes={start}-{end}"
        req = urllib.request.Request(
            url, headers={"Range": rng, "User-Agent": USER_AGENT}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            # 206 = the server honoured the range. A 200 means it ignored it and
            # is sending the WHOLE multi-GB archive, which is exactly what this
            # module exists to avoid.
            if resp.status == 200 and start > 0:
                raise ZipRangeError(
                    "server ignored the Range header and is sending the whole file"
                )
            return resp.read()

    return fetch


def file_fetcher(path: str | Path) -> Fetcher:
    """A Fetcher backed by a local file — same code path, no network."""
    p = Path(path)

    def fetch(start: int, end: int | None = None) -> bytes:
        with p.open("rb") as fh:
            fh.seek(start)
            return fh.read() if end is None else fh.read(end - start + 1)

    return fetch


def _remote_size(url: str, timeout: int = DEFAULT_TIMEOUT) -> int:
    req = urllib.request.Request(
        url, method="HEAD", headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        size = resp.headers.get("Content-Length")
        if not size:
            raise ZipRangeError("server did not report Content-Length")
        return int(size)


# ---------------------------------------------------------------------------
# ZIP central directory
# ---------------------------------------------------------------------------

@dataclass
class ZipEntry:
    name: str
    compress_type: int
    compressed_size: int
    uncompressed_size: int
    header_offset: int


def list_zip_entries(fetch: Fetcher, size: int) -> list[ZipEntry]:
    """Parse a ZIP's central directory using only tail reads.

    Handles ZIP64, which is not optional here: a `.d.zip` above 4 GB stores its
    real central-directory offset in the ZIP64 record and leaves 0xFFFFFFFF in
    the classic one, so a parser that ignores ZIP64 seeks to a garbage offset.
    """
    tail_start = max(0, size - _TAIL_BYTES)
    tail = fetch(tail_start, size - 1)

    idx = tail.rfind(_EOCD_SIG)
    if idx < 0:
        raise ZipRangeError("no end-of-central-directory record in the archive tail")
    cen_size, cen_offset = struct.unpack("<II", tail[idx + 12:idx + 20])

    loc = tail.rfind(_EOCD64_LOCATOR_SIG, 0, idx)
    if loc >= 0:
        (eocd64_offset,) = struct.unpack("<Q", tail[loc + 8:loc + 16])
        rel = eocd64_offset - tail_start
        if 0 <= rel < len(tail) and tail[rel:rel + 4] == _EOCD64_SIG:
            cen_size, cen_offset = struct.unpack("<QQ", tail[rel + 40:rel + 56])
        else:
            head = fetch(eocd64_offset, eocd64_offset + 55)
            if head[:4] != _EOCD64_SIG:
                raise ZipRangeError("ZIP64 locator points at no ZIP64 EOCD record")
            cen_size, cen_offset = struct.unpack("<QQ", head[40:56])

    if cen_offset >= tail_start:
        cen = tail[cen_offset - tail_start:cen_offset - tail_start + cen_size]
    else:
        cen = fetch(cen_offset, cen_offset + cen_size - 1)

    entries: list[ZipEntry] = []
    pos = 0
    while pos + 46 <= len(cen) and cen[pos:pos + 4] == _CEN_SIG:
        (compress_type,) = struct.unpack("<H", cen[pos + 10:pos + 12])
        csize, usize = struct.unpack("<II", cen[pos + 20:pos + 28])
        n_len, x_len, c_len = struct.unpack("<HHH", cen[pos + 28:pos + 34])
        (offset,) = struct.unpack("<I", cen[pos + 42:pos + 46])
        name = cen[pos + 46:pos + 46 + n_len].decode("utf-8", "replace")
        extra = cen[pos + 46 + n_len:pos + 46 + n_len + x_len]
        usize, csize, offset = _apply_zip64_extra(extra, usize, csize, offset)
        entries.append(ZipEntry(name, compress_type, csize, usize, offset))
        pos += 46 + n_len + x_len + c_len
    if not entries:
        raise ZipRangeError("central directory held no entries")
    return entries


def _apply_zip64_extra(
    extra: bytes, usize: int, csize: int, offset: int
) -> tuple[int, int, int]:
    """Replace 0xFFFFFFFF placeholders from the ZIP64 extra field, in order."""
    pos = 0
    while pos + 4 <= len(extra):
        tag, ln = struct.unpack("<HH", extra[pos:pos + 4])
        body = extra[pos + 4:pos + 4 + ln]
        if tag == 0x0001:
            vals = list(struct.unpack(f"<{len(body) // 8}Q", body[:len(body) // 8 * 8]))
            for name in ("usize", "csize", "offset"):
                if not vals:
                    break
                if name == "usize" and usize == 0xFFFFFFFF:
                    usize = vals.pop(0)
                elif name == "csize" and csize == 0xFFFFFFFF:
                    csize = vals.pop(0)
                elif name == "offset" and offset == 0xFFFFFFFF:
                    offset = vals.pop(0)
        pos += 4 + ln
    return usize, csize, offset


def extract_member(fetch: Fetcher, entry: ZipEntry) -> bytes:
    """Range-fetch and inflate one ZIP member."""
    if entry.uncompressed_size > MAX_MEMBER_BYTES:
        raise ZipRangeError(
            f"{entry.name} is {entry.uncompressed_size / 1e6:.0f} MB, "
            f"over the {MAX_MEMBER_BYTES / 1e6:.0f} MB member cap"
        )
    # The local header repeats the name and extra fields with its OWN lengths —
    # they routinely differ from the central directory's, so the data offset has
    # to be computed from the local header, never from the central one.
    head = fetch(entry.header_offset, entry.header_offset + 29)
    if head[:4] != b"PK\x03\x04":
        raise ZipRangeError(f"no local file header at offset {entry.header_offset}")
    n_len, x_len = struct.unpack("<HH", head[26:30])
    data_start = entry.header_offset + 30 + n_len + x_len
    raw = fetch(data_start, data_start + entry.compressed_size - 1)
    if entry.compress_type == 0:
        return raw
    if entry.compress_type == 8:
        return zlib.decompress(raw, -15)
    raise ZipRangeError(f"unsupported compression method {entry.compress_type}")


def fetch_tdf(source: str, member: str = TDF_MEMBER) -> bytes:
    """Pull `analysis.tdf` out of a local or remote `.d` archive.

    `source` is a URL or a path to the `.d.zip`, or to an already-extracted
    `analysis.tdf` (returned as-is).
    """
    if not source.startswith(("http://", "https://")):
        p = Path(source)
        if p.suffix == ".tdf" or p.name == member:
            return p.read_bytes()
        fetch, size = file_fetcher(p), p.stat().st_size
    else:
        fetch, size = http_fetcher(source), _remote_size(source)

    entries = list_zip_entries(fetch, size)
    for e in entries:
        if e.name == member or e.name.endswith("/" + member):
            return extract_member(fetch, e)
    raise ZipRangeError(
        f"{member} not in the archive (members: {', '.join(e.name for e in entries[:8])})"
    )


# ---------------------------------------------------------------------------
# The tables
# ---------------------------------------------------------------------------

@dataclass
class DiaWindow:
    window_group: int
    scan_begin: int
    scan_end: int
    isolation_mz: float
    isolation_width: float
    collision_energy: float

    @property
    def mz_low(self) -> float:
        return self.isolation_mz - self.isolation_width / 2

    @property
    def mz_high(self) -> float:
        return self.isolation_mz + self.isolation_width / 2


@dataclass
class TdfAcquisition:
    windows: list[DiaWindow] = field(default_factory=list)
    properties: dict[str, str] = field(default_factory=dict)
    source: str = ""

    @property
    def is_dia(self) -> bool:
        return bool(self.windows)

    @property
    def widths(self) -> list[float]:
        return sorted({round(w.isolation_width, 4) for w in self.windows})

    @property
    def uniform_width(self) -> float | None:
        """The single width, or None when the windows are variable-width."""
        return self.widths[0] if len(self.widths) == 1 else None

    @property
    def mz_range(self) -> tuple[float, float] | None:
        if not self.windows:
            return None
        return (
            min(w.mz_low for w in self.windows),
            max(w.mz_high for w in self.windows),
        )

    @property
    def ce_range(self) -> tuple[float, float] | None:
        if not self.windows:
            return None
        ces = [w.collision_energy for w in self.windows]
        return (min(ces), max(ces))


def read_tdf(blob: bytes | str | Path, source: str = "") -> TdfAcquisition:
    """Read the acquisition tables out of an `analysis.tdf` SQLite database."""
    if isinstance(blob, (str, Path)):
        path, tmp = Path(blob), None
    else:
        # sqlite3 needs a file. Named temp, deleted on the way out.
        tmp = tempfile.NamedTemporaryFile(suffix=".tdf", delete=False)
        tmp.write(blob)
        tmp.close()
        path = Path(tmp.name)
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            return _read_conn(conn, source)
        finally:
            conn.close()
    finally:
        if tmp is not None:
            path.unlink(missing_ok=True)


def _read_conn(conn: sqlite3.Connection, source: str) -> TdfAcquisition:
    out = TdfAcquisition(source=source)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}

    if "DiaFrameMsMsWindows" in tables:
        rows = conn.execute(
            "SELECT WindowGroup, ScanNumBegin, ScanNumEnd, IsolationMz, "
            "IsolationWidth, CollisionEnergy FROM DiaFrameMsMsWindows "
            "ORDER BY WindowGroup, ScanNumBegin"
        ).fetchall()
        out.windows = [
            DiaWindow(int(g), int(sb), int(se), float(mz), float(w), float(ce))
            for g, sb, se, mz, w, ce in rows
        ]

    # GlobalMetadata is the tdf's own key/value table (instrument, acquisition
    # software, sample name). Absent in some older schemas — not an error.
    if "GlobalMetadata" in tables:
        for k, v in conn.execute("SELECT Key, Value FROM GlobalMetadata"):
            out.properties[str(k)] = str(v)
    return out


# ---------------------------------------------------------------------------
# What to actually write in the SDRF
# ---------------------------------------------------------------------------

def describe_isolation_window(acq: TdfAcquisition) -> dict:
    """Decide what `comment[isolation window width]` can honestly carry.

    The column is a single scalar (`pattern: ^\\d+(\\.\\d+)?$`, examples 25/8/4),
    which assumes uniform SWATH-style windows. diaPASEF windows are variable by
    design, and no single number is correct for them — so the honest value is
    the reserved word, with the measured table going in the report. Deriving a
    mean or a span/count average produces a plausible wrong number that passes
    both the regex and parse_sdrf.
    """
    if not acq.windows:
        return {
            "acquisition": "not DIA (no DiaFrameMsMsWindows rows)",
            "sdrf_value": None,
            "rationale": "no DIA window table in this run",
        }
    uniform = acq.uniform_width
    lo, hi = acq.mz_range
    ce_lo, ce_hi = acq.ce_range
    common = {
        "n_windows": len(acq.windows),
        "n_window_groups": len({w.window_group for w in acq.windows}),
        "widths": acq.widths,
        "mz_range": [round(lo, 2), round(hi, 2)],
        "ce_range": [ce_lo, ce_hi],
    }
    if uniform is not None:
        return {
            **common,
            "acquisition": "DIA, uniform windows",
            "sdrf_value": f"{uniform:g}",
            "rationale": "every window has the same width, so the scalar column can carry it",
        }
    return {
        **common,
        "acquisition": "DIA, variable windows (diaPASEF)",
        "sdrf_value": "not available",
        "rationale": (
            f"{len(acq.widths)} distinct widths ({min(acq.widths):g}-{max(acq.widths):g} m/z); "
            "comment[isolation window width] is a single scalar and cannot express them. "
            "Do NOT compute a mean or (span/n_windows) — that yields a number matching no "
            "actual window, and it passes both the regex and parse_sdrf. Put the measured "
            "table in the report instead."
        ),
    }


def render(acq: TdfAcquisition) -> str:
    """Human-readable summary for the CLI and for pasting into a report."""
    d = describe_isolation_window(acq)
    lines = [f"source: {acq.source or '(local)'}", f"acquisition: {d['acquisition']}"]
    if instrument := acq.properties.get("InstrumentName"):
        lines.append(f"instrument: {instrument}")
    if not acq.windows:
        return "\n".join(lines)

    lines += [
        f"windows: {d['n_windows']} in {d['n_window_groups']} group(s)",
        f"m/z coverage: {d['mz_range'][0]:.2f} - {d['mz_range'][1]:.2f}",
        f"collision energy: {d['ce_range'][0]:g} - {d['ce_range'][1]:g} eV",
        f"widths ({len(d['widths'])} distinct): "
        + ", ".join(f"{w:g}" for w in d["widths"]),
        "",
        f"{'grp':>4} {'scanBeg':>8} {'scanEnd':>8} {'IsolationMz':>12} "
        f"{'IsolWidth':>10} {'CE':>7}",
    ]
    for w in acq.windows:
        lines.append(
            f"{w.window_group:>4} {w.scan_begin:>8} {w.scan_end:>8} "
            f"{w.isolation_mz:>12.2f} {w.isolation_width:>10.2f} "
            f"{w.collision_energy:>7.1f}"
        )
    lines += ["", f"comment[isolation window width] -> {d['sdrf_value']}",
              f"  {d['rationale']}"]
    return "\n".join(lines)


def analyze(source: str) -> TdfAcquisition:
    """Fetch (or open) an `analysis.tdf` and read its acquisition tables."""
    return read_tdf(fetch_tdf(source), source=source)

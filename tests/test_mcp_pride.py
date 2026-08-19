"""Contract tests for mcp/server.py PRIDE + article-identifier tools.

Offline: PRIDE responses are stubbed. These pin the exact call formats that
skills/sdrf-metascreen/SKILL.md documents — the failure mode they guard is
silent, because a rejected identifier degrades to "no evidence" rather than
raising, which a screening skill then reports as `uncertain`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "mcp"))
import server  # noqa: E402


# --- identifier formats -------------------------------------------------

@pytest.mark.parametrize("raw", ["35695565", "PMC9174028", "10.1038/s41467-022-30310-x"])
def test_classify_article_id_accepts_bare_forms(raw):
    assert server._classify_article_id(raw) is not None


@pytest.mark.parametrize("raw", ["PMID:35695565", "pmid:35695565", "doi:10.1038/x"])
def test_classify_article_id_rejects_prefixed_forms(raw):
    """get_article_metadata takes BARE ids. Prefixed forms yield an error record."""
    assert server._classify_article_id(raw) is None


def test_get_article_metadata_flags_unrecognised_instead_of_raising():
    [rec] = server.get_article_metadata(["PMID:35695565"])
    assert "Unrecognised identifier" in rec["error"]


@pytest.mark.parametrize("raw", ["10.1038/s41467-022-30310-x", "https://doi.org/10.1038/x-y", "35695565"])
def test_parse_identifier_accepts_unpaywall_forms(raw):
    assert server._parse_identifier(raw) is not None


def test_parse_identifier_rejects_doi_prefix():
    """get_pdf_by_unpaywall takes a BARE DOI; the 'doi:' prefix fails the regex."""
    assert server._parse_identifier("doi:10.1038/s41467-022-30310-x") is None


# --- PRIDE project details ---------------------------------------------

_DETAILS = {
    "accession": "PXD005969",
    "title": "t",
    "projectDescription": "d",
    "sampleProcessingProtocol": "spp",
    "dataProcessingProtocol": "dpp",
    "organisms": [{"name": "Human gut metagenome"}],
    "organismParts": [{"name": "Blood"}],
    "countries": ["Canada"],
    "instruments": [{"name": "Q Exactive"}],
    "experimentTypes": [{"name": "Shotgun proteomics"}],
    "quantificationMethods": [{"name": "TIC"}],
    "identifiedPTMStrings": [],
    "keywords": ["Metaproteomics"],
    "references": [],
}


def test_get_project_details_surfaces_screening_fields(monkeypatch):
    """experiment_types / quantification_methods drive criteria screening."""
    monkeypatch.setattr(server, "_cached_get_json", lambda *a, **k: _DETAILS)
    d = server.get_project_details("PXD005969")
    assert d["experiment_types"] == ["Shotgun proteomics"]
    assert d["quantification_methods"] == ["TIC"]
    assert d["organism_parts"] == ["Blood"]
    assert d["countries"] == ["Canada"]
    assert d["instruments"] == ["Q Exactive"]


def test_get_project_details_reports_missing_project(monkeypatch):
    """MassIVE accessions are not served by PRIDE — must surface, not fabricate."""
    monkeypatch.setattr(server, "_cached_get_json", lambda *a, **k: None)
    d = server.get_project_details("MSV000078958")
    assert "error" in d and "not found" in d["error"]


# --- PRIDE search -------------------------------------------------------

def test_search_projects_parses_plain_string_fields(monkeypatch):
    """/search/projects returns bare strings where /projects/{acc} returns CvParams."""
    hit = {
        "accession": "PXD077488",
        "title": "t",
        "projectDescription": "d",
        "organisms": ["Candidatus accumulibacter phosphatis"],
        "organismsPart": [],
        "instruments": ["Q Exactive Plus"],
        "experimentTypes": ["Data-dependent acquisition", "Bottom-up proteomics"],
        "quantificationMethods": [],
        "keywords": ["Metaproteomics"],
        "publicationDate": "2025-01-01",
        "sdrf": None,
    }
    monkeypatch.setattr(server, "_cached_get_json", lambda *a, **k: [hit])
    r = server.search_projects("metaproteomics", repository="pride")
    [got] = r["results"]
    assert got["instruments"] == ["Q Exactive Plus"]
    assert got["experiment_types"] == ["Data-dependent acquisition", "Bottom-up proteomics"]
    assert got["organism"] == ["Candidatus accumulibacter phosphatis"]
    assert got["has_sdrf"] is False


def test_search_projects_parses_cvparam_fields(monkeypatch):
    """Accept the dict shape too, so the tool survives an API alignment."""
    hit = {"accession": "PXD1", "instruments": [{"name": "Orbitrap Eclipse"}]}
    monkeypatch.setattr(server, "_cached_get_json", lambda *a, **k: [hit])
    [got] = server.search_projects("x", repository="pride")["results"]
    assert got["instruments"] == ["Orbitrap Eclipse"]


def test_search_projects_handles_unreachable(monkeypatch):
    monkeypatch.setattr(server, "_cached_get_json", lambda *a, **k: None)
    r = server.search_projects("x", repository="pride")
    assert r["count"] == 0 and r["results"] == []
    assert any("PRIDE" in e for e in r["errors"])


def test_search_projects_rejects_bad_repository():
    assert "error" in server.search_projects("x", repository="nope")


# --- MassIVE / PROXI ----------------------------------------------------

_MASSIVE = {
    "title": "Integrated metagenomics/metaproteomics",
    "summary": "Human gut metaproteome.",
    "accession": [
        {"accession": "MS:1002487", "value": "MSV000079512"},
        {"accession": "MS:1001919", "value": "PXD003626"},
    ],
    "instruments": [{"name": "instrument model", "value": "LTQ Orbitrap"}],
    # species / publications / contacts are nested one list deeper than PRIDE
    "species": [[{"name": "taxonomy: common name", "value": "Human gut metaproteome"}]],
    "keywords": [
        {"value": "metaproteomics"},
        {"value": "null"},      # MassIVE writes the STRING "null" for missing
        {"value": None},
    ],
    "publications": [[
        {"accession": "MS:1000879", "value": "23209564"},
        {"accession": "MS:1002866", "value": "Erickson AR et al. PLoS ONE. 2012."},
    ]],
    "modifications": [{"value": "N/A"}],
}


def test_proxi_values_flattens_and_drops_placeholders():
    """The literal string 'null' is MassIVE's missing marker — never a value."""
    assert server._proxi_values(_MASSIVE, "keywords") == ["metaproteomics"]
    assert server._proxi_values(_MASSIVE, "species") == ["Human gut metaproteome"]
    assert server._proxi_values(_MASSIVE, "modifications") == []


def test_massive_to_project_prefers_pxd_and_keeps_both(monkeypatch):
    monkeypatch.setattr(server, "_resolve_publication",
                        lambda pmid, doi, ref: {"pmid": pmid, "pmcid": None, "doi": doi,
                                                "is_open_access": False, "reference": ref})
    p = server._massive_to_project(_MASSIVE)
    assert p["accession"] == "PXD003626"
    assert set(p["all_accessions"]) == {"MSV000079512", "PXD003626"}
    assert p["repository"] == "MassIVE"
    assert p["instruments"] == ["LTQ Orbitrap"]
    assert p["publications"][0]["pmid"] == "23209564"
    # MassIVE publishes none of these — empty, never fabricated
    assert p["experiment_types"] == [] and p["quantification_methods"] == []
    assert p["sample_processing_protocol"] is None


def test_massive_search_hit_never_resolves_publications(monkeypatch):
    """Search hits don't expose `publications` — resolving them would be a
    wasted Europe PMC call per record. Fail loudly if that call ever fires."""
    def boom(*a, **k):
        raise AssertionError("search hit must not resolve publications")

    monkeypatch.setattr(server, "_resolve_publication", boom)
    hit = server._massive_search_hit(_MASSIVE)
    assert "publications" not in hit
    assert hit["accession"] == "PXD003626"
    assert hit["instruments"] == ["LTQ Orbitrap"]


def test_get_project_details_routes_msv_to_massive(monkeypatch):
    monkeypatch.setattr(server, "_massive_get_dataset", lambda acc: _MASSIVE)
    monkeypatch.setattr(server, "_resolve_publication",
                        lambda *a: {"pmid": "1", "pmcid": None, "doi": None,
                                    "is_open_access": False, "reference": ""})
    d = server.get_project_details("MSV000079512")
    assert d["repository"] == "MassIVE"
    assert d["accession"] == "MSV000079512"  # echoes what was queried


def test_get_project_details_falls_back_to_massive_for_pxd(monkeypatch):
    """PXD003626 is real, is 404 in PRIDE, and lives at MassIVE."""
    monkeypatch.setattr(server, "_cached_get_json", lambda *a, **k: None)
    monkeypatch.setattr(server, "_massive_get_dataset", lambda acc: _MASSIVE)
    monkeypatch.setattr(server, "_resolve_publication",
                        lambda *a: {"pmid": "1", "pmcid": None, "doi": None,
                                    "is_open_access": False, "reference": ""})
    d = server.get_project_details("PXD003626")
    assert d["repository"] == "MassIVE" and "error" not in d


def test_get_project_details_errors_when_neither_repo_has_it(monkeypatch):
    monkeypatch.setattr(server, "_cached_get_json", lambda *a, **k: None)
    monkeypatch.setattr(server, "_massive_get_dataset", lambda acc: None)
    d = server.get_project_details("PXD999999999")
    assert "PRIDE or MassIVE" in d["error"]


def test_search_dedups_massive_record_already_seen_in_pride(monkeypatch):
    """A MassIVE record whose PXD is already a PRIDE hit must not double-count."""
    pride_hit = {"accession": "PXD003626", "instruments": ["Q Exactive"]}

    def fake_get(url, params=None, **kw):
        return [pride_hit] if "pride" in url else [_MASSIVE]

    monkeypatch.setattr(server, "_cached_get_json", fake_get)
    r = server.search_projects("x", repository="all")
    assert r["count"] == 1 and r["results"][0]["repository"] == "PRIDE"


def test_search_dedups_two_massive_records_sharing_an_accession(monkeypatch):
    """Two MassIVE hits in the same page can share an accession (e.g. a
    dataset re-listed under both its MSV and PXD entry) — `seen` must grow as
    each MassIVE hit is accepted, not just start from the PRIDE results."""
    dupe = {
        "title": "Same dataset, second listing",
        "accession": [{"accession": "MS:1002487", "value": "MSV000079512"}],
    }

    def fake_get(url, params=None, **kw):
        return [] if "pride" in url else [_MASSIVE, dupe]

    monkeypatch.setattr(server, "_cached_get_json", fake_get)
    r = server.search_projects("x", repository="all")
    assert r["count"] == 1


# --- transport-level contracts -----------------------------------------

class _Resp:
    def __init__(self, status, body: bytes, encoding="utf-8"):
        self.status_code, self._body, self.encoding = status, body, encoding

    def json(self):
        return json.loads(self._body.decode("utf-8"))  # httpx decodes bytes as UTF-8

    @property
    def text(self):
        return self._body.decode(self.encoding)


def _stub_client(monkeypatch, resp):
    server._json_cache.clear()
    monkeypatch.setattr(server, "_get_client",
                        lambda: type("C", (), {"get": lambda *a, **k: resp})())


def test_cached_get_json_decodes_latin1_body(monkeypatch):
    """MassIVE serves charset=ISO-8859-1; one accented byte must not drop a page."""
    body = '[{"title":"Café proteomics"}]'.encode("latin-1")
    _stub_client(monkeypatch, _Resp(200, body, encoding="ISO-8859-1"))
    data = _cached_uncached()
    assert data == [{"title": "Café proteomics"}]


def _cached_uncached():
    return server._cached_get_json("https://example.invalid/x")


def test_cached_get_json_404_is_not_found_not_failure(monkeypatch):
    _stub_client(monkeypatch, _Resp(404, b""))
    assert server._cached_get_json("https://example.invalid/y") is None
    server._json_cache.clear()
    assert server._cached_get_json("https://example.invalid/y", not_found_ok=True) == []


# --- search_extensive: multi-keyword union + visible truncation ---------

def _pride_pages(pages: dict):
    """Fake _cached_get_json serving PRIDE pages keyed by (keyword, filter, page)."""
    def fake(url, params=None, **kw):
        params = params or {}
        if "pride" not in url:
            return []          # MassIVE: exhausted immediately
        key = (params.get("keyword"), params.get("filter"), params.get("page"))
        return pages.get(key, [])
    return fake


def _accs(n, start=1):
    return [{"accession": f"PXD{i:06d}"} for i in range(start, start + n)]


def test_search_extensive_unions_keywords_and_dedupes(monkeypatch):
    """Recall needs a keyword sweep; the same dataset found twice is one row."""
    monkeypatch.setattr(server, "_cached_get_json", _pride_pages({
        ("SCoPE2", None, "0"): _accs(2, 1),          # PXD000001, PXD000002
        ("nanoPOTS", None, "0"): _accs(2, 2),        # PXD000002 again, PXD000003
    }))
    r = server.search_extensive(["SCoPE2", "nanoPOTS"], page_size=100)
    assert r["count"] == 3
    assert r["per_keyword"]["SCoPE2"]["new"] == 2
    assert r["per_keyword"]["nanoPOTS"]["new"] == 1   # the overlap is not double counted
    assert "truncated" not in r


def test_search_extensive_accepts_a_single_string(monkeypatch):
    monkeypatch.setattr(server, "_cached_get_json", _pride_pages({
        ("plexDIA", None, "0"): _accs(1),
    }))
    assert server.search_extensive("plexDIA")["count"] == 1


def test_search_extensive_pages_until_a_short_page(monkeypatch):
    """A full page is never the end: only a short page proves exhaustion."""
    monkeypatch.setattr(server, "_cached_get_json", _pride_pages({
        ("proteomics", None, "0"): _accs(2, 1),
        ("proteomics", None, "1"): _accs(2, 3),
        ("proteomics", None, "2"): _accs(1, 5),
    }))
    r = server.search_extensive("proteomics", page_size=2)
    assert r["count"] == 5
    assert r["per_keyword"]["proteomics"]["status"].startswith("exhausted")
    # Every page is fetched once: a re-read page would inflate `hits` past `count`.
    assert r["per_keyword"]["proteomics"]["hits"] == 5


def test_full_page_then_empty_page_triggers_partitioned_retry(monkeypatch):
    """The historical PRIDE cap (#28): a full page then an empty one is ambiguous.

    It must not be reported as exhaustion. The year-partitioned retry recovers
    the records the plain walk could not reach.
    """
    year = server.date.today().year
    monkeypatch.setattr(server, "_cached_get_json", _pride_pages({
        ("proteomics", None, "0"): _accs(2, 1),
        ("proteomics", None, "1"): [],                       # looks like the end
        ("proteomics", f"submissionDate=={year}", "0"): _accs(1, 3),
    }))
    r = server.search_extensive("proteomics", page_size=2)
    assert r["per_keyword"]["proteomics"]["status"].startswith("partitioned")
    assert r["count"] == 3                                   # PXD000003 recovered
    assert "truncated" not in r


def test_a_partition_still_capped_is_reported_not_swallowed(monkeypatch):
    year = server.date.today().year
    monkeypatch.setattr(server, "_cached_get_json", _pride_pages({
        ("proteomics", None, "0"): _accs(2, 1),
        ("proteomics", None, "1"): [],
        ("proteomics", f"submissionDate=={year}", "0"): _accs(2, 3),
        ("proteomics", f"submissionDate=={year}", "1"): [],   # capped again
    }))
    r = server.search_extensive("proteomics", page_size=2)
    assert any(f"@{year}:suspected_cap" in t for t in r["truncated"])
    assert "NOT complete" in r["warning"]


def test_search_extensive_reports_a_lost_page_as_incomplete(monkeypatch):
    def fake(url, params=None, **kw):
        return None if "pride" in url else []
    monkeypatch.setattr(server, "_cached_get_json", fake)
    r = server.search_extensive("proteomics")
    assert any("INCOMPLETE" in e for e in r["errors"])


def test_search_extensive_rejects_empty_and_bad_input():
    assert "error" in server.search_extensive([])
    assert "error" in server.search_extensive(["x"], repository="nope")

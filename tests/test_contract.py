from __future__ import annotations

import json

import pytest

from tools.contract import load_terms, render_json, render_text, template_contract


def test_contract_orders_source_first_and_factor_last():
    c = template_contract(["ms-proteomics", "human"])
    names = [col.name for col in c.columns]
    assert names[0] == "source name"
    order = ["source name", "characteristics", "special", "comment", "factor value"]
    sections = [col.section for col in c.columns]
    assert sections == sorted(sections, key=order.index)


def test_contract_flags_required_and_multiple():
    c = template_contract(["ms-proteomics"])
    by = {col.name: col for col in c.columns}
    assert by["comment[label]"].requirement == "required"
    assert by["comment[modification parameters]"].multiple is True
    assert by["comment[label]"].multiple is False


def test_contract_reads_reserved_word_permissions_from_terms():
    c = template_contract(["ms-proteomics", "human"])
    by = {col.name: col for col in c.columns}
    assert by["characteristics[organism part]"].allow_not_available is True
    assert by["comment[label]"].allow_not_available is False


def test_contract_value_forms():
    c = template_contract(["ms-proteomics"])
    by = {col.name: col for col in c.columns}
    assert by["comment[precursor mass tolerance]"].value_form == "<number> ppm|Da"
    assert by["comment[fraction identifier]"].value_form == "integer"
    assert by["characteristics[organism]"].value_form == "bare value"
    assert by["comment[instrument]"].value_form == "NT=<name>;AC=<accession>"


def test_contract_fixes_technology_type_for_ms_unions():
    assert template_contract(["ms-proteomics", "human"]).technology_type == "proteomic profiling by mass spectrometry"
    assert template_contract(["affinity-proteomics"]).technology_type is None


def test_contract_unknown_template_names_known_ones():
    with pytest.raises(ValueError) as e:
        template_contract(["ms-proteomics", "not-a-template"])
    assert "not-a-template" in str(e.value)
    assert "ms-proteomics" in str(e.value)


def test_render_text_is_compact_and_lists_every_column():
    c = template_contract(["ms-proteomics", "human"])
    text = render_text(c)
    assert len(text) < 8000  # ~2k tokens
    for col in c.columns:
        assert col.name in text
    assert "factor value[...] last" in text


def test_render_json_roundtrips_names():
    c = template_contract(["ms-proteomics"])
    data = json.loads(render_json(c))
    assert data["templates"] == ["ms-proteomics"]
    assert [x["name"] for x in data["columns"]] == [col.name for col in c.columns]


def test_load_terms_keys_are_inner_names():
    terms = load_terms()
    assert "fraction identifier" in terms
    assert "label" in terms
    assert terms["organism part"]["allow_not_available"] is True


def test_cli_contract_prints_text(capsys):
    import sys

    from tools.cli import main
    argv = sys.argv
    sys.argv = ["tools", "contract", "-t", "ms-proteomics", "-t", "human"]
    try:
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 0
    finally:
        sys.argv = argv
    out = capsys.readouterr().out
    assert "CONTRACT for templates: ms-proteomics" in out
    assert "comment[label]" in out

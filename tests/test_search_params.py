"""Fixtures are trimmed from real deposited files (MaxQuant mqpar.xml / summary.txt /
parameters.txt, DIA-NN 2.5.1 log, PD 1.x .msf parameter rows) except fragger.params, which
follows MSFragger's own closed-search defaults."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

from tools.search_params import extract, name_by_mass, render_json, render_text, rows

FIX = Path(__file__).parent / "fixtures" / "search_params"


def mods(p):
    return {m.name: m for m in p.modifications}


def test_mqpar_mods_enzyme_tolerances_and_file_map():
    p = extract(FIX / "mqpar.xml")
    m = mods(p)
    assert m["Carbamidomethyl"].fixed and m["Carbamidomethyl"].residues == "C"
    assert m["Acetyl"].position == "Protein N-term" and m["Acetyl"].residues is None
    assert p.enzyme == "Trypsin/P"
    assert p.precursor_tolerance == "4.5 ppm"
    assert p.fragment_tolerance == "20 ppm"
    assert [e["file"] for e in p.file_map] == ["sample1.raw", "sample2.raw", "sample3.raw"]


def test_summary_txt_carries_the_mods_parameters_txt_does_not():
    p = extract(FIX / "summary.txt")
    assert set(mods(p)) == {"Carbamidomethyl", "Oxidation", "Acetyl"}
    assert p.enzyme == "Trypsin/P"
    assert p.file_map[0]["experiment"] == "A1"
    q = extract(FIX / "parameters.txt")
    assert not q.modifications
    assert any("summary.txt" in n for n in q.notes)
    assert q.fragment_tolerance is None and any("per analyzer" in n for n in q.notes)


def test_terminal_mod_renders_pp_never_ta():
    value = dict(rows(extract(FIX / "mqpar.xml")))["comment[modification parameters]"]
    acetyl = next(v for v in value.split(" | ") if v.startswith("NT=Acetyl"))
    assert acetyl == "NT=Acetyl;AC=UNIMOD:1;PP=Protein N-term;MT=Variable"


def test_diann_log_reads_the_applied_modification_lines():
    p = extract(FIX / "diann.log")
    m = mods(p)
    assert m["Carbamidomethyl"].fixed and m["Carbamidomethyl"].residues == "C"
    assert m["Acetyl"].position == "Protein N-term" and not m["Acetyl"].fixed
    assert p.fragment_tolerance is None and any("auto-optimised" in n for n in p.notes)


def test_diann_command_line_fallback_keeps_repeated_flags():
    p = extract(FIX / "diann_cmdline.log")
    m = mods(p)
    assert set(m) == {"Carbamidomethyl", "Oxidation", "Acetyl"}  # both --var-mod kept
    assert m["Acetyl"].accession == "UNIMOD:1"  # UniMod:1 spelling
    assert p.enzyme == "Trypsin/P"
    assert (p.precursor_tolerance, p.fragment_tolerance) == ("10 ppm", "20 ppm")


def test_fragger_params():
    p = extract(FIX / "fragger.params")
    m = mods(p)
    assert m["Carbamidomethyl"].fixed and m["Carbamidomethyl"].residues == "C"
    assert m["TMT6plex"].residues == "K"
    assert m["Acetyl"].position == "Protein N-term"
    assert m["Phospho"].residues == "S,T,Y"
    assert m["Gln->pyro-Glu"].residues == "Q" and m["Gln->pyro-Glu"].position == "Any N-term"
    assert p.enzyme == "Trypsin/P"  # stricttrypsin: KR, no proline rule
    assert (p.precursor_tolerance, p.fragment_tolerance) == ("20 ppm", "20 ppm")
    assert any("12.3456" in u for u in p.unmapped)


def test_mass_match_refuses_tmtpro_vs_itraq8_at_low_precision():
    assert name_by_mass("304.21") is None
    assert name_by_mass("304.2071") == "TMTpro"
    assert name_by_mass("304.2054") == "iTRAQ8plex"
    assert name_by_mass("15.9949") == "Oxidation"


def _pd1(tmp_path):
    """The PD 1.x layout: ProcessingNodeParameters rows as in a real Mascot + Sequest .msf."""
    path = tmp_path / "search.msf"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE ProcessingNodeParameters (ProcessingNodeNumber INT, ParameterName TEXT, "
                "FriendlyName TEXT, IntendedPurpose INT, ParameterValue TEXT, ValueDisplayString TEXT)")
    con.executemany("INSERT INTO ProcessingNodeParameters VALUES (?,?,?,?,?,?)", [
        (3, "FragmentTolerance", "Fragment Mass Tolerance", 3, "20 mmu", "20 mmu"),
        (3, "Enzyme", "Enzyme Name", 8, "Trypsin", "Trypsin"),
        (3, "PeptideTolerance", "Precursor Mass Tolerance", 2, "5 ppm", "5 ppm"),
        (3, "DynMod_1", "1. Dynamic Modification", 0, "Oxidation (M)", "Oxidation (M)"),
        (3, "StaticMod_1", "1. Static Modification", 0, "Carbamidomethyl (C)", "Carbamidomethyl (C)"),
        (4, "DynModification_1", "1. Dynamic Modification", 5, "11#45", "Oxidation / +15.995 Da (M)"),
        (4, "DynNTermModification", "N-Terminal Modification", 5, "1#3", "Acetyl / +42.011 Da (Protein N-Terminus)"),
    ])
    con.commit()
    con.close()
    return path


def test_pd1_msf(tmp_path):
    p = extract(_pd1(tmp_path))
    m = mods(p)
    assert len([x for x in p.modifications if x.name == "Oxidation"]) == 1  # two nodes, one mod
    assert m["Carbamidomethyl"].fixed
    assert m["Acetyl"].position == "Protein N-term" and m["Acetyl"].residues is None
    assert p.enzyme == "Trypsin"
    assert (p.precursor_tolerance, p.fragment_tolerance) == ("5 ppm", "0.02 Da")


def test_pd2_workflow_xml(tmp_path):
    path = tmp_path / "study.pdResult"
    xml = ('<WorkflowTree><WorkflowNode Name="Sequest HT">'
           '<ProcessingNodeParameter Name="StaticModification" IntendedPurpose="StaticModification" '
           'DisplayValue="Carbamidomethyl / +57.021 Da (C)"><Modification UnimodAccession="4"/></ProcessingNodeParameter>'
           '<ProcessingNodeParameter Name="DynModification_1" IntendedPurpose="DynamicModification" '
           'DisplayValue="Oxidation / +15.995 Da (M)"><Modification UnimodAccession="35"/></ProcessingNodeParameter>'
           '<ProcessingNodeParameter Name="StaticTerminal" IntendedPurpose="StaticTerminalModification" '
           'DisplayValue="TMT6plex / +229.163 Da (Any N-Terminus)"><Modification UnimodAccession="737"/></ProcessingNodeParameter>'
           '<ProcessingNodeParameter Name="Enzyme" IntendedPurpose="CleavageReagent" DisplayValue="Trypsin (Full)"/>'
           '</WorkflowNode></WorkflowTree>')
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE Workflows (WorkflowID INT, WorkflowXML TEXT)")
    con.execute("INSERT INTO Workflows VALUES (1, ?)", (xml,))
    con.commit()
    con.close()
    p = extract(path)
    m = mods(p)
    assert m["TMT6plex"].position == "Any N-term" and m["TMT6plex"].residues is None and m["TMT6plex"].fixed
    assert m["Oxidation"].accession == "UNIMOD:35"
    assert p.enzyme == "Trypsin"


REAL_MSF = Path("/Users/yperez/work/pia/src/test/resources/QExHF04458.msf")


@pytest.mark.skipif(not REAL_MSF.exists(), reason="real PD 1.x .msf not on this machine")
def test_real_pd1_msf():
    p = extract(REAL_MSF)
    assert {m.name for m in p.modifications} == {"Oxidation", "Carbamidomethyl"}


def test_json_carries_technical_rows():
    data = json.loads(render_json(extract(FIX / "mqpar.xml")))
    assert data["technical_rows"][0][0] == "comment[modification parameters]"


def test_text_lists_unmapped(tmp_path):
    text = render_text(extract(FIX / "fragger.params"))
    assert "# unmapped" in text and "12.3456" in text


def _cli(argv):
    from tools.cli import main
    old = sys.argv
    sys.argv = ["tools", "search-params", *argv]
    try:
        with pytest.raises(SystemExit) as e:
            main()
        return e.value.code
    finally:
        sys.argv = old


def test_cli_exit_codes(tmp_path, capsys):
    assert _cli([str(FIX / "mqpar.xml")]) == 0
    assert "comment[cleavage agent details]\tNT=Trypsin/P;AC=MS:1001313" in capsys.readouterr().out
    junk = tmp_path / "notes.txt"
    junk.write_text("nothing here\n")
    assert _cli([str(junk)]) == 2
    assert _cli([str(tmp_path / "missing.xml")]) == 2


def test_other_xml_and_params_files_are_refused_not_read_as_empty(tmp_path):
    pep = tmp_path / "interact.pep.xml"
    pep.write_text('<?xml version="1.0"?><msms_pipeline_analysis/>')
    comet = tmp_path / "comet.params"
    comet.write_text("# comet_version 2019.01\npeptide_mass_tolerance = 20\nadd_C_cysteine = 57.021464\n")
    for f in (pep, comet):
        with pytest.raises(ValueError):
            extract(f)


def test_corrupt_inputs_exit_2(tmp_path):
    partial = tmp_path / "big.msf"
    partial.write_bytes(b"SQLite format 3\0" + b"\0" * 50)  # a truncated download
    bomb = tmp_path / "mqpar.xml"
    bomb.write_text('<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]><MaxQuantParams>&a;</MaxQuantParams>')
    empty = tmp_path / "summary.txt"
    empty.write_text("")
    for f in (partial, bomb, empty):
        assert _cli([str(f)]) == 2


def test_unmapped_mod_listed_once_across_raw_files(tmp_path):
    f = tmp_path / "summary.txt"
    f.write_text("Raw file\tFixed modifications\tVariable modifications\n"
                 "a\tCarbamidomethyl (C)\tMadeUpMod (K)\nb\tCarbamidomethyl (C)\tMadeUpMod (K)\n")
    assert extract(f).unmapped == ["modification 'MadeUpMod (K)'"]


def test_fragger_pre_3x_enzyme_keys(tmp_path):
    f = tmp_path / "fragger.params"
    f.write_text("precursor_mass_lower = -10\nprecursor_mass_upper = 10\nsearch_enzyme_name = Trypsin\n"
                 "search_enzyme_cutafter = KR\nsearch_enzyme_butnotafter = P\n")
    assert extract(f).enzyme == "Trypsin"

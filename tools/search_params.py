"""Read the search settings out of a deposited search-engine file.

`comment[modification parameters]`, `comment[cleavage agent details]` and the two tolerance
columns describe what the search actually did, and the deposited search files are the only
primary source for that (paper Methods and PRIDE fields are downstream of it). Without a
reader, every annotation run re-derives a parser from prose; this does it once, the same way.

Supported, each checked against a real deposited file:
  MaxQuant    mqpar.xml, summary.txt, parameters.txt (MaxQuant 2.x writes no modifications
              into parameters.txt - use summary.txt or mqpar.xml)
  FragPipe    fragger.params
  DIA-NN      the log (report.log.txt, diann.log, *summary.log)
  PD          .msf / .pdResult / .pdStudy on local disk (SQLite): PD 1.x ProcessingNodeParameters
              and PD 2.x Workflows XML

It reports, it does not decide: a modification it cannot name with certainty goes to
`unmapped`, and a value that depends on the instrument (MaxQuant keeps one MS/MS tolerance per
analyzer) goes to `notes` for the annotator to settle. No network."""

from __future__ import annotations

import csv
import json
import re
import sqlite3
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from pathlib import Path

from tools.column_ontology_map import UNIMOD_KNOWN

# Beyond UNIMOD_KNOWN; labels checked against OLS 2026-09-23.
UNIMOD_EXTRA = {
    "UNIMOD:27": "Glu->pyro-Glu", "UNIMOD:28": "Gln->pyro-Glu", "UNIMOD:41": "Hex",
    "UNIMOD:43": "HexNAc", "UNIMOD:64": "Succinyl", "UNIMOD:121": "GG",
    "UNIMOD:765": "Met-loss", "UNIMOD:766": "Met-loss+Acetyl",
}
UNIMOD_NAMES = {**UNIMOD_KNOWN, **UNIMOD_EXTRA}
ACCESSION_BY_NAME = {name.lower(): acc for acc, name in UNIMOD_NAMES.items()}

# engine spellings -> UNIMOD label
ALIASES = {
    "deamidation": "Deamidated", "glygly": "GG", "gg": "GG", "carbamidomethylation": "Carbamidomethyl",
    "tmt": "TMT6plex", "tmt10plex": "TMT6plex", "tmt11plex": "TMT6plex", "tmt6plex": "TMT6plex",
    "tmtpro": "TMTpro", "tmtpro16plex": "TMTpro", "tmtpro18plex": "TMTpro", "tmt16plex": "TMTpro",
    "tmt18plex": "TMTpro", "itraq": "iTRAQ4plex", "phosphorylation": "Phospho", "acetylation": "Acetyl",
    "arg10": "Label:13C(6)15N(4)", "lys8": "Label:13C(6)15N(2)", "arg6": "Label:13C(6)",
    "lys6": "Label:13C(6)", "lys4": "Label:2H(4)",
}

# UNIMOD monoisotopic delta masses, for engines that log masses instead of names
MONO_MASS = {
    "Acetyl": 42.010565, "Carbamidomethyl": 57.021464, "Carbamyl": 43.005814, "Deamidated": 0.984016,
    "Phospho": 79.966331, "Propionamide": 71.037114, "Methyl": 14.015650, "Oxidation": 15.994915,
    "Dimethyl": 28.031300, "Trimethyl": 42.046950, "Formyl": 27.994915, "Label:13C(6)": 6.020129,
    "Label:13C(6)15N(2)": 8.014199, "Label:13C(6)15N(4)": 10.008269, "Label:2H(4)": 4.025107,
    "iTRAQ4plex": 144.102063, "iTRAQ8plex": 304.205360, "TMT6plex": 229.162932, "TMT2plex": 225.155833,
    "TMTpro": 304.207146, "Glu->pyro-Glu": -18.010565, "Gln->pyro-Glu": -17.026549, "GG": 114.042927,
    "Met-loss": -131.040485, "Met-loss+Acetyl": -89.029920, "HexNAc": 203.079373, "Hex": 162.052824,
    "Succinyl": 100.016044, "Nitro": 44.985078, "Cysteinyl": 119.004099,
}

# a modification whose specificity is part of its definition
IMPLIED_TARGET = {"Gln->pyro-Glu": ("Q", "Any N-term"), "Glu->pyro-Glu": ("E", "Any N-term")}

ENZYMES = {  # MS accession, OLS label (the NT= value); checked against OLS 2026-09-23
    "trypsin": ("MS:1001251", "Trypsin"), "trypsin/p": ("MS:1001313", "Trypsin/P"),
    "stricttrypsin": ("MS:1001313", "Trypsin/P"), "lys-c": ("MS:1001309", "Lys-C"),
    "lysc": ("MS:1001309", "Lys-C"), "chymotrypsin": ("MS:1001306", "Chymotrypsin"),
    "asp-n": ("MS:1001304", "Asp-N"), "aspn": ("MS:1001304", "Asp-N"),
    "arg-c": ("MS:1001303", "Arg-C"), "argc": ("MS:1001303", "Arg-C"),
    "lys-c/p": ("MS:1001310", "Lys-C/P"), "lysc/p": ("MS:1001310", "Lys-C/P"),
    "glu-c": ("MS:1001917", "glutamyl endopeptidase"), "gluc": ("MS:1001917", "glutamyl endopeptidase"),
}

POSITIONS = ("Protein N-term", "Protein C-term", "Any N-term", "Any C-term")


@dataclass
class Modification:
    name: str                 # UNIMOD label when known, else the engine's own spelling
    accession: str | None     # "UNIMOD:4"; None when unmapped
    fixed: bool
    residues: str | None      # "C", "S,T,Y" -> TA=
    position: str | None      # one of POSITIONS -> PP=
    source: str               # verbatim from the file

    def sdrf(self) -> str:
        parts = [f"NT={self.name}"]
        if self.accession:
            parts.append(f"AC={self.accession}")
        if self.residues:
            parts.append(f"TA={self.residues}")
        if self.position:
            parts.append(f"PP={self.position}")
        parts.append(f"MT={'Fixed' if self.fixed else 'Variable'}")
        return ";".join(parts)


@dataclass
class SearchParams:
    engine: str
    modifications: list[Modification] = field(default_factory=list)
    enzyme: str | None = None
    precursor_tolerance: str | None = None
    fragment_tolerance: str | None = None
    label: str | None = None
    channels: list[str] = field(default_factory=list)
    file_map: list[dict[str, str]] = field(default_factory=list)
    unmapped: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def add(self, mod: Modification | None) -> None:
        if mod is None:
            return
        key = (mod.name, mod.residues, mod.position, mod.fixed)
        if all((m.name, m.residues, m.position, m.fixed) != key for m in self.modifications):
            self.modifications.append(mod)
            if not mod.accession:
                self.unmapped.append(f"modification '{mod.source}'")


# --- names, masses, targets -------------------------------------------------------------

def unimod_name(name: str) -> tuple[str, str | None]:
    """Engine spelling -> (UNIMOD label, accession); the input back with None when unknown."""
    n = name.strip()
    m = re.match(r"^unimod:(\d+)$", n, re.IGNORECASE)
    if m:
        acc = f"UNIMOD:{m.group(1)}"
        return UNIMOD_NAMES.get(acc, n), acc
    label = ALIASES.get(n.lower(), n)
    acc = ACCESSION_BY_NAME.get(label.lower())
    return (UNIMOD_NAMES[acc], acc) if acc else (n, None)


def name_by_mass(text: str) -> str | None:
    """Match a logged delta mass; tolerance follows the decimals the file printed, and two
    candidates in range (TMTpro vs iTRAQ8plex at 2 decimals) is no match."""
    try:
        mass = float(text)
    except ValueError:
        return None
    decimals = len(text.split(".")[1]) if "." in text else 0
    tol = 0.5 * 10 ** -decimals + 1e-4
    hits = [n for n, m in MONO_MASS.items() if abs(m - mass) <= tol]
    return hits[0] if len(hits) == 1 else None


def residues_of(letters: str) -> str | None:
    aa = [c for c in letters.upper() if c.isalpha() and c != "X"]
    return ",".join(dict.fromkeys(aa)) or None


def make_mod(name: str, fixed: bool, source: str, residues: str | None = None,
             position: str | None = None, accession: str | None = None) -> Modification:
    label, acc = unimod_name(name)
    if accession and not acc:
        acc = accession
        label = UNIMOD_NAMES.get(acc, label)
    if label in IMPLIED_TARGET and not residues and not position:
        residues, position = IMPLIED_TARGET[label]
    return Modification(label, acc, fixed, residues, position, source)


def split_target(spec: str) -> tuple[str | None, str | None]:
    """'STY' -> ('S,T,Y', None); 'Protein N-term M' -> ('M', 'Protein N-term'); 'N-term' -> Any."""
    s = spec.strip()
    position = None
    m = re.search(r"(protein|any)?\s*([nc])-?\s*term(inus)?(al)?", s, re.IGNORECASE)
    if m:
        kind = "Protein" if (m.group(1) or "").lower() == "protein" else "Any"
        position = f"{kind} {m.group(2).upper()}-term"
        s = (s[:m.start()] + s[m.end():]).strip()
    return residues_of(s) if s else None, position


# --- MaxQuant ------------------------------------------------------------------------------

def mq_mod(text: str, fixed: bool) -> Modification | None:
    """'Oxidation (M)', 'Acetyl (Protein N-term)', 'Label:13C(6)', 'Gln->pyro-Glu'."""
    text = text.strip()
    if not text:
        return None
    m = re.match(r"^(.*\S)\s+\(([^()]*)\)$", text)  # the specificity is a space-separated trailing group
    name, spec = (m.group(1), m.group(2)) if m else (text, "")
    residues, position = split_target(spec) if spec else (None, None)
    return make_mod(name, fixed, text, residues, position)


def mq_isobaric(p: SearchParams, labels: list[tuple[str, str]]) -> None:
    """[(internalLabel, terminalLabel)] e.g. ('TMT10plex-Lys126C', 'TMT10plex-Nter126C')."""
    if not labels:
        return
    plex = labels[0][0].split("-")[0]
    p.label = plex
    for internal, _ in labels:
        m = re.search(r"(\d{3}[NC]?)$", internal)
        if m:
            tag = m.group(1)
            if plex.lower().startswith("tmt") and tag == "126C":
                tag = "126"
            p.channels.append(("TMT" if plex.lower().startswith("tmt") else "iTRAQ") + tag)
    p.add(make_mod(plex, True, f"{labels[0][0]} (isobaric label)", residues="K"))
    if labels[0][1]:
        p.add(make_mod(plex, True, f"{labels[0][1]} (isobaric label)", position="Any N-term"))


def mq_silac(p: SearchParams, states: list[str]) -> None:
    """labelMods per state, e.g. ['', 'Arg6;Lys4', 'Arg10;Lys8']."""
    heavy = [s for s in states if s.strip()]
    if not heavy:
        return
    p.label = "SILAC"
    p.notes.append(f"SILAC states (light first): {' | '.join(s or 'light' for s in states)}")
    for state in heavy:
        for lab in state.split(";"):
            residue = {"a": "R", "l": "K"}.get(lab[:1].lower())
            p.add(make_mod(lab, False, lab, residues=residue))


def mq_fragment_note(p: SearchParams, per_analyzer: dict[str, str]) -> None:
    if not per_analyzer:
        return
    if len(set(per_analyzer.values())) == 1:
        p.fragment_tolerance = next(iter(per_analyzer.values()))
        return
    listing = ", ".join(f"{k} {v}" for k, v in per_analyzer.items())
    p.notes.append(f"MS/MS tolerance is per analyzer ({listing}); use the one of the instrument's "
                   "MS2 analyzer for comment[fragment mass tolerance]")


def parse_mqpar(path: Path) -> SearchParams:
    root = _xml(path.read_text(encoding="utf-8-sig", errors="replace"))
    p = SearchParams("MaxQuant")
    for pg in root.iter("parameterGroup"):
        for tag, fixed in (("fixedModifications", True), ("variableModifications", False)):
            for s in pg.findall(f"{tag}/string"):
                p.add(mq_mod(s.text or "", fixed))
        enz = [s.text.strip() for s in pg.findall("enzymes/string") if s.text and s.text.strip()]
        if enz and not p.enzyme:
            p.enzyme = enz[0]
            if len(enz) > 1:
                p.notes.append(f"several enzymes: {', '.join(enz)} (one cleavage agent column per enzyme)")
        tol = pg.findtext("mainSearchTol")
        unit = (pg.findtext("searchTolInPpm") or "True").strip().lower()
        if tol and not p.precursor_tolerance:
            p.precursor_tolerance = f"{_num(tol)} {'ppm' if unit == 'true' else 'Da'}"
        iso = [(i.findtext("internalLabel") or "", i.findtext("terminalLabel") or "")
               for i in pg.findall("isobaricLabels/IsobaricLabelInfo")]
        if iso and not p.label:
            mq_isobaric(p, iso)
        states = [s.text or "" for s in pg.findall("labelMods/string")]
        if len(states) > 1 and not p.label:
            mq_silac(p, states)
    per_analyzer = {}
    for mp in root.iter("msmsParams"):
        name, tol = mp.findtext("Name"), mp.findtext("MatchTolerance")
        if name and tol:
            ppm = (mp.findtext("MatchToleranceInPpm") or "").strip().lower() == "true"
            per_analyzer[name] = f"{_num(tol)} {'ppm' if ppm else 'Da'}"
    mq_fragment_note(p, per_analyzer)
    files = [s.text or "" for s in root.findall("filePaths/string")]
    exps = [s.text or "" for s in root.findall("experiments/string")]
    fracs = [s.text or "" for s in root.findall("fractions/short")]
    for i, f in enumerate(files):
        entry = {"file": re.split(r"[\\/]", f)[-1]}
        if i < len(exps) and exps[i]:
            entry["experiment"] = exps[i]
        if i < len(fracs) and fracs[i] and fracs[i] != "32767":  # 32767 = no fractions
            entry["fraction"] = fracs[i]
        p.file_map.append(entry)
    return p


def _xml(text: str) -> ET.Element:
    """Parse a deposited XML document; a search config never needs a DTD, so refuse one
    rather than expand its entities."""
    if "<!DOCTYPE" in text[:4096] or "<!ENTITY" in text:
        raise ValueError("XML with a DTD/entity declarations is not a search config; refusing to parse it")
    return ET.fromstring(text)


def _num(text: str) -> str:
    v = float(text)
    return str(int(v)) if v.is_integer() else str(v)


def _tol(text: str) -> str | None:
    """'20 ppm', '0.5 Da', '20 mmu' -> SDRF '<number> ppm|Da'."""
    m = re.match(r"^\s*([\d.]+)\s*(ppm|da|mmu)\s*$", text or "", re.IGNORECASE)
    if not m:
        return None
    value, unit = float(m.group(1)), m.group(2).lower()
    if unit == "mmu":
        return f"{_num(str(value / 1000))} Da"
    return f"{_num(m.group(1))} {'ppm' if unit == 'ppm' else 'Da'}"


def parse_mq_table(path: Path) -> SearchParams:
    """summary.txt (one row per raw file + Total) or parameters.txt (Parameter/Value)."""
    p = SearchParams("MaxQuant")
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh, delimiter="\t"))
    if not rows:
        raise ValueError(f"'{path.name}' is empty")
    if rows and [c.strip() for c in rows[0][:2]] == ["Parameter", "Value"]:
        kv = {r[0].strip(): r[1].strip() for r in rows[1:] if len(r) >= 2}
        per_row = [kv]
    else:
        header = rows[0]
        per_row = [dict(zip(header, r)) for r in rows[1:] if r and r[0] not in ("Total", "")]
    for row in per_row:
        for key, fixed in (("Fixed modifications", True), ("Variable modifications", False)):
            for mod in (row.get(key) or "").split(";"):
                p.add(mq_mod(mod, fixed))
        enz = (row.get("Enzyme") or row.get("Enzymes") or "").split(";")[0].strip()
        p.enzyme = p.enzyme or enz or None
        if "Raw file" in row:
            entry = {"file": row["Raw file"]}
            for k in ("Experiment", "Fraction"):
                if row.get(k):
                    entry[k.lower()] = row[k]
            p.file_map.append(entry)
    first = per_row[0] if per_row else {}
    labels = [first.get(f"Labels{i}", "") for i in range(4) if f"Labels{i}" in first]
    if (first.get("Multiplicity") or "1") not in ("", "1") and labels:
        mq_silac(p, labels)
    per_analyzer = {m.group(1): t for k, v in first.items()
                    if (m := re.match(r"^MS/MS tol\. \((\w+)\)$", k)) and (t := _tol(v))}
    mq_fragment_note(p, per_analyzer)
    if path.name.lower() == "parameters.txt" and not p.modifications:
        p.notes.append("MaxQuant 2.x writes no fixed/variable modifications into parameters.txt; "
                       "read summary.txt or mqpar.xml from the same search")
    return p


# --- FragPipe -------------------------------------------------------------------------------

def fragger_target(spec: str) -> tuple[str | None, str | None]:
    """MSFragger sites: residues, '^' any residue, n/c peptide termini, [ ] protein termini."""
    position = None
    for marker, pos in (("[", "Protein N-term"), ("]", "Protein C-term"), ("n", "Any N-term"), ("c", "Any C-term")):
        if marker in spec:
            position = pos
            spec = spec.replace(marker, "")
    return residues_of(spec.replace("^", "")), position


def parse_fragger(path: Path) -> SearchParams:
    p = SearchParams("FragPipe")
    kv = {}
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = line.split("#", 1)[0].strip()
        if "=" in line:
            k, v = line.split("=", 1)
            kv[k.strip()] = v.strip()
    units = {"0": "Da", "1": "ppm"}
    lo, hi = kv.get("precursor_mass_lower"), kv.get("precursor_mass_upper")
    if lo and hi and float(lo) == -float(hi):
        p.precursor_tolerance = f"{_num(hi)} {units.get(kv.get('precursor_mass_units', '1'), 'ppm')}"
    elif kv.get("precursor_true_tolerance"):
        p.precursor_tolerance = (f"{_num(kv['precursor_true_tolerance'])} "
                                 f"{units.get(kv.get('precursor_true_units', '1'), 'ppm')}")
        p.notes.append(f"precursor window {lo}..{hi} is a mass-offset/open search; "
                       "reported precursor_true_tolerance instead")
    if kv.get("fragment_mass_tolerance"):
        p.fragment_tolerance = f"{_num(kv['fragment_mass_tolerance'])} {units.get(kv.get('fragment_mass_units', '1'), 'ppm')}"
    # search_enzyme_name_1/cut_1/nocut_1 since MSFragger 3.x; name/cutafter/butnotafter before
    enz = kv.get("search_enzyme_name_1") or kv.get("search_enzyme_name", "")
    cut = kv.get("search_enzyme_cut_1") or kv.get("search_enzyme_cutafter", "")
    nocut = kv.get("search_enzyme_nocut_1") if "search_enzyme_cut_1" in kv else kv.get("search_enzyme_butnotafter", "")
    if enz.lower() in ("trypsin", "stricttrypsin") and cut.upper() == "KR":
        enz = "Trypsin" if (nocut or "").upper() == "P" else "Trypsin/P"
    p.enzyme = enz or None
    for k in sorted(kv):
        if re.match(r"^variable_mod_\d+$", k) and kv[k]:
            parts = kv[k].split()
            if len(parts) >= 2:
                name = name_by_mass(parts[0])
                residues, position = fragger_target(parts[1])
                p.add(make_mod(name or f"{parts[0]} Da", False, kv[k], residues, position))
        m = re.match(r"^add_(Nterm|Cterm)_(peptide|protein)$|^add_([A-Z])_\w+$", k)
        if m and kv[k] and float(kv[k]) != 0:
            name = name_by_mass(kv[k])
            if m.group(3):
                residues, position = m.group(3), None
            else:
                residues = None
                position = f"{'Protein' if m.group(2) == 'protein' else 'Any'} {m.group(1)[0]}-term"
            p.add(make_mod(name or f"{kv[k]} Da", True, f"{k} = {kv[k]}", residues, position))
    return p


# --- DIA-NN -----------------------------------------------------------------------------------

def diann_target(spec: str) -> tuple[str | None, str | None]:
    """DIA-NN sites: residues, '*n' protein N-term, 'n' peptide N-term."""
    position = None
    if "*n" in spec:
        position, spec = "Protein N-term", spec.replace("*n", "")
    elif "n" in spec:
        position, spec = "Any N-term", spec.replace("n", "")
    return residues_of(spec), position


def parse_diann(path: Path) -> SearchParams:
    p = SearchParams("DIA-NN")
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    # every DIA-NN version prints the modifications it applied, whatever flags produced them
    for m in re.finditer(r"Modification (\S+) with mass delta (\S+) at (\S+) will be considered as (fixed|variable)", text):
        name, mass, site, kind = m.groups()
        residues, position = diann_target(site)
        _, acc = unimod_name(name)
        if not acc and (by_mass := name_by_mass(mass)):
            name = by_mass
        p.add(make_mod(name, kind == "fixed", m.group(0), residues, position))
    if not p.modifications:  # older logs: fall back to the command line
        flags = re.findall(r"--(fixed-mod|var-mod)\s+([^\s]+)", text)
        for flag, value in flags:
            parts = value.split(",")
            if len(parts) >= 3:
                residues, position = diann_target(parts[2])
                p.add(make_mod(parts[0], flag == "fixed-mod", f"--{flag} {value}", residues, position))
        if re.search(r"--unimod4\b", text):
            p.add(make_mod("Carbamidomethyl", True, "--unimod4", residues="C"))
    cut = re.search(r"--cut\s+(\S+)", text) or re.search(r"cuts at (\S+)", text)
    if cut:
        sites = cut.group(1).rstrip(",")
        if set(sites.split(",")) >= {"K*", "R*"}:
            p.enzyme = "Trypsin" if "!*P" in sites else "Trypsin/P"
        else:
            p.unmapped.append(f"cleavage rule '{sites}'")
    fixed_acc = re.search(r"Mass accuracy will be fixed to (\S+) \(MS2\) and (\S+) \(MS1\)", text)
    ms2 = re.search(r"--mass-acc\s+([\d.]+)", text)
    ms1 = re.search(r"--mass-acc-ms1\s+([\d.]+)", text)
    if fixed_acc:
        p.fragment_tolerance = f"{_num(str(round(float(fixed_acc.group(1)) * 1e6, 3)))} ppm"
        p.precursor_tolerance = f"{_num(str(round(float(fixed_acc.group(2)) * 1e6, 3)))} ppm"
    else:
        if ms2:
            p.fragment_tolerance = f"{_num(ms2.group(1))} ppm"
        if ms1:
            p.precursor_tolerance = f"{_num(ms1.group(1))} ppm"
    if not (fixed_acc or ms2 or ms1) and "automatically optimise the mass accuracy" in text:
        p.notes.append("mass accuracy was auto-optimised per run; the log carries no fixed tolerance")
    return p


# --- Proteome Discoverer -----------------------------------------------------------------------

PD_MOD_RE = re.compile(r"^\s*(?P<name>[^/(]+?)\s*(?:/\s*[-+][\d.]+\s*Da\s*)?\((?P<target>[^()]*)\)\s*$")


def pd_mod(display: str, fixed: bool, accession: str | None = None) -> Modification | None:
    """'Oxidation / +15.995 Da (M)', 'Carbamidomethyl (C)', 'Acetyl / +42.011 Da (Protein N-Terminus)'."""
    if not display or display.strip().lower() in ("none", "false"):
        return None
    m = PD_MOD_RE.match(display)
    if not m:
        return make_mod(display.strip(), fixed, display.strip(), accession=accession)
    residues, position = split_target(m.group("target").replace("Any", ""))
    return make_mod(m.group("name"), fixed, display.strip(), residues, position, accession)


def _pd_purpose(name: str) -> str | None:
    """Parameter name -> 'fixed' | 'variable' | 'enzyme' | 'precursor' | 'fragment'."""
    n = name.lower()
    if "mod" in n and ("static" in n or n.startswith("stat")):
        return "fixed"
    if "mod" in n and "dyn" in n:
        return "variable"
    if n in ("enzyme", "enzymename", "cleavagereagent") or "cleavagereagent" in n:
        return "enzyme"
    if "precursor" in n and "tol" in n or n == "peptidetolerance":
        return "precursor"
    if "fragment" in n and "tol" in n:
        return "fragment"
    return None


def _pd_apply(p: SearchParams, purpose: str, value: str, accession: str | None = None) -> None:
    if purpose in ("fixed", "variable"):
        p.add(pd_mod(value, purpose == "fixed", accession))
    elif purpose == "enzyme" and not p.enzyme:
        p.enzyme = re.sub(r"\s*\((full|semi|none)[^)]*\)\s*$", "", value, flags=re.IGNORECASE).strip() or None
    elif purpose == "precursor" and not p.precursor_tolerance:
        p.precursor_tolerance = _tol(value)
    elif purpose == "fragment" and not p.fragment_tolerance:
        p.fragment_tolerance = _tol(value)


def parse_pd(path: Path) -> SearchParams:
    p = SearchParams("Proteome Discoverer")
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        tables = {r[0].lower(): r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "processingnodeparameters" in tables:  # PD 1.x
            for name, display in con.execute(
                    "SELECT ParameterName, ValueDisplayString FROM ProcessingNodeParameters ORDER BY ProcessingNodeNumber"):
                purpose = _pd_purpose(name or "")
                if purpose:
                    _pd_apply(p, purpose, display or "")
        if "workflows" in tables:  # PD 2.x: one XML document per workflow
            cols = [r[1] for r in con.execute(f"PRAGMA table_info({tables['workflows']})")]
            for col in cols:
                for (blob,) in con.execute(f'SELECT "{col}" FROM "{tables["workflows"]}"'):
                    text = blob.decode("utf-8", "replace") if isinstance(blob, bytes) else blob
                    if isinstance(text, str) and text.lstrip().startswith("<"):
                        _pd_workflow_xml(p, text)
    finally:
        con.close()
    if not (p.modifications or p.enzyme):
        p.notes.append("no search parameters found in this PD file")
    return p


def _pd_workflow_xml(p: SearchParams, text: str) -> None:
    try:
        root = _xml(text)
    except (ET.ParseError, ValueError):
        return
    for el in root.iter():
        purpose_attr = el.get("IntendedPurpose") or ""
        name = el.get("Name") or el.get("ParameterName") or ""
        purpose = {"staticmodification": "fixed", "dynamicmodification": "variable",
                   "cleavagereagent": "enzyme"}.get(purpose_attr.lower())
        if purpose is None and "terminalmodification" in purpose_attr.lower():
            purpose = "fixed" if purpose_attr.lower().startswith("static") else "variable"
        purpose = purpose or _pd_purpose(name)
        if not purpose:
            continue
        value = el.get("DisplayValue") or el.get("ValueDisplayString") or el.get("Value") or (el.text or "").strip()
        inner = " ".join(ET.tostring(el, encoding="unicode").split())
        acc = re.search(r'UnimodAccession="(\d+)"', inner)
        _pd_apply(p, purpose, value, f"UNIMOD:{acc.group(1)}" if acc else None)


# --- entry ----------------------------------------------------------------------------------

def extract(path: str | Path) -> SearchParams:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"no such file: {path}")
    name = path.name.lower()
    with open(path, "rb") as fh:
        raw = fh.read(4096)
    head = raw.decode("utf-8-sig", "replace")
    # the content decides, not the extension: a PRIDE deposit also holds pep.xml, prot.xml, comet.params
    if raw.startswith(b"SQLite format 3\0") and name.endswith((".msf", ".pdresult", ".pdstudy")):
        p = parse_pd(path)
    elif "<MaxQuantParams" in head:
        p = parse_mqpar(path)
    elif "precursor_mass_lower" in head or "search_enzyme_name" in head:
        p = parse_fragger(path)
    elif name in ("summary.txt", "parameters.txt") and head.startswith(("Raw file\t", "Parameter\tValue")):
        p = parse_mq_table(path)
    elif "DIA-NN" in head or "diann" in head.lower():
        p = parse_diann(path)
    else:
        raise ValueError(f"unrecognised search file '{path.name}' (expected mqpar.xml, summary.txt, "
                         "parameters.txt, fragger.params, a DIA-NN log, or a PD .msf/.pdResult)")
    if p.enzyme and p.enzyme.lower() not in ENZYMES:
        p.unmapped.append(f"enzyme '{p.enzyme}'")
    return p


def rows(p: SearchParams) -> list[tuple[str, str]]:
    """technical.tsv rows ('|' separates the values of a multiple column)."""
    out = []
    if p.modifications:
        out.append(("comment[modification parameters]", " | ".join(m.sdrf() for m in p.modifications)))
    if p.enzyme:
        acc, label = ENZYMES.get(p.enzyme.lower(), (None, p.enzyme))
        out.append(("comment[cleavage agent details]", f"NT={label}" + (f";AC={acc}" if acc else "")))
    if p.precursor_tolerance:
        out.append(("comment[precursor mass tolerance]", p.precursor_tolerance))
    if p.fragment_tolerance:
        out.append(("comment[fragment mass tolerance]", p.fragment_tolerance))
    return out


def render_text(p: SearchParams) -> str:
    lines = [f"# {p.engine}", "column\tvalue"] + [f"{c}\t{v}" for c, v in rows(p)]
    if p.label:
        lines.append(f"# label: {p.label}" + (f"; channels: {', '.join(p.channels)}" if p.channels else ""))
    for title, items in (("unmapped - look these up, do not guess", p.unmapped), ("notes", p.notes)):
        if items:
            lines += [f"# {title}:"] + [f"#   {i}" for i in items]
    if p.file_map:
        lines.append(f"# file map ({len(p.file_map)} files):")
        lines += ["#   " + "\t".join(f"{k}={v}" for k, v in e.items()) for e in p.file_map]
    return "\n".join(lines)


def render_json(p: SearchParams) -> str:
    return json.dumps({**asdict(p), "technical_rows": rows(p)}, indent=1)

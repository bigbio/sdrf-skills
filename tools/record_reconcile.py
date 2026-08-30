"""Reconcile an SDRF's claims against the deposit record they were supposedly derived from.

A repository archive record has two kinds of metadata, and they are not equally reliable:

* **structured fields** — PRIDE's ``instruments``, ``diseases``, ``organismParts`` and
  ``organisms`` are dropdowns the submitter picked from at deposition time;
* **prose and file names** — the title, the sample- and data-processing protocols, and the
  names the submitter gave the deposited runs.

Annotating from the structured fields alone is the single most productive source of
*well-formed false claims* in SDRF: values that resolve in the right ontology, pass
``parse_sdrf`` and pass a repository's review gate while saying something the deposit itself
contradicts. In one 390-file batch this produced ``organism part = heart`` for epicardial
adipose tissue, human HeLa QC injections annotated as mouse heart, ``Trypsin`` for a study
that digested nothing, and a patient diagnosis on wild-type control runs.

This module treats the structured field as one witness rather than the record. Every check
returns a :class:`Finding` when the prose or the run names disagree, and ``None`` when they
do not. Nothing here decides what to write: an annotator's correct response to a finding is
usually a sentinel, and a sentinel is a result, not a failure.

Typical use::

    findings = reconcile(record, sdrf_rows)
    for f in findings:
        print(f)
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

BLOCKER = "blocker"   # the annotation contradicts the deposit
MAJOR = "major"       # the deposit supports something more specific or more complete
MINOR = "minor"       # worth knowing, does not misrepresent the data


@dataclass
class Finding:
    code: str
    severity: str
    column: str
    summary: str
    evidence: str = ""

    def __str__(self) -> str:
        tail = f"  [{self.evidence}]" if self.evidence else ""
        return f"{self.severity.upper():8s} {self.code} ({self.column}): {self.summary}{tail}"


# --------------------------------------------------------------------------- text handling
_PROSE_KEYS = ("title", "projectDescription", "sampleProcessingProtocol", "dataProcessingProtocol")
# Abbreviations that would otherwise split a sentence in the middle of a method.
_ABBR = [(r"(\d)\.(\d)", r"\1<DOT>\2"),
         (r"\b(e\.g|i\.e|vs|cf|approx|ca|Fig|no|et al)\.", r"\1<DOT>"),
         (r"(\d\s*°?\s*C)\.", r"\1<DOT>")]


def prose(record: dict, *keys: str) -> str:
    """The submitter's own free text, joined. Defaults to every prose field."""
    return " ".join(str(record.get(k) or "") for k in (keys or _PROSE_KEYS))


def sentences(text: str) -> list[str]:
    """Split into sentences without breaking on decimals, temperatures or 'e.g.'."""
    for pat, rep in _ABBR:
        text = re.sub(pat, rep, text, flags=re.IGNORECASE)
    return [s.replace("<DOT>", ".") for s in re.split(r"(?<=[.;])\s+", text) if s.strip()]


# --------------------------------------------------------------------------- organism
_SPECIES = [
    (r"\bmice\b|\bmouse\b|\bmurine\b|C57BL/6|BALB/c", "Mus musculus"),
    (r"\brats?\b|Sprague[- ]Dawley|Wistar|\bWKY\b", "Rattus norvegicus"),
    (r"\bpigs?\b|\bporcine\b|\bswine\b", "Sus scrofa"),
    (r"\bbovine\b|\bcows?\b|\bcattle\b", "Bos taurus"),
    (r"\brabbits?\b", "Oryctolagus cuniculus"),
    (r"\bzebrafish\b", "Danio rerio"),
    (r"\bhumans?\b|\bhuman-derived\b", "Homo sapiens"),
]


# A species name inside a reagent is not the study organism. "modified porcine trypsin",
# "bovine serum albumin" and "goat anti-rabbit IgG" are the common offenders.
_SPECIES_AS_REAGENT = re.compile(
    r"(porcine|bovine|rabbit|goat|sheep|horse|mouse|murine|human)\s+"
    r"(trypsin|serum albumin|BSA|serum|IgG|anti-|antibod|albumin|insulin|"
    r"gelatin|collagen|fibronectin|thrombin)", re.IGNORECASE)


def check_organism(record: dict, declared: str) -> Finding | None:
    """Flag a declared organism the prose never mentions while naming exactly one other.

    Deliberately conservative, and silent wherever it cannot judge:

    * the declared organism is outside this module's small species vocabulary — its absence
      from the text then carries no information, and reporting would flag every yeast,
      bacterial or plant deposit;
    * the prose names several species, or none;
    * the only species named appears in a reagent (``modified porcine trypsin``) rather than
      as the material under study.

    A species is mentioned in passing in almost every study — a human ortholog, a human
    search database, human disease context — so a contradiction is only reported when the
    declared species appears *nowhere* in the text.
    """
    declared_pat = next((pat for pat, sp in _SPECIES if sp == declared), None)
    if declared_pat is None:
        return None
    text = prose(record, "title", "projectDescription", "sampleProcessingProtocol")
    text = _SPECIES_AS_REAGENT.sub(" ", text)
    named = {sp for pat, sp in _SPECIES if re.search(pat, text, re.IGNORECASE)}
    if len(named) != 1:
        return None
    only = next(iter(named))
    if only == declared or declared.startswith(only.split()[0]):
        return None
    if re.search(declared_pat, text, re.IGNORECASE):
        return None
    return Finding("organism_contradicted", BLOCKER, "characteristics[organism]",
                   f"the record names only {only} and never {declared}",
                   f"declared {declared!r}")


# --------------------------------------------------------------------------- organism part
# Tissues a keyword sweep confuses with the organ it was searching for. Each pairing below
# was an observed false positive where the structured field said one thing and the title
# said another.
_TITLE_TISSUE = [
    ((r"\b(epicardial|pericardial|mediastinal|perivascular|subcutaneous|visceral)"
      r"\s+(adipose|fat)\b|\bEAT\b(?!\w)"), "adipose tissue"),
    (r"\baortic\s+(arch(es)?|aneurysm|root)\b|\babdominal aortic aneurysm\b", "aorta"),
    (r"\bcarotid\b.{0,20}\b(plaque|artery)\b", "carotid artery"),
    (r"\bpericardial fluid\b", "pericardial fluid"),
]
# Material with an anatomical *identity* but no anatomical *source*. An iPSC-derived
# cardiomyocyte was never part of a heart; a purified recombinant protein was never a tissue.
_NO_SOURCE = re.compile(
    r"\bhiPSC|\biPSC\b|induced pluripotent|\bhPSC\b|embryonic stem cell|immortali[sz]ed|"
    r"\bcell line\b|recombinant|purified\s+\w+\s+protein", re.IGNORECASE)
# Run-name tokens that name the material directly.
_RUN_TISSUE = [
    (r"(^|[_\-. ])aorta", "aorta"), (r"(^|[_\-. ])(carotid|plaque)", "carotid artery"),
    (r"(^|[_\-. ])(liver|hepat)", "liver"), (r"(^|[_\-. ])(kidney|renal)", "kidney"),
    (r"(^|[_\-. ])(brain|cortex|cerebell)", "brain"), (r"(^|[_\-. ])lung", "lung"),
    (r"(^|[_\-. ])spleen", "spleen"), (r"(^|[_\-. ])(skeletal|quadriceps|gastrocnem|soleus)",
                                       "skeletal muscle"),
    (r"(^|[_\-. ])(adipose|fat)([_\-. ]|$)", "adipose tissue"),
]
_CELL_LINE_RUN = re.compile(
    r"(^|[_\-. ])(hela|hct116|hek\s?-?293|hepg2|jurkat|k562|thp-?1|c2c12|h9c2|hl-?1)", re.IGNORECASE)


def check_organism_part(record: dict, declared: str,
                        run_names: Sequence[str] = ()) -> list[Finding]:
    """Flag an organism part the title, the material class or the run names contradict."""
    out: list[Finding] = []
    if not declared or declared.lower() in ("not available", "not applicable"):
        return out
    title = prose(record, "title", "projectDescription")
    for pat, what in _TITLE_TISSUE:
        if re.search(pat, title, re.IGNORECASE):
            m = re.search(pat, title, re.IGNORECASE)
            out.append(Finding("organism_part_contradicted", BLOCKER,
                               "characteristics[organism part]",
                               f"the title names {what}, but the annotation says {declared!r}",
                               m.group(0).strip()))
            break
    if _NO_SOURCE.search(title):
        m = _NO_SOURCE.search(title)
        out.append(Finding("organism_part_from_cultured_material", MAJOR,
                           "characteristics[organism part]",
                           "cultured, engineered or purified material has an anatomical "
                           "identity but no anatomical source",
                           m.group(0).strip()))
    lines = [n for n in run_names if _CELL_LINE_RUN.search(n)]
    if lines:
        out.append(Finding("run_names_name_a_cell_line", BLOCKER,
                           "characteristics[organism part]",
                           f"{len(lines)} of {len(run_names)} run names name an immortalised "
                           f"cell line, not the annotated tissue", lines[0]))
    for pat, what in _RUN_TISSUE:
        hits = [n for n in run_names if re.search(pat, n, re.IGNORECASE)]
        if hits and what.split()[0].lower() not in declared.lower():
            out.append(Finding("run_names_name_another_organ", BLOCKER,
                               "characteristics[organism part]",
                               f"{len(hits)} of {len(run_names)} run names name {what}, "
                               f"but every row says {declared!r}", hits[0]))
            break
    return out


# --------------------------------------------------------------------------- instrument
_INSTRUMENT_PROSE = [
    (r"Q[\s-]?Exactive\s*HF[\s-]?X|Q[\s-]?Exactive\s*HFX", "Q Exactive HF-X"),
    (r"Q[\s-]?Exactive\s*HF\b", "Q Exactive HF"),
    (r"Q[\s-]?Exactive\s*Plus|QExactivePlus", "Q Exactive Plus"),
    (r"Orbitrap\s*Exploris\s*480|Exploris\s*480", "Orbitrap Exploris 480"),
    (r"Orbitrap\s*Exploris\s*240|Exploris\s*240", "Orbitrap Exploris 240"),
    (r"Orbitrap\s*Astral\s*Zoom", "Orbitrap Astral Zoom"),
    (r"Orbitrap\s*Ascend", "Orbitrap Ascend"),
    (r"Orbitrap\s*Eclipse", "Orbitrap Eclipse"),
    (r"Fusion\s*Lumos", "Orbitrap Fusion Lumos"),
    (r"LTQ\s*Orbitrap\s*XL", "LTQ Orbitrap XL"),
    (r"Orbitrap\s*Velos\s*Pro", "Orbitrap Velos Pro"),
    (r"timsTOF\s*SCP", "timsTOF SCP"),
    (r"timsTOF\s*Pro\s*2", "timsTOF Pro 2"),
    (r"timsTOF\s*Pro", "timsTOF Pro"),
    (r"TripleTOF\s*6600", "TripleTOF 6600"),
    (r"TripleTOF\s*5600\s*\+", "TripleTOF 5600+"),
]
# A vendor's acquisition software writes its own container format. This is the one check in
# the module that needs no prose at all and admits no judgement.
_VENDOR_OF = [
    (r"orbitrap|q exactive|ltq|exploris|astral|velos|lcq|fusion|lumos|ascend", "thermo"),
    (r"timstof|maxis|impact|amazon|hct|ultraflex|autoflex", "bruker"),
    (r"triplet?of|qstar|q trap|x500|zenotof", "sciex"),
    (r"synapt|xevo", "waters"),
]
_VENDOR_EXT = {
    "thermo": (".raw", ".raw.zip"),
    "bruker": (".d", ".d.zip", ".d.7z", ".d.tar", ".baf", ".yep", ".tdf", ".fid"),
    "sciex": (".wiff", ".wiff.zip"),
    "waters": (".raw", ".raw.zip"),
}
_NEUTRAL_EXT = (".mzml", ".mzxml", ".mgf")


def _vendor(model: str) -> str | None:
    low = model.lower()
    return next((v for pat, v in _VENDOR_OF if re.search(pat, low)), None)


def check_instrument(record: dict, declared_model: str,
                     data_files: Sequence[str] = ()) -> list[Finding]:
    """Flag an instrument the prose contradicts, or that cannot have written the files."""
    out: list[Finding] = []
    text = prose(record)
    for pat, model in _INSTRUMENT_PROSE:
        if re.search(pat, text, re.IGNORECASE):
            if model.lower() != declared_model.lower():
                m = re.search(pat, text, re.IGNORECASE)
                out.append(Finding("instrument_contradicted", MAJOR, "comment[instrument]",
                                   f"the protocol names {model!r}, the annotation says "
                                   f"{declared_model!r}", m.group(0).strip()))
            break
    vendor = _vendor(declared_model)
    if vendor and data_files:
        allowed = set(_VENDOR_EXT[vendor]) | set(_NEUTRAL_EXT)
        every = sorted({e for exts in _VENDOR_EXT.values() for e in exts} | set(_NEUTRAL_EXT),
                       key=len, reverse=True)
        seen = {next((e for e in every if f.lower().endswith(e)), None) for f in data_files}
        seen.discard(None)
        if seen and not (seen & allowed):
            out.append(Finding("instrument_cannot_write_these_files", BLOCKER,
                               "comment[instrument]",
                               f"{declared_model} is a {vendor} instrument and cannot produce "
                               f"{'/'.join(sorted(seen))} files", data_files[0]))
    return out


# --------------------------------------------------------------------------- disease
_CONTROL_RUN = re.compile(
    r"(^|[_\-. ])(wt|ctrl|ctl|ctr|control|sham|scr|scramble|untreated|vehicle|veh|"
    r"naive|healthy|normal|nc|mock|blank|pbs|dmso|nonfailing|non-failing)([_\-. 0-9]|$)", re.IGNORECASE)
_CONTROL_PROSE = re.compile(
    r"\bsham(-operated)?\b|\bwild[- ]?type\b|\bcontrol (group|animals?|subjects?|samples?|arm|"
    r"mice|rats?)\b|\bhealthy (donors?|subjects?|controls?|volunteers?)\b|\bnon-?failing\b|"
    r"\bnormoxi|\bvehicle\b|\buntreated\b|\bplacebo\b|\bcontrols?\s*\(n\s*=", re.IGNORECASE)
# Registry buckets rather than diagnoses, and values that are not disease terms at all.
GENERIC_DISEASE = {"cardiovascular system disease", "heart disease", "cardiovascular disorder",
                   "disease", "cardiomyopathy", "cancer", "neoplasm"}
NON_DISEASE = {"inflammation", "mixed disorder as reaction to stress"}


def check_disease(record: dict, declared: str,
                  run_names: Sequence[str] = ()) -> list[Finding]:
    """Flag a project-level diagnosis asserted per sample, on controls, or not a disease."""
    out: list[Finding] = []
    value = (declared or "").strip().lower()
    if not value or value in ("not available", "not applicable", "normal"):
        return out
    if value in NON_DISEASE:
        out.append(Finding("not_a_disease_term", MAJOR, "characteristics[disease]",
                           f"{declared!r} has no term in a disease ontology "
                           f"(EFO/MONDO/DOID); it is a symptom or phenotype"))
    elif value in GENERIC_DISEASE:
        out.append(Finding("generic_disease_bucket", MINOR, "characteristics[disease]",
                           f"{declared!r} is a registry bucket, not a diagnosis; the record "
                           f"title usually names the actual condition"))
    controls = [n for n in run_names if _CONTROL_RUN.search(n)]
    if controls:
        out.append(Finding("disease_on_control_runs", BLOCKER, "characteristics[disease]",
                           f"{len(controls)} of {len(run_names)} run names mark a control arm, "
                           f"but every row asserts {declared!r}", controls[0]))
    elif run_names:
        m = _CONTROL_PROSE.search(prose(record))
        if m:
            out.append(Finding("disease_with_control_arm_in_record", MAJOR,
                               "characteristics[disease]",
                               f"the record describes a control arm, so {declared!r} cannot "
                               f"hold for every row", m.group(0).strip()))
    return out


# --------------------------------------------------------------------------- acquisition
_DDA_RUN = re.compile(r"(^|[_\-.])(dda|ida|ddalib|dda[_\-]?lib)([_\-.]|$)", re.IGNORECASE)
_DIA_RUN = re.compile(r"(^|[_\-.])(dia|swath|diapasef|udmse|hdmse|mse)([_\-.]|$)", re.IGNORECASE)
_PRM_RUN = re.compile(r"(^|[_\-.])(prm|srm|mrm)\d*([_\-.]|$)", re.IGNORECASE)


def acquisition_from_run_name(run_name: str) -> str | None:
    """The mode the submitter encoded in the run's own name, if any."""
    if _PRM_RUN.search(run_name):
        return "Parallel reaction monitoring"
    dda, dia = _DDA_RUN.search(run_name), _DIA_RUN.search(run_name)
    if dda and not dia:
        return "Data-dependent acquisition"
    if dia and not dda:
        return "Data-independent acquisition"
    return None


def check_acquisition(declared_per_row: Sequence[str],
                      run_names: Sequence[str]) -> list[Finding]:
    """Flag rows whose acquisition mode their own run name contradicts.

    A DIA deposit normally also contains the DDA runs that built its spectral library. One
    value for the whole file mislabels them.
    """
    bad: list[tuple[str, str, str]] = []
    for value, name in zip(declared_per_row, run_names):
        from_name = acquisition_from_run_name(name)
        written = re.sub(r"^NT=|;AC=.*$", "", value or "")
        if from_name and written and from_name.lower() != written.lower():
            bad.append((name, written, from_name))
    if not bad:
        return []
    name, written, expected = bad[0]
    return [Finding("acquisition_contradicted_by_run_name", BLOCKER,
                    "comment[proteomics data acquisition method]",
                    f"{len(bad)} of {len(run_names)} rows say {written!r} while the run name "
                    f"says {expected!r}", name)]


# --------------------------------------------------------------------------- cleavage agent
_DIGEST_CUE = re.compile(
    r"digest\w*|proteolytic|in-?gel|in-?solution|FASP|SP3|1\s*:\s*\d+\s*\(?w/w|"
    r"enzyme[- ]to[- ]protein|overnight at 37|incubated with|"
    r"enzyme\s+(specificity|was|used)|specificity\s+(was|of)|enzymes?\s+such as|"
    r"as the (proteolytic )?enzyme|cleav\w+\s+(agent|specificity)", re.IGNORECASE)
# The protease name is the analyte, a proteasome activity readout, an inhibitor or a
# contaminant-database entry rather than the reagent that produced the peptides.
_PROTEASE_ROLE_EXCLUDE = re.compile(
    r"chymotrypsin-?like|trypsin-?like|caspase-?like|presence of|\blevels\b|inhibitor|"
    r"\bactivity\b|cleavage sites by|contaminant|\bcRAP\b|western|elisa|immunoblot|"
    r"abundance of", re.IGNORECASE)
_PROTEASES = [
    (r"\btryps(in|inis|iniz)\w*\b|\btryptic\b", "Trypsin"),
    (r"\blys\s*-?\s*c\b|lysyl\s*endopeptidase|endoproteinase\s+lys-?c", "Lys-C"),
    (r"\bchymotryps\w*\b", "Chymotrypsin"),
    (r"\bglu\s*-?\s*c\b|endoproteinase\s+glu-?c|\bv8\s+protease", "glutamyl endopeptidase"),
    (r"\basp\s*-?\s*n\b", "Asp-N"),
    (r"\barg\s*-?\s*c\b", "Arg-C"),
    (r"lysargin[ae]se", "LysargiNase"),
]


def proteases_in_record(record: dict) -> list[str]:
    """Proteases the record names as *digest reagents*, in the module's fixed order.

    Evidence is scoped to the sentence. A character window bleeds across boundaries — so
    "…responsible for digestion. Western analysis shows that trypsin in plasma is elevated…"
    reads as a digest — and truncates sequential digests, where the second enzyme sits far
    from the single "digested with".
    """
    found: list[str] = []
    for sentence in sentences(prose(record)):
        if not _DIGEST_CUE.search(sentence) or _PROTEASE_ROLE_EXCLUDE.search(sentence):
            continue
        for pat, label in _PROTEASES:
            if label not in found and re.search(pat, sentence, re.IGNORECASE):
                found.append(label)
    return found


def check_cleavage_agent(record: dict, declared: Iterable[str]) -> list[Finding]:
    """Flag a protease the record does not support, or a co-digest reduced to one enzyme."""
    written = [re.sub(r"^NT=|;AC=.*$", "", d or "").strip() for d in declared]
    written = [w for w in written if w]
    supported = proteases_in_record(record)
    out: list[Finding] = []
    if not supported:
        if written:
            out.append(Finding("cleavage_agent_unsupported", BLOCKER,
                               "comment[cleavage agent details]",
                               f"the record never names {', '.join(written)} as a digest "
                               f"reagent; the annotation may have matched the enzyme in "
                               f"another role"))
        return out
    for w in written:
        if w.lower() not in {s.lower() for s in supported}:
            out.append(Finding("cleavage_agent_contradicted", BLOCKER,
                               "comment[cleavage agent details]",
                               f"the annotation says {w!r} but the record's digest names "
                               f"{', '.join(supported)}"))
    missing = [s for s in supported if s.lower() not in {w.lower() for w in written}]
    if missing and written:
        out.append(Finding("cleavage_agent_incomplete", MAJOR,
                           "comment[cleavage agent details]",
                           f"the record names a {'/'.join(supported)} digest but only "
                           f"{', '.join(written)} is declared",
                           f"missing: {', '.join(missing)}"))
    return out


# --------------------------------------------------------------------------- labelling
_LABELLED = re.compile(
    r"\bSILAC\b|\bTMT\s?pro\b|\bTMT\s?\d*\s?-?\s?plex\b|\bTMT\b\s*(label|reagent|tag|method)|"
    r"\biTRAQ\b|isobaric\s+(label|tag|mass tag)|tandem mass tag|"
    r"reductive\s+d[ei]methylation|d[ei]methyl\s+label|dimethyl\s+labell?ing|"
    r"\bICAT\b|OxICAT|\bmTRAQ\b|MS1[- ]based isotope label|reporter ion (ms2|ms3|quantif)|"
    r"heavy lysine|\bLys8\b|\bArg10\b|1[45]N[- ]label|\b18O\b\s*(water|label)", re.IGNORECASE)
_LABELLED_QUANT = re.compile(
    r"\bSILAC\b|\bTMT\b|\biTRAQ\b|dimethyl|\bICAT\b|isobaric|tandem mass tag|"
    r"MS1 based isotope label", re.IGNORECASE)


def check_labelled(record: dict, declared_label: str = "") -> Finding | None:
    """Flag a labelled deposit annotated as label-free.

    A labelled run carries several samples in one file. Annotating it label-free asserts a
    one-to-one run-to-sample relation the data does not have, which is why this is a blocker
    even though every value involved is a valid CV term.
    """
    if declared_label and "label free" not in declared_label.lower():
        return None
    for method in record.get("quantificationMethods") or []:
        if _LABELLED_QUANT.search(str(method)):
            return Finding("labelled_annotated_as_label_free", BLOCKER, "comment[label]",
                           "the record registers a labelled quantification method",
                           f"quantificationMethods = {method!r}")
    match = _LABELLED.search(prose(record))
    if match:
        return Finding("labelled_annotated_as_label_free", BLOCKER, "comment[label]",
                       "the protocol describes isotope or isobaric labelling",
                       match.group(0))
    return None


# --------------------------------------------------------------------------- entry point
@dataclass
class ReconcileReport:
    accession: str = ""
    findings: list[Finding] = field(default_factory=list)

    @property
    def blockers(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == BLOCKER]

    @property
    def clean(self) -> bool:
        return not self.findings

    def render(self) -> str:
        if self.clean:
            return (f"{self.accession or 'SDRF'}: every annotated value agrees with the "
                    f"deposit record.")
        head = (f"{self.accession or 'SDRF'}: {len(self.findings)} value(s) disagree with the "
                f"deposit record:")
        order = {BLOCKER: 0, MAJOR: 1, MINOR: 2}
        return "\n".join([head, ""] +
                         [f"  {f}" for f in sorted(self.findings, key=lambda f: order[f.severity])])


def reconcile(record: dict, rows: Sequence[dict], accession: str = "") -> ReconcileReport:
    """Reconcile an SDRF's values against the deposit record.

    ``record`` is the archive's project metadata (PRIDE's ``/projects/{acc}`` shape or the
    search record; only the prose keys and ``quantificationMethods`` are read). ``rows`` are
    the SDRF data rows as dictionaries. Repeated columns should be pre-collapsed by the
    caller, since a plain ``csv.DictReader`` keeps only the last value for a repeated name.
    """
    report = ReconcileReport(accession=accession)
    if not rows:
        return report

    def col(name: str) -> list[str]:
        return [str(r.get(name) or "") for r in rows]

    runs = [r.get("assay name") or r.get("comment[data file]") or "" for r in rows]
    files = col("comment[data file]")

    organism = next((v for v in col("characteristics[organism]") if v), "")
    if organism:
        found = check_organism(record, organism)
        if found:
            report.findings.append(found)

    part = next((v for v in col("characteristics[organism part]") if v), "")
    report.findings += check_organism_part(record, part, runs)

    instrument = next((v for v in col("comment[instrument]") if v), "")
    if instrument:
        model = re.sub(r"^NT=|;AC=.*$", "", instrument).strip()
        report.findings += check_instrument(record, model, files)

    disease = next((v for v in col("characteristics[disease]") if v), "")
    report.findings += check_disease(record, disease, runs)

    report.findings += check_acquisition(
        col("comment[proteomics data acquisition method]"), runs)

    cleavage = [v for v in col("comment[cleavage agent details]") if v]
    if cleavage:
        report.findings += check_cleavage_agent(record, set(cleavage))

    label = next((v for v in col("comment[label]") if v), "")
    found = check_labelled(record, label)
    if found:
        report.findings.append(found)

    return report

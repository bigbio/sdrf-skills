#!/usr/bin/env python3
"""
sdrf_skills_benchmark.py — repeatable scorecard for the sdrf-skills benchmark.

Two data domains:
  (1) FILE-based metrics  — fully standalone. Diff a delivered SDRF against a
      reference, compute coverage / fill / reserved-word / hallucination /
      validation. Run anywhere with pandas + (optionally) the `sdrf` conda env
      for parse_sdrf and OLS resolution.
  (2) SESSION-based metrics — cost, tokens, verification calls, execution
      economy. These live in the Claude Science session DB and are pulled with
      host.query() inside a `repl` cell (see benchmark_protocol.md §4 for the
      SQL). Pass the extracted dict into session_metrics() to fold them in.

Usage (file metrics for one arm):
    python sdrf_skills_benchmark.py --sdrf <ACCESSION>_with_skills.sdrf.tsv \
        --templates ms-proteomics human immunopeptidomics \
        --template-dir /path/to/sdrf-templates \
        --reference <ACCESSION>_reference.sdrf.tsv \
        --deposited-files pride_files.json \
        --out scorecard_with.json

    # For TMT/iTRAQ (multiple rows per raw file), key the curated diff on
    # (data file + channel) so channels are not cross-joined:
    #   --key 'comment[data file]' 'comment[label]'

Compare two arms:
    python sdrf_skills_benchmark.py --compare scorecard_with.json scorecard_without.json \
        --out comparison.csv
"""
import argparse, json, os, re, subprocess, sys
from collections import OrderedDict

RESERVED_OK = {"not available", "not applicable"}
RESERVED_BAD = {"", "na", "n/a", "nan", "unknown", "null", "none", "todo"}
ACC_RE = re.compile(r'\b([A-Z][A-Za-z]+):\d+\b')            # CURIE, e.g. MS:1000133
NT_RE  = re.compile(r'NT=([^;]+)')
AC_RE  = re.compile(r'AC=([^;]+)')
# --- Family E pricing model (cross-agent) ------------------------------------
# A pricing profile decouples the cost metric from any one agent platform. Each
# profile supplies (a) `weights`: price ratios of each token class vs the base
# fresh-input rate, and (b) `fields`: a map from the four canonical token
# concepts to the field names in THAT platform's usage/session record. Set a
# field to None when the platform has no such concept (e.g. OpenAI has no
# cache-WRITE premium). `session_metrics(..., pricing_profile=...)` accepts a
# profile NAME (looked up here), a dict, or a path to a JSON file.
#
# IMPORTANT: cost numbers are only comparable WITHIN one platform — different
# models, cache semantics, and price tables mean Family E is never a cross-agent
# leaderboard. The FILE metrics (B/D/A1/A4/A5) are the apples-to-apples signal.
PRICING_PROFILES = {
    "anthropic": {
        "weights": {"read": 0.10, "fresh": 1.0, "write": 1.25, "output": 5.0},
        "fields": {"read": "cache_read_tokens", "write": "cache_write_tokens",
                   "input_total": "input_tokens", "output": "output_tokens",
                   "total_cost": "total_cost"},
        "note": "Claude Science frames-row schema. Weights are price ratios vs "
                "base input (5-min cache: read 0.1x, write 1.25x, output 5x).",
    },
    "openai": {
        # STUB — illustrative GPT-class ratios; verify against current OpenAI
        # pricing before relying on the dollar split. OpenAI caches
        # automatically with no separate write premium, so write is None.
        "weights": {"read": 0.25, "fresh": 1.0, "write": 0.0, "output": 4.0},
        "fields": {"read": "cached_tokens", "write": None,
                   "input_total": "prompt_tokens", "output": "completion_tokens",
                   "total_cost": "total_cost"},
        "note": "STUB for OpenAI/Codex. Usage schema: prompt_tokens, "
                "completion_tokens, prompt_tokens_details.cached_tokens. No "
                "cache-write premium. Populate weights + total_cost from the "
                "run's own usage record before use.",
    },
    "generic": {
        "weights": {"read": 1.0, "fresh": 1.0, "write": 1.0, "output": 1.0},
        "fields": {"read": "cache_read_tokens", "write": "cache_write_tokens",
                   "input_total": "input_tokens", "output": "output_tokens",
                   "total_cost": "total_cost"},
        "note": "Unweighted token counts. Use when price ratios are unknown; "
                "cost_by_type then reflects raw token share, not dollars.",
    },
}

# Back-compat alias: the original module-level constant still resolves.
TOKEN_WEIGHTS = PRICING_PROFILES["anthropic"]["weights"]


def resolve_pricing_profile(profile):
    """Accept a profile NAME, a profile DICT, or a PATH to a JSON profile.
    Returns a normalised {weights, fields, note} dict."""
    if profile is None:
        profile = "anthropic"
    if isinstance(profile, str):
        if profile in PRICING_PROFILES:
            return PRICING_PROFILES[profile]
        if os.path.exists(profile):
            with open(profile) as fh:
                return json.load(fh)
        raise ValueError(f"unknown pricing profile '{profile}'; "
                         f"choices: {sorted(PRICING_PROFILES)} or a JSON path")
    if isinstance(profile, dict):
        return profile
    raise TypeError("pricing_profile must be a name, dict, or JSON path")


# ----------------------------------------------------------------------------- IO
def read_sdrf(path):
    import pandas as pd
    df = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)
    # de-duplicate repeated headers (e.g. 3x comment[sdrf template])
    seen = {}; cols = []
    for c in df.columns:
        seen[c] = seen.get(c, 0) + 1
        cols.append(c if seen[c] == 1 else f"{c}.{seen[c]}")
    df.columns = cols
    return df


def load_template_columns(template_dir, templates):
    """Return {column_name: max_requirement} across the inheritance union.
    template_dir holds <name>/<version>/*.yaml or <name>.yaml."""
    import yaml
    rank = {"required": 3, "recommended": 2, "optional": 1}
    union = OrderedDict()
    for t in templates:
        path = _find_template_yaml(template_dir, t)
        if not path:
            continue
        d = yaml.safe_load(open(path))
        for c in d.get("columns", []):
            n, r = c["name"], c.get("requirement", "optional")
            if n not in union or rank[r] > rank[union[n]]:
                union[n] = r
    return union


def _find_template_yaml(template_dir, name):
    # accept <dir>/<name>.yaml, <dir>/<name>/<version>/*.yaml, newest version
    direct = os.path.join(template_dir, f"{name}.yaml")
    if os.path.exists(direct):
        return direct
    base = os.path.join(template_dir, name)
    if os.path.isdir(base):
        versions = sorted(os.listdir(base), reverse=True)
        for v in versions:
            vf = os.path.join(base, v)
            if os.path.isdir(vf):
                yamls = [f for f in os.listdir(vf) if f.endswith(".yaml")]
                if yamls:
                    return os.path.join(vf, yamls[0])
    return None


# --------------------------------------------------------------- FILE metrics (B,D,A5)
def coverage(df, template_union):
    """B6: present/defined per requirement tier."""
    present = set(c.split(".")[0] for c in df.columns)
    tiers = {"required": [0, 0], "recommended": [0, 0], "optional": [0, 0]}
    for col, req in template_union.items():
        tiers[req][1] += 1
        if col in present:
            tiers[req][0] += 1
    return {k: {"present": v[0], "defined": v[1],
                "pct": round(100 * v[0] / v[1], 1) if v[1] else None}
            for k, v in tiers.items()}


def fill_rate(df):
    """B7: non-'not available' applicable cells / applicable cells (characteristics+comment)."""
    cols = [c for c in df.columns if c.startswith(("characteristics[", "comment["))]
    total = filled = 0
    for c in cols:
        for v in df[c]:
            total += 1
            if v.strip().lower() not in RESERVED_OK and v.strip() != "":
                filled += 1
    return {"filled": filled, "applicable": total,
            "pct": round(100 * filled / total, 1) if total else None}


def reserved_word_discipline(df):
    """B8: count illegal blanks where a value/reserved word is expected."""
    bad = 0; examples = []
    for c in df.columns:
        if not c.startswith(("characteristics[", "comment[")):
            continue
        for v in df[c]:
            s = v.strip().lower()
            if s in RESERVED_BAD:
                bad += 1
                if len(examples) < 8:
                    examples.append((c, repr(v)))
    return {"illegal_blanks": bad, "examples": examples}


def ontology_breadth(df):
    """B9: distinct ontology prefixes used."""
    onts = set()
    for c in df.columns:
        for v in df[c]:
            for m in ACC_RE.finditer(v):
                onts.add(m.group(1))
    return {"n_ontologies": len(onts), "ontologies": sorted(onts)}


def nt_ac_consistency(df):
    """A3(a): rows where NT= label and AC= accession are both present (internal pairing)."""
    paired = mismatched = 0
    for c in df.columns:
        for v in df[c]:
            if "NT=" in v and "AC=" in v:
                paired += 1
    return {"nt_ac_paired_cells": paired}


def row_structure_fidelity(df, deposited_files_json):
    """A5: precision/recall of delivered rows vs deposited run list."""
    if not deposited_files_json or not os.path.exists(deposited_files_json):
        return None
    raw = json.load(open(deposited_files_json))
    # accept either a list of names or PRIDE file objects
    names = set()
    items = raw if isinstance(raw, list) else raw.get("files", raw.get("_embedded", {}).get("files", []))
    for it in items:
        fn = it if isinstance(it, str) else (it.get("fileName") or it.get("value") or "")
        if fn.lower().endswith(".mzml"):
            names.add(os.path.basename(fn))
    if not names:
        return {"note": "no mzML names parsed from deposited file list"}
    dcol = [c for c in df.columns if c.split(".")[0] == "comment[data file]"]
    delivered = set(os.path.basename(x) for x in df[dcol[0]]) if dcol else set()
    tp = len(delivered & names)
    return {"deposited": len(names), "delivered": len(delivered),
            "matched": tp,
            "precision": round(tp / len(delivered), 4) if delivered else None,
            "recall": round(tp / len(names), 4) if names else None}


# --------------------------------------------------------------- A4 hallucination (needs OLS)
def hallucinated_accessions(df, resolver=None, limit=None):
    """A4: fraction of accessions that fail to resolve. resolver(curie)->bool.
    If resolver is None, only collects the accession inventory (resolve later)."""
    accs = {}
    for c in df.columns:
        for v in df[c]:
            for m in ACC_RE.finditer(v):
                cur = m.group(0)
                accs[cur] = accs.get(cur, 0) + 1
    inv = sorted(accs)
    if resolver is None:
        return {"n_distinct_accessions": len(inv), "accessions": inv, "resolved": None}
    checked = inv[:limit] if limit else inv
    bad = [a for a in checked if not resolver(a)]
    return {"n_distinct_accessions": len(inv), "n_checked": len(checked),
            "n_unresolved": len(bad), "unresolved": bad,
            "hallucination_rate": round(len(bad) / len(checked), 4) if checked else 0.0}


# --------------------------------------------------------------- D validation
def validate(sdrf_path, templates, cache_only=True):
    """D14: run parse_sdrf validate-sdrf with the given templates via -t."""
    cmd = ["parse_sdrf", "validate-sdrf", "-s", sdrf_path]
    for t in templates:
        cmd += ["-t", t]
    if cache_only:
        cmd += ["--use_ols_cache_only"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        out = (p.stdout + p.stderr)
    except Exception as e:
        return {"error": str(e)}
    passed = "Everything seems to be fine" in out
    errs = len(re.findall(r'(?im)^ERROR', out))
    warns = len(re.findall(r'(?i)warning', out))
    return {"templates": templates, "cache_only": cache_only,
            "pass": passed, "error_lines": errs, "warning_lines": warns}


def template_self_declaration(df, expected_templates=None):
    """D16 (structural): does the file declare its own templates via
    comment[sdrf template]?  parse_sdrf silently defaults to a template when -t
    is omitted and never reads comment[sdrf template], so a validation-run test
    is meaningless — self-sufficiency is a STRUCTURAL property: a downstream
    consumer can only know which templates to validate against if the file
    declares them itself.  Returns declared count + which templates + coverage
    of the expected set + a self_sufficient boolean."""
    cols = [c for c in df.columns if c.split(".")[0] == "comment[sdrf template]"]
    declared = []
    for c in cols:
        # take the first non-empty value in the column
        vals = [v for v in df[c] if str(v).strip()]
        if not vals:
            continue
        v = str(vals[0])
        m = re.search(r'NT=([\w-]+)', v) or re.match(r'\s*([\w-]+)\s+v', v)
        declared.append(m.group(1) if m else v.strip())
    declared = [d for d in declared if d]
    result = {"n_template_declarations": len(cols),
              "declared_templates": declared,
              "self_sufficient": len(declared) > 0}
    if expected_templates:
        exp = set(expected_templates)
        result["expected"] = sorted(exp)
        result["declared_of_expected"] = sorted(exp & set(declared))
        result["coverage_pct"] = round(100 * len(exp & set(declared)) / len(exp), 1) if exp else None
    return result


# --------------------------------------------------------------- curated diff (A1/A2)
def curated_diff(df, curated_df, key="comment[data file]"):
    """A1: per-column agreement on the shared row key; divergences for triage.

    `key` may be a single column name (str) or a list of column names forming a
    COMPOSITE key. A composite key is required whenever the data-file column is
    not unique per row — e.g. TMT/iTRAQ multiplexing, where each raw file yields
    one row per reporter channel. Joining on the data-file column alone then
    cross-joins the channels (an N-channel run fans out to N*N rows), silently
    inflating `n_matched_rows` and diluting every agreement percentage.
    Passing key=["comment[data file]", "comment[label]"] keys on
    (raw file + channel) and restores a 1:1 row match. Columns matching the
    basename-column names (data file / source name) are compared on basename;
    all other key parts on their raw normalised value. Backward-compatible: a
    single-column key reproduces the original behaviour exactly.
    """
    import pandas as pd
    def norm(s):  # normalise for comparison
        return re.sub(r'\s+', ' ', str(s).strip().lower())
    keys = [key] if isinstance(key, str) else list(key)
    basename_cols = {"comment[data file]", "source name"}

    def build_key(frame):
        cols_used = []
        parts = []
        for k in keys:
            hit = [c for c in frame.columns if c.split(".")[0] == k]
            if not hit:
                return None, k
            col = hit[0]; cols_used.append(k)
            if k in basename_cols:
                parts.append(frame[col].map(lambda x: os.path.basename(str(x))))
            else:
                parts.append(frame[col].map(norm))
        return parts, None

    d = df.copy(); g = curated_df.copy()
    pd_parts, missing_d = build_key(d)
    pg_parts, missing_g = build_key(g)
    if missing_d or missing_g:
        return {"note": f"key column '{missing_d or missing_g}' absent in one file",
                "key": keys}
    d["_k"] = ["\u241f".join(vals) for vals in zip(*pd_parts)]
    g["_k"] = ["\u241f".join(vals) for vals in zip(*pg_parts)]

    m = d.merge(g, on="_k", suffixes=("_run", "_curated"))
    # fan-out guard: a proper key matches at most max(len(df), len(curated)) rows.
    fanout = len(m) > max(len(d), len(g))
    shared = [c for c in df.columns if c in curated_df.columns and c not in keys]
    per_col = {}; divergences = []
    for c in shared:
        cr, cg = f"{c}_run", f"{c}_curated"
        if cr not in m or cg not in m:
            continue
        agree = (m[cr].map(norm) == m[cg].map(norm))
        per_col[c] = {"agree": int(agree.sum()), "n": int(len(m)),
                      "pct": round(100 * agree.mean(), 1)}
        for _, row in m[~agree][[cr, cg]].drop_duplicates().head(3).iterrows():
            divergences.append({"column": c, "run": row[cr][:60], "curated": row[cg][:60],
                                "triage": "UNTRIAGED"})
    out = {"key": keys, "n_matched_rows": int(len(m)), "shared_columns": len(shared),
           "per_column_agreement": per_col, "divergences_for_triage": divergences}
    if fanout:
        out["WARNING"] = (f"n_matched_rows ({len(m)}) exceeds max input rows "
                          f"({max(len(d), len(g))}): the key {keys} is not unique per row "
                          f"(likely TMT/iTRAQ channels). Pass a composite --key "
                          f"'comment[data file]' 'comment[label]' to fix.")
    return out


# --------------------------------------------------------------- E session cost
def session_metrics(frame_row, annotation_snapshot=None, pricing_profile=None):
    """E17/E19 from a session-usage row dict. `annotation_snapshot` overrides
    cumulative fields for a still-open session (see protocol §4 caveat).

    `pricing_profile` (name / dict / JSON path) decouples this metric from any
    one agent platform. It supplies the token-class price `weights` and a
    `fields` map from the four canonical concepts (read, write, input_total,
    output, plus total_cost) to the field names in `frame_row`. Defaults to the
    'anthropic' profile, reproducing the original Claude Science behaviour
    exactly. A field mapped to None (e.g. OpenAI cache-write) contributes 0.
    """
    prof = resolve_pricing_profile(pricing_profile)
    weights = prof["weights"]; fmap = prof["fields"]
    r = dict(frame_row)
    if annotation_snapshot:
        r.update(annotation_snapshot)

    def get(concept, default=0):
        col = fmap.get(concept)
        return r.get(col, default) if col else default

    read = get("read"); write = get("write")
    input_total = get("input_total")
    fresh = input_total - read - write
    out = get("output")
    total_cost = get("total_cost", None)
    parts = {"read": read, "fresh": fresh, "write": write, "output": out}
    weighted = {k: v * weights.get(k, 1.0) for k, v in parts.items()}
    tw = sum(weighted.values())
    if total_cost is not None and tw:
        dollars = {k: round(total_cost * v / tw, 3) for k, v in weighted.items()}
    else:
        dollars = {}   # no total_cost supplied -> weighted token share only
    return {"pricing_profile": prof.get("note", "custom"),
            "tokens_by_type": parts,
            "weighted_share": {k: round(v / tw, 3) for k, v in weighted.items()} if tw else {},
            "cost_by_type_usd": dollars,
            "total_cost_usd": total_cost,
            "cache_read_write_ratio": round(read / write, 1) if write else None,
            "pct_tokens_cache_read": round(100 * read / input_total, 1) if input_total else None}


# --------------------------------------------------------------- driver
def score_arm(args):
    df = read_sdrf(args.sdrf)
    result = {"sdrf": os.path.basename(args.sdrf), "n_rows": len(df),
              "n_columns": len(df.columns)}
    if args.template_dir:
        union = load_template_columns(args.template_dir, args.templates)
        result["B6_coverage"] = coverage(df, union)
    result["B7_fill_rate"] = fill_rate(df)
    result["B8_reserved_words"] = reserved_word_discipline(df)
    result["B9_ontology_breadth"] = ontology_breadth(df)
    result["A3_nt_ac"] = nt_ac_consistency(df)
    result["A4_accessions"] = hallucinated_accessions(df)   # inventory; resolve separately
    if args.deposited_files:
        result["A5_row_structure"] = row_structure_fidelity(df, args.deposited_files)
    if args.templates:
        result["D14_validate_with_templates"] = validate(args.sdrf, args.templates)
    result["D16_template_self_declaration"] = template_self_declaration(df, args.templates)
    if args.reference and os.path.exists(args.reference):
        diff_key = args.key if getattr(args, "key", None) else "comment[data file]"
        result["A1_curated_diff"] = curated_diff(df, read_sdrf(args.reference), key=diff_key)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sdrf")
    ap.add_argument("--templates", nargs="*", default=["ms-proteomics", "human", "immunopeptidomics"])
    ap.add_argument("--template-dir")
    ap.add_argument("--reference")
    ap.add_argument("--deposited-files")
    ap.add_argument("--key", nargs="+", default=None,
                    help="row-match key for the curated diff (A1). Default: 'comment[data file]'. "
                         "For TMT/iTRAQ pass a composite key, e.g. "
                         "--key 'comment[data file]' 'comment[label]'.")
    ap.add_argument("--out", default="scorecard.json")
    ap.add_argument("--compare", nargs=2, metavar=("ARM_A", "ARM_B"))
    args = ap.parse_args()

    if args.compare:
        import csv
        a = json.load(open(args.compare[0])); b = json.load(open(args.compare[1]))
        rows = [("metric", "arm_A", "arm_B")]
        rows.append(("n_columns", a["n_columns"], b["n_columns"]))
        rows.append(("fill_rate_pct", a["B7_fill_rate"]["pct"], b["B7_fill_rate"]["pct"]))
        rows.append(("illegal_blanks", a["B8_reserved_words"]["illegal_blanks"], b["B8_reserved_words"]["illegal_blanks"]))
        rows.append(("n_ontologies", a["B9_ontology_breadth"]["n_ontologies"], b["B9_ontology_breadth"]["n_ontologies"]))
        rows.append(("n_accessions", a["A4_accessions"]["n_distinct_accessions"], b["A4_accessions"]["n_distinct_accessions"]))
        for k in ("required", "recommended"):
            if "B6_coverage" in a and "B6_coverage" in b:
                rows.append((f"coverage_{k}_pct", a["B6_coverage"][k]["pct"], b["B6_coverage"][k]["pct"]))
        with open(args.out, "w", newline="") as f:
            csv.writer(f).writerows(rows)
        print(f"wrote {args.out}")
        return

    res = score_arm(args)
    json.dump(res, open(args.out, "w"), indent=2)
    print(f"wrote {args.out}")
    print(json.dumps({k: v for k, v in res.items() if not isinstance(v, dict) or len(str(v)) < 400}, indent=2))


if __name__ == "__main__":
    main()

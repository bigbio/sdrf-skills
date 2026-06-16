#!/usr/bin/env python3
"""
Fetch and normalize Europe PMC full text into LLM-friendly text or JSON.

The tool resolves a PMCID/PMID/DOI through Europe PMC, downloads the open-access
JATS XML full text, removes most citation/link noise, and emits either:

- clean text with article metadata + selected sections
- a table-of-contents style section index
- structured JSON for downstream agent workflows

Examples:
  python scripts/europepmc_fulltext.py PMC4047622 --format text
  python scripts/europepmc_fulltext.py 24657495 --id-type pmid --section methods
  python scripts/europepmc_fulltext.py 10.1016/j.jprot.2014.03.010 --id-type doi --format json
  python scripts/europepmc_fulltext.py --xml-file article.xml --format toc
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError

try:
    # Hardened parser: protects against XML entity-expansion / XXE attacks.
    from defusedxml.ElementTree import fromstring as _safe_fromstring
except ImportError:  # pragma: no cover - fallback when defusedxml is unavailable
    _safe_fromstring = ET.fromstring


EUROPE_PMC_BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"
USER_AGENT = "sdrf-skills/europepmc-fulltext/0.1"
DEFAULT_TIMEOUT = 120
XLINK_HREF = "{http://www.w3.org/1999/xlink}href"

PMCID_RE = re.compile(r"^PMC\d+$", re.IGNORECASE)
PMID_RE = re.compile(r"^\d+$")  # PMIDs are positive integers of any length
DOI_RE = re.compile(r"^10\.\S+/\S+$", re.IGNORECASE)
HTTP_URL_RE = re.compile(r"https?://[^\s<>()\[\]{}\"']+", re.IGNORECASE)

ACCESSION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("ProteomeXchange", re.compile(r"\bPXD\d{6}\b", re.IGNORECASE)),
    ("MassIVE", re.compile(r"\bMSV\d{9}\b", re.IGNORECASE)),
    ("BioProject", re.compile(r"\bPRJ(?:NA|EB|DB)\d+\b", re.IGNORECASE)),
    ("SRA study", re.compile(r"\bSRP\d+\b", re.IGNORECASE)),
    ("SRA run", re.compile(r"\bSRR\d+\b", re.IGNORECASE)),
    ("SRA experiment", re.compile(r"\bSRX\d+\b", re.IGNORECASE)),
    ("SRA sample", re.compile(r"\bSRS\d+\b", re.IGNORECASE)),
    ("ArrayExpress", re.compile(r"\bE-[A-Z]+-\d+\b", re.IGNORECASE)),
    ("GEO series", re.compile(r"\bGSE\d+\b", re.IGNORECASE)),
    ("GEO sample", re.compile(r"\bGSM\d+\b", re.IGNORECASE)),
    ("BioSample", re.compile(r"\bSAM(?:N|E[A-Z]?)\d+\b", re.IGNORECASE)),
]

DROP_XREF_TYPES = {
    "aff",
    "app",
    "author-notes",
    "bibr",
    "corresp",
    "fig",
    "fn",
    "sec",
    "supplementary-material",
    "table",
    "table-fn",
}

DEFAULT_TEXT_ORDER = [
    "abstract",
    "introduction",
    "methods",
    "results",
    "discussion",
    "conclusion",
]

SECTION_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("abstract", ("abstract", "summary")),
    ("introduction", ("introduction", "background")),
    (
        "methods",
        (
            "materials and methods",
            "methods and materials",
            "materials & methods",
            "method",
            "methods",
            "experimental",
            "experimental procedures",
            "experimental design",
            "patients and methods",
            "study design",
            "sample preparation",
            "statistical analysis",
        ),
    ),
    ("results", ("results", "findings")),
    ("discussion", ("discussion", "interpretation")),
    ("conclusion", ("conclusion", "conclusions", "concluding remarks")),
    ("acknowledgements", ("acknowledg", "funding", "author contributions")),
    ("supplementary", ("supplementary", "supporting information", "appendix")),
]

PRIMARY_SECTION_CATEGORIES = {
    "introduction",
    "methods",
    "results",
    "discussion",
    "conclusion",
}


@dataclass
class SectionEntry:
    title: str
    category: str
    path: str
    text: str
    block_count: int
    char_count: int


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT) as response:
        return response.read().decode("utf-8")


def fetch_json(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT) as response:
        return json.load(response)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def normalize_inline_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)
    text = re.sub(r"\[\s+", "[", text)
    text = re.sub(r"\s+\]", "]", text)
    return text.strip()


def normalize_block_text(text: str) -> str:
    lines = [normalize_inline_text(line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines).strip()


def strip_balancing_punctuation(value: str) -> str:
    return value.rstrip(".,;:)]}>")


def normalize_pmcid(value: str) -> str:
    value = value.strip().upper()
    if value and not value.startswith("PMC"):
        value = f"PMC{value}"
    return value


def normalize_doi(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).strip()
    value = re.sub(r"(?i)^doi:\s*", "", value)
    value = re.sub(r"(?i)^https?://(?:dx\.)?doi\.org/", "", value)
    value = urllib.parse.unquote(value)
    return strip_balancing_punctuation(value)


def canonicalize_link_value(value: str) -> str:
    raw = unicodedata.normalize("NFKC", value).strip()
    if not raw:
        return ""

    raw = strip_balancing_punctuation(raw)
    lower_raw = raw.lower()

    if lower_raw.startswith(("http://", "https://")):
        return raw

    if DOI_RE.match(raw) or lower_raw.startswith(
        (
            "doi:",
            "https://doi.org/",
            "http://doi.org/",
            "http://dx.doi.org/",
            "https://dx.doi.org/",
        )
    ):
        doi = normalize_doi(raw)
        return f"https://doi.org/{doi}" if doi else ""

    if PMCID_RE.match(raw):
        return f"https://europepmc.org/articles/{normalize_pmcid(raw)}"

    if PMID_RE.match(raw):
        return f"https://pubmed.ncbi.nlm.nih.gov/{raw}/"

    return ""


def normalize_identifier_input(identifier: str) -> tuple[str, str | None]:
    value = unicodedata.normalize("NFKC", identifier).strip()
    value = strip_balancing_punctuation(value)
    lower_value = value.lower()

    if lower_value.startswith(("http://", "https://")):
        parsed = urllib.parse.urlparse(value)
        path = parsed.path.strip("/")
        host = (parsed.netloc or "").lower()

        if "doi.org" in host:
            doi = normalize_doi(path)
            if doi:
                return doi, "doi"

        if "pubmed.ncbi.nlm.nih.gov" in host and path:
            pmid = path.split("/", 1)[0]
            if PMID_RE.match(pmid):
                return pmid, "pmid"

        if "ncbi.nlm.nih.gov" in host and "/pmc/" in parsed.path.lower():
            match = re.search(r"(PMC\d+)", parsed.path, re.IGNORECASE)
            if match:
                return normalize_pmcid(match.group(1)), "pmcid"

        if "europepmc.org" in host:
            match = re.search(r"(PMC\d+)", parsed.path, re.IGNORECASE)
            if match:
                return normalize_pmcid(match.group(1)), "pmcid"
            article_match = re.search(
                r"/article/(?:med|pmc)/([^/]+)", parsed.path, re.IGNORECASE
            )
            if article_match:
                article_id = article_match.group(1)
                if PMID_RE.match(article_id):
                    return article_id, "pmid"
                if PMCID_RE.match(article_id):
                    return normalize_pmcid(article_id), "pmcid"

    pmcid_match = re.match(r"(?i)^pmcid:\s*(PMC?\d+)$", value)
    if pmcid_match:
        return normalize_pmcid(pmcid_match.group(1)), "pmcid"

    pmid_match = re.match(r"(?i)^pmid:\s*(\d+)$", value)
    if pmid_match:
        return pmid_match.group(1), "pmid"

    doi_match = re.match(r"(?i)^doi:\s*(.+)$", value)
    if doi_match:
        return normalize_doi(doi_match.group(1)), "doi"

    if DOI_RE.match(value):
        return normalize_doi(value), "doi"

    if PMCID_RE.match(value):
        return normalize_pmcid(value), "pmcid"

    return value, None


def detect_id_type(identifier: str) -> str:
    value, normalized_type = normalize_identifier_input(identifier)
    if normalized_type:
        return normalized_type
    if PMCID_RE.match(value):
        return "pmcid"
    if PMID_RE.match(value):
        return "pmid"
    if DOI_RE.match(value):
        return "doi"
    raise SystemExit(
        "Could not infer identifier type. Use --id-type pmcid|pmid|doi or --xml-file."
    )


def search_query_for_identifier(identifier: str, id_type: str) -> str:
    if id_type == "pmcid":
        pmcid = identifier.upper()
        if not pmcid.startswith("PMC"):
            pmcid = f"PMC{pmcid}"
        return f'PMCID:{pmcid}'
    if id_type == "pmid":
        return f"EXT_ID:{identifier} AND SRC:MED"
    if id_type == "doi":
        return f'DOI:"{identifier}"'
    raise ValueError(f"Unsupported id_type: {id_type}")


def resolve_article(identifier: str, id_type: str) -> dict:
    query = search_query_for_identifier(identifier, id_type)
    params = urllib.parse.urlencode(
        {
            "query": query,
            "format": "json",
            "resultType": "core",
            "pageSize": 1,
        }
    )
    payload = fetch_json(f"{EUROPE_PMC_BASE}/search?{params}")
    results = payload.get("resultList", {}).get("result", [])
    if not results:
        raise SystemExit(f"No Europe PMC record found for {id_type}:{identifier}")
    record = results[0]
    pmcid = record.get("pmcid") or record.get("fullTextId")
    if not pmcid:
        raise SystemExit(
            f"Europe PMC found a record for {identifier}, but there is no PMCID/full text XML in Europe PMC."
        )
    if not str(pmcid).upper().startswith("PMC"):
        pmcid = f"PMC{pmcid}"
    record["resolvedPmcid"] = str(pmcid).upper()
    return record


def read_xml_source(
    identifier: str | None, id_type: str | None, xml_file: str | None
) -> tuple[str, dict]:
    if xml_file:
        xml_path = Path(xml_file)
        xml_text = xml_path.read_text(encoding="utf-8")
        return xml_text, {"source": "xml-file", "xmlFile": str(xml_path)}

    if not identifier:
        raise SystemExit("Either an identifier or --xml-file is required.")

    normalized_identifier, inferred_type = normalize_identifier_input(identifier)
    resolved_type = id_type or inferred_type or detect_id_type(normalized_identifier)
    record = resolve_article(normalized_identifier, resolved_type)
    pmcid = record["resolvedPmcid"]
    try:
        xml_text = fetch_text(f"{EUROPE_PMC_BASE}/{pmcid}/fullTextXML")
    except HTTPError as exc:
        if exc.code == 404:
            raise SystemExit(
                f"No full-text XML available for {pmcid} "
                "(the article may not be in the Europe PMC open-access subset)."
            )
        raise SystemExit(f"Failed to fetch full-text XML for {pmcid}: HTTP {exc.code}")
    except URLError as exc:
        raise SystemExit(f"Network error fetching full-text XML for {pmcid}: {exc.reason}")
    return xml_text, record


def walk_text(node: ET.Element) -> list[str]:
    parts: list[str] = []
    if node.text:
        parts.append(node.text)

    for child in list(node):
        child_tag = local_name(child.tag)
        if child_tag == "xref":
            ref_type = (child.attrib.get("ref-type") or "").lower()
            if ref_type not in DROP_XREF_TYPES:
                parts.extend(walk_text(child))
        else:
            parts.extend(walk_text(child))
        if child.tail:
            parts.append(child.tail)
    return parts


def node_text(node: ET.Element) -> str:
    return normalize_inline_text("".join(walk_text(node)))


def direct_children(node: ET.Element, tag_name: str) -> list[ET.Element]:
    return [child for child in list(node) if local_name(child.tag) == tag_name]


def first_direct_child(node: ET.Element, tag_name: str) -> ET.Element | None:
    for child in list(node):
        if local_name(child.tag) == tag_name:
            return child
    return None


def first_direct_text(node: ET.Element, tag_name: str, default: str = "") -> str:
    child = first_direct_child(node, tag_name)
    if child is None:
        return default
    return node_text(child) or default


def collapse_blocks(blocks: list[str]) -> str:
    cleaned = [
        normalize_block_text(block)
        for block in blocks
        if normalize_block_text(block)
    ]
    return "\n\n".join(cleaned).strip()


def extract_list_block(node: ET.Element) -> str:
    items: list[str] = []
    for child in list(node):
        if local_name(child.tag) != "list-item":
            continue
        text = node_text(child)
        if text:
            items.append(f"- {text}")
    return "\n".join(items).strip()


def extract_caption(node: ET.Element, prefix: str) -> str:
    caption = first_direct_child(node, "caption")
    label = first_direct_text(node, "label")
    if caption is None:
        return ""
    title = first_direct_text(caption, "title")
    caption_text = node_text(caption)
    parts = [prefix]
    if label:
        parts.append(label)
    if title and title not in caption_text:
        parts.append(title)
    if caption_text:
        parts.append(caption_text)
    return normalize_block_text(": ".join(part for part in parts if part))


def extract_blocks(node: ET.Element) -> list[str]:
    blocks: list[str] = []
    for child in list(node):
        tag = local_name(child.tag)
        if tag in {"sec", "title"}:
            continue
        if tag == "p":
            text = node_text(child)
            if text:
                blocks.append(text)
        elif tag == "list":
            text = extract_list_block(child)
            if text:
                blocks.append(text)
        elif tag in {"disp-quote", "speech", "statement"}:
            text = collapse_blocks(extract_blocks(child)) or node_text(child)
            if text:
                blocks.append(text)
        elif tag in {"boxed-text", "def-list"}:
            text = collapse_blocks(extract_blocks(child))
            if text:
                blocks.append(text)
        elif tag == "fig":
            caption = extract_caption(child, "Figure caption")
            if caption:
                blocks.append(caption)
        elif tag == "table-wrap":
            caption = extract_caption(child, "Table caption")
            if caption:
                blocks.append(caption)
        elif tag == "supplementary-material":
            caption = extract_caption(child, "Supplementary caption")
            if caption:
                blocks.append(caption)
    return blocks


def normalize_section_title(node: ET.Element, fallback: str) -> str:
    title = first_direct_text(node, "title")
    if title:
        return title
    sec_type = node.attrib.get("sec-type", "")
    if sec_type:
        return normalize_inline_text(sec_type.replace("-", " "))
    return fallback


def match_section_categories(normalized: str) -> list[str]:
    matches: list[str] = []
    for category, patterns in SECTION_PATTERNS:
        if any(pattern in normalized for pattern in patterns):
            matches.append(category)
    return matches


def classify_section(
    title: str, sec_type: str = "", parent_category: str = ""
) -> str:
    normalized = f"{title} {sec_type}".strip().lower()
    normalized = re.sub(r"[^a-z0-9\s&/-]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    matches = match_section_categories(normalized)
    if matches:
        if (
            parent_category == "discussion"
            and matches == ["results"]
            and "results" not in normalized
        ):
            return parent_category
        return matches[0]

    if parent_category in PRIMARY_SECTION_CATEGORIES:
        return parent_category
    return "other"


def collect_section_entries(
    node: ET.Element,
    parent_titles: list[str] | None = None,
    parent_category: str = "",
) -> list[SectionEntry]:
    parent_titles = parent_titles or []
    entries: list[SectionEntry] = []
    for index, sec in enumerate(direct_children(node, "sec"), start=1):
        title = normalize_section_title(sec, f"Untitled section {index}")
        path_titles = parent_titles + [title]
        path = " > ".join(path_titles)
        sec_type = sec.attrib.get("sec-type", "")
        category = classify_section(title, sec_type, parent_category)
        blocks = extract_blocks(sec)
        text = collapse_blocks(blocks)
        entries.append(
            SectionEntry(
                title=title,
                category=category,
                path=path,
                text=text,
                block_count=len([block for block in blocks if block.strip()]),
                char_count=len(text),
            )
        )
        entries.extend(collect_section_entries(sec, path_titles, category))
    return entries


def collect_abstract_entries(root: ET.Element) -> list[SectionEntry]:
    entries: list[SectionEntry] = []
    abstract_nodes = [node for node in root.iter() if local_name(node.tag) == "abstract"]
    for index, abstract in enumerate(abstract_nodes, start=1):
        title = (
            first_direct_text(abstract, "title")
            or abstract.attrib.get("abstract-type")
            or f"Abstract {index}"
        )
        blocks = extract_blocks(abstract)
        if not blocks:
            text = node_text(abstract)
        else:
            text = collapse_blocks(blocks)
        entries.append(
            SectionEntry(
                title=normalize_inline_text(title),
                category="abstract",
                path=normalize_inline_text(title) or f"Abstract {index}",
                text=text,
                block_count=len([block for block in blocks if block.strip()]),
                char_count=len(text),
            )
        )
    return entries


def collect_captions(root: ET.Element, tag_name: str, prefix: str) -> list[str]:
    captions: list[str] = []
    for node in root.iter():
        if local_name(node.tag) != tag_name:
            continue
        caption = extract_caption(node, prefix)
        if caption:
            captions.append(caption)
    return captions


def canonical_article_links(metadata: dict) -> dict[str, str]:
    links: dict[str, str] = {}
    pmcid = metadata.get("pmcid", "")
    pmid = metadata.get("pmid", "")
    doi = metadata.get("doi", "")

    if pmcid:
        pmcid = normalize_pmcid(str(pmcid))
        links["europepmc"] = f"https://europepmc.org/articles/{pmcid}"
        links["pmc"] = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"
    if pmid:
        links["pubmed"] = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    if doi:
        links["doi"] = f"https://doi.org/{normalize_doi(str(doi))}"
    return links


def collect_external_links(root: ET.Element) -> list[str]:
    links: list[str] = []
    for node in root.iter():
        href = node.attrib.get(XLINK_HREF) or node.attrib.get("href")
        if href:
            canonical = canonicalize_link_value(href)
            if canonical:
                links.append(canonical)
        text = (node.text or "").strip()
        if text:
            canonical = canonicalize_link_value(text)
            if canonical:
                links.append(canonical)
    return sorted({link for link in links if link})


def find_accessions_in_text(text: str) -> list[dict[str, str]]:
    matches: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for source, pattern in ACCESSION_PATTERNS:
        for match in pattern.finditer(text):
            accession = match.group(0).upper()
            key = (source, accession)
            if key in seen:
                continue
            seen.add(key)
            matches.append({"source": source, "accession": accession})
    return matches


def collect_detected_accessions(
    metadata: dict, all_entries: list[SectionEntry], captions: list[str]
) -> list[dict[str, object]]:
    seen: set[tuple[str, str, str]] = set()
    detected: list[dict[str, object]] = []

    sources: list[tuple[str, str, str]] = []
    metadata_text = " ".join(
        str(value) for value in metadata.values() if isinstance(value, str)
    )
    if metadata_text:
        sources.append(("metadata", "article metadata", metadata_text))

    for entry in all_entries:
        if entry.text:
            sources.append(("section", entry.path, entry.text))

    for caption in captions:
        sources.append(("caption", "caption", caption))

    for location_type, location, text in sources:
        for match in find_accessions_in_text(text):
            key = (match["source"], match["accession"], location)
            if key in seen:
                continue
            seen.add(key)
            detected.append(
                {
                    "source": match["source"],
                    "accession": match["accession"],
                    "location_type": location_type,
                    "location": location,
                }
            )
    return detected


def extract_metadata(root: ET.Element, record: dict) -> dict:
    article_meta = None
    for node in root.iter():
        if local_name(node.tag) == "article-meta":
            article_meta = node
            break

    journal_meta = None
    for node in root.iter():
        if local_name(node.tag) == "journal-meta":
            journal_meta = node
            break

    title = ""
    if article_meta is not None:
        title_group = first_direct_child(article_meta, "title-group")
        if title_group is not None:
            title = first_direct_text(title_group, "article-title")

    journal = ""
    if journal_meta is not None:
        journal_title_group = first_direct_child(journal_meta, "journal-title-group")
        if journal_title_group is not None:
            journal = first_direct_text(journal_title_group, "journal-title")

    authors: list[str] = []
    if article_meta is not None:
        contrib_group = first_direct_child(article_meta, "contrib-group")
        if contrib_group is not None:
            for contrib in direct_children(contrib_group, "contrib"):
                if (contrib.attrib.get("contrib-type") or "").lower() not in {"", "author"}:
                    continue
                name = first_direct_child(contrib, "name")
                collab = first_direct_text(contrib, "collab")
                if name is not None:
                    surname = first_direct_text(name, "surname")
                    given = first_direct_text(name, "given-names")
                    full = " ".join(part for part in [given, surname] if part).strip()
                    if full:
                        authors.append(full)
                elif collab:
                    authors.append(collab)

    article_ids: dict[str, str] = {}
    if article_meta is not None:
        for article_id in direct_children(article_meta, "article-id"):
            article_ids[article_id.attrib.get("pub-id-type", "unknown")] = node_text(
                article_id
            )

    publication_date = ""
    if article_meta is not None:
        for pub_date in direct_children(article_meta, "pub-date"):
            year = first_direct_text(pub_date, "year")
            month = first_direct_text(pub_date, "month")
            day = first_direct_text(pub_date, "day")
            if year:
                parts = [year]
                if month:
                    parts.append(month.zfill(2))
                if day:
                    parts.append(day.zfill(2))
                publication_date = "-".join(parts)
                break

    metadata = {
        "title": title or record.get("title", ""),
        "journal": journal or record.get("journalTitle", ""),
        "publication_date": publication_date
        or str(record.get("firstPublicationDate") or ""),
        "authors": authors
        or ([record["authorString"]] if record.get("authorString") else []),
        "pmcid": article_ids.get("pmcid")
        or record.get("resolvedPmcid")
        or record.get("pmcid", ""),
        "pmid": article_ids.get("pmid") or str(record.get("pmid") or ""),
        "doi": article_ids.get("doi") or record.get("doi", ""),
        "article_type": root.attrib.get("article-type", ""),
        "source": record.get("source", "europepmc"),
        "is_open_access": str(record.get("isOpenAccess", "")).lower()
        in {"y", "true", "1"},
    }
    metadata["pmcid"] = (
        normalize_pmcid(str(metadata["pmcid"])) if metadata.get("pmcid") else ""
    )
    metadata["doi"] = normalize_doi(str(metadata["doi"])) if metadata.get("doi") else ""
    metadata["links"] = canonical_article_links(metadata)
    return metadata


def build_payload(root: ET.Element, record: dict) -> dict:
    abstract_entries = collect_abstract_entries(root)

    body = next((node for node in root.iter() if local_name(node.tag) == "body"), None)
    body_entries = collect_section_entries(body) if body is not None else []

    back = next((node for node in root.iter() if local_name(node.tag) == "back"), None)
    back_entries = collect_section_entries(back, ["Back matter"]) if back is not None else []

    all_entries = abstract_entries + body_entries + back_entries
    section_buckets: dict[str, list[str]] = {}
    for entry in all_entries:
        section_buckets.setdefault(entry.category, [])
        if entry.text:
            section_buckets[entry.category].append(entry.text)

    aggregated = {
        category: collapse_blocks(texts)
        for category, texts in section_buckets.items()
        if collapse_blocks(texts)
    }

    available_sections = [
        {
            "title": entry.title,
            "category": entry.category,
            "path": entry.path,
            "blocks": entry.block_count,
            "chars": entry.char_count,
        }
        for entry in all_entries
    ]

    figure_captions = collect_captions(root, "fig", "Figure caption")
    table_captions = collect_captions(root, "table-wrap", "Table caption")
    supplementary_captions = collect_captions(
        root, "supplementary-material", "Supplementary caption"
    )
    metadata = extract_metadata(root, record)
    external_links = collect_external_links(root)
    detected_accessions = collect_detected_accessions(
        metadata,
        all_entries,
        figure_captions + table_captions + supplementary_captions,
    )

    return {
        "source": "europepmc",
        "metadata": metadata,
        "available_section_categories": sorted(
            {entry.category for entry in all_entries}
        ),
        "available_sections": available_sections,
        "sections_by_category": aggregated,
        "sections": [
            {
                "title": entry.title,
                "category": entry.category,
                "path": entry.path,
                "text": entry.text,
            }
            for entry in all_entries
            if entry.text
        ],
        "figure_captions": figure_captions,
        "table_captions": table_captions,
        "supplementary_captions": supplementary_captions,
        "external_links": external_links,
        "detected_accessions": detected_accessions,
    }


def filter_sections(payload: dict, filters: list[str]) -> dict:
    if not filters:
        return payload

    filters_lower = [item.lower() for item in filters]

    def match(section: dict) -> bool:
        haystacks = [
            section.get("category", "").lower(),
            section.get("title", "").lower(),
            section.get("path", "").lower(),
        ]
        return any(
            filter_value in haystack
            for filter_value in filters_lower
            for haystack in haystacks
        )

    sections = [section for section in payload["sections"] if match(section)]
    categories = sorted({section["category"] for section in sections})
    by_category: dict[str, list[str]] = {}
    for section in sections:
        by_category.setdefault(section["category"], []).append(section["text"])

    payload = dict(payload)
    payload["sections"] = sections
    payload["available_sections"] = [
        section for section in payload["available_sections"] if match(section)
    ]
    payload["available_section_categories"] = categories
    payload["sections_by_category"] = {
        category: collapse_blocks(texts)
        for category, texts in by_category.items()
        if collapse_blocks(texts)
    }
    return payload


def maybe_truncate(text: str, max_chars: int | None) -> str:
    if not max_chars or len(text) <= max_chars:
        return text
    clipped = text[: max_chars - 24].rstrip()
    return f"{clipped}\n\n[truncated at {max_chars} chars]"


def render_toc(payload: dict) -> str:
    lines = ["ARTICLE METADATA"]
    for key, value in payload["metadata"].items():
        if key == "links" and isinstance(value, dict):
            continue
        if isinstance(value, list):
            value = "; ".join(item for item in value if item)
        lines.append(f"{key}: {value}")

    links = payload["metadata"].get("links", {})
    if links:
        lines.append("")
        lines.append("CANONICAL LINKS")
        for label, url in links.items():
            lines.append(f"- {label}: {url}")

    if payload["detected_accessions"]:
        lines.append("")
        lines.append("DETECTED ACCESSIONS")
        for item in payload["detected_accessions"]:
            lines.append(
                f"- {item['source']} | {item['accession']} | {item['location_type']} | {item['location']}"
            )

    lines.append("")
    lines.append("AVAILABLE SECTION CATEGORIES")
    for category in payload["available_section_categories"]:
        lines.append(f"- {category}")

    lines.append("")
    lines.append("AVAILABLE SECTIONS")
    for section in payload["available_sections"]:
        lines.append(
            f"- {section['category']} | {section['path']} | {section['chars']} chars | {section['blocks']} blocks"
        )
    return "\n".join(lines)


def render_text(payload: dict, max_chars: int | None, all_sections: bool) -> str:
    lines = ["ARTICLE METADATA"]
    for key, value in payload["metadata"].items():
        if key == "links" and isinstance(value, dict):
            continue
        if isinstance(value, list):
            value = "; ".join(item for item in value if item)
        lines.append(f"{key}: {value}")

    links = payload["metadata"].get("links", {})
    if links:
        lines.append("")
        lines.append("CANONICAL LINKS")
        for label, url in links.items():
            lines.append(f"- {label}: {url}")

    if payload["detected_accessions"]:
        lines.append("")
        lines.append("DETECTED ACCESSIONS")
        for item in payload["detected_accessions"]:
            lines.append(
                f"- {item['source']} | {item['accession']} | {item['location_type']} | {item['location']}"
            )

    lines.append("")
    lines.append("AVAILABLE SECTIONS")
    for section in payload["available_sections"]:
        lines.append(
            f"- {section['category']} | {section['path']} | {section['chars']} chars"
        )

    section_order = list(DEFAULT_TEXT_ORDER)
    if all_sections:
        for category in payload["available_section_categories"]:
            if category not in section_order:
                section_order.append(category)
    else:
        extras = [
            category
            for category in payload["available_section_categories"]
            if category not in section_order
        ]
        if not any(
            category in payload["sections_by_category"] for category in section_order
        ):
            section_order.extend(extras)

    for category in section_order:
        text = payload["sections_by_category"].get(category, "")
        if not text:
            continue
        lines.append("")
        lines.append(category.upper())
        lines.append(maybe_truncate(text, max_chars))

    if payload["table_captions"]:
        lines.append("")
        lines.append("TABLE CAPTIONS")
        for caption in payload["table_captions"]:
            lines.append(f"- {maybe_truncate(caption, max_chars)}")

    if payload["supplementary_captions"]:
        lines.append("")
        lines.append("SUPPLEMENTARY CAPTIONS")
        for caption in payload["supplementary_captions"]:
            lines.append(f"- {maybe_truncate(caption, max_chars)}")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "identifier",
        nargs="?",
        help="PMCID, PMID, or DOI. Omit when using --xml-file.",
    )
    parser.add_argument(
        "--id-type",
        choices=("auto", "pmcid", "pmid", "doi"),
        default="auto",
        help="Identifier type; defaults to auto-detection.",
    )
    parser.add_argument(
        "--xml-file",
        help="Read a local Europe PMC fullTextXML/JATS file instead of fetching from the API.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json", "toc"),
        default="text",
        help="Output format.",
    )
    parser.add_argument(
        "--section",
        action="append",
        default=[],
        help="Restrict output to matching section categories/titles/paths. Repeatable.",
    )
    parser.add_argument(
        "--all-sections",
        action="store_true",
        help="In text mode, include every available section category instead of the default major buckets only.",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=None,
        help="Optional per-section text truncation for LLM context control.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    id_type = None if args.id_type == "auto" else args.id_type
    xml_text, record = read_xml_source(args.identifier, id_type, args.xml_file)
    root = _safe_fromstring(xml_text)
    payload = build_payload(root, record)
    payload = filter_sections(payload, args.section)

    if args.format == "json":
        json.dump(payload, sys.stdout, indent=2)
        print()
        return

    if args.format == "toc":
        print(render_toc(payload))
        return

    print(render_text(payload, args.max_chars, args.all_sections))


if __name__ == "__main__":
    main()

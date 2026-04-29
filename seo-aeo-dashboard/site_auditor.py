#!/usr/bin/env python3
"""
site_auditor.py — Real AEO/GEO scoring from live venue websites.

Fetches each venue's main page plus known sub-pages (access, faq, getting-here,
venue-info) and scores 12 components across two engines:

  AEO: structured_data (20%), faq_qa_content (15%), heading_semantic (15%),
       internal_linking (10%), page_speed_proxy (10%), content_clarity (30%)

  GEO: entity_clarity (20%), content_chunking (15%), topical_completeness (20%),
       external_corroboration (10%), structured_data_richness (15%),
       prompt_relevance (20%)

Writes real scores back to data/venues_sample.json (preserves slug/url/region).

Requirements:
    pip install requests beautifulsoup4

Usage:
    python site_auditor.py                              # all 20 venues
    python site_auditor.py --venue o2-academy-brixton   # single venue
    python site_auditor.py --dry-run                    # show URLs only
    python site_auditor.py --rate-limit 2.0             # slower crawl
    python site_auditor.py --output data/audit_test.json
"""

import argparse
import json
import logging
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

try:
    import requests
    from bs4 import BeautifulSoup, Tag
except ImportError:
    raise ImportError("pip install requests beautifulsoup4")

ROOT       = Path(__file__).parent
DATA_DIR   = ROOT / "data"
VENUES_FILE = DATA_DIR / "venues_sample.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

# AEO component weights (must sum to 1.0)
AEO_WEIGHTS = {
    "structured_data":  0.20,
    "faq_qa_content":   0.15,
    "heading_semantic": 0.15,
    "internal_linking": 0.10,
    "page_speed_proxy": 0.10,
    "content_clarity":  0.30,
}

# GEO component weights (must sum to 1.0)
GEO_WEIGHTS = {
    "entity_clarity":          0.20,
    "content_chunking":        0.15,
    "topical_completeness":    0.20,
    "external_corroboration":  0.10,
    "structured_data_richness": 0.15,
    "prompt_relevance":        0.20,
}

# Sub-page path fragments to look for (order = priority)
SUB_PAGE_SIGNALS = {
    "access":       ["access", "accessibility", "disabled"],
    "getting-here": ["getting-here", "getting_here", "transport", "directions", "travel"],
    "venue-info":   ["venue-info", "venue_info", "venueinfo", "info", "practical"],
    "faq":          ["faq", "faqs", "frequently-asked", "help"],
}

# Capacity signals (regex pattern)
CAPACITY_RE = re.compile(
    r'\b(\d[\d,]+)\s*(?:capacity|standing|seated|people|guests|max)\b'
    r'|\b(?:capacity|holds|fits|seats)\s*(?:up\s*to\s*)?(\d[\d,]+)',
    re.IGNORECASE
)
PHONE_RE    = re.compile(r'(\+44|0)\s*\d[\d\s\-]{8,}')
POSTCODE_RE = re.compile(r'\b[A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}\b', re.IGNORECASE)


# ── HTTP utilities ────────────────────────────────────────────────────────────

def make_session(timeout: int = 15) -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = (
        "Mozilla/5.0 (compatible; AMG-SEO-Auditor/1.0; +https://academymusicgroup.com)"
    )
    s.headers["Accept"] = "text/html,application/xhtml+xml,*/*"
    return s


def fetch(url: str, session: requests.Session, timeout: int = 15):
    """Fetch URL. Returns (soup, response_time_ms) or (None, None) on error."""
    try:
        t0 = time.monotonic()
        r  = session.get(url, timeout=timeout, allow_redirects=True)
        ms = int((time.monotonic() - t0) * 1000)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            return soup, ms
        logger.debug("  %s → HTTP %d", url, r.status_code)
        return None, None
    except Exception as exc:
        logger.debug("  %s → %s", url, exc)
        return None, None


def find_sub_pages(main_soup: BeautifulSoup, base_url: str) -> dict[str, str]:
    """
    Return {category: absolute_url} for sub-pages found via link analysis.
    Also tries common path variations as fallback.
    """
    parsed   = urlparse(base_url)
    domain   = f"{parsed.scheme}://{parsed.netloc}"
    base_path = parsed.path.rstrip("/")          # e.g. /o2academybrixton

    # Gather all internal href values
    hrefs: list[str] = []
    for a in main_soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("http"):
            if parsed.netloc in href:
                hrefs.append(href)
        elif href.startswith("/"):
            hrefs.append(domain + href)
        elif href and not href.startswith("#"):
            hrefs.append(urljoin(base_url, href))

    found: dict[str, str] = {}
    for category, signals in SUB_PAGE_SIGNALS.items():
        for href in hrefs:
            path_lower = urlparse(href).path.lower()
            if any(sig in path_lower for sig in signals):
                found[category] = href
                break

    # Fallback: try guessing common paths
    for category, signals in SUB_PAGE_SIGNALS.items():
        if category in found:
            continue
        for sig in signals[:2]:
            candidate = f"{domain}{base_path}/{sig}"
            found[f"_try_{category}"] = candidate   # prefixed so caller knows to verify

    return found


# ── JSON-LD extraction ────────────────────────────────────────────────────────

def extract_schemas(soup: BeautifulSoup) -> list[dict]:
    """Return list of all JSON-LD objects/arrays from the page."""
    schemas: list[dict] = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            payload = json.loads(tag.string or "")
            if isinstance(payload, list):
                schemas.extend(payload)
            elif isinstance(payload, dict):
                # Unwrap @graph if present
                if "@graph" in payload:
                    schemas.extend(payload["@graph"])
                else:
                    schemas.append(payload)
        except (json.JSONDecodeError, TypeError):
            pass
    return schemas


def schema_types(schemas: list[dict]) -> set[str]:
    types: set[str] = set()
    for s in schemas:
        t = s.get("@type", "")
        if isinstance(t, list):
            types.update(t)
        elif t:
            types.add(t)
    return types


def has_type(schemas: list[dict], *wanted: str) -> bool:
    types = schema_types(schemas)
    return any(w in types for w in wanted)


def schema_value(schemas: list[dict], key: str):
    """Return first truthy value found for key across all schemas."""
    for s in schemas:
        if s.get(key):
            return s[key]
    return None


# ── Visible text helpers ──────────────────────────────────────────────────────

def visible_text(soup: BeautifulSoup) -> str:
    """Strip scripts/styles and return clean body text."""
    for tag in soup(["script", "style", "noscript", "nav", "footer", "head"]):
        tag.decompose()
    return " ".join(soup.get_text(" ", strip=True).split())


def word_count(text: str) -> int:
    return len(text.split())


def contains_any(text: str, *terms: str) -> bool:
    lower = text.lower()
    return any(t.lower() in lower for t in terms)


# ── AEO scoring ───────────────────────────────────────────────────────────────

def score_structured_data(schemas: list[dict]) -> tuple[int, list[str]]:
    """AEO: structured_data (0-100). Is machine-readable schema present and correct?"""
    score    = 0
    findings = []
    types    = schema_types(schemas)

    if not schemas:
        findings.append("No JSON-LD structured data found on page.")
        return 0, findings

    type_names = ", ".join(sorted(types)) or "unknown"
    findings.append(f"Schema types found: {type_names}")

    score += 15   # any schema present

    if "MusicVenue" in types:
        score += 30
        findings.append("MusicVenue schema present — correct type for a live music venue.")
    elif types & {"LocalBusiness", "Organization", "Place"}:
        score += 10
        findings.append("Generic business schema found — should be upgraded to MusicVenue.")

    if has_type(schemas, "Event", "MusicEvent"):
        score += 15
        findings.append("Event / MusicEvent schema present.")

    if has_type(schemas, "FAQPage"):
        score += 25
        findings.append("FAQPage schema present — enables FAQ rich results.")
    else:
        findings.append("No FAQPage schema — add to FAQ content to unlock rich results.")

    cap = schema_value(schemas, "maximumAttendeeCapacity")
    if cap:
        score += 15
        findings.append(f"maximumAttendeeCapacity = {cap} in schema.")
    else:
        findings.append("maximumAttendeeCapacity missing from schema.")

    return min(score, 100), findings


def score_faq_content(
    soups: list[BeautifulSoup],
    schemas: list[dict],
    sub_pages_found: dict[str, str],
) -> tuple[int, list[str]]:
    """AEO: faq_qa_content (0-100). Does FAQ / Q&A content exist and is it marked up?"""
    score    = 0
    findings = []

    # FAQPage schema is the gold standard
    if has_type(schemas, "FAQPage"):
        score += 30
        findings.append("FAQPage JSON-LD present on page.")
        qa_items = []
        for s in schemas:
            if s.get("@type") == "FAQPage":
                qa_items = s.get("mainEntity", [])
        if qa_items:
            n = len(qa_items)
            bonus = min(30, n * 5)
            score += bonus
            findings.append(f"{n} Q&A items in FAQPage schema.")
    else:
        findings.append("No FAQPage schema — markup is missing even if FAQ content exists.")

    # Detect FAQ headings / sections in HTML across all fetched pages
    faq_heading_found = False
    qa_count = 0
    for soup in soups:
        text_lower = soup.get_text(" ").lower()
        # FAQ heading
        for heading in soup.find_all(["h1","h2","h3","h4"]):
            if "faq" in heading.get_text().lower() or "frequently" in heading.get_text().lower():
                faq_heading_found = True
        # Count Q&A-like patterns (details/summary, dl, .faq-item)
        qa_count += len(soup.find_all("details"))
        qa_count += len(soup.find_all("dl"))
        # Regex: lines ending with "?" followed by answer text
        questions = re.findall(r'[A-Z][^.?!]{10,80}\?', text_lower, re.MULTILINE)
        qa_count += len(questions)

    if faq_heading_found:
        score += 20
        findings.append("FAQ heading detected in page content.")

    if qa_count >= 6:
        score += 20
        findings.append(f"~{qa_count} Q&A-style items detected across pages.")
    elif qa_count >= 3:
        score += 10
        findings.append(f"~{qa_count} Q&A-style items detected — aim for 6+.")
    elif qa_count > 0:
        score += 5
        findings.append(f"Only ~{qa_count} Q&A item(s) detected — add more FAQ content.")

    # Note if FAQ is on a sub-page but not the main page
    if "faq" in sub_pages_found:
        if not has_type(schemas, "FAQPage"):
            findings.append(
                f"Dedicated FAQ sub-page found ({sub_pages_found['faq']}) "
                "but FAQPage schema not applied there — add schema to maximise AEO impact."
            )

    if score == 0:
        findings.append("No FAQ content or schema detected. Add 6–8 Q&A pairs with FAQPage schema.")

    return min(score, 100), findings


def score_heading_semantic(soup: BeautifulSoup, venue_name: str) -> tuple[int, list[str]]:
    """AEO: heading_semantic (0-100). Is heading hierarchy clean and descriptive?"""
    score    = 0
    findings = []

    h1s = soup.find_all("h1")
    h2s = soup.find_all("h2")
    h3s = soup.find_all("h3")

    if len(h1s) == 1:
        score += 30
        h1_text = h1s[0].get_text(strip=True)
        findings.append(f"Single H1 present: '{h1_text[:60]}'")
        if venue_name.lower()[:10] in h1_text.lower():
            score += 20
            findings.append("H1 contains venue name — good for entity identification.")
    elif len(h1s) > 1:
        score += 10
        findings.append(f"{len(h1s)} H1 tags found — should be exactly one.")
    else:
        findings.append("No H1 tag found — critical for AEO entity recognition.")

    if len(h2s) >= 3:
        score += 30
        findings.append(f"{len(h2s)} H2 tags provide good semantic sectioning.")
    elif len(h2s) >= 1:
        score += 15
        findings.append(f"Only {len(h2s)} H2 tag(s) — add more to improve content structure.")
    else:
        findings.append("No H2 tags — page lacks semantic structure.")

    if h3s:
        score += 20
        findings.append(f"{len(h3s)} H3 tag(s) present.")

    return min(score, 100), findings


def score_internal_linking(
    main_soup: BeautifulSoup,
    sub_pages_found: dict[str, str],
) -> tuple[int, list[str]]:
    """AEO: internal_linking (0-100). Do key sub-pages exist and are they linked?"""
    score    = 0
    findings = []

    confirmed = {k: v for k, v in sub_pages_found.items() if not k.startswith("_try_")}
    all_links = main_soup.find_all("a", href=True)
    link_count = len(all_links)

    findings.append(f"{link_count} links found on main page.")

    for category in ["access", "getting-here", "venue-info", "faq"]:
        if category in confirmed:
            score += 25
            findings.append(f"Sub-page linked: {category} ({confirmed[category]})")
        else:
            findings.append(f"No {category} sub-page detected.")

    return min(score, 100), findings


def score_page_speed(response_ms: int) -> tuple[int, list[str]]:
    """AEO: page_speed_proxy (0-100). Response time as speed proxy."""
    findings = [f"Page loaded in {response_ms}ms (structural proxy — run Lighthouse for accuracy)."]
    if response_ms < 800:
        return 100, findings
    if response_ms < 1500:
        return 80, findings
    if response_ms < 2500:
        return 60, findings
    if response_ms < 4000:
        return 40, findings
    if response_ms < 6000:
        return 20, findings
    return 10, findings


def score_content_clarity(
    soups: list[BeautifulSoup],
    text_combined: str,
) -> tuple[int, list[str]]:
    """AEO: content_clarity (0-100). Volume and usefulness of body copy."""
    score    = 0
    findings = []
    words    = word_count(text_combined)

    if words >= 600:
        score += 60
        findings.append(f"Good content volume ({words} words across crawled pages).")
    elif words >= 350:
        score += 45
        findings.append(f"Moderate content volume ({words} words) — aim for 600+.")
    elif words >= 150:
        score += 25
        findings.append(f"Thin content ({words} words) — expand substantially.")
    else:
        score += 5
        findings.append(f"Very thin content ({words} words) — major gap.")

    if CAPACITY_RE.search(text_combined):
        score += 15
        m = CAPACITY_RE.search(text_combined)
        cap_val = (m.group(1) or m.group(2) or "").strip()
        findings.append(f"Capacity information present: {cap_val}.")
    else:
        findings.append("No capacity figure found in page text.")

    if contains_any(text_combined, "tube", "bus", "train", "underground",
                    "getting here", "nearest station", "transport"):
        score += 15
        findings.append("Transport / directions information present.")
    else:
        findings.append("No transport or directions content found.")

    if contains_any(text_combined, "accessible", "wheelchair", "disabled", "assistance"):
        score += 10
        findings.append("Accessibility information present.")
    else:
        findings.append("No accessibility information found.")

    if POSTCODE_RE.search(text_combined):
        addr_match = POSTCODE_RE.search(text_combined)
        findings.append(f"Address / postcode found: {addr_match.group()}")

    return min(score, 100), findings


# ── GEO scoring ───────────────────────────────────────────────────────────────

def score_entity_clarity(text: str, schemas: list[dict]) -> tuple[int, list[str]]:
    """GEO: entity_clarity (0-100). Can an LLM extract the core facts?"""
    score = 0; findings = []
    m = CAPACITY_RE.search(text)
    if m:
        cap = (m.group(1) or m.group(2) or "").strip()
        score += 35
        findings.append(f"Capacity figure found in page text: {cap}.")
    else:
        findings.append("No capacity figure in page text — LLMs cannot answer capacity queries.")
    if POSTCODE_RE.search(text):
        score += 35
        findings.append(f"Address / postcode present: {POSTCODE_RE.search(text).group()}.")
    else:
        findings.append("No postcode / address found in page text.")
    if PHONE_RE.search(text):
        score += 30
        findings.append("Phone number present.")
    else:
        findings.append("No phone number found.")
    return min(score, 100), findings


def score_content_chunking(soups: list) -> tuple[int, list[str]]:
    """GEO: content_chunking (0-100). Is content broken into digestible sections?"""
    score = 0; findings = []
    h_count    = sum(len(s.find_all(["h2", "h3"])) for s in soups)
    list_count = sum(len(s.find_all(["ul", "ol"])) for s in soups)
    p_count    = sum(len(s.find_all("p")) for s in soups)
    if h_count >= 8:   score += 50
    elif h_count >= 4: score += 35
    elif h_count >= 1: score += 15
    findings.append(f"{h_count} H2/H3 section headers across crawled pages.")
    if list_count >= 3:   score += 30; findings.append(f"{list_count} list elements.")
    elif list_count >= 1: score += 15; findings.append(f"{list_count} list element(s) — add more.")
    else:                 findings.append("No list elements found.")
    if p_count >= 8:   score += 20; findings.append(f"{p_count} paragraphs — good content depth.")
    elif p_count >= 3: score += 10
    return min(score, 100), findings


def score_topical_completeness(text: str) -> tuple[int, list[str]]:
    """GEO: topical_completeness (0-100). Does the page cover all six key topics?"""
    TOPICS = {
        "Identity / brand":   ["o2", "academy", "venue", "music", "live"],
        "Capacity":           ["capacity", "standing", "seated", "holds"],
        "History / heritage": ["opened", "history", "established", "heritage", "since", "iconic"],
        "Accessibility":      ["accessible", "wheelchair", "disabled", "assistance", "hearing loop"],
        "Transport":          ["tube", "bus", "train", "underground", "station", "getting here"],
        "Events / programme": ["events", "gigs", "concerts", "tickets", "upcoming"],
    }
    score = 0; findings = []; per = 100 // len(TOPICS)
    for topic, sigs in TOPICS.items():
        if contains_any(text, *sigs): score += per
        else: findings.append(f"Missing topic coverage: {topic}.")
    if not findings: findings.append("All six key topics covered.")
    return min(score, 100), findings


def score_external_corroboration(soups: list, schemas: list[dict]) -> tuple[int, list[str]]:
    """GEO: external_corroboration (0-100). Are there authoritative external references?"""
    score = 0; findings = []
    same_as = schema_value(schemas, "sameAs")
    if same_as:
        score += 40
        refs = same_as if isinstance(same_as, list) else [same_as]
        findings.append(f"sameAs in schema: {', '.join(str(r) for r in refs[:3])}")
    else:
        findings.append("No sameAs in schema — add Wikidata / Wikipedia links.")
    wiki = any("wikipedia.org" in (a.get("href","")) for s in soups for a in s.find_all("a", href=True))
    wikidata = any("wikidata.org" in (a.get("href","")) for s in soups for a in s.find_all("a", href=True))
    if wiki:     score += 30; findings.append("Link to Wikipedia article found.")
    else:        findings.append("No Wikipedia link found.")
    if wikidata: score += 30; findings.append("Link to Wikidata entity found.")
    return min(score, 100), findings


def score_schema_richness(schemas: list[dict]) -> tuple[int, list[str]]:
    """GEO: structured_data_richness (0-100). How complete is the schema entity?"""
    score = 0; findings = []
    if has_type(schemas, "MusicVenue"):
        score += 30; findings.append("MusicVenue type — correct entity classification.")
    elif has_type(schemas, "LocalBusiness", "Organization"):
        score += 10; findings.append("LocalBusiness/Organization — upgrade to MusicVenue.")
    else:
        findings.append("No venue entity schema found.")
    if schema_value(schemas, "maximumAttendeeCapacity"):
        score += 25; findings.append("maximumAttendeeCapacity declared.")
    else:
        findings.append("maximumAttendeeCapacity missing from schema.")
    if any(s.get("address") or s.get("location") for s in schemas):
        score += 25; findings.append("Postal address in schema.")
    else:
        findings.append("No address in schema.")
    if schema_value(schemas, "sameAs"):
        score += 20; findings.append("sameAs links present.")
    return min(score, 100), findings


def score_prompt_relevance(text: str) -> tuple[int, list[str]]:
    """GEO: prompt_relevance (0-100). Does content map to common LLM query types?"""
    CLUSTERS = {
        "Capacity queries":      ["capacity", "holds", "standing", "seated"],
        "Transport queries":     ["tube", "underground", "bus", "train", "station"],
        "Accessibility queries": ["wheelchair", "accessible", "disabled", "hearing loop"],
        "History queries":       ["opened", "history", "established", "iconic"],
        "Genre / music queries": ["rock", "pop", "indie", "metal", "electronic", "hip-hop",
                                  "jazz", "folk", "r&b"],
    }
    score = 0; findings = []; per = 100 // len(CLUSTERS)
    for cluster, terms in CLUSTERS.items():
        if contains_any(text, *terms): score += per
        else: findings.append(f"Low relevance for '{cluster}' — add targeted content.")
    if not findings: findings.append("Page content addresses all five LLM query clusters.")
    return min(score, 100), findings


# ── Band + weighted score ─────────────────────────────────────────────────────

def band(score: float) -> str:
    if score >= 67: return "strong"
    if score >= 50: return "good"
    if score >= 35: return "moderate"
    if score >= 20: return "weak"
    return "critical"


def weighted_score(components: dict[str, dict], weights: dict[str, float]) -> float:
    total = sum(components[k]["score"] * weights[k] for k in weights if k in components)
    return round(total, 1)


def make_component(score: int, weight: float, findings: list[str]) -> dict:
    return {"score": score, "weighted": round(score * weight, 2), "findings": findings}


# ── Text narrative generation ─────────────────────────────────────────────────

def generate_text_fields(
    aeo_components: dict,
    geo_components: dict,
    aeo_score: float,
    geo_score: float,
    venue_name: str,
    sub_pages_found: dict[str, str],
) -> dict:
    strengths, weaknesses, quick_wins, priority_fixes = [], [], [], []
    schema_recs, content_recs, linking_recs = [], [], []

    aeo_labels = {
        "structured_data": "Structured Data", "faq_qa_content": "FAQ / Q&A",
        "heading_semantic": "Headings", "internal_linking": "Internal Links",
        "page_speed_proxy": "Page Speed", "content_clarity": "Content Clarity",
    }
    geo_labels = {
        "entity_clarity": "Entity Clarity", "content_chunking": "Chunking",
        "topical_completeness": "Topical Coverage", "external_corroboration": "Corroboration",
        "structured_data_richness": "Schema Richness", "prompt_relevance": "Prompt Relevance",
    }

    all_components = {**{f"AEO:{k}": (v, aeo_labels.get(k, k)) for k, v in aeo_components.items()},
                      **{f"GEO:{k}": (v, geo_labels.get(k, k)) for k, v in geo_components.items()}}

    for key, (comp, label) in all_components.items():
        s = comp["score"]
        engine = key.split(":")[0]
        short  = key.split(":")[1]
        if s >= 70:
            strengths.append(f"{label}: {s}/100")
        elif s < 30:
            weaknesses.append(f"{label}: {s}/100")

    # Schema recommendations
    if aeo_components["structured_data"]["score"] < 50:
        schema_recs.append(
            "Replace LocalBusiness with MusicVenue schema. Add maximumAttendeeCapacity, "
            "geo coordinates, openingHoursSpecification."
        )
    if not any("FAQPage" in f for f in aeo_components.get("structured_data", {}).get("findings", [])):
        schema_recs.append(
            "Add FAQPage JSON-LD wrapping existing FAQ content — "
            "this alone can unlock rich results without any new copy."
        )
    if geo_components["external_corroboration"]["score"] < 40:
        schema_recs.append(
            "Add sameAs to schema pointing to the Wikidata entity (Q-number) "
            "and Wikipedia article."
        )

    # Content recommendations
    if aeo_components["content_clarity"]["score"] < 60:
        content_recs.append(
            "Expand venue page copy to 600+ words covering history, atmosphere, "
            "notable past performances, and practical visitor info."
        )
    if geo_components["topical_completeness"]["score"] < 80:
        missing = [f for f in geo_components["topical_completeness"]["findings"]
                   if "Missing" in f]
        for m in missing[:3]:
            content_recs.append(m.replace("Missing topic coverage: ", "Add content on: "))
    if aeo_components["faq_qa_content"]["score"] < 60:
        faq_sub = sub_pages_found.get("faq", "")
        if faq_sub and not faq_sub.startswith("_try_"):
            content_recs.append(
                f"FAQ page exists at {faq_sub} — add FAQPage schema and embed key Q&As "
                "on the main venue page for maximum AEO impact."
            )
        else:
            content_recs.append(
                "Build a FAQ section answering: 'What is the capacity?', "
                "'How do I get there?', 'Is the venue accessible?', "
                "'What is the age policy?', 'Is there parking nearby?'. "
                "Wrap in FAQPage schema."
            )

    # Linking recommendations
    for cat in ["access", "getting-here", "venue-info"]:
        if cat not in sub_pages_found or sub_pages_found[cat].startswith("_try_"):
            linking_recs.append(f"Create and link a dedicated '{cat}' sub-page.")

    # Quick wins (fast, high-impact)
    if aeo_components["structured_data"]["score"] < 50:
        quick_wins.append(
            "Add MusicVenue JSON-LD with capacity and address — ~30 min, "
            f"+{14 if aeo_components['structured_data']['score'] < 20 else 8} AEO pts estimated."
        )
    if geo_components["external_corroboration"]["score"] < 40:
        quick_wins.append("Add sameAs (Wikidata + Wikipedia) to schema — ~10 min, +8 GEO pts.")
    if geo_components["entity_clarity"]["score"] < 70:
        quick_wins.append(
            "Add capacity, full address, and phone number visibly to the page — ~15 min."
        )

    # Priority fixes
    if aeo_components["faq_qa_content"]["score"] < 30:
        impact = "+10–14"
        faq_sub = sub_pages_found.get("faq", "")
        if faq_sub and not faq_sub.startswith("_try_"):
            priority_fixes.append(
                f"[HIGH] FAQ page exists ({faq_sub}) but lacks FAQPage schema and is not "
                "embedded on main page. Add schema and surface 6+ Q&As on the venue page. "
                f"Estimated AEO impact: {impact} points."
            )
        else:
            priority_fixes.append(
                "[HIGH] Build a FAQ section answering: 'What is the capacity?', "
                "'How do I get there?', 'Is the venue accessible?', 'What is the age policy?', "
                f"'Is there parking nearby?'. Wrap in FAQPage schema. Estimated AEO impact: {impact} points."
            )
    if aeo_components["structured_data"]["score"] < 30:
        priority_fixes.append(
            "[CRITICAL] No MusicVenue schema detected. Implement JSON-LD with type, "
            "capacity, address, and sameAs. Estimated AEO impact: +12–16 points."
        )

    band_str = band(aeo_score)
    summary = (
        f"{venue_name} scores {aeo_score}/100 AEO ({band_str}) and {geo_score}/100 GEO ({band(geo_score)}). "
    )
    if strengths:
        summary += f"Strengths: {strengths[0]}. "
    if priority_fixes:
        summary += "Priority action: " + priority_fixes[0][:120] + "."

    return {
        "summary": summary,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "quick_wins": quick_wins,
        "priority_fixes": priority_fixes,
        "schema_recommendations": schema_recs,
        "content_recommendations": content_recs,
        "internal_linking_recommendations": linking_recs,
    }


# ── Per-venue audit orchestrator ──────────────────────────────────────────────

def audit_venue(venue: dict, session: requests.Session, rate_limit: float) -> dict:
    slug = venue["slug"]
    name = venue["venue_name"]
    url  = venue["url"]
    logger.info("[%s] Fetching %s", slug, url)

    main_soup, resp_ms = fetch(url, session)
    if main_soup is None:
        logger.error("[%s] Failed to fetch main page", slug)
        return {**venue, "crawl_errors": [f"Failed to fetch {url}"]}

    errors: list[str] = []

    # Discover sub-pages from link analysis
    candidates = find_sub_pages(main_soup, url)

    # Try to fetch confirmed + candidate sub-pages
    sub_soups: dict[str, object] = {}
    sub_pages_confirmed: dict[str, str] = {}

    for cat, sub_url in candidates.items():
        is_candidate = cat.startswith("_try_")
        real_cat = cat.replace("_try_", "")
        if real_cat in sub_pages_confirmed:
            continue
        time.sleep(rate_limit * 0.5)  # lighter delay for sub-pages
        sub_soup, _ = fetch(sub_url, session)
        if sub_soup:
            sub_soups[real_cat] = sub_soup
            sub_pages_confirmed[real_cat] = sub_url
            if is_candidate:
                logger.info("  [%s] Found sub-page via guess: %s → %s", slug, real_cat, sub_url)
            else:
                logger.info("  [%s] Found sub-page via link: %s → %s", slug, real_cat, sub_url)

    all_soups = [main_soup] + list(sub_soups.values())
    all_schemas = []
    for s in all_soups:
        all_schemas.extend(extract_schemas(s))

    # Combine visible text from all pages
    text_parts = [visible_text(s) for s in all_soups]
    text_all = " ".join(text_parts)

    # ── Score all components ──
    sd_score,  sd_find  = score_structured_data(all_schemas)
    faq_score, faq_find = score_faq_content(all_soups, all_schemas, sub_pages_confirmed)
    h_score,   h_find   = score_heading_semantic(main_soup, name)
    il_score,  il_find  = score_internal_linking(main_soup, sub_pages_confirmed)
    ps_score,  ps_find  = score_page_speed(resp_ms)
    cc_score,  cc_find  = score_content_clarity(all_soups, text_all)

    ec_score,  ec_find  = score_entity_clarity(text_all, all_schemas)
    ch_score,  ch_find  = score_content_chunking(all_soups)
    tc_score,  tc_find  = score_topical_completeness(text_all)
    xc_score,  xc_find  = score_external_corroboration(all_soups, all_schemas)
    sr_score,  sr_find  = score_schema_richness(all_schemas)
    pr_score,  pr_find  = score_prompt_relevance(text_all)

    aeo_components = {
        "structured_data":  make_component(sd_score,  AEO_WEIGHTS["structured_data"],  sd_find),
        "faq_qa_content":   make_component(faq_score, AEO_WEIGHTS["faq_qa_content"],   faq_find),
        "heading_semantic": make_component(h_score,   AEO_WEIGHTS["heading_semantic"],  h_find),
        "internal_linking": make_component(il_score,  AEO_WEIGHTS["internal_linking"],  il_find),
        "page_speed_proxy": make_component(ps_score,  AEO_WEIGHTS["page_speed_proxy"],  ps_find),
        "content_clarity":  make_component(cc_score,  AEO_WEIGHTS["content_clarity"],   cc_find),
    }
    geo_components = {
        "entity_clarity":          make_component(ec_score, GEO_WEIGHTS["entity_clarity"],          ec_find),
        "content_chunking":        make_component(ch_score, GEO_WEIGHTS["content_chunking"],        ch_find),
        "topical_completeness":    make_component(tc_score, GEO_WEIGHTS["topical_completeness"],    tc_find),
        "external_corroboration":  make_component(xc_score, GEO_WEIGHTS["external_corroboration"],  xc_find),
        "structured_data_richness": make_component(sr_score, GEO_WEIGHTS["structured_data_richness"], sr_find),
        "prompt_relevance":        make_component(pr_score, GEO_WEIGHTS["prompt_relevance"],        pr_find),
    }

    aeo = weighted_score(aeo_components, AEO_WEIGHTS)
    geo = weighted_score(geo_components, GEO_WEIGHTS)

    texts = generate_text_fields(
        aeo_components, geo_components, aeo, geo, name, sub_pages_confirmed
    )

    return {
        **venue,
        "aeo_score":       aeo,
        "geo_score":       geo,
        "aeo_band":        band(aeo),
        "geo_band":        band(geo),
        "aeo_components":  aeo_components,
        "geo_components":  geo_components,
        "crawl_errors":    errors,
        **texts,
    }


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Audit venue websites for real AEO/GEO scores.")
    parser.add_argument("--dry-run",    action="store_true", help="Print URLs only, no fetching.")
    parser.add_argument("--venue",      default="",          help="Single venue slug to audit.")
    parser.add_argument("--output",     default=str(VENUES_FILE), help="Output JSON path.")
    parser.add_argument("--rate-limit", type=float, default=1.0, metavar="SECONDS",
                        help="Pause between venues in seconds (default: 1.0).")
    args = parser.parse_args()

    venues: list[dict] = json.loads(Path(VENUES_FILE).read_text())

    if args.venue:
        targets = [v for v in venues if v["slug"] == args.venue]
        if not targets:
            print(f"No venue with slug {args.venue!r}")
            return
    else:
        targets = venues

    if args.dry_run:
        print(f"\nDry run — would audit {len(targets)} venue(s):\n")
        for v in targets:
            print(f"  {v['slug']:<45} {v['url']}")
            for cat, sigs in SUB_PAGE_SIGNALS.items():
                print(f"    sub-page to find: {cat} ({', '.join(sigs[:2])})")
        return

    session    = make_session()
    output     = Path(args.output)
    results    = {v["slug"]: v for v in venues}   # preserve untouched venues

    for i, venue in enumerate(targets, 1):
        logger.info("[%d/%d] Auditing: %s", i, len(targets), venue["venue_name"])
        updated = audit_venue(venue, session, args.rate_limit)
        results[venue["slug"]] = updated
        logger.info(
            "  → AEO %.1f (%s)  GEO %.1f (%s)",
            updated["aeo_score"], updated["aeo_band"],
            updated["geo_score"], updated["geo_band"],
        )
        if i < len(targets):
            time.sleep(args.rate_limit)

    output.write_text(json.dumps(list(results.values()), indent=2))
    logger.info("Written → %s (%d venues)", output, len(results))

    # Print summary table
    print(f"\n{'Venue':<45} {'AEO':>6} {'GEO':>6}  AEO Band")
    print("─" * 72)
    for v in list(results.values()):
        if v["slug"] in {t["slug"] for t in targets}:
            print(f"{v['venue_name']:<45} {v['aeo_score']:>6.1f} {v['geo_score']:>6.1f}  {v['aeo_band']}")


if __name__ == "__main__":
    main()

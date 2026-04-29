#!/usr/bin/env python3
"""
citation_runner.py — Real LLM citation measurement for O2/AMG venues.

Sends each test prompt to the Claude or OpenAI API, detects which portfolio
venues are mentioned in the response, and writes results to
data/citation_results.json — preserving all metadata (monthly search
volumes, intent categories, relevant_prompt_ids, gap_analysis).

Requirements:
    pip install anthropic openai   # install both; only the chosen one is used
    export ANTHROPIC_API_KEY=sk-ant-...   # for --provider anthropic (default)
    export OPENAI_API_KEY=sk-...          # for --provider openai

Usage:
    # Dry run — show prompts and API call plan, no charges
    python citation_runner.py --dry-run

    # Full live run with Claude (default)
    python citation_runner.py

    # Full live run with ChatGPT
    python citation_runner.py --provider openai --model gpt-4o

    # Run only specific prompts
    python citation_runner.py --prompts p01,p07,p12

    # Debug — save raw LLM responses to data/citation_debug.json
    python citation_runner.py --debug

    # Verbose — print each LLM response to stdout
    python citation_runner.py --verbose

    # Write to a custom output file
    python citation_runner.py --output data/citation_test.json
"""

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
VENUES_FILE = DATA_DIR / "venues_sample.json"
CITATIONS_FILE = DATA_DIR / "citation_results.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Band thresholds ───────────────────────────────────────────────────────────

def citation_band(rate: float) -> str:
    if rate >= 67: return "strong"
    if rate >= 45: return "good"
    if rate >= 25: return "moderate"
    if rate >= 10: return "weak"
    return "critical"


# ── Per-venue relevance map (which prompts are topically relevant) ────────────
# A venue should only be measured against prompts that make geographic /
# topical sense for it.  Prompts outside a venue's region are excluded so
# citation rates reflect genuine performance, not off-topic misses.

RELEVANT_PROMPTS: dict[str, list[str]] = {
    # p01-p05 are UK-wide (relevant to all); p06-p20 are venue/region-specific
    "o2-academy-brixton":           ["p01","p02","p03","p04","p05","p06","p07","p10","p19","p20"],
    "o2-academy-islington":         ["p01","p02","p03","p04","p05","p19","p20"],
    "o2-forum-kentish-town":        ["p01","p02","p03","p04","p05","p08","p19","p20"],
    "o2-shepherds-bush-empire":     ["p01","p02","p03","p04","p05","p09","p19","p20"],
    "o2-academy-birmingham":        ["p01","p02","p03","p04","p05","p14","p19","p20"],
    "o2-institute-birmingham":      ["p01","p02","p03","p04","p05","p14","p19","p20"],
    "o2-academy-leicester":         ["p01","p02","p03","p04","p05","p19","p20"],
    "o2-academy-oxford":            ["p01","p02","p03","p04","p05","p19","p20"],
    "o2-academy-bournemouth":       ["p01","p02","p03","p04","p05","p19","p20"],
    "o2-academy-bristol":           ["p01","p02","p03","p04","p05","p18","p19","p20"],
    "o2-guildhall-southampton":     ["p01","p02","p03","p04","p05","p19","p20"],
    "o2-academy-liverpool":         ["p01","p02","p03","p04","p05","p19","p20"],
    "o2-ritz-manchester":           ["p01","p02","p03","p04","p05","p19","p20"],
    "o2-victoria-warehouse-manchester": ["p01","p02","p03","p04","p05","p13","p19","p20"],
    "o2-apollo-manchester":         ["p01","p02","p03","p04","p05","p11","p12","p19","p20"],
    "o2-academy-leeds":             ["p01","p02","p03","p04","p05","p17","p19","p20"],
    "o2-academy-sheffield":         ["p01","p02","p03","p04","p05","p19","p20"],
    "o2-city-hall-newcastle":       ["p01","p02","p03","p04","p05","p19","p20"],
    "o2-academy-glasgow":           ["p01","p02","p03","p04","p05","p16","p19","p20"],
    "edinburgh-corn-exchange":      ["p01","p02","p03","p04","p05","p15","p19","p20"],
}

GAP_ADVICE: dict[str, str] = {
    "p01": "Add a clear bag policy page and FAQ entry. Ensure FAQPage schema is implemented on the /faqs page with a bag policy Q&A.",
    "p02": "Publish explicit age restriction information on the venue page and in FAQPage schema. LLMs pull from structured FAQ content.",
    "p03": "Add a FAQ entry clarifying on-door ticket policy. Many venues sell remaining tickets on the door — if you do, state it clearly.",
    "p04": "Add finish/curfew time information to the venue FAQ. This is one of the highest-volume pre-visit queries.",
    "p05": "Publish a dedicated accessibility page with specific details (step-free access, hearing loops, companion tickets). Link from nav.",
    "p06": "Add a 'Getting Here' page with tube line, nearest stop (Brixton, Victoria line), and walking directions. Add TransportationRoute schema.",
    "p07": "Add capacity and seating/standing format explicitly to the venue page and MusicVenue schema (maximumAttendeeCapacity field).",
    "p08": "Add nearest tube/Overground station to the Kentish Town Forum 'Getting Here' page. Include walking time from station.",
    "p09": "Add capacity and standing/seated info to Shepherd's Bush Empire venue page and MusicVenue structured data.",
    "p10": "Add a 'When to arrive' FAQ entry for Brixton. Recommend doors time + 30 mins for busy shows. This drives repeat visits.",
    "p11": "Add parking info and tram directions to the Apollo Manchester 'Getting Here' page. Metrolink stop: Deansgate-Castlefield.",
    "p12": "Add O2 Apollo Manchester capacity (3,500) to the venue page, FAQ, and MusicVenue schema.",
    "p13": "Add event type content to Victoria Warehouse page — electronic, dance, and club night heritage content improves topical authority.",
    "p14": "Add Birmingham New Street / Moor Street walking directions to O2 Academy Birmingham 'Getting Here' page.",
    "p15": "Add atmosphere, capacity, and format details for Edinburgh Corn Exchange. Include a 'What to expect' section.",
    "p16": "Add capacity and standing/seated format to O2 Academy Glasgow venue page and MusicVenue schema.",
    "p17": "Add hotel recommendations or a 'Staying nearby' section to the Leeds venue page. Affiliate links or local partner hotels.",
    "p18": "Add food and drink information to O2 Academy Bristol venue page. List bars, food stalls, and drink policies.",
    "p19": "Add a clear refund/exchange policy page linked from ticketing. Include in FAQPage schema.",
    "p20": "Ensure venue pages link prominently to event listings. Add Event structured data for upcoming shows to improve LLM discoverability.",
}


# ── Result aggregation ────────────────────────────────────────────────────────

def aggregate(
    slugs: list[str],
    prompt_results: list[dict],
    existing_venues: dict,
) -> dict:
    """Build the venues dict from fresh citation results + preserved metadata."""
    all_ids = [p["prompt_id"] for p in prompt_results]
    total = len(all_ids)

    cited_by: dict[str, list[str]] = {s: [] for s in slugs}
    for r in prompt_results:
        for slug in r.get("venues_cited", []):
            if slug in cited_by:
                cited_by[slug].append(r["prompt_id"])

    venues_out = {}
    for slug in slugs:
        cited = cited_by[slug]
        missed = [pid for pid in all_ids if pid not in cited]
        count = len(cited)
        rate = round(count / total * 100, 1) if total else 0.0

        rel_ids = RELEVANT_PROMPTS.get(slug, [])
        rel_cited = [pid for pid in rel_ids if pid in cited]
        rel_missed = [pid for pid in rel_ids if pid not in cited]
        rel_count = len(rel_cited)
        rel_total = len(rel_ids)
        rel_rate = round(rel_count / rel_total * 100, 1) if rel_total else 0.0

        gap = [
            {"prompt_id": pid, "advice": GAP_ADVICE.get(pid, "Add targeted content for this query type.")}
            for pid in rel_missed[:5]
        ]

        venues_out[slug] = {
            "citation_count": count,
            "citation_rate": rate,
            "citation_band": citation_band(rate),
            "cited_by_prompts": cited,
            "missed_by_prompts": missed,
            "relevant_prompt_ids": rel_ids,
            "relevant_citation_count": rel_count,
            "relevant_citation_rate": rel_rate,
            "relevant_citation_band": citation_band(rel_rate),
            "gap_analysis": gap,
        }

    return venues_out


def build_prompts_block(
    prompt_results: list[dict],
    prompt_objects,
) -> list[dict]:
    """Merge API results with static prompt metadata."""
    prompt_meta = {p.id: p for p in prompt_objects}
    out = []
    for r in prompt_results:
        pid = r["prompt_id"]
        p = prompt_meta.get(pid)
        entry = {
            "id": pid,
            "text": r["prompt_text"],
            "venues_cited": r.get("venues_cited", []),
        }
        if p:
            entry["monthly_searches"] = p.monthly_searches
            entry["intent_category"] = p.intent_category
            entry["topic_tags"] = p.topic_tags
        out.append(entry)
    return out


# ── Summary printer ───────────────────────────────────────────────────────────

def print_summary(venues_out: dict, venues: list[dict]) -> None:
    name_map = {v["slug"]: v["venue_name"] for v in venues}
    ranked = sorted(venues_out.items(), key=lambda x: x[1]["relevant_citation_rate"], reverse=True)

    print(f"\n{'Venue':<45} {'All':>7} {'Relevant':>10}  Band")
    print("─" * 80)
    for slug, r in ranked:
        name = name_map.get(slug, slug)
        all_r = f"{r['citation_count']}/{r['citation_count'] + len(r['missed_by_prompts'])} ({r['citation_rate']}%)"
        rel_r = f"{r['relevant_citation_count']}/{len(r['relevant_prompt_ids'])} ({r['relevant_citation_rate']}%)"
        print(f"{name:<45} {all_r:>12}  {rel_r:>13}  {r['relevant_citation_band']}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run LLM citation test prompts against the Claude API.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would run — no API calls, no file writes.",
    )
    parser.add_argument(
        "--provider",
        default="anthropic",
        choices=["anthropic", "openai"],
        help="LLM provider: anthropic (default) or openai",
    )
    parser.add_argument(
        "--model",
        default="",
        help="Model name (default: claude-opus-4-5 for anthropic, gpt-4o for openai)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Save raw LLM responses to data/citation_debug.json for inspection.",
    )
    parser.add_argument(
        "--prompts",
        default="",
        help="Comma-separated prompt IDs to run (default: all 20). E.g. p01,p07,p12",
    )
    parser.add_argument(
        "--output",
        default=str(CITATIONS_FILE),
        help=f"Output JSON path (default: {CITATIONS_FILE})",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print each LLM response in full.",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=0.5,
        metavar="SECONDS",
        help="Pause between API calls in seconds (default: 0.5)",
    )
    args = parser.parse_args()

    # Load data
    venues = json.loads(VENUES_FILE.read_text())
    output_path = Path(args.output)

    try:
        existing = json.loads(output_path.read_text()) if output_path.exists() else {}
    except json.JSONDecodeError:
        existing = {}

    from llm_simulation.prompts import PROMPTS

    # Filter prompts if requested
    if args.prompts:
        ids = {p.strip() for p in args.prompts.split(",")}
        prompts = [p for p in PROMPTS if p.id in ids]
        unknown = ids - {p.id for p in PROMPTS}
        if unknown:
            logger.warning("Unknown prompt IDs: %s", ", ".join(sorted(unknown)))
    else:
        prompts = PROMPTS

    # Resolve model default per provider
    provider = args.provider
    if args.model:
        model = args.model
    elif provider == "openai":
        model = "gpt-4o"
    else:
        model = "claude-opus-4-5"

    # ── Dry run ───────────────────────────────────────────────────────────────
    if args.dry_run:
        print(f"\nDry run — {len(prompts)} prompt(s) would be sent to {model} via {provider}\n")
        total_monthly = sum(p.monthly_searches for p in prompts)
        for p in prompts:
            print(f"  [{p.id}] {p.text}")
            print(f"         intent={p.intent_category}  region={p.region_filter or 'UK-wide'}  "
                  f"searches={p.monthly_searches:,}/mo")
        print(f"\nTotal monthly search coverage: {total_monthly:,}/mo ({total_monthly//30:,}/day)\n")
        return

    # ── Live run ──────────────────────────────────────────────────────────────
    logger.info("Starting citation run: %d prompts, provider=%s, model=%s", len(prompts), provider, model)

    from llm_simulation.runner import run_live

    results = run_live(
        venues=venues,
        prompts=prompts,
        model=model,
        provider=provider,
        rate_limit_s=args.rate_limit,
        verbose=args.verbose,
    )

    # Fail loudly if every call errored — surfaces API key / quota problems
    error_count = sum(1 for r in results if r.response_text.startswith("__ERROR__"))
    if error_count == len(results):
        first_err = next(r.response_text for r in results if r.response_text.startswith("__ERROR__"))
        logger.error("All %d prompts failed. First error: %s", len(results), first_err)
        sys.exit(1)
    elif error_count:
        logger.warning("%d/%d prompts failed — partial results written.", error_count, len(results))

    # ── Debug dump ────────────────────────────────────────────────────────────
    if args.debug:
        debug_path = DATA_DIR / "citation_debug.json"
        debug_data = [
            {
                "prompt_id": r.prompt_id,
                "prompt_text": r.prompt_text,
                "venues_cited": r.venues_cited,
                "response_text": r.response_text,
            }
            for r in results
        ]
        debug_path.write_text(json.dumps(debug_data, indent=2))
        logger.info("Debug responses written → %s", debug_path)

    # If we ran only a subset, merge with existing prompt results
    if args.prompts and existing.get("prompts"):
        run_ids = {r.prompt_id for r in results}
        kept = [p for p in existing["prompts"] if p["id"] not in run_ids]
        raw_results = [
            {"prompt_id": r.prompt_id, "prompt_text": r.prompt_text, "venues_cited": r.venues_cited}
            for r in results
        ]
        all_results = kept + [
            {"prompt_id": p["prompt_id"], "prompt_text": p["text"], "venues_cited": p["venues_cited"]}
            for p in kept
        ]
        # Rebuild properly
        prompt_results_for_agg = [
            {"prompt_id": r.prompt_id, "prompt_text": r.prompt_text, "venues_cited": r.venues_cited}
            for r in results
        ]
        # Extend with un-run existing prompts
        existing_by_id = {p["id"]: p for p in existing.get("prompts", [])}
        for pid, ep in existing_by_id.items():
            if pid not in {r.prompt_id for r in results}:
                prompt_results_for_agg.append({
                    "prompt_id": pid,
                    "prompt_text": ep["text"],
                    "venues_cited": ep.get("venues_cited", []),
                })
    else:
        prompt_results_for_agg = [
            {"prompt_id": r.prompt_id, "prompt_text": r.prompt_text, "venues_cited": r.venues_cited}
            for r in results
        ]

    slugs = [v["slug"] for v in venues]
    venues_out = aggregate(slugs, prompt_results_for_agg, existing.get("venues", {}))
    prompts_block = build_prompts_block(prompt_results_for_agg, PROMPTS)

    output = {
        "run_date": str(date.today()),
        "model": f"{provider}/{model}",
        "total_prompts": len(prompt_results_for_agg),
        "venues": venues_out,
        "prompts": prompts_block,
    }

    output_path.write_text(json.dumps(output, indent=2))
    logger.info("Written → %s", output_path)

    print_summary(venues_out, venues)
    print(f"\nRun date: {output['run_date']}  Model: {args.model}")
    print(f"Output:   {output_path}\n")


if __name__ == "__main__":
    main()

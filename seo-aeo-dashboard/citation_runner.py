#!/usr/bin/env python3
"""
citation_runner.py — Real LLM citation measurement for O2/AMG venues.

For each venue, sends 15 venue-specific prompts to the LLM (e.g.
"What is the capacity of O2 Academy Brixton?") and checks whether the
response actually cites that venue. This measures how well LLMs know
each venue specifically, across three question categories:

  must-answer   — capacity, transport, doors, standing/seated, bag policy
  demand-driven — atmosphere, best spots, food & drink, arrival, accessibility
  geo-stress    — reputation, famous acts, history, comparison, music types

Requirements:
    pip install anthropic openai   # install both; only the chosen one is used
    export ANTHROPIC_API_KEY=sk-ant-...   # for --provider anthropic (default)
    export OPENAI_API_KEY=sk-...          # for --provider openai

Usage:
    # Dry run — show prompts per venue, no API calls
    python citation_runner.py --dry-run

    # Full live run (20 venues × 15 prompts = 300 API calls)
    python citation_runner.py --provider openai --model gpt-4o

    # Run a single venue only
    python citation_runner.py --venue o2-academy-brixton

    # Debug — save raw LLM responses to data/citation_debug.json
    python citation_runner.py --debug

    # Verbose — print each LLM response to stdout
    python citation_runner.py --verbose
"""

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
VENUES_FILE      = DATA_DIR / "venues_sample.json"
COMPETITORS_FILE = DATA_DIR / "competitors_sample.json"
CITATIONS_FILE   = DATA_DIR / "citation_results.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "You are a knowledgeable UK music industry expert. "
    "Answer questions about live music venues accurately, helpfully, and concisely. "
    "Name specific real venues where relevant. Do not invent venues."
)


def citation_band(rate: float) -> str:
    if rate >= 67: return "strong"
    if rate >= 45: return "good"
    if rate >= 25: return "moderate"
    if rate >= 10: return "weak"
    return "critical"


def venue_is_cited(response: str, venue_name: str, slug: str) -> bool:
    """Return True if the response mentions this specific venue."""
    lower = response.lower()
    name_lower = venue_name.lower()

    # Direct name match
    if name_lower in lower:
        return True

    # Slug-derived short names (e.g. "brixton" for o2-academy-brixton)
    # Also check known distinctive words per slug
    SLUG_SIGNALS: dict[str, list[str]] = {
        # Portfolio venues
        "o2-academy-brixton":            ["brixton academy", "o2 brixton"],
        "o2-academy-islington":          ["islington academy", "o2 islington"],
        "o2-forum-kentish-town":         ["kentish town forum", "forum kentish town", "o2 forum"],
        "o2-shepherds-bush-empire":      ["shepherd's bush empire", "shepherds bush empire", "bush empire"],
        "o2-academy-birmingham":         ["birmingham academy", "o2 birmingham"],
        "o2-institute-birmingham":       ["institute birmingham", "birmingham institute", "o2 institute"],
        "o2-academy-leicester":          ["leicester academy", "o2 leicester"],
        "o2-academy-oxford":             ["oxford academy", "o2 oxford"],
        "o2-academy-bournemouth":        ["bournemouth academy", "o2 bournemouth"],
        "o2-academy-bristol":            ["bristol academy", "o2 bristol"],
        "o2-guildhall-southampton":      ["guildhall southampton", "southampton guildhall"],
        "o2-academy-liverpool":          ["liverpool academy", "o2 liverpool"],
        "o2-ritz-manchester":            ["ritz manchester", "manchester ritz", "o2 ritz"],
        "o2-victoria-warehouse-manchester": ["victoria warehouse"],
        "o2-apollo-manchester":          ["apollo manchester", "manchester apollo", "o2 apollo"],
        "o2-academy-leeds":              ["leeds academy", "o2 leeds"],
        "o2-academy-sheffield":          ["sheffield academy", "o2 sheffield"],
        "o2-city-hall-newcastle":        ["city hall newcastle", "newcastle city hall", "o2 newcastle"],
        "o2-academy-glasgow":            ["glasgow academy", "o2 glasgow"],
        "edinburgh-corn-exchange":       ["corn exchange edinburgh", "edinburgh corn exchange"],
        # Competitor venues
        "roundhouse":                    ["roundhouse"],
        "koko-london":                   ["koko"],
        "electric-ballroom":             ["electric ballroom"],
        "fabric-london":                 ["fabric london", "fabric club"],
        "manchester-academy":            ["manchester academy", "academy manchester"],
        "band-on-the-wall":              ["band on the wall"],
        "leadmill-sheffield":            ["leadmill", "the leadmill"],
        "brudenell-social-club":         ["brudenell"],
        "swx-bristol":                   ["swx"],
        "usher-hall-edinburgh":          ["usher hall"],
    }
    for sig in SLUG_SIGNALS.get(slug, []):
        if sig in lower:
            return True
    return False


def find_also_cited(response: str, excluded_slug: str, all_venues: list[dict]) -> list[str]:
    """Return slugs of other venues mentioned in the response, excluding the target venue."""
    return [
        v["slug"] for v in all_venues
        if v["slug"] != excluded_slug
        and venue_is_cited(response, v["venue_name"], v["slug"])
    ]


def _call_anthropic(client, model: str, prompt_text: str) -> str:
    message = client.messages.create(
        model=model,
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt_text}],
    )
    return message.content[0].text


def _call_openai(client, model: str, prompt_text: str) -> str:
    response = client.chat.completions.create(
        model=model,
        max_tokens=600,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text},
        ],
    )
    return response.choices[0].message.content


def print_summary(venues_out: dict, venues: list[dict]) -> None:
    name_map = {v["slug"]: v["venue_name"] for v in venues}
    ranked = sorted(venues_out.items(), key=lambda x: x[1]["citation_rate"], reverse=True)
    total = next(iter(venues_out.values()), {}).get("citation_count", 0)
    n_prompts = len(next(iter(venues_out.values()), {}).get("prompts", []))

    print(f"\n{'Venue':<45} {'Cited':>6} {'Rate':>7}  Band")
    print("─" * 72)
    for slug, r in ranked:
        name = name_map.get(slug, slug)
        rate_str = f"{r['citation_rate']}%"
        cited_str = f"{r['citation_count']}/{n_prompts}"
        print(f"{name:<45} {cited_str:>6}  {rate_str:>6}  {r['citation_band']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run venue-specific LLM citation prompts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Show prompts that would run — no API calls.")
    parser.add_argument("--provider", default="anthropic", choices=["anthropic", "openai"],
                        help="LLM provider (default: anthropic)")
    parser.add_argument("--model", default="",
                        help="Model name (default: claude-opus-4-5 / gpt-4o)")
    parser.add_argument("--venue", default="",
                        help="Run for a single venue slug only (default: all 20)")
    parser.add_argument("--debug", action="store_true",
                        help="Save raw LLM responses to data/citation_debug.json")
    parser.add_argument("--verbose", action="store_true",
                        help="Print each LLM response to stdout")
    parser.add_argument("--output", default=str(CITATIONS_FILE),
                        help=f"Output JSON path (default: {CITATIONS_FILE})")
    parser.add_argument("--rate-limit", type=float, default=0.5, metavar="SECONDS",
                        help="Pause between API calls in seconds (default: 0.5)")
    args = parser.parse_args()

    venues_data = json.loads(VENUES_FILE.read_text())
    competitors_data = json.loads(COMPETITORS_FILE.read_text()) if COMPETITORS_FILE.exists() else []
    all_venues = venues_data + competitors_data  # used for also_cited detection

    if args.venue:
        venues_data = [v for v in venues_data if v["slug"] == args.venue]
        if not venues_data:
            logger.error("No venue found with slug %r", args.venue)
            sys.exit(1)

    from llm_simulation.prompts import PROMPT_TEMPLATES

    provider = args.provider
    model = args.model or ("gpt-4o" if provider == "openai" else "claude-opus-4-5")
    output_path = Path(args.output)

    total_calls = len(venues_data) * len(PROMPT_TEMPLATES)

    # ── Dry run ───────────────────────────────────────────────────────────────
    if args.dry_run:
        print(f"\nDry run — {total_calls} API calls ({len(venues_data)} venues × {len(PROMPT_TEMPLATES)} prompts)")
        print(f"Provider: {provider}  Model: {model}\n")
        for v in venues_data[:3]:
            print(f"  {v['venue_name']}:")
            for t in PROMPT_TEMPLATES[:3]:
                print(f"    [{t.id}] {t.for_venue(v['venue_name'])}")
            print(f"    … {len(PROMPT_TEMPLATES) - 3} more prompts")
        if len(venues_data) > 3:
            print(f"  … {len(venues_data) - 3} more venues")
        return

    # ── Set up API client ─────────────────────────────────────────────────────
    if provider == "anthropic":
        try:
            import anthropic
        except ImportError:
            raise ImportError("pip install anthropic")
        api_key = __import__("os").environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY is not set.")
        client = anthropic.Anthropic(api_key=api_key)
        call_fn = lambda text: _call_anthropic(client, model, text)
    else:
        try:
            import openai as openai_module
        except ImportError:
            raise ImportError("pip install openai")
        api_key = __import__("os").environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY is not set.")
        client = openai_module.OpenAI(api_key=api_key)
        call_fn = lambda text: _call_openai(client, model, text)

    import time

    logger.info("Starting run: %d venues × %d prompts = %d calls (%s / %s)",
                len(venues_data), len(PROMPT_TEMPLATES), total_calls, provider, model)

    # ── Per-venue prompt loop ─────────────────────────────────────────────────
    debug_log: list[dict] = []
    venues_out: dict[str, dict] = {}
    call_n = 0
    error_count = 0

    # Load existing output so we can merge if running a single venue
    try:
        existing = json.loads(output_path.read_text()) if output_path.exists() else {}
    except json.JSONDecodeError:
        existing = {}

    for v in venues_data:
        slug = v["slug"]
        name = v["venue_name"]
        prompt_results = []

        for t in PROMPT_TEMPLATES:
            call_n += 1
            prompt_text = t.for_venue(name)
            logger.info("[%d/%d] %s — %s", call_n, total_calls, name, t.id)

            try:
                response_text = call_fn(prompt_text)
            except Exception as exc:
                logger.error("  FAILED: %s", exc)
                response_text = f"__ERROR__: {exc}"
                error_count += 1

            if response_text.startswith("__ERROR__"):
                cited = False
                also_cited: list[str] = []
            else:
                cited = venue_is_cited(response_text, name, slug)
                also_cited = [] if cited else find_also_cited(response_text, slug, all_venues)

            if args.verbose:
                logger.info("  Response: %s", response_text[:200])
            logger.info("  Cited: %s  Also cited: %s", cited, also_cited or "-")

            if args.debug:
                debug_log.append({
                    "venue": slug,
                    "prompt_id": t.id,
                    "prompt_text": prompt_text,
                    "cited": cited,
                    "also_cited": also_cited,
                    "response_text": response_text,
                })

            entry: dict = {
                "id": t.id,
                "text": prompt_text,
                "monthly_searches": t.monthly_searches,
                "intent_category": t.intent_category,
                "topic_tags": t.topic_tags,
                "cited": cited,
                "advice": t.advice,
            }
            if also_cited:
                entry["also_cited"] = also_cited
            prompt_results.append(entry)

            if call_n < total_calls:
                time.sleep(args.rate_limit)

        citation_count = sum(1 for p in prompt_results if p["cited"])
        total = len(prompt_results)
        rate = round(citation_count / total * 100, 1) if total else 0.0

        venues_out[slug] = {
            "citation_count": citation_count,
            "citation_rate": rate,
            "citation_band": citation_band(rate),
            "prompts": prompt_results,
        }

    if error_count == total_calls:
        first_err = next(
            (d["response_text"] for d in debug_log if d["response_text"].startswith("__ERROR__")),
            "Unknown error"
        )
        logger.error("All %d calls failed. First error: %s", total_calls, first_err)
        sys.exit(1)
    elif error_count:
        logger.warning("%d/%d calls failed — partial results written.", error_count, total_calls)

    if args.debug:
        debug_path = DATA_DIR / "citation_debug.json"
        debug_path.write_text(json.dumps(debug_log, indent=2))
        logger.info("Debug log → %s", debug_path)

    # Merge with existing when running a single venue
    if args.venue and existing.get("venues"):
        merged = dict(existing["venues"])
        merged.update(venues_out)
        venues_out = merged

    output = {
        "run_date": str(date.today()),
        "model": f"{provider}/{model}",
        "prompts_per_venue": len(PROMPT_TEMPLATES),
        "venues": venues_out,
    }

    output_path.write_text(json.dumps(output, indent=2))
    logger.info("Written → %s", output_path)

    # ── Append to citation history ────────────────────────────────────────────
    history_path = DATA_DIR / "citation_history.json"
    try:
        citation_history = json.loads(history_path.read_text()) if history_path.exists() else {}
    except json.JSONDecodeError:
        citation_history = {}

    today = str(date.today())
    for slug, v in venues_out.items():
        if slug not in citation_history:
            citation_history[slug] = []
        # Remove any existing entry for today (idempotent re-runs)
        citation_history[slug] = [s for s in citation_history[slug] if s["date"] != today]
        citation_history[slug].append({
            "date":           today,
            "week":           len(citation_history[slug]) + 1,
            "citation_rate":  v["citation_rate"],
            "citation_count": v["citation_count"],
            "citation_band":  v["citation_band"],
        })
        # Keep only the most recent 8 snapshots
        citation_history[slug] = citation_history[slug][-8:]

    history_path.write_text(json.dumps(citation_history, indent=2))
    logger.info("Citation history updated → %s", history_path)

    print_summary(venues_out, json.loads(VENUES_FILE.read_text()))
    print(f"\nRun date: {output['run_date']}  Model: {model}")
    print(f"Output:   {output_path}\n")


if __name__ == "__main__":
    main()

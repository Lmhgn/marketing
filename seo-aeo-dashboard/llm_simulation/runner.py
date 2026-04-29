"""
LLM citation runner — sends each prompt to the Claude or OpenAI API and
detects which O2/AMG venues are mentioned in each response.

Detection strategy:
  Two-tier matching per venue:
  1. Alias list  — multi-word phrases that unambiguously identify the venue
  2. Signature words — single distinctive terms used only for that venue
     (e.g. "brixton", "kentish town", "corn exchange") that are highly
     unlikely to appear in a UK music venue context for any other reason.

  Both checks are case-insensitive substring matches against the full
  lowercased response text.

Requirements (install both so either provider works):
    pip install anthropic openai
    export ANTHROPIC_API_KEY=sk-ant-...   # for Claude
    export OPENAI_API_KEY=sk-...          # for ChatGPT
"""

import os
import re
import time
import logging
from dataclasses import dataclass, field

from .prompts import Prompt

logger = logging.getLogger(__name__)

DEFAULT_ANTHROPIC_MODEL = "claude-opus-4-5"
DEFAULT_OPENAI_MODEL    = "gpt-4o"

SYSTEM_PROMPT = (
    "You are a knowledgeable UK music industry expert. "
    "Answer questions about live music venues accurately, helpfully, and concisely. "
    "Name specific real venues where relevant. Do not invent venues."
)

# ── Multi-word aliases (all must be substrings of the lowercased response) ────
VENUE_ALIASES: dict[str, list[str]] = {
    "o2-academy-brixton": [
        "o2 academy brixton", "brixton academy", "o2 brixton",
        "academy brixton",
    ],
    "o2-academy-islington": [
        "o2 academy islington", "islington academy", "academy islington",
        "o2 islington",
    ],
    "o2-forum-kentish-town": [
        "o2 forum kentish town", "forum kentish town", "kentish town forum",
        "o2 forum",
    ],
    "o2-shepherds-bush-empire": [
        "o2 shepherd's bush empire", "o2 shepherds bush empire",
        "shepherd's bush empire", "shepherds bush empire", "bush empire",
        "shepherd's bush", "shepherds bush",
    ],
    "o2-academy-birmingham": [
        "o2 academy birmingham", "birmingham academy", "academy birmingham",
        "o2 birmingham",
    ],
    "o2-institute-birmingham": [
        "o2 institute birmingham", "institute birmingham",
        "birmingham institute", "o2 institute",
    ],
    "o2-academy-leicester": [
        "o2 academy leicester", "leicester academy", "academy leicester",
        "o2 leicester",
    ],
    "o2-academy-oxford": [
        "o2 academy oxford", "oxford academy", "academy oxford",
        "o2 oxford",
    ],
    "o2-academy-bournemouth": [
        "o2 academy bournemouth", "bournemouth academy", "academy bournemouth",
        "o2 bournemouth",
    ],
    "o2-academy-bristol": [
        "o2 academy bristol", "bristol academy", "academy bristol",
        "o2 bristol",
    ],
    "o2-guildhall-southampton": [
        "o2 guildhall southampton", "guildhall southampton",
        "southampton guildhall", "o2 guildhall",
    ],
    "o2-academy-liverpool": [
        "o2 academy liverpool", "liverpool academy", "academy liverpool",
        "o2 liverpool",
    ],
    "o2-ritz-manchester": [
        "o2 ritz manchester", "ritz manchester", "the ritz manchester",
        "manchester ritz", "o2 ritz",
    ],
    "o2-victoria-warehouse-manchester": [
        "o2 victoria warehouse manchester", "victoria warehouse manchester",
        "victoria warehouse", "o2 victoria warehouse",
    ],
    "o2-apollo-manchester": [
        "o2 apollo manchester", "apollo manchester", "manchester apollo",
        "the apollo manchester", "o2 apollo",
    ],
    "o2-academy-leeds": [
        "o2 academy leeds", "leeds academy", "academy leeds", "o2 leeds",
    ],
    "o2-academy-sheffield": [
        "o2 academy sheffield", "sheffield academy", "academy sheffield",
        "o2 sheffield",
    ],
    "o2-city-hall-newcastle": [
        "o2 city hall newcastle", "city hall newcastle", "newcastle city hall",
        "o2 newcastle",
    ],
    "o2-academy-glasgow": [
        "o2 academy glasgow", "glasgow academy", "academy glasgow",
        "o2 glasgow",
    ],
    "edinburgh-corn-exchange": [
        "edinburgh corn exchange", "corn exchange edinburgh",
        "corn exchange",
    ],
}

# ── Single-word / short signatures that unambiguously identify one venue ──────
# Only include terms that would NOT naturally appear for any other UK venue.
VENUE_SIGNATURES: dict[str, list[str]] = {
    "o2-academy-brixton":            ["brixton"],
    "o2-forum-kentish-town":         ["kentish town"],
    "o2-victoria-warehouse-manchester": ["victoria warehouse"],
    "o2-guildhall-southampton":      ["guildhall southampton", "southampton guildhall"],
    "o2-city-hall-newcastle":        ["newcastle city hall"],
    "edinburgh-corn-exchange":       ["corn exchange"],
}


@dataclass
class PromptResult:
    prompt_id: str
    prompt_text: str
    response_text: str
    venues_cited: list[str] = field(default_factory=list)


def detect_citations(response: str, venue_slugs: list[str]) -> list[str]:
    """Return slugs of venues whose name (or signature) appears in the response."""
    lower = response.lower()
    cited = []
    for slug in venue_slugs:
        matched = False
        # Tier 1: multi-word alias match
        for alias in VENUE_ALIASES.get(slug, []):
            if alias in lower:
                matched = True
                break
        # Tier 2: signature word match
        if not matched:
            for sig in VENUE_SIGNATURES.get(slug, []):
                if sig in lower:
                    matched = True
                    break
        if matched:
            cited.append(slug)
    return cited


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


def run_live(
    venues: list[dict],
    prompts: list[Prompt],
    model: str = DEFAULT_ANTHROPIC_MODEL,
    provider: str = "anthropic",
    rate_limit_s: float = 0.5,
    verbose: bool = False,
) -> list[PromptResult]:
    """
    Run prompts against the chosen LLM API. Returns PromptResult for each prompt.

    provider: "anthropic" (default) or "openai"
    """
    provider = provider.lower()

    if provider == "anthropic":
        try:
            import anthropic
        except ImportError:
            raise ImportError("pip install anthropic")
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY is not set.")
        client = anthropic.Anthropic(api_key=api_key)
        call_fn = lambda text: _call_anthropic(client, model, text)

    elif provider == "openai":
        try:
            import openai as openai_module
        except ImportError:
            raise ImportError("pip install openai")
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY is not set.")
        client = openai_module.OpenAI(api_key=api_key)
        call_fn = lambda text: _call_openai(client, model, text)

    else:
        raise ValueError(f"Unknown provider '{provider}'. Use 'anthropic' or 'openai'.")

    slugs = [v["slug"] for v in venues]
    results: list[PromptResult] = []

    for i, prompt in enumerate(prompts):
        logger.info("[%d/%d] %s: %s", i + 1, len(prompts), prompt.id, prompt.text[:70])

        try:
            response_text = call_fn(prompt.text)
        except Exception as exc:
            logger.warning("Prompt %s failed: %s", prompt.id, exc)
            response_text = ""

        cited = detect_citations(response_text, slugs)

        if verbose:
            logger.info("  Response:\n%s", response_text)
        logger.info("  Cited (%d): %s", len(cited), ", ".join(cited) if cited else "none")

        results.append(PromptResult(
            prompt_id=prompt.id,
            prompt_text=prompt.text,
            response_text=response_text,
            venues_cited=cited,
        ))

        if i < len(prompts) - 1:
            time.sleep(rate_limit_s)

    return results

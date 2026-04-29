"""
LLM citation runner — sends each prompt to the Claude API and detects
which O2/AMG venues are mentioned in each response.

Detection strategy:
  Each venue has a list of known name aliases (official name, common
  shortforms, bare names without the O2 prefix). The runner checks the
  LLM response against every alias using simple substring matching.
  This is more reliable than asking the LLM to output JSON because it
  captures partial name references ("Brixton Academy", "the Apollo", etc.)

Requirements:
    pip install anthropic
    export ANTHROPIC_API_KEY=sk-ant-...
"""

import os
import re
import time
import logging
from dataclasses import dataclass, field

from .prompts import Prompt

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-opus-4-5"

SYSTEM_PROMPT = (
    "You are a knowledgeable UK music industry expert. "
    "Answer questions about live music venues accurately, helpfully, and concisely. "
    "Name specific real venues where relevant. Do not invent venues."
)

# Known alias forms for each venue slug.
# Add any common shortform names the public uses.
VENUE_ALIASES: dict[str, list[str]] = {
    "o2-academy-brixton": [
        "o2 academy brixton", "brixton academy", "o2 brixton",
        "academy brixton", "brixton o2",
    ],
    "o2-academy-islington": [
        "o2 academy islington", "islington academy", "academy islington",
    ],
    "o2-forum-kentish-town": [
        "o2 forum kentish town", "forum kentish town", "kentish town forum",
        "o2 forum",
    ],
    "o2-shepherds-bush-empire": [
        "o2 shepherd's bush empire", "o2 shepherds bush empire",
        "shepherd's bush empire", "shepherds bush empire", "bush empire",
    ],
    "o2-academy-birmingham": [
        "o2 academy birmingham", "birmingham academy", "academy birmingham",
        "o2 birmingham",
    ],
    "o2-institute-birmingham": [
        "o2 institute birmingham", "institute birmingham",
        "birmingham institute",
    ],
    "o2-academy-leicester": [
        "o2 academy leicester", "leicester academy", "academy leicester",
    ],
    "o2-academy-oxford": [
        "o2 academy oxford", "oxford academy", "academy oxford",
    ],
    "o2-academy-bournemouth": [
        "o2 academy bournemouth", "bournemouth academy", "academy bournemouth",
    ],
    "o2-academy-bristol": [
        "o2 academy bristol", "bristol academy", "academy bristol",
        "o2 bristol",
    ],
    "o2-guildhall-southampton": [
        "o2 guildhall southampton", "guildhall southampton",
        "southampton guildhall",
    ],
    "o2-academy-liverpool": [
        "o2 academy liverpool", "liverpool academy", "academy liverpool",
        "o2 liverpool",
    ],
    "o2-ritz-manchester": [
        "o2 ritz manchester", "ritz manchester", "the ritz manchester",
        "manchester ritz",
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


@dataclass
class PromptResult:
    prompt_id: str
    prompt_text: str
    response_text: str
    venues_cited: list[str] = field(default_factory=list)


def detect_citations(response: str, venue_slugs: list[str]) -> list[str]:
    """Return slugs of venues whose name (or alias) appears in the response."""
    lower = response.lower()
    cited = []
    for slug in venue_slugs:
        aliases = VENUE_ALIASES.get(slug, [slug.replace("-", " ")])
        for alias in aliases:
            if alias in lower:
                cited.append(slug)
                break
    return cited


def run_live(
    venues: list[dict],
    prompts: list[Prompt],
    model: str = DEFAULT_MODEL,
    rate_limit_s: float = 0.5,
    verbose: bool = False,
) -> list[PromptResult]:
    """
    Run prompts against the Claude API. Returns PromptResult for each prompt.
    Raises EnvironmentError if ANTHROPIC_API_KEY is not set.
    """
    try:
        import anthropic
    except ImportError:
        raise ImportError(
            "anthropic package required: pip install anthropic"
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY environment variable is not set.\n"
            "  Export it with: export ANTHROPIC_API_KEY=sk-ant-...\n"
            "  Or run generate_citation_sample.py for offline simulation."
        )

    client = anthropic.Anthropic(api_key=api_key)
    slugs = [v["slug"] for v in venues]
    results: list[PromptResult] = []

    for i, prompt in enumerate(prompts):
        logger.info("[%d/%d] %s: %s", i + 1, len(prompts), prompt.id, prompt.text[:70])

        try:
            message = client.messages.create(
                model=model,
                max_tokens=600,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt.text}],
            )
            response_text = message.content[0].text
        except Exception as exc:
            logger.warning("Prompt %s failed: %s", prompt.id, exc)
            response_text = ""

        cited = detect_citations(response_text, slugs)

        if verbose:
            logger.info("  Response: %s", response_text[:200].replace("\n", " "))
        logger.info("  Cited: %s", ", ".join(cited) if cited else "none")

        results.append(PromptResult(
            prompt_id=prompt.id,
            prompt_text=prompt.text,
            response_text=response_text,
            venues_cited=cited,
        ))

        if i < len(prompts) - 1:
            time.sleep(rate_limit_s)

    return results

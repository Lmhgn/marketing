"""
Operational prompt suite — 20 audience-intent queries reflecting what people
actually search before, during, and after attending a show at an O2/AMG venue.

Intents covered:
  transport   — how to get there, parking, nearest station
  venue-info  — capacity, seating/standing, accessibility, bag policy
  planning    — arrival time, finish time, hotels nearby, food & drink
  tickets     — on-door sales, refunds, finding upcoming events
"""

from typing import Optional
from dataclasses import dataclass, field


@dataclass
class Prompt:
    id: str
    text: str
    intent: str
    intent_category: str
    region_filter: Optional[str] = None
    capacity_hint: Optional[str] = None
    monthly_searches: int = 0
    topic_tags: list = field(default_factory=list)


PROMPTS: list[Prompt] = [
    # ── UK-wide operational (relevant to all 20 venues) ───────────────────────
    Prompt(
        id="p01",
        text="What is the bag policy at O2 Academy venues — what can I bring to a concert?",
        intent="venue_policy",
        intent_category="venue-info",
        monthly_searches=3200,
        topic_tags=["bag-policy", "o2-academy", "uk-wide"],
    ),
    Prompt(
        id="p02",
        text="What are the age restrictions at O2 Academy venues in the UK?",
        intent="venue_policy",
        intent_category="venue-info",
        monthly_searches=2800,
        topic_tags=["age-restrictions", "o2-academy", "uk-wide"],
    ),
    Prompt(
        id="p03",
        text="Can I buy tickets on the door at O2 venues, or do I need to book in advance?",
        intent="ticketing",
        intent_category="tickets",
        monthly_searches=4100,
        topic_tags=["on-door", "tickets", "o2-venues", "uk-wide"],
    ),
    Prompt(
        id="p04",
        text="What time do concerts usually finish at O2 Academy venues?",
        intent="planning",
        intent_category="planning",
        monthly_searches=5400,
        topic_tags=["finish-time", "curfew", "o2-academy", "uk-wide"],
    ),
    Prompt(
        id="p05",
        text="Are O2 Academy venues accessible and wheelchair friendly?",
        intent="accessibility",
        intent_category="venue-info",
        monthly_searches=1900,
        topic_tags=["accessibility", "wheelchair", "o2-academy", "uk-wide"],
    ),
    # ── London venue queries ──────────────────────────────────────────────────
    Prompt(
        id="p06",
        text="How do I get to O2 Academy Brixton by public transport — what tube stop?",
        intent="transport",
        intent_category="transport",
        region_filter="London",
        monthly_searches=6200,
        topic_tags=["transport", "tube", "brixton", "london"],
    ),
    Prompt(
        id="p07",
        text="What is the capacity of O2 Academy Brixton and is it standing or seated?",
        intent="venue_info",
        intent_category="venue-info",
        region_filter="London",
        monthly_searches=4800,
        topic_tags=["capacity", "seating", "brixton", "london"],
    ),
    Prompt(
        id="p08",
        text="What is the nearest tube station to O2 Forum Kentish Town?",
        intent="transport",
        intent_category="transport",
        region_filter="London",
        monthly_searches=2100,
        topic_tags=["transport", "tube", "kentish-town", "london"],
    ),
    Prompt(
        id="p09",
        text="Is Shepherd's Bush Empire standing or seated, and what is the capacity?",
        intent="venue_info",
        intent_category="venue-info",
        region_filter="London",
        monthly_searches=3300,
        topic_tags=["capacity", "seating", "shepherds-bush", "london"],
    ),
    Prompt(
        id="p10",
        text="How early should I arrive at O2 Academy Brixton before a show?",
        intent="planning",
        intent_category="planning",
        region_filter="London",
        monthly_searches=3900,
        topic_tags=["arrival-time", "brixton", "london"],
    ),
    # ── Manchester venue queries ──────────────────────────────────────────────
    Prompt(
        id="p11",
        text="Is there parking near O2 Apollo Manchester, and how do I get there by tram?",
        intent="transport",
        intent_category="transport",
        region_filter="North West",
        monthly_searches=2700,
        topic_tags=["transport", "parking", "apollo", "manchester"],
    ),
    Prompt(
        id="p12",
        text="What is the capacity of O2 Apollo Manchester — is it a big venue?",
        intent="venue_info",
        intent_category="venue-info",
        region_filter="North West",
        monthly_searches=3100,
        topic_tags=["capacity", "apollo", "manchester"],
    ),
    Prompt(
        id="p13",
        text="What kind of music events does Victoria Warehouse Manchester host?",
        intent="events",
        intent_category="tickets",
        region_filter="North West",
        monthly_searches=2400,
        topic_tags=["events", "victoria-warehouse", "manchester"],
    ),
    # ── Birmingham, Scotland, Yorkshire, South queries ────────────────────────
    Prompt(
        id="p14",
        text="How do I get to O2 Academy Birmingham by train — what is the nearest station?",
        intent="transport",
        intent_category="transport",
        region_filter="Midlands",
        monthly_searches=2900,
        topic_tags=["transport", "train", "birmingham"],
    ),
    Prompt(
        id="p15",
        text="What is Edinburgh Corn Exchange like as a concert venue — capacity and atmosphere?",
        intent="venue_info",
        intent_category="venue-info",
        region_filter="Scotland",
        monthly_searches=2200,
        topic_tags=["capacity", "atmosphere", "corn-exchange", "edinburgh"],
    ),
    Prompt(
        id="p16",
        text="Is O2 Academy Glasgow standing or seated, and how big is it?",
        intent="venue_info",
        intent_category="venue-info",
        region_filter="Scotland",
        monthly_searches=2600,
        topic_tags=["capacity", "seating", "glasgow"],
    ),
    Prompt(
        id="p17",
        text="Are there hotels near O2 Academy Leeds for a concert night?",
        intent="planning",
        intent_category="planning",
        region_filter="Yorkshire",
        monthly_searches=1800,
        topic_tags=["hotels", "accommodation", "leeds"],
    ),
    Prompt(
        id="p18",
        text="What food and drink is available at O2 Academy Bristol?",
        intent="planning",
        intent_category="planning",
        region_filter="South",
        monthly_searches=1600,
        topic_tags=["food", "drink", "bristol"],
    ),
    # ── Ticket & event queries ────────────────────────────────────────────────
    Prompt(
        id="p19",
        text="How do I get a refund or exchange for an O2 venue ticket?",
        intent="ticketing",
        intent_category="tickets",
        monthly_searches=4700,
        topic_tags=["refund", "exchange", "tickets", "uk-wide"],
    ),
    Prompt(
        id="p20",
        text="How do I find upcoming gigs and events at O2 Academy venues near me?",
        intent="discovery",
        intent_category="tickets",
        monthly_searches=6800,
        topic_tags=["upcoming-events", "gigs", "o2-academy", "uk-wide"],
    ),
]

PROMPT_MAP: dict[str, Prompt] = {p.id: p for p in PROMPTS}

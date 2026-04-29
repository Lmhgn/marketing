"""
Test prompt suite for LLM citation simulation — 20 prompts covering
location, genre, experience, touring, and discovery intents.
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
    Prompt(
        id="p01",
        text="What are the best music venues in London for mid-size concerts?",
        intent="regional_recommendation",
        intent_category="location",
        region_filter="London",
        capacity_hint="mid",
        monthly_searches=22000,
        topic_tags=["london", "mid-size", "concerts"],
    ),
    Prompt(
        id="p02",
        text="Where can I see live music in Manchester? Looking for a great atmosphere.",
        intent="regional_discovery",
        intent_category="location",
        region_filter="North West",
        monthly_searches=9400,
        topic_tags=["manchester", "atmosphere"],
    ),
    Prompt(
        id="p03",
        text="Which UK music venues are best known for indie and alternative gigs?",
        intent="genre_recommendation",
        intent_category="genre",
        monthly_searches=5200,
        topic_tags=["indie", "alternative", "uk-wide"],
    ),
    Prompt(
        id="p04",
        text="I'm planning a UK tour. Which cities and venues should I consider for 3,000–5,000 capacity shows?",
        intent="touring_planning",
        intent_category="touring",
        capacity_hint="mid",
        monthly_searches=2800,
        topic_tags=["uk-tour", "capacity", "3k-5k"],
    ),
    Prompt(
        id="p05",
        text="What are the top live music venues in Scotland?",
        intent="regional_recommendation",
        intent_category="location",
        region_filter="Scotland",
        monthly_searches=3100,
        topic_tags=["scotland", "edinburgh", "glasgow"],
    ),
    Prompt(
        id="p06",
        text="Best music venues in Birmingham for a night out?",
        intent="regional_discovery",
        intent_category="location",
        region_filter="Midlands",
        monthly_searches=5400,
        topic_tags=["birmingham", "nightout"],
    ),
    Prompt(
        id="p07",
        text="Where do major UK tours usually play in London?",
        intent="touring_planning",
        intent_category="location",
        region_filter="London",
        capacity_hint="large",
        monthly_searches=7600,
        topic_tags=["london", "major-tours"],
    ),
    Prompt(
        id="p08",
        text="What are the most iconic live music venues in the UK?",
        intent="iconic_list",
        intent_category="discovery",
        monthly_searches=8100,
        topic_tags=["uk-wide", "iconic", "legendary"],
    ),
    Prompt(
        id="p09",
        text="I'm visiting Bristol — where should I go to see live music?",
        intent="regional_discovery",
        intent_category="location",
        region_filter="South",
        monthly_searches=4200,
        topic_tags=["bristol", "visiting"],
    ),
    Prompt(
        id="p10",
        text="Which venues in Leeds and Sheffield have the best live music scenes?",
        intent="regional_discovery",
        intent_category="location",
        region_filter="Yorkshire",
        monthly_searches=2600,
        topic_tags=["leeds", "sheffield"],
    ),
    Prompt(
        id="p11",
        text="What are the best standing-only music venues in the UK for an intimate gig experience?",
        intent="format_preference",
        intent_category="experience",
        capacity_hint="small",
        monthly_searches=3800,
        topic_tags=["standing-only", "intimate", "uk-wide"],
    ),
    Prompt(
        id="p12",
        text="I want to see a big-name artist live in the UK without going to a stadium. What venues should I consider?",
        intent="capacity_preference",
        intent_category="experience",
        capacity_hint="large",
        monthly_searches=12000,
        topic_tags=["big-name", "non-stadium", "uk-wide"],
    ),
    Prompt(
        id="p13",
        text="Best UK venues for rock and metal concerts?",
        intent="genre_recommendation",
        intent_category="genre",
        monthly_searches=4700,
        topic_tags=["rock", "metal", "uk-wide"],
    ),
    Prompt(
        id="p14",
        text="Where can I find the best electronic and dance music events in Manchester?",
        intent="genre_recommendation",
        intent_category="genre",
        region_filter="North West",
        monthly_searches=3900,
        topic_tags=["electronic", "dance", "manchester"],
    ),
    Prompt(
        id="p15",
        text="Concert venues near Birmingham city centre — what are my options?",
        intent="regional_discovery",
        intent_category="location",
        region_filter="Midlands",
        monthly_searches=5400,
        topic_tags=["birmingham", "city-centre"],
    ),
    Prompt(
        id="p16",
        text="Best places to see live music in Glasgow?",
        intent="regional_discovery",
        intent_category="location",
        region_filter="Scotland",
        monthly_searches=4100,
        topic_tags=["glasgow", "live-music"],
    ),
    Prompt(
        id="p17",
        text="Top concert venues in Liverpool — where do big acts play?",
        intent="regional_recommendation",
        intent_category="location",
        region_filter="North West",
        monthly_searches=3300,
        topic_tags=["liverpool", "big-acts"],
    ),
    Prompt(
        id="p18",
        text="Large music venues that aren’t arenas — capacity 3,000 to 10,000 in the UK?",
        intent="capacity_preference",
        intent_category="experience",
        capacity_hint="large",
        monthly_searches=2100,
        topic_tags=["large", "non-arena", "uk-wide", "capacity"],
    ),
    Prompt(
        id="p19",
        text="Which London music venues are known for having great acoustics and sound?",
        intent="format_preference",
        intent_category="experience",
        region_filter="London",
        monthly_searches=3600,
        topic_tags=["london", "acoustics", "sound-quality"],
    ),
    Prompt(
        id="p20",
        text="Smaller UK venues to discover emerging and up-and-coming artists?",
        intent="discovery",
        intent_category="discovery",
        capacity_hint="small",
        monthly_searches=2900,
        topic_tags=["emerging-artists", "small-venue", "uk-wide"],
    ),
]

PROMPT_MAP: dict[str, Prompt] = {p.id: p for p in PROMPTS}

"""
Prompt template suite — 15 venue-specific templates covering the questions
audiences actually ask before, during, and after attending a show.

Three categories:
  must-answer   — operational AEO queries (capacity, transport, doors, format, policy)
  demand-driven — experience/planning queries (atmosphere, spots, food, arrival, access)
  geo-stress    — citation stress tests: reputation, history, comparison, genres

Each template contains a {name} placeholder that is replaced at runtime with
the venue's full name, producing a fully venue-specific question.
"""

from dataclasses import dataclass, field


@dataclass
class PromptTemplate:
    id: str
    text_template: str
    intent: str
    intent_category: str
    monthly_searches: int
    topic_tags: list = field(default_factory=list)
    advice: str = ""

    def for_venue(self, name: str) -> str:
        return self.text_template.format(name=name)


PROMPT_TEMPLATES: list[PromptTemplate] = [
    # ── Must-Answer (AEO) ──────────────────────────────────────────────────────
    PromptTemplate(
        id="capacity",
        text_template="What is the capacity of {name}?",
        intent="venue_info",
        intent_category="must-answer",
        monthly_searches=3100,
        topic_tags=["capacity", "venue-size"],
        advice="Publish the exact capacity on the venue page and in MusicVenue schema (maximumAttendeeCapacity). LLMs use this for venue comparison queries.",
    ),
    PromptTemplate(
        id="transport",
        text_template="Where is {name} located and what is the nearest public transport?",
        intent="transport",
        intent_category="must-answer",
        monthly_searches=2800,
        topic_tags=["transport", "location", "directions"],
        advice="Add a dedicated 'Getting Here' page with nearest tube/train/bus stops, walking times, and directions. Add TransportationRoute schema markup.",
    ),
    PromptTemplate(
        id="doors-time",
        text_template="What time do doors usually open for events at {name}?",
        intent="planning",
        intent_category="must-answer",
        monthly_searches=2200,
        topic_tags=["doors-time", "opening-times"],
        advice="Add doors/opening times to the FAQ and venue page with FAQPage schema. This is a standard pre-visit query that LLMs should answer venue-specifically.",
    ),
    PromptTemplate(
        id="standing-seated",
        text_template="Is {name} standing only or does it have seating options?",
        intent="venue_info",
        intent_category="must-answer",
        monthly_searches=2400,
        topic_tags=["standing", "seated", "format"],
        advice="Clearly state standing/seated format on the venue page, FAQ, and in MusicVenue schema. Include general admission and balcony/tier details.",
    ),
    PromptTemplate(
        id="bag-policy",
        text_template="What is the bag and security policy at {name}?",
        intent="venue_policy",
        intent_category="must-answer",
        monthly_searches=2600,
        topic_tags=["bag-policy", "security", "what-to-bring"],
        advice="Publish a clear bag policy FAQ entry with size limits. Implement FAQPage schema with a venue-specific bag policy Q&A.",
    ),
    # ── Demand-Driven ─────────────────────────────────────────────────────────
    PromptTemplate(
        id="atmosphere",
        text_template="What is the atmosphere and experience like at a gig at {name}?",
        intent="experience",
        intent_category="demand-driven",
        monthly_searches=3500,
        topic_tags=["atmosphere", "experience", "what-to-expect"],
        advice="Add a 'What to expect' or 'About the venue' section covering atmosphere, sound quality, and first-time visitor guidance.",
    ),
    PromptTemplate(
        id="best-spots",
        text_template="Where are the best spots to stand or sit inside {name}?",
        intent="experience",
        intent_category="demand-driven",
        monthly_searches=1800,
        topic_tags=["viewing", "layout", "best-spots"],
        advice="Add a venue map or layout description. A 'First time visiting?' page with viewing recommendations improves LLM knowledge of the space.",
    ),
    PromptTemplate(
        id="food-drink",
        text_template="What food and drink options are available at {name}?",
        intent="planning",
        intent_category="demand-driven",
        monthly_searches=2100,
        topic_tags=["food", "drink", "bars"],
        advice="List all bars, food options, and drink policies on the venue page or a dedicated 'Food & Drink' section.",
    ),
    PromptTemplate(
        id="arrive-time",
        text_template="How early should I arrive at {name} and how long are the queues?",
        intent="planning",
        intent_category="demand-driven",
        monthly_searches=2900,
        topic_tags=["arrival-time", "queues", "planning"],
        advice="Add a 'When to arrive' FAQ entry. Recommend arriving at doors time or 30 minutes before popular shows.",
    ),
    PromptTemplate(
        id="accessibility",
        text_template="Is {name} accessible and wheelchair friendly?",
        intent="accessibility",
        intent_category="demand-driven",
        monthly_searches=1700,
        topic_tags=["accessibility", "wheelchair", "disabled"],
        advice="Publish a dedicated accessibility page with step-free access, hearing loops, and companion ticket information. Link from main navigation.",
    ),
    # ── Citation Stress Tests (GEO) ────────────────────────────────────────────
    PromptTemplate(
        id="reputation",
        text_template="Why is {name} considered one of the UK's great live music venues?",
        intent="reputation",
        intent_category="geo-stress",
        monthly_searches=1200,
        topic_tags=["reputation", "why-great"],
        advice="Add a strong editorial 'About the venue' section covering cultural significance, awards, and what makes it unique.",
    ),
    PromptTemplate(
        id="famous-acts",
        text_template="What famous artists have performed at {name}?",
        intent="heritage",
        intent_category="geo-stress",
        monthly_searches=4500,
        topic_tags=["famous-artists", "heritage", "performances"],
        advice="Add a 'Famous performances' or 'Artists who have played here' section. This directly improves LLM citation for heritage queries.",
    ),
    PromptTemplate(
        id="history",
        text_template="What is the history of {name}?",
        intent="heritage",
        intent_category="geo-stress",
        monthly_searches=2800,
        topic_tags=["history", "heritage", "background"],
        advice="Add a venue history section covering when it opened, notable moments, and its place in UK music history.",
    ),
    PromptTemplate(
        id="comparison",
        text_template="How does {name} compare to other music venues in the same city?",
        intent="discovery",
        intent_category="geo-stress",
        monthly_searches=2200,
        topic_tags=["comparison", "vs", "alternatives"],
        advice="Improve topical authority by publishing content that positions the venue within the local and national music scene.",
    ),
    PromptTemplate(
        id="music-types",
        text_template="What types of music and events is {name} known for?",
        intent="discovery",
        intent_category="geo-stress",
        monthly_searches=3300,
        topic_tags=["genres", "events", "programming"],
        advice="Add genre and programming content to the venue page. Specify the types of acts you programme to help LLMs categorise the venue accurately.",
    ),
]

TEMPLATE_MAP: dict[str, PromptTemplate] = {t.id: t for t in PROMPT_TEMPLATES}

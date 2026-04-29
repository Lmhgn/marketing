import { getVenueCitations } from "@/lib/citations";
import type { VenueReport } from "@/types/venue";

export interface ContentGap {
  promptId:       string;
  question:       string;
  monthlySearches: number;
  advice:         string;
  alsoСited:      string[];
  intentCategory: string;
}

export interface SchemaField {
  key:         string;
  value:       string;
  todo:        boolean;
  description: string;
}

export interface VenueBrief {
  hasMusicVenueSchema:  boolean;
  hasFaqSchema:         boolean;
  faqSubPageUrl:        string | null;
  contentGaps:          ContentGap[];
  schemaFields:         SchemaField[];
  quickWins:            string[];
  priorityFixes:        string[];
  crawlDate:            string;
  aeoScore:             number;
  geoScore:             number;
  topFindings:          string[];
}

const REGION_CITY: Record<string, string> = {
  "London":        "London",
  "West Midlands": "Birmingham",
  "East Midlands": "Leicester",
  "South Coast":   "Southampton",
  "North West":    "Manchester",
  "Yorkshire":     "Sheffield",
  "North East":    "Newcastle upon Tyne",
  "Scotland":      "Glasgow",
};

export function getVenueBrief(venue: VenueReport): VenueBrief {
  const citations = getVenueCitations(venue.slug);

  // Detect what schema exists from findings
  const schemaFindings = venue.aeo_components.structured_data?.findings ?? [];
  const hasMusicVenueSchema = schemaFindings.some(f => f.includes("MusicVenue schema present"));
  const hasFaqSchema        = schemaFindings.some(f => f.includes("FAQPage schema present"))
    || (venue.aeo_components.faq_qa_content?.findings ?? []).some(f => f.includes("FAQPage JSON-LD present"));

  // Detect FAQ sub-page URL from findings
  const faqFinding = (venue.aeo_components.faq_qa_content?.findings ?? [])
    .find(f => f.includes("Dedicated FAQ sub-page found"));
  const faqMatch    = faqFinding?.match(/found \(([^)]+)\)/);
  const faqSubPageUrl = faqMatch ? faqMatch[1] : null;

  // Missed prompts sorted by search volume
  const contentGaps: ContentGap[] = citations
    ? citations.prompts
        .filter(p => !p.cited)
        .sort((a, b) => b.monthly_searches - a.monthly_searches)
        .map(p => ({
          promptId:        p.id,
          question:        p.text,
          monthlySearches: p.monthly_searches,
          advice:          p.advice,
          alsoСited:       p.also_cited ?? [],
          intentCategory:  p.intent_category,
        }))
    : [];

  // Generate schema fields (pre-filled where known, TODO otherwise)
  const city = REGION_CITY[venue.region] ?? venue.region;
  const capacityFinding = (venue.aeo_components.content_clarity?.findings ?? [])
    .find(f => f.includes("Capacity information present"));
  const capacityMatch = capacityFinding?.match(/Capacity information present:\s*([\d,]+)/);
  const capacityValue = capacityMatch ? capacityMatch[1].replace(/,/g, "") : null;

  const postcodeFinding = (venue.geo_components.entity_clarity?.findings ?? [])
    .find(f => f.includes("Address / postcode present"));
  const postcodeMatch = postcodeFinding?.match(/present:\s*([A-Z0-9 ]+)\./i);
  const postcode = postcodeMatch ? postcodeMatch[1].trim() : null;

  const schemaFields: SchemaField[] = [
    {
      key: "@type", value: "MusicVenue", todo: false,
      description: "Correct schema type for a live music venue",
    },
    {
      key: "name", value: venue.venue_name, todo: false,
      description: "Venue display name",
    },
    {
      key: "url", value: venue.url, todo: false,
      description: "Canonical venue URL",
    },
    {
      key: "maximumAttendeeCapacity",
      value: capacityValue ?? "ADD_CAPACITY",
      todo: !capacityValue,
      description: "Total capacity — critical for tour promoter and fan queries",
    },
    {
      key: "address.addressLocality", value: city, todo: false,
      description: "City name",
    },
    {
      key: "address.postalCode",
      value: postcode ?? "ADD_POSTCODE",
      todo: !postcode,
      description: "Full UK postcode",
    },
    {
      key: "address.addressCountry", value: "GB", todo: false,
      description: "Country code",
    },
    {
      key: "sameAs[0]",
      value: "ADD_WIKIPEDIA_URL",
      todo: true,
      description: "e.g. https://en.wikipedia.org/wiki/O2_Academy_Brixton",
    },
    {
      key: "sameAs[1]",
      value: "ADD_WIKIDATA_URL",
      todo: true,
      description: "e.g. https://www.wikidata.org/wiki/Q12345",
    },
  ];

  // Top findings to surface
  const allFindings = [
    ...(venue.aeo_components.structured_data?.findings ?? []),
    ...(venue.aeo_components.faq_qa_content?.findings ?? []),
    ...(venue.geo_components.entity_clarity?.findings ?? []),
    ...(venue.geo_components.external_corroboration?.findings ?? []),
  ].filter(f =>
    f.includes("missing") || f.includes("No ") || f.includes("not") || f.includes("upgrade")
  ).slice(0, 6);

  return {
    hasMusicVenueSchema,
    hasFaqSchema,
    faqSubPageUrl,
    contentGaps,
    schemaFields,
    quickWins:      venue.quick_wins      ?? [],
    priorityFixes:  venue.priority_fixes  ?? [],
    crawlDate:      new Date().toISOString().slice(0, 10),
    aeoScore:       venue.aeo_score,
    geoScore:       venue.geo_score,
    topFindings:    allFindings,
  };
}

export function buildSchemaSnippet(fields: SchemaField[], venueName: string, url: string): string {
  const cap   = fields.find(f => f.key === "maximumAttendeeCapacity");
  const city  = fields.find(f => f.key === "address.addressLocality");
  const pc    = fields.find(f => f.key === "address.postalCode");
  const sameAs0 = fields.find(f => f.key === "sameAs[0]");
  const sameAs1 = fields.find(f => f.key === "sameAs[1]");

  return JSON.stringify({
    "@context": "https://schema.org",
    "@type": "MusicVenue",
    "name": venueName,
    "url": url,
    "maximumAttendeeCapacity": cap?.todo ? "⚠ ADD_CAPACITY" : Number(cap?.value),
    "address": {
      "@type": "PostalAddress",
      "addressLocality": city?.value ?? "",
      "postalCode": pc?.todo ? "⚠ ADD_POSTCODE" : pc?.value,
      "addressCountry": "GB",
    },
    "sameAs": [
      sameAs0?.value ?? "⚠ ADD_WIKIPEDIA_URL",
      sameAs1?.value ?? "⚠ ADD_WIKIDATA_URL",
    ],
  }, null, 2);
}

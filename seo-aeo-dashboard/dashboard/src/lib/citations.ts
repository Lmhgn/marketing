import citationData from "../../../data/citation_results.json";

export interface VenuePrompt {
  id: string;
  text: string;
  monthly_searches: number;
  intent_category: string;
  topic_tags: string[];
  cited: boolean;
  advice: string;
}

export interface CitationResult {
  citation_count: number;
  citation_rate: number;
  citation_band: string;
  prompts: VenuePrompt[];
}

export interface CitationMeta {
  run_date: string;
  model: string;
  total_prompts: number;
}

const data = citationData as unknown as {
  run_date: string;
  model: string;
  prompts_per_venue: number;
  venues: Record<string, CitationResult>;
};

export const citationMeta: CitationMeta = {
  run_date: data.run_date,
  model: data.model,
  total_prompts: data.prompts_per_venue,
};

export function getVenueCitations(slug: string): CitationResult | null {
  return data.venues[slug] ?? null;
}

export function getAllCitations(): Record<string, CitationResult> {
  return data.venues;
}

export function citationBandColor(band: string): string {
  const map: Record<string, string> = {
    strong:   "text-emerald-600",
    good:     "text-blue-600",
    moderate: "text-amber-600",
    weak:     "text-orange-500",
    critical: "text-red-600",
  };
  return map[band] ?? "text-slate-500";
}

export function citationBandBg(band: string): string {
  const map: Record<string, string> = {
    strong:   "bg-emerald-100 text-emerald-800",
    good:     "bg-blue-100 text-blue-800",
    moderate: "bg-amber-100 text-amber-800",
    weak:     "bg-orange-100 text-orange-700",
    critical: "bg-red-100 text-red-700",
  };
  return map[band] ?? "bg-slate-100 text-slate-600";
}

export function intentLabel(category: string): string {
  const map: Record<string, string> = {
    "must-answer":   "Must-Answer",
    "demand-driven": "Demand-Driven",
    "geo-stress":    "Citation Stress Tests",
    // legacy
    "venue-info":    "Venue Info",
    "transport":     "Getting There",
    "planning":      "Visit Planning",
    "tickets":       "Tickets & Events",
    location:        "Location",
    genre:           "Genre / Style",
    experience:      "Experience",
    touring:         "Tour Planning",
    discovery:       "Discovery",
  };
  return map[category] ?? category;
}

export function intentColor(category: string): string {
  const map: Record<string, string> = {
    "must-answer":   "bg-blue-100 text-blue-700",
    "demand-driven": "bg-teal-100 text-teal-700",
    "geo-stress":    "bg-purple-100 text-purple-700",
    // legacy
    "venue-info":    "bg-blue-100 text-blue-700",
    "transport":     "bg-teal-100 text-teal-700",
    "planning":      "bg-amber-100 text-amber-700",
    "tickets":       "bg-purple-100 text-purple-700",
    location:        "bg-blue-100 text-blue-700",
    genre:           "bg-purple-100 text-purple-700",
    experience:      "bg-teal-100 text-teal-700",
    touring:         "bg-amber-100 text-amber-700",
    discovery:       "bg-emerald-100 text-emerald-700",
  };
  return map[category] ?? "bg-slate-100 text-slate-600";
}

export function dailySearches(monthly: number): string {
  const d = Math.round(monthly / 30);
  if (d >= 1000) return `~${(d / 1000).toFixed(1)}k/day`;
  return `~${d}/day`;
}

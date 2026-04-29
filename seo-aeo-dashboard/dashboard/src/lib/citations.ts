import citationData from "../../../data/citation_results.json";

export interface GapItem {
  prompt_id: string;
  advice: string;
}

export interface CitationResult {
  citation_count: number;
  citation_rate: number;
  citation_band: string;
  cited_by_prompts: string[];
  missed_by_prompts: string[];
  relevant_prompt_ids: string[];
  relevant_citation_count: number;
  relevant_citation_rate: number;
  relevant_citation_band: string;
  gap_analysis: GapItem[];
}

export interface CitationPrompt {
  id: string;
  text: string;
  venues_cited: string[];
  monthly_searches?: number;
  intent_category?: string;
  topic_tags?: string[];
}

export interface CitationMeta {
  run_date: string;
  model: string;
  total_prompts: number;
}

const data = citationData as {
  run_date: string;
  model: string;
  total_prompts: number;
  venues: Record<string, CitationResult>;
  prompts: CitationPrompt[];
};

export const citationMeta: CitationMeta = {
  run_date: data.run_date,
  model: data.model,
  total_prompts: data.total_prompts,
};

export function getVenueCitations(slug: string): CitationResult | null {
  return data.venues[slug] ?? null;
}

export function getPromptDetails(promptIds: string[]): CitationPrompt[] {
  return data.prompts.filter(p => promptIds.includes(p.id));
}

export function getAllPrompts(): CitationPrompt[] {
  return data.prompts;
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
    location:   "Location",
    genre:      "Genre / Style",
    experience: "Experience",
    touring:    "Tour Planning",
    discovery:  "Discovery",
  };
  return map[category] ?? category;
}

export function intentColor(category: string): string {
  const map: Record<string, string> = {
    location:   "bg-blue-100 text-blue-700",
    genre:      "bg-purple-100 text-purple-700",
    experience: "bg-teal-100 text-teal-700",
    touring:    "bg-amber-100 text-amber-700",
    discovery:  "bg-emerald-100 text-emerald-700",
  };
  return map[category] ?? "bg-slate-100 text-slate-600";
}

export function dailySearches(monthly: number): string {
  const d = Math.round(monthly / 30);
  if (d >= 1000) return `~${(d / 1000).toFixed(1)}k/day`;
  return `~${d}/day`;
}

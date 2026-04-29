import historyData from "../../../data/citation_history.json";

export interface CitationSnapshot {
  date: string;
  week: number;
  citation_rate: number;
  citation_count: number;
  citation_band: string;
}

const history = historyData as unknown as Record<string, CitationSnapshot[]>;

export function getVenueCitationHistory(slug: string): CitationSnapshot[] {
  return history[slug] ?? [];
}

export function getCitationDelta(slug: string): number | null {
  const snaps = getVenueCitationHistory(slug);
  if (snaps.length < 2) return null;
  return Math.round(
    (snaps[snaps.length - 1].citation_rate - snaps[0].citation_rate) * 10,
  ) / 10;
}

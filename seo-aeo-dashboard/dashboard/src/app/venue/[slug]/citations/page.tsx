import Link from "next/link";
import { notFound } from "next/navigation";
import { venues } from "@/lib/data";
import {
  getVenueCitations,
  citationMeta,
  citationBandBg,
  intentLabel,
  intentColor,
  dailySearches,
  type VenuePrompt,
} from "@/lib/citations";
import { getVenueCitationHistory, getCitationDelta } from "@/lib/citation-history";
import CitationTrendChart from "@/components/CitationTrendChart";
import PromptRow from "@/components/PromptRow";

export function generateStaticParams() {
  return venues.map(v => ({ slug: v.slug }));
}

const INTENT_ORDER = ["must-answer", "demand-driven", "geo-stress"];

export default function CitationsDetail({ params }: { params: { slug: string } }) {
  const venue = venues.find(v => v.slug === params.slug);
  if (!venue) notFound();

  const citations = getVenueCitations(params.slug);
  if (!citations) notFound();

  const citationHistory = getVenueCitationHistory(params.slug);
  const citationDelta   = getCitationDelta(params.slug);

  const { prompts } = citations;

  // Group prompts by intent category
  const grouped: Record<string, VenuePrompt[]> = {};
  for (const p of prompts) {
    if (!grouped[p.intent_category]) grouped[p.intent_category] = [];
    grouped[p.intent_category].push(p);
  }

  const citedPrompts  = prompts.filter(p => p.cited);
  const missedPrompts = prompts.filter(p => !p.cited);

  const totalMonthly  = prompts.reduce((s, p) => s + p.monthly_searches, 0);
  const citedMonthly  = citedPrompts.reduce((s, p) => s + p.monthly_searches, 0);
  const missedMonthly = totalMonthly - citedMonthly;

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <Link href="/" className="hover:text-blue-600">Overview</Link>
        <span>›</span>
        <Link href={`/venue/${params.slug}`} className="hover:text-blue-600">{venue.venue_name}</Link>
        <span>›</span>
        <span className="text-slate-800">LLM Citation Report</span>
      </div>

      {/* Header */}
      <section className="bg-white rounded-lg border border-slate-200 p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">LLM Citation Performance</h1>
            <p className="text-sm text-slate-500 mt-1">{venue.venue_name} · {venue.region}</p>
            <p className="text-xs text-slate-400 mt-1">
              Run via {citationMeta.model} · {citationMeta.total_prompts} venue-specific prompts · {citationMeta.run_date}
            </p>
          </div>
          <span className={`px-3 py-1.5 rounded-lg text-sm font-medium ${citationBandBg(citations.citation_band)}`}>
            {citations.citation_band} — {citations.citation_rate}%
          </span>
        </div>

        {/* Summary stat row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
          <StatCard
            label="Prompts cited"
            value={`${citations.citation_count} / ${prompts.length}`}
            sub="cited / total"
            color="blue"
          />
          <StatCard
            label="Citation rate"
            value={`${citations.citation_rate}%`}
            sub="venue-specific prompts"
            color={citations.citation_rate >= 67 ? "green" : citations.citation_rate >= 45 ? "amber" : "red"}
          />
          <StatCard
            label="Monthly search reach"
            value={citedMonthly.toLocaleString()}
            sub="searches/mo where cited"
            color="green"
          />
          <StatCard
            label="Monthly search gap"
            value={missedMonthly.toLocaleString()}
            sub="searches/mo where missed"
            color="red"
          />
        </div>
      </section>

      {/* Citation rate trend */}
      {citationHistory.length > 1 && (
        <section className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-medium text-slate-700">Citation rate — 4-week trend</h2>
            {citationDelta !== null && (
              <span className={`text-xs font-mono font-medium ${citationDelta >= 0 ? "text-emerald-600" : "text-red-500"}`}>
                {citationDelta >= 0 ? "+" : ""}{citationDelta}% since week 1
              </span>
            )}
          </div>
          <CitationTrendChart data={citationHistory} />
        </section>
      )}

      {/* Gap analysis */}
      {missedPrompts.length > 0 && (
        <section className="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <h2 className="text-sm font-semibold text-amber-800 mb-3">Priority citation gaps</h2>
          <ul className="space-y-2">
            {missedPrompts.slice(0, 5).map(p => (
              <li key={p.id} className="flex gap-3 text-sm">
                <span className="text-amber-500 mt-0.5 shrink-0">⚑</span>
                <div>
                  <p className="text-amber-900 font-medium">&ldquo;{p.text}&rdquo;
                    {p.monthly_searches > 0 && (
                      <span className="ml-2 text-xs font-normal text-amber-600">
                        {dailySearches(p.monthly_searches)} · {p.monthly_searches.toLocaleString()}/mo
                      </span>
                    )}
                  </p>
                  <p className="text-amber-700 mt-0.5">{p.advice}</p>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Prompts by intent category */}
      {INTENT_ORDER.filter(cat => grouped[cat]?.length).map(cat => (
        <section key={cat}>
          <div className="flex items-center gap-2 mb-3">
            <h2 className="text-base font-medium text-slate-900">{intentLabel(cat)}</h2>
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${intentColor(cat)}`}>
              {grouped[cat].filter(p => p.cited).length} / {grouped[cat].length} cited
            </span>
          </div>
          <div className="space-y-2">
            {grouped[cat].map(p => (
              <PromptRow key={p.id} prompt={p} />
            ))}
          </div>
        </section>
      ))}

      {/* Daily search landscape */}
      <section className="bg-white rounded-lg border border-slate-200 p-4">
        <h2 className="text-sm font-medium text-slate-700 mb-4">Daily search landscape — all prompts ranked by volume</h2>
        <div className="space-y-2">
          {[...prompts]
            .sort((a, b) => b.monthly_searches - a.monthly_searches)
            .map(p => {
              const daily = Math.round(p.monthly_searches / 30);
              const maxMonthly = Math.max(...prompts.map(x => x.monthly_searches));
              const barWidth = maxMonthly ? Math.round(p.monthly_searches / maxMonthly * 100) : 0;
              return (
                <div key={p.id} className="flex items-center gap-3 text-xs">
                  <div className="w-4 shrink-0">
                    {p.cited
                      ? <span className="text-emerald-500 font-bold">✓</span>
                      : <span className="text-red-400">✗</span>
                    }
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-slate-700 truncate">{p.text}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden max-w-[200px]">
                        <div
                          className={`h-full rounded-full ${p.cited ? "bg-emerald-400" : "bg-slate-300"}`}
                          style={{ width: `${barWidth}%` }}
                        />
                      </div>
                      <span className="text-slate-400 shrink-0">{daily.toLocaleString()}/day · {p.monthly_searches.toLocaleString()}/mo</span>
                    </div>
                  </div>
                  <span className={`px-1.5 py-0.5 rounded text-xs shrink-0 ${intentColor(p.intent_category)}`}>
                    {intentLabel(p.intent_category)}
                  </span>
                </div>
              );
            })}
        </div>
      </section>
    </div>
  );
}


function StatCard({
  label, value, sub, color,
}: {
  label: string; value: string; sub: string; color: "blue" | "green" | "amber" | "red";
}) {
  const styles: Record<string, string> = {
    blue:  "bg-blue-50 border-blue-200 text-blue-800",
    green: "bg-emerald-50 border-emerald-200 text-emerald-800",
    amber: "bg-amber-50 border-amber-200 text-amber-800",
    red:   "bg-red-50 border-red-200 text-red-800",
  };
  const valStyles: Record<string, string> = {
    blue:  "text-blue-900",
    green: "text-emerald-900",
    amber: "text-amber-900",
    red:   "text-red-900",
  };
  return (
    <div className={`rounded-lg border p-3 ${styles[color]}`}>
      <p className="text-xs uppercase tracking-wide opacity-70">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${valStyles[color]}`}>{value}</p>
      <p className="text-xs opacity-60 mt-0.5">{sub}</p>
    </div>
  );
}

import Link from "next/link";
import { notFound } from "next/navigation";
import { venues } from "@/lib/data";
import {
  getVenueCitations,
  getAllPrompts,
  citationMeta,
  citationBandBg,
  intentLabel,
  intentColor,
  dailySearches,
  type CitationPrompt,
} from "@/lib/citations";

export function generateStaticParams() {
  return venues.map(v => ({ slug: v.slug }));
}

const INTENT_ORDER = ["venue-info", "transport", "planning", "tickets", "location", "experience", "touring", "genre", "discovery"];

export default function CitationsDetail({ params }: { params: { slug: string } }) {
  const venue = venues.find(v => v.slug === params.slug);
  if (!venue) notFound();

  const citations = getVenueCitations(params.slug);
  if (!citations) notFound();

  const allPrompts = getAllPrompts();

  // Group all prompts by intent
  const grouped: Record<string, CitationPrompt[]> = {};
  for (const p of allPrompts) {
    const cat = p.intent_category ?? "other";
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(p);
  }

  const relevantSet = new Set(citations.relevant_prompt_ids);
  const citedSet = new Set(citations.cited_by_prompts);

  // Stats
  const totalMonthly = allPrompts
    .filter(p => relevantSet.has(p.id))
    .reduce((s, p) => s + (p.monthly_searches ?? 0), 0);

  const citedMonthly = allPrompts
    .filter(p => relevantSet.has(p.id) && citedSet.has(p.id))
    .reduce((s, p) => s + (p.monthly_searches ?? 0), 0);

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
              Simulated via {citationMeta.model} · {citationMeta.total_prompts} test prompts · run {citationMeta.run_date}
            </p>
          </div>
          <span className={`px-3 py-1.5 rounded-lg text-sm font-medium ${citationBandBg(citations.relevant_citation_band)}`}>
            {citations.relevant_citation_band} — {citations.relevant_citation_rate}%
          </span>
        </div>

        {/* Summary stat row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
          <StatCard
            label="Relevant prompts"
            value={`${citations.relevant_citation_count} / ${citations.relevant_prompt_ids.length}`}
            sub="cited / applicable"
            color="blue"
          />
          <StatCard
            label="Relevant citation rate"
            value={`${citations.relevant_citation_rate}%`}
            sub="excl. off-topic queries"
            color={citations.relevant_citation_rate >= 60 ? "green" : citations.relevant_citation_rate >= 40 ? "amber" : "red"}
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

      {/* Gap analysis */}
      {citations.gap_analysis.length > 0 && (
        <section className="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <h2 className="text-sm font-semibold text-amber-800 mb-3">Priority citation gaps</h2>
          <ul className="space-y-2">
            {citations.gap_analysis.map(g => {
              const prompt = allPrompts.find(p => p.id === g.prompt_id);
              return (
                <li key={g.prompt_id} className="flex gap-3 text-sm">
                  <span className="text-amber-500 mt-0.5 shrink-0">⚑</span>
                  <div>
                    {prompt && (
                      <p className="text-amber-900 font-medium">&ldquo;{prompt.text}&rdquo;
                        {prompt.monthly_searches && (
                          <span className="ml-2 text-xs font-normal text-amber-600">
                            {dailySearches(prompt.monthly_searches)} · {prompt.monthly_searches.toLocaleString()}/mo
                          </span>
                        )}
                      </p>
                    )}
                    <p className="text-amber-700 mt-0.5">{g.advice}</p>
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      {/* Prompts by intent category */}
      {INTENT_ORDER.filter(cat => grouped[cat]?.length).map(cat => (
        <section key={cat}>
          <div className="flex items-center gap-2 mb-3">
            <h2 className="text-base font-medium text-slate-900">{intentLabel(cat)}</h2>
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${intentColor(cat)}`}>
              {grouped[cat].filter(p => citedSet.has(p.id)).length} / {grouped[cat].filter(p => relevantSet.has(p.id)).length} relevant cited
            </span>
          </div>
          <div className="space-y-2">
            {grouped[cat].map(p => {
              const cited = citedSet.has(p.id);
              const relevant = relevantSet.has(p.id);
              const coVenues = p.venues_cited.filter(s => s !== params.slug);
              return (
                <PromptRow
                  key={p.id}
                  prompt={p}
                  cited={cited}
                  relevant={relevant}
                  coVenues={coVenues}
                  allVenues={venues}
                />
              );
            })}
          </div>
        </section>
      ))}

      {/* Daily search landscape */}
      <section className="bg-white rounded-lg border border-slate-200 p-4">
        <h2 className="text-sm font-medium text-slate-700 mb-4">Daily search landscape — all relevant prompts</h2>
        <div className="space-y-2">
          {allPrompts
            .filter(p => relevantSet.has(p.id))
            .sort((a, b) => (b.monthly_searches ?? 0) - (a.monthly_searches ?? 0))
            .map(p => {
              const cited = citedSet.has(p.id);
              const daily = Math.round((p.monthly_searches ?? 0) / 30);
              const maxMonthly = Math.max(...allPrompts.filter(x => relevantSet.has(x.id)).map(x => x.monthly_searches ?? 0));
              const barWidth = maxMonthly ? Math.round((p.monthly_searches ?? 0) / maxMonthly * 100) : 0;
              return (
                <div key={p.id} className="flex items-center gap-3 text-xs">
                  <div className="w-4 shrink-0">
                    {cited
                      ? <span className="text-emerald-500 font-bold">✓</span>
                      : <span className="text-red-400">✗</span>
                    }
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-slate-700 truncate">{p.text}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden max-w-[200px]">
                        <div
                          className={`h-full rounded-full ${cited ? "bg-emerald-400" : "bg-slate-300"}`}
                          style={{ width: `${barWidth}%` }}
                        />
                      </div>
                      <span className="text-slate-400 shrink-0">{daily.toLocaleString()}/day · {(p.monthly_searches ?? 0).toLocaleString()}/mo</span>
                    </div>
                  </div>
                  {p.intent_category && (
                    <span className={`px-1.5 py-0.5 rounded text-xs shrink-0 ${intentColor(p.intent_category)}`}>
                      {intentLabel(p.intent_category)}
                    </span>
                  )}
                </div>
              );
            })}
        </div>
      </section>
    </div>
  );
}

function PromptRow({
  prompt,
  cited,
  relevant,
  coVenues,
  allVenues,
}: {
  prompt: CitationPrompt;
  cited: boolean;
  relevant: boolean;
  coVenues: string[];
  allVenues: { slug: string; venue_name: string }[];
}) {
  const daily = prompt.monthly_searches ? Math.round(prompt.monthly_searches / 30) : null;

  return (
    <div className={`rounded-lg border p-3 text-sm ${
      !relevant
        ? "bg-slate-50 border-slate-100 opacity-50"
        : cited
          ? "bg-emerald-50 border-emerald-200"
          : "bg-red-50 border-red-200"
    }`}>
      <div className="flex items-start gap-3">
        <span className={`mt-0.5 text-base shrink-0 ${cited ? "text-emerald-500" : relevant ? "text-red-400" : "text-slate-300"}`}>
          {cited ? "✓" : relevant ? "✗" : "—"}
        </span>
        <div className="flex-1 min-w-0">
          <p className={`font-medium leading-snug ${cited ? "text-emerald-900" : relevant ? "text-red-900" : "text-slate-500"}`}>
            &ldquo;{prompt.text}&rdquo;
          </p>
          <div className="flex flex-wrap items-center gap-3 mt-1.5">
            {daily !== null && (
              <span className="text-xs text-slate-500">
                <span className="font-medium text-slate-700">{daily.toLocaleString()}</span>/day &nbsp;·&nbsp;
                <span className="font-medium text-slate-700">{(prompt.monthly_searches ?? 0).toLocaleString()}</span>/mo
              </span>
            )}
            {!relevant && (
              <span className="text-xs text-slate-400 italic">Not relevant to this venue&rsquo;s region</span>
            )}
            {cited && coVenues.length > 0 && (
              <span className="text-xs text-emerald-700">
                Also cited: {coVenues.map(s => {
                  const v = allVenues.find(x => x.slug === s);
                  return v?.venue_name ?? s;
                }).slice(0, 3).join(", ")}
                {coVenues.length > 3 ? ` +${coVenues.length - 3} more` : ""}
              </span>
            )}
            {!cited && relevant && coVenues.length > 0 && (
              <span className="text-xs text-red-600">
                Cited instead: {coVenues.map(s => {
                  const v = allVenues.find(x => x.slug === s);
                  return v?.venue_name ?? s;
                }).slice(0, 3).join(", ")}
                {coVenues.length > 3 ? ` +${coVenues.length - 3} more` : ""}
              </span>
            )}
            {!cited && relevant && coVenues.length === 0 && (
              <span className="text-xs text-red-500 italic">No venues cited — zero-result query</span>
            )}
          </div>
          {prompt.topic_tags && (
            <div className="flex flex-wrap gap-1 mt-1.5">
              {prompt.topic_tags.map(t => (
                <span key={t} className="px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded text-xs">{t}</span>
              ))}
            </div>
          )}
        </div>
      </div>
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

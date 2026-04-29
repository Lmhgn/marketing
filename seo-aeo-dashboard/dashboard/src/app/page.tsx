import Link from "next/link";
import { averages, topOpportunities, venues } from "@/lib/data";
import {
  getAllCitations,
  computePortfolioStats,
  computeReadinessScore,
  readinessBand,
} from "@/lib/citations";
import { ScoreBadge } from "@/components/ScoreBadge";
import { VenueTable } from "@/components/VenueTable";
import ExportButton from "@/components/ExportButton";
import { AEO_LABELS, GEO_LABELS } from "@/types/venue";

export default function OverviewPage() {
  const aeoBand  = bandFor(averages.aeo);
  const geoBand  = bandFor(averages.geo);
  const citations = getAllCitations();
  const stats    = computePortfolioStats(citations);

  const citationValues = Object.values(citations);
  const avgCitationRate = citationValues.length
    ? citationValues.reduce((s, c) => s + c.citation_rate, 0) / citationValues.length
    : 0;
  const avgReadiness = computeReadinessScore(averages.aeo, averages.geo, avgCitationRate);
  const rBand = readinessBand(avgReadiness);

  const totalPrompts = venues.length * (citationValues[0]?.prompts.length ?? 0);

  return (
    <div className="space-y-8">
      <section>
        <h1 className="text-2xl font-semibold text-slate-900 mb-1">Portfolio Overview</h1>
        <p className="text-sm text-slate-600">{venues.length} UK music venues — average scores across the portfolio.</p>
      </section>

      {/* AI Market Share Banner */}
      <section className="bg-slate-900 rounded-xl p-6 text-white">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div>
            <p className="text-xs uppercase tracking-widest text-slate-400 mb-2">AI Search Capture Rate</p>
            <div className="flex items-baseline gap-3">
              <span className="text-6xl font-bold tabular-nums">{stats.captureRate}%</span>
              <span className="text-slate-400 text-sm max-w-[200px] leading-snug">
                of available AI search opportunity currently captured
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-3">
              {totalPrompts} venue-specific prompts across {venues.length} venues
            </p>
          </div>

          <div className="flex items-center gap-6">
            <div className="text-center">
              <p className="text-3xl font-bold text-emerald-400 tabular-nums">
                {stats.citedDaily.toLocaleString()}
              </p>
              <p className="text-xs text-slate-400 mt-1">searches/day<br/>captured</p>
            </div>
            <div className="w-px h-12 bg-slate-700" />
            <div className="text-center">
              <p className="text-3xl font-bold text-red-400 tabular-nums">
                {stats.missedDaily.toLocaleString()}
              </p>
              <p className="text-xs text-slate-400 mt-1">searches/day<br/>missed</p>
            </div>
          </div>
        </div>

        <div className="mt-5">
          <div className="flex justify-between text-xs text-slate-500 mb-1.5">
            <span>Current capture</span>
            <span>Gap to close</span>
          </div>
          <div className="h-2.5 bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-emerald-400 rounded-full transition-all"
              style={{ width: `${stats.captureRate}%` }}
            />
          </div>
        </div>
      </section>

      {/* Metric cards */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <ScoreBadge score={averages.aeo} band={aeoBand} label="Avg. AEO score" />
          <p className="text-xs text-slate-500 mt-3">
            Answer Engine Optimisation — structured data, FAQ content, semantic clarity.
          </p>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <ScoreBadge score={averages.geo} band={geoBand} label="Avg. GEO score" />
          <p className="text-xs text-slate-500 mt-3">
            Generative Engine Optimisation — entity signals, topical depth, corroboration.
          </p>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <ScoreBadge score={avgReadiness} band={rBand} label="Avg. AI Readiness" />
          <p className="text-xs text-slate-500 mt-3">
            Combined score: AEO (40%) + GEO (35%) + LLM citation rate (25%).
          </p>
        </div>
      </section>

      {/* Venue table */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-medium text-slate-900">Venue comparison</h2>
          <ExportButton venues={venues} citations={citations} />
        </div>
        <VenueTable venues={venues} />
      </section>

      {/* Top opportunities */}
      <section>
        <h2 className="text-lg font-medium text-slate-900 mb-4">Top opportunities</h2>
        <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="text-left px-4 py-2 font-medium">Venue</th>
                <th className="text-left px-4 py-2 font-medium">Component</th>
                <th className="text-left px-4 py-2 font-medium">Type</th>
                <th className="text-right px-4 py-2 font-medium">Score</th>
              </tr>
            </thead>
            <tbody>
              {topOpportunities.map((o, i) => (
                <tr key={i} className="border-t border-slate-100">
                  <td className="px-4 py-2">
                    <Link href={`/venue/${o.slug}`} className="text-blue-600 hover:underline">{o.venue}</Link>
                  </td>
                  <td className="px-4 py-2 text-slate-700">
                    {(o.type === "AEO" ? AEO_LABELS : GEO_LABELS)[o.component] ?? o.component}
                  </td>
                  <td className="px-4 py-2 text-slate-600">{o.type}</td>
                  <td className="px-4 py-2 text-right font-mono text-red-600">{o.score}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function bandFor(n: number): "critical" | "weak" | "moderate" | "good" | "strong" {
  if (n < 30) return "critical";
  if (n < 50) return "weak";
  if (n < 70) return "moderate";
  if (n < 85) return "good";
  return "strong";
}

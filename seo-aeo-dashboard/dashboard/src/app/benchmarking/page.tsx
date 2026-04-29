import { competitors, portfolio, getAllPlotPoints, getMarketAverages } from "@/lib/competitors";
import { bandColor } from "@/lib/data";
import { getCompetitorCitationLeaderboard } from "@/lib/citations";
import ScatterPlot from "@/components/ScatterPlot";
import Link from "next/link";

// Build slug → name maps for the co-citation leaderboard display
const PORTFOLIO_MAP:  Record<string, string> = {};
const COMPETITOR_MAP: Record<string, string> = {};
for (const v of portfolio)   PORTFOLIO_MAP[v.slug]  = v.venue_name;
for (const v of competitors) COMPETITOR_MAP[v.slug] = v.venue_name;

export default function Benchmarking() {
  const points  = getAllPlotPoints();
  const averages = getMarketAverages();
  const portfolioGap = {
    aeo: Math.round((averages.portfolio.aeo  - averages.competitors.aeo)  * 10) / 10,
    geo: Math.round((averages.portfolio.geo  - averages.competitors.geo)  * 10) / 10,
  };

  const leaderboard = getCompetitorCitationLeaderboard();
  const maxWeighted = leaderboard[0]?.weighted_monthly ?? 1;

  const allVenues = [
    ...competitors.map(v => ({ ...v, type: "competitor" as const })),
    ...portfolio.map(v   => ({ ...v, type: "portfolio" as const })),
  ].sort((a, b) => (b.aeo_score + b.geo_score) - (a.aeo_score + a.geo_score));

  return (
    <div className="space-y-8">
      <div>
        <Link href="/" className="text-sm text-blue-600 hover:underline">← Portfolio overview</Link>
        <h1 className="text-2xl font-semibold text-slate-900 mt-3">Competitor Benchmarking</h1>
        <p className="text-sm text-slate-500 mt-1">
          O2 / AMG portfolio vs 10 independent UK music venues — AEO &amp; GEO scores compared.
        </p>
      </div>

      {/* Summary stat cards */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Portfolio avg AEO"
          value={averages.portfolio.aeo}
          sub="20 O2 / AMG venues"
          highlight={false}
        />
        <StatCard
          label="Market avg AEO"
          value={averages.competitors.aeo}
          sub="10 independent venues"
          highlight={averages.competitors.aeo > averages.portfolio.aeo}
        />
        <StatCard
          label="Portfolio avg GEO"
          value={averages.portfolio.geo}
          sub="20 O2 / AMG venues"
          highlight={false}
        />
        <StatCard
          label="Market avg GEO"
          value={averages.competitors.geo}
          sub="10 independent venues"
          highlight={averages.competitors.geo > averages.portfolio.geo}
        />
      </section>

      {(portfolioGap.aeo < 0 || portfolioGap.geo < 0) && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-sm text-amber-800">
          <strong>Gap alert:</strong> Competitors lead by{" "}
          {portfolioGap.aeo < 0 && <><strong>{Math.abs(portfolioGap.aeo)} pts</strong> on AEO</>}
          {portfolioGap.aeo < 0 && portfolioGap.geo < 0 && " and "}
          {portfolioGap.geo < 0 && <><strong>{Math.abs(portfolioGap.geo)} pts</strong> on GEO</>}.
          {" "}Structured data and FAQ content are the primary differentiators.
        </div>
      )}

      {/* Scatter plot */}
      <section className="bg-gray-950 rounded-xl border border-gray-800 p-4">
        <h2 className="text-sm font-medium text-gray-300 mb-1">Market landscape — AEO vs GEO</h2>
        <p className="text-xs text-gray-500 mb-4">
          Top-right quadrant = strong performers. Each dot is one venue. Orange = competitor, blue = O2 portfolio.
        </p>
        <ScatterPlot data={points} />
      </section>

      {/* Co-citation leaderboard */}
      {leaderboard.length > 0 && (
        <section className="bg-white rounded-lg border border-slate-200 overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-100">
            <h2 className="text-base font-medium text-slate-900">LLM Co-Citation Leaderboard</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Venues cited instead of us on missed prompts — ranked by total search opportunity displaced.{" "}
              <span className="px-1.5 py-0.5 rounded bg-orange-100 text-orange-700 text-xs font-medium">Competitor</span>
              {" "}<span className="px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 text-xs font-medium">Portfolio</span>
            </p>
          </div>
          <div className="divide-y divide-slate-50">
            {leaderboard.map((entry, i) => {
              const isCompetitor = !!COMPETITOR_MAP[entry.slug];
              const name = COMPETITOR_MAP[entry.slug] ?? PORTFOLIO_MAP[entry.slug] ?? entry.slug;
              const href = isCompetitor ? `/competitor/${entry.slug}` : `/venue/${entry.slug}`;
              const barPct = Math.round(entry.weighted_monthly / maxWeighted * 100);
              const daily  = Math.round(entry.weighted_monthly / 30);
              return (
                <div key={entry.slug} className="flex items-center gap-4 px-4 py-3">
                  <span className="text-xs text-slate-400 font-mono w-5 shrink-0">{i + 1}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Link href={href} className="text-sm font-medium text-slate-800 hover:text-blue-600 hover:underline">
                        {name}
                      </Link>
                      <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                        isCompetitor ? "bg-orange-100 text-orange-700" : "bg-blue-100 text-blue-700"
                      }`}>
                        {isCompetitor ? "Competitor" : "Portfolio"}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 max-w-[240px] h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${isCompetitor ? "bg-orange-400" : "bg-blue-400"}`}
                          style={{ width: `${barPct}%` }}
                        />
                      </div>
                      <span className="text-xs text-slate-400 shrink-0">
                        {daily.toLocaleString()}/day displaced · {entry.appearances} prompt{entry.appearances !== 1 ? "s" : ""}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Combined ranked table */}
      <section>
        <h2 className="text-lg font-medium text-slate-900 mb-3">All venues ranked</h2>
        <div className="overflow-x-auto bg-white rounded-lg border border-slate-200">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="text-left px-4 py-3 font-medium w-8">#</th>
                <th className="text-left px-4 py-3 font-medium">Venue</th>
                <th className="text-left px-4 py-3 font-medium">Region</th>
                <th className="text-left px-4 py-3 font-medium">Type</th>
                <th className="text-right px-4 py-3 font-medium">AEO</th>
                <th className="text-right px-4 py-3 font-medium">GEO</th>
              </tr>
            </thead>
            <tbody>
              {allVenues.map((v, i) => (
                <tr
                  key={v.slug}
                  className={`border-t border-slate-100 ${
                    v.type === "competitor" ? "bg-orange-50/40 hover:bg-orange-50" : "hover:bg-slate-50"
                  }`}
                >
                  <td className="px-4 py-3 text-slate-400 text-xs">{i + 1}</td>
                  <td className="px-4 py-3 font-medium text-slate-900">
                    <Link
                      href={v.type === "portfolio" ? `/venue/${v.slug}` : `/competitor/${v.slug}`}
                      className="hover:text-blue-600 hover:underline"
                    >
                      {v.venue_name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-slate-500">{v.region}</td>
                  <td className="px-4 py-3">
                    <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                      v.type === "competitor"
                        ? "bg-orange-100 text-orange-700"
                        : "bg-blue-100 text-blue-700"
                    }`}>
                      {v.type === "competitor" ? "Competitor" : "O2 / AMG"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="inline-flex items-center gap-2">
                      <span className="font-mono">{v.aeo_score.toFixed(1)}</span>
                      <span className={`px-1.5 py-0.5 rounded text-xs ${bandColor[v.aeo_band]}`}>
                        {v.aeo_band}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="inline-flex items-center gap-2">
                      <span className="font-mono">{v.geo_score.toFixed(1)}</span>
                      <span className={`px-1.5 py-0.5 rounded text-xs ${bandColor[v.geo_band]}`}>
                        {v.geo_band}
                      </span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function StatCard({
  label, value, sub, highlight,
}: {
  label: string; value: number; sub: string; highlight: boolean;
}) {
  return (
    <div className={`rounded-lg border p-4 ${
      highlight
        ? "bg-amber-50 border-amber-200"
        : "bg-white border-slate-200"
    }`}>
      <p className="text-xs text-slate-500 uppercase tracking-wide">{label}</p>
      <p className={`text-3xl font-bold mt-1 ${highlight ? "text-amber-700" : "text-slate-900"}`}>
        {value}
      </p>
      <p className="text-xs text-slate-400 mt-1">{sub}</p>
      {highlight && (
        <p className="text-xs text-amber-600 font-medium mt-1">↑ above portfolio</p>
      )}
    </div>
  );
}

"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { bandColor, regions } from "@/lib/data";
import { getAllCitations, citationBandBg, computeReadinessScore, readinessBand } from "@/lib/citations";
import CitationBar from "@/components/CitationBar";
import type { VenueReport } from "@/types/venue";

const citations = getAllCitations();

type SortCol = "readiness" | "aeo" | "geo" | "citation";

function SortHeader({
  label, col, active, dir, onClick, align = "right", tooltip,
}: {
  label: string; col: SortCol; active: SortCol; dir: "asc" | "desc";
  onClick: (c: SortCol) => void; align?: "left" | "right"; tooltip?: string;
}) {
  const isActive = col === active;
  return (
    <th
      className={`px-4 py-3 font-medium cursor-pointer select-none hover:text-slate-900 relative group/hdr ${align === "right" ? "text-right" : "text-left"}`}
      onClick={() => onClick(col)}
    >
      <span className="inline-flex items-center gap-1">
        {align === "right" && (
          <span className={`text-xs ${isActive ? "text-slate-700" : "text-slate-300"}`}>
            {isActive ? (dir === "desc" ? "↓" : "↑") : "⇅"}
          </span>
        )}
        {label}
        {tooltip && <span className="ml-0.5 text-slate-400 text-xs font-normal">ⓘ</span>}
        {align === "left" && (
          <span className={`text-xs ${isActive ? "text-slate-700" : "text-slate-300"}`}>
            {isActive ? (dir === "desc" ? "↓" : "↑") : "⇅"}
          </span>
        )}
      </span>

      {tooltip && (
        <div className="absolute left-1/2 -translate-x-1/2 top-full mt-2 z-30 w-72 p-3 bg-slate-900 text-white text-xs rounded-lg shadow-xl opacity-0 group-hover/hdr:opacity-100 pointer-events-none transition-opacity normal-case font-normal text-left leading-relaxed whitespace-normal">
          <div className="absolute -top-1.5 left-1/2 -translate-x-1/2 w-3 h-3 bg-slate-900 rotate-45 rounded-sm" />
          {tooltip}
        </div>
      )}
    </th>
  );
}

export function VenueTable({ venues }: { venues: VenueReport[] }) {
  const [region,  setRegion]  = useState<string>("All");
  const [minScore, setMinScore] = useState<number>(0);
  const [sortCol, setSortCol]  = useState<SortCol>("readiness");
  const [sortDir, setSortDir]  = useState<"asc" | "desc">("desc");

  function handleSort(col: SortCol) {
    if (col === sortCol) {
      setSortDir(d => d === "desc" ? "asc" : "desc");
    } else {
      setSortCol(col);
      setSortDir("desc");
    }
  }

  const rows = useMemo(() => {
    return venues
      .filter(v => region === "All" || v.region === region)
      .filter(v => Math.min(v.aeo_score, v.geo_score) >= minScore)
      .map(v => {
        const c = citations[v.slug];
        const readiness = computeReadinessScore(
          v.aeo_score,
          v.geo_score,
          c?.citation_rate ?? 0,
        );
        return { v, c, readiness };
      })
      .sort((a, b) => {
        let diff = 0;
        if      (sortCol === "aeo")      diff = a.v.aeo_score      - b.v.aeo_score;
        else if (sortCol === "geo")      diff = a.v.geo_score      - b.v.geo_score;
        else if (sortCol === "citation") diff = (a.c?.citation_rate ?? 0) - (b.c?.citation_rate ?? 0);
        else                            diff = a.readiness         - b.readiness;
        return sortDir === "desc" ? -diff : diff;
      });
  }, [venues, region, minScore, sortCol, sortDir]);

  return (
    <div>
      {/* Filters */}
      <div className="flex flex-wrap gap-4 mb-4 items-end">
        <div>
          <label className="block text-xs text-slate-500 mb-1">Region</label>
          <select
            value={region}
            onChange={e => setRegion(e.target.value)}
            className="border border-slate-300 rounded px-2 py-1 text-sm bg-white"
          >
            <option value="All">All regions</option>
            {regions.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs text-slate-500 mb-1">Min combined score: {minScore}</label>
          <input
            type="range" min={0} max={100} value={minScore}
            onChange={e => setMinScore(Number(e.target.value))}
            className="w-48"
          />
        </div>
        <div className="text-xs text-slate-500 ml-auto">{rows.length} venues</div>
      </div>

      <div className="overflow-x-auto bg-white rounded-lg border border-slate-200">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="text-left px-4 py-3 font-medium">Venue</th>
              <th className="text-left px-4 py-3 font-medium">Region</th>
              <SortHeader label="AI Readiness" col="readiness" active={sortCol} dir={sortDir} onClick={handleSort}
                tooltip="The overall score combining AEO (40%), GEO (35%), and LLM Citation (25%). A venue scoring 'strong' is well-placed to appear when someone asks an AI assistant like ChatGPT or Siri 'Where should I see a gig in Manchester?'" />
              <SortHeader label="AEO" col="aeo" active={sortCol} dir={sortDir} onClick={handleSort}
                tooltip="Answer Engine Optimisation — does the website make facts easy for AI to extract? E.g. if someone asks Alexa 'What is the capacity of O2 Academy Brixton?' the answer needs to be clearly structured on the page. Scored on schema markup, FAQ sections, headings, and content." />
              <SortHeader label="GEO" col="geo" active={sortCol} dir={sortDir} onClick={handleSort}
                tooltip="Generative Engine Optimisation — how well-known is the venue inside AI systems? E.g. when someone asks ChatGPT 'What are the best live music venues in London?' does it know enough about this venue to include it? Scored on Wikipedia presence, external references, and factual coverage." />
              <SortHeader label="LLM citation" col="citation" active={sortCol} dir={sortDir} onClick={handleSort} align="left"
                tooltip="We sent 15 real questions to Claude — e.g. 'What's the atmosphere like at O2 Forum Kentish Town?' — and checked how often it actually named the venue. A 73% rate means it was cited in 11 out of 15 prompts. Click the bar to see each question." />
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {rows.map(({ v, c, readiness }) => {
              const rBand = readinessBand(readiness);
              const promptTotal = c?.prompts.length ?? 15;
              return (
                <tr key={v.slug} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium text-slate-900">{v.venue_name}</td>
                  <td className="px-4 py-3 text-slate-500 text-xs">{v.region}</td>

                  {/* AI Readiness */}
                  <td className="px-4 py-3 text-right">
                    <div className="inline-flex items-center gap-2">
                      <span className="font-mono font-semibold text-slate-900">{readiness.toFixed(1)}</span>
                      <span className={`px-1.5 py-0.5 rounded text-xs ${bandColor[rBand]}`}>{rBand}</span>
                    </div>
                  </td>

                  {/* AEO */}
                  <td className="px-4 py-3 text-right">
                    <div className="inline-flex items-center gap-2">
                      <span className="font-mono text-slate-700">{v.aeo_score.toFixed(1)}</span>
                      <span className={`px-1.5 py-0.5 rounded text-xs ${bandColor[v.aeo_band]}`}>{v.aeo_band}</span>
                    </div>
                  </td>

                  {/* GEO */}
                  <td className="px-4 py-3 text-right">
                    <div className="inline-flex items-center gap-2">
                      <span className="font-mono text-slate-700">{v.geo_score.toFixed(1)}</span>
                      <span className={`px-1.5 py-0.5 rounded text-xs ${bandColor[v.geo_band]}`}>{v.geo_band}</span>
                    </div>
                  </td>

                  {/* LLM citation */}
                  <td className="px-4 py-3">
                    {c ? (
                      <Link href={`/venue/${v.slug}/citations`} className="block group">
                        <CitationBar
                          rate={c.citation_rate}
                          band={c.citation_band}
                          count={c.citation_count}
                          total={promptTotal}
                          compact
                        />
                      </Link>
                    ) : (
                      <span className="text-xs text-slate-400">—</span>
                    )}
                  </td>

                  <td className="px-4 py-3 text-right whitespace-nowrap">
                    <Link href={`/venue/${v.slug}`} className="text-blue-600 hover:underline text-xs">
                      Details →
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

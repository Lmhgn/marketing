"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import type { ScoreSnapshot } from "@/lib/history";
import type { CitationSnapshot } from "@/lib/citation-history";

interface Props {
  data: ScoreSnapshot[];
  citationData?: CitationSnapshot[];
}

const AEO_COLOR      = "#6366f1"; // indigo-500
const GEO_COLOR      = "#10b981"; // emerald-500
const CITATION_COLOR = "#a855f7"; // purple-500

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

export default function TrendChart({ data, citationData }: Props) {
  if (!data.length) return null;

  const citationByDate = citationData
    ? Object.fromEntries(citationData.map(s => [s.date, s.citation_rate]))
    : {};

  const chartData = data.map(s => ({
    label:    formatDate(s.date),
    AEO:      s.aeo_score,
    GEO:      s.geo_score,
    ...(citationData ? { Citation: citationByDate[s.date] ?? null } : {}),
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
        <XAxis
          dataKey="label"
          tick={{ fill: "#9ca3af", fontSize: 12 }}
          tickLine={false}
          axisLine={{ stroke: "#374151" }}
        />
        <YAxis
          domain={[0, 100]}
          tick={{ fill: "#9ca3af", fontSize: 12 }}
          tickLine={false}
          axisLine={false}
          width={32}
        />
        <Tooltip
          contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 6, fontSize: 13 }}
          labelStyle={{ color: "#f9fafb", marginBottom: 4 }}
          itemStyle={{ color: "#d1d5db" }}
        />
        <Legend
          wrapperStyle={{ fontSize: 13, paddingTop: 8 }}
          formatter={value => <span style={{ color: "#d1d5db" }}>{value} score</span>}
        />
        <ReferenceLine y={50} stroke="#374151" strokeDasharray="4 4" />
        <Line type="monotone" dataKey="AEO" stroke={AEO_COLOR} strokeWidth={2}
          dot={{ r: 4, fill: AEO_COLOR, strokeWidth: 0 }} activeDot={{ r: 6 }} />
        <Line type="monotone" dataKey="GEO" stroke={GEO_COLOR} strokeWidth={2}
          dot={{ r: 4, fill: GEO_COLOR, strokeWidth: 0 }} activeDot={{ r: 6 }} />
        {citationData && (
          <Line type="monotone" dataKey="Citation" stroke={CITATION_COLOR} strokeWidth={2}
            strokeDasharray="5 3"
            dot={{ r: 4, fill: CITATION_COLOR, strokeWidth: 0 }} activeDot={{ r: 6 }} />
        )}
      </LineChart>
    </ResponsiveContainer>
  );
}

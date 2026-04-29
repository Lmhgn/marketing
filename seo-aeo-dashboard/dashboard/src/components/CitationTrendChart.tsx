"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import type { CitationSnapshot } from "@/lib/citation-history";

interface Props {
  data: CitationSnapshot[];
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

export default function CitationTrendChart({ data }: Props) {
  if (data.length < 2) return null;

  const chartData = data.map(s => ({
    label:    formatDate(s.date),
    rate:     s.citation_rate,
    count:    s.citation_count,
    band:     s.citation_band,
  }));

  return (
    <ResponsiveContainer width="100%" height={160}>
      <AreaChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="citationGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#a855f7" stopOpacity={0.25} />
            <stop offset="95%" stopColor="#a855f7" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis
          dataKey="label"
          tick={{ fill: "#94a3b8", fontSize: 11 }}
          tickLine={false}
          axisLine={{ stroke: "#e2e8f0" }}
        />
        <YAxis
          domain={[0, 100]}
          tick={{ fill: "#94a3b8", fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          width={32}
          tickFormatter={v => `${v}%`}
        />
        <Tooltip
          contentStyle={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 6, fontSize: 12 }}
          labelStyle={{ color: "#0f172a", marginBottom: 2, fontWeight: 600 }}
          formatter={(value: number) => [`${value}%`, "Citation rate"]}
        />
        <ReferenceLine y={67} stroke="#a855f7" strokeDasharray="4 3" strokeOpacity={0.4}
          label={{ value: "Strong", position: "right", fontSize: 10, fill: "#a855f7" }} />
        <Area
          type="monotone"
          dataKey="rate"
          stroke="#a855f7"
          strokeWidth={2}
          fill="url(#citationGrad)"
          dot={{ r: 4, fill: "#a855f7", strokeWidth: 0 }}
          activeDot={{ r: 6 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

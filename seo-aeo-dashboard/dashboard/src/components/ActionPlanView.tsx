"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import type { ActionItem, ActionCategory, ActionPriority } from "@/lib/actions";

const CATEGORY_LABELS: Record<ActionCategory, string> = {
  schema:  "Schema / Technical",
  faq:     "FAQ Content",
  content: "Content Depth",
  linking: "Internal Linking",
};

const CATEGORY_COLORS: Record<ActionCategory, string> = {
  schema:  "bg-indigo-100 text-indigo-700",
  faq:     "bg-purple-100 text-purple-700",
  content: "bg-teal-100 text-teal-700",
  linking: "bg-slate-100 text-slate-600",
};

const PRIORITY_COLORS: Record<ActionPriority, string> = {
  critical: "bg-red-100 text-red-700 border-red-200",
  high:     "bg-amber-100 text-amber-700 border-amber-200",
  medium:   "bg-blue-100 text-blue-700 border-blue-200",
};

const PRIORITY_DOT: Record<ActionPriority, string> = {
  critical: "bg-red-500",
  high:     "bg-amber-400",
  medium:   "bg-blue-400",
};

const EFFORT_COLORS: Record<string, string> = {
  quick:       "text-emerald-600",
  medium:      "text-amber-600",
  substantial: "text-orange-600",
};

type DeployStatus = "recommended" | "in-progress" | "deployed";

const STATUS_CONFIG: Record<DeployStatus, { label: string; dot: string; text: string; next: DeployStatus }> = {
  "recommended": { label: "To do",       dot: "bg-slate-300",   text: "text-slate-500",   next: "in-progress" },
  "in-progress": { label: "In progress", dot: "bg-amber-400",   text: "text-amber-700",   next: "deployed"    },
  "deployed":    { label: "Deployed",    dot: "bg-emerald-500", text: "text-emerald-700", next: "recommended" },
};

const LS_KEY = "action-deploy-status";

function loadStatus(): Record<string, DeployStatus> {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(localStorage.getItem(LS_KEY) ?? "{}");
  } catch {
    return {};
  }
}

function saveStatus(s: Record<string, DeployStatus>) {
  try { localStorage.setItem(LS_KEY, JSON.stringify(s)); } catch { /* noop */ }
}

const ALL = "all" as const;
type Filter = ActionCategory | typeof ALL;

const TABS: { key: Filter; label: string }[] = [
  { key: ALL,       label: "All fixes" },
  { key: "schema",  label: "Schema" },
  { key: "faq",     label: "FAQ" },
  { key: "content", label: "Content" },
  { key: "linking", label: "Linking" },
];

const MAX_VENUE_CHIPS = 5;

export default function ActionPlanView({ items }: { items: ActionItem[] }) {
  const [filter,   setFilter]   = useState<Filter>(ALL);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [status,   setStatus]   = useState<Record<string, DeployStatus>>({});

  useEffect(() => { setStatus(loadStatus()); }, []);

  const getStatus = useCallback(
    (actionId: string, venueSlug: string): DeployStatus =>
      status[`${actionId}:${venueSlug}`] ?? "recommended",
    [status],
  );

  const cycleStatus = useCallback((actionId: string, venueSlug: string) => {
    const key     = `${actionId}:${venueSlug}`;
    const current = status[key] ?? "recommended";
    const next    = STATUS_CONFIG[current].next;
    const updated = { ...status, [key]: next };
    setStatus(updated);
    saveStatus(updated);
  }, [status]);

  function deployedCount(item: ActionItem): number {
    return item.affectedVenues.filter(v => getStatus(item.id, v.slug) === "deployed").length;
  }

  const visible = filter === ALL ? items : items.filter(i => i.category === filter);

  function toggle(id: string) {
    setExpanded(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  return (
    <div>
      {/* Category filter tabs */}
      <div className="flex gap-1 mb-6 border-b border-slate-200">
        {TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setFilter(t.key)}
            className={`px-4 py-2 text-sm font-medium rounded-t transition-colors ${
              filter === t.key
                ? "bg-white border border-b-white border-slate-200 -mb-px text-slate-900"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            {t.label}
            <span className="ml-1.5 text-xs text-slate-400">
              ({(t.key === ALL ? items : items.filter(i => i.category === t.key)).length})
            </span>
          </button>
        ))}
      </div>

      {/* Action cards */}
      <ol className="space-y-4">
        {visible.map((item, idx) => {
          const isOpen   = expanded.has(item.id);
          const shown    = item.affectedVenues.slice(0, MAX_VENUE_CHIPS);
          const extra    = item.affectedVenues.length - MAX_VENUE_CHIPS;
          const deployed = deployedCount(item);
          const total    = item.affectedVenues.length;
          const pct      = Math.round(deployed / total * 100);

          return (
            <li key={item.id} className="bg-white rounded-lg border border-slate-200 overflow-hidden">
              {/* Card header */}
              <div className="flex items-start gap-4 p-4">
                <span className="flex-shrink-0 w-7 h-7 rounded-full bg-slate-100 text-slate-500 text-xs font-mono flex items-center justify-center mt-0.5">
                  {idx + 1}
                </span>

                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded border text-xs font-semibold ${PRIORITY_COLORS[item.priority]}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${PRIORITY_DOT[item.priority]}`} />
                      {item.priority.toUpperCase()}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${CATEGORY_COLORS[item.category]}`}>
                      {CATEGORY_LABELS[item.category]}
                    </span>
                    <span className={`text-xs ${EFFORT_COLORS[item.effort]}`}>
                      ⏱ {item.effortLabel}
                    </span>
                  </div>

                  <h3 className="text-sm font-semibold text-slate-900 mb-1">{item.title}</h3>
                  <p className="text-xs text-slate-500 leading-relaxed">{item.description}</p>

                  <div className="flex flex-wrap gap-4 mt-3 text-xs">
                    <span className="text-indigo-600 font-medium">
                      AEO uplift: +{item.totalAeoImpact} pts across {total} venue{total !== 1 ? "s" : ""}
                    </span>
                    <span className="text-emerald-600 font-medium">
                      GEO uplift: +{item.totalGeoImpact} pts
                    </span>
                    <span className="text-slate-400">
                      (+{item.aeoImpactPerVenue} AEO / +{item.geoImpactPerVenue} GEO per venue)
                    </span>
                  </div>

                  {/* Deployment progress bar */}
                  <div className="mt-3 flex items-center gap-2">
                    <div className="flex-1 max-w-[160px] h-1.5 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${deployed === total ? "bg-emerald-500" : "bg-amber-400"}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="text-xs text-slate-500">
                      {deployed}/{total} venues deployed
                    </span>
                  </div>
                </div>

                <button
                  onClick={() => toggle(item.id)}
                  className="flex-shrink-0 text-xs text-slate-400 hover:text-slate-600 flex flex-col items-end gap-1"
                >
                  <span className="font-mono text-slate-600 font-medium">{total}/20 venues</span>
                  <span>{isOpen ? "▲ hide" : "▼ show"}</span>
                </button>
              </div>

              {/* Expandable venue list with status toggles */}
              {isOpen && (
                <div className="border-t border-slate-100 px-4 py-3 bg-slate-50">
                  <p className="text-xs text-slate-400 mb-2">
                    Click a venue status badge to cycle: To do → In progress → Deployed
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {item.affectedVenues.map(v => {
                      const s    = getStatus(item.id, v.slug);
                      const cfg  = STATUS_CONFIG[s];
                      return (
                        <div key={v.slug} className="flex items-center gap-1 bg-white rounded border border-slate-200 pl-2 pr-1 py-0.5">
                          <Link
                            href={`/venue/${v.slug}`}
                            className="text-xs text-slate-700 hover:text-blue-700"
                          >
                            {v.name}
                          </Link>
                          <button
                            onClick={() => cycleStatus(item.id, v.slug)}
                            title={`Click to advance status (currently: ${cfg.label})`}
                            className={`inline-flex items-center gap-1 ml-1 px-1.5 py-0.5 rounded text-xs ${cfg.text} hover:opacity-75 transition-opacity`}
                          >
                            <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
                            {cfg.label}
                          </button>
                        </div>
                      );
                    })}
                    {extra > 0 && (
                      <span className="px-2 py-0.5 rounded bg-slate-200 text-xs text-slate-500 self-center">
                        +{extra} more (expand to see all)
                      </span>
                    )}
                  </div>
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

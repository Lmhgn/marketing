"use client";

import { useState } from "react";
import { type VenuePrompt } from "@/lib/citations";

export default function PromptRow({
  prompt,
}: {
  prompt: VenuePrompt;
}) {
  const [showResponse, setShowResponse] = useState(false);
  const daily = Math.round(prompt.monthly_searches / 30);

  return (
    <div className={`rounded-lg border p-3 text-sm ${
      prompt.cited
        ? "bg-emerald-50 border-emerald-200"
        : "bg-red-50 border-red-200"
    }`}>
      <div className="flex items-start gap-3">
        <span className={`mt-0.5 text-base shrink-0 ${prompt.cited ? "text-emerald-500" : "text-red-400"}`}>
          {prompt.cited ? "✓" : "✗"}
        </span>
        <div className="flex-1 min-w-0">
          <p className={`font-medium leading-snug ${prompt.cited ? "text-emerald-900" : "text-red-900"}`}>
            &ldquo;{prompt.text}&rdquo;
          </p>
          <div className="flex flex-wrap items-center gap-3 mt-1.5">
            <span className="text-xs text-slate-500">
              <span className="font-medium text-slate-700">{daily.toLocaleString()}</span>/day &nbsp;·&nbsp;
              <span className="font-medium text-slate-700">{prompt.monthly_searches.toLocaleString()}</span>/mo
            </span>
          </div>

          {!prompt.cited && (
            <p className="text-xs text-red-700 mt-1.5 italic">{prompt.advice}</p>
          )}

          {prompt.response_text && (
            <div className="mt-2">
              <button
                onClick={() => setShowResponse(v => !v)}
                className="text-xs text-slate-400 hover:text-slate-600 underline-offset-2 hover:underline transition-colors"
              >
                {showResponse ? "Hide AI response ↑" : "View AI response ↓"}
              </button>
              {showResponse && (
                <div className="mt-2 p-3 bg-white border border-slate-200 rounded-lg text-xs text-slate-600 leading-relaxed whitespace-pre-wrap max-h-52 overflow-y-auto font-mono">
                  {prompt.response_text}
                  {prompt.response_text.length >= 800 && (
                    <span className="text-slate-400 not-italic"> … [truncated]</span>
                  )}
                </div>
              )}
            </div>
          )}

          {prompt.topic_tags.length > 0 && (
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

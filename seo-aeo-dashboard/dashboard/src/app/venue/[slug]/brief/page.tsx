import Link from "next/link";
import { notFound } from "next/navigation";
import { venues } from "@/lib/data";
import { getVenueBrief, buildSchemaSnippet } from "@/lib/brief";
import { intentLabel, intentColor, dailySearches } from "@/lib/citations";
import SchemaBlock from "@/components/SchemaBlock";

export function generateStaticParams() {
  return venues.map(v => ({ slug: v.slug }));
}

export default function BriefPage({ params }: { params: { slug: string } }) {
  const venue = venues.find(v => v.slug === params.slug);
  if (!venue) notFound();

  const brief  = getVenueBrief(venue);
  const schema = buildSchemaSnippet(brief.schemaFields, venue.venue_name, venue.url);

  const todoCount = brief.schemaFields.filter(f => f.todo).length;

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <Link href="/" className="hover:text-blue-600">Overview</Link>
        <span>›</span>
        <Link href={`/venue/${params.slug}`} className="hover:text-blue-600">{venue.venue_name}</Link>
        <span>›</span>
        <span className="text-slate-800">Content Brief</span>
      </div>

      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Content Brief</h1>
        <p className="text-sm text-slate-500 mt-1">
          {venue.venue_name} · Generated from live site crawl · {brief.crawlDate}
        </p>
      </div>

      {/* What this brief covers */}
      <section className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-900">
        <p className="font-semibold mb-1">How to use this brief</p>
        <p className="text-blue-800 leading-relaxed">
          This brief is generated from a live crawl of the venue website and real AI test results.
          Section 1 gives you schema markup to copy and deploy. Section 2 shows every question
          an AI failed to answer for this venue, with specific content to add.
        </p>
      </section>

      {/* ── Section 1: Schema ── */}
      <section className="bg-white rounded-lg border border-slate-200 overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">1. Schema markup</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Copy this JSON-LD into the{" "}
              <code className="bg-slate-100 px-1 py-0.5 rounded text-slate-700">&lt;head&gt;</code>{" "}
              of the venue page. Fields marked{" "}
              <span className="text-amber-600 font-medium">⚠</span> need filling in before deploying.
            </p>
          </div>
          <div className="text-right shrink-0">
            {brief.hasMusicVenueSchema ? (
              <span className="px-2 py-1 rounded bg-emerald-100 text-emerald-700 text-xs font-medium">Already deployed</span>
            ) : (
              <span className="px-2 py-1 rounded bg-red-100 text-red-700 text-xs font-medium">Not deployed</span>
            )}
          </div>
        </div>

        {!brief.hasMusicVenueSchema && (
          <div className="px-5 py-3 bg-amber-50 border-b border-amber-100 text-xs text-amber-800">
            <strong>{todoCount} field{todoCount !== 1 ? "s" : ""} need manual input</strong> —
            capacity, postcode, and Wikipedia/Wikidata links are not auto-detectable and must be added by the team.
          </div>
        )}

        <div className="p-5 space-y-4">
          {/* Field checklist */}
          <div className="grid grid-cols-1 gap-1.5">
            {brief.schemaFields.map(f => (
              <div key={f.key} className="flex items-start gap-2 text-xs">
                <span className={`mt-0.5 shrink-0 font-bold ${f.todo ? "text-amber-500" : "text-emerald-500"}`}>
                  {f.todo ? "⚠" : "✓"}
                </span>
                <span className="font-mono text-slate-600 w-52 shrink-0">{f.key}</span>
                <span className={f.todo ? "text-amber-700 italic" : "text-slate-700"}>
                  {f.todo ? `Needs input — ${f.description}` : f.value}
                </span>
              </div>
            ))}
          </div>

          {/* Copyable snippet */}
          <SchemaBlock code={schema} />
        </div>
      </section>

      {/* ── Section 1b: FAQ schema ── */}
      {!brief.hasFaqSchema && (
        <section className="bg-white rounded-lg border border-slate-200 p-5">
          <div className="flex items-start justify-between gap-4 mb-3">
            <div>
              <h2 className="text-base font-semibold text-slate-900">2. FAQPage schema</h2>
              <p className="text-xs text-slate-500 mt-0.5">
                {brief.faqSubPageUrl
                  ? <>Your FAQ page exists at <a href={brief.faqSubPageUrl} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">{brief.faqSubPageUrl}</a> but has no FAQPage schema.</>
                  : "No FAQ page detected — create one and add FAQPage schema."}
              </p>
            </div>
            <span className="px-2 py-1 rounded bg-red-100 text-red-700 text-xs font-medium shrink-0">Not deployed</span>
          </div>

          <div className="bg-slate-50 rounded-lg p-3 text-xs text-slate-600 space-y-1.5">
            <p className="font-semibold text-slate-800">What to do:</p>
            {brief.faqSubPageUrl ? (
              <>
                <p>1. Add the following JSON-LD to the <code className="bg-white border border-slate-200 px-1 rounded">{"<head>"}</code> of <strong>{brief.faqSubPageUrl}</strong></p>
                <p>2. Surface 6–8 key Q&As from that page directly on the main venue page (e.g. in a collapsible FAQ section)</p>
              </>
            ) : (
              <>
                <p>1. Create a <strong>/faqs</strong> sub-page with 6–8 Q&A pairs covering: capacity, transport, accessibility, age policy, bag policy, parking</p>
                <p>2. Add FAQPage JSON-LD schema to that page</p>
                <p>3. Link from the main venue page and embed the top 3 questions inline</p>
              </>
            )}
            <p className="text-emerald-700 font-medium pt-1">Estimated impact: +10–14 AEO pts · unlocks FAQ rich results in Google</p>
          </div>
        </section>
      )}

      {/* ── Section 3: Content gaps ── */}
      <section>
        <div className="mb-3">
          <h2 className="text-base font-semibold text-slate-900">
            {brief.hasFaqSchema ? "2." : "3."} Citation gaps — questions AI couldn't answer
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            {brief.contentGaps.length} question{brief.contentGaps.length !== 1 ? "s" : ""} where AI failed to cite this venue,
            sorted by monthly search volume. Add the suggested content to fix each one.
          </p>
        </div>

        {brief.contentGaps.length === 0 ? (
          <p className="text-sm text-emerald-600 bg-emerald-50 border border-emerald-200 rounded-lg px-4 py-3">
            All prompts cited — no content gaps to fix.
          </p>
        ) : (
          <div className="space-y-3">
            {brief.contentGaps.map((gap, i) => (
              <div key={gap.promptId} className="bg-white rounded-lg border border-slate-200 p-4">
                <div className="flex items-start gap-3">
                  <span className="text-xs text-slate-400 font-mono w-5 shrink-0 mt-0.5">{i + 1}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1.5">
                      <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${intentColor(gap.intentCategory)}`}>
                        {intentLabel(gap.intentCategory)}
                      </span>
                      <span className="text-xs text-slate-400">
                        {dailySearches(gap.monthlySearches)} · {gap.monthlySearches.toLocaleString()}/mo
                      </span>
                      {gap.alsoСited.length > 0 && (
                        <span className="text-xs text-orange-600">
                          AI cited instead: {gap.alsoСited.slice(0, 2).join(", ")}
                        </span>
                      )}
                    </div>
                    <p className="text-sm font-medium text-slate-800 mb-2">&ldquo;{gap.question}&rdquo;</p>
                    <div className="bg-slate-50 rounded px-3 py-2 text-xs text-slate-700 leading-relaxed border border-slate-100">
                      <span className="font-semibold text-slate-900">What to add: </span>
                      {gap.advice}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

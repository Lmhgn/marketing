"use client";

import { useState } from "react";

export default function SchemaBlock({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);

  function copy() {
    const scriptTag = `<script type="application/ld+json">\n${code}\n</script>`;
    navigator.clipboard.writeText(scriptTag).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="relative rounded-lg border border-slate-200 bg-slate-950 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-800">
        <span className="text-xs text-slate-400 font-mono">JSON-LD · paste into &lt;head&gt;</span>
        <button
          onClick={copy}
          className="text-xs px-2.5 py-1 rounded bg-slate-700 hover:bg-slate-600 text-slate-200 transition-colors font-medium"
        >
          {copied ? "✓ Copied" : "Copy"}
        </button>
      </div>
      <pre className="p-4 text-xs text-slate-300 overflow-x-auto leading-relaxed">
        <code>{`<script type="application/ld+json">\n${code}\n</script>`}</code>
      </pre>
    </div>
  );
}

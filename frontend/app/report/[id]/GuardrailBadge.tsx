"use client";

import { useState } from "react";
import { SectionReport } from "@/lib/api";
import { Shield, ShieldAlert, ChevronDown, ChevronRight } from "lucide-react";

const GUARDRAIL_DESCRIPTIONS: Record<string, string> = {
  tone_normalizer: "Removed overconfident speculative language (e.g., 'definitely will', 'guaranteed to').",
  citation_enforcer: "Detected numeric claims without citation URLs. Review flagged figures before relying on them.",
};

export function GuardrailPanel({ sections }: { sections: SectionReport[] }) {
  const [open, setOpen] = useState(false);

  const allTriggered = sections.flatMap((s) =>
    s.guardrails_triggered.map((g) => ({ section: s.section, guardrail: g }))
  );
  const triggered = allTriggered.length > 0;

  return (
    <div className="bg-slate-900/50 border border-slate-700 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-slate-800/40 transition-colors"
      >
        {triggered
          ? <ShieldAlert className="w-5 h-5 text-orange-400" />
          : <Shield className="w-5 h-5 text-green-400" />}
        <span className="font-semibold text-white">Guardrails</span>
        {triggered
          ? <span className="text-xs bg-orange-900/40 text-orange-300 border border-orange-700 px-2 py-0.5 rounded-full">{allTriggered.length} triggered</span>
          : <span className="text-xs bg-green-900/40 text-green-300 border border-green-700 px-2 py-0.5 rounded-full">All clear</span>}
        <span className="ml-auto">{open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}</span>
      </button>
      {open && (
        <div className="px-5 pb-5 space-y-3">
          {!triggered && (
            <p className="text-sm text-slate-400">No guardrails were triggered for this report.</p>
          )}
          {allTriggered.map((item, i) => (
            <div key={i} className="flex gap-3 p-3 bg-orange-900/20 border border-orange-800 rounded-lg">
              <ShieldAlert className="w-4 h-4 text-orange-400 shrink-0 mt-0.5" />
              <div>
                <div className="text-sm font-medium text-orange-300">
                  {item.guardrail} <span className="text-orange-500 font-normal">({item.section} section)</span>
                </div>
                <div className="text-xs text-slate-400 mt-0.5">
                  {GUARDRAIL_DESCRIPTIONS[item.guardrail] || "Guardrail triggered."}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

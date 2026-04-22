"use client";

import { useState } from "react";
import { DueDiligenceReport } from "@/lib/api";
import { BarChart2, ChevronDown, ChevronRight } from "lucide-react";

function ScoreBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 70 ? "bg-green-500" : pct >= 40 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-slate-400">{label}</span>
        <span className="text-white font-medium">{pct}%</span>
      </div>
      <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function EvalScore({ report }: { report: DueDiligenceReport }) {
  const [open, setOpen] = useState(false);
  const scores = report.eval_scores;
  const sections = report.sections.filter((s) => s.llm_judge_score != null);

  if (!scores && sections.length === 0) return null;

  return (
    <div className="bg-slate-900/50 border border-slate-700 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-slate-800/40 transition-colors"
      >
        <BarChart2 className="w-5 h-5 text-blue-400" />
        <span className="font-semibold text-white">Eval Scores</span>
        <span className="text-xs text-slate-500">LLM-as-judge + deterministic metrics</span>
        <span className="ml-auto">{open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}</span>
      </button>
      {open && (
        <div className="px-5 pb-5 space-y-5">
          {scores && (
            <div>
              <div className="text-xs text-slate-500 mb-3">DETERMINISTIC METRICS</div>
              <div className="space-y-2">
                {Object.entries(scores)
                  .filter(([k]) => !k.startsWith("judge"))
                  .map(([k, v]) => (
                    <ScoreBar key={k} label={k.replace(/_/g, " ")} value={v as number} />
                  ))}
              </div>
            </div>
          )}
          {sections.length > 0 && (
            <div>
              <div className="text-xs text-slate-500 mb-3">LLM JUDGE SCORES (per section)</div>
              <div className="space-y-2">
                {sections.map((s) => (
                  <ScoreBar
                    key={s.section}
                    label={`${s.section} section`}
                    value={s.llm_judge_score!}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

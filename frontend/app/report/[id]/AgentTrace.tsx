"use client";

import { useState } from "react";
import { AgentStep } from "@/lib/api";
import { ChevronDown, ChevronRight, Wrench, Brain, Link } from "lucide-react";

function ToolCallRow({ tc }: { tc: AgentStep["tool_calls"][0] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border border-slate-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-3 py-2 bg-slate-800/60 text-left hover:bg-slate-700/50 transition-colors"
      >
        <Wrench className="w-3 h-3 text-blue-400 shrink-0" />
        <span className="text-xs font-mono text-blue-300">{tc.tool_name}</span>
        {open ? <ChevronDown className="w-3 h-3 ml-auto" /> : <ChevronRight className="w-3 h-3 ml-auto" />}
      </button>
      {open && (
        <div className="px-3 pb-3 bg-slate-900/40 space-y-2 text-xs font-mono">
          <div>
            <div className="text-slate-500 mt-2 mb-1">INPUT</div>
            <pre className="text-slate-300 whitespace-pre-wrap break-all">{JSON.stringify(tc.input, null, 2)}</pre>
          </div>
          <div>
            <div className="text-slate-500 mb-1">OUTPUT</div>
            <pre className="text-slate-300 whitespace-pre-wrap break-all">{tc.output.slice(0, 800)}{tc.output.length > 800 ? "..." : ""}</pre>
          </div>
        </div>
      )}
    </div>
  );
}

function StepRow({ step, index }: { step: AgentStep; index: number }) {
  const [open, setOpen] = useState(false);
  const confidenceColor = step.confidence >= 0.7 ? "text-green-400" : step.confidence >= 0.4 ? "text-yellow-400" : "text-red-400";

  return (
    <div className="border border-slate-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-4 py-3 bg-slate-800/40 text-left hover:bg-slate-700/40 transition-colors"
      >
        <span className="text-xs bg-slate-700 text-slate-300 rounded px-1.5 py-0.5 font-mono shrink-0">
          {String(index + 1).padStart(2, "0")}
        </span>
        <Brain className="w-4 h-4 text-purple-400 shrink-0" />
        <span className="text-sm font-medium text-white">{step.agent_name.replace("_", " ")}</span>
        <span className={`text-xs ml-auto ${confidenceColor}`}>
          {Math.round(step.confidence * 100)}% conf
        </span>
        <span className="text-xs text-slate-500">{step.tokens_used.toLocaleString()} tok</span>
        {open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
      </button>
      {open && (
        <div className="px-4 pb-4 space-y-3 bg-slate-900/20">
          {step.tool_calls.length > 0 && (
            <div>
              <div className="text-xs text-slate-500 mb-2 mt-3">TOOL CALLS ({step.tool_calls.length})</div>
              <div className="space-y-1">
                {step.tool_calls.map((tc, i) => (
                  <ToolCallRow key={i} tc={tc} />
                ))}
              </div>
            </div>
          )}
          {step.guardrails_triggered.length > 0 && (
            <div>
              <div className="text-xs text-slate-500 mb-1">GUARDRAILS TRIGGERED</div>
              <div className="flex gap-1 flex-wrap">
                {step.guardrails_triggered.map((g) => (
                  <span key={g} className="text-xs bg-orange-900/40 text-orange-300 border border-orange-700 px-2 py-0.5 rounded">
                    {g}
                  </span>
                ))}
              </div>
            </div>
          )}
          {step.citations.length > 0 && (
            <div>
              <div className="text-xs text-slate-500 mb-1">CITATIONS</div>
              <div className="space-y-0.5">
                {step.citations.slice(0, 5).map((url, i) => (
                  <div key={i} className="flex items-center gap-1">
                    <Link className="w-3 h-3 text-blue-400 shrink-0" />
                    <a href={url} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-400 hover:underline truncate">
                      {url}
                    </a>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function AgentTrace({ steps }: { steps: AgentStep[] }) {
  const [open, setOpen] = useState(false);
  const totalTokens = steps.reduce((s, t) => s + t.tokens_used, 0);

  return (
    <div className="bg-slate-900/50 border border-slate-700 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-slate-800/40 transition-colors"
      >
        <Brain className="w-5 h-5 text-purple-400" />
        <span className="font-semibold text-white">Agent Trace</span>
        <span className="text-xs text-slate-500">{steps.length} steps · {totalTokens.toLocaleString()} tokens</span>
        <span className="ml-auto">{open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}</span>
      </button>
      {open && (
        <div className="px-5 pb-5 space-y-2">
          {steps.map((step, i) => (
            <StepRow key={i} step={step} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}

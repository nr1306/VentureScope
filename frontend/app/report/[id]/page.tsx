"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import { getReport, ReportStatusResponse, SectionReport } from "@/lib/api";
import { downloadJSON, downloadDOCX, downloadPDF } from "@/lib/download";
import { AgentTrace } from "./AgentTrace";
import { GuardrailPanel } from "./GuardrailBadge";
import { EvalScore } from "./EvalScore";
import {
  TrendingUp, DollarSign, Swords, AlertTriangle,
  CheckCircle, XCircle, Clock, Loader2, Link, Eye,
  Download, FileJson, FileText, File, ChevronDown as ChevDown
} from "lucide-react";

const SECTION_META: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
  market: { icon: <TrendingUp className="w-4 h-4" />, label: "Market Analysis", color: "border-blue-700" },
  financial: { icon: <DollarSign className="w-4 h-4" />, label: "Financial Analysis", color: "border-purple-700" },
  competitor: { icon: <Swords className="w-4 h-4" />, label: "Competitive Analysis", color: "border-cyan-700" },
  risk: { icon: <AlertTriangle className="w-4 h-4" />, label: "Risk Analysis", color: "border-orange-700" },
};

const RISK_COLORS: Record<string, string> = {
  low: "bg-green-900/40 text-green-300 border border-green-700",
  medium: "bg-yellow-900/40 text-yellow-300 border border-yellow-700",
  high: "bg-red-900/40 text-red-300 border border-red-700",
};

const RECOMMENDATION_STYLES: Record<string, string> = {
  invest: "bg-green-900/30 border-green-600 text-green-300",
  monitor: "bg-yellow-900/30 border-yellow-600 text-yellow-300",
  pass: "bg-red-900/30 border-red-600 text-red-300",
};

function Prose({ content }: { content: string }) {
  return (
    <ReactMarkdown
      components={{
        p: ({ children }) => <p className="text-sm text-slate-300 leading-relaxed mb-2 last:mb-0">{children}</p>,
        strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
        em: ({ children }) => <em className="italic text-slate-200">{children}</em>,
        ul: ({ children }) => <ul className="space-y-1 mb-2">{children}</ul>,
        ol: ({ children }) => <ol className="space-y-1 mb-2 list-decimal list-inside">{children}</ol>,
        li: ({ children }) => (
          <li className="flex gap-2 text-sm text-slate-300">
            <span className="text-slate-500 mt-0.5 shrink-0">▸</span>
            <span>{children}</span>
          </li>
        ),
        h2: ({ children }) => <h2 className="text-sm font-bold text-white mt-3 mb-1">{children}</h2>,
        h3: ({ children }) => <h3 className="text-sm font-semibold text-slate-200 mt-2 mb-1">{children}</h3>,
        a: ({ href, children }) => (
          <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">{children}</a>
        ),
        code: ({ children }) => <code className="text-xs bg-slate-800 px-1 rounded">{children}</code>,
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

function DownloadDropdown({ report }: { report: import("@/lib/api").DueDiligenceReport }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  async function handle(fmt: "json" | "docx" | "pdf") {
    setOpen(false); setBusy(fmt);
    try {
      if (fmt === "json") downloadJSON(report);
      else if (fmt === "docx") await downloadDOCX(report);
      else await downloadPDF(report);
    } finally { setBusy(null); }
  }

  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen(v => !v)}
        className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-600 text-slate-200 text-sm font-medium rounded-xl transition-colors">
        {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
        Export <ChevDown className="w-3.5 h-3.5 text-slate-400" />
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-44 bg-slate-800 border border-slate-700 rounded-xl shadow-xl overflow-hidden z-20">
          {([["json", "JSON", "yellow", "raw data"], ["docx", "Word (.docx)", "blue", "editable"], ["pdf", "PDF", "red", "print-ready"]] as const).map(([fmt, label, color, hint]) => (
            <button key={fmt} onClick={() => handle(fmt)}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-slate-300 hover:bg-slate-700 hover:text-white transition-colors">
              {fmt === "json" ? <FileJson className={`w-4 h-4 text-${color}-400`} /> : fmt === "docx" ? <FileText className={`w-4 h-4 text-${color}-400`} /> : <File className={`w-4 h-4 text-${color}-400`} />}
              {label} <span className="ml-auto text-xs text-slate-500">{hint}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function SectionCard({ section }: { section: SectionReport }) {
  const [open, setOpen] = useState(true);
  const meta = SECTION_META[section.section];
  const confidence = Math.round(section.confidence * 100);

  return (
    <div className={`bg-slate-900/50 border ${meta.color} rounded-xl overflow-hidden`}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-slate-800/30 transition-colors"
      >
        <span className="text-slate-300">{meta.icon}</span>
        <span className="font-semibold text-white">{meta.label}</span>
        <span className={`text-xs px-2 py-0.5 rounded-full ${RISK_COLORS[section.risk_level]}`}>
          {section.risk_level} risk
        </span>
        {section.needs_review && (
          <span className="text-xs bg-red-900/40 text-red-300 border border-red-700 px-2 py-0.5 rounded-full flex items-center gap-1">
            <Eye className="w-3 h-3" /> Needs Review
          </span>
        )}
        <span className="text-xs text-slate-500 ml-auto">{confidence}% confidence</span>
      </button>

      {open && (
        <div className="px-5 pb-5 space-y-4">
          {/* Confidence bar */}
          <div className="h-1 bg-slate-700 rounded-full">
            <div
              className={`h-full rounded-full ${confidence >= 70 ? "bg-green-500" : confidence >= 40 ? "bg-yellow-500" : "bg-red-500"}`}
              style={{ width: `${confidence}%` }}
            />
          </div>

          {/* Summary */}
          <Prose content={section.summary} />

          {/* Key findings */}
          {section.key_findings.length > 0 && (
            <div>
              <div className="text-xs text-slate-500 mb-2">KEY FINDINGS</div>
              <ul className="space-y-1">
                {section.key_findings.map((f, i) => (
                  <li key={i} className="flex gap-2 text-sm text-slate-300">
                    <span className="text-slate-500 mt-0.5 shrink-0">•</span>
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Citations */}
          {section.citations.length > 0 && (
            <div>
              <div className="text-xs text-slate-500 mb-2">CITATIONS ({section.citations.length})</div>
              <div className="space-y-1">
                {section.citations.slice(0, 4).map((url, i) => (
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

          {/* LLM Judge score */}
          {section.llm_judge_score != null && (
            <div className="text-xs text-slate-500">
              LLM Judge Score: <span className="text-white font-medium">{Math.round(section.llm_judge_score * 100)}%</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<ReportStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [polling, setPolling] = useState(true);

  const fetchReport = useCallback(async () => {
    try {
      setLoadError("");
      const res = await getReport(id);
      setData(res);
      setLoading(false);
      if (res.status === "completed" || res.status === "failed") {
        setPolling(false);
      }
    } catch (err: unknown) {
      setLoading(false);
      setLoadError(err instanceof Error ? err.message : "Failed to load report.");
      setPolling(false);
    }
  }, [id]);

  useEffect(() => {
    void fetchReport();
  }, [fetchReport]);

  useEffect(() => {
    if (!polling) return;
    const interval = setInterval(fetchReport, 3000);
    return () => clearInterval(interval);
  }, [polling, fetchReport]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
      </div>
    );
  }

  if (loadError && !data) {
    return (
      <div className="max-w-xl mx-auto py-24">
        <div className="p-4 bg-red-900/20 border border-red-700 rounded-xl text-red-300 text-sm">
          {loadError}
        </div>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const { report, status, company_name, error } = data;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">{company_name}</h1>
          <div className="flex items-center gap-2 mt-1">
            {status === "running" && <Loader2 className="w-4 h-4 animate-spin text-blue-400" />}
            {status === "completed" && <CheckCircle className="w-4 h-4 text-green-400" />}
            {status === "failed" && <XCircle className="w-4 h-4 text-red-400" />}
            {status === "pending" && <Clock className="w-4 h-4 text-slate-400" />}
            <span className="text-sm text-slate-400 capitalize">
              {status === "running" ? "Agents are working..." : status}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {report && status === "completed" && <DownloadDropdown report={report} />}
          {report?.overall_recommendation && (
            <div className={`px-4 py-2 rounded-xl border text-lg font-bold ${RECOMMENDATION_STYLES[report.overall_recommendation]}`}>
              {report.overall_recommendation.toUpperCase()}
              {report.overall_confidence != null && (
                <div className="text-xs font-normal text-center mt-0.5">
                  {Math.round(report.overall_confidence * 100)}% confidence
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Running state skeleton */}
      {status === "running" && !report && (
        <div className="space-y-3">
          {["market", "financial", "competitor", "risk"].map((s) => (
            <div key={s} className="h-20 bg-slate-800/50 border border-slate-700 rounded-xl animate-pulse" />
          ))}
        </div>
      )}

      {/* Error */}
      {loadError && data && (
        <div className="p-4 bg-red-900/20 border border-red-700 rounded-xl text-red-300 text-sm">
          {loadError}
        </div>
      )}

      {status === "failed" && (
        <div className="p-4 bg-red-900/20 border border-red-700 rounded-xl text-red-300 text-sm">
          {error || "Analysis failed. Please try again."}
        </div>
      )}

      {/* Report sections */}
      {report && (
        <>
          <div className="space-y-4">
            {report.sections.map((s: SectionReport) => (
              <SectionCard key={s.section} section={s} />
            ))}
          </div>

          {/* Bottom panels */}
          <GuardrailPanel sections={report.sections} />
          <EvalScore report={report} />
          {report.agent_trace.length > 0 && <AgentTrace steps={report.agent_trace} />}

          {/* Langfuse link */}
          {report.langfuse_trace_id && (
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <Link className="w-4 h-4" />
              <span>Langfuse Trace:</span>
              <span className="font-mono text-xs text-blue-400">{report.langfuse_trace_id}</span>
            </div>
          )}
        </>
      )}
    </div>
  );
}

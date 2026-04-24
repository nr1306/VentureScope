"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import ReactMarkdown from "react-markdown";
import {
  startAnalysis, getReport, listReports,
  ReportStatusResponse, SectionReport, DueDiligenceReport,
} from "@/lib/api";
import { downloadJSON, downloadDOCX, downloadPDF } from "@/lib/download";
import { deleteReport } from "@/lib/api";
import {
  Search, TrendingUp, DollarSign, Swords, AlertTriangle,
  Loader2, CheckCircle, XCircle, Clock, AlertCircle,
  Link, ChevronDown, ChevronRight, Eye, ArrowRight, Sparkles,
  Download, FileJson, FileText, File, Trash2, History
} from "lucide-react";

// ─── Agent metadata ───────────────────────────────────────────────────────────
const AGENTS = [
  {
    key: "market",
    label: "Market Agent",
    icon: TrendingUp,
    accent: "from-blue-600/20 to-blue-900/10 border-blue-700/50",
    iconColor: "text-blue-400",
    badge: "bg-blue-900/40 text-blue-300 border-blue-700",
    desc: "TAM/SAM/SOM · growth trends · tailwinds",
  },
  {
    key: "financial",
    label: "Financial Agent",
    icon: DollarSign,
    accent: "from-purple-600/20 to-purple-900/10 border-purple-700/50",
    iconColor: "text-purple-400",
    badge: "bg-purple-900/40 text-purple-300 border-purple-700",
    desc: "Funding · revenue signals · valuation",
  },
  {
    key: "competitor",
    label: "Competitor Agent",
    icon: Swords,
    accent: "from-cyan-600/20 to-cyan-900/10 border-cyan-700/50",
    iconColor: "text-cyan-400",
    badge: "bg-cyan-900/40 text-cyan-300 border-cyan-700",
    desc: "Landscape · moat · positioning",
  },
  {
    key: "risk",
    label: "Risk Agent",
    icon: AlertTriangle,
    accent: "from-orange-600/20 to-orange-900/10 border-orange-700/50",
    iconColor: "text-orange-400",
    badge: "bg-orange-900/40 text-orange-300 border-orange-700",
    desc: "Regulatory · operational · market risk",
  },
] as const;

type AgentKey = "market" | "financial" | "competitor" | "risk";

const RISK_COLORS: Record<string, string> = {
  low: "bg-green-900/40 text-green-300 border border-green-700",
  medium: "bg-yellow-900/40 text-yellow-300 border border-yellow-700",
  high: "bg-red-900/40 text-red-300 border border-red-700",
};

const RECOMMENDATION_STYLES: Record<string, { style: string; label: string }> = {
  invest: { style: "bg-green-900/30 border-green-500 text-green-300", label: "INVEST" },
  monitor: { style: "bg-yellow-900/30 border-yellow-500 text-yellow-300", label: "MONITOR" },
  pass: { style: "bg-red-900/30 border-red-500 text-red-300", label: "PASS" },
};

// ─── Markdown prose renderer ─────────────────────────────────────────────────
function Prose({ content }: { content: string }) {
  return (
    <ReactMarkdown
      components={{
        p: ({ children }) => <p className="text-sm text-slate-300 leading-relaxed mb-3 last:mb-0">{children}</p>,
        strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
        em: ({ children }) => <em className="italic text-slate-200">{children}</em>,
        ul: ({ children }) => <ul className="space-y-1.5 mb-3">{children}</ul>,
        ol: ({ children }) => <ol className="space-y-1.5 mb-3 list-decimal list-inside">{children}</ol>,
        li: ({ children }) => (
          <li className="flex gap-2 text-sm text-slate-300">
            <span className="text-slate-500 mt-0.5 shrink-0">▸</span>
            <span>{children}</span>
          </li>
        ),
        h1: ({ children }) => <h1 className="text-base font-bold text-white mt-4 mb-2">{children}</h1>,
        h2: ({ children }) => <h2 className="text-sm font-bold text-white mt-3 mb-1.5">{children}</h2>,
        h3: ({ children }) => <h3 className="text-sm font-semibold text-slate-200 mt-2 mb-1">{children}</h3>,
        a: ({ href, children }) => (
          <a href={href} target="_blank" rel="noopener noreferrer"
            className="text-blue-400 hover:underline">{children}</a>
        ),
        code: ({ children }) => <code className="text-xs bg-slate-800 text-slate-300 px-1 py-0.5 rounded">{children}</code>,
        blockquote: ({ children }) => (
          <blockquote className="border-l-2 border-slate-600 pl-3 text-slate-400 italic my-2">{children}</blockquote>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

// ─── Download button ──────────────────────────────────────────────────────────
function DownloadButton({ report }: { report: DueDiligenceReport }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  async function handle(format: "json" | "docx" | "pdf") {
    setOpen(false);
    setBusy(format);
    try {
      if (format === "json") downloadJSON(report);
      else if (format === "docx") await downloadDOCX(report);
      else await downloadPDF(report);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-600 text-slate-200 text-sm font-medium rounded-xl transition-colors"
      >
        {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
        Export
        <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-44 bg-slate-800 border border-slate-700 rounded-xl shadow-xl overflow-hidden z-20">
          <button
            onClick={() => handle("json")}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
          >
            <FileJson className="w-4 h-4 text-yellow-400" /> JSON
            <span className="ml-auto text-xs text-slate-500">raw data</span>
          </button>
          <button
            onClick={() => handle("docx")}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
          >
            <FileText className="w-4 h-4 text-blue-400" /> Word (.docx)
            <span className="ml-auto text-xs text-slate-500">editable</span>
          </button>
          <button
            onClick={() => handle("pdf")}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
          >
            <File className="w-4 h-4 text-red-400" /> PDF
            <span className="ml-auto text-xs text-slate-500">print-ready</span>
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Section detail panel ────────────────────────────────────────────────────
function SectionPanel({ section }: { section: SectionReport }) {
  const [citationsOpen, setCitationsOpen] = useState(false);
  const confidence = Math.round(section.confidence * 100);

  return (
    <div className="space-y-5">
      {/* Confidence bar */}
      <div>
        <div className="flex justify-between text-xs text-slate-400 mb-1.5">
          <span>Confidence</span>
          <span className={confidence >= 70 ? "text-green-400" : confidence >= 40 ? "text-yellow-400" : "text-red-400"}>
            {confidence}%
          </span>
        </div>
        <div className="h-1.5 bg-slate-700 rounded-full">
          <div
            className={`h-full rounded-full transition-all duration-700 ${confidence >= 70 ? "bg-green-500" : confidence >= 40 ? "bg-yellow-500" : "bg-red-500"}`}
            style={{ width: `${confidence}%` }}
          />
        </div>
      </div>

      {/* Risk level + review flag */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className={`text-xs px-2.5 py-1 rounded-full border ${RISK_COLORS[section.risk_level]}`}>
          {section.risk_level} risk
        </span>
        {section.needs_review && (
          <span className="text-xs bg-red-900/40 text-red-300 border border-red-700 px-2.5 py-1 rounded-full flex items-center gap-1">
            <Eye className="w-3 h-3" /> Needs Review
          </span>
        )}
        {section.llm_judge_score != null && (
          <span className="text-xs bg-slate-800 text-slate-300 border border-slate-600 px-2.5 py-1 rounded-full ml-auto">
            Judge score: {Math.round(section.llm_judge_score * 100)}%
          </span>
        )}
      </div>

      {/* Summary rendered as prose (no asterisks) */}
      <div>
        <div className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-3">Summary</div>
        <Prose content={section.summary} />
      </div>

      {/* Key findings */}
      {section.key_findings.length > 0 && (
        <div>
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">
            Key Findings
          </div>
          <ul className="space-y-2">
            {section.key_findings.map((f, i) => (
              <li key={i} className="flex gap-2 text-sm text-slate-300">
                <span className="text-slate-500 mt-0.5 shrink-0">▸</span>
                <span><Prose content={f} /></span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Citations collapsible */}
      {section.citations.length > 0 && (
        <div className="border border-slate-700 rounded-lg overflow-hidden">
          <button
            onClick={() => setCitationsOpen(!citationsOpen)}
            className="w-full flex items-center gap-2 px-4 py-2.5 bg-slate-800/50 text-left hover:bg-slate-700/40 transition-colors text-xs text-slate-400"
          >
            <Link className="w-3.5 h-3.5 text-blue-400" />
            <span>{section.citations.length} citations</span>
            <span className="ml-auto">{citationsOpen ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}</span>
          </button>
          {citationsOpen && (
            <div className="px-4 pb-3 pt-1 space-y-1 bg-slate-900/30">
              {section.citations.map((url, i) => (
                <div key={i} className="flex items-center gap-1.5">
                  <Link className="w-3 h-3 text-blue-400 shrink-0" />
                  <a href={url} target="_blank" rel="noopener noreferrer"
                    className="text-xs text-blue-400 hover:underline truncate">
                    {url}
                  </a>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Agent card ───────────────────────────────────────────────────────────────
function AgentCard({
  agent, status, section, isActive, onClick,
}: {
  agent: typeof AGENTS[number];
  status: "idle" | "working" | "done" | "failed";
  section?: SectionReport;
  isActive: boolean;
  onClick?: () => void;
}) {
  const Icon = agent.icon;
  const confidence = section ? Math.round(section.confidence * 100) : null;

  return (
    <button
      onClick={onClick}
      disabled={status === "idle" || status === "working"}
      className={`
        relative w-full text-left rounded-2xl border bg-gradient-to-br p-5 transition-all duration-200
        ${agent.accent}
        ${status === "done" ? "cursor-pointer hover:brightness-110 hover:shadow-lg hover:shadow-black/20" : "cursor-default"}
        ${isActive ? "ring-2 ring-white/20 brightness-110" : ""}
      `}
    >
      {/* Status indicator dot */}
      <div className="absolute top-3 right-3">
        {status === "idle" && <div className="w-2 h-2 rounded-full bg-slate-600" />}
        {status === "working" && (
          <div className="w-2 h-2 rounded-full bg-blue-400 animate-pulse shadow-[0_0_6px_2px_rgba(96,165,250,0.5)]" />
        )}
        {status === "done" && <CheckCircle className="w-4 h-4 text-green-400" />}
        {status === "failed" && <XCircle className="w-4 h-4 text-red-400" />}
      </div>

      {/* Icon */}
      <div className={`mb-3 ${agent.iconColor}`}>
        {status === "working"
          ? <Loader2 className="w-7 h-7 animate-spin" />
          : <Icon className="w-7 h-7" />
        }
      </div>

      {/* Label */}
      <div className="font-semibold text-white text-sm mb-1">{agent.label}</div>
      <div className="text-xs text-slate-400">{agent.desc}</div>

      {/* Confidence when done */}
      {status === "done" && confidence !== null && (
        <div className="mt-3 flex items-center justify-between">
          <div className="h-1 flex-1 bg-slate-700 rounded-full mr-3">
            <div
              className={`h-full rounded-full ${confidence >= 70 ? "bg-green-500" : confidence >= 40 ? "bg-yellow-500" : "bg-red-500"}`}
              style={{ width: `${confidence}%` }}
            />
          </div>
          <span className="text-xs text-slate-400 shrink-0">{confidence}%</span>
        </div>
      )}

      {/* "View" hint when active and done */}
      {status === "done" && isActive && (
        <div className="mt-2 text-xs text-slate-400 flex items-center gap-1">
          <span>Viewing</span><ArrowRight className="w-3 h-3" />
        </div>
      )}
      {status === "done" && !isActive && (
        <div className="mt-2 text-xs text-slate-500">Click to view</div>
      )}
    </button>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
type Phase = "idle" | "analyzing" | "completed" | "failed";

export default function HomePage() {
  const [company, setCompany] = useState("");
  const [inputError, setInputError] = useState("");
  const [actionError, setActionError] = useState("");
  const [historyError, setHistoryError] = useState("");
  const [historyLoading, setHistoryLoading] = useState(true);
  const [phase, setPhase] = useState<Phase>("idle");
  const [reportId, setReportId] = useState<string | null>(null);
  const [reportData, setReportData] = useState<ReportStatusResponse | null>(null);
  const [activeTab, setActiveTab] = useState<AgentKey>("market");
  const [allReports, setAllReports] = useState<ReportStatusResponse[]>([]);
  const [showBanner, setShowBanner] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [clearingAll, setClearingAll] = useState(false);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const resultRef = useRef<HTMLDivElement>(null);

  const refreshReports = useCallback(async () => {
    setHistoryLoading(true);
    setHistoryError("");
    try {
      setAllReports(await listReports());
    } catch (err: unknown) {
      setHistoryError(err instanceof Error ? err.message : "Failed to load analysis history.");
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => { void refreshReports(); }, [refreshReports]);

  const completedReports = allReports.filter((r) => r.status === "completed");
  const failedReports = allReports.filter((r) => r.status === "failed");

  async function handleDelete(e: React.MouseEvent, id: string) {
    e.preventDefault();
    e.stopPropagation();
    setDeletingId(id);
    setActionError("");
    try {
      await deleteReport(id);
      setAllReports((prev) => prev.filter((r) => r.report_id !== id));
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to delete report.");
    } finally {
      setDeletingId(null);
    }
  }

  async function handleClearAll(section: "completed" | "failed") {
    const ids = (section === "completed" ? completedReports : failedReports).map((r) => r.report_id);
    setClearingAll(true);
    setActionError("");
    try {
      await Promise.all(ids.map((id) => deleteReport(id)));
      setAllReports((prev) => prev.filter((r) => !ids.includes(r.report_id)));
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to clear report history.");
    } finally {
      setClearingAll(false);
    }
  }

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  const pollReport = useCallback(async (id: string) => {
    try {
      const res = await getReport(id);
      setInputError("");
      setReportData(res);
      if (res.status === "completed") {
        stopPolling();
        setPhase("completed");
        setShowBanner(true);
        void refreshReports();
        // Scroll to result
        setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 100);
      } else if (res.status === "failed") {
        stopPolling();
        setPhase("failed");
      }
    } catch (err: unknown) {
      setInputError(
        err instanceof Error
          ? err.message
          : "Unable to refresh analysis status right now.",
      );
    }
  }, [stopPolling, refreshReports]);

  useEffect(() => () => stopPolling(), [stopPolling]);

  async function handleAnalyze(e: React.FormEvent) {
    e.preventDefault();
    if (!company.trim()) return;
    stopPolling();
    setInputError("");
    setActionError("");
    setPhase("analyzing");
    setReportData(null);
    setShowBanner(false);
    try {
      const res = await startAnalysis(company.trim());
      setReportId(res.report_id);
      pollingRef.current = setInterval(() => pollReport(res.report_id), 3000);
      void pollReport(res.report_id);
    } catch (err: unknown) {
      setInputError(err instanceof Error ? err.message : "Something went wrong");
      setPhase("idle");
    }
  }

  function getAgentStatus(key: AgentKey): "idle" | "working" | "done" | "failed" {
    if (phase === "idle") return "idle";
    if (phase === "completed" || phase === "failed") {
      const section = reportData?.report?.sections.find((s) => s.section === key);
      return section ? "done" : phase === "failed" ? "failed" : "working";
    }
    return "working";
  }

  function getSectionData(key: AgentKey): SectionReport | undefined {
    return reportData?.report?.sections.find((s) => s.section === key);
  }

  const rec = reportData?.report?.overall_recommendation;
  const recStyle = rec ? RECOMMENDATION_STYLES[rec] : null;

  return (
    <div className="space-y-10 pb-16">

      {/* ── Hero ─────────────────────────────────────────────────────── */}
      <div className="text-center space-y-4 pt-6">
        <div className="inline-flex items-center gap-2 bg-slate-800/60 border border-slate-700 rounded-full px-4 py-1.5 text-xs text-slate-400 mb-2">
          <Sparkles className="w-3.5 h-3.5 text-blue-400" />
          Multi-agent AI · OpenAI gpt-4o-mini · RAG + pgvector
        </div>
        <h1 className="text-5xl font-bold text-white tracking-tight">
          Venture<span className="text-blue-400">Scope</span>
        </h1>
        <p className="text-slate-400 max-w-lg mx-auto text-base leading-relaxed">
          Enter a company name. Four specialized AI agents research the market, financials,
          competitors, and risks — then synthesize a structured due-diligence report.
        </p>
      </div>

      {/* ── Search bar ───────────────────────────────────────────────── */}
      <form onSubmit={handleAnalyze} className="max-w-lg mx-auto">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-3.5 w-4 h-4 text-slate-500" />
            <input
              type="text"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder="e.g. Stripe, Notion, Linear..."
              disabled={phase === "analyzing"}
              className="w-full pl-10 pr-4 py-3 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:opacity-50 transition-colors"
            />
          </div>
          <button
            type="submit"
            disabled={phase === "analyzing" || !company.trim()}
            className="px-5 py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium rounded-xl transition-colors flex items-center gap-2 shrink-0"
          >
            {phase === "analyzing"
              ? <><Loader2 className="w-4 h-4 animate-spin" /> Analyzing…</>
              : <><Search className="w-4 h-4" /> Analyze</>}
          </button>
        </div>
        {inputError && (
          <div className="mt-2 flex items-center gap-2 text-red-400 text-sm">
            <AlertCircle className="w-4 h-4" /> {inputError}
          </div>
        )}
      </form>

      {/* ── Completion banner ─────────────────────────────────────────── */}
      {showBanner && reportData && (
        <div className="max-w-lg mx-auto">
          <div className="flex items-center gap-3 px-4 py-3 bg-green-900/20 border border-green-700/60 rounded-xl text-sm text-green-300">
            <CheckCircle className="w-4 h-4 shrink-0" />
            <span>
              Analysis complete for <strong>{reportData.company_name}</strong> — select an agent card below to explore results.
            </span>
            <button onClick={() => setShowBanner(false)} className="ml-auto text-green-600 hover:text-green-400 text-lg leading-none">×</button>
          </div>
        </div>
      )}

      {/* ── Failed banner ─────────────────────────────────────────────── */}
      {phase === "failed" && (
        <div className="max-w-lg mx-auto">
          <div className="flex items-center gap-3 px-4 py-3 bg-red-900/20 border border-red-700/60 rounded-xl text-sm text-red-300">
            <XCircle className="w-4 h-4 shrink-0" />
            <span>{reportData?.error || "Analysis failed. Please try again."}</span>
          </div>
        </div>
      )}

      {/* ── Agent cards ───────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto">
        {AGENTS.map((agent) => {
          const status = getAgentStatus(agent.key);
          return (
            <AgentCard
              key={agent.key}
              agent={agent}
              status={status}
              section={getSectionData(agent.key)}
              isActive={phase === "completed" && activeTab === agent.key}
              onClick={phase === "completed" ? () => setActiveTab(agent.key) : undefined}
            />
          );
        })}
      </div>

      {/* ── Analysis progress label ───────────────────────────────────── */}
      {phase === "analyzing" && (
        <div className="text-center text-sm text-slate-400 flex items-center justify-center gap-2 -mt-4">
          <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
          Agents are working on <span className="text-white font-medium">{company}</span>…
        </div>
      )}

      {/* ── Result area ───────────────────────────────────────────────── */}
      {phase === "completed" && reportData?.report && (
        <div ref={resultRef} className="max-w-4xl mx-auto space-y-6">

          {/* Recommendation header */}
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-xl font-bold text-white">{reportData.company_name}</h2>
              <p className="text-sm text-slate-400 mt-0.5">
                Completed {reportData.completed_at ? new Date(reportData.completed_at).toLocaleString() : ""}
              </p>
            </div>
            <div className="flex items-center gap-3 shrink-0">
              <DownloadButton report={reportData.report} />
              {rec && recStyle && (
                <div className={`px-5 py-2.5 rounded-xl border font-bold text-lg ${recStyle.style}`}>
                  {recStyle.label}
                  {reportData.report.overall_confidence != null && (
                    <div className="text-xs font-normal text-center mt-0.5 opacity-80">
                      {Math.round(reportData.report.overall_confidence * 100)}% confidence
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Tab navigation */}
          <div className="flex gap-1 p-1 bg-slate-800/60 border border-slate-700 rounded-xl w-fit">
            {AGENTS.map((agent) => {
              const Icon = agent.icon;
              const section = getSectionData(agent.key);
              const isActive = activeTab === agent.key;
              return (
                <button
                  key={agent.key}
                  onClick={() => setActiveTab(agent.key)}
                  className={`
                    flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all
                    ${isActive
                      ? "bg-slate-700 text-white shadow-sm"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-700/50"
                    }
                  `}
                >
                  <Icon className={`w-4 h-4 ${isActive ? agent.iconColor : ""}`} />
                  <span className="hidden sm:inline">{agent.label.replace(" Agent", "")}</span>
                  {section?.risk_level && (
                    <span className={`hidden md:inline text-xs px-1.5 py-0.5 rounded border ${RISK_COLORS[section.risk_level]}`}>
                      {section.risk_level}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Active section content */}
          {(() => {
            const section = getSectionData(activeTab);
            const agentMeta = AGENTS.find((a) => a.key === activeTab)!;
            const Icon = agentMeta.icon;
            return section ? (
              <div className={`bg-slate-900/50 border rounded-2xl p-6 bg-gradient-to-br ${agentMeta.accent}`}>
                <div className="flex items-center gap-3 mb-6">
                  <div className={`p-2 rounded-lg bg-slate-800/60 ${agentMeta.iconColor}`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <h3 className="font-semibold text-white text-lg">
                    {agentMeta.label.replace(" Agent", " Analysis")}
                  </h3>
                </div>
                <SectionPanel section={section} />
              </div>
            ) : null;
          })()}
        </div>
      )}

      {/* ── Feature pills (only when idle) ───────────────────────────── */}
      {phase === "idle" && (
        <div className="flex flex-wrap justify-center gap-2">
          {["RAG + pgvector", "Input Guardrails", "Output Guardrails", "LLM-as-Judge Evals", "Langfuse Tracing", "Structured Outputs"].map((f) => (
            <span key={f} className="text-xs bg-slate-800/70 text-slate-500 border border-slate-700/60 px-3 py-1 rounded-full">
              {f}
            </span>
          ))}
        </div>
      )}

      {phase === "idle" && actionError && (
        <div className="max-w-lg mx-auto">
          <div className="flex items-center gap-3 px-4 py-3 bg-red-900/20 border border-red-700/60 rounded-xl text-sm text-red-300">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{actionError}</span>
          </div>
        </div>
      )}

      {phase === "idle" && historyLoading && (
        <div className="max-w-lg mx-auto flex items-center justify-center gap-3 px-4 py-3 bg-slate-900/40 border border-slate-800 rounded-xl text-sm text-slate-400">
          <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
          <span>Loading previous analyses…</span>
        </div>
      )}

      {phase === "idle" && historyError && !historyLoading && (
        <div className="max-w-lg mx-auto">
          <div className="flex items-center gap-3 px-4 py-3 bg-red-900/20 border border-red-700/60 rounded-xl text-sm text-red-300">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{historyError}</span>
          </div>
        </div>
      )}

      {/* ── History ─────────────────────────────────────────────────────── */}
      {!historyLoading && (completedReports.length > 0 || failedReports.length > 0) && phase === "idle" && (
        <div className="max-w-4xl mx-auto space-y-6">

          {/* Completed reports */}
          {completedReports.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <History className="w-4 h-4 text-slate-400" />
                  <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
                    Analysis History
                  </h2>
                  <span className="text-xs bg-slate-800 border border-slate-700 text-slate-500 px-2 py-0.5 rounded-full">
                    {completedReports.length}
                  </span>
                </div>
                <button
                  onClick={() => handleClearAll("completed")}
                  disabled={clearingAll}
                  className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-red-400 transition-colors disabled:opacity-40"
                >
                  {clearingAll ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                  Clear all
                </button>
              </div>

              <div className="space-y-2">
                {completedReports.map((r) => {
                  const rec = r.report?.overall_recommendation;
                  return (
                    <div key={r.report_id} className="group relative">
                      <a
                        href={`/report/${r.report_id}`}
                        className="flex items-center justify-between px-4 py-3.5 bg-slate-800/40 border border-slate-700/60 rounded-xl hover:border-slate-500 hover:bg-slate-800/70 transition-all pr-12"
                      >
                        <div className="flex items-center gap-3">
                          <CheckCircle className="w-4 h-4 text-green-400 shrink-0" />
                          <div>
                            <div className="font-medium text-white text-sm">{r.company_name}</div>
                            <div className="text-xs text-slate-500 mt-0.5">
                              {r.completed_at
                                ? new Date(r.completed_at).toLocaleString()
                                : new Date(r.created_at).toLocaleString()}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          {rec && (
                            <span className={`text-xs px-2.5 py-1 rounded-lg border font-medium ${RECOMMENDATION_STYLES[rec]?.style}`}>
                              {RECOMMENDATION_STYLES[rec]?.label}
                            </span>
                          )}
                          <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-slate-300 transition-colors" />
                        </div>
                      </a>

                      {/* Delete button — absolute so it doesn't break the link layout */}
                      <button
                        onClick={(e) => handleDelete(e, r.report_id)}
                        disabled={deletingId === r.report_id}
                        className="absolute right-3 top-1/2 -translate-y-1/2 w-7 h-7 flex items-center justify-center rounded-lg
                          opacity-0 group-hover:opacity-100 transition-all
                          text-slate-500 hover:text-red-400 hover:bg-red-900/20"
                        title="Delete report"
                      >
                        {deletingId === r.report_id
                          ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          : <Trash2 className="w-3.5 h-3.5" />
                        }
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Failed reports — separate section */}
          {failedReports.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <XCircle className="w-4 h-4 text-red-400" />
                  <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
                    Failed Analyses
                  </h2>
                  <span className="text-xs bg-red-900/30 border border-red-800/50 text-red-400 px-2 py-0.5 rounded-full">
                    {failedReports.length}
                  </span>
                </div>
                <button
                  onClick={() => handleClearAll("failed")}
                  disabled={clearingAll}
                  className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-red-400 transition-colors disabled:opacity-40"
                >
                  {clearingAll ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                  Clear all
                </button>
              </div>

              <div className="space-y-2">
                {failedReports.map((r) => (
                  <div key={r.report_id} className="group relative">
                    <div className="flex items-center justify-between px-4 py-3.5 bg-red-900/10 border border-red-900/30 rounded-xl pr-12">
                      <div className="flex items-center gap-3">
                        <XCircle className="w-4 h-4 text-red-400 shrink-0" />
                        <div>
                          <div className="font-medium text-white text-sm">{r.company_name}</div>
                          <div className="text-xs text-red-400/70 mt-0.5 truncate max-w-xs">
                            {r.error ?? "Analysis failed"}
                          </div>
                        </div>
                      </div>
                      <div className="text-xs text-slate-500">
                        {new Date(r.created_at).toLocaleString()}
                      </div>
                    </div>

                    <button
                      onClick={(e) => handleDelete(e, r.report_id)}
                      disabled={deletingId === r.report_id}
                      className="absolute right-3 top-1/2 -translate-y-1/2 w-7 h-7 flex items-center justify-center rounded-lg
                        opacity-0 group-hover:opacity-100 transition-all
                        text-slate-500 hover:text-red-400 hover:bg-red-900/20"
                      title="Delete"
                    >
                      {deletingId === r.report_id
                        ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        : <Trash2 className="w-3.5 h-3.5" />
                      }
                    </button>
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

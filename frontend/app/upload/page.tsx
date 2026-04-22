"use client";

import { useState, useRef } from "react";
import { uploadDocument } from "@/lib/api";
import { Upload, FileText, CheckCircle, XCircle, Loader2 } from "lucide-react";

interface UploadResult {
  filename: string;
  chunk_count: number;
  document_id: string;
}

export default function UploadPage() {
  const [company, setCompany] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<"idle" | "uploading" | "success" | "error">("idle");
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file || !company.trim()) return;
    setStatus("uploading");
    setError("");
    try {
      const res = await uploadDocument(company.trim(), file) as UploadResult;
      setResult(res);
      setStatus("success");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setStatus("error");
    }
  }

  return (
    <div className="max-w-xl mx-auto space-y-8 pt-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Upload Documents</h1>
        <p className="text-slate-400 mt-1 text-sm">
          Upload pitch decks, financial statements, or reports for a company.
          The RAG pipeline will chunk and embed them for agent retrieval.
        </p>
      </div>

      <form onSubmit={handleUpload} className="space-y-4">
        <div>
          <label className="text-sm text-slate-400 mb-1 block">Company Name</label>
          <input
            type="text"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            placeholder="e.g. Stripe"
            className="w-full px-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-blue-500"
          />
        </div>

        <div>
          <label className="text-sm text-slate-400 mb-1 block">Document</label>
          <div
            onClick={() => inputRef.current?.click()}
            className="border-2 border-dashed border-slate-700 hover:border-slate-500 rounded-xl p-8 text-center cursor-pointer transition-colors"
          >
            {file ? (
              <div className="flex items-center justify-center gap-2">
                <FileText className="w-5 h-5 text-blue-400" />
                <span className="text-white text-sm">{file.name}</span>
                <span className="text-slate-400 text-xs">({(file.size / 1024).toFixed(1)} KB)</span>
              </div>
            ) : (
              <div>
                <Upload className="w-8 h-8 text-slate-500 mx-auto mb-2" />
                <p className="text-slate-400 text-sm">Click to select a file</p>
                <p className="text-slate-600 text-xs mt-1">PDF, DOCX, TXT, Markdown · Max 50MB</p>
              </div>
            )}
          </div>
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.docx,.txt,.md"
            className="hidden"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
        </div>

        <button
          type="submit"
          disabled={!file || !company.trim() || status === "uploading"}
          className="w-full py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
        >
          {status === "uploading" ? (
            <><Loader2 className="w-4 h-4 animate-spin" /> Ingesting...</>
          ) : (
            <><Upload className="w-4 h-4" /> Upload &amp; Ingest</>
          )}
        </button>
      </form>

      {status === "success" && result && (
        <div className="flex gap-3 p-4 bg-green-900/20 border border-green-700 rounded-xl">
          <CheckCircle className="w-5 h-5 text-green-400 shrink-0" />
          <div>
            <div className="text-white font-medium">{result.filename}</div>
            <div className="text-sm text-slate-400 mt-0.5">
              Ingested <span className="text-white">{result.chunk_count}</span> chunks into pgvector.
              Document ID: <span className="font-mono text-xs text-blue-400">{result.document_id}</span>
            </div>
          </div>
        </div>
      )}

      {status === "error" && (
        <div className="flex gap-3 p-4 bg-red-900/20 border border-red-700 rounded-xl">
          <XCircle className="w-5 h-5 text-red-400 shrink-0" />
          <div className="text-sm text-red-300">{error}</div>
        </div>
      )}

      {/* Pipeline explanation */}
      <div className="border border-slate-800 rounded-xl p-4 space-y-2">
        <div className="text-xs text-slate-500 uppercase tracking-wide">RAG Pipeline</div>
        <div className="flex items-center gap-2 text-sm text-slate-400">
          {["Parse (unstructured)", "Chunk (1000 tok)", "Embed (OpenAI)", "Store (pgvector)"].map((step, i, arr) => (
            <span key={step} className="flex items-center gap-2">
              <span className="text-slate-300">{step}</span>
              {i < arr.length - 1 && <span className="text-slate-600">→</span>}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

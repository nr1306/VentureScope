"use client";

import { useEffect } from "react";
import { AlertTriangle } from "lucide-react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="max-w-xl mx-auto py-24">
      <div className="p-5 bg-red-900/20 border border-red-700 rounded-xl space-y-4">
        <div className="flex items-center gap-3 text-red-300">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <h2 className="text-lg font-semibold text-white">Something went wrong</h2>
        </div>
        <p className="text-sm text-red-200/90">
          {error.message || "An unexpected application error occurred."}
        </p>
        <button
          onClick={reset}
          className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white text-sm font-medium rounded-lg transition-colors"
        >
          Try again
        </button>
      </div>
    </div>
  );
}

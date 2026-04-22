import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/components/ThemeProvider";
import { ThemeToggle } from "@/components/NavClient";

export const metadata: Metadata = {
  title: "VentureScope — AI Due Diligence",
  description: "Multi-agent investment due diligence powered by OpenAI",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#0a0d14] text-slate-200 antialiased transition-colors duration-200">
        <ThemeProvider>
          {/* Subtle radial glow — hidden in light mode via CSS */}
          <div className="fixed inset-0 pointer-events-none">
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-blue-600/5 rounded-full blur-3xl" />
          </div>

          <nav className="relative z-10 border-b border-slate-800/80 px-6 py-4 flex items-center justify-between backdrop-blur-sm bg-[#0a0d14]/80">
            <div className="flex items-center gap-2.5">
              <span className="text-base font-bold text-white tracking-tight">
                Venture<span className="text-blue-400">Scope</span>
              </span>
              <span className="text-xs bg-slate-800 text-slate-500 border border-slate-700 px-2 py-0.5 rounded-full">
                beta
              </span>
            </div>
            <div className="flex items-center gap-5">
              <div className="flex gap-5 text-sm text-slate-500">
                <a href="/" className="hover:text-white transition-colors">Analyze</a>
                <a href="/upload" className="hover:text-white transition-colors">Upload Docs</a>
              </div>
              <ThemeToggle />
            </div>
          </nav>

          <main className="relative z-10 max-w-5xl mx-auto px-6 py-10">{children}</main>
        </ThemeProvider>
      </body>
    </html>
  );
}

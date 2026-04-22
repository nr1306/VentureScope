"use client";

import { useTheme } from "./ThemeProvider";
import { Moon, Sun } from "lucide-react";

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  return (
    <button
      onClick={toggle}
      aria-label="Toggle theme"
      className="flex items-center justify-center w-8 h-8 rounded-lg
        bg-slate-800 border border-slate-700 text-slate-400
        hover:text-white hover:border-slate-500
        dark:bg-slate-800 dark:border-slate-700 dark:text-slate-400 dark:hover:text-white
        light:bg-slate-100 light:border-slate-200 light:text-slate-500 light:hover:text-slate-900
        transition-all"
    >
      {theme === "dark"
        ? <Sun className="w-4 h-4" />
        : <Moon className="w-4 h-4" />
      }
    </button>
  );
}

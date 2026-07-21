/**
 * App.tsx
 * -------
 * Root application component. Owns the single piece of top-level state
 * that decides which "page" is showing (home vs. dashboard) — there's no
 * router in this project (kept the dependency list lean), so navigation
 * is just a state switch with an animated crossfade between the two.
 */

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { BrainCog } from "lucide-react";
import HomePage from "@/pages/HomePage";
import DashboardPage from "@/pages/DashboardPage";
import type { AnalyzeResponse } from "@/api/client";

type View = "home" | "dashboard";

export default function App() {
  const [view, setView] = useState<View>("home");
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);

  const handleAnalysisComplete = (result: AnalyzeResponse) => {
    setAnalysis(result);
    setView("dashboard");
  };

  const handleReset = () => {
    setAnalysis(null);
    setView("home");
  };

  return (
    <div className="relative min-h-screen">
      <div className="aurora-backdrop" aria-hidden="true" />

      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <button
          type="button"
          onClick={handleReset}
          className="flex items-center gap-2 font-display text-lg font-semibold text-white"
        >
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-gradient shadow-glow">
            <BrainCog className="h-5 w-5 text-white" />
          </span>
          AI Resume <span className="gradient-text">Analyzer</span>
        </button>

        <a
          href="https://github.com"
          target="_blank"
          rel="noreferrer"
          className="hidden text-sm text-mist-400 transition-colors hover:text-white sm:block"
        >
          FastAPI + React
        </a>
      </header>

      <main>
        <AnimatePresence mode="wait">
          {view === "home" || !analysis ? (
            <motion.div
              key="home"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.35 }}
            >
              <HomePage onAnalysisComplete={handleAnalysisComplete} />
            </motion.div>
          ) : (
            <motion.div
              key="dashboard"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.4 }}
            >
              <DashboardPage analysis={analysis} onReset={handleReset} />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <footer className="mx-auto max-w-6xl px-6 py-10 text-center text-xs text-mist-500">
        Built with FastAPI, spaCy, sentence-transformers, and React. Runs entirely on your machine.
      </footer>
    </div>
  );
}

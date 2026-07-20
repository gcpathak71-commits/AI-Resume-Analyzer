/**
 * HomePage.tsx
 * ------------
 * Landing page: hero copy, feature highlights, and the upload zone. Owns
 * the actual analyzeResume() API call and its loading/error state, then
 * hands the finished AnalyzeResponse up to App.tsx via onAnalysisComplete
 * so the app can switch to DashboardPage.
 */

import { motion } from "framer-motion";
import { Brain, FileSearch, Gauge, Sparkles, Target } from "lucide-react";
import UploadZone from "@/components/UploadZone";
import type { AnalyzeResponse } from "@/api/client";

interface HomePageProps {
  onAnalysisComplete: (analysis: AnalyzeResponse) => void;
}

const FEATURES = [
  {
    icon: Gauge,
    title: "Weighted ATS Score",
    description: "A 0-100 score broken down across skills, experience, education, and formatting.",
  },
  {
    icon: Brain,
    title: "Semantic Skill Detection",
    description: "spaCy phrase matching plus typo-tolerant fuzzy matching — not just keyword search.",
  },
  {
    icon: Target,
    title: "Smart Job Matching",
    description: "Sentence-embedding similarity ranks roles by real semantic relevance to your resume.",
  },
  {
    icon: FileSearch,
    title: "Skill Gap Analysis",
    description: "See exactly which in-demand skills are missing, ranked by importance.",
  },
];

export default function HomePage({ onAnalysisComplete }: HomePageProps) {
  return (
    <div className="mx-auto flex max-w-4xl flex-col items-center px-6 py-20 text-center">
      <motion.div
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="pill-violet mb-6"
      >
        <Sparkles className="h-3.5 w-3.5" />
        AI-Powered Resume Analysis
      </motion.div>

      <motion.h1
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.1 }}
        className="text-4xl font-bold leading-tight sm:text-5xl"
      >
        Know exactly how your resume{" "}
        <span className="gradient-text">stacks up</span>
      </motion.h1>

      <motion.p
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.2 }}
        className="mt-5 max-w-2xl text-lg text-mist-400"
      >
        Upload your resume and get an ATS-readiness score, a detailed skill gap analysis, and
        semantically-matched job role recommendations — all in seconds.
      </motion.p>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.3 }}
        className="mt-12 w-full max-w-xl"
      >
        <UploadZone onAnalysisComplete={onAnalysisComplete} />
      </motion.div>

      <div className="mt-20 grid w-full grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {FEATURES.map((feature, index) => (
          <motion.div
            key={feature.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 + index * 0.08 }}
            className="glass-card flex flex-col items-start gap-3 p-5 text-left"
          >
            <div className="rounded-xl bg-brand-gradient p-2.5">
              <feature.icon className="h-5 w-5 text-white" />
            </div>
            <h3 className="font-display text-sm font-semibold text-white">{feature.title}</h3>
            <p className="text-sm text-mist-400">{feature.description}</p>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
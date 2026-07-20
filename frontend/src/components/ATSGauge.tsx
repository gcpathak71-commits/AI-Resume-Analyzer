/**
 * ATSGauge.tsx
 * ------------
 * The headline ATS score visualization: a custom animated SVG radial
 * gauge (not a default Recharts/chart-library look) with a count-up
 * number in the center and a small breakdown bar list beneath it.
 *
 * A hand-built SVG arc is used here specifically so the score gauge has
 * a distinctive, on-brand appearance — Recharts is used elsewhere
 * (SkillRadarChart, RoleMatchChart) where its interactivity earns its
 * keep, but a gauge is simple enough that a custom component gives more
 * control over the exact glow/gradient look the design calls for.
 */

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import type { ATSBreakdown } from "@/api/client";

interface ATSGaugeProps {
  score: number;
  breakdown: ATSBreakdown;
}

const RADIUS = 88;
const STROKE_WIDTH = 16;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

const CATEGORY_LABELS: Record<keyof ATSBreakdown, string> = {
  skills: "Skills Match",
  experience: "Experience",
  education: "Education",
  projects: "Projects",
  certifications: "Certifications",
  contact_info: "Contact Info",
  formatting: "Formatting",
};

const CATEGORY_MAX: Record<keyof ATSBreakdown, number> = {
  skills: 35,
  experience: 15,
  education: 10,
  projects: 10,
  certifications: 10,
  contact_info: 5,
  formatting: 15,
};

function scoreColor(score: number): { stroke: string; text: string; glow: string } {
  if (score >= 80) return { stroke: "#4ade80", text: "text-mint-400", glow: "drop-shadow(0 0 14px rgba(74,222,128,0.55))" };
  if (score >= 60) return { stroke: "#22d3ee", text: "text-cyan-300", glow: "drop-shadow(0 0 14px rgba(34,211,238,0.5))" };
  if (score >= 40) return { stroke: "#fb923c", text: "text-ember-400", glow: "drop-shadow(0 0 14px rgba(251,146,60,0.5))" };
  return { stroke: "#fb7185", text: "text-rose-400", glow: "drop-shadow(0 0 14px rgba(251,113,133,0.5))" };
}

function useCountUp(target: number, durationMs = 1400): number {
  const [value, setValue] = useState(0);

  useEffect(() => {
    let animationFrame: number;
    const startTime = performance.now();

    const step = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / durationMs, 1);
      // ease-out-cubic for a natural deceleration into the final number
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(Math.round(eased * target));
      if (progress < 1) {
        animationFrame = requestAnimationFrame(step);
      }
    };

    animationFrame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(animationFrame);
  }, [target, durationMs]);

  return value;
}

export default function ATSGauge({ score, breakdown }: ATSGaugeProps) {
  const displayedScore = useCountUp(score);
  const colors = scoreColor(score);
  const dashOffset = CIRCUMFERENCE * (1 - score / 100);

  const verdict =
    score >= 80 ? "Excellent" : score >= 60 ? "Good" : score >= 40 ? "Needs Work" : "Weak";

  return (
    <div className="glass-card flex flex-col items-center gap-8 p-8">
      <div className="relative flex h-56 w-56 items-center justify-center">
        <svg width="224" height="224" viewBox="0 0 224 224" className="-rotate-90">
          <circle
            cx="112"
            cy="112"
            r={RADIUS}
            fill="none"
            stroke="rgba(255,255,255,0.08)"
            strokeWidth={STROKE_WIDTH}
          />
          <motion.circle
            cx="112"
            cy="112"
            r={RADIUS}
            fill="none"
            stroke={colors.stroke}
            strokeWidth={STROKE_WIDTH}
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            initial={{ strokeDashoffset: CIRCUMFERENCE }}
            animate={{ strokeDashoffset: dashOffset }}
            transition={{ duration: 1.4, ease: [0.16, 1, 0.3, 1] }}
            style={{ filter: colors.glow }}
          />
        </svg>

        <div className="absolute flex flex-col items-center">
          <span className={`font-display text-5xl font-bold ${colors.text}`}>{displayedScore}</span>
          <span className="text-sm text-mist-400">out of 100</span>
          <span className={`pill mt-2 border-current/30 bg-current/10 ${colors.text}`}>{verdict}</span>
        </div>
      </div>

      <div className="w-full space-y-3">
        {(Object.keys(CATEGORY_LABELS) as (keyof ATSBreakdown)[]).map((key) => {
          const value = breakdown[key];
          const max = CATEGORY_MAX[key];
          const percent = Math.min((value / max) * 100, 100);

          return (
            <div key={key}>
              <div className="mb-1 flex items-center justify-between text-xs">
                <span className="text-mist-300">{CATEGORY_LABELS[key]}</span>
                <span className="text-mist-500">
                  {value} / {max}
                </span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/5">
                <motion.div
                  className="h-full rounded-full bg-brand-gradient"
                  initial={{ width: 0 }}
                  animate={{ width: `${percent}%` }}
                  transition={{ duration: 1, ease: "easeOut", delay: 0.15 }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

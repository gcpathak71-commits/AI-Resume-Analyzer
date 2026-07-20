/**
 * StrengthsWeaknesses.tsx
 * -------------------------
 * Human-readable feedback panel: a strengths/weaknesses two-column list
 * plus a "skill gap" chip cloud of missing skills, ranked by importance.
 * The missing-skill chips use a staggered Framer Motion entrance — each
 * chip appears slightly after the last — as one of the app's signature
 * micro-interactions.
 */

import { motion } from "framer-motion";
import { CheckCircle2, TrendingUp, XCircle } from "lucide-react";
import type { MissingSkill } from "@/api/client";

interface StrengthsWeaknessesProps {
  strengths: string[];
  weaknesses: string[];
  missingSkills: MissingSkill[];
}

const chipContainerVariants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.06 },
  },
};

const chipVariants = {
  hidden: { opacity: 0, y: 10, scale: 0.9 },
  visible: { opacity: 1, y: 0, scale: 1 },
};

function weightPillClass(weight: number): string {
  if (weight >= 5) return "pill-rose";
  if (weight >= 4) return "pill-cyan";
  return "pill-muted";
}

export default function StrengthsWeaknesses({ strengths, weaknesses, missingSkills }: StrengthsWeaknessesProps) {
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <div className="glass-card p-6">
        <div className="mb-4 flex items-center gap-2">
          <CheckCircle2 className="h-5 w-5 text-mint-400" />
          <h3 className="text-lg font-semibold">Strengths</h3>
        </div>
        <ul className="space-y-3">
          {strengths.length === 0 && (
            <li className="text-sm text-mist-500">No standout strengths detected yet.</li>
          )}
          {strengths.map((strength, index) => (
            <motion.li
              key={strength}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.06, duration: 0.4 }}
              className="flex items-start gap-2.5 text-sm text-mist-200"
            >
              <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-mint-400" />
              {strength}
            </motion.li>
          ))}
        </ul>
      </div>

      <div className="glass-card p-6">
        <div className="mb-4 flex items-center gap-2">
          <XCircle className="h-5 w-5 text-rose-400" />
          <h3 className="text-lg font-semibold">Areas to Improve</h3>
        </div>
        <ul className="space-y-3">
          {weaknesses.length === 0 && (
            <li className="text-sm text-mist-500">No major issues detected — nice work!</li>
          )}
          {weaknesses.map((weakness, index) => (
            <motion.li
              key={weakness}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.06, duration: 0.4 }}
              className="flex items-start gap-2.5 text-sm text-mist-200"
            >
              <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-rose-400" />
              {weakness}
            </motion.li>
          ))}
        </ul>
      </div>

      <div className="glass-card p-6 lg:col-span-2">
        <div className="mb-4 flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-violet-400" />
          <h3 className="text-lg font-semibold">Skill Gap — Consider Learning</h3>
        </div>

        {missingSkills.length === 0 ? (
          <p className="text-sm text-mist-500">
            Excellent coverage — no significant in-demand skills are missing from this resume.
          </p>
        ) : (
          <motion.div
            variants={chipContainerVariants}
            initial="hidden"
            animate="visible"
            className="flex flex-wrap gap-2"
          >
            {missingSkills.map((skill) => (
              <motion.span
                key={skill.skill}
                variants={chipVariants}
                transition={{ type: "spring", stiffness: 300, damping: 20 }}
                className={weightPillClass(skill.weight)}
              >
                {skill.skill}
              </motion.span>
            ))}
          </motion.div>
        )}
      </div>
    </div>
  );
}

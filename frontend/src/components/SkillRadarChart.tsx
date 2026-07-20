/**
 * SkillRadarChart.tsx
 * --------------------
 * Radar chart showing the candidate's relative strength across skill
 * categories (e.g. Programming Language, AI/ML, Cloud, DevOps). Built
 * with Recharts, restyled to match the app's dark "aurora" palette
 * instead of Recharts' default light theme.
 *
 * Per-category "strength" is the weight-weighted average confidence of
 * detected skills in that category — categories where more, higher-
 * weight, higher-confidence skills were found score closer to 100.
 */

import { useMemo } from "react";
import { motion } from "framer-motion";
import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { DetectedSkill } from "@/api/client";

interface SkillRadarChartProps {
  detectedSkills: DetectedSkill[];
}

const MAX_CATEGORIES = 7;

interface CategoryPoint {
  category: string;
  strength: number;
  skillCount: number;
}

function buildCategoryPoints(skills: DetectedSkill[]): CategoryPoint[] {
  const byCategory = new Map<string, { weightedConfidence: number; totalWeight: number; count: number }>();

  for (const skill of skills) {
    const bucket = byCategory.get(skill.category) ?? { weightedConfidence: 0, totalWeight: 0, count: 0 };
    bucket.weightedConfidence += skill.confidence * skill.weight;
    bucket.totalWeight += skill.weight;
    bucket.count += 1;
    byCategory.set(skill.category, bucket);
  }

  const points: CategoryPoint[] = Array.from(byCategory.entries()).map(([category, bucket]) => ({
    category,
    strength: Math.round((bucket.weightedConfidence / bucket.totalWeight) * 100),
    skillCount: bucket.count,
  }));

  return points.sort((a, b) => b.skillCount - a.skillCount).slice(0, MAX_CATEGORIES);
}

function CustomTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const point: CategoryPoint = payload[0].payload;
  return (
    <div className="glass-card px-4 py-2 text-sm">
      <p className="font-medium text-white">{point.category}</p>
      <p className="text-mist-400">
        {point.skillCount} skill{point.skillCount === 1 ? "" : "s"} · {point.strength}% strength
      </p>
    </div>
  );
}

export default function SkillRadarChart({ detectedSkills }: SkillRadarChartProps) {
  const data = useMemo(() => buildCategoryPoints(detectedSkills), [detectedSkills]);

  return (
    <div className="glass-card p-6">
      <h3 className="mb-1 text-lg font-semibold">Skill Category Strength</h3>
      <p className="mb-4 text-sm text-mist-400">
        How strongly your detected skills cover each technical category
      </p>

      {data.length < 3 ? (
        <div className="flex h-72 flex-col items-center justify-center text-center text-mist-500">
          <p>Not enough distinct skill categories detected yet to render a radar chart.</p>
        </div>
      ) : (
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="h-72 w-full"
        >
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={data} outerRadius="72%">
              <PolarGrid stroke="rgba(255,255,255,0.12)" />
              <PolarAngleAxis
                dataKey="category"
                tick={{ fill: "#c9c6ec", fontSize: 11 }}
              />
              <PolarRadiusAxis
                angle={90}
                domain={[0, 100]}
                tick={{ fill: "#8480a8", fontSize: 10 }}
                axisLine={false}
              />
              <Radar
                name="Strength"
                dataKey="strength"
                stroke="#22d3ee"
                fill="#8b5cf6"
                fillOpacity={0.45}
                strokeWidth={2}
                animationDuration={1200}
              />
              <Tooltip content={<CustomTooltip />} />
            </RadarChart>
          </ResponsiveContainer>
        </motion.div>
      )}
    </div>
  );
}

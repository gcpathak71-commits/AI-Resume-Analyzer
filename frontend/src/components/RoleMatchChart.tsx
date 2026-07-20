/**
 * RoleMatchChart.tsx
 * -------------------
 * Horizontal bar chart ranking every candidate job role by match
 * percentage, built with Recharts. The top match is visually
 * highlighted, and each bar's tooltip breaks the blended score down into
 * its two components (skill overlap vs. semantic embedding similarity)
 * so the "why" behind the ranking isn't a black box.
 */

import { useMemo } from "react";
import { motion } from "framer-motion";
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { RoleMatch } from "@/api/client";

interface RoleMatchChartProps {
  roleMatches: RoleMatch[];
}

const MAX_ROLES_SHOWN = 8;
const TOP_COLOR = "#22d3ee";
const OTHER_COLOR = "#8b5cf6";

function CustomTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const role: RoleMatch = payload[0].payload;
  return (
    <div className="glass-card max-w-xs px-4 py-3 text-sm">
      <p className="font-medium text-white">{role.role_name}</p>
      <div className="mt-2 space-y-1 text-mist-400">
        <p>
          Overall match: <span className="font-semibold text-cyan-300">{role.match_percentage}%</span>
        </p>
        <p>Skill overlap: {role.overlap_score}%</p>
        <p>Semantic similarity: {role.similarity_score}%</p>
        <p>Minimum experience: {role.min_experience_years} yr</p>
      </div>
    </div>
  );
}

export default function RoleMatchChart({ roleMatches }: RoleMatchChartProps) {
  const data = useMemo(() => roleMatches.slice(0, MAX_ROLES_SHOWN), [roleMatches]);
  const chartHeight = Math.max(data.length * 42, 200);

  return (
    <div className="glass-card p-6">
      <h3 className="mb-1 text-lg font-semibold">Job Role Matches</h3>
      <p className="mb-4 text-sm text-mist-400">
        Ranked by a blend of skill overlap and semantic resume similarity
      </p>

      {data.length === 0 ? (
        <div className="flex h-48 items-center justify-center text-center text-mist-500">
          No role matches could be calculated.
        </div>
      ) : (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6 }}
          style={{ height: chartHeight }}
          className="w-full"
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} layout="vertical" margin={{ top: 0, right: 24, bottom: 0, left: 0 }}>
              <XAxis type="number" domain={[0, 100]} hide />
              <YAxis
                type="category"
                dataKey="role_name"
                width={170}
                tick={{ fill: "#e7e5fb", fontSize: 12 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
              <Bar dataKey="match_percentage" radius={[0, 8, 8, 0]} barSize={20} animationDuration={1100}>
                {data.map((role, index) => (
                  <Cell key={role.role_name} fill={index === 0 ? TOP_COLOR : OTHER_COLOR} fillOpacity={index === 0 ? 1 : 0.7} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </motion.div>
      )}

      {data.length > 0 && (
        <div className="mt-4 flex items-center gap-2 text-xs text-mist-500">
          <span className="inline-block h-2 w-2 rounded-full bg-cyan-400" />
          Best match
          <span className="ml-3 inline-block h-2 w-2 rounded-full bg-violet-500" />
          Other roles
        </div>
      )}
    </div>
  );
}

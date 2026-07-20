/**
 * DashboardPage.tsx
 * ------------------
 * The results screen: composes every chart/feedback component into the
 * full analysis dashboard. Receives the AnalyzeResponse from App.tsx
 * (produced on HomePage) and renders it — this page owns no API calls
 * of its own besides what ReportDownloadButton triggers internally.
 */

import { motion } from "framer-motion";
import { ArrowLeft, Briefcase, GraduationCap, Mail, Phone, TriangleAlert } from "lucide-react";
import ATSGauge from "@/components/ATSGauge";
import SkillRadarChart from "@/components/SkillRadarChart";
import RoleMatchChart from "@/components/RoleMatchChart";
import StrengthsWeaknesses from "@/components/StrengthsWeaknesses";
import ReportDownloadButton from "@/components/ReportDownloadButton";
import type { AnalyzeResponse, DetectedSkill } from "@/api/client";

interface DashboardPageProps {
  analysis: AnalyzeResponse;
  onReset: () => void;
}

const MATCH_TYPE_PILL: Record<DetectedSkill["match_type"], string> = {
  exact: "pill-mint",
  alias: "pill-cyan",
  fuzzy: "pill-muted",
};

const MATCH_TYPE_LABEL: Record<DetectedSkill["match_type"], string> = {
  exact: "exact",
  alias: "alias",
  fuzzy: "fuzzy match",
};

export default function DashboardPage({ analysis, onReset }: DashboardPageProps) {
  const { resume, ats, role_matches, warnings } = analysis;

  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      {/* Top bar */}
      <div className="mb-8 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <button
            type="button"
            onClick={onReset}
            className="mb-3 flex items-center gap-1.5 text-sm text-mist-400 transition-colors hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" />
            Analyze another resume
          </button>
          <h1 className="text-2xl font-bold text-white sm:text-3xl">{resume.name}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-1 text-sm text-mist-400">
            {resume.email !== "Not Detected" && (
              <span className="flex items-center gap-1.5">
                <Mail className="h-3.5 w-3.5" /> {resume.email}
              </span>
            )}
            {resume.phone !== "Not Detected" && (
              <span className="flex items-center gap-1.5">
                <Phone className="h-3.5 w-3.5" /> {resume.phone}
              </span>
            )}
            <span className="flex items-center gap-1.5">
              <Briefcase className="h-3.5 w-3.5" /> {resume.experience_years} yrs experience
            </span>
            {resume.education.length > 0 && (
              <span className="flex items-center gap-1.5">
                <GraduationCap className="h-3.5 w-3.5" /> {resume.education[0]}
              </span>
            )}
          </div>
        </div>

        <ReportDownloadButton analysis={analysis} />
      </div>

      {/* Warnings */}
      {warnings.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6 flex flex-col gap-2 rounded-xl border border-ember-500/30 bg-ember-500/10 px-4 py-3 text-sm text-ember-400"
        >
          {warnings.map((warning) => (
            <div key={warning} className="flex items-start gap-2">
              <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" />
              {warning}
            </div>
          ))}
        </motion.div>
      )}

      {/* Score + detected skills */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        <div className="lg:col-span-2">
          <ATSGauge score={ats.total_score} breakdown={ats.breakdown} />
        </div>

        <div className="glass-card p-6 lg:col-span-3">
          <h3 className="mb-1 text-lg font-semibold">Detected Skills</h3>
          <p className="mb-4 text-sm text-mist-400">
            {resume.detected_skills.length} skill{resume.detected_skills.length === 1 ? "" : "s"} found across your resume
          </p>

          {resume.detected_skills.length === 0 ? (
            <p className="text-sm text-mist-500">No recognized technical skills were detected.</p>
          ) : (
            <div className="flex max-h-72 flex-wrap gap-2 overflow-y-auto pr-1">
              {resume.detected_skills.map((skill, index) => (
                <motion.span
                  key={skill.skill}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: Math.min(index * 0.03, 0.6), type: "spring", stiffness: 300, damping: 22 }}
                  className={MATCH_TYPE_PILL[skill.match_type]}
                  title={`Confidence: ${Math.round(skill.confidence * 100)}%`}
                >
                  {skill.skill}
                  <span className="opacity-70">· {MATCH_TYPE_LABEL[skill.match_type]}</span>
                </motion.span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Charts */}
      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <SkillRadarChart detectedSkills={resume.detected_skills} />
        <RoleMatchChart roleMatches={role_matches} />
      </div>

      {/* Feedback */}
      <div className="mt-6">
        <StrengthsWeaknesses
          strengths={ats.strengths}
          weaknesses={ats.weaknesses}
          missingSkills={resume.missing_skills}
        />
      </div>
    </div>
  );
}

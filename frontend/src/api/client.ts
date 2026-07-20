/**
 * api/client.ts
 * --------------
 * Thin Axios wrapper around the FastAPI backend, plus the TypeScript
 * interfaces that mirror backend/app/models.py exactly. Keeping the
 * types here (rather than scattered inline in components) means every
 * component that touches API data shares one source of truth.
 */

import axios, { AxiosError } from "axios";

// Vite exposes env vars prefixed with VITE_ via import.meta.env. Falls
// back to localhost:8000 (the default `uvicorn main:app` address) so the
// app works out of the box in local dev without any .env file.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60_000, // resume parsing + embedding inference can take a few seconds
});

// ----------------------------------------------------------------------
// TYPES — mirror backend/app/models.py
// ----------------------------------------------------------------------
export type MatchType = "exact" | "alias" | "fuzzy";

export interface DetectedSkill {
  skill: string;
  category: string;
  weight: number;
  confidence: number;
  match_type: MatchType;
}

export interface MissingSkill {
  skill: string;
  category: string;
  weight: number;
}

export interface ExperienceEntry {
  raw_text: string;
  start_date: string | null;
  end_date: string | null;
  is_current: boolean;
  months: number;
}

export interface SectionsPresent {
  education: boolean;
  experience: boolean;
  skills: boolean;
  projects: boolean;
  certifications: boolean;
  summary: boolean;
  contact_info: boolean;
}

export interface ParsedResume {
  name: string;
  email: string;
  phone: string;
  detected_skills: DetectedSkill[];
  missing_skills: MissingSkill[];
  education: string[];
  experience_years: number;
  experience_entries: ExperienceEntry[];
  projects_count: number;
  certifications_count: number;
  sections_present: SectionsPresent;
  word_count: number;
}

export interface ATSBreakdown {
  skills: number;
  experience: number;
  education: number;
  projects: number;
  certifications: number;
  contact_info: number;
  formatting: number;
}

export interface ATSResult {
  total_score: number;
  breakdown: ATSBreakdown;
  strengths: string[];
  weaknesses: string[];
}

export interface RoleMatch {
  role_name: string;
  description: string;
  matched_skills: string[];
  missing_skills: string[];
  min_experience_years: number;
  overlap_score: number;
  similarity_score: number;
  match_percentage: number;
}

export interface AnalyzeResponse {
  resume: ParsedResume;
  ats: ATSResult;
  role_matches: RoleMatch[];
  warnings: string[];
}

export interface HealthResponse {
  status: "ok";
  spacy_model_loaded: boolean;
  embedding_model_loaded: boolean;
}

// ----------------------------------------------------------------------
// ERROR HANDLING
// ----------------------------------------------------------------------
export class ApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message);
    this.name = "ApiError";
  }
}

function toApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail?: string }>;
    const detail = axiosError.response?.data?.detail;
    if (detail) {
      return new ApiError(detail, axiosError.response?.status);
    }
    if (axiosError.code === "ECONNABORTED") {
      return new ApiError("The request timed out. The server may be under heavy load — please try again.");
    }
    if (!axiosError.response) {
      return new ApiError(
        "Could not reach the backend. Make sure the FastAPI server is running on " + API_BASE_URL
      );
    }
    return new ApiError("Something went wrong while talking to the server.", axiosError.response.status);
  }
  return new ApiError("An unexpected error occurred.");
}

// ----------------------------------------------------------------------
// API CALLS
// ----------------------------------------------------------------------
export async function checkHealth(): Promise<HealthResponse> {
  try {
    const response = await apiClient.get<HealthResponse>("/api/health");
    return response.data;
  } catch (error) {
    throw toApiError(error);
  }
}

export async function analyzeResume(file: File): Promise<AnalyzeResponse> {
  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await apiClient.post<AnalyzeResponse>("/api/analyze", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return response.data;
  } catch (error) {
    throw toApiError(error);
  }
}

export async function downloadReport(analysis: AnalyzeResponse): Promise<Blob> {
  try {
    const response = await apiClient.post<Blob>(
      "/api/report",
      { analysis },
      { responseType: "blob" }
    );
    return response.data;
  } catch (error) {
    throw toApiError(error);
  }
}

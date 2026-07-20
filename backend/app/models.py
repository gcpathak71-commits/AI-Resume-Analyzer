"""
app/models.py
-------------
Pydantic schemas shared across the backend. These define the exact JSON
shape the FastAPI routes accept and return, so the frontend (TypeScript)
has a single, predictable contract to build against.

Design note: the backend is stateless between requests — nothing is
persisted server-side. The `/api/report` endpoint therefore accepts the
*already-computed* AnalyzeResponse (rather than re-uploading and
re-parsing the PDF) so the PDF report always reflects exactly what the
user saw on the dashboard.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ----------------------------------------------------------------------
# SKILLS
# ----------------------------------------------------------------------
class DetectedSkill(BaseModel):
    """A single skill found in the resume, with provenance about *how* it
    was matched (exact name, a known alias, or a fuzzy/typo-tolerant hit)
    and a confidence score reflecting match quality."""

    skill: str
    category: str
    weight: int = Field(ge=1, le=5)
    confidence: float = Field(ge=0.0, le=1.0)
    match_type: Literal["exact", "alias", "fuzzy"]


class MissingSkill(BaseModel):
    """An in-demand skill from the master taxonomy that was NOT found in
    the resume, ranked by importance (weight) in the response order."""

    skill: str
    category: str
    weight: int = Field(ge=1, le=5)


# ----------------------------------------------------------------------
# EXPERIENCE
# ----------------------------------------------------------------------
class ExperienceEntry(BaseModel):
    """One parsed employment date range, e.g. 'Jan 2022 - Present'."""

    raw_text: str
    start_date: Optional[str] = None  # ISO date string (YYYY-MM-DD), if parsed
    end_date: Optional[str] = None    # ISO date string, or null if "Present"
    is_current: bool = False
    months: float = Field(ge=0.0)


# ----------------------------------------------------------------------
# SECTIONS
# ----------------------------------------------------------------------
class SectionsPresent(BaseModel):
    education: bool = False
    experience: bool = False
    skills: bool = False
    projects: bool = False
    certifications: bool = False
    summary: bool = False
    contact_info: bool = False


# ----------------------------------------------------------------------
# PARSED RESUME
# ----------------------------------------------------------------------
class ParsedResume(BaseModel):
    """The full structured output of the parsing + skill-matching pipeline."""

    name: str
    email: str
    phone: str
    detected_skills: List[DetectedSkill]
    missing_skills: List[MissingSkill]
    education: List[str]
    experience_years: float = Field(ge=0.0)
    experience_entries: List[ExperienceEntry]
    projects_count: int = Field(ge=0)
    certifications_count: int = Field(ge=0)
    sections_present: SectionsPresent
    word_count: int = Field(ge=0)


# ----------------------------------------------------------------------
# ATS SCORE
# ----------------------------------------------------------------------
class ATSBreakdown(BaseModel):
    skills: float
    experience: float
    education: float
    projects: float
    certifications: float
    contact_info: float
    formatting: float


class ATSResult(BaseModel):
    total_score: int = Field(ge=0, le=100)
    breakdown: ATSBreakdown
    strengths: List[str]
    weaknesses: List[str]


# ----------------------------------------------------------------------
# JOB ROLE MATCHING
# ----------------------------------------------------------------------
class RoleMatch(BaseModel):
    role_name: str
    description: str
    matched_skills: List[str]
    missing_skills: List[str]
    min_experience_years: int
    overlap_score: float = Field(ge=0.0, le=100.0)
    similarity_score: float = Field(ge=0.0, le=100.0)
    match_percentage: float = Field(ge=0.0, le=100.0)


# ----------------------------------------------------------------------
# TOP-LEVEL API RESPONSES
# ----------------------------------------------------------------------
class AnalyzeResponse(BaseModel):
    """Response returned by POST /api/analyze."""

    resume: ParsedResume
    ats: ATSResult
    role_matches: List[RoleMatch]
    warnings: List[str] = []


class ReportRequest(BaseModel):
    """Request body for POST /api/report — regenerates a PDF from an
    already-computed analysis rather than re-parsing the resume."""

    analysis: AnalyzeResponse


class ErrorResponse(BaseModel):
    detail: str


class HealthResponse(BaseModel):
    status: Literal["ok"]
    spacy_model_loaded: bool
    embedding_model_loaded: bool

"""
app/routes.py
--------------
FastAPI route definitions — the HTTP surface of the backend.

Endpoints:
    GET  /api/health   -> basic readiness check (are the ML models loaded?)
    POST /api/analyze  -> upload a resume PDF, get back the full analysis
    POST /api/report   -> given a previously-returned analysis, get a PDF

The expensive-to-load resources (spaCy pipeline, skill matcher, TF-IDF
based recommender) are loaded exactly once at app startup (see main.py)
and attached to `app.state.resources`. Routes pull them from there rather
than re-instantiating anything per request.
"""

import io
import logging
from typing import List

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import Response

from .ats import calculate_ats_score
from .models import AnalyzeResponse, ErrorResponse, HealthResponse, ReportRequest
from .pdf_report import generate_pdf_report

logger = logging.getLogger("resume_analyzer")

router = APIRouter(prefix="/api", tags=["resume-analyzer"])

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ACCEPTED_CONTENT_TYPES = {"application/pdf", "application/x-pdf", "application/octet-stream"}


def _get_resources(request: Request):
    """Pull the shared ML resources off app.state, where main.py loads
    them once at startup. Returns a 503 rather than crashing if a request
    somehow arrives before startup has finished."""
    resources = getattr(request.app.state, "resources", None)
    if resources is None:
        raise HTTPException(status_code=503, detail="Server is still starting up. Please retry shortly.")
    return resources


@router.get("/health", response_model=HealthResponse)
def health_check(request: Request) -> HealthResponse:
    resources = getattr(request.app.state, "resources", None)
    return HealthResponse(
        status="ok",
        spacy_model_loaded=resources is not None and getattr(resources, "nlp", None) is not None,
        embedding_model_loaded=resources is not None and getattr(resources, "recommender", None) is not None,
    )


@router.post("/analyze", response_model=AnalyzeResponse, responses={400: {"model": ErrorResponse}})
async def analyze_resume(request: Request, file: UploadFile = File(...)) -> AnalyzeResponse:
    """
    Accepts a single PDF resume upload and runs the full pipeline:
    parsing -> skill detection -> ATS scoring -> job role recommendation.
    """
    resources = _get_resources(request)

    if file.filename and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    if file.content_type and file.content_type not in ACCEPTED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File is too large. Please upload a PDF under 10 MB.")

    warnings: List[str] = []

    try:
        parsed = resources.parser.parse(io.BytesIO(file_bytes))
    except ValueError as error:
        # Expected, user-facing failure modes: corrupt PDF, scanned image, etc.
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:  # noqa: BLE001 — deliberately broad: never leak internals
        raise HTTPException(status_code=500, detail="Unexpected error while parsing the resume.") from error

    if parsed["word_count"] < 30:
        warnings.append("This resume appears unusually short — results may be less accurate.")

    try:
        detected_skills, missing_skills = resources.skill_matcher.match(parsed["raw_text"])
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Unexpected error while detecting skills.") from error

    if not detected_skills:
        warnings.append("No recognized technical skills were found. Role matches may be unreliable.")

    parsed_data = {**parsed, "detected_skills": detected_skills, "missing_skills": missing_skills}
    ats_result = calculate_ats_score(parsed_data)

    try:
        role_matches = resources.recommender.recommend_roles(detected_skills, parsed["raw_text"])
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Unexpected error while matching job roles.") from error

    resume_payload = {
        "name": parsed["name"],
        "email": parsed["email"],
        "phone": parsed["phone"],
        "detected_skills": detected_skills,
        "missing_skills": missing_skills,
        "education": parsed["education"],
        "experience_years": parsed["experience_years"],
        "experience_entries": [
            {
                "raw_text": entry.raw_text,
                "start_date": entry.start_date.isoformat() if entry.start_date else None,
                "end_date": entry.end_date.isoformat() if entry.end_date else None,
                "is_current": entry.is_current,
                "months": entry.months,
            }
            for entry in parsed["experience_entries"]
        ],
        "projects_count": parsed["projects_count"],
        "certifications_count": parsed["certifications_count"],
        "sections_present": parsed["sections_present"],
        "word_count": parsed["word_count"],
    }

    return AnalyzeResponse(resume=resume_payload, ats=ats_result, role_matches=role_matches, warnings=warnings)


@router.post("/report")
def download_report(payload: ReportRequest) -> Response:
    """
    Regenerates a PDF report from an already-computed analysis (the exact
    JSON returned by /api/analyze), rather than re-uploading and
    re-parsing the resume. Keeps the backend fully stateless.
    """
    analysis_dict = payload.analysis.model_dump()

    try:
        pdf_bytes = generate_pdf_report(analysis_dict)
    except Exception as error:  # noqa: BLE001
        logger.exception("Failed to generate PDF report")
        raise HTTPException(status_code=500, detail=f"Failed to generate the PDF report: {error}") from error

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=resume_analysis_report.pdf"},
    )
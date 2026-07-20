"""
main.py
-------
FastAPI application entrypoint.

Loads every expensive resource (spaCy pipeline, and the parser/matcher/
recommender objects built on top of it) exactly once at startup via a
lifespan handler, wires in CORS so the Vite dev server can call this API,
and mounts the API router.

Run with:
    uvicorn main:app --reload
"""

import os
import threading
from contextlib import asynccontextmanager
from dataclasses import dataclass

import spacy
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.parser import ResumeParser
from app.recommender import JobRecommender
from app.routes import router
from app.skill_matcher import SkillMatcher

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_CSV_PATH = os.path.join(BASE_DIR, "data", "skills.csv")
ROLES_CSV_PATH = os.path.join(BASE_DIR, "data", "roles.csv")

# In production, set an ALLOWED_ORIGINS env var (comma-separated) to your
# deployed frontend URL(s), e.g. "https://your-app.vercel.app". Local dev
# origins are always included so `npm run dev` keeps working out of the box.
_env_origins = os.environ.get("ALLOWED_ORIGINS", "")

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://ai-resume-analyzer-anurag-pathak-s-projects.vercel.app",
    "https://ai-resume-analyzer-beta-rose.vercel.app",
]

if _env_origins:
    ALLOWED_ORIGINS.extend(
        [origin.strip() for origin in _env_origins.split(",") if origin.strip()]
    )



@dataclass
class AppResources:
    """Bundles every expensive-to-load ML resource so routes.py can pull
    them off app.state as a single object instead of scattered globals."""

    nlp: object
    parser: ResumeParser
    skill_matcher: SkillMatcher
    recommender: JobRecommender


def _load_spacy_model():
    try:
        return spacy.load("en_core_web_sm")
    except OSError as error:
        raise RuntimeError(
            "spaCy model 'en_core_web_sm' is not installed. "
            "Run this command once inside your virtual environment:\n"
            "    python -m spacy download en_core_web_sm"
        ) from error


def _load_resources(app: FastAPI) -> None:
    """
    Loads every ML model and builds the parser/matcher/recommender objects,
    then attaches them to app.state.resources.

    This runs in a background thread (see lifespan below) so it never
    blocks Uvicorn from binding its port and accepting connections. Cloud
    platforms (Render, Railway, etc.) health-check by checking whether the
    port is open — if model loading blocked startup, a slow first load
    (spaCy's model load can take a few seconds on a small free instance)
    could cause the platform to think the app failed to start.

    Until this finishes, app.state.resources stays None, and routes.py's
    _get_resources() returns a 503 "still starting up" response instead of
    crashing — so the API is technically live and reachable immediately,
    it just can't fully serve /api/analyze requests until this completes.
    """
    print("Loading spaCy model (en_core_web_sm)...")
    nlp = _load_spacy_model()

    print("Building skill matcher and job recommender...")
    resume_parser = ResumeParser(nlp)
    skill_matcher = SkillMatcher(SKILLS_CSV_PATH, nlp)
    recommender = JobRecommender(ROLES_CSV_PATH)

    app.state.resources = AppResources(
        nlp=nlp,
        parser=resume_parser,
        skill_matcher=skill_matcher,
        recommender=recommender,
    )
    print("Startup complete. Ready to analyze resumes.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Starts loading ML models in a background thread, then immediately
    yields so Uvicorn opens its port and starts accepting connections right
    away — model loading continues in parallel rather than delaying it."""
    app.state.resources = None
    loading_thread = threading.Thread(target=_load_resources, args=(app,), daemon=True)
    loading_thread.start()

    yield

    app.state.resources = None


app = FastAPI(
    title="AI Resume Analyzer Pro API",
    description="Backend API for parsing resumes, scoring ATS-readiness, and recommending job roles.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root() -> dict:
    return {"message": "AI Resume Analyzer Pro API is running. See /docs for the interactive API reference."}
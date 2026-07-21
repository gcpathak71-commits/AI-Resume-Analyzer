# AI Resume Analyzer

A full-stack, AI-powered resume analyzer: FastAPI backend + React/TypeScript
frontend. Upload a PDF resume and get a weighted ATS score, accurate skill
detection (spaCy + fuzzy matching), a skill gap analysis, and job role
recommendations ranked by a blended skill-overlap + TF-IDF similarity score
— plus a downloadable PDF report.

This is a full rewrite of the original Streamlit prototype: no Streamlit
anywhere, a decoupled REST API + SPA architecture, and materially more
accurate matching logic throughout

---

## Tech Stack

**Backend:** FastAPI, Uvicorn, pdfplumber, spaCy (PhraseMatcher + NER),
scikit-learn (TF-IDF + cosine similarity), rapidfuzz, pandas,
python-dateutil, fpdf2, Pydantic.

**Frontend:** React 18 + Vite + TypeScript, Tailwind CSS (custom design
system), Framer Motion, Recharts, Axios, lucide-react.

---

## Project Structure

```
AI-Resume-Analyzer/
├── backend/
│   ├── main.py                  # FastAPI entrypoint — run this with uvicorn
│   ├── requirements.txt
│   ├── Dockerfile               # Render-oriented Docker build
│   ├── render.yaml               # Render service definition
│   ├── app/
│   │   ├── models.py            # Pydantic schemas (the API contract)
│   │   ├── parser.py            # PDF text/layout extraction, dates, sections
│   │   ├── skill_matcher.py     # spaCy PhraseMatcher + rapidfuzz skill detection
│   │   ├── ats.py               # Weighted ATS scoring engine
│   │   ├── recommender.py       # TF-IDF + skill-overlap job role matching
│   │   ├── pdf_report.py        # fpdf2 report generation
│   │   └── routes.py            # /api/health, /api/analyze, /api/report
│   └── data/
│       ├── skills.csv           # Skill taxonomy (name, category, aliases, weight)
│       └── roles.csv            # Job role definitions
│
└── frontend/
    ├── src/
    │   ├── main.tsx / App.tsx
    │   ├── api/client.ts        # Typed API client
    │   ├── components/          # UploadZone, ATSGauge, RoleMatchChart,
    │   │                        #   SkillRadarChart, StrengthsWeaknesses,
    │   │                        #   ReportDownloadButton
    │   ├── pages/                # HomePage, DashboardPage
    │   └── styles/globals.css
    ├── package.json
    └── vite.config.ts
```

---

## How It Works

1. **Parsing** (`parser.py`) — extracts raw text and layout from the PDF
   with `pdfplumber`, then pulls out name, email, phone, education,
   work-experience entries (with parsed start/end dates), project count,
   certification count, and which standard resume sections are present.
2. **Skill detection** (`skill_matcher.py`) — a two-stage pipeline against
   the taxonomy in `data/skills.csv`:
   - Stage 1: spaCy `PhraseMatcher` for exact names and aliases (handles
     multi-word skills and phrasing variants).
   - Stage 2: `rapidfuzz` fuzzy matching for anything not found exactly,
     so typos like "Pyhton" or "TensorFlow2" still register — at a lower
     confidence.
   Every detected skill carries a `confidence` score and a `match_type`
   (`exact` / `alias` / `fuzzy`).
3. **ATS scoring** (`ats.py`) — a weighted 0–100 score built from Skills
   Match (35 pts), Experience (15), Resume Formatting (15), Education
   (10), Projects (10), Certifications (10), and Contact Info (5).
4. **Job role recommendation** (`recommender.py`) — ranks roles from
   `data/roles.csv` using a blend of **skill overlap** (55% weight, the
   most interpretable signal) and **TF-IDF cosine similarity** (45%
   weight) between the resume text and each role's description/required
   skills.
5. **Report generation** (`pdf_report.py`) — renders the completed
   analysis back into a downloadable PDF via `fpdf2`.

---

## 1. Backend Setup

Open a terminal in `AI-Resume-Analyzer/backend/`:

```bash
# Create and activate a virtual environment
python -m venv venv

# macOS / Linux:
source venv/bin/activate
# Windows (PowerShell):
venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Download the spaCy English model (one-time, ~500 files, a few seconds)
python -m spacy download en_core_web_sm

# Run the API server
uvicorn main:app --reload
```

Startup is quick — there's no large model download on first run. You
should see:
```
Loading spaCy model (en_core_web_sm)...
Building skill matcher and job recommender...
Startup complete. Ready to analyze resumes.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

Model loading happens in a background thread, so Uvicorn opens its port
immediately. If a request hits `/api/analyze` before loading finishes,
the API returns a `503` ("still starting up") rather than failing.

Verify it's alive by visiting **http://localhost:8000/docs** — FastAPI's
interactive API documentation (Swagger UI). You can test `/api/analyze`
directly from that page.

---

## 2. Frontend Setup

Open a **second terminal** in `AI-Resume-Analyzer/frontend/`:

```bash
npm install
npm run dev
```

Vite will start the dev server at **http://localhost:5173**. Open that
URL in your browser — you should see the landing page.

---

## 3. Confirming the Frontend and Backend Are Talking

- The frontend defaults to calling the backend at `http://localhost:8000`
  (see `src/api/client.ts`). To override this — e.g. if you run the
  backend on a different port — create a `.env` file in `frontend/`:
  ```
  VITE_API_BASE_URL=http://localhost:8000
  ```
- CORS in `backend/main.py` already allows `http://localhost:5173` and
  `http://127.0.0.1:5173` (Vite's default dev origins) out of the box.
  Additional origins — e.g. your deployed frontend's URL — can be added
  via a comma-separated `ALLOWED_ORIGINS` environment variable, without
  editing code.
- Quick end-to-end check: upload any PDF resume on the homepage. If you
  see a spinner followed by the dashboard, everything is wired correctly.
  If you get a "Could not reach the backend" error, make sure the
  `uvicorn` terminal is still running and printed "Startup complete".

---

## API Reference

| Method | Endpoint       | Description                                                       |
|--------|----------------|--------------------------------------------------------------------|
| GET    | `/api/health`  | Readiness check — reports whether the spaCy/skill-matching models are loaded. |
| POST   | `/api/analyze` | Upload a PDF resume (max 10 MB); returns the full parsed resume, ATS score, and ranked role matches. |
| POST   | `/api/report`  | Given a previously-returned analysis JSON, regenerates and returns a PDF report. Backend stays stateless — nothing is re-parsed. |

---

## Optional: Deploying

The backend and frontend are deployed separately.

**Backend (FastAPI) → Render**
- `backend/render.yaml` and `backend/Dockerfile` are set up for Render's
  free tier specifically:
  - Python 3.11-slim, chosen because it has broad prebuilt-wheel
    coverage, keeping installs fast and avoiding from-source builds that
    can exhaust free-tier disk space.
  - `sentence-transformers`/`torch` are intentionally **not** included —
    they added several hundred MB, which routinely exceeded the free
    tier's 512MB RAM/disk budget. See **What Changed From v1**.
  - The container listens on Render's injected `$PORT`, not a fixed port.
- Set the `ALLOWED_ORIGINS` env var in Render's dashboard to your
  deployed frontend's URL(s) (comma-separated for multiple).
- Health check path is `/api/health`.

**Frontend (React/Vite) → Vercel**
- Vercel auto-detects Vite projects; build command `npm run build`,
  output directory `dist`.
- Set `VITE_API_BASE_URL` in Vercel's dashboard to your deployed Render
  backend's URL.

Remember: whichever frontend URL you deploy to must be added to
`ALLOWED_ORIGINS` on the backend, or the browser will block the requests
with a CORS error.

---



## License

For personal/portfolio use. Adapt freely.

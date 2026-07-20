# AI Resume Analyzer 

A full-stack, AI-powered resume analyzer: FastAPI backend + React/TypeScript
frontend. Upload a PDF resume and get a weighted ATS score, accurate skill
detection (spaCy + fuzzy matching), a skill gap analysis, and job role
recommendations ranked by real semantic similarity (sentence-transformers)
— plus a downloadable PDF report.

This is a full rewrite of the original Streamlit prototype: no Streamlit
anywhere, a decoupled REST API + SPA architecture, and materially more
accurate matching logic throughout (see **What Changed From v1** below).

---

## Tech Stack

**Backend:** FastAPI, Uvicorn, pdfplumber, spaCy (PhraseMatcher + NER),
sentence-transformers (`all-MiniLM-L6-v2`), rapidfuzz, scikit-learn,
python-dateutil, fpdf2, Pydantic.

**Frontend:** React 18 + Vite + TypeScript, Tailwind CSS (custom design
system), Framer Motion, Recharts, Axios, lucide-react.

---

## Project Structure

```
AI-Resume-Analyzer-Pro/
├── backend/
│   ├── main.py                  # FastAPI entrypoint — run this with uvicorn
│   ├── requirements.txt
│   ├── app/
│   │   ├── models.py            # Pydantic schemas (the API contract)
│   │   ├── parser.py            # PDF text/layout extraction, dates, sections
│   │   ├── skill_matcher.py     # spaCy PhraseMatcher + rapidfuzz skill detection
│   │   ├── ats.py               # Weighted ATS scoring engine
│   │   ├── recommender.py       # Sentence-embedding job role matching
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
    │   ├── components/          # UploadZone, ATSGauge, charts, etc.
    │   ├── pages/                # HomePage, DashboardPage
    │   └── styles/globals.css
    ├── package.json
    └── vite.config.ts
```

---

## 1. Backend Setup

Open a terminal in `AI-Resume-Analyzer-Pro/backend/`:

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

The first startup will take a little longer than usual (10-30 seconds) —
that's the sentence-transformer model (`all-MiniLM-L6-v2`, ~90MB)
downloading and caching locally the very first time it's used. Subsequent
restarts are fast.

You should see:
```
Loading spaCy model (en_core_web_sm)...
Loading sentence-transformer model (all-MiniLM-L6-v2)...
Building skill matcher and job recommender...
Startup complete. Ready to analyze resumes.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

Verify it's alive by visiting **http://localhost:8000/docs** — FastAPI's
interactive API documentation (Swagger UI). You can even test
`/api/analyze` directly from that page.

---

## 2. Frontend Setup

Open a **second terminal** in `AI-Resume-Analyzer-Pro/frontend/`:

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
- CORS is already configured in `backend/main.py` (`ALLOWED_ORIGINS`) to
  accept requests from `http://localhost:5173`, Vite's default port. If
  you change the frontend's port, add the new origin to that list too.
- Quick end-to-end check: upload any PDF resume on the homepage. If you
  see a spinner followed by the dashboard, everything is wired correctly.
  If you get a "Could not reach the backend" error, make sure the
  `uvicorn` terminal is still running and didn't crash on startup (check
  it printed "Startup complete").

---


## Optional: Deploying

This project is designed to run locally, but the backend/frontend split
makes it straightforward to deploy separately if you'd like:

- **Backend (FastAPI)** → Render, Railway, or Fly.io all support Python
  web services directly from a `requirements.txt` + start command
  (`uvicorn main:app --host 0.0.0.0 --port $PORT`). Note the sentence-
  transformer model download on first boot, so pick a plan with enough
  memory (at least ~1GB free) and a reasonable startup timeout.
- **Frontend (React/Vite)** → Vercel or Netlify both auto-detect Vite
  projects; set the build command to `npm run build` and the output
  directory to `dist`. Set the `VITE_API_BASE_URL` environment variable
  in your hosting provider's dashboard to your deployed backend's URL.
- Remember to add your deployed frontend's URL to `ALLOWED_ORIGINS` in
  `backend/main.py` once both are live.

---

## License

For personal/portfolio use. Adapt freely.

---
title: AI Resume Analyzer Backend
emoji: 📄
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# AI Resume Analyzer Pro — Backend API

FastAPI backend for the AI Resume Analyzer Pro project. Parses uploaded PDF
resumes, detects skills via spaCy PhraseMatcher + fuzzy matching, scores
ATS-readiness, and recommends job roles using sentence-transformer semantic
similarity.

Interactive API docs available at `/docs` once the Space is running.

This Space is the backend only. The frontend (React + Vite) is deployed
separately (e.g., on Vercel) and configured to call this Space's URL via
its `VITE_API_BASE_URL` environment variable.

"""
app/pdf_report.py
------------------
Generates the downloadable PDF summary report using fpdf2.

Takes the same JSON shape the frontend receives from POST /api/analyze
(the serialized AnalyzeResponse) and renders it into a clean, printable
PDF — so the report always matches exactly what the user saw on the
dashboard, with no re-parsing or re-scoring involved.
"""

from fpdf import FPDF

# Matches the primary blue used in the frontend design system, so the PDF
# report and the web dashboard feel like the same product.
COLOR_PRIMARY = (30, 64, 175)  # RGB
COLOR_TEXT = (17, 24, 39)
COLOR_MUTED = (75, 85, 99)

# Common "smart" Unicode punctuation mapped to plain ASCII equivalents.
# fpdf2's built-in core fonts (Helvetica) only support Latin-1, so anything
# outside it (curly quotes, em/en dashes, bullets, etc.) must be converted
# or it can crash PDF generation entirely.
_UNICODE_REPLACEMENTS = {
    "\u2014": "-",   # em dash
    "\u2013": "-",   # en dash
    "\u2018": "'",   # left single quote
    "\u2019": "'",   # right single quote
    "\u201c": '"',   # left double quote
    "\u201d": '"',   # right double quote
    "\u2026": "...", # ellipsis
    "\u2022": "-",   # bullet
    "\u00a0": " ",   # non-breaking space
}


def _sanitize(text) -> str:
    """Make any string safe to render with fpdf2's Latin-1-only core fonts.
    Replaces common Unicode punctuation, then drops anything still not
    Latin-1-encodable, so a single unusual character never crashes the
    whole report."""
    text = str(text)
    for unicode_char, replacement in _UNICODE_REPLACEMENTS.items():
        text = text.replace(unicode_char, replacement)
    return text.encode("latin-1", errors="ignore").decode("latin-1")


def generate_pdf_report(analysis: dict) -> bytes:
    """
    Build the full PDF report.

    Args:
        analysis (dict): The serialized AnalyzeResponse — must contain
            "resume", "ats", and "role_matches" keys.

    Returns:
        bytes: The complete PDF file content.
    """
    resume = analysis["resume"]
    ats = analysis["ats"]
    role_matches = analysis.get("role_matches", [])

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    _add_header(pdf, resume)
    _add_ats_section(pdf, ats)
    _add_skills_section(pdf, resume)
    _add_experience_section(pdf, resume)
    _add_role_recommendations(pdf, role_matches)
    _add_feedback_section(pdf, ats)

    return bytes(pdf.output())


def _add_header(pdf: FPDF, resume: dict) -> None:
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*COLOR_PRIMARY)
    pdf.cell(0, 12, "AI Resume Analyzer Pro - Report", new_x="LMARGIN", new_y="NEXT", align="C")

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.cell(0, 8, _sanitize(f"Candidate Name: {resume.get('name', 'Not Detected')}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, _sanitize(f"Email: {resume.get('email', 'Not Detected')}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, _sanitize(f"Phone: {resume.get('phone', 'Not Detected')}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)


def _add_ats_section(pdf: FPDF, ats: dict) -> None:
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.cell(0, 10, f"ATS Score: {ats['total_score']} / 100", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*COLOR_MUTED)
    for category, score in ats["breakdown"].items():
        label = category.replace("_", " ").title()
        pdf.cell(0, 7, _sanitize(f"  - {label}: {score}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_text_color(*COLOR_TEXT)


def _add_skills_section(pdf: FPDF, resume: dict) -> None:
    detected = resume.get("detected_skills", [])
    missing = resume.get("missing_skills", [])

    detected_names = [f"{skill['skill']} ({skill['match_type']})" for skill in detected]
    missing_names = [skill["skill"] for skill in missing]

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "Detected Skills", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 7, _sanitize(", ".join(detected_names) if detected_names else "None detected"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "Missing Skills", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 7, _sanitize(", ".join(missing_names) if missing_names else "None - excellent coverage!"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)


def _add_experience_section(pdf: FPDF, resume: dict) -> None:
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "Experience", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)

    years = resume.get("experience_years", 0.0)
    pdf.cell(0, 7, _sanitize(f"Total calculated experience: {years} years"), new_x="LMARGIN", new_y="NEXT")

    entries = resume.get("experience_entries", [])
    if entries:
        pdf.set_font("Helvetica", "", 10)
        for entry in entries[:8]:
            status = "Present" if entry.get("is_current") else entry.get("end_date", "")
            pdf.cell(
                0, 6,
                _sanitize(f"  - {entry.get('raw_text', '')} -> {entry.get('months', 0)} months (ends {status})"),
                new_x="LMARGIN", new_y="NEXT",
            )
    pdf.ln(4)


def _add_role_recommendations(pdf: FPDF, role_matches: list) -> None:
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "Job Role Recommendation", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)

    if not role_matches:
        pdf.multi_cell(0, 7, "No role recommendation could be generated.", new_x="LMARGIN", new_y="NEXT")
        return

    top_role = role_matches[0]
    pdf.multi_cell(
        0, 7,
        _sanitize(
            f"Best Match: {top_role['role_name']} ({top_role['match_percentage']}% match)\n"
            f"{top_role['description']}"
        ),
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Top Role Comparison:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for role in role_matches[:5]:
        pdf.cell(0, 6, _sanitize(f"  - {role['role_name']}: {role['match_percentage']}%"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)


def _add_feedback_section(pdf: FPDF, ats: dict) -> None:
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "Strengths", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    for strength in ats.get("strengths", []):
        pdf.multi_cell(0, 7, _sanitize(f"+ {strength}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "Improvement Suggestions", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    for weakness in ats.get("weaknesses", []):
        pdf.multi_cell(0, 7, _sanitize(f"- {weakness}"), new_x="LMARGIN", new_y="NEXT")
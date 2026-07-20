"""
app/ats.py
----------
Weighted ATS (Applicant Tracking System) scoring engine.

The final score (0-100) is a weighted combination of several sub-scores,
mirroring how real ATS platforms weigh resumes: skill relevance and
section/formatting completeness matter most, since automated systems
primarily parse structured sections and keyword relevance rather than
subjective writing quality.

    - Skills Match          (35 points)
    - Experience            (15 points)
    - Education             (10 points)
    - Projects              (10 points)
    - Certifications        (10 points)
    - Contact Information   (5 points)
    - Resume Formatting     (15 points)  -> based on which standard sections exist

Improvement over v1: the skills sub-score now uses each missing skill's
*actual* weight from the taxonomy (available since skill_matcher.py
returns full missing-skill metadata) instead of assuming a flat average
weight for every missing skill.
"""

from typing import Dict, List, Tuple

CATEGORY_WEIGHTS = {
    "skills": 35,
    "experience": 15,
    "education": 10,
    "projects": 10,
    "certifications": 10,
    "contact_info": 5,
    "formatting": 15,
}


def calculate_ats_score(parsed_data: dict) -> dict:
    """
    Calculate the overall ATS score and a breakdown of strengths/weaknesses.

    Args:
        parsed_data (dict): Combined structured resume data, containing
            detected_skills, missing_skills, education, experience_years,
            projects_count, certifications_count, and sections_present.

    Returns:
        dict: {
            "total_score": int (0-100),
            "breakdown": dict of per-category scores,
            "strengths": list[str],
            "weaknesses": list[str],
        }
    """
    breakdown = {
        "skills": _score_skills(parsed_data),
        "experience": _score_experience(parsed_data),
        "education": _score_education(parsed_data),
        "projects": _score_projects(parsed_data),
        "certifications": _score_certifications(parsed_data),
        "contact_info": _score_contact_info(parsed_data),
        "formatting": _score_formatting(parsed_data),
    }

    total_score = round(sum(breakdown.values()))
    total_score = max(0, min(total_score, 100))  # clamp to valid range

    strengths, weaknesses = _generate_feedback(parsed_data, breakdown)

    return {
        "total_score": total_score,
        "breakdown": breakdown,
        "strengths": strengths,
        "weaknesses": weaknesses,
    }


# ----------------------------------------------------------------------
# INDIVIDUAL CATEGORY SCORERS
# ----------------------------------------------------------------------
def _score_skills(parsed_data: dict) -> float:
    """
    Score based on the weighted value of detected skills vs. total possible
    weighted value (detected + missing). Rewards both quantity and
    importance of skills found, rather than a flat skill count.

    Unlike v1, missing skills carry their real taxonomy weight here (not
    an assumed average), since skill_matcher.py returns full metadata for
    every missing skill.
    """
    detected: List[dict] = parsed_data.get("detected_skills", [])
    missing: List[dict] = parsed_data.get("missing_skills", [])

    detected_weight_sum = sum(skill["weight"] for skill in detected)
    missing_weight_sum = sum(skill["weight"] for skill in missing)

    total_possible = detected_weight_sum + missing_weight_sum
    if total_possible == 0:
        return 0.0

    ratio = detected_weight_sum / total_possible
    return round(ratio * CATEGORY_WEIGHTS["skills"], 2)


def _score_experience(parsed_data: dict) -> float:
    """Score based on years of experience. Scaled so 5+ years earns full
    marks, while 0 years (common for students/freshers) still earns
    partial credit for having projects instead (handled separately)."""
    years = parsed_data.get("experience_years", 0.0)
    max_years_for_full_score = 5.0
    ratio = min(years / max_years_for_full_score, 1.0)
    return round(ratio * CATEGORY_WEIGHTS["experience"], 2)


def _score_education(parsed_data: dict) -> float:
    """Score based on whether any recognized education keywords were found."""
    education = parsed_data.get("education", [])
    if not education:
        return 0.0
    return float(CATEGORY_WEIGHTS["education"])


def _score_projects(parsed_data: dict) -> float:
    """Score based on number of projects listed, capped at 3+ for full marks."""
    projects_count = parsed_data.get("projects_count", 0)
    max_projects_for_full_score = 3
    ratio = min(projects_count / max_projects_for_full_score, 1.0)
    return round(ratio * CATEGORY_WEIGHTS["projects"], 2)


def _score_certifications(parsed_data: dict) -> float:
    """Score based on number of certifications listed, capped at 2+ for full marks."""
    certifications_count = parsed_data.get("certifications_count", 0)
    max_certifications_for_full_score = 2
    ratio = min(certifications_count / max_certifications_for_full_score, 1.0)
    return round(ratio * CATEGORY_WEIGHTS["certifications"], 2)


def _score_contact_info(parsed_data: dict) -> float:
    """Full marks if either email or phone was detected, since ATS systems
    require at least one reliable contact method."""
    sections_present = parsed_data.get("sections_present", {})
    return float(CATEGORY_WEIGHTS["contact_info"]) if sections_present.get("contact_info") else 0.0


def _score_formatting(parsed_data: dict) -> float:
    """
    Score based on how many standard resume sections are present
    (education, experience, skills, projects, certifications, summary).
    A well-formatted, ATS-friendly resume should contain most of these.
    """
    sections_present = parsed_data.get("sections_present", {})
    relevant_sections = ["education", "experience", "skills", "projects", "certifications", "summary"]
    found_count = sum(1 for section in relevant_sections if sections_present.get(section))
    ratio = found_count / len(relevant_sections)
    return round(ratio * CATEGORY_WEIGHTS["formatting"], 2)


# ----------------------------------------------------------------------
# STRENGTHS / WEAKNESSES FEEDBACK GENERATION
# ----------------------------------------------------------------------
def _generate_feedback(parsed_data: dict, breakdown: dict) -> Tuple[List[str], List[str]]:
    """Translate the numeric breakdown into human-readable strengths and
    weaknesses so the user knows exactly what to improve."""
    strengths: List[str] = []
    weaknesses: List[str] = []

    if breakdown["skills"] >= CATEGORY_WEIGHTS["skills"] * 0.7:
        strengths.append("Strong technical skill coverage relevant to industry roles.")
    else:
        weaknesses.append("Resume is missing several in-demand technical skills.")

    if breakdown["experience"] >= CATEGORY_WEIGHTS["experience"] * 0.5:
        strengths.append("Demonstrates solid professional experience.")
    else:
        weaknesses.append("Limited work experience detected — consider highlighting internships or freelance work.")

    if breakdown["education"] > 0:
        strengths.append("Educational qualifications are clearly stated.")
    else:
        weaknesses.append("No recognizable education section found. Add your degree and institution clearly.")

    if breakdown["projects"] >= CATEGORY_WEIGHTS["projects"] * 0.6:
        strengths.append("Good number of projects showcased, demonstrating practical application of skills.")
    else:
        weaknesses.append("Add more detailed projects to strengthen your practical skill evidence.")

    if breakdown["certifications"] >= CATEGORY_WEIGHTS["certifications"] * 0.5:
        strengths.append("Relevant certifications add credibility to your profile.")
    else:
        weaknesses.append("Consider adding relevant certifications to boost credibility.")

    if breakdown["contact_info"] == CATEGORY_WEIGHTS["contact_info"]:
        strengths.append("Contact information is clearly available for recruiters.")
    else:
        weaknesses.append("Missing clear contact information (email/phone). This can cause automatic rejection by ATS.")

    if breakdown["formatting"] >= CATEGORY_WEIGHTS["formatting"] * 0.7:
        strengths.append("Resume follows a clear, ATS-friendly section structure.")
    else:
        weaknesses.append(
            "Resume is missing standard sections (e.g., Summary, Projects, Certifications), which can confuse ATS parsers."
        )

    return strengths, weaknesses

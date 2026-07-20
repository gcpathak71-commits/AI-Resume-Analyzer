"""
app/recommender.py
-------------------
Job role recommendation engine.

v1 blended a skill-overlap percentage with TF-IDF cosine similarity between
the candidate's *skill list* and each role's *required-skills list* — a
purely lexical comparison that misses relevance when a resume describes
the same competency in different words than the taxonomy uses.

v2 used real sentence embeddings (sentence-transformers, all-MiniLM-L6-v2)
for the textual-similarity half of the blend. That's more semantically
accurate, but sentence-transformers pulls in PyTorch, which alone is
several hundred MB and routinely blows the disk/RAM budget on free-tier
hosts like Render's free plan (512MB RAM, small build disk quota).

v3 (this version) goes back to a pure scikit-learn TF-IDF + cosine
similarity comparison between the resume's full text and each role's
description + required skills. It's lexical rather than semantic, but it
is dramatically lighter (scikit-learn/numpy/pandas are already required
dependencies elsewhere in the app), needs no model download, and starts
instantly — which matters a lot on a memory-constrained free instance.

Skill overlap is still computed and still weighted the most heavily,
since "you have 7 of 10 required skills" remains the most interpretable,
trustworthy signal for the user — TF-IDF similarity adds a secondary
signal on top rather than replacing interpretability entirely.
"""

from typing import List

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# How much weight skill overlap vs. TF-IDF textual similarity gets in the
# final blended match percentage.
OVERLAP_WEIGHT = 0.55
SIMILARITY_WEIGHT = 0.45

# Resumes can be long; capping keeps the vectorizer focused on the most
# information-dense part of the resume (top: summary/skills/recent
# experience) rather than diluting the vector with the entire document.
MAX_RESUME_CHARS_FOR_EMBEDDING = 3000

# TF-IDF cosine similarity between short documents rarely gets close to 1.0
# the way normalized sentence-embedding similarity does, so this rescales
# the raw score into a more useful 0-100 display range. Tune if roles.csv
# grows a lot or descriptions get much longer/shorter.
SIMILARITY_RESCALE_CEILING = 0.30


class JobRecommender:
    """Ranks job roles against a candidate's resume using a blend of skill
    overlap and TF-IDF textual similarity."""

    def __init__(self, roles_csv_path: str) -> None:
        """
        Args:
            roles_csv_path: path to data/roles.csv.
        """
        self.roles_df = pd.read_csv(roles_csv_path)
        self._role_required_skills: List[List[str]] = [
            [skill.strip() for skill in str(row["required_skills"]).split(",") if skill.strip()]
            for _, row in self.roles_df.iterrows()
        ]
        # Precompute the role TF-IDF matrix once at startup — roles.csv is
        # static, so there's no reason to refit the vectorizer per request.
        role_corpora = [
            f"{row['description']} Required skills: {row['required_skills']}"
            for _, row in self.roles_df.iterrows()
        ]
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
        self._role_vectors = self.vectorizer.fit_transform(role_corpora)

    def recommend_roles(self, detected_skills: List[dict], resume_text: str) -> List[dict]:
        """
        Rank every role in roles.csv against the candidate.

        Args:
            detected_skills: output of SkillMatcher.match(), each item
                shaped like {"skill", "category", "weight", ...}.
            resume_text: the full raw resume text (used for the textual
                similarity signal).

        Returns:
            list[dict]: one entry per role, shaped to match the RoleMatch
                schema, sorted by match_percentage descending.
        """
        detected_names_lower = {skill["skill"].lower() for skill in detected_skills}

        resume_vector = self.vectorizer.transform([resume_text[:MAX_RESUME_CHARS_FOR_EMBEDDING]])
        similarity_scores = cosine_similarity(resume_vector, self._role_vectors).flatten()
        similarity_scores = np.clip(similarity_scores / SIMILARITY_RESCALE_CEILING, 0.0, 1.0) * 100

        results: List[dict] = []
        for index, role in self.roles_df.iterrows():
            required_skills = self._role_required_skills[index]
            matched_skills = [skill for skill in required_skills if skill.lower() in detected_names_lower]
            missing_skills = [skill for skill in required_skills if skill.lower() not in detected_names_lower]

            overlap_score = (len(matched_skills) / len(required_skills) * 100) if required_skills else 0.0
            similarity_score = float(similarity_scores[index])
            match_percentage = round(
                (overlap_score * OVERLAP_WEIGHT) + (similarity_score * SIMILARITY_WEIGHT), 2
            )

            results.append(
                {
                    "role_name": role["role_name"],
                    "description": role["description"],
                    "matched_skills": matched_skills,
                    "missing_skills": missing_skills,
                    "min_experience_years": int(role["min_experience_years"]),
                    "overlap_score": round(overlap_score, 2),
                    "similarity_score": round(similarity_score, 2),
                    "match_percentage": match_percentage,
                }
            )

        results.sort(key=lambda item: item["match_percentage"], reverse=True)
        return results

"""
app/skill_matcher.py
---------------------
Detects technical/soft skills in resume text against the master taxonomy
in data/skills.csv, replacing v1's plain regex substring matching with a
two-stage pipeline that is both more accurate and typo-tolerant:

  Stage 1 — spaCy PhraseMatcher (exact / alias matches):
      Every skill name and alias from skills.csv is compiled into a
      PhraseMatcher pattern. This correctly handles multi-word skills
      ("Natural Language Processing") and phrasing variants ("scikit
      learn" vs "Scikit-learn") using spaCy's tokenizer rather than
      fragile regex word-boundary hacks.

  Stage 2 — rapidfuzz fuzzy matching (typo-tolerant):
      Skills NOT found by the exact matcher are checked against every
      unigram/bigram phrase in the resume using rapidfuzz's fuzzy string
      scoring, so minor misspellings ("Pyhton", "TensorFlow2") still
      register — with a lower confidence score than an exact hit.

Every detected skill carries a `confidence` (0-1) and `match_type`
("exact" | "alias" | "fuzzy") so the frontend/report can be transparent
about match quality rather than presenting every hit as equally certain.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

import pandas as pd
from rapidfuzz import fuzz, process
from spacy.matcher import PhraseMatcher

FUZZY_SCORE_CUTOFF = 85  # rapidfuzz score (0-100) below which a fuzzy hit is discarded
MAX_MISSING_SKILLS = 15  # cap so the UI/report stay readable
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9\+\#\.]+")


class SkillMatcher:
    """Loads the skills taxonomy once and matches resume text against it."""

    def __init__(self, skills_csv_path: str, nlp) -> None:
        """
        Args:
            skills_csv_path: path to data/skills.csv.
            nlp: a loaded spaCy Language pipeline (shared across the app).
        """
        self.nlp = nlp
        self.skills_df = pd.read_csv(skills_csv_path)
        self._term_to_skill: Dict[str, dict] = {}
        self.matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
        self._build_patterns()

    def _build_patterns(self) -> None:
        """Compile every skill name + alias into PhraseMatcher patterns,
        and build a lookup table from lowercased term -> skill metadata
        (used both to resolve matcher hits and to drive fuzzy matching)."""
        for _, row in self.skills_df.iterrows():
            skill_name = str(row["skill_name"])
            category = str(row["category"])
            weight = int(row["weight"])
            aliases = str(row["aliases"]) if pd.notna(row["aliases"]) else ""

            terms = [skill_name] + [alias.strip() for alias in aliases.split(",") if alias.strip()]
            patterns = []
            for term in terms:
                term_lower = term.lower()
                self._term_to_skill[term_lower] = {
                    "skill": skill_name,
                    "category": category,
                    "weight": weight,
                    "is_canonical": term_lower == skill_name.lower(),
                }
                patterns.append(self.nlp.make_doc(term_lower))

            self.matcher.add(skill_name, patterns)

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------
    def match(self, text: str) -> Tuple[List[dict], List[dict]]:
        """
        Detect every skill present in the given resume text.

        Returns:
            tuple:
                detected_skills (list[dict]): each shaped like
                    {"skill", "category", "weight", "confidence", "match_type"}
                missing_skills (list[dict]): non-soft-skill entries from the
                    taxonomy that were NOT detected, sorted by weight
                    descending and capped at MAX_MISSING_SKILLS.
        """
        doc = self.nlp(text)
        detected_by_skill: Dict[str, dict] = {}

        # Stage 1: exact / alias matches via PhraseMatcher
        for match_id, start, end in self.matcher(doc):
            span_text = doc[start:end].text.lower()
            meta = self._term_to_skill.get(span_text)
            if meta is None:
                continue
            skill_name = meta["skill"]
            match_type = "exact" if meta["is_canonical"] else "alias"
            confidence = 1.0 if match_type == "exact" else 0.92

            existing = detected_by_skill.get(skill_name)
            if existing is None or confidence > existing["confidence"]:
                detected_by_skill[skill_name] = {
                    "skill": skill_name,
                    "category": meta["category"],
                    "weight": meta["weight"],
                    "confidence": confidence,
                    "match_type": match_type,
                }

        # Stage 2: fuzzy matching for everything the exact stage missed
        remaining_rows = self.skills_df[~self.skills_df["skill_name"].isin(detected_by_skill.keys())]
        if not remaining_rows.empty:
            candidate_phrases = self._build_candidate_phrases(text)
            if candidate_phrases:
                self._fuzzy_match_remaining(remaining_rows, candidate_phrases, detected_by_skill)

        detected_skills = sorted(detected_by_skill.values(), key=lambda item: (-item["weight"], item["skill"]))
        missing_skills = self._build_missing_skills(detected_by_skill)

        return detected_skills, missing_skills

    # ------------------------------------------------------------------
    # INTERNAL HELPERS
    # ------------------------------------------------------------------
    def _build_candidate_phrases(self, text: str) -> List[str]:
        """Build a deduplicated list of unigram + bigram phrases from the
        resume text to serve as the fuzzy-matching candidate pool. Using
        n-grams (rather than fuzzy-scanning the raw text directly) keeps
        the rapidfuzz comparison fast and focused on plausible skill-length
        phrases."""
        tokens = TOKEN_PATTERN.findall(text.lower())
        if not tokens:
            return []

        unigrams = set(tokens)
        bigrams = {f"{tokens[i]} {tokens[i + 1]}" for i in range(len(tokens) - 1)}
        # Filter out very short noise tokens that would fuzzy-match everything
        return [phrase for phrase in (unigrams | bigrams) if len(phrase) >= 3]

    def _fuzzy_match_remaining(
        self, remaining_rows: pd.DataFrame, candidate_phrases: List[str], detected_by_skill: Dict[str, dict]
    ) -> None:
        for _, row in remaining_rows.iterrows():
            skill_name = str(row["skill_name"])
            category = str(row["category"])
            weight = int(row["weight"])
            aliases = str(row["aliases"]) if pd.notna(row["aliases"]) else ""
            terms = [skill_name] + [alias.strip() for alias in aliases.split(",") if alias.strip()]

            best_score = 0.0
            for term in terms:
                result = process.extractOne(
                    term.lower(), candidate_phrases, scorer=fuzz.WRatio, score_cutoff=FUZZY_SCORE_CUTOFF
                )
                if result is not None:
                    _, score, _ = result
                    best_score = max(best_score, score)

            if best_score > 0:
                detected_by_skill[skill_name] = {
                    "skill": skill_name,
                    "category": category,
                    "weight": weight,
                    "confidence": round(best_score / 100, 2),
                    "match_type": "fuzzy",
                }

    def _build_missing_skills(self, detected_by_skill: Dict[str, dict]) -> List[dict]:
        candidates: List[dict] = []
        for _, row in self.skills_df.iterrows():
            skill_name = str(row["skill_name"])
            category = str(row["category"])
            if skill_name in detected_by_skill or category == "Soft Skill":
                continue
            candidates.append({"skill": skill_name, "category": category, "weight": int(row["weight"])})

        candidates.sort(key=lambda item: item["weight"], reverse=True)
        return candidates[:MAX_MISSING_SKILLS]

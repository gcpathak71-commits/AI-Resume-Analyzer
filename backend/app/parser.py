"""
app/parser.py
-------------
Resume PDF ingestion and structural extraction.

Responsible for turning an uploaded PDF into: contact details, name,
education, structured experience date-ranges (with real duration math),
project/certification counts, and a layout-aware section map.

Skill detection itself lives in skill_matcher.py — this module only
extracts raw text, layout metadata, and non-skill structured fields.

Layout-aware section detection: pdfplumber exposes each character's font
size and font name. A resume's section headings are almost always larger
and/or bolder than the surrounding body text, so instead of only matching
keyword phrases anywhere in the text (which false-positives on sentences
like "monitored production experience"), we first identify heading-sized
lines and only classify a section as "present" when a keyword appears on
one of those heading lines. We fall back to plain keyword scanning if
layout extraction yields no usable font metadata (some PDF generators
strip font info entirely).
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from datetime import date
from typing import BinaryIO, Dict, List, Optional, Tuple, Union

from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta


# ----------------------------------------------------------------------
# STATIC REFERENCE DATA
# ----------------------------------------------------------------------
EDUCATION_KEYWORDS = [
    "b.tech", "btech", "bachelor of technology",
    "m.tech", "mtech", "master of technology",
    "b.e", "bachelor of engineering",
    "m.e", "master of engineering",
    "bachelor", "master", "b.sc", "bsc", "m.sc", "msc",
    "mba", "bba", "phd", "ph.d", "doctorate",
    "diploma", "high school", "intermediate", "12th", "10th",
]

SECTION_KEYWORDS: Dict[str, List[str]] = {
    "education": ["education", "academic background", "qualification", "academics"],
    "experience": ["experience", "work history", "employment", "work experience", "professional experience"],
    "skills": ["skills", "technical skills", "core competencies", "skill set"],
    "projects": ["projects", "academic projects", "personal projects", "key projects"],
    "certifications": ["certifications", "certificates", "licenses", "certification"],
    "summary": ["summary", "objective", "profile", "professional summary"],
}

# Matches ranges like: "Jan 2022 - Present", "2021-2023", "March 2020 to June 2021"
DATE_RANGE_PATTERN = re.compile(
    r"(?P<start>(?:[A-Za-z]{3,9}\.?\s+\d{4})|\d{4})"
    r"\s*(?:-|–|—|to)\s*"
    r"(?P<end>(?:[A-Za-z]{3,9}\.?\s+\d{4})|\d{4}|present|current|ongoing)",
    re.IGNORECASE,
)

FALLBACK_YEARS_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*\+?\s*years?", re.IGNORECASE)


@dataclass
class LineInfo:
    """A single visual line of text with layout metadata."""

    text: str
    page: int
    top: float
    avg_size: float
    is_bold: bool


@dataclass
class ExperienceEntry:
    raw_text: str
    start_date: Optional[date]
    end_date: Optional[date]
    is_current: bool
    months: float


class ResumeParser:
    """Encapsulates all non-skill resume parsing logic."""

    def __init__(self, nlp) -> None:
        """
        Args:
            nlp: A loaded spaCy Language pipeline, used only for PERSON
                named-entity recognition to guess the candidate's name.
        """
        self.nlp = nlp

    # ------------------------------------------------------------------
    # PDF TEXT + LAYOUT EXTRACTION
    # ------------------------------------------------------------------
    def extract_text_and_lines(self, file: Union[str, BinaryIO]) -> Tuple[str, List[LineInfo]]:
        """
        Extract both plain text (for regex-based extraction) and a list of
        layout-annotated lines (for heading detection) from a PDF.

        Raises:
            ValueError: if the PDF is corrupt, encrypted, or has no
                extractable text (e.g. a scanned image-only PDF).
        """
        import pdfplumber  # imported here to keep module import fast for testing

        text_chunks: List[str] = []
        lines: List[LineInfo] = []

        try:
            with pdfplumber.open(file) as pdf:
                if len(pdf.pages) == 0:
                    raise ValueError("The PDF has no pages.")

                for page_number, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text_chunks.append(page_text)

                    lines.extend(self._extract_lines_from_page(page, page_number))
        except ValueError:
            raise
        except Exception as error:  # pdfplumber/pdfminer can raise many error types
            raise ValueError(
                "This PDF could not be read. It may be corrupted, password-protected, "
                "or in an unsupported format."
            ) from error

        full_text = "\n".join(text_chunks)

        if not full_text.strip():
            raise ValueError(
                "No extractable text was found in this PDF. It may be a scanned "
                "image — please upload a text-based (not scanned) PDF."
            )

        return full_text, lines

    def _extract_lines_from_page(self, page, page_number: int) -> List[LineInfo]:
        """Group a page's characters into visual lines and compute each
        line's average font size and whether it looks bold, using
        pdfplumber's character-level layout data."""
        chars = page.chars
        if not chars:
            return []

        # Group characters into lines by rounding their vertical position.
        # pdfplumber's 'top' is the distance from the top of the page.
        buckets: Dict[int, List[dict]] = {}
        for char in chars:
            bucket_key = round(char["top"])
            buckets.setdefault(bucket_key, []).append(char)

        lines: List[LineInfo] = []
        for top_key in sorted(buckets.keys()):
            row_chars = sorted(buckets[top_key], key=lambda c: c["x0"])
            text = "".join(c["text"] for c in row_chars).strip()
            if not text:
                continue

            sizes = [c.get("size", 0) for c in row_chars if c.get("size")]
            avg_size = statistics.mean(sizes) if sizes else 0.0
            bold_count = sum(1 for c in row_chars if "bold" in c.get("fontname", "").lower())
            is_bold = bold_count > len(row_chars) * 0.5

            lines.append(
                LineInfo(text=text, page=page_number, top=float(top_key), avg_size=avg_size, is_bold=is_bold)
            )

        return lines

    # ------------------------------------------------------------------
    # LAYOUT-AWARE SECTION DETECTION
    # ------------------------------------------------------------------
    def detect_sections(self, full_text: str, lines: List[LineInfo]) -> Dict[str, str]:
        """
        Slice the resume into named sections using font-size/bold heading
        detection when layout data is available, falling back to plain
        keyword-line scanning on the raw text otherwise.

        Returns:
            dict: section_name -> the text content belonging to that section
                (empty string if not found).
        """
        heading_indices = self._find_heading_lines(lines)

        if heading_indices:
            return self._slice_by_layout_headings(lines, heading_indices)

        return self._slice_by_keyword_fallback(full_text)

    def _find_heading_lines(self, lines: List[LineInfo]) -> List[Tuple[int, str]]:
        """Identify which lines are likely section headings: short lines
        that are meaningfully larger and/or bolder than the resume's
        typical body text, and whose text matches a known section keyword."""
        if not lines:
            return []

        body_sizes = [line.avg_size for line in lines if line.avg_size > 0]
        if not body_sizes:
            return []

        median_size = statistics.median(body_sizes)
        heading_indices: List[Tuple[int, str]] = []

        for index, line in enumerate(lines):
            cleaned = line.text.strip().lower().rstrip(":")
            if len(cleaned.split()) > 5:
                continue  # headings are short

            looks_like_heading = line.avg_size >= median_size * 1.12 or line.is_bold
            if not looks_like_heading:
                continue

            for section, keywords in SECTION_KEYWORDS.items():
                if any(cleaned == kw or cleaned.startswith(kw) for kw in keywords):
                    heading_indices.append((index, section))
                    break

        return heading_indices

    def _slice_by_layout_headings(
        self, lines: List[LineInfo], heading_indices: List[Tuple[int, str]]
    ) -> Dict[str, str]:
        sections = {name: "" for name in SECTION_KEYWORDS}
        for position, (line_index, section_name) in enumerate(heading_indices):
            start = line_index + 1
            end = heading_indices[position + 1][0] if position + 1 < len(heading_indices) else len(lines)
            content = "\n".join(lines[i].text for i in range(start, end))
            # If a section keyword appears more than once, keep the longer match
            if len(content) > len(sections[section_name]):
                sections[section_name] = content
        return sections

    def _slice_by_keyword_fallback(self, full_text: str) -> Dict[str, str]:
        """Plain keyword-on-line scanning, used when a PDF has no usable
        font metadata (rare, but happens with some PDF generators)."""
        text_lines = full_text.splitlines()
        sections = {name: "" for name in SECTION_KEYWORDS}

        for section_name, keywords in SECTION_KEYWORDS.items():
            start_index = None
            for index, line in enumerate(text_lines):
                cleaned = line.strip().lower().rstrip(":")
                if any(cleaned == kw or cleaned.startswith(kw) for kw in keywords):
                    start_index = index + 1
                    break
            if start_index is None:
                continue

            end_index = len(text_lines)
            for index in range(start_index, len(text_lines)):
                line = text_lines[index].strip()
                if line and len(line.split()) <= 4 and line.isupper():
                    end_index = index
                    break

            sections[section_name] = "\n".join(text_lines[start_index:end_index])

        return sections

    # ------------------------------------------------------------------
    # CONTACT + NAME EXTRACTION
    # ------------------------------------------------------------------
    def extract_name(self, text: str) -> str:
        doc = self.nlp(text[:2000])  # NER only needs the header area; keeps this fast
        for entity in doc.ents:
            if entity.label_ == "PERSON":
                candidate = entity.text.strip()
                if 1 <= len(candidate.split()) <= 4:
                    return candidate

        for line in text.splitlines():
            stripped = line.strip()
            if stripped and len(stripped.split()) <= 4 and not any(char.isdigit() for char in stripped):
                return stripped

        return "Not Detected"

    def extract_email(self, text: str) -> str:
        match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
        return match.group(0) if match else "Not Detected"

    def extract_phone(self, text: str) -> str:
        match = re.search(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3,5}\)?[-.\s]?\d{3}[-.\s]?\d{3,4}", text)
        return match.group(0).strip() if match else "Not Detected"

    # ------------------------------------------------------------------
    # EDUCATION
    # ------------------------------------------------------------------
    def extract_education(self, text: str) -> List[str]:
        lowered = text.lower()
        found: List[str] = []
        for keyword in EDUCATION_KEYWORDS:
            if keyword in lowered and keyword not in found:
                found.append(keyword)
        return found

    # ------------------------------------------------------------------
    # EXPERIENCE (real date-range parsing)
    # ------------------------------------------------------------------
    def extract_experience(self, text: str) -> Tuple[float, List[ExperienceEntry]]:
        """
        Find date ranges (e.g. "Jan 2022 - Present") anywhere in the resume
        and compute real elapsed months for each, using python-dateutil for
        robust natural-language date parsing. Overlapping ranges are merged
        so concurrent roles aren't double-counted. Falls back to matching
        phrases like "3 years of experience" if no date ranges are found.
        """
        entries: List[ExperienceEntry] = []
        intervals: List[Tuple[date, date]] = []
        today = date.today()

        for match in DATE_RANGE_PATTERN.finditer(text):
            raw = match.group(0)
            start_text = match.group("start")
            end_text = match.group("end")

            start_dt = self._safe_parse_date(start_text)
            if start_dt is None:
                continue

            is_current = end_text.strip().lower() in {"present", "current", "ongoing"}
            end_dt = today if is_current else self._safe_parse_date(end_text)
            if end_dt is None:
                continue

            if end_dt < start_dt:
                continue  # nonsensical range, skip rather than guess

            months = self._months_between(start_dt, end_dt)
            entries.append(
                ExperienceEntry(
                    raw_text=raw, start_date=start_dt, end_date=end_dt, is_current=is_current, months=months
                )
            )
            intervals.append((start_dt, end_dt))

        if intervals:
            total_months = self._merge_and_sum_months(intervals)
            return round(total_months / 12, 2), entries

        # Fallback: no parseable date ranges found at all
        fallback_matches = FALLBACK_YEARS_PATTERN.findall(text.lower())
        fallback_years = [float(value) for value in fallback_matches if float(value) < 40]
        return (max(fallback_years) if fallback_years else 0.0), entries

    def _safe_parse_date(self, text: str) -> Optional[date]:
        cleaned = text.strip().rstrip(".")
        try:
            # default to the 1st of the month when only a month+year is given
            return date_parser.parse(cleaned, default=date(2000, 1, 1)).date()
        except (ValueError, OverflowError):
            return None

    def _months_between(self, start: date, end: date) -> float:
        delta = relativedelta(end, start)
        return round(delta.years * 12 + delta.months + (delta.days / 30), 2)

    def _merge_and_sum_months(self, intervals: List[Tuple[date, date]]) -> float:
        """Merge overlapping date intervals before summing, so two jobs
        held concurrently (or an internship inside a longer role) aren't
        counted as separate additive experience."""
        sorted_intervals = sorted(intervals, key=lambda pair: pair[0])
        merged: List[Tuple[date, date]] = []

        for start, end in sorted_intervals:
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))

        return sum(self._months_between(start, end) for start, end in merged)

    # ------------------------------------------------------------------
    # PROJECTS / CERTIFICATIONS COUNTS
    # ------------------------------------------------------------------
    def count_bullet_items(self, section_text: str) -> int:
        """Count list-like items in a section: bullet-prefixed lines if
        present, otherwise every non-empty line as a rough proxy."""
        if not section_text.strip():
            return 0
        bullet_lines = re.findall(r"^[ \t]*[•\-\*▪‣]\s+.+", section_text, flags=re.MULTILINE)
        if bullet_lines:
            return len(bullet_lines)
        return len([line for line in section_text.splitlines() if line.strip()])

    # ------------------------------------------------------------------
    # MASTER PARSE METHOD
    # ------------------------------------------------------------------
    def parse(self, file: Union[str, BinaryIO]) -> dict:
        """
        Run the full non-skill extraction pipeline on an uploaded PDF.

        Returns:
            dict with keys: name, email, phone, education, experience_years,
            experience_entries, projects_count, certifications_count,
            sections_present, word_count, raw_text, sections (raw section
            text, used by skill_matcher/ats for section-scoped analysis).
        """
        full_text, lines = self.extract_text_and_lines(file)
        sections = self.detect_sections(full_text, lines)

        experience_years, experience_entries = self.extract_experience(full_text)
        email = self.extract_email(full_text)
        phone = self.extract_phone(full_text)

        sections_present = {name: bool(content.strip()) for name, content in sections.items()}
        # A section can be "present" even with empty sliced content if it's
        # the resume's final section (nothing follows it to slice against) —
        # re-check headings directly to catch that edge case.
        if not any(sections_present.values()) and lines:
            heading_names = {name for _, name in self._find_heading_lines(lines)}
            for name in heading_names:
                sections_present[name] = True
        sections_present["contact_info"] = email != "Not Detected" or phone != "Not Detected"

        return {
            "name": self.extract_name(full_text),
            "email": email,
            "phone": phone,
            "education": self.extract_education(full_text),
            "experience_years": experience_years,
            "experience_entries": experience_entries,
            "projects_count": self.count_bullet_items(sections.get("projects", "")),
            "certifications_count": self.count_bullet_items(sections.get("certifications", "")),
            "sections_present": sections_present,
            "word_count": len(full_text.split()),
            "raw_text": full_text,
            "sections": sections,
        }

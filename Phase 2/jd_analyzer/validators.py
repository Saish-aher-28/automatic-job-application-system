"""
validators.py — Input validation and output normalization for Phase 2.

validate_jd_input()   — checks raw JD text before sending to Gemini.
normalize_analysis()  — deduplicates and normalizes the structured output.
"""

from __future__ import annotations

import re
from typing import List

from phase_2.jd_analyzer.config import config
from phase_2.jd_analyzer.schemas import JDAnalysis


# ────────────────────────────────────────────────────────────────────────────
# JD input validation
# ────────────────────────────────────────────────────────────────────────────

class JDValidationError(ValueError):
    """Raised when the raw JD input is invalid."""


def validate_jd_input(text: str) -> str:
    """
    Validate raw JD text before sending to Gemini.

    Returns the stripped text if valid.
    Raises JDValidationError with a clear message if not.
    """
    if not isinstance(text, str):
        raise JDValidationError("JD input must be a string.")

    stripped = text.strip()

    if not stripped:
        raise JDValidationError(
            "JD input cannot be empty. Please provide a job description."
        )

    if len(stripped) < config.MIN_JD_LENGTH:
        raise JDValidationError(
            f"JD input is too short ({len(stripped)} chars). "
            f"Minimum is {config.MIN_JD_LENGTH} characters."
        )

    if len(stripped) > config.MAX_JD_LENGTH:
        raise JDValidationError(
            f"JD input is too long ({len(stripped)} chars). "
            f"Maximum is {config.MAX_JD_LENGTH} characters."
        )

    return stripped


# ────────────────────────────────────────────────────────────────────────────
# Normalization helpers
# ────────────────────────────────────────────────────────────────────────────

# Known equivalent technology names → canonical form
_TECH_ALIASES: dict[str, str] = {
    "react.js":           "React",
    "reactjs":            "React",
    "react js":           "React",
    "node.js":            "Node.js",
    "nodejs":             "Node.js",
    "amazon web services": "AWS",
    "restful api":        "REST API",
    "restful apis":       "REST APIs",
    "rest apis":          "REST APIs",
    "rest api":           "REST API",
    "postgresql":         "PostgreSQL",
    "postgres":           "PostgreSQL",
    "mongo db":           "MongoDB",
    "k8s":                "Kubernetes",
    "js":                 "JavaScript",
    "ts":                 "TypeScript",
    "py":                 "Python",
    "ml":                 "Machine Learning",
    "dl":                 "Deep Learning",
    "ci/cd":              "CI/CD",
    "cicd":               "CI/CD",
    "tensorflow 2":       "TensorFlow",
    "tf":                 "TensorFlow",
    "scikit learn":       "Scikit-learn",
    "sklearn":            "Scikit-learn",
}


def _normalize_tech(name: str) -> str:
    """Return the canonical name for a technology string."""
    key = name.lower().strip()
    return _TECH_ALIASES.get(key, name.strip())


def _dedup_preserve_order(items: List[str]) -> List[str]:
    """Remove duplicates (case-insensitive) while preserving first-seen order."""
    seen: set[str] = set()
    result: List[str] = []
    for item in items:
        key = item.lower().strip()
        if key and key not in seen:
            seen.add(key)
            result.append(item.strip())
    return result


def normalize_analysis(analysis: JDAnalysis) -> JDAnalysis:
    """
    Post-process a JDAnalysis object:
    - Normalize tech aliases in skills/technologies.
    - Deduplicate all list fields (case-insensitive, order-preserving).
    - Strip whitespace from string values.
    """
    def _norm_list(items: List[str]) -> List[str]:
        return _dedup_preserve_order([_normalize_tech(i) for i in items])

    return JDAnalysis(
        job_title=analysis.job_title,
        company=analysis.company,
        role_category=analysis.role_category,
        experience_level=analysis.experience_level,
        employment_type=analysis.employment_type,
        location=analysis.location,
        required_skills=_norm_list(analysis.required_skills),
        preferred_skills=_norm_list(analysis.preferred_skills),
        technologies=_norm_list(analysis.technologies),
        responsibilities=_dedup_preserve_order(analysis.responsibilities),
        education_requirements=_dedup_preserve_order(analysis.education_requirements),
        experience_requirements=_dedup_preserve_order(analysis.experience_requirements),
        keywords=_dedup_preserve_order(
            [kw.lower().strip() for kw in analysis.keywords]
        ),
    )

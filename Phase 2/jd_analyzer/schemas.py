"""
schemas.py — Pydantic models for Phase 2 JD Analysis.

JDAnalysis is the canonical structured output for any analyzed job description.
FirestoreJDDocument is the full record stored in Firestore.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class JDAnalysis(BaseModel):
    """
    Structured representation of a parsed job description.

    All string fields default to None when not mentioned in the JD.
    All list fields default to [] when not mentioned in the JD.
    The model must NOT invent values not supported by the source JD.
    """

    # ── Metadata ─────────────────────────────────────────────────────────────
    job_title:          Optional[str] = Field(None, description="Exact job title from JD")
    company:            Optional[str] = Field(None, description="Company name if explicitly stated")
    role_category:      Optional[str] = Field(None, description="High-level category: Backend, Frontend, ML, etc.")
    experience_level:   Optional[str] = Field(None, description="Entry Level, Mid Level, Senior, etc.")
    employment_type:    Optional[str] = Field(None, description="Full-time, Part-time, Contract, Internship")
    location:           Optional[str] = Field(None, description="Location if explicitly stated")

    # ── Skills ────────────────────────────────────────────────────────────────
    required_skills:    List[str] = Field(default_factory=list, description="Mandatory/essential skills")
    preferred_skills:   List[str] = Field(default_factory=list, description="Nice-to-have / preferred skills")

    # ── Technical ─────────────────────────────────────────────────────────────
    technologies:       List[str] = Field(default_factory=list, description="All explicit technical tools and frameworks")

    # ── Role details ──────────────────────────────────────────────────────────
    responsibilities:         List[str] = Field(default_factory=list)
    education_requirements:   List[str] = Field(default_factory=list)
    experience_requirements:  List[str] = Field(default_factory=list)
    keywords:                 List[str] = Field(default_factory=list)

    @field_validator(
        "required_skills", "preferred_skills", "technologies",
        "responsibilities", "education_requirements",
        "experience_requirements", "keywords",
        mode="before",
    )
    @classmethod
    def coerce_list(cls, v):
        """Accept None → [], str → [str], or pass-through lists."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v.strip() else []
        return v

    @field_validator(
        "job_title", "company", "role_category",
        "experience_level", "employment_type", "location",
        mode="before",
    )
    @classmethod
    def coerce_empty_string(cls, v):
        """Convert empty strings to None."""
        if isinstance(v, str) and not v.strip():
            return None
        return v

    model_config = {"str_strip_whitespace": True}


class FirestoreJDDocument(BaseModel):
    """Full Firestore document structure for a saved JD analysis."""

    raw_text:         str
    analysis:         JDAnalysis
    model:            str
    created_at:       str          # ISO-8601 string (server time on read, local on write)
    analysis_version: str = "1.0"

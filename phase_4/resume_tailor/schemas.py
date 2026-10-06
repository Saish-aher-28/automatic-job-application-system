"""
schemas.py — Pydantic models for Phase 4 Resume Tailoring.

TailoringPlan:       Structured output from Gemini (or deterministic fallback).
TailoredResumeResult: Final result returned by the pipeline.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class TailoringPlan(BaseModel):
    """
    Gemini-produced tailoring plan.

    Contains ONLY data-driven instructions — never raw LaTeX or fabricated content.
    All fields must reference information already present in the user's real profile.
    """

    summary_focus: List[str] = Field(
        default_factory=list,
        description=(
            "Existing skills/technologies from the real profile to emphasize "
            "in the summary. Must be a subset of actual profile skills."
        ),
    )
    skills_to_emphasize: List[str] = Field(
        default_factory=list,
        description=(
            "Existing skills (from Firestore) to move to the front of their "
            "category. Must be a strict subset of the user's actual skills."
        ),
    )
    project_ids: List[str] = Field(
        default_factory=list,
        description=(
            "Firestore _id values of the selected projects, ordered by relevance. "
            "Must be IDs from Phase 3 ranked_projects only."
        ),
    )
    tailoring_notes: str = Field(
        default="",
        description="Short human-readable explanation of the tailoring decisions.",
    )


class TailoredResumeResult(BaseModel):
    """Full result returned by the Phase 4 pipeline."""

    resume_id: str = Field(..., description="Firestore document ID of the saved result")
    match_id: str = Field(..., description="Phase 3 job_matches document ID (input)")
    jd_document_id: str = Field(..., description="Phase 2 job_descriptions document ID")
    job_title: str = Field(..., description="Job title from Phase 3 match result")

    selected_project_ids: List[str] = Field(
        default_factory=list,
        description="Firestore _id of each selected project",
    )
    selected_project_names: List[str] = Field(
        default_factory=list,
        description="Display names of selected projects (in selection order)",
    )
    emphasized_skills: List[str] = Field(
        default_factory=list,
        description="Skills that were moved to the front of their categories",
    )

    page_count: Optional[int] = Field(
        None, description="Final PDF page count (None if compilation failed)"
    )
    tex_path: str = Field(..., description="Absolute path to generated .tex file")
    pdf_path: Optional[str] = Field(
        None, description="Absolute path to generated .pdf (None if compilation failed)"
    )

    generation_status: str = Field(
        ...,
        description="'success' | 'partial' | 'failed'",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Non-fatal warnings encountered during generation",
    )

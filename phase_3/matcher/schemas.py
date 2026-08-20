"""
schemas.py — Pydantic models for Phase 3 matching result.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class ProjectMatchDetail(BaseModel):
    """Relevance and mapping details for a single candidate project."""

    project_id:              str = Field(..., description="Firestore document ID of the project")
    project_name:            str = Field(..., description="Display name of the project")
    preliminary_score:       float = Field(..., ge=0.0, le=100.0, description="Stage 1 deterministic score")
    semantic_score:          Optional[float] = Field(None, ge=0.0, le=100.0, description="Stage 2 Gemini semantic score")
    final_project_score:     float = Field(..., ge=0.0, le=100.0, description="Final combined project score")
    matched_skills:          List[str] = Field(default_factory=list, description="Required/preferred skills matches")
    matched_technologies:    List[str] = Field(default_factory=list, description="Matched technology names")
    missing_relevant_skills: List[str] = Field(default_factory=list, description="JD required/preferred skills missing in project")
    reason:                  str = Field(..., description="Explanation text for this project's ranking")


class JobMatchResult(BaseModel):
    """Overall Job ↔ User Profile match result schema."""

    jd_document_id:              str = Field(..., description="Firestore document ID of the analyzed JD")
    job_title:                   str = Field(..., description="Job title extracted from the JD")
    overall_match_score:         float = Field(..., ge=0.0, le=100.0, description="Weighted final match score")
    required_skill_match_score:  float = Field(..., ge=0.0, le=100.0, description="Required skill match score percentage")
    preferred_skill_match_score: float = Field(..., ge=0.0, le=100.0, description="Preferred skill match score percentage")
    technology_match_score:      float = Field(..., ge=0.0, le=100.0, description="Technology match score percentage")
    project_relevance_score:     float = Field(..., ge=0.0, le=100.0, description="Calculated project score (average of top matches)")
    matched_required_skills:     List[str] = Field(default_factory=list, description="User skills matching required JD skills")
    missing_required_skills:     List[str] = Field(default_factory=list, description="Required JD skills missing in user profile")
    matched_preferred_skills:    List[str] = Field(default_factory=list, description="User skills matching preferred JD skills")
    missing_preferred_skills:    List[str] = Field(default_factory=list, description="Preferred JD skills missing in user profile")
    matched_technologies:        List[str] = Field(default_factory=list, description="Technologies matching JD technologies")
    missing_technologies:        List[str] = Field(default_factory=list, description="Technologies requested in JD but missing in user profile")
    ranked_projects:             List[ProjectMatchDetail] = Field(default_factory=list, description="Ranked list of all user projects")


class ProjectSemanticMatch(BaseModel):
    """Structured Pydantic model for Gemini response validation."""

    relevance_score:      float = Field(..., ge=0.0, le=100.0, description="Semantic score from 0 to 100")
    matched_requirements: List[str] = Field(..., description="Requirements matched with evidence")
    supporting_evidence:  List[str] = Field(..., description="Evidence strings directly extracted from project details")
    missing_requirements: List[str] = Field(..., description="Requested requirements absent in project details")
    reason:               str = Field(..., description="Concise explanation for the assigned score")

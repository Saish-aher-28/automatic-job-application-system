"""
schemas.py — Pydantic model representing structured job extraction schema for Gemini.
"""

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class ExtractedJob(BaseModel):
    """
    Structured extraction of a job post from raw candidate text.
    All fields default to None or [] if they cannot be verified in the source.
    The model must NOT fabricate or infer URLs or info not present in the source text.

    content_type classifies the nature of the post:
      TRUE_JOB, ADVERTISEMENT, COURSE, CERTIFICATION, TRAINING, WEBINAR,
      EVENT, PROMOTION, OTHER.
    Only TRUE_JOB posts are ingested as opportunities.
    """

    content_type: Optional[str] = Field(
        None,
        description=(
            "Classification of this content. Must be exactly one of: "
            "TRUE_JOB, ADVERTISEMENT, COURSE, CERTIFICATION, TRAINING, "
            "WEBINAR, EVENT, PROMOTION, OTHER. "
            "Use TRUE_JOB only when the post is clearly a real open job position at a company."
        )
    )

    company: Optional[str] = Field(None, description="Company name hiring for the role")
    job_title: Optional[str] = Field(None, description="Job title of the open position")
    description: Optional[str] = Field(None, description="Detailed job description or summary of responsibilities")
    application_url: Optional[str] = Field(None, description="Apply URL or email address explicitly mentioned")
    
    location: Optional[str] = Field(None, description="Location of work (Remote, Hybrid, or city/country)")
    employment_type: Optional[str] = Field(None, description="Full-time, Part-time, Contract, Internship, Freelance")
    experience: Optional[str] = Field(None, description="Experience requirements mentioned (e.g., '2+ years')")
    salary: Optional[str] = Field(None, description="Salary or compensation package if mentioned")
    
    skills: List[str] = Field(default_factory=list, description="Extracted key skills requested (e.g. ['React', 'Machine Learning'])")
    technologies: List[str] = Field(default_factory=list, description="Extracted technologies, databases, tools, or frameworks")

    @field_validator("skills", "technologies", mode="before")
    @classmethod
    def coerce_list(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v.strip() else []
        return v

    @field_validator("company", "job_title", "application_url", "location", "employment_type", "experience", "salary", mode="before")
    @classmethod
    def coerce_empty_string(cls, v):
        if isinstance(v, str) and not v.strip():
            return None
        return v

    model_config = {"str_strip_whitespace": True}

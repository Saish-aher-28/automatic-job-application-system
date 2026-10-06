"""
opportunity.py — Pydantic model for JobOpportunity in Phase 6.
"""

from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class JobOpportunity(BaseModel):
    """
    Canonical representation of a discovered job opportunity from any source.
    """

    id: Optional[str] = Field(None, description="Firestore document ID")
    source: str = Field(..., description="E.g., telegram, website, etc.")
    source_type: str = Field(..., description="E.g., group, channel, static_crawl, dynamic_crawl")
    source_name: str = Field(..., description="Human readable name of the source")
    source_channel: Optional[str] = Field(None, description="Telegram channel identifier if applicable")
    source_message_id: Optional[int] = Field(None, description="Telegram message ID if applicable")
    source_url: Optional[str] = Field(None, description="Direct link to the job post or website listing")
    
    company: Optional[str] = Field(None, description="Company hiring for the position")
    job_title: Optional[str] = Field(None, description="Exact or parsed title of the job")
    description: Optional[str] = Field(None, description="Extracted role description")
    raw_text: str = Field(..., description="Original raw source text of the message/page")
    application_url: Optional[str] = Field(None, description="URL to apply for this job")
    
    location: Optional[str] = Field(None, description="Hiring location or Remote/Hybrid classification")
    employment_type: Optional[str] = Field(None, description="Full-time, Part-time, Contract, Internship")
    experience: Optional[str] = Field(None, description="Experience requirements or raw text description of it")
    salary: Optional[str] = Field(None, description="Offered compensation if listed")
    
    skills: List[str] = Field(default_factory=list, description="Extracted required skills")
    technologies: List[str] = Field(default_factory=list, description="Extracted technical tools/frameworks")
    
    posted_at: Optional[str] = Field(None, description="ISO-8601 string when the job was posted at the source")
    discovered_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="ISO-8601 timestamp of discovery")
    
    # ── Long-term deduplication index keys ──────────────────────────────────────
    # Stored as direct Firestore fields so each level can be queried with
    # a targeted where("field", "==", value).limit(1) instead of scanning docs.

    # L1: Normalized canonical application URL (trailing slashes, fragments, UTM stripped)
    canonical_url: Optional[str] = Field(None, description="Canonical normalized application URL for L1 dedup")
    # L2: Telegram message identity key — 'telegram:{channel}:{message_id}'
    telegram_message_key: Optional[str] = Field(None, description="Unique Telegram message identity key for L2 dedup")
    # L4: Normalized company+title+location identity key (MD5 hex)
    job_identity_key: Optional[str] = Field(None, description="Normalized company+title+location key for L4 dedup")
    # L3: Content hash (already exists, now also used for indexed query)
    content_hash: str = Field(..., description="SHA-256 hash of normalized company+title+description for L3 dedup")

    ingestion_status: str = Field("DISCOVERED", description="DISCOVERED, STORED, DUPLICATE, FAILED, IGNORED")
    is_duplicate: bool = Field(False, description="Flag representing if this is a duplicate of another opportunity")
    duplicate_of: Optional[str] = Field(None, description="ID of the canonical job opportunity if this is a duplicate")
    extraction_confidence: float = Field(1.0, description="Extraction confidence score (0.0 to 1.0)")
    
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

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

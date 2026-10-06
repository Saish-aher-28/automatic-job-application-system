"""
base.py — JobSource interface and RawJobItem model for Phase 6.
"""

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel


class RawJobItem(BaseModel):
    """
    Represents a raw job posting retrieved from a source before detection and extraction.
    """
    source: str
    source_type: str
    source_name: str
    source_url: Optional[str] = None
    source_channel: Optional[str] = None
    source_message_id: Optional[int] = None
    raw_text: str
    posted_at: Optional[str] = None


class JobSource:
    """
    Abstract base interface for all job discovery sources (Telegram, Websites, etc.).
    """

    def fetch(self) -> List[RawJobItem]:
        """
        Retrieves recent items/messages from the source.
        
        Returns:
            A list of RawJobItem instances.
        """
        raise NotImplementedError("Subclasses must implement fetch()")

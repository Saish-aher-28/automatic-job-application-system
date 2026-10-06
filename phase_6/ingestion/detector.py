"""
detector.py — Rule-based preliminary job detection logic.
"""

from __future__ import annotations
import re
from typing import List, Dict, Any


DEFAULT_KEYWORDS = [
    r"\bhiring\b", r"\bvacancy\b", r"\bvacancies\b", r"\bjob\b", r"\bjobs\b",
    r"\bopening\b", r"\bopenings\b", r"\bdeveloper\b", r"\bengineer\b",
    r"\bintern\b", r"\binternship\b", r"\binternships\b", r"\brecruiting\b",
    r"\bapply\b", r"\bposition\b", r"\bpositions\b", r"\bcareer\b",
    r"\bcareers\b", r"\bwalk-in\b", r"\bfresher\b", r"\bfreshers\b",
    r"\bopportunity\b", r"\bopportunities\b", r"\btech stack\b",
    r"\brequirement\b", r"\brequirements\b"
]


class JobDetector:
    """
    Scans raw text to quickly detect if it represents a potential job opportunity.
    Allows filtering out general chat, spam, or news posts before calling LLM APIs.
    """

    def __init__(self, keywords: List[str] = None):
        self.keywords = keywords or DEFAULT_KEYWORDS

    def detect(self, raw_text: str) -> Dict[str, Any]:
        """
        Analyzes the raw text for job signal matches.
        
        Returns:
            Dict containing 'is_candidate' (bool), 'confidence' (float), and 'reasons' (list).
        """
        if not raw_text or not raw_text.strip():
            return {
                "is_candidate": False,
                "confidence": 0.0,
                "reasons": ["empty text"]
            }

        text_lower = raw_text.lower()
        matched_reasons = []
        matches_count = 0

        # Scan for keyword matches using word boundaries
        for kw_pattern in self.keywords:
            if re.search(kw_pattern, text_lower):
                matches_count += 1
                clean_kw = kw_pattern.replace(r"\b", "")
                matched_reasons.append(f"matched keyword: {clean_kw}")

        # Check for URL signal (common in job posts)
        url_matches = re.findall(r"https?://[^\s]+", text_lower)
        if url_matches:
            matched_reasons.append(f"contains {len(url_matches)} application or info link(s)")
            matches_count += 1

        # Calculate a simple heuristic confidence score
        # Cap confidence at 1.0
        confidence = min(matches_count / 4.0, 1.0)
        
        # Candidate threshold: requires at least 2 distinct matches
        is_candidate = matches_count >= 2

        return {
            "is_candidate": is_candidate,
            "confidence": round(confidence, 2),
            "reasons": matched_reasons
        }

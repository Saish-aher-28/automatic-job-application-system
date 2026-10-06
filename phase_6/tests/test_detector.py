"""
test_detector.py — Job detection unit tests for Phase 6.
"""

from __future__ import annotations
from phase_6.ingestion.detector import JobDetector


def test_detect_clean_job_post():
    detector = JobDetector()
    text = "We are hiring! Looking for a Software Engineer to join our team. Apply at https://example.com/careers"
    
    result = detector.detect(text)
    assert result["is_candidate"] is True
    assert result["confidence"] > 0.0
    assert any("hiring" in r or "engineer" in r for r in result["reasons"])


def test_detect_messy_job_post():
    detector = JobDetector()
    text = "vacancy details: developer role open. technical requirements: Python, React, Flask. Please drop resume at hr@company.com"
    
    result = detector.detect(text)
    assert result["is_candidate"] is True
    assert result["confidence"] > 0.0


def test_detect_non_job_post():
    detector = JobDetector()
    text = "What is the best way to study data structures and algorithms in Python? Any recommendations?"
    
    result = detector.detect(text)
    assert result["is_candidate"] is False


def test_detect_empty_or_whitespace():
    detector = JobDetector()
    assert detector.detect("")["is_candidate"] is False
    assert detector.detect("   ")["is_candidate"] is False


def test_detect_misleading_post():
    detector = JobDetector()
    # Post containing only one signal keyword (not enough to trigger candidacy)
    text = "I just got a job!"
    result = detector.detect(text)
    assert result["is_candidate"] is False

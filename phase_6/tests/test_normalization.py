"""
test_normalization.py — Normalization and standardization unit tests for Phase 6.
"""

from __future__ import annotations
from phase_6.normalizer.normalizer import JobNormalizer


def test_normalize_company():
    assert JobNormalizer.normalize_company("Google LLC") == "Google"
    assert JobNormalizer.normalize_company("Facebook Inc.") == "Facebook"
    assert JobNormalizer.normalize_company("Acme Corp") == "Acme"
    assert JobNormalizer.normalize_company("Hiring Company Limited") == "Hiring Company Limited"
    assert JobNormalizer.normalize_company("") is None
    assert JobNormalizer.normalize_company("  ") is None


def test_normalize_title():
    assert JobNormalizer.normalize_title("software engineer") == "Software Engineer"
    assert JobNormalizer.normalize_title("PYTHON DEVELOPER") == "Python Developer"
    assert JobNormalizer.normalize_title("ml engineer / researcher") == "Ml Engineer / Researcher"


def test_normalize_location():
    # Remote/Hybrid variants
    assert JobNormalizer.normalize_location("Remote, US") == "Remote"
    assert JobNormalizer.normalize_location("pune (hybrid)") == "Hybrid"
    
    # Standard formats
    assert JobNormalizer.normalize_location("Pune, Maharashtra, India") == "Pune"
    assert JobNormalizer.normalize_location("Mumbai, MH") == "Mumbai"
    assert JobNormalizer.normalize_location("") is None


def test_normalize_technologies():
    # Canonical mappings
    assert JobNormalizer.normalize_technologies(["react.js", "AWS", "postgres"]) == ["React", "AWS", "PostgreSQL"]
    assert JobNormalizer.normalize_technologies(["mongodb", "nodejs"]) == ["MongoDB", "Node.js"]
    
    # Deduplication and order preservation
    assert JobNormalizer.normalize_technologies(["react js", "React", "ReactJS"]) == ["React"]
    
    # Case normalization
    assert JobNormalizer.normalize_technologies(["python", "docker", "kubernetes"]) == ["Python", "Docker", "Kubernetes"]


def test_normalization_false_match_protection():
    # Java vs JavaScript
    assert JobNormalizer.normalize_technologies(["java"]) == ["Java"]
    assert JobNormalizer.normalize_technologies(["javascript"]) == ["JavaScript"]
    assert JobNormalizer.normalize_technologies(["java", "javascript"]) == ["Java", "JavaScript"]

    # React vs React Native
    assert JobNormalizer.normalize_technologies(["react native"]) == ["react native"]
    assert JobNormalizer.normalize_technologies(["react", "react native"]) == ["React", "react native"]

    # Docker vs Kubernetes (separate and independent)
    assert JobNormalizer.normalize_technologies(["docker"]) == ["Docker"]
    assert JobNormalizer.normalize_technologies(["kubernetes"]) == ["Kubernetes"]


def test_normalize_experience():
    assert JobNormalizer.normalize_experience("Freshers") == "0 years"
    assert JobNormalizer.normalize_experience("Entry Level") == "0 years"
    assert JobNormalizer.normalize_experience("1-3 years of experience") == "1-3 years"
    assert JobNormalizer.normalize_experience("2+ years") == "2+ years"
    assert JobNormalizer.normalize_experience("no prior experience needed") == "no prior experience needed"

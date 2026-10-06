"""
test_adversarial_matching.py — Adversarial and safety tests for Phase 3 matching.

Tests:
1. False match protections:
   - Kubernetes vs Docker
   - React vs React Native
   - Java vs JavaScript
   - PostgreSQL vs MongoDB
   - Python vs PyTorch
   - AWS vs Azure
   - Flask vs FastAPI
2. Low evidence project scoring for SRE vs Web Frontend project
3. Empty list safety (no NaN/Infinity)
"""

import pytest
from phase_3.matcher.normalization import normalize_skill_name, normalize_skill_list
from phase_3.matcher.skill_matcher import calculate_match_details, match_skills_and_technologies
from phase_3.matcher.scorer import calculate_overall_match_score, calculate_project_final_score

def test_adversarial_normalization_distinctness():
    """Verify distinct technologies are not false-matched via normalization."""
    # Java != JavaScript
    assert normalize_skill_name("Java") != normalize_skill_name("JavaScript")
    assert "java" not in [s.lower() for s in normalize_skill_list(["JavaScript"])]

    # React != React Native
    assert normalize_skill_name("React") != normalize_skill_name("React Native")

    # Kubernetes != Docker
    assert normalize_skill_name("Kubernetes") != normalize_skill_name("Docker")

    # PostgreSQL != MongoDB
    assert normalize_skill_name("PostgreSQL") != normalize_skill_name("MongoDB")

    # Python != PyTorch
    assert normalize_skill_name("Python") != normalize_skill_name("PyTorch")

    # AWS != Azure
    assert normalize_skill_name("AWS") != normalize_skill_name("Azure")

    # Flask != FastAPI
    assert normalize_skill_name("Flask") != normalize_skill_name("FastAPI")

def test_adversarial_skill_matcher():
    """Test skill matcher handles distinct technology lists without false positives."""
    jd_skills = ["Kubernetes", "Docker", "Terraform", "AWS EKS", "Helm"]
    profile_skills = ["React", "CSS", "HTML", "Node.js"]

    matched, missing, score = calculate_match_details(jd_skills, profile_skills)
    assert score == 0.0
    assert len(matched) == 0
    assert len(missing) == 5

def test_empty_data_scoring_safety():
    """Verify empty lists produce mathematically valid scores (no NaN or exception)."""
    # 0 projects should result in project_relevance = 0
    score = calculate_overall_match_score(
        required_score=100.0,
        preferred_score=100.0,
        tech_score=100.0,
        project_scores=[]
    )
    # 100*0.5 + 100*0.15 + 100*0.15 + 0*0.20 = 50 + 15 + 15 = 80.0
    assert score == 80.0

def test_irrelevant_project_scoring():
    """Verify irrelevant project preliminary + semantic blend stays low."""
    # Preliminary 20, Semantic 15
    final_score = calculate_project_final_score(preliminary_score=20.0, semantic_score=15.0)
    # (20 * 0.3) + (15 * 0.7) = 6 + 10.5 = 16.5
    assert final_score == 16.5
    assert final_score < 30.0

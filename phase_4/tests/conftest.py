"""
conftest.py — Shared fixtures for Phase 4 tests.

Adds the project root to sys.path so 'phase_4' and 'resume_engine' can be imported.
"""

import sys
from pathlib import Path

import pytest

# Add Phase 1 root to sys.path (two levels up from this conftest)
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


# ── Shared fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def mock_profile():
    return {
        "name": "Saish Aher",
        "degree_title": "B.Tech — Information Technology",
        "phone": "+91 9999999999",
        "email": "saish@example.com",
        "linkedin": "https://linkedin.com/in/saishaher",
        "github": "https://github.com/saishaher",
        "location": "Kopargaon, Maharashtra, India",
        "summary": (
            "Results-driven B.Tech Information Technology student with hands-on "
            "experience in Python, Flask, and AWS cloud infrastructure. "
            "Passionate about building scalable backend systems."
        ),
    }


@pytest.fixture
def mock_skills_grouped():
    return {
        "Programming Languages": ["Python", "C++", "Java", "JavaScript"],
        "Web Development":       ["Flask", "React", "HTML", "CSS"],
        "Databases":             ["MySQL", "MongoDB", "Firebase"],
        "AI/ML":                 ["Scikit-learn", "XGBoost", "Pandas", "NumPy"],
        "Other":                 ["AWS", "Docker", "Git", "Linux"],
    }


@pytest.fixture
def mock_projects():
    """Five mock projects with varying relevance scores."""
    return [
        {
            "_id": "proj_a",
            "name": "CloudReport Pipeline",
            "year": "2024",
            "description": "Cloud data pipeline using Python and AWS Lambda.",
            "technologies": ["Python", "AWS", "Lambda", "S3"],
            "keywords": ["cloud", "pipeline", "backend"],
            "categories": ["Backend", "Cloud"],
            "resume_bullets": ["Built ETL pipeline on AWS.", "Reduced latency by 40%."],
            "enabled": True,
        },
        {
            "_id": "proj_b",
            "name": "InventIQ",
            "year": "2024",
            "description": "Inventory management system with Flask REST API.",
            "technologies": ["Python", "Flask", "MySQL"],
            "keywords": ["backend", "rest api", "inventory"],
            "categories": ["Backend"],
            "resume_bullets": ["Developed REST APIs with Flask.", "Managed MySQL schemas."],
            "enabled": True,
        },
        {
            "_id": "proj_c",
            "name": "Cybersecurity Threat Analyser",
            "year": "2023",
            "description": "ML-based threat classification with Scikit-learn.",
            "technologies": ["Python", "Scikit-learn", "Pandas"],
            "keywords": ["machine learning", "security", "classification"],
            "categories": ["AI/ML"],
            "resume_bullets": ["Trained threat classifier achieving 92% accuracy."],
            "enabled": True,
        },
        {
            "_id": "proj_d",
            "name": "Transportation App",
            "year": "2023",
            "description": "Transport booking frontend built with React.",
            "technologies": ["React", "JavaScript", "CSS"],
            "keywords": ["frontend", "web"],
            "categories": ["Frontend"],
            "resume_bullets": ["Built responsive transport booking UI."],
            "enabled": True,
        },
        {
            "_id": "proj_e",
            "name": "Customer Churn Predictor",
            "year": "2022",
            "description": "Churn prediction model using XGBoost.",
            "technologies": ["Python", "XGBoost", "Pandas"],
            "keywords": ["machine learning", "churn"],
            "categories": ["AI/ML"],
            "resume_bullets": ["Predicted churn with 88% AUC."],
            "enabled": True,
        },
    ]


@pytest.fixture
def mock_ranked_projects():
    """Simulated Phase 3 ranked_projects list (descending by final_project_score)."""
    return [
        {
            "project_id": "proj_a",
            "project_name": "CloudReport Pipeline",
            "preliminary_score": 88.0,
            "semantic_score": 92.0,
            "final_project_score": 91.0,
            "matched_skills": ["Python", "AWS"],
            "matched_technologies": ["Python", "AWS"],
            "missing_relevant_skills": [],
            "reason": "Strong backend/cloud alignment.",
        },
        {
            "project_id": "proj_b",
            "project_name": "InventIQ",
            "preliminary_score": 76.0,
            "semantic_score": 80.0,
            "final_project_score": 78.0,
            "matched_skills": ["Python", "Flask"],
            "matched_technologies": ["Python", "Flask"],
            "missing_relevant_skills": ["Docker"],
            "reason": "Good backend alignment.",
        },
        {
            "project_id": "proj_c",
            "project_name": "Cybersecurity Threat Analyser",
            "preliminary_score": 55.0,
            "semantic_score": 62.0,
            "final_project_score": 60.0,
            "matched_skills": ["Python"],
            "matched_technologies": ["Python"],
            "missing_relevant_skills": ["AWS", "Flask"],
            "reason": "Moderate relevance — Python shared.",
        },
        {
            "project_id": "proj_d",
            "project_name": "Transportation App",
            "preliminary_score": 30.0,
            "semantic_score": 25.0,
            "final_project_score": 27.0,
            "matched_skills": [],
            "matched_technologies": [],
            "missing_relevant_skills": ["Python", "AWS", "Flask"],
            "reason": "Frontend project — low backend relevance.",
        },
        {
            "project_id": "proj_e",
            "project_name": "Customer Churn Predictor",
            "preliminary_score": 20.0,
            "semantic_score": 18.0,
            "final_project_score": 19.0,
            "matched_skills": ["Python"],
            "matched_technologies": ["Python"],
            "missing_relevant_skills": ["AWS", "Flask"],
            "reason": "Weak alignment to backend JD.",
        },
    ]


@pytest.fixture
def mock_match_result():
    """Simulated Phase 3 Firestore document (nested structure as stored)."""
    return {
        "jd_document_id": "jd-doc-backend-001",
        "job_title": "Backend Developer",
        "scores": {
            "overall": 82.0,
            "required_skills": 90.0,
            "preferred_skills": 60.0,
            "technologies": 75.0,
            "projects": 76.5,
        },
        "skill_match": {
            "matched_required":    ["Python", "Flask", "AWS"],
            "missing_required":    ["Docker"],
            "matched_preferred":   ["Git"],
            "missing_preferred":   ["Kubernetes"],
            "matched_technologies": ["Python", "Flask", "AWS"],
            "missing_technologies": ["Docker", "PostgreSQL"],
        },
        "ranked_projects": [
            {
                "project_id": "proj_a",
                "project_name": "CloudReport Pipeline",
                "preliminary_score": 88.0,
                "semantic_score": 92.0,
                "final_project_score": 91.0,
                "matched_skills": ["Python", "AWS"],
                "matched_technologies": ["Python", "AWS"],
                "missing_relevant_skills": [],
                "reason": "Strong alignment.",
            },
            {
                "project_id": "proj_b",
                "project_name": "InventIQ",
                "preliminary_score": 76.0,
                "semantic_score": 80.0,
                "final_project_score": 78.0,
                "matched_skills": ["Python", "Flask"],
                "matched_technologies": ["Python", "Flask"],
                "missing_relevant_skills": ["Docker"],
                "reason": "Good alignment.",
            },
            {
                "project_id": "proj_c",
                "project_name": "Cybersecurity Threat Analyser",
                "preliminary_score": 55.0,
                "semantic_score": 62.0,
                "final_project_score": 60.0,
                "matched_skills": ["Python"],
                "matched_technologies": ["Python"],
                "missing_relevant_skills": ["AWS"],
                "reason": "Moderate relevance.",
            },
        ],
        "matcher_version": "1.0",
        "created_at": "2026-08-20T10:00:00+00:00",
    }

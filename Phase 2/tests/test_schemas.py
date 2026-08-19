"""
test_schemas.py — Unit tests for Pydantic schema models.

No Gemini calls. No Firestore. Pure Python.
"""

import pytest
from phase_2.jd_analyzer.schemas import JDAnalysis, FirestoreJDDocument


class TestJDAnalysis:

    def test_defaults_all_none_and_empty(self):
        a = JDAnalysis()
        assert a.job_title is None
        assert a.company is None
        assert a.role_category is None
        assert a.experience_level is None
        assert a.employment_type is None
        assert a.location is None
        assert a.required_skills == []
        assert a.preferred_skills == []
        assert a.technologies == []
        assert a.responsibilities == []
        assert a.education_requirements == []
        assert a.experience_requirements == []
        assert a.keywords == []

    def test_full_valid_object(self):
        a = JDAnalysis(
            job_title="Backend Developer",
            company="TechNova",
            role_category="Backend",
            experience_level="Mid Level",
            employment_type="Full-time",
            location="Pune, India",
            required_skills=["Python", "Flask"],
            preferred_skills=["Docker"],
            technologies=["Python", "Flask", "AWS"],
            responsibilities=["Build APIs"],
            education_requirements=["B.Tech in CS"],
            experience_requirements=["1-3 years"],
            keywords=["python", "backend", "flask"],
        )
        assert a.job_title == "Backend Developer"
        assert a.required_skills == ["Python", "Flask"]
        assert a.technologies == ["Python", "Flask", "AWS"]

    def test_none_list_coerced_to_empty(self):
        a = JDAnalysis(required_skills=None)
        assert a.required_skills == []

    def test_empty_string_coerced_to_none(self):
        a = JDAnalysis(job_title="", company="   ")
        assert a.job_title is None
        assert a.company is None

    def test_string_list_coerced_to_list(self):
        a = JDAnalysis(required_skills="Python")
        assert a.required_skills == ["Python"]

    def test_whitespace_only_string_in_list_excluded(self):
        a = JDAnalysis(required_skills="   ")
        assert a.required_skills == []

    def test_model_dump(self):
        a = JDAnalysis(job_title="ML Engineer", required_skills=["Python"])
        d = a.model_dump()
        assert d["job_title"] == "ML Engineer"
        assert d["required_skills"] == ["Python"]
        assert "company" in d

    def test_model_validate_from_dict(self):
        data = {
            "job_title": "DevOps Engineer",
            "required_skills": ["Docker", "Kubernetes"],
            "preferred_skills": ["Terraform"],
            "technologies": ["Docker", "Kubernetes", "AWS"],
        }
        a = JDAnalysis.model_validate(data)
        assert a.job_title == "DevOps Engineer"
        assert "Docker" in a.required_skills


class TestFirestoreJDDocument:

    def test_basic_construction(self):
        analysis = JDAnalysis(job_title="Data Analyst")
        doc = FirestoreJDDocument(
            raw_text="We need a data analyst.",
            analysis=analysis,
            model="gemini-3.1-flash-lite",
            created_at="2026-01-01T00:00:00+00:00",
        )
        assert doc.analysis_version == "1.0"
        assert doc.model == "gemini-3.1-flash-lite"
        assert doc.raw_text == "We need a data analyst."

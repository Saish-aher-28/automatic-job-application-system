"""
test_no_hallucination.py — Tests that Phase 4 never fabricates resume content.

Verifies:
  - Missing required skill (Kubernetes) NOT added to generated resume
  - Project technology not in Firestore NOT added to LaTeX
  - No fabricated skills appear in the skills section
"""

import pytest
from unittest.mock import patch, MagicMock
from phase_4.resume_tailor.schemas import TailoringPlan


def _make_minimal_profile():
    return {
        "name": "Test User",
        "email": "test@example.com",
        "phone": "+1 000",
        "degree_title": "B.Tech",
        "linkedin": "https://linkedin.com/in/testuser",
        "github": "https://github.com/testuser",
        "location": "Test City",
        "summary": "Python and Flask developer.",
    }


def _make_project_python_flask_only():
    """Project that ONLY contains Python, Flask, AWS — no PostgreSQL, no Kubernetes."""
    return {
        "_id": "proj-pf-001",
        "name": "API Backend Project",
        "year": "2024",
        "technologies": ["Python", "Flask", "AWS"],
        "description": "A REST API built with Python, Flask, and AWS.",
        "resume_bullets": [
            "Built REST API endpoints using Flask.",
            "Deployed to AWS EC2.",
        ],
        "keywords": ["backend", "api"],
        "categories": ["Backend"],
        "enabled": True,
    }


def _render_resume_data(resume_data: dict) -> str:
    """Actually render the resume and return the LaTeX string."""
    from resume_engine.latex_renderer import render_resume
    return render_resume(resume_data)


class TestNoHallucination:

    def test_missing_required_skill_kubernetes_not_in_output(self):
        """
        Phase 3 reports Kubernetes as a missing required skill.
        Phase 4 must NOT add Kubernetes to the generated resume.
        """
        from phase_4.resume_tailor.skill_selector import reorder_skills

        skills_grouped = {
            "Programming Languages": ["Python", "C++"],
            "Web Development": ["Flask"],
            "Other": ["AWS", "Docker"],
        }

        # Simulate Phase 4 reordering (without Kubernetes, which is missing)
        reordered = reorder_skills(
            skills_grouped=skills_grouped,
            skills_to_emphasize=["Python", "AWS"],  # only real profile skills
        )

        # Render the resume
        resume_data = {
            "profile": _make_minimal_profile(),
            "projects": [_make_project_python_flask_only()],
            "skills": reordered,
            "education": [],
            "experience": [],
            "certifications": [],
            "languages": [],
            "interests": [],
        }

        tex = _render_resume_data(resume_data)

        # Kubernetes must NOT appear anywhere in the LaTeX output
        assert "Kubernetes" not in tex, (
            "Kubernetes was added to the resume even though it is a MISSING skill."
        )

    def test_fabricated_technology_postgresql_not_in_project_tex(self):
        """
        The project has Python, Flask, AWS.
        PostgreSQL must NOT appear in the rendered project section.
        """
        resume_data = {
            "profile": _make_minimal_profile(),
            "projects": [_make_project_python_flask_only()],
            "skills": {"Programming Languages": ["Python"], "Web Development": ["Flask"]},
            "education": [],
            "experience": [],
            "certifications": [],
            "languages": [],
            "interests": [],
        }

        tex = _render_resume_data(resume_data)

        # Find the Projects section only (not the whole doc, but project tech line)
        assert "PostgreSQL" not in tex, (
            "PostgreSQL appeared in the resume even though the project only has Python/Flask/AWS."
        )

    def test_only_real_skills_appear_in_skills_section(self):
        """The skills section must contain ONLY skills from the profile."""
        profile_skills = ["Python", "Flask", "AWS", "MySQL"]
        skills_grouped = {"Web/Backend": profile_skills}

        resume_data = {
            "profile": _make_minimal_profile(),
            "projects": [],
            "skills": skills_grouped,
            "education": [],
            "experience": [],
            "certifications": [],
            "languages": [],
            "interests": [],
        }

        tex = _render_resume_data(resume_data)

        # Inventions that should NOT appear
        for fabricated in ["Kubernetes", "FastAPI", "Rust", "TensorFlow", "PostgreSQL"]:
            assert fabricated not in tex, (
                f"Fabricated skill '{fabricated}' appeared in the resume."
            )

        # Real skills should appear
        for real_skill in profile_skills:
            assert real_skill in tex, (
                f"Real skill '{real_skill}' is missing from the resume."
            )

    def test_project_section_uses_only_actual_technologies(self):
        """
        Rendered project LaTeX must include only the technologies stored in Firestore.
        No invented technologies should appear in the project's technology line.
        """
        project = {
            "_id": "p1",
            "name": "My Project",
            "year": "2024",
            "technologies": ["Python", "Flask"],  # only these two
            "description": "A Flask app.",
            "resume_bullets": [],
            "keywords": [],
            "categories": [],
            "enabled": True,
        }

        resume_data = {
            "profile": _make_minimal_profile(),
            "projects": [project],
            "skills": {},
            "education": [],
            "experience": [],
            "certifications": [],
            "languages": [],
            "interests": [],
        }

        tex = _render_resume_data(resume_data)

        # Ensure ONLY Flask and Python appear in the project tech line
        # and Docker (not in project) does NOT appear
        assert "Python" in tex
        assert "Flask" in tex
        assert "Docker" not in tex  # Docker is not in this project's technologies

    def test_tailoring_plan_cannot_inject_missing_skill(self, mock_skills_grouped):
        """
        A TailoringPlan returned by Gemini that contains a missing skill
        must be stripped by the validation layer before use.
        """
        from phase_4.resume_tailor.content_tailor import ContentTailor

        tailor = ContentTailor.__new__(ContentTailor)
        tailor._api_key = "test"
        tailor._model   = "test"
        tailor._client  = MagicMock()

        # Simulate Gemini hallucinating PostgreSQL as an existing profile skill
        bad_plan = TailoringPlan(
            summary_focus=["Python"],
            skills_to_emphasize=["Python", "PostgreSQL"],  # PostgreSQL not in profile
            project_ids=["proj_a"],
            tailoring_notes="",
        )

        validated = tailor._validate_plan(
            plan=bad_plan,
            skills_grouped=mock_skills_grouped,
            ranked_project_ids=["proj_a"],
            project_limit=1,
        )

        # PostgreSQL must be rejected
        assert "PostgreSQL" not in validated.skills_to_emphasize
        assert "Python" in validated.skills_to_emphasize

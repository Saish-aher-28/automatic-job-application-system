"""
test_resume_generator.py — Integration tests for the resume generator pipeline.

Uses mocked Firestore — no real credentials needed.
"""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile
import os


# ────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────

def _make_stream(items: list[dict], id_prefix: str = "doc"):
    """Create mock Firestore stream docs from a list of dicts."""
    docs = []
    for i, item in enumerate(items):
        doc = MagicMock()
        doc.id = f"{id_prefix}_{i}"
        doc.to_dict.return_value = item
        docs.append(doc)
    return iter(docs)


def _mock_profile_doc(data: dict):
    doc = MagicMock()
    doc.exists = True
    doc.to_dict.return_value = data
    return doc


SAMPLE_PROFILE = {
    "name": "John Doe",
    "degree_title": "B.E. Computer Science",
    "email": "john@example.com",
    "phone": "+91 99999 99999",
    "location": "Mumbai, India",
    "linkedin": "https://linkedin.com/in/johndoe",
    "github": "https://github.com/johndoe",
    "summary": "Passionate engineer.",
}

SAMPLE_PROJECTS = [
    {
        "name": "Project Alpha",
        "description": "Great project",
        "technologies": ["Python"],
        "resume_bullets": ["Built API"],
        "enabled": True,
    }
]

SAMPLE_SKILLS = [
    {"name": "Python", "category": "Programming Languages", "enabled": True, "sort_order": 1},
]

SAMPLE_EDUCATION = [
    {
        "degree": "B.E.",
        "field": "CS",
        "institution": "VJTI",
        "location": "Mumbai",
        "graduation_year": 2025,
        "details": ["CGPA: 9/10"],
        "sort_order": 1,
    }
]

SAMPLE_CERTIFICATIONS = [
    {"name": "AWS SAA", "issuer": "Amazon", "date": "2024", "enabled": True, "sort_order": 1},
]

SAMPLE_LANGUAGES = [
    {"name": "English", "proficiency": "Native", "enabled": True, "sort_order": 1},
]

SAMPLE_INTERESTS = [
    {"name": "Chess", "enabled": True, "sort_order": 1},
]


class TestResumeGeneratorOffline:
    """
    Tests the resume generator with mocked Firestore.
    Validates .tex generation without requiring pdflatex.
    """

    def _setup_mock_db(self, mock_gfc):
        """Wire up a full mock Firestore client with sample data."""
        mock_db = MagicMock()

        def collection_side_effect(name):
            coll = MagicMock()
            if name == "profiles":
                doc = MagicMock()
                doc.get.return_value = _mock_profile_doc(SAMPLE_PROFILE)
                coll.document.return_value = doc
            elif name == "projects":
                coll.stream.return_value = _make_stream(SAMPLE_PROJECTS, "proj")
            elif name == "skills":
                coll.stream.return_value = _make_stream(SAMPLE_SKILLS, "skill")
            elif name == "education":
                coll.stream.return_value = _make_stream(SAMPLE_EDUCATION, "edu")
            elif name == "experience":
                coll.stream.return_value = _make_stream([], "exp")
            elif name == "certifications":
                coll.stream.return_value = _make_stream(SAMPLE_CERTIFICATIONS, "cert")
            elif name == "languages":
                coll.stream.return_value = _make_stream(SAMPLE_LANGUAGES, "lang")
            elif name == "interests":
                coll.stream.return_value = _make_stream(SAMPLE_INTERESTS, "int")
            return coll

        mock_db.collection.side_effect = collection_side_effect
        mock_gfc.return_value = mock_db
        return mock_db

    @patch("resume_engine.profile_service.get_firestore_client")
    @patch("resume_engine.project_service.get_firestore_client")
    @patch("resume_engine.skill_service.get_firestore_client")
    @patch("resume_engine.education_service.get_firestore_client")
    @patch("resume_engine.experience_service.get_firestore_client")
    @patch("resume_engine.certification_service.get_firestore_client")
    @patch("resume_engine.language_service.get_firestore_client")
    @patch("resume_engine.interest_service.get_firestore_client")
    def test_generates_tex_file(
        self, mock_int, mock_lang, mock_cert, mock_exp, mock_edu,
        mock_skill, mock_proj, mock_profile
    ):
        """generate_resume should successfully write a .tex file."""
        for mock in [mock_int, mock_lang, mock_cert, mock_exp, mock_edu,
                     mock_skill, mock_proj, mock_profile]:
            self._setup_mock_db(mock)

        from resume_engine.resume_generator import generate_resume
        result = generate_resume(project_limit=3)

        assert result.success is True
        assert result.tex_path is not None
        assert result.tex_path.exists()

        # Read the generated .tex and check content
        with open(result.tex_path, "r", encoding="utf-8") as f:
            tex = f.read()

        assert "John Doe" in tex
        assert "Project Alpha" in tex
        assert r"\begin{document}" in tex

    @patch("resume_engine.profile_service.get_firestore_client")
    @patch("resume_engine.project_service.get_firestore_client")
    @patch("resume_engine.skill_service.get_firestore_client")
    @patch("resume_engine.education_service.get_firestore_client")
    @patch("resume_engine.experience_service.get_firestore_client")
    @patch("resume_engine.certification_service.get_firestore_client")
    @patch("resume_engine.language_service.get_firestore_client")
    @patch("resume_engine.interest_service.get_firestore_client")
    def test_master_template_unchanged_after_generation(
        self, mock_int, mock_lang, mock_cert, mock_exp, mock_edu,
        mock_skill, mock_proj, mock_profile
    ):
        """CRITICAL: master template must be unchanged after generate_resume()."""
        for mock in [mock_int, mock_lang, mock_cert, mock_exp, mock_edu,
                     mock_skill, mock_proj, mock_profile]:
            self._setup_mock_db(mock)

        from resume_engine.config import config
        from resume_engine.resume_generator import generate_resume

        with open(config.LATEX_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            before = f.read()

        generate_resume(project_limit=1)

        with open(config.LATEX_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            after = f.read()

        assert before == after, "CRITICAL: Master template was modified by generate_resume()!"


class TestPageCountValidation:

    def test_count_pdf_pages_missing_file(self):
        """Should return None gracefully if PDF doesn't exist."""
        from resume_engine.resume_generator import count_pdf_pages
        result = count_pdf_pages(Path("/nonexistent/path/resume.pdf"))
        assert result is None

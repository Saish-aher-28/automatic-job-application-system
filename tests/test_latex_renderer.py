"""
test_latex_renderer.py — Tests for LaTeX section rendering and placeholder replacement.

These tests require NO Firestore connection.
"""

import pytest
from pathlib import Path

from resume_engine.latex_renderer import (
    render_education,
    render_skills,
    render_projects,
    render_certifications,
    render_languages,
    render_interests,
    render_resume,
    write_tex,
)


# ────────────────────────────────────────────────────────────────────
# Education Rendering
# ────────────────────────────────────────────────────────────────────

class TestRenderEducation:

    def test_empty_returns_note(self):
        result = render_education([])
        assert "No education" in result

    def test_single_record(self):
        rec = {
            "degree": "Bachelor of Engineering",
            "field": "Computer Science",
            "institution": "MIT",
            "location": "Cambridge, MA",
            "graduation_year": 2025,
            "details": ["CGPA: 9.0/10"],
        }
        result = render_education([rec])
        assert "Bachelor of Engineering" in result
        assert "Computer Science" in result
        assert "MIT" in result
        assert "2025" in result
        assert "CGPA" in result

    def test_special_chars_escaped(self):
        rec = {
            "degree": "B.E",
            "field": "CS & IT",
            "institution": "VJTI",
            "location": "Mumbai",
        }
        result = render_education([rec])
        assert r"\&" in result

    def test_multiple_records_separated(self):
        recs = [
            {"institution": "College A", "degree": "BE", "field": "CS"},
            {"institution": "College B", "degree": "ME", "field": "AI"},
        ]
        result = render_education(recs)
        assert "College A" in result
        assert "College B" in result
        assert "vspace" in result  # separator present


# ────────────────────────────────────────────────────────────────────
# Skills Rendering
# ────────────────────────────────────────────────────────────────────

class TestRenderSkills:

    def test_empty_returns_note(self):
        assert "No skills" in render_skills({})

    def test_single_category(self):
        grouped = {"Programming Languages": ["Python", "C++", "Java"]}
        result = render_skills(grouped)
        assert "Programming Languages" in result
        assert "Python" in result
        assert r"C\+\+" not in result  # + is not special
        assert "C++" in result

    def test_multiple_categories(self):
        grouped = {
            "Programming Languages": ["Python"],
            "Databases": ["MySQL"],
        }
        result = render_skills(grouped)
        assert "Programming Languages" in result
        assert "Databases" in result

    def test_underscore_in_skill_escaped(self):
        grouped = {"Other": ["node_js"]}
        result = render_skills(grouped)
        assert r"node\_js" in result

    def test_ampersand_in_category_escaped(self):
        grouped = {"AI & ML": ["TensorFlow"]}
        result = render_skills(grouped)
        assert r"AI \& ML" in result


# ────────────────────────────────────────────────────────────────────
# Projects Rendering
# ────────────────────────────────────────────────────────────────────

class TestRenderProjects:

    def test_empty_returns_note(self):
        assert "No projects" in render_projects([])

    def test_single_project_with_bullets(self):
        proj = {
            "name": "Alpha Project",
            "year": "2024",
            "technologies": ["Python", "Flask"],
            "resume_bullets": ["Built REST API", "Improved performance by 40%"],
        }
        result = render_projects([proj])
        assert "Alpha Project" in result
        assert "2024" in result
        assert "Python" in result
        assert "Built REST API" in result
        assert "itemize" in result

    def test_project_description_fallback(self):
        """If no bullets, description should appear."""
        proj = {
            "name": "Beta Project",
            "description": "A fallback description.",
            "technologies": [],
        }
        result = render_projects([proj])
        assert "fallback description" in result
        assert "itemize" not in result

    def test_special_chars_in_project_name_escaped(self):
        proj = {
            "name": "R&D Tool",
            "description": "desc",
            "technologies": [],
        }
        result = render_projects([proj])
        assert r"\&" in result

    def test_multiple_projects_separated(self):
        projects = [
            {"name": "Proj A", "description": "d", "technologies": []},
            {"name": "Proj B", "description": "d", "technologies": []},
        ]
        result = render_projects(projects)
        assert "Proj A" in result
        assert "Proj B" in result
        assert "vspace" in result

    def test_github_url_in_href(self):
        proj = {
            "name": "MyProj",
            "description": "d",
            "technologies": [],
            "github_url": "https://github.com/user/repo",
        }
        result = render_projects([proj])
        assert r"\href{https://github.com/user/repo}" in result
        assert "GitHub" in result


# ────────────────────────────────────────────────────────────────────
# Certifications Rendering
# ────────────────────────────────────────────────────────────────────

class TestRenderCertifications:

    def test_empty_returns_note(self):
        assert "No certifications" in render_certifications([])

    def test_single_cert(self):
        cert = {"name": "AWS SAA", "issuer": "Amazon", "date": "2023"}
        result = render_certifications([cert])
        assert "AWS SAA" in result
        assert "Amazon" in result
        assert "2023" in result

    def test_cert_with_url_uses_href(self):
        cert = {
            "name": "GCP ACE",
            "issuer": "Google",
            "credential_url": "https://cloud.google.com/cert",
        }
        result = render_certifications([cert])
        assert r"\href" in result

    def test_percent_in_cert_escaped(self):
        cert = {"name": "Top 5% Award", "issuer": "Org"}
        result = render_certifications([cert])
        assert r"\%" in result


# ────────────────────────────────────────────────────────────────────
# Languages Rendering
# ────────────────────────────────────────────────────────────────────

class TestRenderLanguages:

    def test_empty_returns_note(self):
        assert "No languages" in render_languages([])

    def test_single_language(self):
        langs = [{"name": "English", "proficiency": "Native"}]
        result = render_languages(langs)
        assert "English" in result
        assert "Native" in result

    def test_multiple_languages(self):
        langs = [
            {"name": "English", "proficiency": "Native"},
            {"name": "Hindi",   "proficiency": "Fluent"},
        ]
        result = render_languages(langs)
        assert "English" in result
        assert "Hindi" in result


# ────────────────────────────────────────────────────────────────────
# Interests Rendering
# ────────────────────────────────────────────────────────────────────

class TestRenderInterests:

    def test_empty_returns_note(self):
        assert "No interests" in render_interests([])

    def test_single_interest(self):
        result = render_interests([{"name": "Chess"}])
        assert "Chess" in result

    def test_multiple_comma_separated(self):
        interests = [{"name": "Chess"}, {"name": "Reading"}, {"name": "Hiking"}]
        result = render_interests(interests)
        assert "Chess" in result
        assert "Reading" in result
        assert "Hiking" in result
        assert "," in result


# ────────────────────────────────────────────────────────────────────
# Full Resume Rendering
# ────────────────────────────────────────────────────────────────────

class TestRenderResume:
    """Tests using the actual master template file."""

    SAMPLE_DATA = {
        "profile": {
            "name": "John Doe",
            "degree_title": "B.E. Computer Science",
            "email": "john@example.com",
            "phone": "+91 99999 99999",
            "location": "Mumbai, India",
            "linkedin": "https://linkedin.com/in/johndoe",
            "github": "https://github.com/johndoe",
            "summary": "Passionate software engineer with 2 years of experience.",
        },
        "projects": [
            {
                "name": "Project Alpha",
                "year": "2024",
                "technologies": ["Python", "Flask"],
                "resume_bullets": ["Built REST API", "Deployed on cloud"],
            }
        ],
        "skills": {"Programming Languages": ["Python", "C++"]},
        "education": [
            {
                "degree": "B.E.",
                "field": "Computer Science",
                "institution": "VJTI",
                "location": "Mumbai",
                "graduation_year": 2025,
                "details": ["CGPA: 9.2/10"],
            }
        ],
        "certifications": [
            {"name": "AWS SAA", "issuer": "Amazon", "date": "2024"},
        ],
        "languages": [
            {"name": "English", "proficiency": "Native"},
        ],
        "interests": [{"name": "Chess"}, {"name": "Reading"}],
        "experience": [],
    }

    def test_render_produces_valid_latex(self):
        """render_resume should return a string containing \\begin{document}."""
        tex = render_resume(self.SAMPLE_DATA)
        assert r"\begin{document}" in tex
        assert r"\end{document}" in tex

    def test_name_substituted(self):
        tex = render_resume(self.SAMPLE_DATA)
        assert "John Doe" in tex

    def test_email_substituted(self):
        tex = render_resume(self.SAMPLE_DATA)
        assert "john@example.com" in tex

    def test_linkedin_username_extracted(self):
        tex = render_resume(self.SAMPLE_DATA)
        assert "johndoe" in tex
        assert "{{LINKEDIN_USERNAME}}" not in tex

    def test_github_username_extracted(self):
        tex = render_resume(self.SAMPLE_DATA)
        assert "{{GITHUB_USERNAME}}" not in tex

    def test_no_unfilled_placeholders(self):
        """All {{PLACEHOLDER}} tokens must be replaced."""
        import re
        tex = render_resume(self.SAMPLE_DATA)
        remaining = re.findall(r"\{\{[A-Z_]+\}\}", tex)
        assert remaining == [], f"Unfilled placeholders: {remaining}"

    def test_project_in_output(self):
        tex = render_resume(self.SAMPLE_DATA)
        assert "Project Alpha" in tex

    def test_skills_in_output(self):
        tex = render_resume(self.SAMPLE_DATA)
        assert "Programming Languages" in tex
        assert "Python" in tex

    def test_master_template_unchanged(self):
        """
        CRITICAL: render_resume must NEVER modify the master template.
        """
        from resume_engine.config import config

        with open(config.LATEX_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            before = f.read()

        render_resume(self.SAMPLE_DATA)

        with open(config.LATEX_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            after = f.read()

        assert before == after, (
            "CRITICAL: Master template was modified during render! "
            "The template must remain unchanged."
        )

    def test_adding_project_does_not_change_template(self):
        """
        Verifies that adding a new project does NOT require any template changes.
        """
        from resume_engine.config import config

        with open(config.LATEX_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            template_before = f.read()

        # Render with 1 project
        data_1 = {**self.SAMPLE_DATA}
        render_resume(data_1)

        # Render with 2 projects (simulating adding Project D)
        data_2 = {
            **self.SAMPLE_DATA,
            "projects": [
                {"name": "Proj A", "description": "d", "technologies": []},
                {"name": "Proj B", "description": "d", "technologies": []},
                {"name": "Proj C", "description": "d", "technologies": []},
                {"name": "Proj D", "description": "d", "technologies": []},  # NEW
            ],
        }
        render_resume(data_2)

        with open(config.LATEX_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            template_after = f.read()

        assert template_before == template_after, (
            "Adding a new project must NOT change the LaTeX master template."
        )

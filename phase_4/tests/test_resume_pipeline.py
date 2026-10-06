"""
test_resume_pipeline.py — Tests for the Phase 4 resume pipeline orchestrator.

Uses fully mocked Firestore and Phase 1 renderer to test pipeline behaviour.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


def _make_full_mock_context(tmp_path, page_count=1, compile_ok=True):
    """
    Build patch context for the full pipeline.
    Returns a context manager.
    """
    import contextlib

    mock_profile = {
        "name": "Saish Aher", "email": "s@example.com", "phone": "+91 99",
        "degree_title": "B.Tech IT",
        "linkedin": "https://linkedin.com/in/saishaher",
        "github": "https://github.com/saishaher",
        "location": "Kopargaon",
        "summary": "Python and AWS developer.",
    }

    mock_match_doc = {
        "jd_document_id": "jd-pipeline-001",
        "job_title": "Backend Developer",
        "scores": {"overall": 82.0, "required_skills": 90.0, "preferred_skills": 60.0,
                   "technologies": 75.0, "projects": 78.0},
        "skill_match": {
            "matched_required": ["Python", "Flask"],
            "missing_required": ["Docker"],
            "matched_preferred": [],
            "missing_preferred": ["Kubernetes"],
            "matched_technologies": ["Python", "Flask"],
            "missing_technologies": ["Docker"],
        },
        "ranked_projects": [
            {"project_id": "p1", "project_name": "CloudReport",
             "preliminary_score": 90.0, "semantic_score": 92.0,
             "final_project_score": 91.5, "matched_skills": ["Python"],
             "matched_technologies": ["Python"], "missing_relevant_skills": [],
             "reason": "Strong match."},
            {"project_id": "p2", "project_name": "InventIQ",
             "preliminary_score": 75.0, "semantic_score": 78.0,
             "final_project_score": 77.0, "matched_skills": ["Python", "Flask"],
             "matched_technologies": ["Python", "Flask"], "missing_relevant_skills": [],
             "reason": "Good match."},
            {"project_id": "p3", "project_name": "Threat Analyser",
             "preliminary_score": 55.0, "semantic_score": 60.0,
             "final_project_score": 58.0, "matched_skills": ["Python"],
             "matched_technologies": ["Python"], "missing_relevant_skills": [],
             "reason": "Moderate match."},
        ],
    }

    mock_projects = [
        {"_id": "p1", "name": "CloudReport", "year": "2024",
         "technologies": ["Python", "AWS"], "description": "Cloud pipeline.",
         "resume_bullets": ["Built cloud pipeline."], "keywords": [], "categories": [], "enabled": True},
        {"_id": "p2", "name": "InventIQ", "year": "2024",
         "technologies": ["Python", "Flask"], "description": "Inventory API.",
         "resume_bullets": ["Built REST API."], "keywords": [], "categories": [], "enabled": True},
        {"_id": "p3", "name": "Threat Analyser", "year": "2023",
         "technologies": ["Python", "Scikit-learn"], "description": "ML threat analysis.",
         "resume_bullets": ["Classified threats."], "keywords": [], "categories": [], "enabled": True},
    ]

    pdf_path = tmp_path / "resume.pdf"
    pdf_path.write_bytes(b"%PDF")

    @contextlib.contextmanager
    def _ctx():
        import phase_4.resume_tailor.firestore_service as fs
        from phase_4.resume_tailor import resume_pipeline as rp
        from resume_engine import resume_generator as rg

        with patch.object(fs, "get_match_result", return_value=mock_match_doc), \
             patch.object(fs, "get_jd_analysis", return_value={"analysis": {
                 "required_skills": ["Python", "Flask"],
                 "preferred_skills": ["Docker"],
                 "technologies": ["Python", "Flask", "Docker"],
                 "role_category": "Backend",
                 "job_title": "Backend Developer",
             }}), \
             patch.object(fs, "get_profile", return_value=mock_profile), \
             patch.object(fs, "get_all_skills_grouped",
                          return_value={"Programming Languages": ["Python", "Java"],
                                        "Web Development": ["Flask", "React"],
                                        "Other": ["AWS", "Docker"]}), \
             patch.object(fs, "get_all_projects", return_value=mock_projects), \
             patch.object(fs, "get_education", return_value=[]), \
             patch.object(fs, "get_experience", return_value=[]), \
             patch.object(fs, "get_certifications", return_value=[]), \
             patch.object(fs, "get_languages", return_value=[]), \
             patch.object(fs, "get_interests", return_value=[]), \
             patch.object(fs, "save_tailored_resume", return_value="mock-resume-id"), \
             patch.object(rg, "compile_pdf",
                          return_value=(compile_ok, pdf_path if compile_ok else None, "OK")), \
             patch.object(rg, "count_pdf_pages", return_value=page_count):
            yield

    return _ctx()


class TestResumePipeline:

    def test_pipeline_returns_tailored_resume_result(self, tmp_path):
        """Full pipeline produces a TailoredResumeResult."""
        from phase_4.resume_tailor.resume_pipeline import generate_tailored_resume
        from phase_4.resume_tailor.schemas import TailoredResumeResult

        with _make_full_mock_context(tmp_path, page_count=1):
            result = generate_tailored_resume("match-pipeline-test")

        assert isinstance(result, TailoredResumeResult)
        assert result.match_id == "match-pipeline-test"
        assert result.job_title == "Backend Developer"
        assert result.generation_status == "success"

    def test_output_goes_to_tailored_directory(self, tmp_path):
        """Generated .tex file goes to latex/output/tailored/<match_id>/, not latex/output/."""
        from phase_4.resume_tailor.resume_pipeline import generate_tailored_resume
        from phase_4.resume_tailor.config import config

        match_id = "match-output-dir-test"
        with _make_full_mock_context(tmp_path, page_count=1):
            result = generate_tailored_resume(match_id)

        assert "tailored" in result.tex_path
        assert match_id in result.tex_path
        # Must NOT be the standard Phase 1 output path
        assert str(config.LATEX_TEMPLATE_PATH) not in result.tex_path

    def test_different_match_ids_produce_isolated_outputs(self, tmp_path):
        """Two different match IDs must produce different output paths."""
        from phase_4.resume_tailor.config import config

        path_a = config.tailored_tex_path("match-A")
        path_b = config.tailored_tex_path("match-B")

        assert path_a != path_b
        assert "match-A" in str(path_a)
        assert "match-B" in str(path_b)

    def test_dry_run_skips_compilation(self, tmp_path):
        """--dry-run returns a result without compiling PDF."""
        from phase_4.resume_tailor.resume_pipeline import generate_tailored_resume

        with _make_full_mock_context(tmp_path, page_count=1):
            result = generate_tailored_resume("match-dry-run", dry_run=True)

        assert result.pdf_path is None
        assert result.page_count is None
        assert any("dry-run" in w.lower() for w in result.warnings)

    def test_selected_projects_correspond_to_phase3_ranking(self, tmp_path):
        """Selected projects follow Phase 3 ranking (highest score first)."""
        from phase_4.resume_tailor.resume_pipeline import generate_tailored_resume

        with _make_full_mock_context(tmp_path, page_count=1):
            result = generate_tailored_resume("match-ranking-test")

        # CloudReport (score 91.5) should come before InventIQ (77.0)
        assert result.selected_project_names[0] == "CloudReport"
        assert result.selected_project_names[1] == "InventIQ"

    def test_compilation_failure_results_in_failed_status(self, tmp_path):
        """If PDF compilation fails, generation_status is not 'success'."""
        from phase_4.resume_tailor.resume_pipeline import generate_tailored_resume

        with _make_full_mock_context(tmp_path, compile_ok=False):
            result = generate_tailored_resume("match-compile-fail")

        assert result.generation_status != "success"

    def test_parse_match_doc_normalises_structure(self):
        """_parse_match_doc correctly flattens the nested Phase 3 structure."""
        from phase_4.resume_tailor.resume_pipeline import _parse_match_doc

        raw = {
            "jd_document_id": "jd-abc",
            "job_title": "ML Engineer",
            "scores": {
                "overall": 75.0,
                "required_skills": 80.0,
                "preferred_skills": 60.0,
                "technologies": 70.0,
                "projects": 65.0,
            },
            "skill_match": {
                "matched_required": ["Python", "TensorFlow"],
                "missing_required": ["Kubernetes"],
                "matched_preferred": ["Docker"],
                "missing_preferred": [],
                "matched_technologies": ["Python"],
                "missing_technologies": ["Kubernetes"],
            },
            "ranked_projects": [],
        }

        parsed = _parse_match_doc(raw)

        assert parsed["jd_document_id"] == "jd-abc"
        assert parsed["job_title"] == "ML Engineer"
        assert parsed["overall_match_score"] == 75.0
        assert parsed["matched_required_skills"] == ["Python", "TensorFlow"]
        assert parsed["missing_required_skills"] == ["Kubernetes"]
        assert parsed["ranked_projects"] == []

    def test_match_not_found_raises_runtime_error(self, tmp_path):
        """Pipeline raises RuntimeError (not crashes silently) if match ID not found."""
        from phase_4.resume_tailor.resume_pipeline import generate_tailored_resume
        import phase_4.resume_tailor.firestore_service as fs

        with patch.object(fs, "get_match_result",
                          side_effect=ValueError("No job match found")):
            with pytest.raises(RuntimeError, match="Match result not found"):
                generate_tailored_resume("nonexistent-match-id")

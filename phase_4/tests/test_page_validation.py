"""
test_page_validation.py — Tests for PDF page count validation and overflow handling.

Tests:
  - 1-page PDF → success
  - 2-page PDF → success
  - 3-page PDF → overflow remediation triggered
  - Overflow drops lowest project and re-renders
  - After max iterations still > 2 → generation_status = "partial"
"""

import pytest
from unittest.mock import patch, MagicMock, call
from pathlib import Path


def _build_mock_match(ranked_projects=None):
    """Helper: build a minimal Phase 3 match dict."""
    if ranked_projects is None:
        ranked_projects = [
            {"project_id": f"p{i}", "project_name": f"Project {i}",
             "preliminary_score": float(100 - i*10), "semantic_score": float(90 - i*10),
             "final_project_score": float(95 - i*10), "matched_skills": [],
             "matched_technologies": [], "missing_relevant_skills": [], "reason": "Test."}
            for i in range(1, 6)
        ]
    return {
        "jd_document_id": "jd-page-test",
        "job_title": "Test Job",
        "scores": {"overall": 80.0, "required_skills": 80.0, "preferred_skills": 50.0,
                   "technologies": 70.0, "projects": 75.0},
        "skill_match": {
            "matched_required": ["Python"],
            "missing_required": [],
            "matched_preferred": [],
            "missing_preferred": [],
            "matched_technologies": ["Python"],
            "missing_technologies": [],
        },
        "ranked_projects": ranked_projects,
    }


def _build_mock_projects(n=5):
    """Build n mock project dicts."""
    return [
        {"_id": f"p{i}", "name": f"Project {i}", "year": "2024",
         "technologies": ["Python"], "description": f"Project {i} description.",
         "resume_bullets": [f"Bullet for project {i}."],
         "keywords": [], "categories": [], "enabled": True}
        for i in range(1, n + 1)
    ]


def _patch_pipeline(
    tmp_path,
    match_doc,
    projects,
    page_counts,    # list of page counts to return on successive calls
):
    """
    Context manager that patches the full pipeline for page-validation tests.
    `page_counts` is consumed one per compile_pdf call.
    """
    import contextlib

    mock_profile = {
        "name": "Test User", "email": "t@t.com", "phone": "000",
        "degree_title": "B.Tech", "linkedin": "https://linkedin.com/in/t",
        "github": "https://github.com/t", "location": "City",
        "summary": "Python developer.",
    }

    page_iter = iter(page_counts)

    @contextlib.contextmanager
    def _ctx():
        import phase_4.resume_tailor.firestore_service as fs
        from phase_4.resume_tailor import resume_pipeline as rp
        from resume_engine import resume_generator as rg

        pdf_path = tmp_path / "resume.pdf"
        pdf_path.write_bytes(b"%PDF")

        with patch.object(fs, "get_match_result", return_value=match_doc), \
             patch.object(fs, "get_jd_analysis", return_value={"analysis": {
                 "required_skills": ["Python"], "preferred_skills": [],
                 "technologies": ["Python"], "role_category": "Backend"}}), \
             patch.object(fs, "get_profile", return_value=mock_profile), \
             patch.object(fs, "get_all_skills_grouped", return_value={"Lang": ["Python"]}), \
             patch.object(fs, "get_all_projects", return_value=projects), \
             patch.object(fs, "get_education", return_value=[]), \
             patch.object(fs, "get_experience", return_value=[]), \
             patch.object(fs, "get_certifications", return_value=[]), \
             patch.object(fs, "get_languages", return_value=[]), \
             patch.object(fs, "get_interests", return_value=[]), \
             patch.object(fs, "save_tailored_resume", return_value="saved-id"), \
             patch.object(rp, "_write_tailored_tex", return_value=tmp_path / "resume.tex"), \
             patch.object(rg, "compile_pdf", return_value=(True, pdf_path, "OK")), \
             patch.object(rg, "count_pdf_pages", side_effect=lambda _: next(page_iter, 1)):
            yield

    return _ctx()


class TestPageValidation:

    def test_one_page_pdf_is_success(self, tmp_path):
        """A 1-page PDF produces generation_status='success'."""
        from phase_4.resume_tailor.resume_pipeline import generate_tailored_resume

        with _patch_pipeline(
            tmp_path,
            match_doc=_build_mock_match(),
            projects=_build_mock_projects(3),
            page_counts=[1],
        ):
            result = generate_tailored_resume("match-page-1")

        assert result.generation_status == "success"
        assert result.page_count == 1

    def test_two_page_pdf_is_success(self, tmp_path):
        """A 2-page PDF produces generation_status='success'."""
        from phase_4.resume_tailor.resume_pipeline import generate_tailored_resume

        with _patch_pipeline(
            tmp_path,
            match_doc=_build_mock_match(),
            projects=_build_mock_projects(3),
            page_counts=[2],
        ):
            result = generate_tailored_resume("match-page-2")

        assert result.generation_status == "success"
        assert result.page_count == 2

    def test_three_page_triggers_overflow_and_succeeds(self, tmp_path):
        """
        A 3-page PDF triggers overflow remediation.
        Second compile (after dropping one project) returns 2 pages → success.
        """
        from phase_4.resume_tailor.resume_pipeline import generate_tailored_resume

        with _patch_pipeline(
            tmp_path,
            match_doc=_build_mock_match(),
            projects=_build_mock_projects(3),
            page_counts=[3, 2],   # first attempt = 3 pages, after drop = 2 pages
        ):
            result = generate_tailored_resume("match-overflow-1")

        assert result.generation_status == "success"
        assert result.page_count == 2

    def test_persistent_overflow_becomes_partial(self, tmp_path):
        """
        If overflow persists after MAX_OVERFLOW_RETRIES drops,
        generation_status becomes 'partial'.
        """
        from phase_4.resume_tailor.resume_pipeline import generate_tailored_resume
        from phase_4.resume_tailor.config import config

        # Always return 3 pages regardless of iteration
        always_3_pages = [3] * (config.MAX_OVERFLOW_RETRIES + 1)

        with _patch_pipeline(
            tmp_path,
            match_doc=_build_mock_match(),
            projects=_build_mock_projects(5),
            page_counts=always_3_pages,
        ):
            result = generate_tailored_resume("match-persistent-overflow")

        # Should be partial with a warning
        assert result.generation_status == "partial"
        assert any("page" in w.lower() or "overflow" in w.lower() for w in result.warnings)

    def test_overflow_does_not_modify_master_template(self, tmp_path):
        """
        Even during overflow remediation, the master template file stays unchanged.
        """
        import hashlib
        from phase_4.resume_tailor.resume_pipeline import generate_tailored_resume
        from phase_4.resume_tailor.config import config

        template_path = config.LATEX_TEMPLATE_PATH
        if not template_path.exists():
            pytest.skip("Master template not present in test environment.")

        def sha(p):
            h = hashlib.sha256()
            with open(p, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            return h.hexdigest()

        before = sha(template_path)

        with _patch_pipeline(
            tmp_path,
            match_doc=_build_mock_match(),
            projects=_build_mock_projects(3),
            page_counts=[3, 2],
        ):
            generate_tailored_resume("match-overflow-immutability")

        after = sha(template_path)
        assert before == after, "Master template was modified during overflow handling!"

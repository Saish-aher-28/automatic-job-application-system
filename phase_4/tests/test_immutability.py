"""
test_immutability.py — Verifies that the master LaTeX template is NEVER modified.

test_master_template_unchanged is the key acceptance test for Phase 4.
"""

import hashlib
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from phase_4.resume_tailor.config import config


def _hash_file(path: Path) -> str:
    """Return SHA-256 hex digest of a file's byte content."""
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def test_master_template_unchanged(tmp_path):
    """
    CRITICAL ACCEPTANCE TEST.

    The master LaTeX template (latex/resume_tex.tex) must be byte-identical
    before and after any Phase 4 pipeline operation.

    This test:
      1. Records the SHA-256 hash of the template before running Phase 4.
      2. Runs the Phase 4 pipeline (with a mocked Firestore + renderer).
      3. Records the SHA-256 hash again after.
      4. Asserts the hashes are identical.
    """
    template_path = config.LATEX_TEMPLATE_PATH
    assert template_path.exists(), (
        f"Master template not found at {template_path}. "
        "Cannot verify immutability without the original file."
    )

    # ── Step 1: Record pre-run hash ──────────────────────────────────────────
    hash_before = _hash_file(template_path)

    # ── Step 2: Run Phase 4 pipeline (fully mocked, no real Firestore) ───────
    with _mocked_pipeline_context(tmp_path):
        from phase_4.resume_tailor.resume_pipeline import generate_tailored_resume
        try:
            generate_tailored_resume("mock-match-id-immutability-test")
        except Exception:
            pass  # We only care about template immutability, not pipeline success

    # ── Step 3: Record post-run hash ─────────────────────────────────────────
    hash_after = _hash_file(template_path)

    # ── Step 4: Assert identical ─────────────────────────────────────────────
    assert hash_before == hash_after, (
        "CRITICAL: Master LaTeX template was modified by Phase 4!\n"
        f"Template path: {template_path}\n"
        f"Hash before: {hash_before}\n"
        f"Hash after:  {hash_after}"
    )


def test_template_path_is_correct():
    """The configured template path points to the expected master file."""
    assert config.LATEX_TEMPLATE_PATH.name == "resume_tex.tex"
    assert config.LATEX_TEMPLATE_PATH.exists()


def test_tailored_output_does_not_use_template_path(tmp_path):
    """
    Tailored output goes to a DIFFERENT path than the master template.
    The output path must never equal the template path.
    """
    match_id = "test-match-immutability"
    out_tex = config.tailored_tex_path(match_id)
    assert out_tex != config.LATEX_TEMPLATE_PATH
    assert "tailored" in str(out_tex)
    assert match_id in str(out_tex)


# ── Helper: mock the pipeline so no real Firestore / compilation runs ─────────

def _mocked_pipeline_context(tmp_path):
    """
    Context manager that patches the key pipeline dependencies so:
    - No real Firestore calls are made
    - No real LaTeX compilation happens
    - The master template file itself is READ (by render_resume) but never written to
    """
    import contextlib

    mock_match = {
        "jd_document_id": "jd-doc-001",
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
        "ranked_projects": [
            {"project_id": "p1", "project_name": "Test Project",
             "preliminary_score": 80.0, "semantic_score": 85.0,
             "final_project_score": 83.0, "matched_skills": ["Python"],
             "matched_technologies": ["Python"], "missing_relevant_skills": [],
             "reason": "Test."},
        ],
    }

    mock_profile = {
        "name": "Test User", "email": "test@example.com",
        "phone": "+1 000", "degree_title": "B.Tech IT",
        "linkedin": "https://linkedin.com/in/testuser",
        "github": "https://github.com/testuser",
        "location": "Test City",
        "summary": "Test summary with Python skills.",
    }

    mock_project = {
        "_id": "p1", "name": "Test Project", "year": "2024",
        "technologies": ["Python"], "description": "A test project.",
        "resume_bullets": ["Did something."], "enabled": True,
        "keywords": [], "categories": [],
    }

    @contextlib.contextmanager
    def _ctx():
        import phase_4.resume_tailor.firestore_service as fs
        with patch.object(fs, "_get_firestore_client"):
            with patch.object(fs, "get_match_result", return_value=mock_match):
                with patch.object(fs, "get_jd_analysis", return_value={"analysis": {
                    "job_title": "Test Job", "required_skills": ["Python"],
                    "preferred_skills": [], "technologies": ["Python"],
                    "role_category": "Backend",
                }}):
                    with patch.object(fs, "get_profile", return_value=mock_profile):
                        with patch.object(fs, "get_all_skills_grouped",
                                          return_value={"Programming Languages": ["Python"]}):
                            with patch.object(fs, "get_all_projects",
                                              return_value=[mock_project]):
                                with patch.object(fs, "get_education", return_value=[]):
                                    with patch.object(fs, "get_experience", return_value=[]):
                                        with patch.object(fs, "get_certifications", return_value=[]):
                                            with patch.object(fs, "get_languages", return_value=[]):
                                                with patch.object(fs, "get_interests", return_value=[]):
                                                    with patch.object(fs, "save_tailored_resume",
                                                                      return_value="mock-resume-id"):
                                                        from phase_4.resume_tailor import resume_pipeline as rp
                                                        with patch.object(rp, "_write_tailored_tex",
                                                                          return_value=tmp_path / "resume.tex"):
                                                            from resume_engine import resume_generator as rg
                                                            with patch.object(rg, "compile_pdf",
                                                                              return_value=(True, tmp_path / "resume.pdf", "OK")):
                                                                with patch.object(rg, "count_pdf_pages",
                                                                                  return_value=1):
                                                                    yield

    return _ctx()

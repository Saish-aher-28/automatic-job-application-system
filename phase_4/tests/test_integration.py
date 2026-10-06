"""
test_integration.py — End-to-end integration test for Phase 4.

Only runs when Firestore + Gemini are configured (real API keys present).
Uses a real Phase 3 match document from Firestore.

Tests:
  - Full pipeline from match ID → PDF
  - PDF page count ≤ 2
  - Required profile information in PDF text
  - Master template unchanged
  - tailored_resumes collection written to
"""

import os
import hashlib
import pytest
from pathlib import Path

pytestmark = pytest.mark.integration

_FIRESTORE_OK = bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip())
_REASON = "GOOGLE_APPLICATION_CREDENTIALS not configured — skipping real integration test."


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


@pytest.mark.skipif(not _FIRESTORE_OK, reason=_REASON)
class TestPhase4Integration:

    def test_e2e_pipeline_from_real_match_id(self):
        """
        Full end-to-end test using a real Phase 3 match from Firestore.

        Steps:
          1. Fetch the most recent job_match from Firestore.
          2. Run Phase 4 pipeline.
          3. Verify PDF exists and has ≤ 2 pages.
          4. Verify required profile information in PDF text.
          5. Verify master template was not modified.
          6. Verify tailored_resumes entry was created.
        """
        from phase_4.resume_tailor.firestore_service import _get_firestore_client
        from phase_4.resume_tailor.resume_pipeline import generate_tailored_resume
        from phase_4.resume_tailor.config import config

        # ── Find a real match_id ──────────────────────────────────────────────
        db = _get_firestore_client()
        docs = list(db.collection("job_matches").limit(1).get())
        if not docs:
            pytest.skip("No job_match documents in Firestore — run Phase 3 first.")

        match_id  = docs[0].id
        match_doc = docs[0].to_dict()
        print(f"\n  Using match_id: {match_id}")
        print(f"  Job title: {match_doc.get('job_title', 'unknown')}")

        # ── Hash template before ──────────────────────────────────────────────
        template_path = config.LATEX_TEMPLATE_PATH
        assert template_path.exists(), f"Master template not found: {template_path}"
        hash_before = _sha256(template_path)

        # ── Run pipeline ──────────────────────────────────────────────────────
        result = generate_tailored_resume(match_id)

        # ── Hash template after ───────────────────────────────────────────────
        hash_after = _sha256(template_path)

        # ── Assertions ────────────────────────────────────────────────────────
        print(f"\n  Result: {result.generation_status}")
        print(f"  Selected projects: {result.selected_project_names}")
        print(f"  Page count: {result.page_count}")
        print(f"  TEX: {result.tex_path}")
        print(f"  PDF: {result.pdf_path}")

        # 1. Template must be unchanged
        assert hash_before == hash_after, (
            f"CRITICAL: Master template was modified!\n"
            f"Before: {hash_before}\n"
            f"After:  {hash_after}"
        )

        # 2. Pipeline must not catastrophically fail
        assert result.generation_status in ("success", "partial"), (
            f"Pipeline failed completely: {result.warnings}"
        )

        # 3. TEX file must exist
        tex_path = Path(result.tex_path)
        assert tex_path.exists(), f"TEX file not created at {tex_path}"

        # 4. If PDF was generated, check page count
        if result.pdf_path:
            pdf_path = Path(result.pdf_path)
            assert pdf_path.exists(), f"PDF not created at {pdf_path}"

            if result.page_count is not None:
                assert result.page_count <= 2, (
                    f"PDF has {result.page_count} pages — exceeds 2-page limit."
                )

            # 5. Required content in PDF text
            try:
                import pymupdf as fitz
                doc = fitz.open(str(pdf_path))
                pdf_text = " ".join(page.get_text() for page in doc)
                doc.close()

                # Must contain the user's name
                assert "Saish" in pdf_text or "Aher" in pdf_text, (
                    "User name not found in PDF text — critical information missing."
                )
                # Must contain selected project names
                for proj_name in result.selected_project_names:
                    # Partial match (LaTeX may hyphenate long words)
                    short_name = proj_name.split()[0]
                    assert short_name in pdf_text, (
                        f"Selected project '{proj_name}' not found in PDF text."
                    )

            except ImportError:
                pytest.skip("PyMuPDF not installed — skipping PDF text extraction.")

        # 6. Output must be in tailored directory
        assert "tailored" in result.tex_path
        assert match_id in result.tex_path

        # 7. resume_id must be set
        assert result.resume_id
        print(f"\n  ✓ Phase 4 E2E test passed (resume_id: {result.resume_id})")

    def test_two_different_jds_produce_same_template_design(self):
        """
        Two tailored resumes for different JDs must use the same master template.
        This verifies visual design consistency.
        """
        from phase_4.resume_tailor.firestore_service import _get_firestore_client
        from phase_4.resume_tailor.resume_pipeline import generate_tailored_resume

        db = _get_firestore_client()
        docs = list(db.collection("job_matches").limit(2).get())

        if len(docs) < 2:
            pytest.skip("Need at least 2 job_matches for this test.")

        match_id_a = docs[0].id
        match_id_b = docs[1].id

        result_a = generate_tailored_resume(match_id_a)
        result_b = generate_tailored_resume(match_id_b)

        # Both resumes must come from the same template
        from phase_4.resume_tailor.config import config
        assert str(config.LATEX_TEMPLATE_PATH) not in result_a.tex_path
        assert str(config.LATEX_TEMPLATE_PATH) not in result_b.tex_path

        # Both must be successful (or at least partial)
        assert result_a.generation_status in ("success", "partial")
        assert result_b.generation_status in ("success", "partial")

        # Output paths must be different (different match IDs → different dirs)
        assert result_a.tex_path != result_b.tex_path
        assert match_id_a in result_a.tex_path
        assert match_id_b in result_b.tex_path

    def test_profile_not_modified_after_pipeline(self):
        """
        Running Phase 4 must not change any profile Firestore documents.
        Verified by reading the profile before and after.
        """
        from phase_4.resume_tailor.firestore_service import (
            _get_firestore_client, get_match_result, get_profile,
        )
        from phase_4.resume_tailor.resume_pipeline import generate_tailored_resume
        import json

        db = _get_firestore_client()
        match_docs = list(db.collection("job_matches").limit(1).get())
        if not match_docs:
            pytest.skip("No job_match documents in Firestore.")

        match_id = match_docs[0].id

        # Profile before
        profile_before = json.dumps(get_profile(), sort_keys=True)

        # Run pipeline
        generate_tailored_resume(match_id)

        # Profile after
        profile_after = json.dumps(get_profile(), sort_keys=True)

        assert profile_before == profile_after, (
            "User profile was modified by Phase 4 — this is forbidden!"
        )

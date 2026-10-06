"""
test_firestore.py — Unit tests for Phase 4 Firestore operations (mocked).

Tests:
  - save_tailored_resume stores required schema fields
  - get_match_result raises ValueError for nonexistent doc
  - Tailored resume document has all required Firestore fields
  - Phase 3 match collection is never written to
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone


def _make_mock_db(doc_id="saved-resume-id-xyz"):
    mock_db = MagicMock()
    mock_doc_ref = MagicMock()
    mock_doc_ref.id = doc_id
    mock_db.collection.return_value.add.return_value = (MagicMock(), mock_doc_ref)
    return mock_db


class TestFirestoreService:

    def test_save_tailored_resume_returns_doc_id(self):
        """save_tailored_resume returns the auto-generated Firestore doc ID."""
        from phase_4.resume_tailor import firestore_service as fs

        mock_db = _make_mock_db("new-resume-abc")
        with patch.object(fs, "_get_firestore_client", return_value=mock_db):
            doc_id = fs.save_tailored_resume({
                "resume_id": "r1",
                "match_id": "m1",
                "job_title": "Backend Developer",
            })

        assert doc_id == "new-resume-abc"
        mock_db.collection.assert_called_once_with("tailored_resumes")

    def test_save_tailored_resume_stores_required_fields(self):
        """save_tailored_resume stores all required Firestore schema fields."""
        from phase_4.resume_tailor import firestore_service as fs

        mock_db = MagicMock()
        captured_data = {}

        def capture_add(data):
            captured_data.update(data)
            ref = MagicMock()
            ref.id = "captured-id"
            return (MagicMock(), ref)

        mock_db.collection.return_value.add.side_effect = capture_add

        payload = {
            "resume_id": "resume-001",
            "match_id": "match-abc",
            "jd_document_id": "jd-xyz",
            "job_title": "Backend Developer",
            "generator_version": "4.0",
            "selected_projects": ["CloudReport", "InventIQ"],
            "selected_project_ids": ["p1", "p2"],
            "emphasized_skills": ["Python", "AWS"],
            "page_count": 2,
            "generation_status": "success",
            "tex_path": "latex/output/tailored/match-abc/resume.tex",
            "pdf_path": "latex/output/tailored/match-abc/resume.pdf",
            "warnings": [],
        }

        with patch.object(fs, "_get_firestore_client", return_value=mock_db):
            fs.save_tailored_resume(payload)

        # Verify all required schema fields are stored
        for key in payload:
            assert key in captured_data, f"Required field '{key}' missing from Firestore document."

        # created_at is auto-injected
        assert "created_at" in captured_data

    def test_get_match_result_raises_for_nonexistent_doc(self):
        """get_match_result raises ValueError when doc doesn't exist."""
        from phase_4.resume_tailor import firestore_service as fs

        mock_db = MagicMock()
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        with patch.object(fs, "_get_firestore_client", return_value=mock_db):
            with pytest.raises(ValueError, match="No job match found"):
                fs.get_match_result("nonexistent-id")

    def test_get_match_result_returns_data(self):
        """get_match_result returns the Firestore document dict."""
        from phase_4.resume_tailor import firestore_service as fs

        expected_data = {
            "jd_document_id": "jd-123",
            "scores": {"overall": 82.0},
        }
        mock_db = MagicMock()
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = expected_data
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        with patch.object(fs, "_get_firestore_client", return_value=mock_db):
            result = fs.get_match_result("existing-match-id")

        assert result["jd_document_id"] == "jd-123"
        assert result["scores"]["overall"] == 82.0

    def test_job_matches_never_written_to(self):
        """
        save_tailored_resume must NEVER write to 'job_matches' collection.
        Only 'tailored_resumes' is allowed as a write target.
        """
        from phase_4.resume_tailor import firestore_service as fs

        mock_db = _make_mock_db()
        with patch.object(fs, "_get_firestore_client", return_value=mock_db):
            fs.save_tailored_resume({"match_id": "m1", "job_title": "Test"})

        # Verify the only collection call is for tailored_resumes
        call_args = [str(c) for c in mock_db.collection.call_args_list]
        for arg in call_args:
            assert "job_matches" not in arg, (
                "save_tailored_resume wrote to job_matches — this is forbidden!"
            )

    def test_auto_adds_created_at_if_missing(self):
        """save_tailored_resume automatically injects created_at timestamp."""
        from phase_4.resume_tailor import firestore_service as fs

        mock_db = MagicMock()
        captured = {}

        def capture_add(data):
            captured.update(data)
            ref = MagicMock()
            ref.id = "id"
            return (MagicMock(), ref)

        mock_db.collection.return_value.add.side_effect = capture_add

        with patch.object(fs, "_get_firestore_client", return_value=mock_db):
            fs.save_tailored_resume({"match_id": "m1"})  # no created_at provided

        assert "created_at" in captured
        # Verify it's a valid ISO-8601 string
        datetime.fromisoformat(captured["created_at"])

    def test_generator_version_is_stored(self):
        """generator_version = '4.0' is stored in the Firestore document."""
        from phase_4.resume_tailor import firestore_service as fs
        from phase_4.resume_tailor.config import config

        mock_db = MagicMock()
        captured = {}

        def capture_add(data):
            captured.update(data)
            ref = MagicMock()
            ref.id = "id"
            return (MagicMock(), ref)

        mock_db.collection.return_value.add.side_effect = capture_add

        with patch.object(fs, "_get_firestore_client", return_value=mock_db):
            fs.save_tailored_resume({"match_id": "m1"})

        assert captured.get("generator_version") == config.GENERATOR_VERSION

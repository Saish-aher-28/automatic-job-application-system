"""
test_firestore.py — Tests for Phase 2 Firestore operations.

Uses mocked Firestore — no real Firebase connection required.
"""

import pytest
from unittest.mock import MagicMock, patch
from phase_2.jd_analyzer.schemas import JDAnalysis


SAMPLE_ANALYSIS = JDAnalysis(
    job_title="Backend Developer",
    role_category="Backend",
    required_skills=["Python", "Flask"],
    preferred_skills=["Docker"],
    technologies=["Python", "Flask", "AWS"],
    keywords=["python", "backend"],
)

SAMPLE_RAW_TEXT = "We need a Python backend developer with Flask experience."
SAMPLE_MODEL    = "gemini-3.1-flash-lite"


def _make_mock_db(doc_id: str = "test-doc-123"):
    """Return a MagicMock Firestore client."""
    mock_db = MagicMock()
    mock_doc_ref = MagicMock()
    mock_doc_ref.id = doc_id
    mock_db.collection.return_value.add.return_value = (MagicMock(), mock_doc_ref)
    return mock_db


class TestSaveJDAnalysis:

    def test_returns_document_id(self):
        from phase_2.jd_analyzer import firestore_service
        mock_db = _make_mock_db("generated-id-abc")
        with patch.object(firestore_service, "_get_firestore_client", return_value=mock_db):
            doc_id = firestore_service.save_jd_analysis(
                SAMPLE_RAW_TEXT, SAMPLE_ANALYSIS, SAMPLE_MODEL
            )
        assert doc_id == "generated-id-abc"

    def test_adds_to_correct_collection(self):
        from phase_2.jd_analyzer import firestore_service
        from phase_2.jd_analyzer.config import config
        mock_db = _make_mock_db()
        with patch.object(firestore_service, "_get_firestore_client", return_value=mock_db):
            firestore_service.save_jd_analysis(
                SAMPLE_RAW_TEXT, SAMPLE_ANALYSIS, SAMPLE_MODEL
            )
        mock_db.collection.assert_called_once_with(config.FIRESTORE_JD_COLLECTION)

    def test_raw_text_preserved_in_document(self):
        from phase_2.jd_analyzer import firestore_service
        mock_db = _make_mock_db()
        saved_data = {}

        def capture_add(data):
            saved_data.update(data)
            ref = MagicMock()
            ref.id = "abc"
            return (MagicMock(), ref)

        mock_db.collection.return_value.add.side_effect = capture_add
        with patch.object(firestore_service, "_get_firestore_client", return_value=mock_db):
            firestore_service.save_jd_analysis(
                SAMPLE_RAW_TEXT, SAMPLE_ANALYSIS, SAMPLE_MODEL
            )
        assert saved_data["raw_text"] == SAMPLE_RAW_TEXT

    def test_analysis_stored_as_dict(self):
        from phase_2.jd_analyzer import firestore_service
        mock_db = _make_mock_db()
        saved_data = {}

        def capture_add(data):
            saved_data.update(data)
            ref = MagicMock()
            ref.id = "abc"
            return (MagicMock(), ref)

        mock_db.collection.return_value.add.side_effect = capture_add
        with patch.object(firestore_service, "_get_firestore_client", return_value=mock_db):
            firestore_service.save_jd_analysis(
                SAMPLE_RAW_TEXT, SAMPLE_ANALYSIS, SAMPLE_MODEL
            )
        assert isinstance(saved_data["analysis"], dict)
        assert saved_data["analysis"]["job_title"] == "Backend Developer"

    def test_model_name_stored(self):
        from phase_2.jd_analyzer import firestore_service
        mock_db = _make_mock_db()
        saved_data = {}

        def capture_add(data):
            saved_data.update(data)
            ref = MagicMock()
            ref.id = "abc"
            return (MagicMock(), ref)

        mock_db.collection.return_value.add.side_effect = capture_add
        with patch.object(firestore_service, "_get_firestore_client", return_value=mock_db):
            firestore_service.save_jd_analysis(
                SAMPLE_RAW_TEXT, SAMPLE_ANALYSIS, SAMPLE_MODEL
            )
        assert saved_data["model"] == SAMPLE_MODEL

    def test_analysis_version_stored(self):
        from phase_2.jd_analyzer import firestore_service
        mock_db = _make_mock_db()
        saved_data = {}

        def capture_add(data):
            saved_data.update(data)
            ref = MagicMock()
            ref.id = "xyz"
            return (MagicMock(), ref)

        mock_db.collection.return_value.add.side_effect = capture_add
        with patch.object(firestore_service, "_get_firestore_client", return_value=mock_db):
            firestore_service.save_jd_analysis(
                SAMPLE_RAW_TEXT, SAMPLE_ANALYSIS, SAMPLE_MODEL
            )
        assert saved_data["analysis_version"] == "1.0"

    def test_created_at_stored(self):
        from phase_2.jd_analyzer import firestore_service
        mock_db = _make_mock_db()
        saved_data = {}

        def capture_add(data):
            saved_data.update(data)
            ref = MagicMock()
            ref.id = "ts"
            return (MagicMock(), ref)

        mock_db.collection.return_value.add.side_effect = capture_add
        with patch.object(firestore_service, "_get_firestore_client", return_value=mock_db):
            firestore_service.save_jd_analysis(
                SAMPLE_RAW_TEXT, SAMPLE_ANALYSIS, SAMPLE_MODEL
            )
        assert "created_at" in saved_data
        assert saved_data["created_at"]  # non-empty


class TestGetJDAnalysis:

    def test_returns_document_data(self):
        from phase_2.jd_analyzer import firestore_service
        mock_db = MagicMock()
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "raw_text": SAMPLE_RAW_TEXT,
            "analysis": SAMPLE_ANALYSIS.model_dump(),
            "model": SAMPLE_MODEL,
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        with patch.object(firestore_service, "_get_firestore_client", return_value=mock_db):
            result = firestore_service.get_jd_analysis("test-doc-123")

        assert result["raw_text"] == SAMPLE_RAW_TEXT

    def test_raises_for_nonexistent_document(self):
        from phase_2.jd_analyzer import firestore_service
        mock_db = MagicMock()
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        with patch.object(firestore_service, "_get_firestore_client", return_value=mock_db):
            with pytest.raises(ValueError, match="No JD analysis found"):
                firestore_service.get_jd_analysis("nonexistent-id")

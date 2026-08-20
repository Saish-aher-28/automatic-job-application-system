"""
test_firestore.py — Unit tests for Phase 3 Firestore operations (mocked database).
"""

import pytest
from unittest.mock import MagicMock, patch
from phase_3.matcher.schemas import JobMatchResult, ProjectMatchDetail


SAMPLE_MATCH_RESULT = JobMatchResult(
    jd_document_id="jd-doc-123",
    job_title="Backend Developer",
    overall_match_score=85.5,
    required_skill_match_score=100.0,
    preferred_skill_match_score=50.0,
    technology_match_score=80.0,
    project_relevance_score=90.0,
    matched_required_skills=["Python", "Flask"],
    missing_required_skills=[],
    matched_preferred_skills=["Docker"],
    missing_preferred_skills=["Kubernetes"],
    matched_technologies=["Python", "Flask", "Docker"],
    missing_technologies=["PostgreSQL"],
    ranked_projects=[
        ProjectMatchDetail(
            project_id="p1",
            project_name="CloudReport",
            preliminary_score=80.0,
            semantic_score=90.0,
            final_project_score=87.0,
            matched_skills=["Python"],
            matched_technologies=["Python"],
            missing_relevant_skills=[],
            reason="Strong relevance.",
        )
    ],
)


def _make_mock_db(doc_id: str = "generated-match-123"):
    mock_db = MagicMock()
    mock_doc_ref = MagicMock()
    mock_doc_ref.id = doc_id
    mock_db.collection.return_value.add.return_value = (MagicMock(), mock_doc_ref)
    return mock_db


class TestFirestoreServiceMocked:

    def test_save_match_result_returns_doc_id(self):
        from phase_3.matcher import firestore_service
        mock_db = _make_mock_db("match-id-xyz")

        with patch.object(firestore_service, "_get_firestore_client", return_value=mock_db):
            doc_id = firestore_service.save_match_result(SAMPLE_MATCH_RESULT)

        assert doc_id == "match-id-xyz"
        mock_db.collection.assert_called_once_with("job_matches")

    def test_save_match_result_saves_expected_structure(self):
        from phase_3.matcher import firestore_service
        mock_db = _make_mock_db()
        captured_data = {}

        def capture_add(data):
            captured_data.update(data)
            ref = MagicMock()
            ref.id = "captured-id"
            return (MagicMock(), ref)

        mock_db.collection.return_value.add.side_effect = capture_add

        with patch.object(firestore_service, "_get_firestore_client", return_value=mock_db):
            firestore_service.save_match_result(SAMPLE_MATCH_RESULT)

        assert captured_data["jd_document_id"] == "jd-doc-123"
        assert captured_data["scores"]["overall"] == 85.5
        assert captured_data["scores"]["projects"] == 90.0
        assert captured_data["skill_match"]["matched_required"] == ["Python", "Flask"]
        assert captured_data["skill_match"]["missing_preferred"] == ["Kubernetes"]
        assert len(captured_data["ranked_projects"]) == 1
        assert captured_data["matcher_version"] == "1.0"
        assert "created_at" in captured_data

    def test_get_match_result_returns_data(self):
        from phase_3.matcher import firestore_service
        mock_db = MagicMock()
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "jd_document_id": "jd-doc-123",
            "scores": {"overall": 85.5},
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        with patch.object(firestore_service, "_get_firestore_client", return_value=mock_db):
            res = firestore_service.get_match_result("match-id-abc")

        assert res["jd_document_id"] == "jd-doc-123"
        assert res["scores"]["overall"] == 85.5

    def test_get_match_result_raises_for_nonexistent_doc(self):
        from phase_3.matcher import firestore_service
        mock_db = MagicMock()
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        with patch.object(firestore_service, "_get_firestore_client", return_value=mock_db):
            with pytest.raises(ValueError, match="No match result found"):
                firestore_service.get_match_result("nonexistent-match-id")

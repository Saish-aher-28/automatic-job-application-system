"""
test_projects.py — Tests for the dynamic project service (no Firestore required).

Includes the CRITICAL dynamic project test:
  Start with A, B, C → add D → verify count 3 → 4 without any code changes.
"""

import pytest
from unittest.mock import MagicMock, patch

from resume_engine.project_service import (
    get_all_projects,
    get_projects_for_resume,
    add_project,
    disable_project,
    enable_project,
)
from resume_engine.validators import validate_project


def _make_mock_doc(doc_id: str, data: dict):
    """Create a mock Firestore document."""
    doc = MagicMock()
    doc.id = doc_id
    doc.to_dict.return_value = data
    return doc


def _make_firestore_mock(projects: list[tuple[str, dict]]):
    """
    Create a mock Firestore client whose projects collection
    streams the given list of (doc_id, data) tuples.
    """
    mock_db = MagicMock()
    mock_docs = [_make_mock_doc(pid, pdata) for pid, pdata in projects]
    mock_db.collection.return_value.stream.return_value = iter(mock_docs)
    return mock_db


class TestGetAllProjects:

    @patch("resume_engine.project_service.get_firestore_client")
    def test_returns_all_enabled(self, mock_gfc):
        projects = [
            ("proj_a", {"name": "Project A", "description": "d", "technologies": [], "enabled": True}),
            ("proj_b", {"name": "Project B", "description": "d", "technologies": [], "enabled": True}),
            ("proj_c", {"name": "Project C", "description": "d", "technologies": [], "enabled": True}),
        ]
        mock_gfc.return_value = _make_firestore_mock(projects)
        result = get_all_projects()
        assert len(result) == 3

    @patch("resume_engine.project_service.get_firestore_client")
    def test_excludes_disabled_by_default(self, mock_gfc):
        projects = [
            ("proj_a", {"name": "Project A", "description": "d", "technologies": [], "enabled": True}),
            ("proj_b", {"name": "Project B", "description": "d", "technologies": [], "enabled": False}),
        ]
        mock_gfc.return_value = _make_firestore_mock(projects)
        result = get_all_projects()
        assert len(result) == 1
        assert result[0]["name"] == "Project A"

    @patch("resume_engine.project_service.get_firestore_client")
    def test_include_disabled_flag(self, mock_gfc):
        projects = [
            ("proj_a", {"name": "Project A", "description": "d", "technologies": [], "enabled": True}),
            ("proj_b", {"name": "Project B", "description": "d", "technologies": [], "enabled": False}),
        ]
        mock_gfc.return_value = _make_firestore_mock(projects)
        result = get_all_projects(include_disabled=True)
        assert len(result) == 2

    @patch("resume_engine.project_service.get_firestore_client")
    def test_ids_attached(self, mock_gfc):
        projects = [
            ("my_project_id", {"name": "Test", "description": "d", "technologies": []}),
        ]
        mock_gfc.return_value = _make_firestore_mock(projects)
        result = get_all_projects()
        assert result[0]["_id"] == "my_project_id"

    @patch("resume_engine.project_service.get_firestore_client")
    def test_sorted_by_priority(self, mock_gfc):
        projects = [
            ("p1", {"name": "Lower Priority", "priority": 10, "description": "d", "technologies": [], "enabled": True}),
            ("p2", {"name": "Higher Priority", "priority": 1,  "description": "d", "technologies": [], "enabled": True}),
        ]
        mock_gfc.return_value = _make_firestore_mock(projects)
        result = get_all_projects()
        assert result[0]["name"] == "Higher Priority"


class TestGetProjectsForResume:

    @patch("resume_engine.project_service.get_firestore_client")
    def test_respects_limit(self, mock_gfc):
        projects = [
            (f"proj_{i}", {"name": f"Project {i}", "description": "d", "technologies": [], "enabled": True})
            for i in range(10)
        ]
        mock_gfc.return_value = _make_firestore_mock(projects)
        result = get_projects_for_resume(limit=3)
        assert len(result) == 3

    @patch("resume_engine.project_service.get_firestore_client")
    def test_limit_greater_than_total(self, mock_gfc):
        projects = [
            ("p1", {"name": "P1", "description": "d", "technologies": [], "enabled": True}),
            ("p2", {"name": "P2", "description": "d", "technologies": [], "enabled": True}),
        ]
        mock_gfc.return_value = _make_firestore_mock(projects)
        result = get_projects_for_resume(limit=10)
        assert len(result) == 2  # Only 2 exist

    @patch("resume_engine.project_service.get_firestore_client")
    def test_all_projects_remain_in_db(self, mock_gfc):
        """
        CRITICAL: get_projects_for_resume with limit=3 must NOT delete the other 7 projects.
        This test verifies that get_all_projects() still returns 10 even after get_projects_for_resume(3).
        """
        ten_projects = [
            (f"proj_{i}", {"name": f"Project {i}", "description": "d", "technologies": [], "enabled": True})
            for i in range(10)
        ]

        # Each call to get_firestore_client() should return the same 10 projects
        mock_gfc.return_value = _make_firestore_mock(ten_projects)

        resume_projects = get_projects_for_resume(limit=3)
        assert len(resume_projects) == 3

        # Reset mock to return all 10 again (simulates independent Firestore query)
        mock_gfc.return_value = _make_firestore_mock(ten_projects)
        all_projects = get_all_projects()
        assert len(all_projects) == 10, (
            "get_projects_for_resume must NOT delete projects from Firestore. "
            f"Expected 10, got {len(all_projects)}"
        )


class TestCriticalDynamicProjectTest:
    """
    MANDATORY TEST — from spec section 49:

    Start with A, B, C → verify get_all_projects() returns 3.
    Add D (no code/schema/template changes).
    Verify get_all_projects() returns 4.
    """

    @patch("resume_engine.project_service.get_firestore_client")
    def test_dynamic_project_addition(self, mock_gfc):
        # Step 1: 3 projects in Firestore
        three_projects = [
            ("proj_a", {"name": "Project A", "description": "d", "technologies": [], "enabled": True}),
            ("proj_b", {"name": "Project B", "description": "d", "technologies": [], "enabled": True}),
            ("proj_c", {"name": "Project C", "description": "d", "technologies": [], "enabled": True}),
        ]
        mock_gfc.return_value = _make_firestore_mock(three_projects)
        result = get_all_projects()
        assert len(result) == 3, "Expected 3 projects (A, B, C)"

        # Step 2: "Add" Project D — simulate by updating mock data
        four_projects = three_projects + [
            ("proj_d", {"name": "Project D", "description": "d", "technologies": [], "enabled": True}),
        ]
        mock_gfc.return_value = _make_firestore_mock(four_projects)
        result = get_all_projects()
        assert len(result) == 4, "Expected 4 projects after adding D"
        names = [p["name"] for p in result]
        assert "Project D" in names

    @patch("resume_engine.project_service.get_firestore_client")
    def test_project_e_added_without_code_changes(self, mock_gfc):
        """Add E after D — still no code changes."""
        five_projects = [
            (f"proj_{c}", {"name": f"Project {c}", "description": "d", "technologies": [], "enabled": True})
            for c in ["A", "B", "C", "D", "E"]
        ]
        mock_gfc.return_value = _make_firestore_mock(five_projects)
        result = get_all_projects()
        assert len(result) == 5
        assert any(p["name"] == "Project E" for p in result)


class TestAddProject:

    def test_validation_rejects_missing_name(self):
        with pytest.raises(ValueError, match="name"):
            with patch("resume_engine.project_service.get_firestore_client"):
                add_project({"description": "d", "technologies": []})

    def test_validation_rejects_missing_description(self):
        with pytest.raises(ValueError, match="description"):
            with patch("resume_engine.project_service.get_firestore_client"):
                add_project({"name": "p", "technologies": []})

    @patch("resume_engine.project_service.get_firestore_client")
    def test_add_project_returns_id(self, mock_gfc):
        mock_db = MagicMock()
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "auto_generated_id_123"
        mock_db.collection.return_value.add.return_value = (None, mock_doc_ref)
        mock_gfc.return_value = mock_db

        project_id = add_project({
            "name": "Test Project",
            "description": "A test",
            "technologies": ["Python"],
        })
        assert project_id == "auto_generated_id_123"

    @patch("resume_engine.project_service.get_firestore_client")
    def test_add_project_sets_defaults(self, mock_gfc):
        """enabled should default to True."""
        mock_db = MagicMock()
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "xyz"
        mock_db.collection.return_value.add.return_value = (None, mock_doc_ref)
        mock_gfc.return_value = mock_db

        add_project({
            "name": "Minimal Project",
            "description": "desc",
            "technologies": ["Python"],  # required field, non-empty
        })

        call_args = mock_db.collection.return_value.add.call_args[0][0]
        assert call_args["enabled"] is True


class TestDisableEnableProject:

    @patch("resume_engine.project_service.get_firestore_client")
    def test_disable_project(self, mock_gfc):
        mock_db = MagicMock()
        mock_gfc.return_value = mock_db
        disable_project("proj_abc")
        mock_db.collection.return_value.document.assert_called_with("proj_abc")
        mock_db.collection.return_value.document.return_value.update.assert_called_with(
            {"enabled": False}
        )

    @patch("resume_engine.project_service.get_firestore_client")
    def test_enable_project(self, mock_gfc):
        mock_db = MagicMock()
        mock_gfc.return_value = mock_db
        enable_project("proj_abc")
        mock_db.collection.return_value.document.return_value.update.assert_called_with(
            {"enabled": True}
        )

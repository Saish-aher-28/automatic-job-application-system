"""
test_profile.py — Tests for profile service (mocked Firestore).
"""

import pytest
from unittest.mock import MagicMock, patch

from resume_engine.profile_service import get_profile, upsert_profile


class TestGetProfile:

    @patch("resume_engine.profile_service.get_firestore_client")
    def test_returns_profile_data(self, mock_gfc):
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "name": "John Doe",
            "email": "john@example.com",
        }
        mock_db = MagicMock()
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        mock_gfc.return_value = mock_db

        profile = get_profile("main")
        assert profile["name"] == "John Doe"
        assert profile["email"] == "john@example.com"

    @patch("resume_engine.profile_service.get_firestore_client")
    def test_returns_empty_dict_if_not_found(self, mock_gfc):
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_db = MagicMock()
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        mock_gfc.return_value = mock_db

        profile = get_profile("nonexistent")
        assert profile == {}

    @patch("resume_engine.profile_service.get_firestore_client")
    def test_uses_config_profile_id_as_default(self, mock_gfc):
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"name": "Test"}
        mock_db = MagicMock()
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        mock_gfc.return_value = mock_db

        from resume_engine.config import config
        profile = get_profile()  # No explicit profile_id
        mock_db.collection.return_value.document.assert_called_with(config.FIRESTORE_PROFILE_ID)


class TestUpsertProfile:

    @patch("resume_engine.profile_service.get_firestore_client")
    def test_upsert_calls_set_with_merge(self, mock_gfc):
        mock_db = MagicMock()
        mock_gfc.return_value = mock_db

        data = {"name": "Jane", "email": "jane@example.com"}
        upsert_profile(data, profile_id="test_id")

        mock_db.collection.return_value.document.assert_called_with("test_id")
        mock_db.collection.return_value.document.return_value.set.assert_called_with(
            data, merge=True
        )

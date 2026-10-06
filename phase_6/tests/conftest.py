"""
conftest.py — Pytest configuration and global fixtures for Phase 6.
"""

from __future__ import annotations
import pytest
from unittest.mock import MagicMock

# Force testing configuration
import os
os.environ["GEMINI_API_KEY"] = "mock-api-key-123"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "mock-credentials-path.json"
os.environ["TELEGRAM_API_ID"] = "12345"
os.environ["TELEGRAM_API_HASH"] = "mock-telegram-hash"


@pytest.fixture(autouse=True)
def mock_firestore(monkeypatch):
    """
    Globally mocks firebase-admin client to ensure tests run 100% offline.
    """
    mock_db = MagicMock()
    mock_app = MagicMock()
    
    # Mock _get_client in phase_6.firestore.db
    monkeypatch.setattr("phase_6.firestore.db._firestore_client", mock_db)
    monkeypatch.setattr("firebase_admin.initialize_app", MagicMock(return_value=mock_app))
    monkeypatch.setattr("firebase_admin.get_app", MagicMock(return_value=mock_app))
    monkeypatch.setattr("firebase_admin._apps", {"phase6": mock_app})
    
    return mock_db

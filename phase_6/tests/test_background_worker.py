"""
test_background_worker.py — Tests for initial source seeding and CLI background worker integration.
"""

from unittest.mock import MagicMock, patch
import pytest

from phase_6.firestore.db import seed_initial_sources, get_source_from_firestore
from phase_6.ingestion.main import IngestionOrchestrator


def test_seed_initial_sources():
    """Verifies that seed_initial_sources creates default real source documents without duplicates."""
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_db.collection.return_value = mock_collection

    # Mock no existing sources found
    mock_collection.where.return_value.limit.return_value.stream.return_value = []
    mock_doc_ref = MagicMock()
    mock_doc_ref.id = "mock-source-id-123"
    mock_collection.document.return_value = mock_doc_ref

    with patch("phase_6.firestore.db._get_client", return_value=mock_db):
        seeded = seed_initial_sources("test_user_id")

        assert len(seeded) == 3
        assert mock_collection.document.call_count == 3


def test_orchestrator_source_id_cli():
    """Verifies IngestionOrchestrator handles a single source_id correctly."""
    mock_source = {
        "id": "source-123",
        "name": "Freshers Hunt",
        "type": "telegram",
        "identifier": "@freshershunt",
        "enabled": True,
        "state": "ENABLED"
    }

    with patch("phase_6.ingestion.main.db.get_source_from_firestore", return_value=mock_source), \
         patch("phase_6.sources.telegram.adapter.TelegramSource.fetch", return_value=[]):
        
        orchestrator = IngestionOrchestrator(dry_run=True)
        stats = orchestrator.run(source_id="source-123")

        assert "telegram" in stats
        assert "processing_time_sec" in stats

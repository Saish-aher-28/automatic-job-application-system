"""
test_firestore.py — Ingestion Firestore integration unit tests for Phase 6.
"""

from __future__ import annotations
import pytest
from unittest.mock import MagicMock, patch
from phase_6.firestore import db
from phase_6.models.opportunity import JobOpportunity


def test_incremental_marker_tracking():
    mock_db = db._get_client()
    
    # Mock DocumentSnapshot and DocRef
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {"last_processed_id": 1050}
    
    mock_ref = MagicMock()
    mock_ref.get.return_value = mock_doc
    
    mock_collection = MagicMock()
    mock_collection.document.return_value = mock_ref
    
    mock_db.collection.return_value = mock_collection
    
    # Check get_last_processed_id
    last_id = db.get_last_processed_id("telegram_@testchannel")
    assert last_id == 1050
    mock_db.collection.assert_called_with("ingestion_meta")
    mock_collection.document.assert_called_with("telegram_@testchannel")
    
    # Check save_last_processed_id
    db.save_last_processed_id("telegram_@testchannel", 1080)
    mock_ref.set.assert_called_once()
    set_args = mock_ref.set.call_args[0][0]
    assert set_args["last_processed_id"] == 1080


def test_save_opportunity_new_document():
    # Test saving a new unique opportunity inside a transaction context
    mock_db = db._get_client()
    
    # Transactional Mocking
    mock_transaction = MagicMock()
    
    # Mock no existing documents (empty stream)
    mock_stream = MagicMock()
    mock_stream.__iter__.return_value = []
    
    mock_collection = MagicMock()
    mock_collection.limit.return_value.stream.return_value = mock_stream
    
    mock_doc_ref = MagicMock()
    mock_doc_ref.id = "mock-new-doc-id"
    mock_collection.document.return_value = mock_doc_ref
    
    mock_db.collection.return_value = mock_collection
    
    # Build a clean mock job opportunity
    op = JobOpportunity(
        source="website",
        source_type="static_crawl",
        source_name="Mock Board",
        raw_text="Hiring Backend dev at Stripe.",
        company="Stripe",
        job_title="Backend Developer",
        content_hash="stripe-hash-123"
    )
    
    # Call the transactional block directly to test logic
    doc_id = db._save_in_transaction(mock_transaction, mock_collection, op)
    
    assert doc_id == "mock-new-doc-id"
    # Assert transaction set was called with the document ref and data
    mock_transaction.set.assert_called_once()
    set_ref = mock_transaction.set.call_args[0][0]
    set_data = mock_transaction.set.call_args[0][1]
    
    assert set_ref == mock_doc_ref
    assert set_data["company"] == "Stripe"
    assert set_data["job_title"] == "Backend Developer"
    assert len(set_data["sources"]) == 1

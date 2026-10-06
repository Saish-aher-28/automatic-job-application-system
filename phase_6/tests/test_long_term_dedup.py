"""
test_long_term_dedup.py — Unit test for long-term deduplication.
This test explicitly verifies that long-term deduplication does not rely on a
limit(100) sliding window, but uses O(1) targeted Firestore index queries.
"""

from __future__ import annotations
import pytest
from unittest.mock import MagicMock, patch

from phase_6.models.opportunity import JobOpportunity
from phase_6.deduplicator.deduplicator import JobDeduplicator
from phase_6.firestore import db


def test_long_term_dedup_queries():
    """
    Verifies that save_opportunity executes specific targeted queries for deduplication
    rather than loading all/last 100 documents.
    """
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_transaction = MagicMock()
    
    mock_db.collection.return_value = mock_collection
    
    # Setup mock stream return values for each level query
    # All queries return empty list (no match found)
    mock_stream = MagicMock()
    mock_stream.__iter__.return_value = []
    mock_collection.where.return_value.limit.return_value.stream.return_value = mock_stream
    
    # Doc ref when creating a new record
    mock_new_ref = MagicMock()
    mock_new_ref.id = "new-opportunity-123"
    mock_collection.document.return_value = mock_new_ref
    
    op = JobOpportunity(
        source="telegram",
        source_type="channel",
        source_name="Test Channel",
        source_channel="@pythonchannel",
        source_message_id=456,
        source_url="https://t.me/pythonchannel/456",
        company="Stripe",
        job_title="Senior Python Engineer",
        description="Write beautiful code in python.",
        raw_text="Hiring senior python dev at stripe.",
        canonical_url="https://t.me/pythonchannel/456",
        telegram_message_key="telegram:pythonchannel:456",
        job_identity_key="stripe:senior-python-engineer:remote",
        content_hash="stripe-python-hash"
    )
    
    # Patch _get_client to return our mock DB client
    with patch("phase_6.firestore.db._get_client", return_value=mock_db):
        doc_id = db._save_in_transaction(mock_transaction, mock_collection, op)
        
        assert doc_id == "new-opportunity-123"
        
        # Verify that targeted where queries were called
        # L1: canonical_url
        mock_collection.where.assert_any_call("canonical_url", "==", op.canonical_url)
        # L2: telegram_message_key
        mock_collection.where.assert_any_call("telegram_message_key", "==", op.telegram_message_key)
        # L3: content_hash
        mock_collection.where.assert_any_call("content_hash", "==", op.content_hash)
        # L4: job_identity_key
        mock_collection.where.assert_any_call("job_identity_key", "==", op.job_identity_key)
        
        # Verify transaction set was called to insert the new record
        mock_transaction.set.assert_called_once()


def test_long_term_dedup_match_found():
    """
    Verifies that if a targeted query returns a document, it is correctly identified
    as a duplicate, metadata is merged, and it is saved.
    """
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_transaction = MagicMock()
    
    mock_db.collection.return_value = mock_collection
    
    # Setup mock document that represents the duplicate
    mock_doc = MagicMock()
    mock_doc.id = "existing-duplicate-id"
    mock_doc.to_dict.return_value = {
        "id": "existing-duplicate-id",
        "company": "Stripe",
        "job_title": "Senior Python Engineer",
        "canonical_url": "https://t.me/pythonchannel/456",
        "telegram_message_key": "telegram:pythonchannel:456",
        "content_hash": "stripe-python-hash",
        "sources": [
            {"source": "telegram", "source_channel": "@pythonchannel", "source_message_id": 456}
        ]
    }
    
    # Mocking that query returns a match
    mock_stream = MagicMock()
    mock_stream.__iter__.return_value = [mock_doc]
    mock_collection.where.return_value.limit.return_value.stream.return_value = mock_stream
    
    # Mock doc ref for set
    mock_doc_ref = MagicMock()
    mock_collection.document.return_value = mock_doc_ref
    mock_doc_ref.get.return_value = mock_doc
    
    op = JobOpportunity(
        source="website",
        source_type="static_crawl",
        source_name="Stripe Careers",
        source_url="https://stripe.com/jobs/senior-python-dev",
        company="Stripe",
        job_title="Senior Python Engineer",
        description="Write beautiful code in python.",
        raw_text="Hiring senior python dev at stripe.",
        canonical_url="https://stripe.com/jobs/senior-python-dev",
        content_hash="stripe-python-hash"
    )
    
    with patch("phase_6.firestore.db._get_client", return_value=mock_db):
        doc_id = db._save_in_transaction(mock_transaction, mock_collection, op)
        
        # Verify the returned ID is the duplicate ID
        assert doc_id == "existing-duplicate-id"
        
        # Verify that merged metadata is updated on the existing doc
        mock_transaction.set.assert_called_once()
        set_args = mock_transaction.set.call_args[0]
        # First arg should be the doc_ref for the duplicate
        assert set_args[0] == mock_doc_ref
        # Second arg should contain merged sources
        assert len(set_args[1]["sources"]) == 2

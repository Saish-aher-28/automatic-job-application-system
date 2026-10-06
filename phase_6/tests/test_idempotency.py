"""
test_idempotency.py — Unit tests for Phase 6.2 idempotency and cross-source deduplication.
"""

from __future__ import annotations
import pytest
from unittest.mock import MagicMock, patch

from phase_6.sources.base import RawJobItem
from phase_6.models.opportunity import JobOpportunity
from phase_6.deduplicator.deduplicator import JobDeduplicator
from phase_6.ingestion.main import IngestionOrchestrator
from phase_6.firestore import db


def test_telegram_idempotency_skips_processed():
    """
    Verifies that if a Telegram message was already processed, the orchestrator
    skips Gemini extraction and increments the duplicate count.
    """
    orchestrator = IngestionOrchestrator(dry_run=True)
    mock_extractor = MagicMock()
    orchestrator.detector = MagicMock()
    
    item = RawJobItem(
        source="telegram",
        source_type="channel",
        source_name="Telegram channel: @reactjobs",
        source_channel="@reactjobs",
        source_message_id=123,
        source_url="https://t.me/reactjobs/123",
        raw_text="Hiring React dev."
    )
    
    # Mock db.is_telegram_message_processed to return True
    with patch("phase_6.firestore.db.is_telegram_message_processed", return_value=True) as mock_processed, \
         patch("phase_6.ingestion.main.GeminiExtractor", return_value=mock_extractor), \
         patch("phase_6.sources.telegram.adapter.TelegramSource.fetch", return_value=[item]):
         
        stats = orchestrator.run("telegram")
        
        # Verify processed check was called
        mock_processed.assert_called_once_with("telegram:reactjobs:123")
        
        # Verify detector and extractor were NEVER called
        mock_extractor.extract.assert_not_called()
        orchestrator.detector.detect.assert_not_called()
        
        # Verify stats reflect duplicates
        assert stats["telegram"]["duplicates"] == 1
        assert stats["telegram"]["scanned"] == 1
        assert stats["telegram"]["extracted"] == 0


def test_website_idempotency_skips_processed():
    """
    Verifies that if a website URL was already processed, it is skipped.
    """
    orchestrator = IngestionOrchestrator(dry_run=True)
    mock_extractor = MagicMock()
    orchestrator.detector = MagicMock()
    
    item = RawJobItem(
        source="website",
        source_type="static_crawl",
        source_name="Careers Site",
        source_url="https://example.com/jobs/456",
        raw_text="Hiring Backend engineer."
    )
    
    # Mock both is_canonical_url_processed and is_url_processed
    with patch("phase_6.firestore.db.is_canonical_url_processed", return_value=False), \
         patch("phase_6.firestore.db.is_url_processed", return_value=True) as mock_url_processed, \
         patch("phase_6.ingestion.main.GeminiExtractor", return_value=mock_extractor), \
         patch("phase_6.sources.websites.adapter.WebsiteSource.fetch", return_value=[item]):
         
        stats = orchestrator.run("websites")
        
        # Verify processed check was called on canonicalized URL
        canonical = JobDeduplicator.compute_canonical_url("https://example.com/jobs/456")
        mock_url_processed.assert_called_once_with(canonical)
        
        # Verify LLM extraction skipped
        mock_extractor.extract.assert_not_called()
        assert stats["website"]["duplicates"] == 1


def test_cross_source_deduplication():
    """
    Verifies that if a job is discovered via Telegram and then via Website,
    the merge_source_metadata preserves both references.
    """
    op1 = JobOpportunity(
        source="telegram",
        source_type="channel",
        source_name="React Jobs Channel",
        source_channel="@reactjobs",
        source_message_id=789,
        source_url="https://t.me/reactjobs/789",
        company="Vercel",
        job_title="Frontend Engineer",
        description="Build Next.js framework.",
        raw_text="Hiring frontend eng.",
        canonical_url="https://vercel.com/careers/frontend",
        content_hash="vercel-hash-123"
    )
    
    op2 = JobOpportunity(
        source="website",
        source_type="static_crawl",
        source_name="Vercel Careers",
        source_url="https://vercel.com/careers/frontend",
        company="Vercel",
        job_title="Frontend Engineer",
        description="Build Next.js framework.",
        raw_text="Careers site post.",
        canonical_url="https://vercel.com/careers/frontend",
        content_hash="vercel-hash-123"
    )
    
    doc_data = op1.model_dump()
    doc_data["sources"] = [{
        "source": op1.source,
        "source_type": op1.source_type,
        "source_name": op1.source_name,
        "source_channel": op1.source_channel,
        "source_message_id": op1.source_message_id,
        "source_url": op1.source_url,
        "discovered_at": op1.discovered_at
    }]
    
    merged = JobDeduplicator.merge_source_metadata(doc_data, op2)
    
    assert len(merged["sources"]) == 2
    assert merged["sources"][0]["source"] == "telegram"
    assert merged["sources"][1]["source"] == "website"
    assert merged["sources"][1]["source_url"] == "https://vercel.com/careers/frontend"

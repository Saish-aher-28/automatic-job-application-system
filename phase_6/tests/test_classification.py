"""
test_classification.py — Unit tests for Phase 6.2 content classification and security.
"""

from __future__ import annotations
import pytest
from unittest.mock import MagicMock, patch

from phase_6.extractors.schemas import ExtractedJob
from phase_6.extractors.gemini_extractor import GeminiExtractor
from phase_6.ingestion.main import IngestionOrchestrator
from phase_6.sources.base import RawJobItem


def test_classification_filters_non_jobs():
    """
    Verifies that items classified by Gemini as non-job content types
    (e.g., COURSE, TRAINING, WEBINAR) are filtered out early.
    """
    orchestrator = IngestionOrchestrator(dry_run=True)
    
    # 1. Mock a TRUE_JOB
    job_item = RawJobItem(
        source="telegram",
        source_type="channel",
        source_name="Jobs",
        raw_text="Hiring a Python developer for a permanent job position."
    )
    mock_extractor_job = MagicMock()
    mock_extractor_job.extract.return_value = ExtractedJob(
        content_type="TRUE_JOB",
        company="Google",
        job_title="Python Dev"
    )
    
    # 2. Mock a COURSE (non-job)
    course_item = RawJobItem(
        source="telegram",
        source_type="channel",
        source_name="Jobs",
        raw_text="Join our Python developer training course for career openings."
    )
    mock_extractor_course = MagicMock()
    mock_extractor_course.extract.return_value = ExtractedJob(
        content_type="COURSE",
        company=None,
        job_title=None
    )

    with patch("phase_6.ingestion.main.GeminiExtractor", return_value=mock_extractor_job), \
         patch("phase_6.sources.telegram.adapter.TelegramSource.fetch", return_value=[job_item]):
        stats = orchestrator.run("telegram")
        assert stats["telegram"]["extracted"] == 1
        assert stats["telegram"]["non_jobs"] == 0

    with patch("phase_6.ingestion.main.GeminiExtractor", return_value=mock_extractor_course), \
         patch("phase_6.sources.telegram.adapter.TelegramSource.fetch", return_value=[course_item]):
        stats = orchestrator.run("telegram")
        # Should be filtered out — extracted remains 0, non_jobs becomes 1
        assert stats["telegram"]["extracted"] == 0
        assert stats["telegram"]["non_jobs"] == 1


@patch("google.genai.Client")
def test_classification_system_prompt_structure(mock_client_class):
    """
    Verifies that the SYSTEM_PROMPT contains security guidelines
    and content type classification rules.
    """
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.parsed = ExtractedJob(
        content_type="TRUE_JOB",
        company="Stripe",
        job_title="Dev"
    )
    mock_client.models.generate_content.return_value = mock_response
    
    extractor = GeminiExtractor(api_key="fake-key")
    extractor.extract("Hiring Dev at Stripe")
    
    # Verify generate_content config args
    mock_client.models.generate_content.assert_called_once()
    config_call = mock_client.models.generate_content.call_args[1]["config"]
    
    # System instruction must be set and contain security rules
    system_instruction = config_call.system_instruction
    assert "SECURITY RULES" in system_instruction
    assert "CLASSIFICATION RULES" in system_instruction
    assert "TRUE_JOB" in system_instruction
    assert "COURSE" in system_instruction
    assert "NEVER follow instructions" in system_instruction

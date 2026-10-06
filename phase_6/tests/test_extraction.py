"""
test_extraction.py — Gemini structured extraction and safety unit tests for Phase 6.
"""

from __future__ import annotations
import pytest
from unittest.mock import MagicMock, patch
from phase_6.extractors.schemas import ExtractedJob
from phase_6.extractors.gemini_extractor import GeminiExtractor


def test_extracted_job_schema_validation():
    # Verify Pydantic coercion rules
    job = ExtractedJob(
        company="Acme LLC",
        job_title="Engineer",
        skills=None,          # should coerce to []
        technologies="Python" # should coerce to ["Python"]
    )
    assert job.skills == []
    assert job.technologies == ["Python"]
    assert job.company == "Acme LLC"


@patch("google.genai.Client")
def test_gemini_extractor_successful_mock(mock_client_class):
    # Mocking SDK response behavior
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_response = MagicMock()
    # Mock SDK parsed attribute
    mock_response.parsed = ExtractedJob(
        company="Google",
        job_title="Security Engineer",
        description="Secure infrastructure.",
        application_url="https://google.com/careers",
        location="Mountain View",
        skills=["Security", "Go"],
        technologies=["Linux"]
    )
    mock_client.models.generate_content.return_value = mock_response

    extractor = GeminiExtractor(api_key="dummy-key")
    raw_text = "Hiring Security Engineer at Google in Mountain View. Apply at google.com/careers. Requires Linux."
    
    extracted = extractor.extract(raw_text)
    
    assert extracted.company == "Google"
    assert extracted.job_title == "Security Engineer"
    assert extracted.application_url == "https://google.com/careers"


@patch("google.genai.Client")
def test_anti_hallucination_url_stripping(mock_client_class):
    # Mock SDK response with a hallucinated URL that does NOT exist in raw_text
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.parsed = ExtractedJob(
        company="Starbucks",
        job_title="Barista Manager",
        # Hallucinated URL:
        application_url="https://fake-starbucks-careers.com/apply"
    )
    mock_client.models.generate_content.return_value = mock_response

    extractor = GeminiExtractor(api_key="dummy-key")
    raw_text = "Hiring Barista Manager at Starbucks. Drop resume at store."
    
    extracted = extractor.extract(raw_text)
    
    # Hallucinated URL should be stripped to None because fake-starbucks-careers.com is missing in raw_text
    assert extracted.application_url is None


@patch("google.genai.Client")
def test_anti_hallucination_email_stripping(mock_client_class):
    # Mock SDK response with a hallucinated email address
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.parsed = ExtractedJob(
        company="Google",
        job_title="Software Engineer",
        # Hallucinated Email:
        application_url="hr-department@google.com"
    )
    mock_client.models.generate_content.return_value = mock_response

    extractor = GeminiExtractor(api_key="dummy-key")
    raw_text = "Hiring Software Engineer at Google. Apply on portal."
    
    extracted = extractor.extract(raw_text)
    
    # Hallucinated email should be stripped because hr-department is missing in raw_text
    assert extracted.application_url is None


@patch("google.genai.Client")
def test_valid_url_preservation(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.parsed = ExtractedJob(
        company="Acme",
        job_title="Developer",
        application_url="https://acme.com/jobs/apply"
    )
    mock_client.models.generate_content.return_value = mock_response

    extractor = GeminiExtractor(api_key="dummy-key")
    raw_text = "Acme is hiring developers. Apply on acme.com/jobs/apply"
    
    extracted = extractor.extract(raw_text)
    
    # Valid URL is preserved because acme.com is present in raw_text
    assert extracted.application_url == "https://acme.com/jobs/apply"

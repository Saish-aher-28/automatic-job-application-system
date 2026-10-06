"""
test_deduplication.py — Deduplication and source merging unit tests for Phase 6.
"""

from __future__ import annotations
from phase_6.models.opportunity import JobOpportunity
from phase_6.deduplicator.deduplicator import JobDeduplicator


def build_mock_opportunity(
    company="TestCorp",
    title="Software Engineer",
    description="Build python microservices.",
    url="https://example.com/job",
    channel=None,
    msg_id=None,
    location="Remote"
):
    content_hash = JobDeduplicator.compute_content_hash(company, title, description)
    return JobOpportunity(
        source="telegram" if channel else "website",
        source_type="channel" if channel else "static_crawl",
        source_name="TestSource",
        source_channel=channel,
        source_message_id=msg_id,
        source_url=url,
        company=company,
        job_title=title,
        description=description,
        raw_text=description,
        application_url=url,
        location=location,
        content_hash=content_hash
    )


def test_deduplication_same_url():
    # URL matches but descriptions differ slightly
    op1 = build_mock_opportunity(url="https://example.com/unique-url")
    op2 = build_mock_opportunity(description="Slightly different text but same post.", url="https://example.com/unique-url")
    
    dup = JobDeduplicator.find_duplicate(op2, [op1])
    assert dup is not None
    assert dup.application_url == op1.application_url


def test_deduplication_same_telegram_message():
    # Telegram channel + message ID match
    op1 = build_mock_opportunity(channel="@jobchannel", msg_id=999, url="https://t.me/jobchannel/999")
    op2 = build_mock_opportunity(description="Different text post from same message id.", channel="@jobchannel", msg_id=999, url="https://t.me/jobchannel/999")
    
    dup = JobDeduplicator.find_duplicate(op2, [op1])
    assert dup is not None
    assert dup.source_message_id == 999


def test_deduplication_content_hash():
    # Exact content matches, different URLs
    op1 = build_mock_opportunity(description="Deterministic job description text.")
    op2 = build_mock_opportunity(description="Deterministic job description text.", url="https://other.com/job-post")
    
    dup = JobDeduplicator.find_duplicate(op2, [op1])
    assert dup is not None
    assert dup.content_hash == op1.content_hash


def test_deduplication_company_title_location():
    # Same company + title + location, different description wording
    op1 = build_mock_opportunity(company="Google", title="SRE", location="Pune")
    op2 = build_mock_opportunity(company="Google", title="SRE", location="Pune", description="Different description text entirely.")
    
    dup = JobDeduplicator.find_duplicate(op2, [op1])
    assert dup is not None


def test_no_duplicate_for_different_roles():
    # Same company, different roles (ensure different URLs so Level 1 doesn't match)
    op1 = build_mock_opportunity(company="Acme", title="Frontend Developer", url="https://example.com/acme-frontend")
    op2 = build_mock_opportunity(company="Acme", title="Backend Developer", url="https://example.com/acme-backend")
    
    dup = JobDeduplicator.find_duplicate(op2, [op1])
    assert dup is None


def test_no_duplicate_for_different_locations():
    # Same company and title, different locations (ensure different description and URLs so Level 1 & 3 don't match)
    op1 = build_mock_opportunity(company="Google", title="Software Engineer", location="Bangalore", url="https://example.com/google-blr", description="Build search backend in Bangalore.")
    op2 = build_mock_opportunity(company="Google", title="Software Engineer", location="Remote", url="https://example.com/google-remote", description="Build search backend remotely.")
    
    dup = JobDeduplicator.find_duplicate(op2, [op1])
    assert dup is None


def test_merge_source_metadata():
    op1 = build_mock_opportunity(channel="@channelA", msg_id=1, url="https://t.me/channelA/1")
    op2 = build_mock_opportunity(channel="@channelB", msg_id=2, url="https://t.me/channelB/2")
    
    doc_data = op1.model_dump()
    
    # Initialize sources array with first source details
    first_ref = {
        "source": op1.source,
        "source_type": op1.source_type,
        "source_name": op1.source_name,
        "source_channel": op1.source_channel,
        "source_message_id": op1.source_message_id,
        "source_url": op1.source_url,
        "discovered_at": op1.discovered_at
    }
    doc_data["sources"] = [first_ref]
    
    # Merge second source details
    merged_data = JobDeduplicator.merge_source_metadata(doc_data, op2)
    
    assert len(merged_data["sources"]) == 2
    assert merged_data["sources"][0]["source_channel"] == "@channelA"
    assert merged_data["sources"][1]["source_channel"] == "@channelB"
    assert merged_data["sources"][1]["source_message_id"] == 2

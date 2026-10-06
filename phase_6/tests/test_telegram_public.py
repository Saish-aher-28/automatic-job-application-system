"""
test_telegram_public.py — Unit tests for Public Telegram Web Ingestion Adapter.
"""

from unittest.mock import MagicMock, patch
import pytest
import requests

from phase_6.sources.telegram_public.adapter import TelegramPublicSource


def test_channel_username_normalization():
    """Verify normalize_channel correctly extracts channel usernames from multiple input formats."""
    assert TelegramPublicSource.normalize_channel("@freshershunt") == "freshershunt"
    assert TelegramPublicSource.normalize_channel("freshershunt") == "freshershunt"
    assert TelegramPublicSource.normalize_channel("https://t.me/freshershunt") == "freshershunt"
    assert TelegramPublicSource.normalize_channel("https://t.me/s/freshershunt") == "freshershunt"
    assert TelegramPublicSource.normalize_channel("https://t.me/freshershunt?start=123") == "freshershunt"
    assert TelegramPublicSource.normalize_channel("https://t.me/s/fresheroffcampus/") == "fresheroffcampus"
    assert TelegramPublicSource.normalize_channel("  @FresherOffCampus  ") == "fresheroffcampus"
    assert TelegramPublicSource.normalize_channel("") == ""


@patch("requests.get")
def test_successful_public_feed_parsing(mock_get):
    """Verify successful HTML parsing of Telegram public messages."""
    html_content = """
    <div class="tgme_channel_info_header_title">Freshers Hunt Feed</div>
    <div class="tgme_widget_message" data-post="freshershunt/12345">
        <a class="tgme_widget_message_date" href="https://t.me/freshershunt/12345">
            <time datetime="2026-08-25T11:00:00+00:00">2026-08-25 11:00</time>
        </a>
        <div class="tgme_widget_message_text">Company X hiring Software Engineer. Apply: https://example.com/job1</div>
    </div>
    <div class="tgme_widget_message" data-post="freshershunt/12346">
        <a class="tgme_widget_message_date" href="https://t.me/freshershunt/12346">
            <time datetime="2026-08-25T11:05:00+00:00">2026-08-25 11:05</time>
        </a>
        <div class="tgme_widget_message_text">Learn AWS and get certified today!</div>
    </div>
    """
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.text = html_content
    mock_get.return_value = mock_res

    # Mock incremental marker database queries to return 0 (no processed marker yet)
    with patch("phase_6.sources.telegram_public.adapter.get_last_processed_id", return_value=0), \
         patch("phase_6.sources.telegram_public.adapter.save_last_processed_id") as mock_save:
         
        src = TelegramPublicSource(channels=["@freshershunt"])
        items = src.fetch()

        assert len(items) == 2
        
        # Verify first item fields
        assert items[0].source_message_id == 12345
        assert items[0].source_channel == "freshershunt"
        assert items[0].source_url == "https://t.me/freshershunt/12345"
        assert "Company X hiring" in items[0].raw_text
        assert items[0].posted_at == "2026-08-25T11:00:00+00:00"

        # Verify second item fields
        assert items[1].source_message_id == 12346
        assert items[1].source_channel == "freshershunt"
        assert items[1].source_url == "https://t.me/freshershunt/12346"
        assert "Learn AWS and get" in items[1].raw_text
        assert items[1].posted_at == "2026-08-25T11:05:00+00:00"

        # Verify database marker saved with max message ID
        mock_save.assert_called_with("telegram_freshershunt", 12346)


@patch("requests.get")
def test_incremental_marker_skips_processed(mock_get):
    """Verify incremental marker skipping works to prevent parsing previously processed posts."""
    html_content = """
    <div class="tgme_channel_info_header_title">Freshers Hunt Feed</div>
    <div class="tgme_widget_message" data-post="freshershunt/12345">
        <a class="tgme_widget_message_date" href="https://t.me/freshershunt/12345">
            <time datetime="2026-08-25T11:00:00+00:00">2026-08-25 11:00</time>
        </a>
        <div class="tgme_widget_message_text">Older processed post text</div>
    </div>
    <div class="tgme_widget_message" data-post="freshershunt/12346">
        <a class="tgme_widget_message_date" href="https://t.me/freshershunt/12346">
            <time datetime="2026-08-25T11:05:00+00:00">2026-08-25 11:05</time>
        </a>
        <div class="tgme_widget_message_text">Newer unprocessed post text</div>
    </div>
    """
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.text = html_content
    mock_get.return_value = mock_res

    # Mock database to return last_id = 12345 (skipping message 12345)
    with patch("phase_6.sources.telegram_public.adapter.get_last_processed_id", return_value=12345), \
         patch("phase_6.sources.telegram_public.adapter.save_last_processed_id") as mock_save:
         
        src = TelegramPublicSource(channels=["@freshershunt"])
        items = src.fetch()

        # Only message 12346 should be returned
        assert len(items) == 1
        assert items[0].source_message_id == 12346
        assert "Newer unprocessed" in items[0].raw_text

        # Verify DB updated
        mock_save.assert_called_with("telegram_freshershunt", 12346)


@patch("requests.get")
def test_rate_limiting_429_graceful_handling(mock_get):
    """Verify HTTP 429 returns an empty list gracefully without crashing."""
    mock_res = MagicMock()
    mock_res.status_code = 429
    mock_get.return_value = mock_res

    src = TelegramPublicSource(channels=["@freshershunt"])
    items = src.fetch()
    assert items == []


@patch("requests.get")
def test_empty_feed_graceful_handling(mock_get):
    """Verify empty feed returns an empty list gracefully."""
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.text = "<html><body>No messages here</body></html>"
    mock_get.return_value = mock_res

    src = TelegramPublicSource(channels=["@freshershunt"])
    items = src.fetch()
    assert items == []


@patch("requests.get")
def test_malformed_html_one_post_fails_other_succeeds(mock_get):
    """Verify that a malformed HTML post does not crash the entire ingestion run."""
    html_content = """
    <div class="tgme_widget_message">
        <!-- Malformed/empty post with no ID -->
    </div>
    <div class="tgme_widget_message" data-post="freshershunt/12347">
        <a class="tgme_widget_message_date" href="https://t.me/freshershunt/12347">
            <time datetime="2026-08-25T11:10:00+00:00">2026-08-25 11:10</time>
        </a>
        <div class="tgme_widget_message_text">Valid post text</div>
    </div>
    """
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.text = html_content
    mock_get.return_value = mock_res

    with patch("phase_6.sources.telegram_public.adapter.get_last_processed_id", return_value=0), \
         patch("phase_6.sources.telegram_public.adapter.save_last_processed_id"):
         
        src = TelegramPublicSource(channels=["@freshershunt"])
        items = src.fetch()

        # The malformed post is skipped, the valid one is fetched
        assert len(items) == 1
        assert items[0].source_message_id == 12347
        assert items[0].raw_text == "Valid post text"

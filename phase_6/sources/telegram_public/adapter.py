"""
adapter.py — Public Telegram Web Feed Ingestion Adapter using BeautifulSoup.
Supports reading public feeds without API keys or credentials.
"""

from __future__ import annotations
import logging
import re
from datetime import datetime
from typing import List, Optional
import urllib.parse

import requests
from bs4 import BeautifulSoup

from phase_6.config.config import config
from phase_6.sources.base import JobSource, RawJobItem
from phase_6.firestore.db import get_last_processed_id, save_last_processed_id

logger = logging.getLogger(__name__)


class TelegramPublicSource(JobSource):
    """
    Ingests messages from public Telegram channels via t.me/s/ web feeds.
    Does not require API credentials, phone numbers, or sessions.
    """

    def __init__(
        self,
        channels: Optional[List[str]] = None,
        max_posts: Optional[int] = None,
        timeout: Optional[int] = None
    ):
        self.channels = channels or config.TELEGRAM_SOURCES
        self.max_posts = max_posts or int(getattr(config, "TELEGRAM_PUBLIC_MAX_POSTS", 20))
        self.timeout = timeout or int(getattr(config, "TELEGRAM_PUBLIC_TIMEOUT_SECONDS", 20))

        # Enforce hard cap
        if self.max_posts > 50:
            self.max_posts = 50

    @staticmethod
    def normalize_channel(identifier: str) -> str:
        """
        Normalizes various user inputs to a clean channel username.
        Examples:
            @freshershunt -> freshershunt
            freshershunt -> freshershunt
            https://t.me/freshershunt -> freshershunt
            https://t.me/s/freshershunt -> freshershunt
        """
        val = identifier.strip()
        if not val:
            return ""

        # Handle URLs
        if val.startswith("http://") or val.startswith("https://"):
            try:
                parsed = urllib.parse.urlparse(val)
                # Should be t.me host
                if "t.me" in parsed.netloc:
                    path_parts = [p for p in parsed.path.split("/") if p.strip()]
                    if len(path_parts) > 1 and path_parts[0] == "s":
                        return path_parts[1].lower()
                    elif len(path_parts) > 0:
                        return path_parts[0].lower()
            except Exception as e:
                logger.warning(f"Failed parsing URL identifier '{identifier}': {e}")

        # Remove leading @
        if val.startswith("@"):
            val = val[1:]

        # Clean any trailing query parameters or slashes
        val = val.split("?")[0].split("/")[0]

        # Basic alphanumeric + underscore check for Telegram usernames
        val = re.sub(r"[^a-zA-Z0-9_]", "", val)

        return val.lower()

    def fetch(self) -> List[RawJobItem]:
        """
        Fetches bounded recent posts from t.me/s/ feeds.
        Supports incremental tracking using Firestore message markers.
        """
        if not self.channels:
            logger.warning("No Telegram channels configured to scan.")
            return []

        raw_items: List[RawJobItem] = []

        for original_channel in self.channels:
            channel = self.normalize_channel(original_channel)
            if not channel:
                logger.warning(f"Invalid channel identifier skipped: '{original_channel}'")
                continue

            feed_url = f"https://t.me/s/{channel}"
            logger.info(f"Fetching public Telegram feed: {feed_url}")

            try:
                # Bounded HTTP Request
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                res = requests.get(feed_url, headers=headers, timeout=self.timeout)

                if res.status_code == 404:
                    logger.error(f"Telegram channel feed not found (404): {feed_url}")
                    continue
                elif res.status_code == 429:
                    logger.warning(f"Rate limited by Telegram (429) for feed: {feed_url}. Backing off.")
                    continue
                elif res.status_code != 200:
                    logger.error(f"Failed to fetch public feed (HTTP {res.status_code}): {feed_url}")
                    continue

                soup = BeautifulSoup(res.text, "html.parser")
                
                # Channel title / metadata
                channel_name_el = soup.select_one(".tgme_channel_info_header_title")
                channel_name = channel_name_el.text.strip() if channel_name_el else channel

                # Messages container selector: div.tgme_widget_message
                message_divs = soup.select(".tgme_widget_message")
                if not message_divs:
                    logger.info(f"No posts found in feed html for channel '{channel}'.")
                    continue

                # Fetch last processed message ID marker
                last_id = get_last_processed_id(f"telegram_{channel}")
                min_id = last_id if last_id is not None else 0

                # Bounded posts evaluation (evaluating newest/last self.max_posts)
                # Usually t.me/s/ serves the last 20 messages.
                recent_divs = message_divs[-self.max_posts:]
                
                max_msg_id = min_id
                processed_items_in_run: List[RawJobItem] = []

                for div in recent_divs:
                    try:
                        # 1. Message ID and URL extraction
                        post_attr = div.get("data-post")  # Format: "channel/id"
                        msg_id = None
                        if post_attr and "/" in post_attr:
                            parts = post_attr.split("/")
                            if parts[-1].isdigit():
                                msg_id = int(parts[-1])
                        
                        # Fallback to link tags
                        if not msg_id:
                            link_el = div.select_one("a.tgme_widget_message_date")
                            if link_el and link_el.get("href"):
                                href_parts = link_el.get("href").strip("/").split("/")
                                if href_parts[-1].isdigit():
                                    msg_id = int(href_parts[-1])

                        if not msg_id:
                            # Skip if message ID could not be parsed safely
                            continue

                        # Update run tracker for max ID
                        if msg_id > max_msg_id:
                            max_msg_id = msg_id

                        # Skip if already processed incrementally
                        if msg_id <= min_id:
                            continue

                        # 2. Text Extraction
                        text_el = div.select_one(".tgme_widget_message_text")
                        if not text_el:
                            # Empty or media-only message
                            continue
                        
                        raw_text = text_el.get_text("\n").strip()
                        if not raw_text:
                            continue

                        # 3. Timestamp extraction
                        time_el = div.select_one(".tgme_widget_message_date time")
                        posted_at = None
                        if time_el and time_el.get("datetime"):
                            posted_at = time_el.get("datetime")
                        else:
                            # Fallback text time
                            posted_at = datetime.utcnow().isoformat()

                        post_url = f"https://t.me/{channel}/{msg_id}"

                        raw_item = RawJobItem(
                            source="telegram",
                            source_type="channel",
                            source_name=channel_name,
                            source_url=post_url,
                            source_channel=channel,
                            source_message_id=msg_id,
                            raw_text=raw_text,
                            posted_at=posted_at
                        )
                        processed_items_in_run.append(raw_item)

                    except Exception as post_err:
                        logger.warning(f"Error parsing individual post in channel {channel}: {post_err}")
                        continue

                # Add processed items to return list
                raw_items.extend(processed_items_in_run)

                # Save updated marker to Firestore only if we advanced
                if max_msg_id > min_id:
                    save_last_processed_id(f"telegram_{channel}", max_msg_id)
                    logger.info(f"Updated Telegram marker for {channel} to message ID: {max_msg_id}")

            except requests.Timeout:
                logger.error(f"Request timeout fetching public feed: {feed_url}")
            except Exception as e:
                logger.error(f"Error reading public feed {feed_url}: {e}")

        return raw_items

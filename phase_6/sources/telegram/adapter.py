"""
adapter.py — Telegram source ingestion adapter using Telethon.
"""

from __future__ import annotations
import logging
from typing import List, Optional

from phase_6.config.config import config
from phase_6.sources.base import JobSource, RawJobItem
from phase_6.firestore.db import get_last_processed_id, save_last_processed_id

logger = logging.getLogger(__name__)


class TelegramSource(JobSource):
    """
    Retrieves messages from configured Telegram channels/groups.
    Implements incremental fetching based on tracked message IDs.
    """

    def __init__(
        self,
        api_id: Optional[str] = None,
        api_hash: Optional[str] = None,
        session_name: Optional[str] = None,
        channels: Optional[List[str]] = None
    ):
        self.api_id = api_id or config.TELEGRAM_API_ID
        self.api_hash = api_hash or config.TELEGRAM_API_HASH
        self.session_name = session_name or config.TELEGRAM_SESSION
        self.channels = channels or config.TELEGRAM_SOURCES

    def fetch(self) -> List[RawJobItem]:
        """
        Connects to Telegram API and fetches new messages incrementally.
        """
        if not self.api_id or not self.api_hash:
            logger.warning("Telegram API ID or Hash not configured. Skipping Telegram fetch.")
            return []

        if not self.channels:
            logger.warning("No Telegram channels configured to scan. Skipping.")
            return []

        # Local import of telethon to keep it lazy
        from telethon.sync import TelegramClient

        # Setup client
        client = TelegramClient(self.session_name, int(self.api_id), self.api_hash)
        
        raw_items = []
        try:
            client.connect()
            if not client.is_user_authorized():
                logger.error("Telegram user is not authorized. Please run the login setup first.")
                return []

            for channel in self.channels:
                logger.info(f"Scanning Telegram source: {channel}")
                
                # Fetch last processed message ID marker
                last_id = get_last_processed_id(f"telegram_{channel}")
                min_id = last_id if last_id is not None else 0
                
                # Retrieve messages newer than last_id
                # limit to config.MAX_MESSAGES to prevent hitting rate limits
                messages = client.get_messages(
                    entity=channel,
                    limit=config.MAX_MESSAGES,
                    min_id=min_id
                )
                
                if not messages:
                    logger.info(f"No new messages found in {channel}.")
                    continue
                
                # Track maximum message ID to update the pagination index marker
                max_msg_id = min_id
                
                for msg in messages:
                    if msg.id > max_msg_id:
                        max_msg_id = msg.id
                        
                    # Skip empty/service messages
                    if not msg.text or not msg.text.strip():
                        continue
                        
                    raw_item = RawJobItem(
                        source="telegram",
                        source_type="channel",
                        source_name=f"Telegram channel: {channel}",
                        source_channel=channel,
                        source_message_id=msg.id,
                        source_url=f"https://t.me/{channel.lstrip('@')}/{msg.id}",
                        raw_text=msg.text,
                        posted_at=msg.date.isoformat() if msg.date else None
                    )
                    raw_items.append(raw_item)
                
                # Save the new marker to Firestore
                if max_msg_id > min_id:
                    save_last_processed_id(f"telegram_{channel}", max_msg_id)
                    logger.info(f"Updated Telegram marker for {channel} to message ID: {max_msg_id}")

        except Exception as e:
            logger.error(f"Error occurred during Telegram fetching: {e}")
            raise e
        finally:
            client.disconnect()

        return raw_items

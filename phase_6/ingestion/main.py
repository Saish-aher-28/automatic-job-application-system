"""
main.py — Main orchestrator CLI controller for Phase 6 Job Ingestion.
"""

from __future__ import annotations
import sys
import json
import argparse
import logging
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from phase_6.config.config import config
from phase_6.sources.base import RawJobItem
from phase_6.sources.telegram.adapter import TelegramSource
from phase_6.sources.telegram_public.adapter import TelegramPublicSource
from phase_6.sources.websites.adapter import WebsiteSource
from phase_6.ingestion.detector import JobDetector
from phase_6.extractors.gemini_extractor import GeminiExtractor
from phase_6.normalizer.normalizer import JobNormalizer
from phase_6.deduplicator.deduplicator import JobDeduplicator
from phase_6.models.opportunity import JobOpportunity
from phase_6.firestore import db
from phase_6.firestore.db import save_opportunity

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


class IngestionOrchestrator:
    """
    Manages the overall discovery, detection, extraction, and ingestion workflow.
    Supports running specific sources configured in the Firestore job_sources collection.
    """

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run or config.DRY_RUN
        self.detector = JobDetector()
        self.extractor = None  # Lazy init to prevent SDK issues when dry-running fake data

    def run(self, source_type: str = "all", source_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes the ingestion run for the selected source type or a specific source ID.
        """
        start_time = time.time()
        stats = {
            "telegram": {"scanned": 0, "detected": 0, "extracted": 0, "duplicates": 0, "non_jobs": 0, "stored": 0, "failed": 0},
            "website": {"scanned": 0, "detected": 0, "extracted": 0, "duplicates": 0, "non_jobs": 0, "stored": 0, "failed": 0},
            "processing_time_sec": 0.0
        }

        # 1. Load source config if source_id is specified
        source_config = None
        if source_id:
            logger.info(f"Loading job source configuration for ID: {source_id}")
            source_config = db.get_source_from_firestore(source_id)
            if not source_config:
                raise ValueError(f"Source configuration not found for ID: {source_id}")

            if not source_config.get("enabled", True):
                logger.info(f"Source '{source_config.get('name')}' is disabled. Skipping ingestion run.")
                stats["processing_time_sec"] = round(time.time() - start_time, 2)
                return stats

            # Override source_type based on loaded configuration
            source_type = source_config.get("type", "telegram")
            if source_type not in ["telegram", "website"]:
                raise ValueError(f"Unsupported source type: {source_type}")

            # Set source state to RUNNING in Firestore
            if not self.dry_run:
                db.update_source_state(source_id, {
                    "state": "RUNNING",
                    "last_run_at": datetime.now(timezone.utc).isoformat()
                })

        raw_items: List[RawJobItem] = []

        try:
            # 2. Fetch raw items from selected sources
            if source_config:
                # Specific source run
                name = source_config.get("name", "Configured Source")
                if source_type == "telegram":
                    identifier = source_config.get("identifier")
                    if not identifier:
                        raise ValueError("Telegram source missing identifier")
                    adapter_mode = source_config.get("adapter_mode", "public_web")
                    logger.info(f"Scanning single Telegram source: {name} ({identifier}) using mode: {adapter_mode}")
                    
                    if adapter_mode == "public_web":
                        tg = TelegramPublicSource(channels=[identifier])
                    else:
                        tg = TelegramSource(channels=[identifier])
                        
                    tg_items = tg.fetch()
                    raw_items.extend(tg_items)
                elif source_type == "website":
                    url = source_config.get("url")
                    if not url:
                        raise ValueError("Website source missing URL")
                    logger.info(f"Scanning single Website source: {name} ({url})")
                    ws = WebsiteSource(sources_config=[{
                         "name": name,
                         "base_url": url,
                         "listing_url": url,
                         "enabled": True
                    }])
                    ws_items = ws.fetch()
                    raw_items.extend(ws_items)
            else:
                # Global scan (fallback / legacy CLI behavior)
                if source_type in ["telegram", "all"]:
                    try:
                        # Fallback: if TELEGRAM_API_ID/HASH are missing, fall back to Public Telegram Web Adapter
                        if not config.TELEGRAM_API_ID or not config.TELEGRAM_API_HASH:
                            logger.info("No Telegram API credentials. Using public Telegram web adapter for global scan.")
                            tg = TelegramPublicSource()
                        else:
                            tg = TelegramSource()
                        tg_items = tg.fetch()
                        raw_items.extend(tg_items)
                    except Exception as e:
                        logger.error(f"Telegram source failed: {e}")

                if source_type in ["websites", "all"]:
                    try:
                        ws = WebsiteSource()
                        ws_items = ws.fetch()
                        raw_items.extend(ws_items)
                    except Exception as e:
                        logger.error(f"Website source failed: {e}")

        except Exception as e:
            logger.error(f"Failed fetching from source: {e}")
            if source_id and not self.dry_run:
                db.update_source_state(source_id, {
                    "state": "ERROR",
                    "last_error": str(e)
                })
            raise e

        if not raw_items:
            logger.info("No raw items fetched from any source.")
            if source_id and not self.dry_run:
                db.update_source_state(source_id, {
                    "state": "ENABLED",
                    "last_success_at": datetime.now(timezone.utc).isoformat(),
                    "last_error": ""
                })
            stats["processing_time_sec"] = round(time.time() - start_time, 2)
            return stats

        # Lazy load extractor if needed
        self.extractor = GeminiExtractor()

        # 3. Process each raw item
        for item in raw_items:
            source_key = "telegram" if item.source == "telegram" else "website"
            stats[source_key]["scanned"] += 1

            logger.info(f"Processing item from {item.source_name} (Msg ID: {item.source_message_id or 'N/A'}, URL: {item.source_url or 'N/A'})")

            # 3.1 Long-term Idempotency checks before calling LLM (Gemini)
            canonical_url = JobDeduplicator.compute_canonical_url(item.source_url)
            telegram_message_key = JobDeduplicator.compute_telegram_message_key(item.source_channel, item.source_message_id)

            if telegram_message_key and db.is_telegram_message_processed(telegram_message_key):
                logger.info(f"  -> Telegram message key already processed: {telegram_message_key}. Skipping Gemini extraction.")
                stats[source_key]["duplicates"] += 1
                continue

            if canonical_url:
                if db.is_canonical_url_processed(canonical_url):
                    logger.info(f"  -> Canonical URL already processed: {canonical_url}. Skipping Gemini extraction.")
                    stats[source_key]["duplicates"] += 1
                    continue
                if db.is_url_processed(canonical_url):
                    logger.info(f"  -> Website URL already in processed markers: {canonical_url}. Skipping Gemini extraction.")
                    stats[source_key]["duplicates"] += 1
                    continue

            # 3.2 Rule-based Job Detection
            detection = self.detector.detect(item.raw_text)
            if not detection["is_candidate"]:
                logger.info(f"  -> Rejected by preliminary detector (reasons: {detection['reasons']})")
                continue

            stats[source_key]["detected"] += 1
            logger.info(f"  -> Detected as job candidate (confidence: {detection['confidence']})")

            # 3.3 Structured Ingestion & Content Type Classification using Gemini
            try:
                extracted = self.extractor.extract(item.raw_text)
            except Exception as e:
                logger.error(f"  -> Structured extraction failed: {e}")
                stats[source_key]["failed"] += 1
                continue

            # Skip if classified as non-job content type (COURSE, WEBINAR, EVENT, etc.)
            content_type = (extracted.content_type or "TRUE_JOB").strip().upper()
            if content_type != "TRUE_JOB":
                logger.info(f"  -> Skipping: Classified as {content_type} (not a TRUE_JOB)")
                stats[source_key]["non_jobs"] += 1
                continue

            # Skip if critical fields (job_title/company) are both empty
            if not extracted.job_title and not extracted.company:
                logger.info("  -> JobTitle and Company both missing in extraction, skipping.")
                continue

            # 3.4 Normalization
            norm_company = JobNormalizer.normalize_company(extracted.company)
            norm_title = JobNormalizer.normalize_title(extracted.job_title)
            norm_location = JobNormalizer.normalize_location(extracted.location)
            norm_experience = JobNormalizer.normalize_experience(extracted.experience)
            norm_tech = JobNormalizer.normalize_technologies(extracted.technologies)
            norm_skills = JobNormalizer.normalize_skills(extracted.skills)

            # 3.5 Compute keys and hashes
            content_hash = JobDeduplicator.compute_content_hash(
                norm_company or "",
                norm_title or "",
                extracted.description or ""
            )

            job_identity_key = JobDeduplicator.compute_job_identity_key(
                norm_company,
                norm_title,
                norm_location
            )

            # Build canonical JobOpportunity model object
            op = JobOpportunity(
                source=item.source,
                source_type=item.source_type,
                source_name=item.source_name,
                source_channel=item.source_channel,
                source_message_id=item.source_message_id,
                source_url=item.source_url or item.source_name,
                company=norm_company,
                job_title=norm_title,
                description=extracted.description or item.raw_text[:1000],
                raw_text=item.raw_text,
                application_url=extracted.application_url or item.source_url,
                location=norm_location,
                employment_type=extracted.employment_type or "Full-time",
                experience=norm_experience,
                salary=extracted.salary,
                skills=norm_skills,
                technologies=norm_tech,
                posted_at=item.posted_at,
                content_hash=content_hash,
                canonical_url=canonical_url,
                telegram_message_key=telegram_message_key,
                job_identity_key=job_identity_key
            )

            stats[source_key]["extracted"] += 1

            # 3.6 Write / Deduplicate
            if self.dry_run:
                logger.info(f"  → [DRY-RUN] Opportunity parsed: {op.company} - {op.job_title} ({op.location})")
                stats[source_key]["stored"] += 1
            else:
                try:
                    # save_opportunity will automatically transaction-merge duplicates
                    doc_id = save_opportunity(op)
                    
                    # Mark website URL as processed in idempotency set
                    if canonical_url and source_key == "website":
                        db.mark_url_processed(canonical_url)

                    stats[source_key]["stored"] += 1
                except Exception as e:
                    logger.error(f"  → Firestore save failed: {e}")
                    stats[source_key]["failed"] += 1

        # 4. Update source state in Firestore on completion
        if source_id and not self.dry_run:
            db.update_source_state(source_id, {
                "state": "ENABLED",
                "last_success_at": datetime.now(timezone.utc).isoformat(),
                "last_error": ""
            })

        stats["processing_time_sec"] = round(time.time() - start_time, 2)
        return stats


def main():
    parser = argparse.ArgumentParser(description="Phase 6 Ingestion Controller CLI")
    parser.add_argument(
        "--source",
        choices=["telegram", "websites", "all"],
        default="all",
        help="Source to scan (default: all)"
    )
    parser.add_argument(
        "--source-id",
        type=str,
        default=None,
        help="ID of a specific source from job_sources collection to scan"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform dry run (do not write to Firestore)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print structured execution stats as JSON"
    )
    args = parser.parse_args()

    # Disable normal logs if --json is requested to keep stdout parseable
    if args.json:
        logging.getLogger().setLevel(logging.WARNING)

    orchestrator = IngestionOrchestrator(dry_run=args.dry_run)
    stats = orchestrator.run(args.source, args.source_id)

    if args.json:
        print(json.dumps(stats, indent=2))
    else:
        print("\n" + "="*50)
        print("PHASE 6 INGESTION RUN SUMMARY")
        print("="*50)
        print(f"Processing Time: {stats['processing_time_sec']} seconds\n")
        
        for key in ["telegram", "website"]:
            print(f"{key.capitalize()} Ingestion:")
            print(f"  Messages/Pages Scanned: {stats[key]['scanned']}")
            print(f"  Opportunities Detected: {stats[key]['detected']}")
            print(f"  Extracted Structured:   {stats[key]['extracted']}")
            print(f"  Non-Job Posts Filtered: {stats[key]['non_jobs']}")
            print(f"  Stored/Merged docs:     {stats[key]['stored']}")
            print(f"  Already Processed:      {stats[key]['duplicates']}")
            print(f"  Failed runs:            {stats[key]['failed']}")
            print()
        print("="*50)


if __name__ == "__main__":
    main()

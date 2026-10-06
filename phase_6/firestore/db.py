"""
db.py — Firestore repository for Phase 6.2.

Phase 6.2 Change: Long-term deterministic deduplication.

  Instead of loading limit(100) documents and scanning locally,
  each deduplication level uses a targeted Firestore query:

    where("field", "==", value).limit(1)

  This is O(1) regardless of how many opportunities exist in Firestore.
  All five levels execute inside a single Firestore transaction.

  New helpers:
    is_url_processed()    — website idempotency check
    mark_url_processed()  — mark a website URL as ingested
    get_source_from_firestore() — load a job_sources document for CLI ingestion
"""

from __future__ import annotations
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

import firebase_admin
from firebase_admin import credentials, firestore

from phase_6.config.config import config
from phase_6.models.opportunity import JobOpportunity
from phase_6.deduplicator.deduplicator import JobDeduplicator

logger = logging.getLogger(__name__)

_firestore_client = None
_APP_NAME = "phase6"


def _get_client():
    """Returns the singleton Firestore client for Phase 6."""
    global _firestore_client
    if _firestore_client is not None:
        return _firestore_client

    cred_path = config.GOOGLE_APPLICATION_CREDENTIALS
    if not cred_path:
        raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS not configured in environment.")

    cred_file = Path(cred_path)
    if not cred_file.exists():
        raise RuntimeError(f"Service account file not found: {cred_file}")

    if _APP_NAME not in firebase_admin._apps:
        cred = credentials.Certificate(str(cred_file))
        firebase_admin.initialize_app(cred, name=_APP_NAME)

    app = firebase_admin.get_app(_APP_NAME)
    _firestore_client = firestore.client(app=app)
    return _firestore_client


# ── Core Deduplication ────────────────────────────────────────────────────────

def save_opportunity(op: JobOpportunity) -> str:
    """
    Saves a JobOpportunity to Firestore with long-term concurrency-safe deduplication.

    Deduplication hierarchy (each level uses a targeted indexed query):
      L1 — canonical_url
      L2 — telegram_message_key
      L3 — content_hash
      L4 — job_identity_key  (only when company + title are non-empty)

    If a duplicate is found at any level: merges source metadata into the
    existing document and returns the existing document ID.

    If no duplicate: creates a new document.

    Returns:
        The canonical document ID (existing or newly created).
    """
    db = _get_client()
    collection_ref = db.collection("job_opportunities")
    transaction = db.transaction()
    return _save_in_transaction(transaction, collection_ref, op)


@firestore.transactional
def _save_in_transaction(transaction, collection_ref, op: JobOpportunity) -> str:
    """
    Transactional deduplication and save.

    Each deduplication level uses where("field","==",value).limit(1) —
    a targeted index lookup, not a document scan.
    """

    def _find_by_field(field: str, value: str) -> Optional[Any]:
        """Helper: query a single document by a specific field value."""
        if not value:
            return None
        docs = list(
            collection_ref.where(field, "==", value).limit(1).stream(transaction=transaction)
        )
        return docs[0] if docs else None

    # L1 — Canonical application URL
    existing_doc = None
    if op.canonical_url:
        existing_doc = _find_by_field("canonical_url", op.canonical_url)

    # L2 — Telegram message key
    if existing_doc is None and op.telegram_message_key:
        existing_doc = _find_by_field("telegram_message_key", op.telegram_message_key)

    # L3 — Content hash (SHA-256)
    if existing_doc is None and op.content_hash:
        existing_doc = _find_by_field("content_hash", op.content_hash)

    # L4 — Company + title + location identity key
    if existing_doc is None and op.job_identity_key:
        existing_doc = _find_by_field("job_identity_key", op.job_identity_key)

    if existing_doc is not None:
        # ── Duplicate found: merge source metadata ─────────────────────────
        logger.info(
            "Duplicate job opportunity detected (ID: %s). Merging source metadata.",
            existing_doc.id
        )
        doc_ref = collection_ref.document(existing_doc.id)
        existing_data = existing_doc.to_dict()

        merged_data = JobDeduplicator.merge_source_metadata(existing_data, op)
        merged_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        transaction.set(doc_ref, merged_data, merge=True)
        return existing_doc.id

    else:
        # ── New job opportunity ────────────────────────────────────────────
        doc_ref = collection_ref.document()
        op.id = doc_ref.id
        op.ingestion_status = "STORED"

        first_source = {
            "source": op.source,
            "source_type": op.source_type,
            "source_name": op.source_name,
            "source_channel": op.source_channel,
            "source_message_id": op.source_message_id,
            "source_url": op.source_url,
            "discovered_at": op.discovered_at
        }

        doc_data = op.model_dump()
        doc_data["sources"] = [first_source]

        transaction.set(doc_ref, doc_data)
        logger.info("Created new job opportunity document: %s", doc_ref.id)
        return doc_ref.id


# ── Website Idempotency ───────────────────────────────────────────────────────

def _url_processed_doc_id(url: str) -> str:
    """Returns a stable Firestore document ID for a website URL."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:40]


def is_url_processed(canonical_url: str) -> bool:
    """
    Returns True if this canonical URL has already been successfully ingested.
    Uses ingestion_meta/website_processed/{doc_id}.
    """
    if not canonical_url:
        return False
    db = _get_client()
    doc_id = _url_processed_doc_id(canonical_url)
    doc = db.collection("ingestion_meta").document("website_processed").collection("urls").document(doc_id).get()
    return doc.exists


def is_telegram_message_processed(key: str) -> bool:
    """
    Checks if a Telegram message key has already been processed and saved in job_opportunities.
    """
    if not key:
        return False
    db = _get_client()
    docs = list(db.collection("job_opportunities").where("telegram_message_key", "==", key).limit(1).stream())
    return len(docs) > 0


def is_canonical_url_processed(canonical_url: str) -> bool:
    """
    Checks if a canonical URL has already been processed and saved in job_opportunities.
    """
    if not canonical_url:
        return False
    db = _get_client()
    docs = list(db.collection("job_opportunities").where("canonical_url", "==", canonical_url).limit(1).stream())
    return len(docs) > 0


def mark_url_processed(canonical_url: str) -> None:
    """Records that a website URL has been successfully ingested."""
    if not canonical_url:
        return
    db = _get_client()
    doc_id = _url_processed_doc_id(canonical_url)
    db.collection("ingestion_meta").document("website_processed").collection("urls").document(doc_id).set({
        "url": canonical_url,
        "processed_at": datetime.now(timezone.utc).isoformat()
    }, merge=True)


# ── Incremental Telegram Marker ───────────────────────────────────────────────

def get_last_processed_id(source_name: str) -> Optional[int]:
    """Retrieves the last processed message ID marker for a Telegram source."""
    db = _get_client()
    doc = db.collection("ingestion_meta").document(source_name).get()
    if doc.exists:
        return doc.to_dict().get("last_processed_id")
    return None


def save_last_processed_id(source_name: str, message_id: int) -> None:
    """Saves the last processed message ID marker for a Telegram source."""
    db = _get_client()
    db.collection("ingestion_meta").document(source_name).set({
        "last_processed_id": message_id,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }, merge=True)


# ── Read Access ───────────────────────────────────────────────────────────────

def get_recent_opportunities(limit: int = 50) -> List[JobOpportunity]:
    """Retrieves recent job opportunities from Firestore."""
    db = _get_client()
    docs = (
        db.collection("job_opportunities")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    results = []
    for doc in docs:
        try:
            op = JobOpportunity.model_validate(doc.to_dict())
            op.id = doc.id
            results.append(op)
        except Exception:
            continue
    return results


# ── Job Sources (Firestore-backed source configuration) ───────────────────────

def get_source_from_firestore(source_id: str) -> Optional[Dict[str, Any]]:
    """
    Loads a job_sources document from Firestore (used by CLI --source-id).
    Returns the raw dict or None if not found.
    """
    db = _get_client()
    doc = db.collection("job_sources").document(source_id).get()
    if doc.exists:
        data = doc.to_dict()
        data["id"] = doc.id
        return data
    return None


def update_source_state(source_id: str, updates: Dict[str, Any]) -> None:
    """
    Updates runtime state fields on a job_sources document.
    Used to record last_run_at, last_success_at, last_error, state.
    """
    db = _get_client()
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    db.collection("job_sources").document(source_id).set(updates, merge=True)


def seed_initial_sources(user_id: str = "system") -> List[str]:
    """
    Seeds the 3 initial real sources (Freshers Hunt, FresherOffCampus, CommonJobs)
    into job_sources collection if they do not already exist for the user/system.
    Returns list of seeded source document IDs.
    """
    db = _get_client()
    sources_ref = db.collection("job_sources")

    initial_defs = [
        {
            "name": "Freshers Hunt",
            "type": "telegram",
            "identifier": "@freshershunt",
            "url": "https://t.me/freshershunt",
            "enabled": True,
            "state": "ENABLED",
        },
        {
            "name": "FresherOffCampus",
            "type": "telegram",
            "identifier": "@fresheroffcampus",
            "url": "https://t.me/fresheroffcampus",
            "enabled": True,
            "state": "ENABLED",
        },
        {
            "name": "CommonJobs",
            "type": "website",
            "identifier": "commonjobs.in",
            "url": "https://commonjobs.in/",
            "enabled": True,
            "state": "ENABLED",
        },
    ]

    seeded_ids = []
    now = datetime.now(timezone.utc).isoformat()

    for item in initial_defs:
        # Check by identifier or url
        existing = list(
            sources_ref.where("identifier", "==", item["identifier"]).limit(1).stream()
        )
        if not existing:
            doc_data = {
                "name": item["name"],
                "type": item["type"],
                "identifier": item["identifier"],
                "url": item["url"],
                "enabled": item["enabled"],
                "state": item["state"],
                "user_id": user_id,
                "last_run_at": None,
                "last_success_at": None,
                "last_error": "",
                "configuration": {},
                "created_at": now,
                "updated_at": now,
            }
            if item["type"] == "telegram":
                doc_data["adapter_mode"] = "public_web"
            doc_ref = sources_ref.document()
            doc_ref.set(doc_data)
            seeded_ids.append(doc_ref.id)
            logger.info("Seeded initial source: %s (ID: %s)", item["name"], doc_ref.id)
        else:
            # Overwrite/ensure adapter_mode for existing Telegram sources to ensure update
            doc_ref = existing[0].reference
            if item["type"] == "telegram":
                doc_ref.set({"adapter_mode": "public_web"}, merge=True)
            seeded_ids.append(existing[0].id)

    return seeded_ids


# ── Maintenance ───────────────────────────────────────────────────────────────

def delete_opportunity(doc_id: str) -> None:
    """Deletes a job opportunity by ID (useful for tests/cleanup)."""
    db = _get_client()
    db.collection("job_opportunities").document(doc_id).delete()


def reset_client():
    """Resets the singleton — used in tests."""
    global _firestore_client
    _firestore_client = None

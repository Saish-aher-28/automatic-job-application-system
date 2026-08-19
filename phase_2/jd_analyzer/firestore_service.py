"""
firestore_service.py — Phase 2 Firestore operations.

Reads from and writes to the 'job_descriptions' collection.
Uses the same Firebase credentials as Phase 1 but is fully isolated.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore

from phase_2.jd_analyzer.config import config
from phase_2.jd_analyzer.schemas import JDAnalysis

logger = logging.getLogger(__name__)

# Module-level singleton — separate from Phase 1's singleton
_firestore_client = None
_APP_NAME = "phase2"   # distinct Firebase app name to avoid collision with Phase 1


def _get_firestore_client():
    """Return (or create) the Phase 2 Firestore client."""
    global _firestore_client

    if _firestore_client is not None:
        return _firestore_client

    cred_path = config.GOOGLE_APPLICATION_CREDENTIALS
    if not cred_path:
        raise RuntimeError(
            "GOOGLE_APPLICATION_CREDENTIALS is not set.\n"
            "Add it to your .env file."
        )

    cred_file = Path(cred_path)
    if not cred_file.exists():
        raise RuntimeError(
            f"Firebase credentials not found: {cred_file}\n"
            f"Check GOOGLE_APPLICATION_CREDENTIALS in .env"
        )

    # Use a named app so Phase 1 and Phase 2 can coexist in the same process
    if _APP_NAME not in firebase_admin._apps:
        cred = credentials.Certificate(str(cred_file))
        firebase_admin.initialize_app(cred, name=_APP_NAME)

    app = firebase_admin.get_app(_APP_NAME)
    _firestore_client = firestore.client(app=app)
    return _firestore_client


def save_jd_analysis(
    raw_text: str,
    analysis: JDAnalysis,
    model: str,
) -> str:
    """
    Save a JD and its structured analysis to Firestore.

    Returns:
        The auto-generated Firestore document ID.
    """
    db = _get_firestore_client()
    collection = db.collection(config.FIRESTORE_JD_COLLECTION)

    # Use server timestamp for accuracy; also store a fallback ISO string
    now_iso = datetime.now(timezone.utc).isoformat()

    doc_data = {
        "raw_text":         raw_text,
        "analysis":         analysis.model_dump(),
        "model":            model,
        "created_at":       now_iso,
        "analysis_version": config.ANALYSIS_VERSION,
    }

    # add() generates a unique document ID automatically
    _, doc_ref = collection.add(doc_data)
    logger.info("Firestore document created: %s/%s", config.FIRESTORE_JD_COLLECTION, doc_ref.id)
    return doc_ref.id


def get_jd_analysis(doc_id: str) -> dict:
    """
    Retrieve a stored JD analysis document by ID.

    Returns:
        The raw Firestore document data as a dict.

    Raises:
        ValueError: if the document does not exist.
    """
    db = _get_firestore_client()
    doc = db.collection(config.FIRESTORE_JD_COLLECTION).document(doc_id).get()

    if not doc.exists:
        raise ValueError(
            f"No JD analysis found with ID '{doc_id}' "
            f"in collection '{config.FIRESTORE_JD_COLLECTION}'."
        )

    return doc.to_dict()


def reset_client():
    """Reset the Firestore singleton — used in tests."""
    global _firestore_client
    _firestore_client = None

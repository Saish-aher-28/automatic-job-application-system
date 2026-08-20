"""
firestore_service.py — Isolated Firestore operations for Phase 3 matching engine.

Reads profile data, skills, and projects from Firestore.
Reads structured JD analyses from job_descriptions.
Saves matching results to job_matches.
Coexists safely with Phase 1 by using a named Firebase App instance.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import firebase_admin
from firebase_admin import credentials, firestore

from phase_3.matcher.config import config
from phase_3.matcher.schemas import JobMatchResult

logger = logging.getLogger(__name__)

_firestore_client = None
_APP_NAME = "phase3"  # distinct Firebase app name to avoid default app collisions


def _get_firestore_client():
    """Return (or create) the Phase 3 Firestore client."""
    global _firestore_client

    if _firestore_client is not None:
        return _firestore_client

    cred_path = config.GOOGLE_APPLICATION_CREDENTIALS
    if not cred_path:
        raise RuntimeError(
            "GOOGLE_APPLICATION_CREDENTIALS environment variable is not set.\n"
            "Please check your .env configuration."
        )

    cred_file = Path(cred_path)
    if not cred_file.exists():
        raise RuntimeError(
            f"Firebase service account JSON file not found at: {cred_file}\n"
            f"Verify GOOGLE_APPLICATION_CREDENTIALS in your .env."
        )

    if _APP_NAME not in firebase_admin._apps:
        cred = credentials.Certificate(str(cred_file))
        firebase_admin.initialize_app(cred, name=_APP_NAME)

    app = firebase_admin.get_app(_APP_NAME)
    _firestore_client = firestore.client(app=app)
    return _firestore_client


def get_jd_analysis(jd_doc_id: str) -> dict:
    """
    Retrieve structured JD analysis from the 'job_descriptions' collection.
    """
    db = _get_firestore_client()
    doc_ref = db.collection(config.FIRESTORE_JD_COLLECTION).document(jd_doc_id)
    doc = doc_ref.get()

    if not doc.exists:
        raise ValueError(
            f"No Job Description document found with ID '{jd_doc_id}' "
            f"in collection '{config.FIRESTORE_JD_COLLECTION}'."
        )
    return doc.to_dict()


def get_user_skills() -> list[str]:
    """
    Fetch all active user skills from the 'skills' collection.
    """
    db = _get_firestore_client()
    docs = db.collection("skills").stream()

    skills = []
    for doc in docs:
        data = doc.to_dict()
        if data.get("enabled", True):
            name = data.get("name")
            if name:
                skills.append(name.strip())
    return skills


def get_user_projects() -> list[dict]:
    """
    Fetch all active user projects from the 'projects' collection.
    """
    db = _get_firestore_client()
    docs = db.collection("projects").stream()

    projects = []
    for doc in docs:
        data = doc.to_dict()
        if data.get("enabled", True):
            data["_id"] = doc.id
            projects.append(data)
    return projects


def get_user_experience() -> list[dict]:
    """
    Fetch all active experience records from the 'experience' collection.
    """
    db = _get_firestore_client()
    docs = db.collection("experience").stream()

    records = []
    for doc in docs:
        data = doc.to_dict()
        if data.get("enabled", True):
            data["_id"] = doc.id
            records.append(data)
    return records


def get_user_profile() -> dict:
    """
    Fetch the main profile record.
    """
    db = _get_firestore_client()
    # Read the first document in profiles (usually 'main')
    docs = db.collection("profiles").limit(1).get()
    if not docs:
        return {}
    return docs[0].to_dict()


def save_match_result(match_result: JobMatchResult) -> str:
    """
    Save the final JobMatchResult to the 'job_matches' collection.
    Automatically generates a unique document ID.
    """
    db = _get_firestore_client()
    collection = db.collection(config.FIRESTORE_MATCH_COLLECTION)

    now_iso = datetime.now(timezone.utc).isoformat()
    result_dict = match_result.model_dump()

    doc_data = {
        "jd_document_id":   result_dict["jd_document_id"],
        "job_title":        result_dict["job_title"],
        "created_at":       now_iso,
        "matcher_version":  config.MATCHER_VERSION,
        "scores": {
            "overall":          result_dict["overall_match_score"],
            "required_skills":  result_dict["required_skill_match_score"],
            "preferred_skills": result_dict["preferred_skill_match_score"],
            "technologies":     result_dict["technology_match_score"],
            "projects":         result_dict["project_relevance_score"],
        },
        "skill_match": {
            "matched_required":    result_dict["matched_required_skills"],
            "missing_required":    result_dict["missing_required_skills"],
            "matched_preferred":   result_dict["matched_preferred_skills"],
            "missing_preferred":   result_dict["missing_preferred_skills"],
            "matched_technologies": result_dict["matched_technologies"],
            "missing_technologies": result_dict["missing_technologies"],
        },
        "ranked_projects": result_dict["ranked_projects"],
    }

    _, doc_ref = collection.add(doc_data)
    logger.info("Saved match result to: %s/%s", config.FIRESTORE_MATCH_COLLECTION, doc_ref.id)
    return doc_ref.id


def get_match_result(match_doc_id: str) -> dict:
    """
    Retrieve saved match result from Firestore.
    """
    db = _get_firestore_client()
    doc = db.collection(config.FIRESTORE_MATCH_COLLECTION).document(match_doc_id).get()
    if not doc.exists:
        raise ValueError(
            f"No match result found with ID '{match_doc_id}' "
            f"in collection '{config.FIRESTORE_MATCH_COLLECTION}'."
        )
    return doc.to_dict()


def reset_client():
    """Reset Firestore singleton (primarily for tests)."""
    global _firestore_client
    _firestore_client = None

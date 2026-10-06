"""
firestore_service.py — Isolated Firestore operations for Phase 4 Resume Tailor.

Uses a named Firebase app ("phase4") to avoid collisions with Phase 1/Phase 3 apps.
Reads:  job_matches, job_descriptions, profiles, skills, projects,
        education, experience, certifications, languages, interests
Writes: tailored_resumes

The master profile is NEVER modified.
The job_matches collection is NEVER modified (Phase 3 results are read-only).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import firebase_admin
from firebase_admin import credentials, firestore

from phase_4.resume_tailor.config import config

logger = logging.getLogger(__name__)

_firestore_client = None
_APP_NAME = "phase4"  # distinct app name to avoid collision with Phase 1 default app


def _get_firestore_client():
    """Return (or create) the Phase 4 Firestore client."""
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


# ── Read operations ──────────────────────────────────────────────────────────

def get_match_result(match_id: str) -> dict:
    """
    Retrieve a Phase 3 match result from 'job_matches/<match_id>'.

    Returns the raw Firestore document dict.
    Raises ValueError if not found.
    """
    db = _get_firestore_client()
    doc = db.collection(config.FIRESTORE_MATCH_COLLECTION).document(match_id).get()
    if not doc.exists:
        raise ValueError(
            f"No job match found with ID '{match_id}' "
            f"in collection '{config.FIRESTORE_MATCH_COLLECTION}'."
        )
    return doc.to_dict()


def get_jd_analysis(jd_doc_id: str) -> dict:
    """
    Retrieve structured JD analysis from 'job_descriptions/<jd_doc_id>'.

    Returns the raw Firestore document dict.
    Raises ValueError if not found.
    """
    db = _get_firestore_client()
    doc = db.collection(config.FIRESTORE_JD_COLLECTION).document(jd_doc_id).get()
    if not doc.exists:
        raise ValueError(
            f"No JD document found with ID '{jd_doc_id}' "
            f"in collection '{config.FIRESTORE_JD_COLLECTION}'."
        )
    return doc.to_dict()


def get_profile() -> dict:
    """
    Fetch the main profile record from the 'profiles' collection.

    Returns the profile dict, or {} if not found.
    """
    db = _get_firestore_client()
    docs = db.collection("profiles").limit(1).get()
    if not docs:
        return {}
    return docs[0].to_dict()


def get_all_skills_grouped() -> dict[str, list[str]]:
    """
    Fetch all enabled skills and return them grouped by category.

    Returns: { "Programming Languages": ["Python", "C++", ...], ... }
    Skills are sorted by sort_order then name within each category.
    """
    db = _get_firestore_client()
    docs = db.collection("skills").stream()

    skills = []
    for doc in docs:
        data = doc.to_dict()
        data.setdefault("enabled", True)
        data.setdefault("sort_order", 999)
        if data.get("enabled", True):
            skills.append(data)

    skills.sort(
        key=lambda s: (s.get("category", ""), s.get("sort_order", 999), s.get("name", ""))
    )

    grouped: dict[str, list[str]] = {}
    for skill in skills:
        cat = skill.get("category", "Other")
        grouped.setdefault(cat, [])
        name = skill.get("name", "")
        if name:
            grouped[cat].append(name)
    return grouped


def get_all_projects() -> list[dict]:
    """
    Fetch all enabled projects from the 'projects' collection.

    Each project dict includes a '_id' field with the Firestore document ID.
    """
    db = _get_firestore_client()
    docs = db.collection("projects").stream()

    projects = []
    for doc in docs:
        data = doc.to_dict()
        data["_id"] = doc.id
        data.setdefault("enabled", True)
        if data.get("enabled", True):
            projects.append(data)
    return projects


def get_project_by_id(project_id: str) -> Optional[dict]:
    """
    Fetch a single project by its Firestore document ID.
    Returns None if not found.
    """
    db = _get_firestore_client()
    doc = db.collection("projects").document(project_id).get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    data["_id"] = doc.id
    return data


def get_education() -> list[dict]:
    """Fetch all education records."""
    db = _get_firestore_client()
    docs = db.collection("education").stream()
    records = []
    for doc in docs:
        data = doc.to_dict()
        data["_id"] = doc.id
        records.append(data)
    records.sort(key=lambda r: r.get("sort_order", 999))
    return records


def get_experience() -> list[dict]:
    """Fetch all experience records (enabled only)."""
    db = _get_firestore_client()
    docs = db.collection("experience").stream()
    records = []
    for doc in docs:
        data = doc.to_dict()
        data["_id"] = doc.id
        if data.get("enabled", True):
            records.append(data)
    return records


def get_certifications() -> list[dict]:
    """Fetch all certifications."""
    db = _get_firestore_client()
    docs = db.collection("certifications").stream()
    records = []
    for doc in docs:
        data = doc.to_dict()
        data["_id"] = doc.id
        records.append(data)
    records.sort(key=lambda r: r.get("sort_order", 999))
    return records


def get_languages() -> list[dict]:
    """Fetch all languages."""
    db = _get_firestore_client()
    docs = db.collection("languages").stream()
    records = []
    for doc in docs:
        data = doc.to_dict()
        data["_id"] = doc.id
        records.append(data)
    records.sort(key=lambda r: r.get("sort_order", 999))
    return records


def get_interests() -> list[dict]:
    """Fetch all interests."""
    db = _get_firestore_client()
    docs = db.collection("interests").stream()
    records = []
    for doc in docs:
        data = doc.to_dict()
        data["_id"] = doc.id
        records.append(data)
    records.sort(key=lambda r: r.get("sort_order", 999))
    return records


# ── Write operations ─────────────────────────────────────────────────────────

def save_tailored_resume(data: dict) -> str:
    """
    Save a tailored resume metadata record to 'tailored_resumes' collection.
    Returns the auto-generated Firestore document ID.

    The master profile and job_matches are NEVER written to.
    """
    db = _get_firestore_client()
    collection = db.collection(config.FIRESTORE_TAILORED_COLLECTION)

    data.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    data.setdefault("generator_version", config.GENERATOR_VERSION)

    _, doc_ref = collection.add(data)
    logger.info(
        "Saved tailored resume to: %s/%s",
        config.FIRESTORE_TAILORED_COLLECTION,
        doc_ref.id,
    )
    return doc_ref.id


# ── Test utilities ────────────────────────────────────────────────────────────

def reset_client() -> None:
    """Reset Firestore singleton (for tests)."""
    global _firestore_client
    _firestore_client = None

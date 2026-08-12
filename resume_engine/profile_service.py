"""
profile_service.py — Firestore CRUD for the 'profiles' collection.

Collection: profiles/{profile_id}

Document schema:
    {
        "name": str,
        "degree_title": str,
        "email": str,
        "phone": str,
        "location": str,
        "linkedin": str,   # full URL e.g. https://linkedin.com/in/username
        "github": str,     # full URL e.g. https://github.com/username
        "portfolio": str,
        "summary": str
    }
"""

from resume_engine.firebase_client import get_firestore_client
from resume_engine.config import config


def get_profile(profile_id: str = None) -> dict:
    """
    Fetch the profile document from Firestore.

    Args:
        profile_id: Firestore document ID. Defaults to FIRESTORE_PROFILE_ID from config.

    Returns:
        Profile data as a dict. Empty dict if not found.

    Raises:
        RuntimeError: if Firestore connection fails.
    """
    pid = profile_id or config.FIRESTORE_PROFILE_ID
    db = get_firestore_client()
    doc = db.collection("profiles").document(pid).get()

    if not doc.exists:
        print(f"  ⚠  Profile '{pid}' not found in Firestore.")
        return {}

    return doc.to_dict()


def upsert_profile(data: dict, profile_id: str = None) -> None:
    """
    Create or update the profile document in Firestore.

    Args:
        data: Profile data dict.
        profile_id: Firestore document ID. Defaults to FIRESTORE_PROFILE_ID.
    """
    pid = profile_id or config.FIRESTORE_PROFILE_ID
    db = get_firestore_client()
    db.collection("profiles").document(pid).set(data, merge=True)
    print(f"  ✓  Profile '{pid}' saved to Firestore.")

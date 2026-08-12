"""
experience_service.py — Firestore CRUD for the 'experience' collection.

Collection: experience/{auto_id}

Document schema:
    {
        "company": str,
        "role": str,
        "location": str,
        "start_date": str,        # e.g. "Jan 2023"
        "end_date": str,          # e.g. "Present"
        "description": str,
        "technologies": [str],
        "resume_bullets": [str],
        "enabled": bool,
        "sort_order": int
    }
"""

from resume_engine.firebase_client import get_firestore_client


def get_all_experience(include_disabled: bool = False) -> list[dict]:
    """
    Fetch all experience records.

    Returns:
        List of experience dicts sorted by sort_order, then start_date (desc).
    """
    db = get_firestore_client()
    docs = db.collection("experience").stream()

    records = []
    for doc in docs:
        data = doc.to_dict()
        data["_id"] = doc.id
        data.setdefault("enabled", True)
        data.setdefault("sort_order", 999)

        if not include_disabled and not data.get("enabled", True):
            continue

        records.append(data)

    records.sort(key=lambda e: (e.get("sort_order", 999),))
    return records


def add_experience(data: dict) -> str:
    """Add a new experience record. Returns the auto-generated document ID."""
    data.setdefault("enabled", True)
    data.setdefault("technologies", [])
    data.setdefault("resume_bullets", [])
    db = get_firestore_client()
    _, doc_ref = db.collection("experience").add(data)
    return doc_ref.id

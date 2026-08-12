"""
language_service.py — Firestore CRUD for the 'languages' collection.

Collection: languages/{auto_id}

Document schema:
    {
        "name": str,          # e.g. "English"
        "proficiency": str,   # e.g. "Professional working fluency"
        "enabled": bool,
        "sort_order": int
    }
"""

from resume_engine.firebase_client import get_firestore_client


def get_all_languages(include_disabled: bool = False) -> list[dict]:
    """
    Fetch all language documents.

    Returns:
        List of language dicts sorted by sort_order, then name.
    """
    db = get_firestore_client()
    docs = db.collection("languages").stream()

    langs = []
    for doc in docs:
        data = doc.to_dict()
        data["_id"] = doc.id
        data.setdefault("enabled", True)
        data.setdefault("sort_order", 999)

        if not include_disabled and not data.get("enabled", True):
            continue

        langs.append(data)

    langs.sort(key=lambda l: (l.get("sort_order", 999), l.get("name", "")))
    return langs


def add_language(name: str, proficiency: str, sort_order: int = 999) -> str:
    """Add a new language. Returns the auto-generated document ID."""
    db = get_firestore_client()
    _, doc_ref = db.collection("languages").add({
        "name": name,
        "proficiency": proficiency,
        "enabled": True,
        "sort_order": sort_order,
    })
    return doc_ref.id

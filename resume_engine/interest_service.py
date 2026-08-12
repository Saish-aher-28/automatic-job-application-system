"""
interest_service.py — Firestore CRUD for the 'interests' collection.

Collection: interests/{auto_id}

Document schema:
    {
        "name": str,       # e.g. "Reading Books"
        "enabled": bool,
        "sort_order": int
    }
"""

from resume_engine.firebase_client import get_firestore_client


def get_all_interests(include_disabled: bool = False) -> list[dict]:
    """
    Fetch all interest documents.

    Returns:
        List of interest dicts sorted by sort_order, then name.
    """
    db = get_firestore_client()
    docs = db.collection("interests").stream()

    interests = []
    for doc in docs:
        data = doc.to_dict()
        data["_id"] = doc.id
        data.setdefault("enabled", True)
        data.setdefault("sort_order", 999)

        if not include_disabled and not data.get("enabled", True):
            continue

        interests.append(data)

    interests.sort(key=lambda i: (i.get("sort_order", 999), i.get("name", "")))
    return interests


def add_interest(name: str, sort_order: int = 999) -> str:
    """Add a new interest. Returns the auto-generated document ID."""
    db = get_firestore_client()
    _, doc_ref = db.collection("interests").add({
        "name": name,
        "enabled": True,
        "sort_order": sort_order,
    })
    return doc_ref.id

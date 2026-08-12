"""
education_service.py — Firestore CRUD for the 'education' collection.

Collection: education/{auto_id}

Document schema:
    {
        "degree": str,            # e.g. "Bachelor of Engineering"
        "field": str,             # e.g. "Computer Science"
        "specialization": str,    # optional
        "institution": str,       # required
        "location": str,
        "start_year": int | null,
        "graduation_year": int | null,
        "details": [str],         # e.g. ["CGPA: 8.5/10", "HSC: 85%", "SSC: 92%"]
        "sort_order": int         # lower = displayed first
    }
"""

from resume_engine.firebase_client import get_firestore_client


def get_all_education() -> list[dict]:
    """
    Fetch all education records, sorted by sort_order then graduation_year (desc).

    Returns:
        List of education dicts with '_id'.
    """
    db = get_firestore_client()
    docs = db.collection("education").stream()

    records = []
    for doc in docs:
        data = doc.to_dict()
        data["_id"] = doc.id
        data.setdefault("sort_order", 999)
        records.append(data)

    records.sort(key=lambda e: (
        e.get("sort_order", 999),
        -(e.get("graduation_year") or 0),
    ))
    return records


def add_education(data: dict) -> str:
    """Add a new education record. Returns the auto-generated document ID."""
    from resume_engine.validators import validate_education
    errors = validate_education(data)
    if errors:
        raise ValueError("Education validation failed:\n  " + "\n  ".join(errors))
    db = get_firestore_client()
    _, doc_ref = db.collection("education").add(data)
    return doc_ref.id

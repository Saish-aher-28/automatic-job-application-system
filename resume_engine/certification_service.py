"""
certification_service.py — Firestore CRUD for the 'certifications' collection.

Collection: certifications/{auto_id}

Document schema:
    {
        "name": str,           # required, e.g. "AWS Certified Solutions Architect"
        "issuer": str,         # e.g. "Amazon Web Services"
        "date": str,           # e.g. "2023"
        "credential_url": str,
        "skills": [str],
        "enabled": bool,
        "sort_order": int
    }
"""

from resume_engine.firebase_client import get_firestore_client


def get_all_certifications(include_disabled: bool = False) -> list[dict]:
    """
    Fetch all certification documents.

    Returns:
        List of certification dicts sorted by sort_order, then name.
    """
    db = get_firestore_client()
    docs = db.collection("certifications").stream()

    certs = []
    for doc in docs:
        data = doc.to_dict()
        data["_id"] = doc.id
        data.setdefault("enabled", True)
        data.setdefault("sort_order", 999)

        if not include_disabled and not data.get("enabled", True):
            continue

        certs.append(data)

    certs.sort(key=lambda c: (c.get("sort_order", 999), c.get("name", "")))
    return certs


def add_certification(data: dict) -> str:
    """Add a new certification. Returns the auto-generated document ID."""
    from resume_engine.validators import validate_certification
    errors = validate_certification(data)
    if errors:
        raise ValueError("Certification validation failed:\n  " + "\n  ".join(errors))
    data.setdefault("enabled", True)
    data.setdefault("skills", [])
    db = get_firestore_client()
    _, doc_ref = db.collection("certifications").add(data)
    return doc_ref.id

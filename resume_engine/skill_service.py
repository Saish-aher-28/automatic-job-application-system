"""
skill_service.py — Firestore CRUD for the 'skills' collection.

Collection: skills/{skill_id}

Document schema:
    {
        "name": str,         # e.g. "Python"
        "category": str,     # e.g. "Programming Languages"
        "enabled": bool,
        "sort_order": int    # optional, for ordering within category
    }

Skills are grouped by 'category' in the generated resume.
Adding a new skill or category requires only a new Firestore document.
"""

from resume_engine.firebase_client import get_firestore_client


def get_all_skills(include_disabled: bool = False) -> list[dict]:
    """
    Fetch all skill documents.

    Returns:
        List of skill dicts, each containing '_id'. Sorted by category, then sort_order, then name.
    """
    db = get_firestore_client()
    docs = db.collection("skills").stream()

    skills = []
    for doc in docs:
        data = doc.to_dict()
        data["_id"] = doc.id
        data.setdefault("enabled", True)
        data.setdefault("sort_order", 999)

        if not include_disabled and not data.get("enabled", True):
            continue

        skills.append(data)

    skills.sort(key=lambda s: (s.get("category", ""), s.get("sort_order", 999), s.get("name", "")))
    return skills


def get_skills_by_category() -> dict[str, list[str]]:
    """
    Return skills grouped by category, preserving sort order.

    Returns:
        OrderedDict-like dict: { "Programming Languages": ["Python", "C++", ...], ... }
        Categories are in the order they first appear when sorted by category name.
    """
    skills = get_all_skills()
    grouped: dict[str, list[str]] = {}
    for skill in skills:
        cat = skill.get("category", "Other")
        grouped.setdefault(cat, [])
        grouped[cat].append(skill.get("name", ""))
    return grouped


def add_skill(name: str, category: str, sort_order: int = 999) -> str:
    """
    Add a new skill document.

    Returns:
        The auto-generated document ID.
    """
    db = get_firestore_client()
    _, doc_ref = db.collection("skills").add({
        "name": name,
        "category": category,
        "enabled": True,
        "sort_order": sort_order,
    })
    return doc_ref.id

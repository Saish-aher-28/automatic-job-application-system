"""
project_service.py — Firestore CRUD for the 'projects' collection.

CRITICAL DESIGN:
  Each project is its own Firestore document.
  Adding a new project = adding a new document.
  NO code changes, NO schema changes, NO template changes required.

Collection: projects/{auto_id}

Document schema:
    {
        "name": str,                    # required
        "year": str,
        "description": str,            # required
        "technologies": [str],          # required
        "categories": [str],
        "keywords": [str],
        "resume_bullets": [str],
        "resume_content": {
            "general": [str],
            "machine_learning": [str],
            "data_science": [str],
            "backend": [str],
            "frontend": [str],
            "cloud": [str],
            "devops": [str]
        },
        "github_url": str,
        "project_url": str,
        "priority": int,               # lower = higher priority (optional, default 999)
        "enabled": bool                # default True
    }
"""

from typing import Optional
from resume_engine.firebase_client import get_firestore_client


def get_all_projects(include_disabled: bool = False) -> list[dict]:
    """
    Fetch ALL project documents from Firestore.

    Args:
        include_disabled: If True, also return projects with enabled=False.

    Returns:
        List of project dicts, each containing a '_id' field with the document ID.
        Ordered by: priority (asc, optional field), then by name (asc) as stable fallback.
    """
    db = get_firestore_client()
    docs = db.collection("projects").stream()

    projects = []
    for doc in docs:
        data = doc.to_dict()
        data["_id"] = doc.id

        # Default enabled to True if not set
        if "enabled" not in data:
            data["enabled"] = True

        if not include_disabled and not data.get("enabled", True):
            continue

        projects.append(data)

    # Sort: priority (lower = first, default 999), then name
    projects.sort(key=lambda p: (p.get("priority", 999), p.get("name", "")))
    return projects


def get_projects_for_resume(limit: int) -> list[dict]:
    """
    Fetch the top `limit` enabled projects for resume generation.

    The remaining projects stay safely in Firestore for future JD-matching.

    Args:
        limit: Maximum number of projects to return.

    Returns:
        List of up to `limit` project dicts.
    """
    all_projects = get_all_projects(include_disabled=False)
    return all_projects[:limit]


def get_project(project_id: str) -> Optional[dict]:
    """
    Fetch a single project by document ID.

    Returns:
        Project dict with '_id' field, or None if not found.
    """
    db = get_firestore_client()
    doc = db.collection("projects").document(project_id).get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    data["_id"] = doc.id
    return data


def add_project(data: dict) -> str:
    """
    Add a new project document to Firestore.
    Firestore auto-generates the document ID.

    Args:
        data: Project data dict. Must include name, description, technologies.

    Returns:
        The auto-generated Firestore document ID.

    Raises:
        ValueError: if required fields are missing.
    """
    from resume_engine.validators import validate_project
    errors = validate_project(data)
    if errors:
        raise ValueError("Project validation failed:\n  " + "\n  ".join(errors))

    # Set defaults
    data.setdefault("enabled", True)
    data.setdefault("technologies", [])
    data.setdefault("categories", [])
    data.setdefault("keywords", [])
    data.setdefault("resume_bullets", [])

    db = get_firestore_client()
    _, doc_ref = db.collection("projects").add(data)
    return doc_ref.id


def disable_project(project_id: str) -> None:
    """
    Mark a project as disabled (enabled=False) without deleting it.
    Disabled projects remain in Firestore but are excluded from resume generation.
    """
    db = get_firestore_client()
    db.collection("projects").document(project_id).update({"enabled": False})


def enable_project(project_id: str) -> None:
    """Re-enable a previously disabled project."""
    db = get_firestore_client()
    db.collection("projects").document(project_id).update({"enabled": True})

"""
import_project.py — Import a project from a JSON file into Firestore.

Usage:
    python -m resume_engine.import_project <path/to/project.json>

Example:
    python -m resume_engine.import_project profile/projects/my_project.json

The JSON file must contain at minimum:
    {
        "name": "...",
        "description": "...",
        "technologies": [...]
    }

See profile/projects/example_project.json for a full example.
"""

import sys
import json
from pathlib import Path


def import_project_from_file(filepath: str) -> None:
    """
    Read a JSON file, validate it, and upload to Firestore.

    Args:
        filepath: Path to the JSON file (relative or absolute).
    """
    path = Path(filepath)

    # ── 1. File exists? ──────────────────────────────────────────────
    if not path.exists():
        print(f"  ✗  File not found: {path}")
        sys.exit(1)

    if path.suffix.lower() != ".json":
        print(f"  ✗  File must be a .json file. Got: {path.suffix}")
        sys.exit(1)

    # ── 2. Parse JSON ────────────────────────────────────────────────
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"  ✗  Invalid JSON in {path}: {e}")
        sys.exit(1)

    print(f"  Reading: {path}")

    # ── 3. Validate ──────────────────────────────────────────────────
    from resume_engine.validators import validate_project
    errors = validate_project(data)
    if errors:
        print("  ✗  Validation failed:")
        for err in errors:
            print(f"       - {err}")
        sys.exit(1)

    print(f"  ✓  Validation passed.")

    # ── 4. Upload to Firestore ───────────────────────────────────────
    try:
        from resume_engine.project_service import add_project
        project_id = add_project(data)
        print(f"  ✓  Project uploaded successfully.")
        print(f"     Project ID: {project_id}")
        print()
        print("  Run 'python -m resume_engine.main' to regenerate your resume.")
        print()
    except Exception as exc:
        print(f"  ✗  Upload failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print()
        print("  Usage: python -m resume_engine.import_project <path/to/project.json>")
        print()
        print("  Example:")
        print("    python -m resume_engine.import_project profile/projects/my_project.json")
        print()
        sys.exit(1)

    print()
    print("═" * 60)
    print("  Import Project from JSON")
    print("═" * 60)
    print()

    import_project_from_file(sys.argv[1])

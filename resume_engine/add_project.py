"""
add_project.py — Interactive CLI to add a new project to Firestore.

Usage:
    python -m resume_engine.add_project

This script is also importable; call add_project_interactive() directly.

DESIGN: Adding a new project requires ONLY running this script.
        No Python code, LaTeX template, or Firestore schema changes needed.
"""

import sys


def _prompt(label: str, required: bool = False) -> str:
    """Prompt user for a string value. Re-prompts if required and empty."""
    while True:
        value = input(f"  {label}: ").strip()
        if value or not required:
            return value
        print(f"  ✗  '{label}' is required. Please enter a value.")


def _prompt_list(label: str) -> list[str]:
    """Prompt for a comma-separated list. Returns a list of stripped strings."""
    raw = input(f"  {label} (comma-separated, or leave blank): ").strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _prompt_bullets() -> list[str]:
    """Prompt for resume bullets one per line. Empty line ends input."""
    print("  Resume bullets (one per line, press Enter on empty line when done):")
    bullets = []
    while True:
        line = input("    > ").strip()
        if not line:
            break
        bullets.append(line)
    return bullets


def add_project_interactive() -> None:
    """
    Run the interactive project-addition flow and upload to Firestore.
    """
    print()
    print("═" * 60)
    print("  Add New Project to Firestore")
    print("═" * 60)
    print()

    name         = _prompt("Project name", required=True)
    year         = _prompt("Year (e.g. 2024, or leave blank)")
    description  = _prompt("Description", required=True)
    technologies = _prompt_list("Technologies")
    categories   = _prompt_list("Categories (e.g. machine_learning, backend)")
    keywords     = _prompt_list("Keywords")
    github_url   = _prompt("GitHub URL")
    project_url  = _prompt("Project URL")
    bullets      = _prompt_bullets()

    print()

    data = {
        "name":           name,
        "description":    description,
        "technologies":   technologies,
        "categories":     categories,
        "keywords":       keywords,
        "resume_bullets": bullets,
        "resume_content": {
            "general":         [],
            "machine_learning":[],
            "data_science":    [],
            "backend":         [],
            "frontend":        [],
            "cloud":           [],
            "devops":          [],
        },
        "enabled": True,
    }
    if year:
        data["year"] = year
    if github_url:
        data["github_url"] = github_url
    if project_url:
        data["project_url"] = project_url

    # Confirm before upload
    print("  Project summary:")
    print(f"    Name:          {name}")
    print(f"    Year:          {year or '(not set)'}")
    print(f"    Technologies:  {', '.join(technologies) or '(none)'}")
    print(f"    Categories:    {', '.join(categories) or '(none)'}")
    print(f"    Bullets:       {len(bullets)} bullet(s)")
    print()

    confirm = input("  Upload to Firestore? [Y/n]: ").strip().lower()
    if confirm not in ("", "y", "yes"):
        print("  Cancelled.")
        return

    try:
        from resume_engine.project_service import add_project
        project_id = add_project(data)
        print()
        print("  ✓  Project added successfully.")
        print(f"     Project ID: {project_id}")
        print()
        print("  Run 'python -m resume_engine.main' to regenerate your resume.")
        print()
    except Exception as exc:
        print(f"\n  ✗  Failed to add project: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    add_project_interactive()

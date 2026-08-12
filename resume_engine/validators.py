"""
validators.py — Input validation and LaTeX-safe string escaping.

Rules:
  - LaTeX escaping applies to ALL user-supplied text inserted into the body.
  - URLs must NOT be escaped — they go inside \\href{URL}{text}.
  - The escape function handles the 10 LaTeX-special characters:
      \\ & % $ # _ { } ^ ~
"""

import re
from typing import Any


# ------------------------------------------------------------------ #
# LaTeX Escaping
# ------------------------------------------------------------------ #

# Order matters: backslash must come first to avoid double-escaping.
_LATEX_ESCAPE_MAP = [
    ("\\", r"\textbackslash{}"),
    ("&",  r"\&"),
    ("%",  r"\%"),
    ("$",  r"\$"),
    ("#",  r"\#"),
    ("_",  r"\_"),
    ("{",  r"\{"),
    ("}",  r"\}"),
    ("^",  r"\textasciicircum{}"),
    ("~",  r"\textasciitilde{}"),
]


def latex_escape(text: str) -> str:
    """
    Escape a plain-text string so it is safe to insert into LaTeX source.

    Examples:
        "C++"          → "C++"          (+ is not special)
        "Python"       → "Python"
        "50%"          → "50\\%"
        "R&D"          → "R\\&D"
        "user_name"    → "user\\_name"
        "$100"         → "\\$100"
        "A & B"        → "A \\& B"
        "path\\file"   → "path\\textbackslash{}file"
    """
    if not isinstance(text, str):
        text = str(text)
    for char, replacement in _LATEX_ESCAPE_MAP:
        text = text.replace(char, replacement)
    return text


def latex_escape_list(items: list) -> list[str]:
    """Escape a list of strings."""
    return [latex_escape(str(item)) for item in items]


def latex_escape_url(url: str) -> str:
    """
    URLs used inside \\href{}{} must not be LaTeX-escaped in the URL slot.
    However, they should have % encoded as \\% if they appear in text.
    This function returns the URL as-is for use in \\href{URL}{...}.
    """
    return url.strip()


# ------------------------------------------------------------------ #
# Field Validation
# ------------------------------------------------------------------ #

REQUIRED_PROJECT_FIELDS = {"name", "description", "technologies"}
REQUIRED_PROFILE_FIELDS = {"name", "email"}


def validate_project(data: dict) -> list[str]:
    """
    Validate a project document dict.
    Returns a list of error messages. Empty = valid.
    """
    errors = []
    for field in REQUIRED_PROJECT_FIELDS:
        if not data.get(field):
            errors.append(f"Project is missing required field: '{field}'")
    if "technologies" in data and not isinstance(data["technologies"], list):
        errors.append("'technologies' must be a list.")
    if "categories" in data and not isinstance(data["categories"], list):
        errors.append("'categories' must be a list.")
    if "keywords" in data and not isinstance(data["keywords"], list):
        errors.append("'keywords' must be a list.")
    if "resume_bullets" in data and not isinstance(data["resume_bullets"], list):
        errors.append("'resume_bullets' must be a list.")
    if "enabled" in data and not isinstance(data["enabled"], bool):
        errors.append("'enabled' must be a boolean.")
    return errors


def validate_profile(data: dict) -> list[str]:
    """
    Validate a profile document dict.
    Returns a list of error messages. Empty = valid.
    """
    errors = []
    for field in REQUIRED_PROFILE_FIELDS:
        if not data.get(field):
            errors.append(f"Profile is missing required field: '{field}'")
    return errors


def validate_certification(data: dict) -> list[str]:
    errors = []
    if not data.get("name"):
        errors.append("Certification is missing required field: 'name'")
    return errors


def validate_education(data: dict) -> list[str]:
    errors = []
    if not data.get("institution"):
        errors.append("Education record is missing required field: 'institution'")
    return errors


def coerce_list(value: Any) -> list:
    """
    Ensure a value is a list.
    Handles: None → [], str → [str], list → list.
    """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def extract_username_from_url(url: str, platform: str) -> str:
    """
    Extract a username from a social URL.

    Examples:
        extract_username_from_url("https://linkedin.com/in/johndoe", "linkedin") → "johndoe"
        extract_username_from_url("https://github.com/johndoe", "github") → "johndoe"
        extract_username_from_url("johndoe", "github") → "johndoe"
    """
    if not url:
        return ""
    url = url.strip().rstrip("/")

    patterns = {
        "linkedin": r"linkedin\.com/in/([^/\s]+)",
        "github":   r"github\.com/([^/\s]+)",
    }
    pattern = patterns.get(platform.lower())
    if pattern:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1)

    # Fallback: return the last path segment
    parts = url.split("/")
    return parts[-1] if parts else url

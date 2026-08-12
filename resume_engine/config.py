"""
config.py — Centralised configuration for the resume engine.

All values are loaded from the .env file via python-dotenv.
Sensible defaults are provided where appropriate.
NEVER hardcode credentials or absolute paths here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root (two levels up from this file)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


class Config:
    """Single configuration object for Phase 1."""

    # ------------------------------------------------------------------ #
    # Firebase / Firestore
    # ------------------------------------------------------------------ #
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS", ""
    )
    FIRESTORE_PROFILE_ID: str = os.getenv("FIRESTORE_PROFILE_ID", "main")

    # ------------------------------------------------------------------ #
    # Resume generation
    # ------------------------------------------------------------------ #
    RESUME_PROJECT_LIMIT: int = int(os.getenv("RESUME_PROJECT_LIMIT", "3"))

    # ------------------------------------------------------------------ #
    # LaTeX paths (relative to project root)
    # ------------------------------------------------------------------ #
    _LATEX_TEMPLATE_PATH: str = os.getenv(
        "LATEX_TEMPLATE_PATH", "latex/resume_tex.tex"
    )
    _LATEX_OUTPUT_DIR: str = os.getenv("LATEX_OUTPUT_DIR", "latex/output")

    LATEX_TEMPLATE_PATH: Path = _PROJECT_ROOT / _LATEX_TEMPLATE_PATH
    LATEX_OUTPUT_DIR: Path = _PROJECT_ROOT / _LATEX_OUTPUT_DIR
    LATEX_OUTPUT_TEX: Path = LATEX_OUTPUT_DIR / "resume.tex"
    LATEX_OUTPUT_PDF: Path = LATEX_OUTPUT_DIR / "resume.pdf"

    # ------------------------------------------------------------------ #
    # Page limit
    # ------------------------------------------------------------------ #
    MAX_RESUME_PAGES: int = 2

    @classmethod
    def validate(cls) -> list[str]:
        """Return a list of configuration warnings. Empty list = all good."""
        warnings = []
        if not cls.GOOGLE_APPLICATION_CREDENTIALS:
            warnings.append(
                "GOOGLE_APPLICATION_CREDENTIALS is not set. "
                "Set it in your .env file pointing to your Firebase service account JSON."
            )
        elif not Path(cls.GOOGLE_APPLICATION_CREDENTIALS).exists():
            warnings.append(
                f"Service account file not found: {cls.GOOGLE_APPLICATION_CREDENTIALS}"
            )
        if not cls.LATEX_TEMPLATE_PATH.exists():
            warnings.append(
                f"LaTeX template not found: {cls.LATEX_TEMPLATE_PATH}"
            )
        return warnings


# Singleton — import and use directly
config = Config()

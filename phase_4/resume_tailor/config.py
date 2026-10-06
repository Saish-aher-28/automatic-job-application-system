"""
config.py — Centralised configuration for Phase 4 Resume Tailoring.

Reads from the shared root .env file.
Never hardcode credentials or absolute paths here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (three levels up from this file)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=False)


class Phase4Config:
    """Single configuration object for Phase 4."""

    # ── Generator versioning ────────────────────────────────────────────────
    GENERATOR_VERSION: str = "4.0"

    # ── Firebase / Firestore ────────────────────────────────────────────────
    GOOGLE_APPLICATION_CREDENTIALS: str = os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS", ""
    )

    # ── Gemini ──────────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_MODEL:   str = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
    MAX_RETRIES:    int = int(os.environ.get("GEMINI_MAX_RETRIES", "3"))
    API_TIMEOUT:    int = int(os.environ.get("GEMINI_TIMEOUT_SECONDS", "60"))

    # ── Firestore collections ───────────────────────────────────────────────
    FIRESTORE_MATCH_COLLECTION:    str = "job_matches"
    FIRESTORE_JD_COLLECTION:       str = "job_descriptions"
    FIRESTORE_TAILORED_COLLECTION: str = "tailored_resumes"

    # ── Resume project selection ────────────────────────────────────────────
    PROJECT_SELECT_LIMIT: int = int(os.environ.get("RESUME_PROJECT_LIMIT", "3"))
    MAX_OVERFLOW_RETRIES: int = 3   # max project drops to attempt for page overflow

    # ── Page limit ──────────────────────────────────────────────────────────
    MAX_RESUME_PAGES: int = 2

    # ── LaTeX paths ─────────────────────────────────────────────────────────
    _LATEX_TEMPLATE_PATH: str = os.environ.get(
        "LATEX_TEMPLATE_PATH", "latex/resume_tex.tex"
    )
    LATEX_TEMPLATE_PATH: Path = _PROJECT_ROOT / _LATEX_TEMPLATE_PATH
    LATEX_TAILORED_OUTPUT_BASE: Path = _PROJECT_ROOT / "latex" / "output" / "tailored"

    def tailored_output_dir(self, match_id: str) -> Path:
        """Return the output directory for a specific match."""
        return self.LATEX_TAILORED_OUTPUT_BASE / match_id

    def tailored_tex_path(self, match_id: str) -> Path:
        return self.tailored_output_dir(match_id) / "resume.tex"

    def tailored_pdf_path(self, match_id: str) -> Path:
        return self.tailored_output_dir(match_id) / "resume.pdf"


# Singleton
config = Phase4Config()

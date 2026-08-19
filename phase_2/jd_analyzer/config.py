"""
config.py — Phase 2 configuration.

Reads all environment variables from the project .env (one level up from Phase 2/).
Never hardcodes secrets.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the Phase 1 root (parent of "phase_2")
_ROOT = Path(__file__).resolve().parent.parent.parent   # e:\AutoResume\Phase 1
_ENV_PATH = _ROOT / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=False)


class Phase2Config:
    # ── Gemini ───────────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_MODEL:   str = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
    MAX_RETRIES:    int = int(os.environ.get("GEMINI_MAX_RETRIES", "3"))
    API_TIMEOUT:    int = int(os.environ.get("GEMINI_TIMEOUT_SECONDS", "60"))

    # ── Firebase (shared with Phase 1 creds) ─────────────────────────────────
    GOOGLE_APPLICATION_CREDENTIALS: str = os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS", ""
    )

    # ── phase_2 paths ─────────────────────────────────────────────────────────
    PHASE2_ROOT:   Path = Path(__file__).resolve().parent.parent   # e:\…\phase_2
    OUTPUT_DIR:    Path = PHASE2_ROOT / "output"
    INPUT_DIR:     Path = PHASE2_ROOT / "input"

    # ── Firestore ─────────────────────────────────────────────────────────────
    FIRESTORE_JD_COLLECTION: str = "job_descriptions"

    # ── Analysis metadata ─────────────────────────────────────────────────────
    ANALYSIS_VERSION: str = "1.0"

    # ── Input limits ──────────────────────────────────────────────────────────
    MIN_JD_LENGTH:  int = 20       # characters
    MAX_JD_LENGTH:  int = 30_000   # characters (well within Gemini context)


config = Phase2Config()

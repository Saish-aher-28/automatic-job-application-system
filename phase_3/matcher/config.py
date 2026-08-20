"""
config.py — Phase 3 configuration parameters.

Reads environment variables from the shared Phase 1 root .env.
Ensures match scoring weights are configurable and valid (sum to 1.0).
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from Phase 1 root
_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_PATH = _ROOT / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=False)


class Phase3Config:
    # ── Gemini ───────────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_MODEL:   str = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
    MAX_RETRIES:    int = int(os.environ.get("GEMINI_MAX_RETRIES", "3"))
    API_TIMEOUT:    int = int(os.environ.get("GEMINI_TIMEOUT_SECONDS", "60"))

    # ── Firebase ─────────────────────────────────────────────────────────────
    GOOGLE_APPLICATION_CREDENTIALS: str = os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS", ""
    )

    # ── Collections ──────────────────────────────────────────────────────────
    FIRESTORE_JD_COLLECTION:    str = "job_descriptions"
    FIRESTORE_MATCH_COLLECTION: str = "job_matches"

    # ── Versioning ───────────────────────────────────────────────────────────
    MATCHER_VERSION: str = "1.0"

    # ── Scoring Weights (Must sum to 1.0) ────────────────────────────────────
    REQUIRED_SKILL_WEIGHT:  float = float(os.environ.get("WEIGHT_REQUIRED_SKILL", "0.50"))
    PREFERRED_SKILL_WEIGHT: float = float(os.environ.get("WEIGHT_PREFERRED_SKILL", "0.15"))
    TECHNOLOGY_WEIGHT:      float = float(os.environ.get("WEIGHT_TECHNOLOGY", "0.15"))
    PROJECT_WEIGHT:         float = float(os.environ.get("WEIGHT_PROJECT", "0.20"))

    # ── Project Deterministic Weights (Must sum to 1.0) ──────────────────────
    PROJECT_REQUIRED_WEIGHT:   float = float(os.environ.get("WEIGHT_PROJECT_REQUIRED", "0.40"))
    PROJECT_PREFERRED_WEIGHT:  float = float(os.environ.get("WEIGHT_PROJECT_PREFERRED", "0.15"))
    PROJECT_TECHNOLOGY_WEIGHT: float = float(os.environ.get("WEIGHT_PROJECT_TECH", "0.20"))
    PROJECT_KEYWORD_WEIGHT:    float = float(os.environ.get("WEIGHT_PROJECT_KEYWORD", "0.15"))
    PROJECT_CATEGORY_WEIGHT:   float = float(os.environ.get("WEIGHT_PROJECT_CATEGORY", "0.10"))

    # ── Project Semantic Options ─────────────────────────────────────────────
    SEMANTIC_PROJECT_CANDIDATES: int = int(os.environ.get("SEMANTIC_PROJECT_CANDIDATES", "5"))
    PROJECT_SEMANTIC_BLEND_WEIGHT: float = float(os.environ.get("PROJECT_SEMANTIC_BLEND_WEIGHT", "0.70"))

    # ── Output directories ───────────────────────────────────────────────────
    PHASE3_ROOT: Path = Path(__file__).resolve().parent.parent
    OUTPUT_DIR:  Path = PHASE3_ROOT / "output"

    def __init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Validate that all scoring weights sum up exactly to 1.0."""
        # 1. Overall matcher weights validation
        overall_sum = (
            self.REQUIRED_SKILL_WEIGHT
            + self.PREFERRED_SKILL_WEIGHT
            + self.TECHNOLOGY_WEIGHT
            + self.PROJECT_WEIGHT
        )
        if not abs(overall_sum - 1.0) < 1e-9:
            raise ValueError(
                f"Overall matcher weights must sum to 1.0 (currently {overall_sum}). "
                f"Weights: required={self.REQUIRED_SKILL_WEIGHT}, preferred={self.PREFERRED_SKILL_WEIGHT}, "
                f"tech={self.TECHNOLOGY_WEIGHT}, project={self.PROJECT_WEIGHT}"
            )

        # 2. Project matcher weights validation
        project_sum = (
            self.PROJECT_REQUIRED_WEIGHT
            + self.PROJECT_PREFERRED_WEIGHT
            + self.PROJECT_TECHNOLOGY_WEIGHT
            + self.PROJECT_KEYWORD_WEIGHT
            + self.PROJECT_CATEGORY_WEIGHT
        )
        if not abs(project_sum - 1.0) < 1e-9:
            raise ValueError(
                f"Project matcher weights must sum to 1.0 (currently {project_sum}). "
                f"Weights: req={self.PROJECT_REQUIRED_WEIGHT}, pref={self.PROJECT_PREFERRED_WEIGHT}, "
                f"tech={self.PROJECT_TECHNOLOGY_WEIGHT}, kw={self.PROJECT_KEYWORD_WEIGHT}, cat={self.PROJECT_CATEGORY_WEIGHT}"
            )


config = Phase3Config()

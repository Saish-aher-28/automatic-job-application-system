"""
config.py — Configuration settings loader for Phase 6.
"""

from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv


class Config:
    """
    Loads Phase 6 configuration variables from process environment and root .env files.
    """

    def __init__(self):
        # Find project root by looking for requirements.txt or go.mod upwards
        self.project_root = Path(__file__).resolve().parents[2]
        
        # Load .env at project root
        env_path = self.project_root / ".env"
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)

        # Load Phase 6 .env if it exists
        phase6_env = self.project_root / "phase_6" / ".env"
        if phase6_env.exists():
            load_dotenv(dotenv_path=phase6_env, override=True)

        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        self.GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        
        self.GOOGLE_APPLICATION_CREDENTIALS = os.getenv(
            "GOOGLE_APPLICATION_CREDENTIALS",
            str(self.project_root / "firebase-credentials" / "automatic-job-applicatio-7b237-firebase-adminsdk-fbsvc-a5c2b6fd17.json")
        )
        self.FIRESTORE_PROFILE_ID = os.getenv("FIRESTORE_PROFILE_ID", "main")

        self.TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
        self.TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
        self.TELEGRAM_SESSION = os.getenv("TELEGRAM_SESSION", "phase6_ingestion")
        
        # Parse comma-separated sources
        sources_raw = os.getenv("TELEGRAM_SOURCES", "")
        self.TELEGRAM_SOURCES = [s.strip() for s in sources_raw.split(",") if s.strip()]

        self.MAX_MESSAGES = int(os.getenv("MAX_MESSAGES", "100"))
        self.MAX_PAGES = int(os.getenv("MAX_PAGES", "5"))
        self.REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "15"))
        self.MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
        self.CRAWL_INTERVAL = int(os.getenv("CRAWL_INTERVAL", "3600"))
        
        dry_run_raw = os.getenv("DRY_RUN", "false").lower()
        self.DRY_RUN = dry_run_raw in ["true", "1", "yes"]

        # Website sources — optional JSON array string configuring crawl targets.
        # Example: '[{"name":"My Job Board","listing_url":"https://example.com/jobs","base_url":"https://example.com","enabled":true}]'
        import json as _json
        website_sources_raw = os.getenv("WEBSITE_SOURCES", "")
        if website_sources_raw.strip():
            try:
                self.WEBSITE_SOURCES = _json.loads(website_sources_raw)
            except Exception:
                self.WEBSITE_SOURCES = []
        else:
            self.WEBSITE_SOURCES = []



config = Config()

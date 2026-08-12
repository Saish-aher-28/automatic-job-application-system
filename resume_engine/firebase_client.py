"""
firebase_client.py — Firebase Admin SDK initialisation and Firestore client.

Responsibilities:
  - Initialise Firebase once (singleton pattern).
  - Authenticate via GOOGLE_APPLICATION_CREDENTIALS.
  - Return a ready-to-use Firestore client.
  - Provide clear, actionable error messages.

Usage:
    from resume_engine.firebase_client import get_firestore_client
    db = get_firestore_client()
    doc = db.collection("projects").document("abc").get()
"""

import os
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore

from resume_engine.config import config

_firestore_client = None  # module-level singleton


def get_firestore_client():
    """
    Return a Firestore client, initialising Firebase Admin if needed.

    Raises:
        RuntimeError: if credentials are missing or invalid.
    """
    global _firestore_client

    if _firestore_client is not None:
        return _firestore_client

    cred_path = config.GOOGLE_APPLICATION_CREDENTIALS

    if not cred_path:
        raise RuntimeError(
            "\n"
            "═══════════════════════════════════════════════════════════\n"
            "  Firebase credentials not configured.\n"
            "\n"
            "  Steps to fix:\n"
            "  1. Go to Firebase Console → Project Settings → Service Accounts\n"
            "  2. Click 'Generate new private key' → download the JSON file\n"
            "  3. Save it somewhere safe (NOT inside the project directory)\n"
            "  4. Copy .env.example to .env\n"
            "  5. Set GOOGLE_APPLICATION_CREDENTIALS=/full/path/to/key.json\n"
            "═══════════════════════════════════════════════════════════\n"
        )

    cred_path = Path(cred_path)
    if not cred_path.exists():
        raise RuntimeError(
            f"\n"
            f"═══════════════════════════════════════════════════════════\n"
            f"  Service account file not found:\n"
            f"    {cred_path}\n"
            f"\n"
            f"  Check the GOOGLE_APPLICATION_CREDENTIALS path in your .env file.\n"
            f"═══════════════════════════════════════════════════════════\n"
        )

    # Only initialise if no app has been initialised yet
    if not firebase_admin._apps:
        cred = credentials.Certificate(str(cred_path))
        firebase_admin.initialize_app(cred)

    _firestore_client = firestore.client()
    return _firestore_client


def reset_client():
    """
    Reset the singleton — used in tests to allow re-initialisation.
    """
    global _firestore_client
    _firestore_client = None

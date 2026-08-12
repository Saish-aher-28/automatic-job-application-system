"""
test_firebase.py — Firebase connection tests.

NOTE: These tests require real Firebase credentials.
      They are SKIPPED automatically if GOOGLE_APPLICATION_CREDENTIALS is not set.

Run with:
    python -m pytest tests/test_firebase.py -v
"""

import pytest
import os
from pathlib import Path


def credentials_available() -> bool:
    cred = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    return bool(cred) and Path(cred).exists()


REQUIRES_FIREBASE = pytest.mark.skipif(
    not credentials_available(),
    reason="GOOGLE_APPLICATION_CREDENTIALS not set or file not found. Set up Firebase first."
)


class TestFirebaseConnection:

    @REQUIRES_FIREBASE
    def test_get_firestore_client_returns_client(self):
        """Firestore client should initialize without error."""
        from resume_engine.firebase_client import get_firestore_client, reset_client
        reset_client()
        db = get_firestore_client()
        assert db is not None

    @REQUIRES_FIREBASE
    def test_firestore_client_is_singleton(self):
        """Two calls should return the same client object."""
        from resume_engine.firebase_client import get_firestore_client
        db1 = get_firestore_client()
        db2 = get_firestore_client()
        assert db1 is db2

    def test_missing_credentials_raises_runtime_error(self):
        """Without credentials, should raise RuntimeError with helpful message."""
        from resume_engine.firebase_client import reset_client
        reset_client()

        import firebase_admin
        # Delete all initialized apps to force re-init
        for app in list(firebase_admin._apps.values()):
            firebase_admin.delete_app(app)
        reset_client()

        original = os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
        try:
            from resume_engine import firebase_client as fc
            fc._firestore_client = None

            # Temporarily override config
            import resume_engine.config as cfg_module
            original_cred = cfg_module.config.GOOGLE_APPLICATION_CREDENTIALS
            cfg_module.config.GOOGLE_APPLICATION_CREDENTIALS = ""

            with pytest.raises(RuntimeError, match="credentials"):
                fc.get_firestore_client()

            cfg_module.config.GOOGLE_APPLICATION_CREDENTIALS = original_cred
        finally:
            if original:
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = original

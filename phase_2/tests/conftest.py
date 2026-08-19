"""
conftest.py — Adds Phase 1 root to sys.path so tests can import phase_2.*.

Placed in phase_2/ root so pytest picks it up automatically.
"""
import sys
from pathlib import Path

# Add Phase 1 root so that `import phase_2` resolves correctly.

_PHASE1_ROOT = Path(__file__).resolve().parent.parent  # e:\AutoResume\Phase 1
if str(_PHASE1_ROOT) not in sys.path:
    sys.path.insert(0, str(_PHASE1_ROOT))

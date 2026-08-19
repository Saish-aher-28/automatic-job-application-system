"""
conftest.py — Adds Phase 2 to sys.path so tests can import phase_2.*.

Placed in Phase 2/ root so pytest picks it up automatically.
"""
import sys
from pathlib import Path

# The "Phase 2" directory is the package root.
# Add its PARENT (Phase 1 root) so that `import phase_2` resolves correctly.
# We also add a symlink-compatible alias: "Phase 2" → "phase_2" isn't valid Python,
# so we add the parent of "Phase 2" and tell Python the package name is "phase_2"
# via the __init__.py at Phase 1 root level.

_PHASE1_ROOT = Path(__file__).resolve().parent.parent  # e:\AutoResume\Phase 1
if str(_PHASE1_ROOT) not in sys.path:
    sys.path.insert(0, str(_PHASE1_ROOT))

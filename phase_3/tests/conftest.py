"""
conftest.py — Adds Phase 1 root to sys.path so tests can import phase_3.*.

Placed in phase_3/tests/ root so pytest picks it up automatically.
"""

import sys
from pathlib import Path

# Add Phase 1 root (two levels up from conftest.py) so that `import phase_3` resolves
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

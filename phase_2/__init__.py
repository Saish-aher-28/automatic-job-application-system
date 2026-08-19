"""
phase_2/__init__.py

This thin package makes `import phase_2.jd_analyzer.*` work from the
Phase 1 project root, even though the real source lives in the
'Phase 2/' directory (which has a space and is not directly importable).

All modules are re-exported transparently via sys.path manipulation below.
"""

import sys
from pathlib import Path

# Add "Phase 2/" itself to sys.path so that `from jd_analyzer.xxx import ...`
# would work directly, BUT we actually want `phase_2.jd_analyzer.*` — so we
# make this package's subpackages importable by modifying __path__.
_PHASE2_DIR = Path(__file__).resolve().parent.parent / "Phase 2"

# Extend this package's search path to include the real "Phase 2" directory.
# This lets `import phase_2.jd_analyzer` find `Phase 2/jd_analyzer/`.
__path__ = [str(_PHASE2_DIR)] + list(__path__)

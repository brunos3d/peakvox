"""Conftest for runtime-registry/xtts-v2 tests.

Mirrors runtime-registry/f5-tts-base/tests/conftest.py: adds the xtts-v2
directory to sys.path so that ``import server`` resolves to
``runtime-registry/xtts-v2/server.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

_XTTS_DIR = Path(__file__).resolve().parents[1]
if str(_XTTS_DIR) not in sys.path:
    sys.path.insert(0, str(_XTTS_DIR))

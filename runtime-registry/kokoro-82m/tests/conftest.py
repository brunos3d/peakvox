"""Conftest for runtime-registry/kokoro-82m tests.

The runtime-registry directory uses a hyphen (per the spec
— "Keep: runtime-registry/ — This remains the correct name"),
which is not directly importable in Python. This conftest
adds the kokoro-82m directory to sys.path so that
``import server`` resolves to
``runtime-registry/kokoro-82m/server.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

_KOKORO_DIR = Path(__file__).resolve().parents[1]
if str(_KOKORO_DIR) not in sys.path:
    sys.path.insert(0, str(_KOKORO_DIR))

"""Conftest for runtime-registry/f5-tts-base tests.

Mirrors runtime-registry/kokoro-82m/tests/conftest.py: adds
the f5-tts-base directory to sys.path so that ``import server``
resolves to ``runtime-registry/f5-tts-base/server.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

_F5_TTS_DIR = Path(__file__).resolve().parents[1]
if str(_F5_TTS_DIR) not in sys.path:
    sys.path.insert(0, str(_F5_TTS_DIR))

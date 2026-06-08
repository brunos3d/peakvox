"""Conftest for runtime-registry/omnivoice-base tests.

Mirrors runtime-registry/kokoro-82m/tests/conftest.py: adds the
omnivoice-base directory to sys.path so that ``import server``
resolves to ``runtime-registry/omnivoice-base/server.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

_OMNIVOICE_DIR = Path(__file__).resolve().parents[1]
if str(_OMNIVOICE_DIR) not in sys.path:
    sys.path.insert(0, str(_OMNIVOICE_DIR))

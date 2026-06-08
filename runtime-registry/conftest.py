"""Top-level conftest for runtime-registry/.

This conftest ensures the ``runtime_registry`` package is
importable when the test runner is invoked from anywhere in
the repository. Tests inside ``runtime-registry/<id>/tests/``
import their server as ``from runtime_registry.<id> import server``.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add the repository root to sys.path so that `import runtime_registry`
# resolves to `runtime-registry/` at the repo root.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


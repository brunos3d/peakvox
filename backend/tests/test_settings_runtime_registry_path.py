"""TDD: RUNTIME_REGISTRY_PATH settings field (2D.5).

The runtime-registry/ path is configured via
``Settings.RUNTIME_REGISTRY_PATH``. The default points to the
in-repo ``runtime-registry/`` directory; deployments can
override it (e.g. to a different mount, or to an empty path
when runtimes are managed externally).
"""

from __future__ import annotations

from pathlib import Path

import pytest


def test_settings_runtime_registry_path_default_points_to_repo_root() -> None:
    """The default RUNTIME_REGISTRY_PATH points to the
    runtime-registry/ directory at the repo root."""
    from app.core.config import Settings
    s = Settings()
    # The default is the directory adjacent to the backend/
    # package's grandparent.
    expected = Path(__file__).resolve().parents[2] / "runtime-registry"
    assert s.RUNTIME_REGISTRY_PATH == expected


def test_settings_runtime_registry_path_can_be_overridden(monkeypatch, tmp_path) -> None:
    """A custom path is reflected in settings.RUNTIME_REGISTRY_PATH."""
    monkeypatch.setenv("RUNTIME_REGISTRY_PATH", str(tmp_path))
    from app.core.config import Settings
    s = Settings()
    assert s.RUNTIME_REGISTRY_PATH == tmp_path

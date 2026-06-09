"""TDD: Settings.RUNTIME_SERVICE_ENABLED (R3) — Phase 3 infrastructure gate.

The runtime subsystem is always-on as of Task 21. The flag governs whether
``main.py`` lifespan instantiates the RuntimeRegistryLoader, DockerRuntimeDriver,
and RuntimeManager, and attaches the manager to PeakVoxRuntime.

CE default: ``True`` (runtime containers are the only execution path; Task 21
removed the in-process fallback). Can be overridden to ``False`` for test/CI
environments without Docker.
"""

from __future__ import annotations

import pytest


def test_settings_runtime_service_enabled_default_is_true() -> None:
    """The default value of RUNTIME_SERVICE_ENABLED is True (Task 21: always-on)."""
    from app.core.config import Settings
    s = Settings()
    assert s.RUNTIME_SERVICE_ENABLED is True


def test_settings_runtime_service_enabled_can_be_disabled(monkeypatch) -> None:
    """Setting the env var RUNTIME_SERVICE_ENABLED=false disables the subsystem."""
    monkeypatch.setenv("RUNTIME_SERVICE_ENABLED", "false")
    from app.core.config import Settings
    s = Settings()
    assert s.RUNTIME_SERVICE_ENABLED is False


def test_settings_runtime_service_enabled_can_be_explicitly_enabled(
    monkeypatch,
) -> None:
    """An explicit 'true' env var is honored (idempotent with the default)."""
    monkeypatch.setenv("RUNTIME_SERVICE_ENABLED", "true")
    from app.core.config import Settings
    s = Settings()
    assert s.RUNTIME_SERVICE_ENABLED is True


def test_settings_runtime_service_enabled_accepts_truthy_strings(
    monkeypatch,
) -> None:
    """The pydantic-settings bool parser accepts common truthy strings."""
    for truthy in ("true", "True", "1", "yes", "on"):
        monkeypatch.setenv("RUNTIME_SERVICE_ENABLED", truthy)
        from app.core.config import Settings
        s = Settings()
        assert s.RUNTIME_SERVICE_ENABLED is True, f"failed for {truthy!r}"

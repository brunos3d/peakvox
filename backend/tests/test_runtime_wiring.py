"""TDD: runtime_wiring.py — Phase 3 startup wiring (R3 + R6).

The runtime subsystem is opt-in at backend startup. The
``Settings.RUNTIME_SERVICE_ENABLED`` flag governs whether
``wire_runtime_services`` constructs the registry, the
driver, and the manager.

When the flag is False (CE default):
  - ``wire_runtime_services`` returns None.
  - ``PeakVoxRuntime.attach_runtime_manager`` is NOT called.
  - The Models page uses the legacy DB-status mock.
  - The in-process adapter path is the only path.

When the flag is True:
  - The function constructs ``RuntimeRegistryLoader``,
    ``DockerRuntimeDriver``, and ``RuntimeManager``.
  - The manager is attached to ``PeakVoxRuntime``.
  - **No runtime container is started at boot** (R6). The
    first ``RuntimeManager.resolve`` call activates the
    runtime lazily.
  - The function returns the manager (so the lifespan can
    start the idle reaper task in P3).

The wiring is **provider-agnostic** — it does not know
about Kokoro, F5, XTTS, OpenVoice, or Fish. The providers
are in the descriptors and the adapter config.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.runtime_manager import RuntimeManager
from app.services.runtime_registry import RuntimeRegistry
from app.services.runtime_wiring import wire_runtime_services


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_registry_dir(tmp_path: Path) -> Path:
    """A temp directory with a single minimal Kokoro descriptor."""
    d = tmp_path / "kokoro-82m"
    d.mkdir()
    descriptor = {
        "api_version": "peakvox.io/v1",
        "kind": "Runtime",
        "metadata": {
            "id": "kokoro-82m",
            "name": "Kokoro 82M Runtime",
            "provider": "kokoro",
            "version": "0.1.0",
            "edition": ["ce"],
        },
        "spec": {
            "runtime_type": "docker",
            "image": {
                "repository": "peakvox/kokoro-runtime",
                "tag": "0.1.0",
            },
            "service": {
                "protocol": "http",
                "port": 8000,
            },
            "capabilities": ["tts"],
            "requirements": {
                "gpu": "optional",
                "edition": ["ce"],
            },
            "model_binding": {
                "model_id": "kokoro-base",
                "is_default": True,
                "priority": 100,
            },
            "lifecycle": {"idle_timeout": "15m"},
        },
    }
    import json
    (d / "descriptor.json").write_text(json.dumps(descriptor))
    return tmp_path


@pytest.fixture
def settings_off(monkeypatch):
    """Settings with RUNTIME_SERVICE_ENABLED=False (CE default)."""
    monkeypatch.setenv("RUNTIME_SERVICE_ENABLED", "false")
    from app.core.config import Settings
    return Settings()


@pytest.fixture
def settings_on(monkeypatch, tmp_registry_dir):
    """Settings with RUNTIME_SERVICE_ENABLED=True and a registry path."""
    monkeypatch.setenv("RUNTIME_SERVICE_ENABLED", "true")
    monkeypatch.setenv("RUNTIME_REGISTRY_PATH", str(tmp_registry_dir))
    from app.core.config import Settings
    return Settings()


# ---------------------------------------------------------------------------
# R3: flag-off path
# ---------------------------------------------------------------------------


def test_wire_runtime_services_returns_none_when_flag_off(settings_off) -> None:
    """When RUNTIME_SERVICE_ENABLED=False, the function returns None
    and the runtime subsystem is not constructed."""
    manager = wire_runtime_services(settings_off)
    assert manager is None


def test_wire_runtime_services_flag_off_does_not_attach_to_peakvox_runtime(
    settings_off,
) -> None:
    """When the flag is off, attach_runtime_manager is NOT called.
    The legacy in-process path is the only path."""
    from app.services.runtime import PeakVoxRuntime
    rt = PeakVoxRuntime()
    with patch.object(rt, "attach_runtime_manager") as mock_attach:
        wire_runtime_services(settings_off)
        mock_attach.assert_not_called()


# ---------------------------------------------------------------------------
# R3: flag-on path
# ---------------------------------------------------------------------------


def test_wire_runtime_services_returns_manager_when_flag_on(
    settings_on,
) -> None:
    """When the flag is on, the function returns a RuntimeManager."""
    manager = wire_runtime_services(settings_on)
    assert manager is not None
    assert isinstance(manager, RuntimeManager)


def test_wire_runtime_services_constructs_registry_with_kokoro_descriptor(
    settings_on,
) -> None:
    """The registry is loaded from the configured path and includes
    the Kokoro descriptor."""
    manager = wire_runtime_services(settings_on)
    assert manager is not None
    assert "kokoro-82m" in manager.registry


def test_wire_runtime_services_attaches_manager_to_peakvox_runtime(
    settings_on,
) -> None:
    """The manager is attached to the PeakVoxRuntime singleton."""
    from app.services import runtime as runtime_module
    # Reset the singleton's manager for a clean assertion.
    runtime_module.runtime._runtime_manager = None
    wire_runtime_services(settings_on)
    assert runtime_module.runtime._runtime_manager is not None
    # Reset for subsequent tests.
    runtime_module.runtime._runtime_manager = None


# ---------------------------------------------------------------------------
# R6: lazy startup
# ---------------------------------------------------------------------------


def test_wire_runtime_services_does_not_start_any_runtime_container(
    settings_on,
) -> None:
    """At backend startup, NO runtime container is started. The
    instance cache is empty. The first resolve() call activates
    the runtime lazily (R6)."""
    # Patch the driver so we can assert start_runtime is never called.
    with patch(
        "app.services.drivers.docker_runtime_driver.DockerRuntimeDriver"
    ) as mock_driver_cls:
        mock_driver = MagicMock()
        mock_driver_cls.return_value = mock_driver
        manager = wire_runtime_services(settings_on)
        assert manager is not None
        mock_driver.start_runtime.assert_not_called()
        mock_driver.install_runtime.assert_not_called()


def test_wire_runtime_services_manager_instance_cache_is_empty(
    settings_on,
) -> None:
    """The manager's instance cache is empty at startup (R6)."""
    with patch(
        "app.services.drivers.docker_runtime_driver.DockerRuntimeDriver"
    ):
        manager = wire_runtime_services(settings_on)
        assert manager is not None
        assert len(manager.list_cached_instances()) == 0


# ---------------------------------------------------------------------------
# Provider-agnosticism
# ---------------------------------------------------------------------------


def test_wire_runtime_services_does_not_reference_kokoro(settings_on) -> None:
    """The wiring module must be provider-agnostic. The CODE must
    not branch on provider names; the registry is loaded from
    disk and the descriptors are opaque to it. (Provider names may
    appear in the module's docstring as illustrative examples;
    what matters is the executable code path.)"""
    import ast
    import inspect
    from app.services import runtime_wiring
    source = inspect.getsource(runtime_wiring)
    tree = ast.parse(source)
    # Walk only the executable statements; skip the docstring
    # (which is ast.Expr(ast.Constant(str)) at module level).
    module_body = tree.body
    string_literals = set()
    for stmt in module_body[1:]:  # skip the module docstring
        for node in ast.walk(stmt):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                string_literals.add(node.value)
            if isinstance(node, ast.Name):
                string_literals.add(node.id)
            if isinstance(node, ast.Attribute):
                string_literals.add(node.attr)
    forbidden_substrings = ["kokoro", "xtts", "openvoice", "fish_audio", "omnivoice"]
    leaks = [tok for tok in forbidden_substrings if any(tok in s.lower() for s in string_literals)]
    assert not leaks, (
        f"runtime_wiring must be provider-agnostic; "
        f"these provider names leaked into code identifiers/literals: {leaks}"
    )

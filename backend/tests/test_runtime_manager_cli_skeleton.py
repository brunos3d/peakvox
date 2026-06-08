"""TDD: RuntimeOperator CLI skeleton (Phase 2D.4).

The CLI skeleton (``scripts/runtime_manager.py``) is the
programmatic entry point for the four CE operations. It is
NOT a real CLI (argparse / Click); it is a Python class
that exposes the operations as methods. The actual CLI is
built on top of this in a later phase.

These tests verify:

- RuntimeOperator.from_settings() loads the registry from
  ``Settings.RUNTIME_REGISTRY_PATH``.
- The four CE operations work end-to-end against a fake
  driver.
- list_runtimes() and list_installed_runtimes() reflect
  the cached state.
- resolve() returns the cached ACTIVE instance when the
  runtime is installed + started.
- The operator does NOT import Docker / K8s / Podman.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List

# Add the repo root to sys.path so ``scripts.runtime_manager``
# is importable.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest

from app.services.runtime_instance import (
    HealthState,
    ImageIdentity,
    RuntimeInstance,
    RuntimeState,
)
from app.services.runtime_driver import RuntimeDriver
from app.services.runtime_types import HealthReport, Liveness, Metrics, Readiness
from datetime import datetime


class _FakeDriver(RuntimeDriver):
    """A driver that records calls and returns Active instances."""

    def __init__(self) -> None:
        self.instances: dict[str, RuntimeInstance] = {}
        self.install_calls: List[str] = []
        self.start_calls: List[str] = []
        self.stop_calls: List[str] = []
        self.update_calls: List[str] = []
        self.remove_calls: List[str] = []

    async def install_runtime(self, runtime_id, descriptor):
        self.install_calls.append(runtime_id)
        inst = RuntimeInstance(
            runtime_id=runtime_id, state=RuntimeState.INSTALLED,
            host="localhost", port=descriptor.spec.service.port,
            image_identity=ImageIdentity(
                repository=descriptor.spec.image.repository,
                tag=descriptor.spec.image.tag, digest=descriptor.spec.image.digest,
            ),
            started_at=None, last_health_at=None, health_state=HealthState.UNKNOWN,
        )
        self.instances[runtime_id] = inst
        return inst

    async def start_runtime(self, runtime_id):
        self.start_calls.append(runtime_id)
        cur = self.instances.get(runtime_id) or _active(runtime_id)
        inst = RuntimeInstance(
            runtime_id=cur.runtime_id, state=RuntimeState.ACTIVE,
            host=cur.host, port=cur.port, image_identity=cur.image_identity,
            started_at=datetime(2026, 6, 7, 0, 0, 0),
            last_health_at=datetime(2026, 6, 7, 0, 0, 0),
            health_state=HealthState.READY,
        )
        self.instances[runtime_id] = inst
        return inst

    async def update_runtime(self, runtime_id, descriptor):
        self.update_calls.append(runtime_id)
        return self.instances.get(runtime_id) or _active(runtime_id)

    async def remove_runtime(self, runtime_id):
        self.remove_calls.append(runtime_id)
        self.instances.pop(runtime_id, None)

    async def stop_runtime(self, runtime_id):
        self.stop_calls.append(runtime_id)
        if runtime_id in self.instances:
            cur = self.instances[runtime_id]
            self.instances[runtime_id] = RuntimeInstance(
                runtime_id=cur.runtime_id, state=RuntimeState.STOPPED,
                host=cur.host, port=cur.port, image_identity=cur.image_identity,
                started_at=cur.started_at, last_health_at=cur.last_health_at,
                health_state=HealthState.UNKNOWN,
            )

    async def restart_runtime(self, runtime_id):
        return await self.start_runtime(runtime_id)

    async def runtime_status(self, runtime_id):
        return self.instances.get(runtime_id) or _active(runtime_id)

    async def runtime_logs(self, runtime_id, since=None):
        async def _empty():
            if False:
                yield ""
        return _empty()

    async def runtime_health(self, runtime_id):
        return HealthReport(
            runtime_id=runtime_id, liveness=Liveness.ALIVE,
            readiness=Readiness.READY, last_error=None,
            checked_at=datetime(2026, 6, 7, 0, 0, 0),
        )

    async def runtime_metrics(self, runtime_id):
        return Metrics()


def _active(runtime_id: str) -> RuntimeInstance:
    return RuntimeInstance(
        runtime_id=runtime_id, state=RuntimeState.ACTIVE,
        host="localhost", port=8000,
        image_identity=ImageIdentity(
            repository="peakvox/kokoro-runtime", tag="0.1.0", digest=None,
        ),
        started_at=datetime(2026, 6, 7, 0, 0, 0),
        last_health_at=datetime(2026, 6, 7, 0, 0, 0),
        health_state=HealthState.READY,
    )


def test_runtime_operator_loads_registry_from_settings() -> None:
    """RuntimeOperator.from_settings() loads the registry from
    Settings.RUNTIME_REGISTRY_PATH (the in-repo path)."""
    from scripts.runtime_manager import RuntimeOperator

    driver = _FakeDriver()
    op = RuntimeOperator.from_settings(driver=driver)
    # The Kokoro descriptor is in the registry.
    inst_list = op.list_runtimes()
    assert inst_list == []  # nothing installed yet
    # The registry has the descriptor.
    res = op.resolve("kokoro-base")
    # resolve() returns None when the runtime is not installed.
    assert res is None


def test_runtime_operator_install_start_stop_remove() -> None:
    """The four CE operations work end-to-end."""
    from scripts.runtime_manager import RuntimeOperator

    driver = _FakeDriver()
    op = RuntimeOperator.from_settings(driver=driver)

    # Install.
    inst = op.install("kokoro-82m")
    assert inst.runtime_id == "kokoro-82m"
    assert inst.state == RuntimeState.INSTALLED
    assert "kokoro-82m" in op.list_installed_runtimes()

    # Start.
    inst = op.start("kokoro-82m")
    assert inst.state == RuntimeState.ACTIVE

    # Resolve.
    res = op.resolve("kokoro-base")
    assert res is not None
    assert res.descriptor.metadata.id == "kokoro-82m"
    assert res.instance.state == RuntimeState.ACTIVE
    assert res.endpoint == "http://localhost:8000"

    # Stop.
    op.stop("kokoro-82m")
    inst = op.status("kokoro-82m")
    assert inst.state == RuntimeState.STOPPED

    # Remove.
    op.remove("kokoro-82m")
    assert "kokoro-82m" not in op.list_installed_runtimes()
    # resolve() returns None after remove.
    assert op.resolve("kokoro-base") is None


def test_runtime_operator_does_not_import_docker() -> None:
    """Architectural invariant: the CLI skeleton depends on
    the RuntimeManager (substrate-neutral), not on the
    Docker SDK. The lint script enforces this; the test
    here is a runtime assertion at module load."""
    import re
    text = open(
        __import__("scripts.runtime_manager", fromlist=["__file__"]).__file__
    ).read()
    text_clean = re.sub(r'\"{3}.*?\"{3}', "", text, flags=re.DOTALL)
    assert not re.search(r"^import docker\b", text_clean, flags=re.MULTILINE)
    assert not re.search(r"^from docker\b", text_clean, flags=re.MULTILINE)


def test_runtime_operator_works_against_in_repo_registry() -> None:
    """The CLI skeleton can be constructed with the in-repo
    RUNTIME_REGISTRY_PATH; the Kokoro descriptor is found."""
    from scripts.runtime_manager import RuntimeOperator

    driver = _FakeDriver()
    op = RuntimeOperator.from_settings(driver=driver)
    op.install("kokoro-82m")
    op.start("kokoro-82m")
    res = op.resolve("kokoro-base")
    assert res is not None
    assert res.descriptor.metadata.id == "kokoro-82m"
    # The descriptor binds to the kokoro-base model.
    assert res.descriptor.spec.model_binding.model_id == "kokoro-base"
    assert res.descriptor.spec.model_binding.is_default is True

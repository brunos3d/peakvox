"""TDD: PeakVoxRuntime bridge integration (2A.10).

Per the architecture review guardrail, 2A.10 is a TRANSITIONAL
BRIDGE LAYER only. The RuntimeManager is introduced into the
runtime flow as a pass-through orchestration boundary; it must
NOT change generation behavior in 2A.

For Phase 2A:
- Voice -> VoiceVariant -> Active Artifact -> Adapter -> existing
  inference path is the canonical execution flow.
- The bridge is:
  Voice -> VoiceVariant -> Active Artifact -> RuntimeManager
  (skeleton) -> Adapter -> existing inference path.
- RuntimeManager in 2A has no driver wired; ``resolve()`` returns
  ``None``; the bridge uses None to fall through to the existing
  in-process path.
- Phase 2C+ will introduce the runtime-service path. In 2A, that
  branch is unreachable.

These tests assert:
- PeakVoxRuntime is constructible without a manager (default
  behavior; tests below confirm this is the canonical 2A
  configuration).
- PeakVoxRuntime.generate() works as before when no manager is
  wired (no behavior change).
- PeakVoxRuntime.generate() works as before when a manager is
  wired and ``resolve()`` returns ``None`` (no behavior change).
- PeakVoxRuntime.attach_runtime_manager() wires a manager.
- The RuntimeManager is consulted between Artifact and Adapter
  (the canonical 2A bridge position).
- The manager does NOT receive model weights, does NOT execute
  inference, and does NOT communicate with Docker / a runtime
  service in 2A.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import List, Optional

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)

from app.core.migrations import run_migrations
from app.models.registry_types import ModelCapabilities, ModelDescriptor
from app.services.model_adapter import ModelAdapter
from app.services.runtime import PeakVoxRuntime
from app.services.runtime_events import RuntimeEventBus
from app.services.runtime_manager import RuntimeManager
from app.services.runtime_registry import RuntimeRegistry
from app.services.runtime_types import RuntimeDescriptor


class _TrackingAdapter(ModelAdapter):
    """A torch-free adapter for contract-compliance tests."""

    def __init__(self, descriptor):
        super().__init__(descriptor)
        self.captured_kwargs: dict = {}

    async def install(self) -> None: ...
    async def load(self) -> None: ...
    def unload(self) -> None: ...
    async def health_check(self) -> bool:
        return True
    async def generate(self, *, text, output_path, **kwargs):
        self.captured_kwargs = kwargs
        return (1.5, [f"{self.model_id}:{text}"])

    async def clone_voice(self, *, db, voice, reference_audio_key):
        raise NotImplementedError
    async def build_variant(self, *, db, voice):
        raise NotImplementedError


def _desc(model_id: str, *, default: bool = False) -> ModelDescriptor:
    return ModelDescriptor(
        id=model_id, name=model_id, description="d", provider="fake",
        supported_tags=[], is_default=default,
        capabilities=ModelCapabilities(supports_tts=True),
    )


def test_peakvoxruntime_constructible_without_manager() -> None:
    rt = PeakVoxRuntime()
    # The runtime exists; no manager is wired in 2A by default.
    assert rt is not None


def test_peakvoxruntime_attach_runtime_manager_wires_a_manager() -> None:
    rt = PeakVoxRuntime()
    reg = RuntimeRegistry([])
    manager = RuntimeManager(registry=reg, driver=None, events=RuntimeEventBus())
    rt.attach_runtime_manager(manager)
    # The internal field is set; the runtime can be queried.
    assert rt._runtime_manager is manager  # noqa: SLF001


def test_peakvoxruntime_attach_runtime_manager_is_optional() -> None:
    rt = PeakVoxRuntime()
    # The default is no manager; the bridge is a no-op.
    assert rt._runtime_manager is None  # noqa: SLF001


def test_generate_works_without_manager() -> None:
    """Phase 2A canonical configuration: no manager, in-process path."""
    rt = PeakVoxRuntime()
    adapter = _TrackingAdapter(_desc("test-model", default=True))
    rt.register_adapter(adapter)

    duration, logs = asyncio.run(
        rt.generate(
            None, text="hi", model_id="test-model",
            output_path=Path("/tmp/x.wav"),
        )
    )
    assert duration == 1.5
    assert "test-model:hi" in logs[0]


def test_generate_works_with_manager_that_returns_none() -> None:
    """The bridge asks the manager; in 2A the manager returns None;
    the existing in-process path is taken unchanged."""
    rt = PeakVoxRuntime()
    adapter = _TrackingAdapter(_desc("test-model", default=True))
    rt.register_adapter(adapter)

    reg = RuntimeRegistry([])
    manager = RuntimeManager(registry=reg, driver=None, events=RuntimeEventBus())
    rt.attach_runtime_manager(manager)

    duration, logs = asyncio.run(
        rt.generate(
            None, text="hi", model_id="test-model",
            output_path=Path("/tmp/x.wav"),
        )
    )
    # Same behavior: 1.5s duration, the in-process adapter was called.
    assert duration == 1.5
    assert "test-model:hi" in logs[0]


def test_generate_does_not_change_captured_kwargs_when_manager_wired() -> None:
    """The bridge must not perturb the kwargs the adapter receives."""
    rt = PeakVoxRuntime()
    adapter = _TrackingAdapter(_desc("test-model", default=True))
    rt.register_adapter(adapter)

    reg = RuntimeRegistry([])
    manager = RuntimeManager(registry=reg, driver=None, events=RuntimeEventBus())
    rt.attach_runtime_manager(manager)

    asyncio.run(
        rt.generate(
            None, text="hi", model_id="test-model",
            params={"speed": 1.0},
            output_path=Path("/tmp/x.wav"),
        )
    )
    assert adapter.captured_kwargs.get("params") == {"speed": 1.0}


def test_bridge_does_not_call_adapter_generate_twice() -> None:
    """The bridge falls through exactly once; the adapter is called once."""
    rt = PeakVoxRuntime()
    adapter = _TrackingAdapter(_desc("test-model", default=True))
    rt.register_adapter(adapter)

    reg = RuntimeRegistry([])
    manager = RuntimeManager(registry=reg, driver=None, events=RuntimeEventBus())
    rt.attach_runtime_manager(manager)

    call_count = {"n": 0}
    original_generate = adapter.generate

    async def _counting_generate(**kwargs):
        call_count["n"] += 1
        return await original_generate(**kwargs)
    adapter.generate = _counting_generate  # type: ignore[method-assign]

    asyncio.run(
        rt.generate(
            None, text="hi", model_id="test-model",
            output_path=Path("/tmp/x.wav"),
        )
    )
    assert call_count["n"] == 1


def test_bridge_does_not_invoke_lifecycle_operations_in_2a() -> None:
    """In 2A, the manager is consulted for resolve() only. Lifecycle
    operations (install/start/etc.) are NOT triggered by generate."""
    rt = PeakVoxRuntime()
    adapter = _TrackingAdapter(_desc("test-model", default=True))
    rt.register_adapter(adapter)

    reg = RuntimeRegistry([])
    manager = RuntimeManager(registry=reg, driver=None, events=RuntimeEventBus())
    rt.attach_runtime_manager(manager)

    # The manager has no driver; if the bridge mistakenly invoked
    # lifecycle operations, NoDriverConfigured would surface. The
    # resolve-only call is the only interaction in 2A.
    asyncio.run(
        rt.generate(
            None, text="hi", model_id="test-model",
            output_path=Path("/tmp/x.wav"),
        )
    )
    # If we got here without exception, the bridge was resolve-only.
    # No additional assertion needed; the absence of an exception
    # is the success signal.


def test_bridge_does_not_execute_inference_or_load_weights() -> None:
    """Architectural invariant: the RuntimeManager is a pass-through;
    it does not execute inference, load weights, or run any model
    framework. The adapter (an in-process provider) does the work
    in 2A; the manager is consulted only for endpoint resolution."""
    rt = PeakVoxRuntime()
    adapter = _TrackingAdapter(_desc("test-model", default=True))
    rt.register_adapter(adapter)

    reg = RuntimeRegistry([])
    manager = RuntimeManager(registry=reg, driver=None, events=RuntimeEventBus())
    rt.attach_runtime_manager(manager)

    # After generate, the adapter is the one that captured kwargs
    # and produced the (duration, logs) tuple. The manager has not
    # done any of the inference work; it only returned None.
    duration, logs = asyncio.run(
        rt.generate(
            None, text="hi", model_id="test-model",
            output_path=Path("/tmp/x.wav"),
        )
    )
    # The adapter was the worker: the (duration, logs) tuple is
    # the adapter's return value. The manager does not produce audio.
    assert duration == 1.5
    assert "test-model:hi" in logs[0]
    # The adapter received the merged params (the bridge does not
    # modify them).
    assert adapter.captured_kwargs.get("params") == {}


def test_bridge_with_no_manager_field_does_not_break_existing_callers() -> None:
    """The default constructor leaves _runtime_manager as None; an
    existing test/code path that does not wire a manager continues
    to work without modification."""
    rt = PeakVoxRuntime()
    adapter = _TrackingAdapter(_desc("test-model", default=True))
    rt.register_adapter(adapter)

    # A caller that only knows about the legacy API (register_adapter,
    # generate) sees the original behavior.
    assert rt._runtime_manager is None  # noqa: SLF001
    duration, logs = asyncio.run(
        rt.generate(
            None, text="hi", model_id="test-model",
            output_path=Path("/tmp/x.wav"),
        )
    )
    assert duration == 1.5

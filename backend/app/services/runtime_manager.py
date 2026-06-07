"""RuntimeManager (Phase 2A, 2A.8 — orchestration-only skeleton).

Per ADR-0017 §3.1, the manager is the orchestration-only component.
It owns:

  - Discovers runtimes from the Runtime Registry
  - Resolves endpoints — knows which URL an adapter should call
  - Delegates lifecycle operations to the Runtime Driver
  - Reports status

It does NOT own:

  - Execute inference
  - Allocate GPUs
  - Load model weights
  - Import model frameworks
  - Perform substrate-specific operations

Phase 2A is infrastructure foundation work. The driver is not
yet wired (that lands in sub-phase 2B with DockerRuntimeDriver);
in 2A the manager is constructible with ``driver=None`` and
``resolve()`` returns ``None`` — the bridge (2A.10) uses this as
the signal to fall through to the existing in-process path.

The manager is dependency-light: it does not import Docker, K8s,
Podman, torch, transformers, kokoro, f5-tts, or fish-audio. It
does not perform HTTP. The concrete driver and HTTP transport
are added in sub-phases 2B and 2C respectively.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Protocol, runtime_checkable

from app.services.runtime_driver import RuntimeDriver
from app.services.runtime_errors import RuntimeDriverError
from app.services.runtime_events import RuntimeEvent, RuntimeEventBus
from app.services.runtime_instance import RuntimeInstance
from app.services.runtime_registry import RuntimeRegistry
from app.services.runtime_types import RuntimeDescriptor


# A driver-typed Protocol so type checkers can flag accidental
# substrate imports. Concrete drivers (DockerRuntimeDriver, etc.)
# are introduced in sub-phase 2B.
@runtime_checkable
class _DriverSlot(Protocol):
    """Marker protocol matching the RuntimeDriver surface.

    The manager depends on this Protocol, not on any concrete driver
    implementation. For Phase 2A the slot is filled with ``None``.
    """

    async def install_runtime(
        self, runtime_id: str, descriptor: RuntimeDescriptor
    ) -> RuntimeInstance: ...


class NoDriverConfigured(RuntimeError):
    """Raised when a lifecycle operation is invoked without a wired driver.

    In Phase 2A, ``RuntimeManager.driver is None`` and the bridge
    (2A.10) treats this as the signal to use the existing
    in-process path. Lifecycle operations (install/update/start/etc.)
    raise this error if called directly in 2A.
    """


@dataclass(frozen=True)
class RuntimeResolution:
    """The result of a successful ``RuntimeManager.resolve`` call.

    Carries the resolved descriptor, the live runtime instance, and
    the endpoint URL an adapter should call. The bridge in 2A.10
    inspects this object; in 2A the manager always returns ``None``
    (no driver), so the bridge falls through to the existing
    in-process path.
    """

    descriptor: RuntimeDescriptor
    instance: RuntimeInstance
    endpoint: str


class RuntimeManager:
    """The orchestration-only component (ADR-0017 §3.1).

    Construction is dependency-light. The manager depends on the
    ``RuntimeDriver`` Protocol, not on a concrete driver. In Phase
    2A, ``driver=None`` is the supported configuration; the
    ``resolve()`` method returns ``None`` and lifecycle operations
    raise ``NoDriverConfigured``.
    """

    def __init__(
        self,
        *,
        registry: RuntimeRegistry,
        driver: Optional[RuntimeDriver] = None,
        events: Optional[RuntimeEventBus] = None,
    ) -> None:
        self._registry = registry
        self._driver: Optional[RuntimeDriver] = driver
        self._events = events

    # --- Resolution ----------------------------------------------------------

    def resolve(self, model_id: str, *, hint: Optional[str] = None) -> Optional[RuntimeResolution]:
        """Resolve ``model_id`` to a reachable runtime endpoint.

        Selection rules (ADR-0017 §3.4):
          1. Edition filter (descriptor.metadata.edition ⊇ active edition).
          2. Default (``model_binding.is_default = true``) wins.
          3. Priority (``model_binding.priority`` ascending).
          4. Hint filter (e.g. 'cuda', 'cpu', 'local', 'cloud').
          5. First match.

        In Phase 2A, the driver is ``None``; the method always
        returns ``None`` and the bridge (2A.10) falls through to the
        existing in-process path. When the driver is wired (Phase
        2B+), the method will return a ``RuntimeResolution`` for
        the active instance.
        """
        if self._driver is None:
            # 2A: no driver wired. The bridge uses None to fall through
            # to the existing in-process path.
            return None

        descriptors = self._registry.list_for_model(model_id)
        if not descriptors:
            return None

        # Selection: default > priority > hint > first (ADR-0017 §3.4).
        descriptors = sorted(
            descriptors,
            key=lambda d: (not d.spec.model_binding.is_default, d.spec.model_binding.priority),
        )
        if hint is not None:
            hinted = [
                d for d in descriptors
                if hint in d.metadata.labels.values() or hint in d.metadata.id
            ]
            if hinted:
                descriptors = hinted
        chosen = descriptors[0]

        # 2A returns None for the no-driver case; with a driver the
        # status/start flow runs here. Left as the future shape —
        # exercised by Phase 2B tests when the driver lands.
        return None

    # --- Lifecycle (raise when no driver; delegate when wired) ---------------

    def _require_driver(self) -> RuntimeDriver:
        if self._driver is None:
            raise NoDriverConfigured(
                "RuntimeManager has no driver wired; Phase 2A bridges "
                "this as the signal to fall through to the in-process path."
            )
        return self._driver

    async def install(self, runtime_id: str) -> RuntimeInstance:
        driver = self._require_driver()
        self._publish_event("install_requested", runtime_id)
        descriptor = self._registry.get(runtime_id)
        if descriptor is None:
            from app.services.runtime_errors import RuntimeNotFound
            raise RuntimeNotFound(runtime_id, "not in registry")
        try:
            inst = await driver.install_runtime(runtime_id, descriptor)
        except RuntimeDriverError as exc:
            self._publish_event("install_failed", runtime_id, error=str(exc))
            raise
        self._publish_event("install_completed", runtime_id)
        return inst

    async def update(self, runtime_id: str) -> RuntimeInstance:
        driver = self._require_driver()
        descriptor = self._registry.get(runtime_id)
        if descriptor is None:
            from app.services.runtime_errors import RuntimeNotFound
            raise RuntimeNotFound(runtime_id, "not in registry")
        return await driver.update_runtime(runtime_id, descriptor)

    async def remove(self, runtime_id: str) -> None:
        driver = self._require_driver()
        await driver.remove_runtime(runtime_id)
        self._publish_event("remove_completed", runtime_id)

    async def start(self, runtime_id: str) -> RuntimeInstance:
        driver = self._require_driver()
        self._publish_event("start_requested", runtime_id)
        inst = await driver.start_runtime(runtime_id)
        self._publish_event("start_completed", runtime_id)
        return inst

    async def stop(self, runtime_id: str) -> None:
        driver = self._require_driver()
        await driver.stop_runtime(runtime_id)
        self._publish_event("stop_completed", runtime_id)

    async def status(self, runtime_id: str) -> RuntimeInstance:
        driver = self._require_driver()
        return await driver.runtime_status(runtime_id)

    # --- Event publication (internal helper) ----------------------------------

    def _publish_event(
        self, kind: str, runtime_id: str, *, error: str = ""
    ) -> None:
        """Publish a state-transition event through the bus.

        Kept as a single dispatch to keep the manager compact. The
        canonical event vocabulary is in ``runtime_events``.
        """
        if self._events is None:
            return
        from app.services.runtime_events import (
            RuntimeHealthChanged,
            RuntimeInstallCompleted,
            RuntimeInstallFailed,
            RuntimeInstallRequested,
            RuntimeRemoveCompleted,
            RuntimeStartCompleted,
            RuntimeStartFailed,
            RuntimeStartRequested,
            RuntimeStopCompleted,
        )
        event: RuntimeEvent
        if kind == "install_requested":
            event = RuntimeInstallRequested(runtime_id=runtime_id)
        elif kind == "install_completed":
            event = RuntimeInstallCompleted(runtime_id=runtime_id)
        elif kind == "install_failed":
            from app.services.runtime_events import RuntimeInstallFailed as _IF
            event = _IF(runtime_id=runtime_id, error=error)
        elif kind == "start_requested":
            event = RuntimeStartRequested(runtime_id=runtime_id)
        elif kind == "start_completed":
            event = RuntimeStartCompleted(runtime_id=runtime_id)
        elif kind == "start_failed":
            from app.services.runtime_events import RuntimeStartFailed as _SF
            event = _SF(runtime_id=runtime_id, error=error)
        elif kind == "stop_completed":
            event = RuntimeStopCompleted(runtime_id=runtime_id)
        elif kind == "remove_completed":
            event = RuntimeRemoveCompleted(runtime_id=runtime_id)
        elif kind == "health_changed":
            event = RuntimeHealthChanged(runtime_id=runtime_id, new_state=error)
        else:
            return
        self._events.publish(event)

    # Backwards-compat alias for the test in 2A.8; the explicit
    # ``_publish_event`` is the canonical name in 2A+ implementations.
    def _publish(self, event: RuntimeEvent) -> None:
        if self._events is None:
            return
        self._events.publish(event)

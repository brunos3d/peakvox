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

import asyncio
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import List, Optional, Protocol, runtime_checkable
from uuid import uuid4

from app.services.runtime_driver import RuntimeDriver
from app.services.runtime_errors import RuntimeDriverError
from app.services.runtime_events import RuntimeEvent, RuntimeEventBus
from app.services.runtime_instance import HealthState, ImageIdentity, RuntimeInstance, RuntimeState
from app.services.runtime_operation import (
    RuntimeOperation,
    RuntimeOperationConflict,
    RuntimeOperationNotFound,
    RuntimeOperationStatus,
    RuntimeOperationType,
)
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
        # Phase 2D: the manager caches the operational state of
        # every runtime it has installed. The cache is in-memory
        # only; persistence is OPEN_DECISIONS Decision 12
        # (future ADR; non-blocking). The cache is the manager's
        # only ownership of operational state — it never
        # references Voice / VoiceVariant / VoiceVariantArtifact
        # (per the Runtime Activation Audit).
        self._instance_cache: dict[str, RuntimeInstance] = {}
        # Task 15: operation state is backend-owned and globally visible.
        self._operations: dict[str, RuntimeOperation] = {}
        self._operation_tasks: dict[str, asyncio.Task[None]] = {}

    # --- Cache (2D.1-2D.3) -----------------------------------------------------

    @property
    def registry(self) -> RuntimeRegistry:
        """Read-only access to the runtime registry (ADR-0017 §2.3)."""
        return self._registry

    def get_cached_instance(self, runtime_id: str) -> Optional[RuntimeInstance]:
        """Return the cached ``RuntimeInstance`` for ``runtime_id``,
        or ``None`` if the runtime is not in the cache (i.e. not        yet installed)."""
        return self._instance_cache.get(runtime_id)

    def list_cached_instances(self) -> List[RuntimeInstance]:
        """All cached ``RuntimeInstance`` objects (operational
        state only; no domain objects)."""
        return list(self._instance_cache.values())

    async def resync_from_substrate(self) -> int:
        """Re-populate the instance cache from the substrate (e.g. Docker).

        Called once at startup to recover operational state from containers
        that survived a backend restart. The manager's instance cache is
        in-memory only; without this call, ``resolve()`` would return None
        for every runtime until each is explicitly started through the
        manager's lifecycle methods. Returns the count of recovered instances.
        """
        if self._driver is None:
            return 0
        recovered = 0
        for desc in self._registry.list():
            runtime_id = desc.metadata.id
            if runtime_id in self._instance_cache:
                continue
            try:
                inst = await self._driver.runtime_status(runtime_id)
                if inst.state == RuntimeState.ACTIVE:
                    self._instance_cache[runtime_id] = inst
                    recovered += 1
            except Exception:  # noqa: BLE001
                pass
        return recovered

    def get_runtime_operation(self, runtime_id: str) -> Optional[RuntimeOperation]:
        """Return the latest operation for a runtime."""
        return self._operations.get(runtime_id)

    def list_runtime_operations(self, *, active_only: bool = True) -> List[RuntimeOperation]:
        """List runtime operations.

        When ``active_only`` is true, return only pending/running operations.
        """
        items = list(self._operations.values())
        if active_only:
            items = [op for op in items if op.status in ("pending", "running")]
        return sorted(items, key=lambda op: op.updated_at, reverse=True)

    async def cancel_runtime_operation(self, runtime_id: str, operation_id: str) -> RuntimeOperation:
        """Cancel a running operation if it is cancellable."""
        op = self._operations.get(runtime_id)
        if op is None or op.id != operation_id:
            raise RuntimeOperationNotFound(
                f"operation {operation_id} for runtime {runtime_id} not found"
            )
        if op.status not in ("pending", "running"):
            return op
        if not op.cancellable:
            return self._set_operation(
                runtime_id,
                status="failed",
                message="Operation cannot be cancelled",
                error="operation_not_cancellable",
            )
        task = self._operation_tasks.get(runtime_id)
        if task is not None and not task.done():
            task.cancel()
        return self._set_operation(
            runtime_id,
            status="cancelled",
            progress=100,
            message="Operation cancelled",
            error="operation_cancelled",
        )

    # --- Resolution ----------------------------------------------------------

    def resolve(self, model_id: str, *, hint: Optional[str] = None) -> Optional[RuntimeResolution]:
        """Resolve ``model_id`` to a reachable runtime endpoint.

        Selection rules (ADR-0017 §3.4):
          1. Edition filter (descriptor.metadata.edition ⊇ active edition).
          2. Default (``model_binding.is_default = true``) wins.
          3. Priority (``model_binding.priority`` ascending).
          4. Hint filter (e.g. 'cuda', 'cpu', 'local', 'cloud').
          5. First match.

        Phase 2D: the manager reads from its instance cache. The
        resolution is returned ONLY when the chosen descriptor
        has a cached ``RuntimeInstance`` whose state is
        ``ACTIVE``. When the runtime is not in the cache (not
        yet installed) or its state is not ACTIVE, the method
        returns ``None`` and the bridge (2A.10) falls through to
        the in-process path.

        Phase 2A: when no driver is wired, the method returns
        ``None`` and the bridge falls through to the in-process
        path. This behavior is preserved.
        """
        if self._driver is None:
            # 2A behavior: no driver wired.
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

        # The resolution is returned ONLY when the cache holds an
        # ACTIVE instance for the chosen descriptor. The cache
        # is populated by ``install()`` + ``start()`` (or by an
        # external operator via the manager's lifecycle methods).
        # When the cache is empty or the instance is not ACTIVE,
        # the bridge falls through to the in-process path.
        cached = self._instance_cache.get(chosen.metadata.id)
        if cached is None or cached.state != RuntimeState.ACTIVE:
            return None
        endpoint = f"http://{cached.host}:{cached.port}"
        return RuntimeResolution(
            descriptor=chosen,
            instance=cached,
            endpoint=endpoint,
        )

    # --- Lifecycle (raise when no driver; delegate when wired) ---------------

    def _require_driver(self) -> RuntimeDriver:
        if self._driver is None:
            raise NoDriverConfigured(
                "RuntimeManager has no driver wired; Phase 2A bridges "
                "this as the signal to fall through to the in-process path."
            )
        return self._driver

    def _utcnow(self) -> datetime:
        return datetime.now(timezone.utc)

    def _set_operation(
        self,
        runtime_id: str,
        *,
        status: Optional[RuntimeOperationStatus] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        error: Optional[str] = None,
    ) -> RuntimeOperation:
        op = self._operations[runtime_id]
        next_progress = op.progress if progress is None else max(0, min(100, progress))
        next_message = op.message if message is None else message
        next_status = op.status if status is None else status
        op = replace(
            op,
            status=next_status,
            progress=next_progress,
            message=next_message,
            updated_at=self._utcnow(),
            error=error,
        )
        self._operations[runtime_id] = op
        return op

    def _begin_operation(
        self,
        runtime_id: str,
        op_type: RuntimeOperationType,
        *,
        cancellable: bool = True,
        initial_message: str,
    ) -> RuntimeOperation:
        existing = self._operations.get(runtime_id)
        if existing is not None and existing.status in ("pending", "running"):
            raise RuntimeOperationConflict(
                f"runtime {runtime_id} already has an active {existing.type} operation"
            )
        now = self._utcnow()
        op = RuntimeOperation(
            id=uuid4().hex,
            runtime_id=runtime_id,
            type=op_type,
            status="running",
            progress=10,
            message=initial_message,
            started_at=now,
            updated_at=now,
            cancellable=cancellable,
            error=None,
        )
        self._operations[runtime_id] = op
        return op

    async def install(self, runtime_id: str) -> RuntimeInstance:
        driver = self._require_driver()
        self._publish_event("install_requested", runtime_id)
        descriptor = self._registry.get(runtime_id)
        if descriptor is None:
            from app.services.runtime_errors import RuntimeNotFound
            raise RuntimeNotFound(runtime_id, "not in registry")
        self._begin_operation(
            runtime_id,
            "install",
            initial_message="Installing runtime",
        )
        self._set_operation(runtime_id, progress=30, message="Pulling runtime image")
        try:
            inst = await driver.install_runtime(runtime_id, descriptor)
        except asyncio.CancelledError:
            self._set_operation(
                runtime_id,
                status="cancelled",
                progress=100,
                message="Install cancelled",
                error="operation_cancelled",
            )
            raise
        except RuntimeDriverError as exc:
            self._publish_event("install_failed", runtime_id, error=str(exc))
            self._set_operation(
                runtime_id,
                status="failed",
                progress=100,
                message="Install failed",
                error=str(exc),
            )
            raise
        # 2D.1: cache the installed instance.
        self._instance_cache[runtime_id] = inst
        self._set_operation(
            runtime_id,
            status="completed",
            progress=100,
            message="Install completed",
            error=None,
        )
        self._publish_event("install_completed", runtime_id)
        return inst

    async def update(self, runtime_id: str) -> RuntimeInstance:
        driver = self._require_driver()
        descriptor = self._registry.get(runtime_id)
        if descriptor is None:
            from app.services.runtime_errors import RuntimeNotFound
            raise RuntimeNotFound(runtime_id, "not in registry")
        self._begin_operation(
            runtime_id,
            "update",
            initial_message="Updating runtime",
        )
        self._set_operation(runtime_id, progress=40, message="Applying runtime update")
        try:
            inst = await driver.update_runtime(runtime_id, descriptor)
        except asyncio.CancelledError:
            self._set_operation(
                runtime_id,
                status="cancelled",
                progress=100,
                message="Update cancelled",
                error="operation_cancelled",
            )
            raise
        except RuntimeDriverError as exc:
            self._set_operation(
                runtime_id,
                status="failed",
                progress=100,
                message="Update failed",
                error=str(exc),
            )
            raise
        # 2D.3: refresh the cache.
        self._instance_cache[runtime_id] = inst
        self._set_operation(
            runtime_id,
            status="completed",
            progress=100,
            message="Update completed",
            error=None,
        )
        return inst

    async def remove(self, runtime_id: str) -> None:
        driver = self._require_driver()
        self._begin_operation(
            runtime_id,
            "remove",
            initial_message="Removing runtime",
        )
        self._set_operation(runtime_id, progress=50, message="Removing runtime resources")
        try:
            await driver.remove_runtime(runtime_id)
        except asyncio.CancelledError:
            self._set_operation(
                runtime_id,
                status="cancelled",
                progress=100,
                message="Remove cancelled",
                error="operation_cancelled",
            )
            raise
        except RuntimeDriverError as exc:
            self._set_operation(
                runtime_id,
                status="failed",
                progress=100,
                message="Remove failed",
                error=str(exc),
            )
            raise
        # 2D.3: clear the cache.
        self._instance_cache.pop(runtime_id, None)
        self._set_operation(
            runtime_id,
            status="completed",
            progress=100,
            message="Remove completed",
            error=None,
        )
        self._publish_event("remove_completed", runtime_id)

    async def start(self, runtime_id: str) -> RuntimeInstance:
        driver = self._require_driver()
        self._publish_event("start_requested", runtime_id)
        self._begin_operation(
            runtime_id,
            "start",
            initial_message="Starting runtime",
        )
        self._set_operation(runtime_id, progress=50, message="Booting runtime container")
        try:
            inst = await driver.start_runtime(runtime_id)
        except asyncio.CancelledError:
            self._set_operation(
                runtime_id,
                status="cancelled",
                progress=100,
                message="Start cancelled",
                error="operation_cancelled",
            )
            raise
        except RuntimeDriverError as exc:
            self._publish_event("start_failed", runtime_id, error=str(exc))
            self._set_operation(
                runtime_id,
                status="failed",
                progress=100,
                message="Start failed",
                error=str(exc),
            )
            raise
        # 2D.2: cache the started instance.
        self._instance_cache[runtime_id] = inst
        self._set_operation(
            runtime_id,
            status="completed",
            progress=100,
            message="Start completed",
            error=None,
        )
        self._publish_event("start_completed", runtime_id)
        return inst

    async def stop(self, runtime_id: str) -> None:
        driver = self._require_driver()
        self._begin_operation(
            runtime_id,
            "stop",
            initial_message="Stopping runtime",
        )
        self._set_operation(runtime_id, progress=60, message="Stopping runtime container")
        try:
            await driver.stop_runtime(runtime_id)
        except asyncio.CancelledError:
            self._set_operation(
                runtime_id,
                status="cancelled",
                progress=100,
                message="Stop cancelled",
                error="operation_cancelled",
            )
            raise
        except RuntimeDriverError as exc:
            self._set_operation(
                runtime_id,
                status="failed",
                progress=100,
                message="Stop failed",
                error=str(exc),
            )
            raise
        # 2D.2: refresh the cache to the stopped state.
        # The driver may return a None in 2A; the cache holds
        # the last-known instance unless remove() is called.
        if runtime_id in self._instance_cache:
            cur = self._instance_cache[runtime_id]
            self._instance_cache[runtime_id] = RuntimeInstance(
                runtime_id=cur.runtime_id,
                state=RuntimeState.STOPPED,
                host=cur.host,
                port=cur.port,
                image_identity=cur.image_identity,
                started_at=cur.started_at,
                last_health_at=cur.last_health_at,
                health_state=HealthState.UNKNOWN,
            )
        self._set_operation(
            runtime_id,
            status="completed",
            progress=100,
            message="Stop completed",
            error=None,
        )
        self._publish_event("stop_completed", runtime_id)

    async def status(self, runtime_id: str) -> RuntimeInstance:
        # 2D.2: status() reads from the cache when present. The
        # cache is the manager's view of the world; the driver is
        # only consulted via runtime_health when the bridge needs
        # to verify readiness. The bridge in 2A.10 is the only
        # consumer of the live health probe.
        if runtime_id in self._instance_cache:
            return self._instance_cache[runtime_id]
        driver = self._require_driver()
        return await driver.runtime_status(runtime_id)

    # --- Phase 3: idle reaping (R7) -----------------------------------------

    async def run_idle_reaper(self) -> int:
        """Auto-stop any Active runtime that has been idle too long (R7).

        For each ``Active`` instance in the cache, compute
        ``now - last_request_at``. If the elapsed time exceeds
        ``descriptor.spec.lifecycle.idle_timeout`` (in seconds),
        call ``stop_runtime`` and emit the ``runtime.idle.timeout``
        event. ``idle_timeout = "never"`` disables the reaper
        for that runtime (Cloud default).

        Returns the number of runtimes that were reaped.
        """
        from datetime import datetime, timezone
        from app.services.runtime_events import RuntimeIdleTimeout
        from app.services.runtime_types import parse_idle_timeout_to_seconds

        now = datetime.now(timezone.utc)
        reaped = 0
        for runtime_id, inst in list(self._instance_cache.items()):
            if inst.state != RuntimeState.ACTIVE:
                continue
            if inst.last_request_at is None:
                # Active but never touched (e.g. started manually
                # outside the manager). Skip; we don't know when
                # the user wants it stopped.
                continue
            descriptor = self._registry.get(runtime_id)
            if descriptor is None:
                continue
            timeout_seconds = parse_idle_timeout_to_seconds(
                descriptor.spec.lifecycle.idle_timeout
            )
            if timeout_seconds is None:
                # "never" — autoscaler owns lifecycle.
                continue
            elapsed = (now - inst.last_request_at).total_seconds()
            if elapsed < timeout_seconds:
                continue
            # Idle timeout exceeded. Auto-stop the container.
            try:
                await self.stop(runtime_id)
                if self._events is not None:
                    self._events.publish(
                        RuntimeIdleTimeout(
                            runtime_id=runtime_id,
                            idle_seconds=elapsed,
                        )
                    )
                reaped += 1
            except Exception:  # noqa: BLE001
                # Don't let one runtime's reaper failure block others.
                continue
        return reaped

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

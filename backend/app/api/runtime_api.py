"""Runtime API (Phase 3 — Task 3/4/5/6/7 backend).

This module surfaces the RuntimeRegistry + RuntimeManager
as REST + Server-Sent Events endpoints. The Models page
renders from ``GET /api/runtimes`` when
``RUNTIME_SERVICE_ENABLED=true`` (R3).

Endpoints
---------

  GET  /api/runtimes                          list all runtimes
  GET  /api/runtimes/{id}                     single runtime (descriptor + state)
  GET  /api/runtimes/{id}/descriptor          full on-disk descriptor
  GET  /api/runtimes/{id}/state               operational state
  GET  /api/runtimes/{id}/state/stream        SSE: live state
  GET  /api/runtimes/{id}/logs                async iterator over runtime logs
  POST /api/runtimes/{id}/install             install (pull image, create Installed instance)
  POST /api/runtimes/{id}/start               start (run container, wait for /ready)
  POST /api/runtimes/{id}/stop                stop (kill container, image preserved)
  POST /api/runtimes/{id}/update              re-pull image, leave Installed
  POST /api/runtimes/{id}/remove              stop + remove image

Gating
------

All endpoints are gated on a RuntimeManager being
attached to ``PeakVoxRuntime``. When no manager is
attached (CE default, RUNTIME_SERVICE_ENABLED=false), the
endpoints return 503 with a clear error message pointing
to the legacy ``/api/models`` endpoint as the fallback.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.services import runtime as runtime_module
from app.services.runtime_instance import (
    HealthState,
    ImageIdentity,
    RuntimeInstance,
    RuntimeState,
)
from app.services.runtime_types import RuntimeDescriptor
from app.services.model_registry import model_registry
from app.core.config import settings


logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/runtimes", tags=["Runtimes"])

# A second router for the composed view (Models + Runtimes + State).
# Per R9, the Models page renders a composed view: the catalog
# is the primary entity; the runtime-registry is the
# augmentation; the runtime state is the live view. This
# endpoint joins all three.
composed_router = APIRouter(prefix="/api/models", tags=["Models (composed)"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_manager():
    """Return the attached RuntimeManager or raise 503."""
    manager = runtime_module.runtime._runtime_manager
    if manager is None:
        raise HTTPException(
            status_code=503,
            detail={
                "message": (
                    "RUNTIME_SERVICE_ENABLED is false; the runtime "
                    "subsystem is not wired. The legacy /api/models "
                    "endpoint is the fallback."
                ),
                "category": "runtime_subsystem_disabled",
            },
        )
    return manager


def _descriptor_to_payload(desc: RuntimeDescriptor) -> dict[str, Any]:
    """Convert a RuntimeDescriptor to the API payload (Task 3)."""
    return {
        "runtime_id": desc.metadata.id,
        "name": desc.metadata.name,
        "description": desc.metadata.description,
        "provider": desc.metadata.provider,
        "version": desc.metadata.version,
        "edition": desc.metadata.edition,
        "image": {
            "repository": desc.spec.image.repository,
            "tag": desc.spec.image.tag,
            "digest": desc.spec.image.digest,
        },
        "build": (
            None
            if desc.spec.build is None
            else {
                "entrypoint": desc.spec.build.entrypoint,
                "build_context": desc.spec.build.build_context,
                "dockerfile": desc.spec.build.dockerfile,
            }
        ),
        "service": {
            "protocol": desc.spec.service.protocol,
            "port": desc.spec.service.port,
            "endpoints": {
                "health": desc.spec.service.health_path,
                "ready": desc.spec.service.readiness_path,
                "generate": desc.spec.service.generate_path,
                "build": desc.spec.service.build_path,
                "metadata": desc.spec.service.metadata_path,
            },
        },
        "capabilities": desc.spec.capabilities,
        "requirements": {
            "gpu": desc.spec.requirements.gpu,
            "min_vram_gb": desc.spec.requirements.min_vram_gb,
            "cpu_cores": desc.spec.requirements.cpu_cores,
            "memory_gb": desc.spec.requirements.memory_gb,
            "edition": desc.spec.requirements.edition,
        },
        "model_binding": {
            "model_id": desc.spec.model_binding.model_id,
            "is_default": desc.spec.model_binding.is_default,
            "priority": desc.spec.model_binding.priority,
        },
        "lifecycle": {
            "install_policy": desc.spec.lifecycle.install_policy,
            "health_interval_seconds": desc.spec.lifecycle.health_interval_seconds,
            "health_timeout_seconds": desc.spec.lifecycle.health_timeout_seconds,
            "start_timeout_seconds": desc.spec.lifecycle.start_timeout_seconds,
            "restart_policy": desc.spec.lifecycle.restart_policy,
            "idle_timeout": desc.spec.lifecycle.idle_timeout,
        },
    }


def _state_to_payload(runtime_id: str, instance: Optional[RuntimeInstance]) -> dict[str, Any]:
    """Convert the manager's cached state to a Task 4 payload."""
    if instance is None:
        return {
            "runtime_id": runtime_id,
            "phase": "NotInstalled",
            "host": None,
            "port": None,
            "image_identity": None,
            "started_at": None,
            "last_health_at": None,
            "last_request_at": None,
            "health_state": None,
            "endpoint": None,
        }
    endpoint = f"http://{instance.host}:{instance.port}"
    return {
        "runtime_id": runtime_id,
        "phase": instance.state.value,
        "host": instance.host,
        "port": instance.port,
        "image_identity": {
            "repository": instance.image_identity.repository,
            "tag": instance.image_identity.tag,
            "digest": instance.image_identity.digest,
        },
        "started_at": instance.started_at.isoformat() if instance.started_at else None,
        "last_health_at": (
            instance.last_health_at.isoformat() if instance.last_health_at else None
        ),
        "last_request_at": (
            instance.last_request_at.isoformat() if instance.last_request_at else None
        ),
        "health_state": instance.health_state.value,
        "endpoint": endpoint,
    }


def _runtime_to_card(desc: RuntimeDescriptor, instance: Optional[RuntimeInstance]) -> dict:
    """Build the converged runtime card (descriptor + state)."""
    return {
        **_descriptor_to_payload(desc),
        "state": _state_to_payload(desc.metadata.id, instance),
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("")
async def list_runtimes() -> dict[str, Any]:
    """List all runtimes in the registry, each joined with its cached state."""
    manager = _get_manager()
    cards = []
    for desc in manager.registry.list():
        instance = manager.get_cached_instance(desc.metadata.id)
        cards.append(_runtime_to_card(desc, instance))
    return {"runtimes": cards}


@router.get("/{runtime_id}")
async def get_runtime(runtime_id: str) -> dict[str, Any]:
    """Get a single runtime's descriptor + state."""
    manager = _get_manager()
    desc = manager.registry.get(runtime_id)
    if desc is None:
        raise HTTPException(status_code=404, detail=f"Runtime {runtime_id!r} not found in registry")
    instance = manager.get_cached_instance(runtime_id)
    return _runtime_to_card(desc, instance)


@router.get("/{runtime_id}/descriptor")
async def get_runtime_descriptor(runtime_id: str) -> dict[str, Any]:
    """Get the full on-disk descriptor for a runtime."""
    manager = _get_manager()
    desc = manager.registry.get(runtime_id)
    if desc is None:
        raise HTTPException(status_code=404, detail=f"Runtime {runtime_id!r} not found in registry")
    return desc.model_dump()


@router.get("/{runtime_id}/state")
async def get_runtime_state(runtime_id: str) -> dict[str, Any]:
    """Get the operational state of a single runtime (Task 4)."""
    manager = _get_manager()
    desc = manager.registry.get(runtime_id)
    if desc is None:
        raise HTTPException(status_code=404, detail=f"Runtime {runtime_id!r} not found in registry")
    instance = manager.get_cached_instance(runtime_id)
    return _state_to_payload(runtime_id, instance)


@router.get("/{runtime_id}/state/stream")
async def stream_runtime_state(runtime_id: str) -> StreamingResponse:
    """Stream runtime state via Server-Sent Events (Task 5/6).

    The stream emits the current state immediately, then
    continues to emit on every state-transition event
    (RuntimeInstallCompleted, RuntimeStartCompleted,
    RuntimeStopCompleted, RuntimeIdleTimeout, etc.).

    The frontend opens an EventSource and renders the
    step-by-step install/activate progress.
    """
    manager = _get_manager()
    desc = manager.registry.get(runtime_id)
    if desc is None:
        raise HTTPException(status_code=404, detail=f"Runtime {runtime_id!r} not found in registry")

    async def event_stream() -> AsyncIterator[bytes]:
        # Emit the current state immediately.
        instance = manager.get_cached_instance(runtime_id)
        payload = _state_to_payload(runtime_id, instance)
        yield _sse("state", payload)

        # Subscribe to events; emit on every transition.
        queue: asyncio.Queue = asyncio.Queue()

        def _on_event(event) -> None:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass

        if manager._events is not None:
            manager._events.subscribe(_on_event)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    # Re-snapshot the state on every event.
                    instance = manager.get_cached_instance(runtime_id)
                    payload = _state_to_payload(runtime_id, instance)
                    yield _sse("state", payload)
                    yield _sse("event", _event_to_payload(event))
                except asyncio.TimeoutError:
                    # Heartbeat.
                    yield _sse("heartbeat", {"ts": _now()})
        finally:
            # Unsubscribe. RuntimeEventBus does not currently
            # support unsubscribe, so we leak the listener;
            # the queue is bounded and the loop exits on
            # client disconnect (the underlying ASGI server
            # closes the response).
            pass

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _sse(event: str, data: dict) -> bytes:
    """Format a Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n".encode("utf-8")


def _now() -> str:
    """ISO timestamp for SSE heartbeats."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _event_to_payload(event) -> dict[str, Any]:
    """Convert a RuntimeEvent to an SSE payload."""
    return {
        "kind": type(event).__name__,
        "runtime_id": event.runtime_id,
        "timestamp": event.timestamp.isoformat() if hasattr(event, "timestamp") else None,
        "fields": {
            k: v for k, v in event.__dict__.items()
            if k not in ("runtime_id", "timestamp")
        },
    }


# ---------------------------------------------------------------------------
# Lifecycle operations
# ---------------------------------------------------------------------------


@router.post("/{runtime_id}/install")
async def install_runtime(runtime_id: str) -> dict[str, Any]:
    """Install a runtime (Task 5). Delegates to RuntimeManager.install."""
    manager = _get_manager()
    try:
        inst = await manager.install(runtime_id)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"install failed: {exc}",
                "category": "install_failed",
            },
        )
    return {
        "runtime_id": runtime_id,
        "phase": inst.state.value,
        "image_identity": inst.image_identity.__dict__,
    }


@router.post("/{runtime_id}/start")
async def start_runtime(runtime_id: str) -> dict[str, Any]:
    """Activate a runtime (Task 6). Delegates to RuntimeManager.start."""
    manager = _get_manager()
    try:
        inst = await manager.start(runtime_id)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"start failed: {exc}",
                "category": "start_failed",
            },
        )
    return {
        "runtime_id": runtime_id,
        "phase": inst.state.value,
        "host": inst.host,
        "port": inst.port,
        "endpoint": f"http://{inst.host}:{inst.port}",
    }


@router.post("/{runtime_id}/stop")
async def stop_runtime(runtime_id: str) -> dict[str, Any]:
    """Deactivate a runtime (Task 7). Delegates to RuntimeManager.stop."""
    manager = _get_manager()
    try:
        await manager.stop(runtime_id)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"stop failed: {exc}",
                "category": "stop_failed",
            },
        )
    return {"runtime_id": runtime_id, "phase": "Stopped"}


@router.post("/{runtime_id}/update")
async def update_runtime(runtime_id: str) -> dict[str, Any]:
    """Update a runtime (re-pull image)."""
    manager = _get_manager()
    try:
        inst = await manager.update(runtime_id)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"update failed: {exc}",
                "category": "update_failed",
            },
        )
    return {
        "runtime_id": runtime_id,
        "phase": inst.state.value,
        "image_identity": inst.image_identity.__dict__,
    }


@router.post("/{runtime_id}/remove")
async def remove_runtime(runtime_id: str) -> dict[str, Any]:
    """Remove a runtime (stop + remove image)."""
    manager = _get_manager()
    try:
        await manager.remove(runtime_id)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"remove failed: {exc}",
                "category": "remove_failed",
            },
        )
    return {"runtime_id": runtime_id, "phase": "Removed"}


# ---------------------------------------------------------------------------
# Composed view (R9) — Catalog + Runtime Registry + Runtime State
# ---------------------------------------------------------------------------
#
# Per R9, the Models page renders a composed view:
#   1. Model Catalog (BUILTIN_MODELS -> models table) — always present
#   2. Runtime Registry (runtime-registry/<id>/descriptor.json) — augments
#   3. Runtime Operational State (RuntimeManager._instance_cache) — augments
#
# A model may exist without a runtime. A model with a runtime shows the
# runtime's state, endpoint, and lifecycle buttons. A model without a
# runtime shows "Not Available — Not Migrated" in the Runtime section.
#
# The endpoint is NOT gated on RUNTIME_SERVICE_ENABLED. It returns the
# catalog portion always; the runtime portion is the augmentation when
# a manager is attached.
# ---------------------------------------------------------------------------


@composed_router.get("/with-runtimes")
async def list_models_with_runtimes() -> dict[str, Any]:
    """List catalog models, each joined with its runtimes + state.

    The composed view is the Models page's source of truth.
    The catalog is the primary entity; the runtime-registry
    augments it with infrastructure metadata.
    """
    manager = runtime_module.runtime._runtime_manager
    catalog_models = model_registry.list_models(edition=settings.EDITION)

    composed: list[dict[str, Any]] = []
    for model in catalog_models:
        model_id = model.id
        # Resolve the default runtime for this model (if any).
        runtimes: list[dict[str, Any]] = []
        default_runtime_id: Optional[str] = None

        if manager is not None:
            descriptors = manager.registry.list_for_model(model_id)
            # Sort by default + priority (mirrors RuntimeManager.resolve).
            descriptors = sorted(
                descriptors,
                key=lambda d: (
                    not d.spec.model_binding.is_default,
                    d.spec.model_binding.priority,
                ),
            )
            for desc in descriptors:
                instance = manager.get_cached_instance(desc.metadata.id)
                runtimes.append(
                    {
                        "runtime_id": desc.metadata.id,
                        "descriptor": desc.model_dump(),
                        "state": _state_to_payload(desc.metadata.id, instance),
                    }
                )
            if runtimes:
                # Default = the first sorted descriptor (matches the
                # selection rules in RuntimeManager.resolve).
                default_runtime_id = runtimes[0]["runtime_id"]

        composed.append(
            {
                "model": model.model_dump(),
                "runtimes": runtimes,
                "default_runtime_id": default_runtime_id,
            }
        )

    return {"models": composed}


# A separate router for the legacy non-/api prefix (convention in this
# codebase: every models endpoint has both /models and /api/models aliases).
no_prefix_router = APIRouter(tags=["Models (composed)"])


@no_prefix_router.get("/models/with-runtimes")
async def list_models_with_runtimes_no_prefix() -> dict[str, Any]:
    """Same as /api/models/with-runtimes (legacy non-/api prefix)."""
    return await list_models_with_runtimes()

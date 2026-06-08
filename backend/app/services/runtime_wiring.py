"""Runtime subsystem wiring (Phase 3 — P2 + P3).

This module is the single point where the runtime subsystem
is constructed at backend startup. It is gated on
``Settings.RUNTIME_SERVICE_ENABLED`` (R3) and is intentionally
**provider-agnostic** (invariant 18): the wiring does not
know about Kokoro, F5-TTS, XTTS, OpenVoice, or Fish Audio.
The providers are in the descriptors (under
``runtime-registry/``) and in the adapter config.

Public surface
--------------

- ``wire_runtime_services(settings) -> RuntimeManager | None``:
  the single entry point. When the flag is off, returns
  ``None``. When the flag is on, constructs the registry,
  the driver, and the manager; attaches the manager to the
  ``PeakVoxRuntime`` singleton; returns the manager (so
  the lifespan can start the idle reaper task).

- ``start_idle_reaper(manager) -> asyncio.Task | None``:
  starts the background reaper task (R7). Returns None if
  no manager is attached.

- ``stop_idle_reaper(task) -> None``:
  cancels the reaper task at shutdown.

The wiring follows the lazy-startup invariant (R6): at
backend boot, **no** runtime container is started. The
first ``RuntimeManager.resolve(model_id)`` call activates
the runtime. The instance cache is empty at startup.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from app.core.config import Settings
from app.services.runtime_driver import RuntimeDriver
from app.services.runtime_events import RuntimeEventBus
from app.services.runtime_manager import RuntimeManager
from app.services.runtime_registry import RuntimeRegistry, RuntimeRegistryLoader


logger = logging.getLogger(__name__)


def _build_registry(settings: Settings) -> RuntimeRegistry:
    """Build the in-memory registry from the on-disk descriptors.

    The loader walks ``settings.RUNTIME_REGISTRY_PATH`` and
    parses each ``<runtime_id>/descriptor.json`` file.
    Malformed descriptors are logged and excluded; one bad
    descriptor does not block the rest.
    """
    return RuntimeRegistryLoader().load_from_directory(settings.RUNTIME_REGISTRY_PATH)


def _build_driver() -> RuntimeDriver:
    """Build the concrete driver.

    Phase 3 uses the ``DockerRuntimeDriver`` (the first
    concrete driver, sub-phase 2B). The wiring imports
    the driver lazily so that the import error is bounded
    to the runtime-subsystem-enabled path.
    """
    from app.services.drivers.docker_runtime_driver import DockerRuntimeDriver
    return DockerRuntimeDriver()


def wire_runtime_services(settings: Settings) -> Optional[RuntimeManager]:
    """Construct the runtime subsystem at backend startup.

    Gated on ``settings.RUNTIME_SERVICE_ENABLED`` (R3). When
    the flag is off, returns ``None`` and does nothing. When
    the flag is on, constructs the registry, the driver, and
    the manager, attaches the manager to ``PeakVoxRuntime``,
    and returns the manager.

    The wiring does NOT start any runtime container (R6);
    the first ``RuntimeManager.resolve`` call activates the
    runtime lazily. The instance cache is empty at startup.

    The wiring is provider-agnostic: it does not branch on
    provider names; the providers are in the descriptors
    and the adapter config, never in the manager or driver.
    """
    if not settings.RUNTIME_SERVICE_ENABLED:
        logger.info(
            "RUNTIME_SERVICE_ENABLED=false; "
            "the runtime subsystem is not constructed. "
            "The in-process adapter path is the only path."
        )
        return None

    logger.info(
        "RUNTIME_SERVICE_ENABLED=true; "
        "constructing the runtime subsystem (R3)."
    )

    # 1. Build the in-memory registry from on-disk descriptors.
    registry = RuntimeRegistryLoader().load_from_directory(settings.RUNTIME_REGISTRY_PATH)
    logger.info(
        "Loaded %d runtime descriptor(s) from %s",
        len(registry),
        settings.RUNTIME_REGISTRY_PATH,
    )

    # 2. Build the driver.
    driver = _build_driver()
    events = RuntimeEventBus()

    # 3. Build the manager.
    manager = RuntimeManager(
        registry=registry,
        driver=driver,
        events=events,
    )
    logger.info(
        "RuntimeManager constructed; "
        "%d runtime(s) registered; "
        "no containers started (R6 — lazy activation).",
        len(registry),
    )

    # 4. Attach the manager to the PeakVoxRuntime singleton.
    from app.services import runtime as runtime_module
    runtime_module.runtime.attach_runtime_manager(manager)

    return manager


async def start_idle_reaper(manager: Optional[RuntimeManager]) -> Optional[asyncio.Task]:
    """Start the idle reaper background task (R7).

    Returns the asyncio.Task (so the lifespan can cancel it
    on shutdown), or None if no manager is attached.

    The reaper wakes up every 60 seconds and calls
    ``manager.run_idle_reaper()`` to auto-stop any Active
    runtime that has been idle for longer than its
    descriptor's ``spec.lifecycle.idle_timeout``.
    """
    if manager is None:
        return None
    task = asyncio.create_task(
        _idle_reaper_loop(manager),
        name="runtime_idle_reaper",
    )
    logger.info("Started runtime idle reaper task (R7).")
    return task


async def stop_idle_reaper(task: Optional[asyncio.Task]) -> None:
    """Cancel the idle reaper task on shutdown."""
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    logger.info("Stopped runtime idle reaper task.")


async def _idle_reaper_loop(manager: RuntimeManager) -> None:
    """The idle reaper coroutine.

    Wakes up every 60 seconds. Calls
    ``manager.run_idle_reaper()`` to auto-stop any Active
    instance whose ``last_request_at`` is older than its
    descriptor's ``idle_timeout``. ``idle_timeout = never``
    disables the reaper for that runtime (Cloud default).
    """
    try:
        while True:
            await asyncio.sleep(60)
            try:
                reaped = manager.run_idle_reaper()
                if reaped:
                    logger.info("Idle reaper stopped %d runtime(s).", reaped)
            except Exception:  # noqa: BLE001
                logger.exception("Idle reaper iteration failed")
    except asyncio.CancelledError:
        raise

"""Runtime Manager CLI skeleton (Phase 2D.4).

This is the PROGRAMMATIC entry point for the four CE
operations on the RuntimeManager. The CLI (Click / Typer /
argparse) is built on top of this in a later phase; the
goal of 2D.4 is to expose the operations as a Python API
that can be invoked from a REPL, a Jupyter notebook, or a
custom operator script.

Usage (programmatic):

    from scripts.runtime_manager import RuntimeOperator
    op = RuntimeOperator.from_settings()
    await op.install("kokoro-82m")
    await op.start("kokoro-82m")
    print(op.status("kokoro-82m"))
    await op.stop("kokoro-82m")
    await op.remove("kokoro-82m")

The four operations are:

  - install(runtime_id)  →  RuntimeInstance
  - start(runtime_id)    →  RuntimeInstance
  - stop(runtime_id)     →  None
  - update(runtime_id)   →  RuntimeInstance
  - remove(runtime_id)   →  None
  - status(runtime_id)   →  RuntimeInstance
  - resolve(model_id)    →  Optional[RuntimeResolution]
  - list_runtimes()      →  List[RuntimeInstance]

Architectural invariants (per the Runtime Activation Audit):

  - The RuntimeOperator depends on the RuntimeManager,
    which is substrate-neutral. The driver (e.g.
    DockerRuntimeDriver) is the only component allowed
    to import Docker libraries.
  - The operator's kwargs do not include Voice /
    VoiceVariant / VoiceVariantArtifact objects. The
    operator works on runtime_ids and model_ids only.
  - The operator is dependency-light: it imports
    pydantic_settings (for Settings), the runtime
    modules, and asyncio. It does not import Docker.
"""

from __future__ import annotations

import asyncio
from typing import List, Optional

from app.core.config import Settings, settings
from app.services.runtime_driver import RuntimeDriver
from app.services.runtime_errors import RuntimeDriverError
from app.services.runtime_events import RuntimeEventBus
from app.services.runtime_instance import RuntimeInstance
from app.services.runtime_manager import (
    NoDriverConfigured,
    RuntimeManager,
    RuntimeResolution,
)
from app.services.runtime_registry import (
    RuntimeRegistry,
    RuntimeRegistryLoader,
)


class RuntimeOperator:
    """A high-level wrapper around RuntimeManager for the four
    CE operations.

    The operator is the programmatic interface for ops teams.
    It owns the lifecycle of the RuntimeManager, the
    RuntimeRegistry, and the RuntimeDriver. The CLI (a
    future phase) is a thin wrapper around this class.

    Architectural invariants:

      - The operator does not import Docker / K8s / Podman.
      - The operator's methods accept only runtime_ids and
        model_ids (string identifiers), NOT Voice /
        VoiceVariant / VoiceVariantArtifact objects.
      - The operator is async (the underlying driver ops are
        async). Synchronous CLI commands call ``.run()`` on
        each operation.
    """

    def __init__(
        self,
        *,
        manager: RuntimeManager,
        settings: Settings,
    ) -> None:
        self._manager = manager
        self._settings = settings

    @classmethod
    def from_settings(
        cls,
        *,
        settings: Settings = settings,
        driver: Optional[RuntimeDriver] = None,
        events: Optional[RuntimeEventBus] = None,
    ) -> "RuntimeOperator":
        """Construct a RuntimeOperator from application settings.

        Loads the runtime registry from ``settings.RUNTIME_REGISTRY_PATH``.
        Wires the supplied driver (caller-provided so the
        CLI can inject DockerRuntimeDriver in production
        and a fake driver in tests). The events bus is
        constructed if not supplied.
        """
        loader = RuntimeRegistryLoader()
        registry = loader.load_from_directory(settings.RUNTIME_REGISTRY_PATH)
        if events is None:
            events = RuntimeEventBus()
        manager = RuntimeManager(registry=registry, driver=driver, events=events)
        return cls(manager=manager, settings=settings)

    # --- The four CE operations (synchronous wrappers) ----

    def install(self, runtime_id: str) -> RuntimeInstance:
        return asyncio.run(self._manager.install(runtime_id))

    def start(self, runtime_id: str) -> RuntimeInstance:
        return asyncio.run(self._manager.start(runtime_id))

    def stop(self, runtime_id: str) -> None:
        asyncio.run(self._manager.stop(runtime_id))

    def update(self, runtime_id: str) -> RuntimeInstance:
        return asyncio.run(self._manager.update(runtime_id))

    def remove(self, runtime_id: str) -> None:
        asyncio.run(self._manager.remove(runtime_id))

    # --- Inspection ----

    def status(self, runtime_id: str) -> RuntimeInstance:
        return asyncio.run(self._manager.status(runtime_id))

    def resolve(self, model_id: str) -> Optional[RuntimeResolution]:
        return self._manager.resolve(model_id)

    def list_runtimes(self) -> List[RuntimeInstance]:
        """All cached ``RuntimeInstance`` objects (operational
        state only; no domain objects)."""
        return self._manager.list_cached_instances()

    def list_installed_runtimes(self) -> List[str]:
        """All runtime_ids that are currently cached (installed)."""
        return [inst.runtime_id for inst in self._manager.list_cached_instances()]


# --- Synchronous CLI-style helpers (for REPL / scripts) ---


def main() -> None:  # pragma: no cover — CLI entry point
    """CLI entry point (Phase 2D.4). The CLI is a thin wrapper
    around ``RuntimeOperator``. This function is the
    placeholder; the actual CLI (Click / Typer / argparse)
    is built on top of this in a later phase."""
    raise NotImplementedError(
        "RuntimeManager CLI is a placeholder in 2D.4; the "
        "programmatic interface is RuntimeOperator. The CLI "
        "(argparse / Click / Typer) is built on top of this "
        "in a later phase."
    )


if __name__ == "__main__":  # pragma: no cover
    main()

"""Runtime driver error hierarchy (Phase 2A, 2A.4 — RuntimeDriverError).

Per ADR-0017 §4.4.1, the driver raises typed errors that the
RuntimeManager catches, logs, and translates into API responses.

Eight subclasses of RuntimeDriverError, plus a small set of helpers
for the most common shapes (substrate, cause, operation/timeout).

Phase 2A is infrastructure foundation work. This module is
dependency-light (no torch, no Docker SDK, no model frameworks, no
HTTP clients).
"""

from __future__ import annotations

from typing import Optional


class RuntimeDriverError(Exception):
    """Base class for all driver errors (ADR-0017 §4.4.1).

    Every subclass carries a ``runtime_id`` (which runtime the error
    concerns) and a human-readable ``message``. Subclasses may add
    subclass-specific fields (cause, substrate, operation, etc.).
    """

    def __init__(self, runtime_id: str, message: str) -> None:
        self.runtime_id = runtime_id
        self.message = message
        super().__init__(f"runtime '{runtime_id}': {message}")


class RuntimeNotFound(RuntimeDriverError):
    """The runtime is not registered with the driver."""


class ImagePullError(RuntimeDriverError):
    """The image could not be pulled (registry 404, auth, network)."""

    def __init__(
        self, runtime_id: str, message: str, *, cause: Optional[BaseException] = None
    ) -> None:
        super().__init__(runtime_id, message)
        self.cause = cause


class SubstrateError(RuntimeDriverError):
    """A generic substrate failure (Docker daemon down, K8s API down, ...)."""

    def __init__(self, runtime_id: str, substrate: str, message: str) -> None:
        super().__init__(runtime_id, f"[{substrate}] {message}")
        self.substrate = substrate


class RuntimeAlreadyExists(RuntimeDriverError):
    """An install was attempted but an instance is already present."""


class RuntimeNotActive(RuntimeDriverError):
    """The operation requires an Active instance (e.g. logs)."""


class TimeoutError(RuntimeDriverError):  # noqa: A001 — intentional shadow
    """An operation exceeded its configured timeout (ADR-0017 §4.4.4)."""

    def __init__(self, runtime_id: str, operation: str, timeout_seconds: int) -> None:
        super().__init__(
            runtime_id, f"operation '{operation}' exceeded {timeout_seconds}s timeout"
        )
        self.operation = operation
        self.timeout_seconds = timeout_seconds


class RuntimeRequirementsNotMet(RuntimeDriverError):
    """The host does not satisfy the descriptor's requirements (e.g. GPU)."""


class RuntimeHealthFailed(RuntimeDriverError):
    """A /ready probe failed during start_runtime (e.g. weights_loading)."""

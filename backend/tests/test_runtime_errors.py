"""TDD: RuntimeDriverError hierarchy (2A.4).

Per ADR-0017 §4.4.1, the driver raises typed errors that the
RuntimeManager catches, logs, and translates into API responses.

Eight subclasses of RuntimeDriverError:
  - RuntimeNotFound
  - ImagePullError
  - SubstrateError
  - RuntimeAlreadyExists
  - RuntimeNotActive
  - TimeoutError
  - RuntimeRequirementsNotMet
  - RuntimeHealthFailed

Phase 2A is infrastructure foundation work. The class hierarchy
is dependency-light (no torch, no Docker SDK).
"""

from __future__ import annotations

import pytest

from app.services.runtime_errors import (
    ImagePullError,
    RuntimeAlreadyExists,
    RuntimeDriverError,
    RuntimeHealthFailed,
    RuntimeNotActive,
    RuntimeNotFound,
    RuntimeRequirementsNotMet,
    SubstrateError,
    TimeoutError,
)


def test_base_class_is_an_exception() -> None:
    assert issubclass(RuntimeDriverError, Exception)
    err = RuntimeDriverError("kokoro-cpu", "boom")
    assert err.runtime_id == "kokoro-cpu"
    assert err.message == "boom"
    assert "kokoro-cpu" in str(err)
    assert "boom" in str(err)


def test_all_eight_subclasses_inherit_from_base() -> None:
    for cls in (
        RuntimeNotFound,
        ImagePullError,
        SubstrateError,
        RuntimeAlreadyExists,
        RuntimeNotActive,
        TimeoutError,
        RuntimeRequirementsNotMet,
        RuntimeHealthFailed,
    ):
        assert issubclass(cls, RuntimeDriverError), f"{cls.__name__} is not a RuntimeDriverError"


def test_runtime_not_found_carries_runtime_id() -> None:
    err = RuntimeNotFound("kokoro-cpu", "not registered with driver")
    assert err.runtime_id == "kokoro-cpu"
    assert "not registered" in err.message
    assert isinstance(err, RuntimeDriverError)


def test_image_pull_error_can_carry_underlying_cause() -> None:
    cause = RuntimeError("registry 404")
    err = ImagePullError("kokoro-cpu", "pull failed", cause=cause)
    assert err.cause is cause
    assert isinstance(err, RuntimeDriverError)


def test_substrate_error_carries_substrate_name() -> None:
    err = SubstrateError("kokoro-cpu", "docker", "daemon down")
    assert err.substrate == "docker"
    assert isinstance(err, RuntimeDriverError)


def test_runtime_requirements_not_met_carries_requirement() -> None:
    err = RuntimeRequirementsNotMet("kokoro-cuda", "gpu=required but host has none")
    assert "gpu" in err.message
    assert isinstance(err, RuntimeDriverError)


def test_health_failed_carries_last_error() -> None:
    err = RuntimeHealthFailed("kokoro-cpu", "/ready timeout")
    assert "timeout" in err.message
    assert isinstance(err, RuntimeDriverError)


def test_timeout_error_carries_operation_and_timeout() -> None:
    err = TimeoutError("kokoro-cpu", "start_runtime", 60)
    assert err.operation == "start_runtime"
    assert err.timeout_seconds == 60
    assert isinstance(err, RuntimeDriverError)

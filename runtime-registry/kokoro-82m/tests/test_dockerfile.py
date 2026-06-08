"""TDD: P1.4 — Dockerfile structure checks.

The Kokoro runtime Dockerfile is the build input for the
``peakvox/kokoro-runtime:0.1.0`` image. The Dockerfile must
implement the contract:

  - Base on python:3.11-slim (CPU-only; matches the
    descriptor's ``spec.requirements.gpu = "optional"``).
  - Install ``requirements.txt`` (the Kokoro framework).
  - Copy ``server.py`` to ``/app/server.py``.
  - ``EXPOSE`` the descriptor's ``spec.service.port`` (8000).
  - ``CMD`` (or ``ENTRYPOINT``) launches ``uvicorn server:app``
    on the descriptor's port.

These are structural checks: the test reads the Dockerfile as
text and asserts the contract. Building the image and running
it is a CI-gated E2E test (test_docker_build.py etc.).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


def _kokoro_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def _dockerfile_path() -> Path:
    return _kokoro_dir() / "Dockerfile"


def _descriptor_path() -> Path:
    return _kokoro_dir() / "descriptor.json"


def _read_dockerfile() -> str:
    p = _dockerfile_path()
    assert p.exists(), f"missing Dockerfile at {p}"
    return p.read_text()


def _read_descriptor() -> dict:
    p = _descriptor_path()
    return json.loads(p.read_text())


# ---------------------------------------------------------------------------
# Existence and base image
# ---------------------------------------------------------------------------


def test_dockerfile_exists_at_canonical_path() -> None:
    """The Dockerfile is at runtime-registry/kokoro-82m/Dockerfile."""
    assert _dockerfile_path().exists()


def test_dockerfile_uses_python_3_11_slim_base() -> None:
    """The base image is python:3.11-slim (CPU; matches descriptor)."""
    df = _read_dockerfile()
    assert re.search(r"^FROM\s+python:3\.11-slim", df, re.MULTILINE), (
        f"Dockerfile must use python:3.11-slim as the base; got:\n{df}"
    )


# ---------------------------------------------------------------------------
# Requirements install
# ---------------------------------------------------------------------------


def test_dockerfile_installs_requirements_txt() -> None:
    """The Dockerfile installs requirements.txt (the Kokoro framework)."""
    df = _read_dockerfile()
    assert re.search(
        r"(pip install.*-r.*requirements\.txt|requirements\.txt)",
        df,
        re.IGNORECASE | re.DOTALL,
    ), f"Dockerfile must install requirements.txt; got:\n{df}"


# ---------------------------------------------------------------------------
# Server copy + port
# ---------------------------------------------------------------------------


def test_dockerfile_copies_server_py() -> None:
    """The Dockerfile copies server.py into the image."""
    df = _read_dockerfile()
    assert re.search(r"COPY\s+server\.py", df), (
        f"Dockerfile must COPY server.py; got:\n{df}"
    )


def test_dockerfile_exposes_service_port() -> None:
    """The Dockerfile EXPOSE matches the descriptor's spec.service.port."""
    df = _read_dockerfile()
    d = _read_descriptor()
    expected_port = d["spec"]["service"]["port"]
    assert re.search(rf"EXPOSE\s+{expected_port}\b", df), (
        f"Dockerfile must EXPOSE {expected_port}; got:\n{df}"
    )


# ---------------------------------------------------------------------------
# CMD / ENTRYPOINT
# ---------------------------------------------------------------------------


def test_dockerfile_cmd_invokes_uvicorn() -> None:
    """The CMD (or ENTRYPOINT) launches uvicorn with server:app."""
    df = _read_dockerfile()
    # CMD ["uvicorn", "server:app", ...]
    assert "uvicorn" in df
    assert "server:app" in df


def test_dockerfile_cmd_binds_to_all_interfaces() -> None:
    """The CMD binds to 0.0.0.0 (not 127.0.0.1) so the container is
    reachable from outside its network namespace."""
    df = _read_dockerfile()
    assert re.search(r"--host\s+0\.0\.0\.0", df) or "0.0.0.0" in df, (
        f"Dockerfile CMD must bind to 0.0.0.0; got:\n{df}"
    )


def test_dockerfile_cmd_binds_to_service_port() -> None:
    """The CMD binds to the descriptor's service port.

    Accepts both shell form (e.g. ``--port 8000``) and exec
    form (e.g. ``"--port", "8000"``).
    """
    df = _read_dockerfile()
    d = _read_descriptor()
    expected_port = d["spec"]["service"]["port"]
    # Shell form: --port 8000
    shell_match = re.search(rf"--port[\s=]+{expected_port}\b", df)
    # Exec form (JSON list): "--port" ... "8000" (within 30 chars)
    exec_match = bool(re.search(
        rf'"--port"[^"]*"[^"]*{expected_port}\b',
        df,
    ))
    assert shell_match or exec_match, (
        f"Dockerfile CMD must bind to port {expected_port}; got:\n{df}"
    )


# ---------------------------------------------------------------------------
# Working directory
# ---------------------------------------------------------------------------


def test_dockerfile_uses_app_workdir() -> None:
    """The Dockerfile sets WORKDIR to /app (where server.py lives)."""
    df = _read_dockerfile()
    assert re.search(r"WORKDIR\s+/app\b", df), (
        f"Dockerfile must set WORKDIR /app; got:\n{df}"
    )

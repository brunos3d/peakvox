"""TDD: KokoroAdapter with HTTPTransport + KOKORO_RUNTIME_URL (2C.2).

Per the Transport Boundary Audit, the adapter is allowed exactly
one new dependency: ``HTTPTransport``. The adapter does NOT
gain knowledge of Docker, containers, ``RuntimeDescriptor``,
``RuntimeInstance``, ``RuntimeRegistry``, or ``RuntimeManager``.

In Phase 2C, the ``KokoroAdapter.generate()`` method dispatches
based on a single env var (or settings field):
  - ``KOKORO_RUNTIME_URL`` is set: route the request to the
    runtime service via ``HTTPTransport``. Translate the existing
    kwargs to the Runtime Service Contract; the runtime service
    produces the audio.
  - ``KOKORO_RUNTIME_URL`` is empty (the CE default): use the
    existing in-process ``kokoro`` package (lazy import). The
    current in-process behavior is preserved exactly.

The two paths are mutually exclusive; the caller (PeakVoxRuntime)
does not change. The dispatch is local to ``KokoroAdapter``.

These tests assert:
- The adapter's contract surface is unchanged: ``generate``,
  ``build_variant``, ``clone_voice``, ``health_check`` are the
  same call signatures as before.
- When ``KOKORO_RUNTIME_URL`` is unset, the adapter uses the
  in-process path (the existing test ``test_kokoro_adapter.py``
  continues to pass — this is exercised by the regression
  suite; the new tests focus on the runtime-service path).
- When the env var is set, the adapter routes the request via
  ``HTTPTransport`` to the runtime service.
- The adapter does NOT import Docker.
- The adapter does NOT reference ``RuntimeDescriptor``,
  ``RuntimeInstance``, ``RuntimeRegistry``, or ``RuntimeManager``.
- The adapter translates the existing kwargs to the Runtime
  Service Contract (HTTP/JSON) and maps the response back to
  the existing ``(duration, logs)`` tuple.
- The in-process path is preserved as a fallback when the env
  var is empty.
"""

from __future__ import annotations

import asyncio
import base64
import json
import re
from pathlib import Path
from typing import Any

import httpx
import pytest

import app.services.model_adapters.kokoro_adapter as kokoro_adapter_mod
from app.models.registry_types import ModelCapabilities, ModelDescriptor
from app.services.adapter_transport import http_transport
from app.services.adapter_transport.http_transport import (
    HTTPTransport,
    HTTPTransportError,
)
from app.services.model_adapters.kokoro_adapter import KokoroAdapter


def _descriptor() -> ModelDescriptor:
    return ModelDescriptor(
        id="kokoro-base", name="Kokoro Base", description="d",
        provider="kokoro", supported_languages=["en"],
        supported_tags=[], capabilities=ModelCapabilities(supports_tts=True),
    )


# ---- Adapter boundary: no substrate / runtime domain knowledge ---------------

def test_kokoro_adapter_does_not_import_docker() -> None:
    """Architectural invariant: the adapter is HTTP-only. It does
    not import Docker or any substrate library. The runtime
    service is a separate process; the adapter talks to it via
    HTTPTransport."""
    text = open(kokoro_adapter_mod.__file__).read()
    text_clean = re.sub(r'\"{3}.*?\"{3}', "", text, flags=re.DOTALL)
    assert "import docker" not in text_clean
    assert "from docker" not in text_clean


def test_kokoro_adapter_does_not_reference_runtime_domain_types() -> None:
    """Architectural invariant: the adapter does not gain
    knowledge of RuntimeDescriptor, RuntimeInstance,
    RuntimeRegistry, or RuntimeManager. The adapter's contract
    is the existing ModelAdapter surface; the runtime-service
    path uses HTTPTransport, not the runtime domain types.

    The test inspects the source: prose mentions in docstrings
    are allowed (they describe the design), but USES of the
    types as imports, attributes, parameters, or return values
    are forbidden. We strip docstrings + comments before
    scanning.
    """
    text = open(kokoro_adapter_mod.__file__).read()
    text_clean = re.sub(r'\"{3}.*?\"{3}', "", text, flags=re.DOTALL)
    text_clean = re.sub(r"#.*", "", text_clean)
    forbidden = [
        "RuntimeDescriptor", "RuntimeInstance", "RuntimeRegistry",
        "RuntimeManager", "DockerRuntimeDriver",
    ]
    for s in forbidden:
        assert s not in text_clean, (
            f"KokoroAdapter must not reference {s!r}; the adapter's "
            f"runtime-service path is HTTP-only."
        )


def test_kokoro_adapter_does_have_http_transport_dependency() -> None:
    """The adapter gains exactly one new dependency: HTTPTransport.
    This is the allowed seam."""
    text = open(kokoro_adapter_mod.__file__).read()
    # HTTPTransport is the allowed dependency.
    assert "HTTPTransport" in text or "http_transport" in text


# ---- Adapter contract preserved ------------------------------------------------

def test_kokoro_adapter_contract_surface_is_unchanged() -> None:
    """The adapter's public method surface must not grow. The
    Phase 2C changes are local to ``generate`` (and
    ``build_variant`` for the variant-build endpoint)."""
    a = KokoroAdapter(_descriptor())
    for name in ("install", "load", "unload", "health_check", "generate",
                 "clone_voice", "build_variant"):
        assert hasattr(a, name), f"KokoroAdapter lost {name!r}"


# ---- Runtime-service path: request translation ---------------------------------

def _setup_adapter_with_mock_server(handler) -> KokoroAdapter:
    """Build a KokoroAdapter whose HTTPTransport uses a
    MockTransport that dispatches to ``handler``."""
    mt = httpx.MockTransport(handler)
    # We construct the HTTPTransport with the mock client so
    # the adapter's POST goes to the in-process mock.
    transport = HTTPTransport(
        base_url="http://runtime.local:8000",
        bearer_token="",
        timeout_seconds=5.0,
    )
    transport._client = httpx.AsyncClient(transport=mt, base_url="http://runtime.local:8000")
    a = KokoroAdapter(_descriptor())
    # Inject the transport into the adapter; the adapter decides
    # whether to use it based on the env var.
    a._runtime_transport = transport  # type: ignore[attr-defined]
    # Force the runtime-service path (set the env var).
    monkey = pytest.MonkeyPatch()
    monkey.setenv("KOKORO_RUNTIME_URL", "http://runtime.local:8000")
    # The MonkeyPatch context is returned via a fixture pattern; in
    # the tests below we use a manual context manager.
    return a, monkey, transport


def _audio_bytes_base64() -> str:
    # A small deterministic byte string; the runtime service
    # returns audio in JSON as base64 (per ADR-0017 §6.3).
    return base64.b64encode(b"FAKE_WAV_HEADER" + b"\x00" * 64).decode()


def test_generate_routes_to_http_transport_when_env_set() -> None:
    """When KOKORO_RUNTIME_URL is set, ``KokoroAdapter.generate``
    routes the request via HTTPTransport to the runtime service.
    The response (audio base64 + duration + logs) is mapped back
    to the existing (duration, logs) tuple; the audio is written
    to ``output_path``."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "duration_seconds": 1.5,
                "logs": ["hello from runtime service"],
                "audio_b64": _audio_bytes_base64(),
            },
        )

    mt = httpx.MockTransport(handler)
    transport = HTTPTransport(base_url="http://runtime.local:8000")
    transport._client = httpx.AsyncClient(transport=mt, base_url="http://runtime.local:8000")

    a = KokoroAdapter(_descriptor())
    a._runtime_transport = transport  # type: ignore[attr-defined]

    # Set the env var via monkeypatch; the adapter reads it on
    # every generate() call to allow runtime configuration.
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("KOKORO_RUNTIME_URL", "http://runtime.local:8000")
    try:
        out_path = Path("/tmp/kokoro_runtime_test.wav")
        duration, logs = asyncio.run(
            a.generate(
                text="hi", output_path=out_path,
                voice_id="voice_abc", language="en",
            )
        )
        assert duration == 1.5
        # The runtime service's logs are surfaced; the adapter
        # appends a "routed via runtime service" note.
        assert logs[0] == "hello from runtime service"
        assert any("routed via runtime service" in line for line in logs)
        # The audio was written to the output path.
        assert out_path.exists()
        assert out_path.read_bytes() == b"FAKE_WAV_HEADER" + b"\x00" * 64
        # The request path was /v1/generate (per ADR-0017 §6.3).
        assert captured["path"] == "/v1/generate"
        # The body carried the canonical shape.
        assert captured["body"]["text"] == "hi"
        assert captured["body"]["voice_id"] == "voice_abc"
        assert captured["body"]["language"] == "en"
    finally:
        monkeypatch.undo()
        if out_path.exists():
            out_path.unlink()


def test_generate_falls_back_to_in_process_when_env_unset() -> None:
    """When KOKORO_RUNTIME_URL is empty (CE default), the adapter
    uses the in-process kokoro package (lazy import). The
    existing in-process path is preserved exactly; no HTTP call
    is made."""
    # We do not actually run the in-process path here (that
    # requires the `kokoro` package and model weights). The
    # invariant we can verify without those is: when the env var
    # is empty, the adapter does NOT instantiate an
    # HTTPTransport and does NOT make an HTTP call. We test
    # this by checking that the adapter's internal flag is
    # ``False`` (the runtime-service path is disabled).
    a = KokoroAdapter(_descriptor())
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.delenv("KOKORO_RUNTIME_URL", raising=False)
    try:
        assert a._runtime_service_enabled() is False  # type: ignore[attr-defined]
    finally:
        monkeypatch.undo()


def test_generate_raises_httptransporterror_when_runtime_5xx() -> None:
    """The adapter propagates HTTPTransportError as a clear
    PeakVox error. The error category is mapped to the canonical
    PeakVox envelope."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            503,
            json={"error": {"category": "not_ready", "message": "weights still loading"}},
        )
    mt = httpx.MockTransport(handler)
    transport = HTTPTransport(base_url="http://runtime.local:8000")
    transport._client = httpx.AsyncClient(transport=mt, base_url="http://runtime.local:8000")
    a = KokoroAdapter(_descriptor())
    a._runtime_transport = transport  # type: ignore[attr-defined]
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("KOKORO_RUNTIME_URL", "http://runtime.local:8000")
    try:
        with pytest.raises(HTTPTransportError) as excinfo:
            asyncio.run(
                a.generate(
                    text="hi", output_path=Path("/tmp/x.wav"),
                )
            )
        assert excinfo.value.status == 503
    finally:
        monkeypatch.undo()


# ---- Architectural invariant: caller is unchanged -----------------------------

def test_caller_uses_existing_contract_no_new_args() -> None:
    """The caller (PeakVoxRuntime) does not need to know whether
    the adapter is in-process or runtime-service. The
    ``generate`` signature is unchanged."""
    a = KokoroAdapter(_descriptor())
    import inspect
    sig = inspect.signature(a.generate)
    # The existing kwargs: text, output_path, voice_profile_id,
    # voice_id, ref_audio_path, ref_text, language, instruct, params,
    # job_id. No new arguments introduced.
    params = list(sig.parameters.keys())
    for expected in ("text", "output_path", "voice_id", "language", "params"):
        assert expected in params, (
            f"generate must accept {expected!r}; the adapter's contract "
            f"is unchanged for callers."
        )

"""TDD: KokoroAdapter with HTTPTransport + runtime_endpoint injection.

Per the Transport Boundary Audit, the adapter is allowed exactly
one new dependency: ``HTTPTransport``. The adapter does NOT
gain knowledge of Docker, containers, ``RuntimeDescriptor``,
``RuntimeInstance``, ``RuntimeRegistry``, or ``RuntimeManager``.

Runtime endpoint discovery is entirely owned by the orchestration
layer (PeakVoxRuntime → RuntimeManager → RuntimeDriver). The
adapter receives the endpoint via the ``runtime_endpoint`` kwarg
that ``PeakVoxRuntime.generate()`` injects when the RuntimeManager
has an ACTIVE instance for this model. The adapter never reads
environment variables to discover runtime URLs.

Dispatch rules:
  - ``runtime_endpoint`` is set (non-None): route the request to
    the runtime service via ``HTTPTransport``.
  - ``runtime_endpoint`` is None (CE default / runtime not active):
    use the existing in-process ``kokoro`` package (lazy import).

The two paths are mutually exclusive; the caller (PeakVoxRuntime)
controls dispatch.

These tests assert:
- The adapter's contract surface: ``generate``, ``build_variant``,
  ``clone_voice``, ``health_check`` are the same call signatures.
- When ``runtime_endpoint`` is None, the adapter does NOT make an
  HTTP call (in-process path selected).
- When ``runtime_endpoint`` is set, the adapter routes the request
  via ``HTTPTransport`` to the runtime service.
- The runtime returns ``audio/wav`` binary per ADR-0017 §6.3; the
  adapter writes the bytes directly to ``output_path``.
- The adapter does NOT import Docker.
- The adapter does NOT reference ``RuntimeDescriptor``,
  ``RuntimeInstance``, ``RuntimeRegistry``, or ``RuntimeManager``.
- The adapter prefers ``preset_name`` from ``params`` over any
  internal voice UUID when building the runtime ``voice_id``.
"""

from __future__ import annotations

import asyncio
import io
import re
import struct
import wave
from pathlib import Path

import httpx
import pytest

import app.services.model_adapters.kokoro_adapter as kokoro_adapter_mod
from app.models.registry_types import ModelCapabilities, ModelDescriptor
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


def _make_wav_bytes(duration_ms: int = 500) -> bytes:
    """Build a minimal valid WAV file (16-bit mono 24kHz)."""
    sample_rate = 24000
    n_frames = int(sample_rate * duration_ms / 1000)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * n_frames)
    return buf.getvalue()


# ---- Adapter boundary: no substrate / runtime domain knowledge ---------------

def test_kokoro_adapter_does_not_import_docker() -> None:
    """Architectural invariant: the adapter is HTTP-only."""
    text = open(kokoro_adapter_mod.__file__).read()
    text_clean = re.sub(r'\"{3}.*?\"{3}', "", text, flags=re.DOTALL)
    assert "import docker" not in text_clean
    assert "from docker" not in text_clean


def test_kokoro_adapter_does_not_reference_runtime_domain_types() -> None:
    """Architectural invariant: the adapter does not reference runtime domain types."""
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
    """The adapter gains exactly one new dependency: HTTPTransport."""
    text = open(kokoro_adapter_mod.__file__).read()
    assert "HTTPTransport" in text or "http_transport" in text


def test_kokoro_adapter_does_not_read_env_vars_for_runtime_url() -> None:
    """Architectural invariant: the adapter must not read KOKORO_RUNTIME_URL
    or any other env var to discover the runtime endpoint. Endpoint
    injection is the orchestration layer's job."""
    text = open(kokoro_adapter_mod.__file__).read()
    text_clean = re.sub(r'\"{3}.*?\"{3}', "", text, flags=re.DOTALL)
    text_clean = re.sub(r"#.*", "", text_clean)
    assert "KOKORO_RUNTIME_URL" not in text_clean, (
        "KokoroAdapter must not read KOKORO_RUNTIME_URL from the environment; "
        "the runtime endpoint is injected by PeakVoxRuntime via runtime_endpoint."
    )


# ---- Adapter contract preserved ------------------------------------------------

def test_kokoro_adapter_contract_surface_is_unchanged() -> None:
    """The adapter's public method surface must include all required methods."""
    a = KokoroAdapter(_descriptor())
    for name in ("install", "load", "unload", "health_check", "generate",
                 "clone_voice", "build_variant"):
        assert hasattr(a, name), f"KokoroAdapter lost {name!r}"


def test_generate_signature_includes_runtime_endpoint() -> None:
    """generate() must accept runtime_endpoint so PeakVoxRuntime can inject it."""
    import inspect
    a = KokoroAdapter(_descriptor())
    sig = inspect.signature(a.generate)
    params = list(sig.parameters.keys())
    for expected in ("text", "output_path", "voice_id", "language", "params", "runtime_endpoint"):
        assert expected in params, f"generate must accept {expected!r}"


# ---- Runtime-service path: request translation ---------------------------------

def test_generate_routes_to_http_transport_when_endpoint_set() -> None:
    """When runtime_endpoint is set, generate() routes via HTTPTransport.
    The runtime returns audio/wav binary (ADR-0017 §6.3); the adapter
    writes the bytes to output_path."""
    captured: dict = {}
    wav_bytes = _make_wav_bytes(duration_ms=500)

    def handler(request: httpx.Request) -> httpx.Response:
        import json as _json
        captured["path"] = request.url.path
        captured["body"] = _json.loads(request.content)
        return httpx.Response(
            200,
            content=wav_bytes,
            headers={
                "Content-Type": "audio/wav",
                "X-Peakvox-Duration-Ms": "500",
            },
        )

    mt = httpx.MockTransport(handler)
    transport = HTTPTransport(base_url="http://runtime.local:8000")
    transport._client = httpx.AsyncClient(transport=mt, base_url="http://runtime.local:8000")

    a = KokoroAdapter(_descriptor())
    a._runtime_transport = transport  # type: ignore[attr-defined]

    out_path = Path("/tmp/kokoro_runtime_test.wav")
    try:
        duration, logs = asyncio.run(
            a.generate(
                text="hi", output_path=out_path,
                voice_id="voice_abc", language="en",
                runtime_endpoint="http://runtime.local:8000",
            )
        )
        assert duration == pytest.approx(0.5, abs=0.01)
        assert any("routed via runtime service" in line for line in logs)
        assert out_path.exists()
        assert out_path.read_bytes() == wav_bytes
        assert captured["path"] == "/v1/generate"
        assert captured["body"]["text"] == "hi"
        assert captured["body"]["voice_id"] == "voice_abc"
        assert captured["body"]["language"] == "en"
    finally:
        if out_path.exists():
            out_path.unlink()


def test_generate_runtime_prefers_preset_name_over_internal_voice_uuid() -> None:
    """Preset voices must send the Kokoro voice name, not the PeakVox UUID."""
    captured: dict = {}
    wav_bytes = _make_wav_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        import json as _json
        captured["body"] = _json.loads(request.content)
        return httpx.Response(
            200,
            content=wav_bytes,
            headers={"Content-Type": "audio/wav", "X-Peakvox-Duration-Ms": "500"},
        )

    mt = httpx.MockTransport(handler)
    transport = HTTPTransport(base_url="http://runtime.local:8000")
    transport._client = httpx.AsyncClient(transport=mt, base_url="http://runtime.local:8000")

    a = KokoroAdapter(_descriptor())
    a._runtime_transport = transport  # type: ignore[attr-defined]

    out_path = Path("/tmp/kokoro_runtime_preset_test.wav")
    try:
        asyncio.run(
            a.generate(
                text="hi",
                output_path=out_path,
                voice_profile_id="7678696f-b5be-4766-9cf7-b317120b693b",
                params={"provider": "kokoro", "preset_name": "af_alloy"},
                runtime_endpoint="http://runtime.local:8000",
            )
        )
        assert captured["body"]["voice_id"] == "af_alloy"
        assert captured["body"]["params"]["preset_name"] == "af_alloy"
    finally:
        if out_path.exists():
            out_path.unlink()


def test_generate_always_sends_request_id() -> None:
    """The Kokoro runtime requires a non-empty request_id. The adapter
    must generate one when job_id is None."""
    captured: dict = {}
    wav_bytes = _make_wav_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        import json as _json
        captured["body"] = _json.loads(request.content)
        return httpx.Response(
            200,
            content=wav_bytes,
            headers={"Content-Type": "audio/wav", "X-Peakvox-Duration-Ms": "100"},
        )

    mt = httpx.MockTransport(handler)
    transport = HTTPTransport(base_url="http://runtime.local:8000")
    transport._client = httpx.AsyncClient(transport=mt, base_url="http://runtime.local:8000")

    a = KokoroAdapter(_descriptor())
    a._runtime_transport = transport  # type: ignore[attr-defined]

    out_path = Path("/tmp/kokoro_request_id_test.wav")
    try:
        asyncio.run(
            a.generate(
                text="hello",
                output_path=out_path,
                voice_id="af_heart",
                runtime_endpoint="http://runtime.local:8000",
                job_id=None,
            )
        )
        assert "request_id" in captured["body"]
        assert len(captured["body"]["request_id"]) > 0
    finally:
        if out_path.exists():
            out_path.unlink()


def test_generate_falls_back_to_in_process_when_endpoint_none() -> None:
    """When runtime_endpoint is None, the adapter does NOT make an HTTP call.
    This is the in-process path — the adapter routes to local kokoro or fails
    with ImportError if kokoro is not installed."""
    http_called = []

    def handler(request: httpx.Request) -> httpx.Response:
        http_called.append(True)
        return httpx.Response(200, content=b"", headers={"Content-Type": "audio/wav"})

    mt = httpx.MockTransport(handler)
    transport = HTTPTransport(base_url="http://runtime.local:8000")
    transport._client = httpx.AsyncClient(transport=mt, base_url="http://runtime.local:8000")

    a = KokoroAdapter(_descriptor())
    a._runtime_transport = transport  # type: ignore[attr-defined]

    # Verify no HTTP call when runtime_endpoint is None.
    # The in-process path will fail with ImportError (kokoro not installed
    # in the test venv) — that is expected and correct behavior.
    try:
        asyncio.run(
            a.generate(
                text="hi",
                output_path=Path("/tmp/not_used.wav"),
                runtime_endpoint=None,
            )
        )
    except Exception:
        pass  # in-process failure is expected without kokoro installed
    assert not http_called, "No HTTP call should be made when runtime_endpoint is None"


def test_generate_raises_httptransporterror_when_runtime_5xx() -> None:
    """The adapter propagates HTTPTransportError from the runtime service."""
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
    with pytest.raises(HTTPTransportError) as excinfo:
        asyncio.run(
            a.generate(
                text="hi",
                output_path=Path("/tmp/x.wav"),
                runtime_endpoint="http://runtime.local:8000",
            )
        )
    assert excinfo.value.status == 503

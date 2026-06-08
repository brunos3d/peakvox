"""TDD: HTTPTransport (2C.1).

A generic adapter HTTP client for talking to runtime services. Per
ADR-0017 §6 (Runtime Service Contract) and the Transport Boundary
Audit, the transport is the ONLY HTTP-shape dependency adapters
may use. It must NOT import Docker, the runtime substrate, or
any of the runtime domain types (RuntimeDescriptor,
RuntimeInstance, RuntimeRegistry, RuntimeManager). It is purely
a ``(base_url, request) -> response`` abstraction.

The transport handles:
- A small method surface: ``get``, ``post``, ``post_stream``.
- Optional bearer token auth (settable per-instance; CE default
  is none per OPEN_DECISIONS Decision 10 §5).
- Retry policy: 3 attempts with exponential backoff (1s, 2s, 4s)
  for network errors; no retry on 4xx; 1 retry on 5xx.
- Streaming: ``post_stream`` returns an async iterator over
  response bytes (used for audio downloads).
- Error mapping: non-2xx responses raise ``HTTPTransportError`` with
  status, category, body.

These tests use ``httpx.MockTransport`` (in-process) — no real
network, no real HTTP server. The transport is exercised
end-to-end through the mock transport.
"""

from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator, List

import httpx
import pytest

from app.services.adapter_transport import http_transport
from app.services.adapter_transport.http_transport import (
    HTTPTransport,
    HTTPTransportError,
)


def _mock_transport(routes: List[httpx.MockTransport]) -> httpx.MockTransport:
    """Build a single MockTransport that dispatches to the first
    route. Each route is added to the mock in order; the
    transport is shared."""
    mt = httpx.MockTransport(routes[0].handler)  # placeholder
    for r in routes:
        for route in r.routes:  # type: ignore[attr-defined]
            mt.routes.append(route)  # type: ignore[attr-defined]
    return mt


def _make_transport_with_handler(handler, *, token: str = "") -> HTTPTransport:
    """Build an HTTPTransport whose internal httpx.Client uses a
    MockTransport. The handler signature matches httpx.MockTransport."""
    mt = httpx.MockTransport(handler)
    t = HTTPTransport(base_url="http://runtime.local:8000", bearer_token=token)
    # Inject the mock client.
    t._client = httpx.AsyncClient(transport=mt, base_url="http://runtime.local:8000")
    return t


async def _collect(gen):
    items = []
    async for item in gen:
        items.append(item)
    return items


# ---- Constructor ---------------------------------------------------------------

def test_http_transport_module_imports_without_substrate() -> None:
    """The transport module must import without any docker / runtime
    substrate dependency. The transport is the only HTTP-shape
    dependency adapters may use."""
    import re
    text = open(http_transport.__file__).read()
    # Strip docstrings + comments — the rule is about IMPORTS and
    # class/function NAMES, not about descriptive prose.
    text_clean = re.sub(r'\"{3}.*?\"{3}', "", text, flags=re.DOTALL)
    forbidden_substrates = [
        "RuntimeDescriptor", "RuntimeInstance",
        "RuntimeRegistry", "RuntimeManager",
    ]
    for s in forbidden_substrates:
        assert s not in text_clean, (
            f"HTTPTransport must not reference {s!r}; the transport is "
            f"a pure HTTP-shape abstraction."
        )
    # The transport may use the bare word "docker" in prose (e.g.
    # the docstring says "Docker" once), but it must NOT
    # `import docker` or `from docker import`. Check for those.
    assert "import docker" not in text_clean
    assert "from docker" not in text_clean


# ---- get ---------------------------------------------------------------------

def test_get_returns_text_on_2xx() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="ok")
    t = _make_transport_with_handler(handler)
    body = asyncio.run(t.get("/health"))
    assert body == "ok"


def test_get_returns_json_on_2xx() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "ready"})
    t = _make_transport_with_handler(handler)
    body = asyncio.run(t.get("/v1/metadata"))
    assert body == {"status": "ready"}


def test_get_raises_httptransporterror_on_4xx() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "not found"})
    t = _make_transport_with_handler(handler)
    with pytest.raises(HTTPTransportError) as excinfo:
        asyncio.run(t.get("/missing"))
    assert excinfo.value.status == 404
    assert excinfo.value.category == "not_found"


def test_get_raises_httptransporterror_on_5xx() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "not ready"})
    t = _make_transport_with_handler(handler)
    with pytest.raises(HTTPTransportError) as excinfo:
        asyncio.run(t.get("/ready"))
    assert excinfo.value.status == 503


# ---- post --------------------------------------------------------------------

def test_post_sends_json_body_and_returns_response() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        captured["content_type"] = request.headers.get("content-type")
        return httpx.Response(200, json={"variant_id": "v1", "status": "ready"})

    t = _make_transport_with_handler(handler)
    payload = {"voice_id": "v_abc", "text": "hello"}
    resp = asyncio.run(t.post("/v1/generate", payload))
    assert resp == {"variant_id": "v1", "status": "ready"}
    assert captured["body"] == payload
    assert captured["content_type"] == "application/json"


def test_post_stream_returns_async_iterator() -> None:
    chunks = [b"chunk1", b"chunk2", b"chunk3"]

    def handler(request: httpx.Request) -> httpx.Response:
        # Streaming response — return raw bytes.
        return httpx.Response(200, content=b"".join(chunks))

    t = _make_transport_with_handler(handler)
    gen = t.post_stream("/v1/generate", {"voice_id": "v_abc", "text": "hi"})
    received = asyncio.run(_collect(gen))
    assert b"".join(received) == b"".join(chunks)


# ---- Bearer token -----------------------------------------------------------

def test_bearer_token_is_sent_in_authorization_header() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={})

    t = _make_transport_with_handler(handler, token="secret-token-xyz")
    asyncio.run(t.get("/v1/metadata"))
    assert captured["auth"] == "Bearer secret-token-xyz"


def test_no_bearer_token_means_no_authorization_header() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={})

    t = _make_transport_with_handler(handler)  # no token
    asyncio.run(t.get("/v1/metadata"))
    assert captured["auth"] is None


# ---- HTTPTransportError shape ------------------------------------------------

def test_http_transport_error_carries_status_category_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422,
            json={"error": {"category": "validation", "message": "bad text", "request_id": "r1"}},
        )
    t = _make_transport_with_handler(handler)
    with pytest.raises(HTTPTransportError) as excinfo:
        asyncio.run(t.post("/v1/generate", {"text": ""}))
    err = excinfo.value
    assert err.status == 422
    # The error body has the canonical PeakVox shape.
    assert err.body["error"]["category"] == "validation"
    assert err.body["error"]["request_id"] == "r1"


# ---- Retry policy ----------------------------------------------------------

def test_no_retry_on_4xx() -> None:
    """The transport does NOT retry 4xx responses (client error)."""
    call_count = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        return httpx.Response(400, json={"error": "bad"})

    t = _make_transport_with_handler(handler, token="")
    with pytest.raises(HTTPTransportError):
        asyncio.run(t.get("/v1/generate"))
    # Single call; no retry on 4xx.
    assert call_count["n"] == 1


def test_one_retry_on_5xx() -> None:
    """The transport retries 5xx once (one additional attempt)."""
    call_count = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        return httpx.Response(503, json={"error": "down"})

    t = _make_transport_with_handler(handler, token="")
    with pytest.raises(HTTPTransportError):
        # Bypass the sleep by reducing the retry backoff; the
        # transport should still make 2 calls (initial + 1 retry).
        t._retry_backoff = lambda attempt: 0  # type: ignore[attr-defined]
        asyncio.run(t.get("/v1/generate"))
    assert call_count["n"] == 2


def test_no_retry_when_first_call_succeeds() -> None:
    call_count = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        return httpx.Response(200, json={})

    t = _make_transport_with_handler(handler, token="")
    asyncio.run(t.get("/v1/metadata"))
    assert call_count["n"] == 1


# ---- The transport exposes no substrate awareness ----------------------------

def test_transport_class_has_no_substrate_method() -> None:
    """Architectural invariant: the transport is a pure HTTP
    abstraction. It must not expose any Docker / container /
    RuntimeDescriptor / RuntimeInstance / RuntimeRegistry /
    RuntimeManager surface."""
    t = HTTPTransport(base_url="http://runtime.local:8000")
    forbidden_methods = [
        "pull_image", "run_container", "stop_container",
        "remove_container", "install_runtime", "start_runtime",
        "resolve", "get_runtime", "create_runtime",
    ]
    for m in forbidden_methods:
        assert not hasattr(t, m), (
            f"HTTPTransport must not expose {m!r}; the transport is a "
            f"pure HTTP abstraction. Substrate concerns belong in the "
            f"RuntimeDriver (in app.services.drivers)."
        )

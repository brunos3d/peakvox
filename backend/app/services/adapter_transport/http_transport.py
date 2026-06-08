"""HTTPTransport (Phase 2C, 2C.1) — generic adapter HTTP client.

A pure ``(base_url, request) -> response`` abstraction that
adapters use to talk to runtime services. The transport is the
ONLY HTTP-shape dependency adapters may use (per the Transport
Boundary Audit).

The transport handles:
- A small method surface: ``get``, ``post``, ``post_stream``.
- Optional bearer token auth (settable per-instance; CE default
  is none per OPEN_DECISIONS Decision 10 §5).
- Retry policy: 1 retry on 5xx; no retry on 4xx; 3 attempts with
  exponential backoff (1s, 2s, 4s) for network errors.
- Streaming: ``post_stream`` returns an async iterator over
  response bytes (used for audio downloads).
- Error mapping: non-2xx responses raise ``HTTPTransportError``
  with status, category, and the canonical PeakVox error body.

Architectural invariants (per the Transport Boundary Audit):
- The transport MUST NOT import Docker.
- The transport MUST NOT reference RuntimeDescriptor /
  RuntimeInstance / RuntimeRegistry / RuntimeManager.
- The transport MUST NOT expose any substrate or runtime domain
  method (no ``pull_image``, ``run_container``, ``install``,
  ``start``, ``resolve``, etc.).
- The transport MUST be a pure HTTP abstraction.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, AsyncIterator, Callable, Optional

import httpx


class HTTPTransportError(Exception):
    """Raised when the transport receives a non-2xx response.

    The body is the canonical PeakVox error envelope
    ``{"error": {"category", "message", "request_id", "timestamp"}}``
    per ADR-0017 §6.6. The ``status`` is the HTTP status code.
    """

    def __init__(self, status: int, body: Any, message: str = "") -> None:
        self.status = status
        self.body = body
        # Extract the canonical message and category from the
        # envelope. ``category`` is a property so callers can
        # read it directly (``err.category``) without diving
        # into the body dict.
        envelope = body.get("error") if isinstance(body, dict) else None
        if isinstance(envelope, dict):
            self._category = envelope.get("category") or _category_for_status(status)
            self._envelope_message = envelope.get("message")
        else:
            self._category = _category_for_status(status)
            self._envelope_message = None
        super().__init__(self._envelope_message or message or f"HTTP {status}")

    @property
    def category(self) -> str:
        return self._category

    @property
    def message(self) -> str:
        return self._envelope_message or f"HTTP {self.status}"


def _category_for_status(status: int) -> str:
    """Map an HTTP status code to a coarse category name."""
    if status == 0:
        return "network"
    if 400 <= status < 500:
        if status == 401:
            return "unauthorized"
        if status == 403:
            return "forbidden"
        if status == 404:
            return "not_found"
        if status == 409:
            return "conflict"
        if status == 422:
            return "validation"
        return "client_error"
    if 500 <= status < 600:
        if status == 503:
            return "not_ready"
        return "substrate"
    return "unknown"


class HTTPTransport:
    """Generic adapter HTTP client (Phase 2C, 2C.1).

    The transport is the ONLY HTTP-shape dependency adapters may
    use. It depends only on ``httpx``; it has no awareness of
    Docker, containers, the runtime registry, the runtime
    manager, the runtime descriptor, or the runtime instance.
    """

    def __init__(
        self,
        *,
        base_url: str,
        bearer_token: str = "",
        timeout_seconds: float = 30.0,
        max_retries_5xx: int = 1,
        max_retries_network: int = 3,
        retry_backoff: Optional[Callable[[int], float]] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        # The base URL is the runtime service's URL. In CE it is
        # typically http://<host>:<port> where the host is the
        # service DNS name inside a Docker network; in Cloud it
        # is the service URL.
        self._base_url = base_url.rstrip("/")
        self._bearer_token = bearer_token
        self._timeout_seconds = timeout_seconds
        self._max_retries_5xx = max_retries_5xx
        self._max_retries_network = max_retries_network
        # The retry backoff is injectable for tests. Default: 1s,
        # 2s, 4s.
        self._retry_backoff: Callable[[int], float] = retry_backoff or (
            lambda attempt: 1.0 * (2 ** (attempt - 1))
        )
        # The httpx client is injectable for tests. Default: a
        # new AsyncClient with the base URL.
        self._client = client or httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout_seconds,
        )

    @property
    def base_url(self) -> str:
        return self._base_url

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self._bearer_token:
            headers["Authorization"] = f"Bearer {self._bearer_token}"
        return headers

    async def _do_request(
        self,
        method: str,
        path: str,
        *,
        body: Optional[dict] = None,
        stream: bool = False,
    ) -> httpx.Response:
        # Retry policy:
        #   - 1 retry on 5xx (server transient)
        #   - 3 attempts on network errors (1s, 2s, 4s backoff)
        #   - 0 retries on 4xx (client error)
        attempts_5xx = 0
        attempts_network = 0
        while True:
            try:
                if stream:
                    request = self._client.build_request(
                        method, path, json=body, headers=self._headers()
                    )
                    response = await self._client.send(request, stream=True)
                else:
                    response = await self._client.request(
                        method, path, json=body, headers=self._headers()
                    )
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as exc:
                attempts_network += 1
                if attempts_network > self._max_retries_network:
                    raise HTTPTransportError(
                        0, {"error": {"category": "network", "message": str(exc)}},
                    ) from exc
                await asyncio.sleep(self._retry_backoff(attempts_network))
                continue

            if 500 <= response.status_code < 600:
                attempts_5xx += 1
                if attempts_5xx > self._max_retries_5xx:
                    return response
                await asyncio.sleep(self._retry_backoff(attempts_5xx))
                continue

            return response

    async def get(self, path: str) -> Any:
        response = await self._do_request("GET", path)
        if not (200 <= response.status_code < 300):
            body = self._safe_json(response)
            raise HTTPTransportError(response.status_code, body)
        if response.headers.get("content-type", "").startswith("application/json"):
            return response.json()
        return response.text

    async def post(self, path: str, body: dict) -> Any:
        response = await self._do_request("POST", path, body=body)
        if not (200 <= response.status_code < 300):
            body_json = self._safe_json(response)
            raise HTTPTransportError(response.status_code, body_json)
        if response.headers.get("content-type", "").startswith("application/json"):
            return response.json()
        return response.text

    async def post_stream(self, path: str, body: dict) -> AsyncIterator[bytes]:
        """Stream the response body. Yields raw bytes (audio data
        or server-sent events, depending on the runtime service)."""
        response = await self._do_request("POST", path, body=body, stream=True)
        if not (200 <= response.status_code < 300):
            body_json = self._safe_json(response)
            await response.aclose()
            raise HTTPTransportError(response.status_code, body_json)
        try:
            async for chunk in response.aiter_bytes():
                yield chunk
        finally:
            await response.aclose()

    @staticmethod
    def _safe_json(response: httpx.Response) -> Any:
        try:
            return response.json()
        except Exception:
            return {"error": {"category": "unknown", "message": response.text}}

    async def aclose(self) -> None:
        """Close the underlying httpx client. Idempotent."""
        await self._client.aclose()

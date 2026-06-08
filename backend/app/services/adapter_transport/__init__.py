"""Adapter transport package — HTTP client abstraction for runtime services.

Per the Transport Boundary Audit (Phase 2C), adapters communicate
with runtime services ONLY through this package. Adapters must
NOT import Docker, the runtime substrate, or any of the runtime
domain types (RuntimeDescriptor, RuntimeInstance, RuntimeRegistry,
RuntimeManager).

The transport is a pure ``(base_url, request) -> response``
abstraction. It depends on ``httpx`` (already a transitive
dependency of ``fastapi.testclient``). It is intentionally
substrate-free: no model code, no runtime domain types, no
substrate imports.
"""

from app.services.adapter_transport.http_transport import (
    HTTPTransport,
    HTTPTransportError,
)

__all__ = ["HTTPTransport", "HTTPTransportError"]

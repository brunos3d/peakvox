"""DockerRuntimeDriver (Phase 2B, 2B.1-2B.4).

Per ADR-0017 §5, this is the first concrete implementation of the
RuntimeDriver Protocol. It wraps the Docker Engine API via the
docker SDK.

ARCHITECTURE-REVIEW GUARDRAIL
-----------------------------
This module is the only component in the backend allowed to import
the docker SDK. The `import docker` is LAZY (inside
``_ensure_client()``) so the module is importable in environments
without the SDK — notably the test venv. Tests use a
``_MockDockerClient`` that has the same surface; the driver does
not know whether its client is real or mocked.

The driver does NOT:
  - Talk to Kubernetes, Podman, or any other substrate.
  - Run on a remote Docker host (Phase 2B is local Docker only;
    remote hosts are a future ADR).
  - Manage Docker networks beyond the runtime container's own
    (custom networks are a future ADR).
  - Run containers in privileged mode.
  - Talk to the Runtime Service Contract endpoints directly; the
    service contract is the adapter's role in Phase 2C+. The
    driver only probes substrate-internal ``/ready`` and ``/health``
    for liveness/readiness.
"""

from __future__ import annotations

import asyncio
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Callable, Optional

from app.services.runtime_driver import RuntimeDriver  # noqa: F401  (re-exported)
from app.services.runtime_errors import (
    ImagePullError,
    RuntimeDriverError,
    RuntimeHealthFailed,
    RuntimeNotFound,
    SubstrateError,
)
from app.services.runtime_instance import (
    HealthState,
    ImageIdentity,
    RuntimeInstance,
    RuntimeState,
)
from app.services.runtime_types import HealthReport, Liveness, Metrics, Readiness, RuntimeDescriptor


__all__ = [
    "DockerRuntimeDriver",
    "RuntimeDriverError",
    "RuntimeNotFound",
    "ImagePullError",
    "SubstrateError",
    "RuntimeHealthFailed",
    "RuntimeInstance",
    "RuntimeState",
    "HealthState",
    "HealthReport",
    "Metrics",
    "Liveness",
    "Readiness",
    "ImageIdentity",
]


# ---- Module-level helpers (no docker imports) ----------------------------------

def _container_name(runtime_id: str) -> str:
    return f"peakvox-runtime-{runtime_id}"


def _is_image_not_found(exc: BaseException) -> bool:
    """Detect a docker 'image not found' error without importing docker."""
    name = exc.__class__.__name__
    if name == "ImageNotFound":
        return True
    # Some SDKs raise generic NotFound on missing image pull.
    if name.endswith("NotFound") and "container" not in str(exc).lower():
        return True
    return False


def _is_image_auth_failed(exc: BaseException) -> bool:
    return "AuthorizationFailed" in exc.__class__.__name__


def _is_daemon_error(exc: BaseException) -> bool:
    name = exc.__class__.__name__
    return name in ("APIError", "DockerException") or "APIError" in name


def _is_container_not_found(exc: BaseException) -> bool:
    # Match docker.errors.NotFound and any test mock that ends in
    # "NotFound" (e.g. _MockNotFound).
    return exc.__class__.__name__.endswith("NotFound")


def _probe_ready(
    host: str,
    port: int,
    path: str = "/ready",
    timeout: float = 3.0,
) -> bool:
    """Synchronous GET to ``http://<host>:<port><path>``.

    Returns True on HTTP 200, False on any other status or any
    network/timeout error. The test venv does not have a real
    container to probe; tests patch this function at the module
    level.
    """
    url = f"http://{host}:{port}{path}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return int(resp.status) == 200
    except (urllib.error.URLError, urllib.error.HTTPError, ConnectionError, TimeoutError, OSError):
        return False


# ---- The driver --------------------------------------------------------------

class DockerRuntimeDriver:
    """First concrete RuntimeDriver (ADR-0017 §5).

    Implements the RuntimeDriver Protocol against the Docker Engine
    API. The ``docker`` import is lazy (inside ``_ensure_client()``)
    so the module is importable without the SDK installed.
    """

    def __init__(
        self,
        *,
        client: Any = None,
        host: str = "localhost",
        default_install_timeout_s: float = 300.0,
        default_start_timeout_s: float = 60.0,
        default_stop_timeout_s: float = 30.0,
        probe_ready: Optional[Callable[..., bool]] = None,
    ) -> None:
        # If client is provided, use it (test path). Otherwise lazy-
        # create on first use so the module is importable without
        # the SDK.
        self._client = client
        self._host = host
        self._default_install_timeout_s = default_install_timeout_s
        self._default_start_timeout_s = default_start_timeout_s
        self._default_stop_timeout_s = default_stop_timeout_s
        # Optional probe override (test path). Default: the module-
        # level _probe_ready which uses urllib.
        self._probe_ready = probe_ready or _probe_ready
        # Per-runtime descriptor cache: install_runtime stores the
        # descriptor here so start_runtime can recover the runtime
        # config (port, image, env) without round-tripping through
        # container labels. Cleared by remove_runtime.
        self._descriptor_cache: dict[str, RuntimeDescriptor] = {}

    # ---- Docker SDK access (lazy) -------------------------------------------

    def _ensure_client(self) -> Any:
        if self._client is None:
            # Lazy import; the test venv does not have the SDK.
            import docker  # type: ignore[import-not-found]
            self._client = docker.from_env()
        return self._client

    # ---- Internal helpers --------------------------------------------------

    def _image_identity_from_descriptor(self, desc: RuntimeDescriptor) -> ImageIdentity:
        return ImageIdentity(
            repository=desc.spec.image.repository,
            tag=desc.spec.image.tag,
            digest=desc.spec.image.digest,
        )

    def _labels(self, desc: RuntimeDescriptor) -> dict:
        return {
            "peakvox.runtime.id": desc.metadata.id,
            "peakvox.runtime.model_id": desc.spec.model_binding.model_id,
            "peakvox.runtime.provider": desc.metadata.provider,
            "peakvox.runtime.version": desc.metadata.version,
            "peakvox.edition": ",".join(desc.metadata.edition),
        }

    def _environment(self, desc: RuntimeDescriptor) -> dict:
        return {
            "PEAKVOX_RUNTIME_ID": desc.metadata.id,
            "PEAKVOX_RUNTIME_PROVIDER": desc.metadata.provider,
            "PEAKVOX_RUNTIME_VERSION": desc.metadata.version,
        }

    def _restart_policy_arg(self, policy: str) -> dict:
        # docker SDK expects {"Name": "on-failure"|"always"|"no"}.
        return {"Name": policy}

    def _port_bindings(self, port: int) -> dict:
        # Bind container port to a host port (same port for simplicity).
        return {f"{port}/tcp": port}

    def _image_ref(self, desc: RuntimeDescriptor) -> str:
        return f"{desc.spec.image.repository}:{desc.spec.image.tag}"

    def _container(self, runtime_id: str) -> Any:
        try:
            return self._ensure_client().containers.get(_container_name(runtime_id))
        except BaseException as exc:
            if _is_container_not_found(exc):
                raise RuntimeNotFound(runtime_id, "no container with this name") from exc
            raise

    def _translate_install_error(self, exc: BaseException, runtime_id: str) -> None:
        if _is_image_not_found(exc):
            raise ImagePullError(runtime_id, f"image not found: {exc}") from exc
        if _is_image_auth_failed(exc):
            raise ImagePullError(runtime_id, f"image auth failed: {exc}", cause=exc) from exc
        if _is_daemon_error(exc):
            raise SubstrateError(runtime_id, "docker", str(exc)) from exc
        raise SubstrateError(runtime_id, "docker", str(exc)) from exc

    def _wait_ready(
        self,
        runtime_id: str,
        host: str,
        port: int,
        readiness_path: str,
        start_timeout_s: float,
        health_interval_s: float,
        health_timeout_s: float,
    ) -> None:
        """Poll /ready until 200 or start_timeout_s elapses."""
        deadline = time.monotonic() + start_timeout_s
        while True:
            if self._probe_ready(host, port, readiness_path, health_timeout_s):
                return
            if time.monotonic() >= deadline:
                raise RuntimeHealthFailed(
                    runtime_id,
                    f"/ready did not return 200 within {start_timeout_s}s",
                )
            time.sleep(max(health_interval_s, 0.0))

    def _descriptor_for_runtime(self, runtime_id: str) -> RuntimeDescriptor:
        """Recover a minimal descriptor from the container's labels.

        In Phase 2B the driver does not own a registry; the
        descriptor is supplied by the manager via install_runtime.
        When the manager calls start_runtime without a prior
        install_runtime, we synthesize a minimal descriptor from
        the container's labels (set during install).
        """
        c = self._container(runtime_id)
        labels = c.labels
        repo = (c.image.split(":")[0] if ":" in c.image else c.image) if c.image else runtime_id
        tag = c.image.split(":", 1)[1] if c.image and ":" in c.image else "latest"
        return RuntimeDescriptor.model_validate({
            "api_version": "peakvox.io/v1",
            "kind": "Runtime",
            "metadata": {
                "id": runtime_id,
                "name": labels.get("peakvox.runtime.id", runtime_id),
                "description": "",
                "provider": labels.get("peakvox.runtime.provider", "unknown"),
                "version": labels.get("peakvox.runtime.version", "0.0.0"),
                "edition": (labels.get("peakvox.edition") or "ce").split(","),
                "labels": {},
            },
            "spec": {
                "runtime_type": "docker",
                "image": {"repository": repo, "tag": tag},
                "service": {"protocol": "http", "port": 8000},
                "capabilities": ["tts"],
                "requirements": {"gpu": "none", "edition": ["ce"]},
                "model_binding": {
                    "model_id": labels.get("peakvox.runtime.model_id", runtime_id),
                    "is_default": False,
                    "priority": 100,
                },
            },
        })

    def _port_for_container(self, c: Any) -> int:
        try:
            attrs = self._ensure_client().api.inspect_container(c.name)
            ports = attrs.get("NetworkSettings", {}).get("Ports", {})
            for key, bindings in ports.items():
                if key.endswith("/tcp") and bindings:
                    return int(bindings[0].get("HostPort", 0))
            return 0
        except Exception:
            return 0

    # ---- The 10 operations --------------------------------------------------

    async def install_runtime(
        self, runtime_id: str, descriptor: RuntimeDescriptor
    ) -> RuntimeInstance:
        client = self._ensure_client()
        image = descriptor.spec.image
        try:
            if image.digest:
                client.images.pull(f"{image.repository}@{image.digest}")
            else:
                client.images.pull(image.repository, tag=image.tag)
        except BaseException as exc:
            self._translate_install_error(exc, runtime_id)
        # Cache the descriptor for later start_runtime; the manager
        # always calls install before start, so the cache is hot
        # at start time.
        self._descriptor_cache[runtime_id] = descriptor
        return RuntimeInstance(
            runtime_id=runtime_id,
            state=RuntimeState.INSTALLED,
            host="",
            port=0,
            image_identity=self._image_identity_from_descriptor(descriptor),
            started_at=None,
            last_health_at=None,
            health_state=HealthState.UNKNOWN,
        )

    async def update_runtime(
        self, runtime_id: str, descriptor: RuntimeDescriptor
    ) -> RuntimeInstance:
        # Stop if active; re-pull the new image; leave in Installed.
        try:
            c = self._container(runtime_id)
            c.stop(timeout=int(self._default_stop_timeout_s))
        except RuntimeNotFound:
            pass
        return await self.install_runtime(runtime_id, descriptor)

    async def remove_runtime(self, runtime_id: str) -> None:
        client = self._ensure_client()
        try:
            c = self._container(runtime_id)
            c.stop(timeout=int(self._default_stop_timeout_s))
            c.remove(force=True)
        except RuntimeNotFound:
            pass
        # Remove the image too (best effort; the image may be shared).
        try:
            c = self._container(runtime_id)
            if c.image:
                client.images.remove(c.image, force=True)
        except BaseException:
            pass
        # Clear the descriptor cache; the runtime is fully removed.
        self._descriptor_cache.pop(runtime_id, None)

    async def start_runtime(self, runtime_id: str) -> RuntimeInstance:
        client = self._ensure_client()
        # Recover the descriptor from the install cache. The manager
        # always calls install before start; direct driver calls
        # without prior install fail with RuntimeNotFound.
        desc = self._descriptor_cache.get(runtime_id)
        if desc is None:
            raise RuntimeNotFound(
                runtime_id, "no descriptor cached; install first"
            )
        # If a container with the same name already exists, remove it.
        try:
            existing = self._container(runtime_id)
            existing.remove(force=True)
        except RuntimeNotFound:
            pass
        port = desc.spec.service.port
        try:
            client.containers.run(
                image=self._image_ref(desc),
                detach=True,
                name=_container_name(runtime_id),
                ports=self._port_bindings(port),
                environment=self._environment(desc),
                labels=self._labels(desc),
                restart_policy=self._restart_policy_arg(desc.spec.lifecycle.restart_policy),
            )
        except BaseException as exc:
            self._translate_install_error(exc, runtime_id)
            raise  # unreachable; the helper always raises
        # Wait for /ready. The probe is synchronous; run it in a
        # thread to avoid blocking the event loop on long waits.
        await asyncio.to_thread(
            self._wait_ready,
            runtime_id,
            self._host,
            port,
            desc.spec.service.readiness_path,
            float(desc.spec.lifecycle.start_timeout_seconds),
            float(desc.spec.lifecycle.health_interval_seconds),
            float(desc.spec.lifecycle.health_timeout_seconds),
        )
        return RuntimeInstance(
            runtime_id=runtime_id,
            state=RuntimeState.ACTIVE,
            host=self._host,
            port=port,
            image_identity=self._image_identity_from_descriptor(desc),
            started_at=datetime.now(timezone.utc),
            last_health_at=datetime.now(timezone.utc),
            health_state=HealthState.READY,
        )

    async def stop_runtime(self, runtime_id: str) -> None:
        c = self._container(runtime_id)
        c.stop(timeout=int(self._default_stop_timeout_s))

    async def restart_runtime(self, runtime_id: str) -> RuntimeInstance:
        await self.stop_runtime(runtime_id)
        return await self.start_runtime(runtime_id)

    async def runtime_status(self, runtime_id: str) -> RuntimeInstance:
        c = self._container(runtime_id)
        c.reload()
        is_running = c.status == "running"
        return RuntimeInstance(
            runtime_id=runtime_id,
            state=RuntimeState.ACTIVE if is_running else RuntimeState.STOPPED,
            host=self._host,
            port=self._port_for_container(c),
            image_identity=ImageIdentity(
                repository=c.image.split(":")[0] if c.image and ":" in c.image else (c.image or ""),
                tag=c.image.split(":", 1)[1] if c.image and ":" in c.image else "",
                digest=None,
            ),
            started_at=None,
            last_health_at=None,
            health_state=HealthState.READY if is_running else HealthState.UNKNOWN,
        )

    async def runtime_logs(
        self, runtime_id: str, since: Optional[datetime] = None
    ) -> AsyncIterator[str]:
        c = self._container(runtime_id)
        # Single batch in 2B; the manager caches this. We yield all
        # available lines from the iterator; the iterator itself
        # terminates when Docker's stream closes.
        for raw in c.logs(stream=True, follow=False):
            line = raw.decode() if isinstance(raw, bytes) else str(raw)
            line = line.rstrip("\n")
            if line:
                yield line

    async def runtime_health(self, runtime_id: str) -> HealthReport:
        c = self._container(runtime_id)
        try:
            attrs = self._ensure_client().api.inspect_container(c.name)
            running = bool(attrs.get("State", {}).get("Running", False))
        except Exception:
            running = False
        port = self._port_for_container(c)
        if port == 0:
            try:
                port = self._descriptor_for_runtime(runtime_id).spec.service.port
            except RuntimeNotFound:
                port = 0
        liveness = Liveness.ALIVE if running else Liveness.DEAD
        if running and port:
            ready = self._probe_ready(self._host, port, "/ready", 3.0)
            readiness = Readiness.READY if ready else Readiness.NOT_READY
        else:
            readiness = Readiness.UNKNOWN
        return HealthReport(
            runtime_id=runtime_id,
            liveness=liveness,
            readiness=readiness,
            last_error=None,
            checked_at=datetime.now(timezone.utc),
        )

    async def runtime_metrics(self, runtime_id: str) -> Metrics:
        # Phase 2B first version: stub returning empty Metrics. A
        # future ADR may wire actual metrics (CPU, memory, network)
        # by parsing docker stats; in 2B the surface exists and the
        # body is intentionally empty.
        return Metrics()

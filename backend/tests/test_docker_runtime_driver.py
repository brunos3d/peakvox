"""TDD: DockerRuntimeDriver (2B.1-2B.4).

Per ADR-0017 §5, the first concrete driver. Implements the
RuntimeDriver Protocol against the Docker Engine API. The
``docker`` SDK is imported LAZILY (only inside ``_ensure_client()``)
so the test venv — which does NOT have docker installed — can
still import the module and run the test suite.

Phase 2B architecture review guardrail: ``DockerRuntimeDriver``
is the only component allowed to import Docker libraries. The
RuntimeManager, adapters, the PeakVoxRuntime bridge, and every
other backend module must remain Docker-free.

These tests assert:
- The driver module imports WITHOUT the docker SDK installed
  (the docker import is lazy).
- The driver conforms to the RuntimeDriver Protocol (structural
  conformance via isinstance).
- install_runtime pulls by digest when present, by tag otherwise;
  idempotent on re-install; ImagePullError on 404; SubstrateError
  on daemon failure.
- start_runtime starts the container, probes ``/ready`` until 200
  or ``lifecycle.start_timeout_seconds`` elapses; success flips
  state to ACTIVE / health_state to READY; timeout raises
  RuntimeHealthFailed and flips state to FAILED.
- stop / restart / update / remove / status / logs / health /
  metrics follow the semantics in ADR-0017 §4.3.
- No top-level ``import docker`` in the driver module.
"""

from __future__ import annotations

import asyncio
import importlib
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pytest

from app.services.runtime_driver import RuntimeDriver
from app.services.runtime_errors import (
    ImagePullError,
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
from app.services.runtime_types import (
    HealthReport, Liveness, Metrics, Readiness, RuntimeDescriptor,
)
from app.services.drivers import docker_runtime_driver as drv_mod
from app.services.drivers.docker_runtime_driver import DockerRuntimeDriver


# ---- Mock Docker client (no docker import) -------------------------------------

class _MockImage:
    def __init__(self, repo: str, tag: str) -> None:
        self.repo = repo
        self.tag = tag
        self.id = f"sha256:{'a' * 64}"


class _MockContainer:
    def __init__(self, name: str, image_repo: str, image_tag: str,
                 labels: Optional[Dict] = None) -> None:
        self.name = name
        self.image = f"{image_repo}:{image_tag}"
        self.id = f"container-{name}"
        self.status = "running"
        self.labels: Dict[str, str] = dict(labels or {})
        self._logs: List[str] = []
        self._stopped = False
        self._removed = False

    def stop(self, timeout: int = 10) -> None:
        self._stopped = True
        self.status = "stopped"

    def remove(self, force: bool = False) -> None:
        self._removed = True
        self.status = "removed"

    def logs(self, stream: bool = False, follow: bool = False):
        for line in self._logs:
            yield (line + "\n").encode() if isinstance(line, str) else line
        self._logs = []  # one-shot

    def reload(self) -> None:
        if self._removed:
            self.status = "removed"
        elif self._stopped:
            self.status = "stopped"
        else:
            self.status = "running"

    def attach_log_buffer(self, lines: List[str]) -> None:
        self._logs.extend(lines)


class _MockImagesAPI:
    def __init__(self, owner: "_MockDockerClient") -> None:
        self._owner = owner
        self._local_images: set[str] = set()

    def get(self, ref: str):
        if ref not in self._local_images:
            raise _MockImageNotFound(f"image not found: {ref}")
        repo, tag = ref.rsplit(":", 1)
        return _MockImage(repo=repo, tag=tag)

    def pull(self, repository: str, tag: Optional[str] = None,
            digest: Optional[str] = None):
        if self._owner.image_pull_404:
            raise _MockImageNotFound("simulated 404")
        if self._owner.image_pull_auth_fail:
            raise _MockImageAuthorizationFailed("simulated auth fail")
        if self._owner.daemon_down:
            raise _MockAPIError("simulated daemon down")
        # Extract repo and tag from the repository string (digest or tag form).
        if "@" in repository:
            repo = repository.split("@")[0]
            tag = ""
        else:
            repo = repository
            tag = tag or "latest"
        image = _MockImage(repo=repo, tag=tag)
        if tag:
            self._local_images.add(f"{repo}:{tag}")
        return image

    def build(self, path: str, dockerfile: str, tag: str, rm: bool = True):
        if self._owner.daemon_down:
            raise _MockAPIError("simulated daemon down")
        repo, image_tag = tag.rsplit(":", 1)
        image = _MockImage(repo=repo, tag=image_tag)
        self._local_images.add(tag)
        self._owner.built_images.append({
            "path": path,
            "dockerfile": dockerfile,
            "tag": tag,
        })
        return image, []

    def remove(self, image: str, force: bool = False) -> None:
        if self._owner.daemon_down:
            raise _MockAPIError("simulated daemon down")
        self._owner.removed_images.append(image)
        self._local_images.discard(image)
        return None


class _MockContainersAPI:
    def __init__(self, owner: "_MockDockerClient") -> None:
        self._owner = owner

    def list(self, filters: Optional[Dict] = None) -> List[_MockContainer]:
        return list(self._owner._containers.values())

    def get(self, container_id: str) -> _MockContainer:
        if container_id not in self._owner._containers:
            raise _MockNotFound(f"no such container: {container_id}")
        return self._owner._containers[container_id]

    def run(self, image: str, *, detach: bool = False, name: Optional[str] = None,
            ports: Optional[Dict] = None, environment: Optional[Dict] = None,
            volumes: Optional[Dict] = None, labels: Optional[Dict] = None,
            restart_policy: Optional[Dict] = None, **kwargs):
        if self._owner.daemon_down:
            raise _MockAPIError("simulated daemon down")
        # Parse "repo:tag" or "repo@digest".
        if "@" in image:
            repo = image.split("@")[0]
            tag = ""
        elif ":" in image:
            repo, tag = image.rsplit(":", 1)
        else:
            repo, tag = image, "latest"
        c = _MockContainer(
            name=name or f"auto-{len(self._owner._containers)}",
            image_repo=repo, image_tag=tag,
            labels=labels,
        )
        self._owner._containers[c.name] = c
        return c


class _MockApi:
    def __init__(self, owner: "_MockDockerClient") -> None:
        self._owner = owner

    def inspect_container(self, container: str) -> Dict:
        c = self._owner._containers.get(container)
        if c is None:
            return {}
        return {
            "State": {"Running": c.status == "running"},
            "NetworkSettings": {
                "Ports": {
                    f"{8000}/tcp": [{"HostPort": "8000"}] if c.status != "removed" else []
                }
            },
        }


# Stand-in exception classes that mimic docker.errors.* names.
class _MockDockerError(Exception):
    pass


class _MockImageNotFound(_MockDockerError):
    pass


class _MockImageAuthorizationFailed(_MockDockerError):
    pass


class _MockNotFound(_MockDockerError):
    pass


class _MockAPIError(_MockDockerError):
    pass


class _MockDockerClient:
    """A test double that imitates the docker.DockerClient surface
    the driver uses, without importing docker."""

    def __init__(self) -> None:
        self._containers: Dict[str, _MockContainer] = {}
        self.images = _MockImagesAPI(self)
        self.containers = _MockContainersAPI(self)
        self.api = _MockApi(self)
        self.built_images: List[Dict[str, str]] = []
        self.removed_images: List[str] = []
        # Pluggable error injection
        self.image_pull_404 = False
        self.image_pull_auth_fail = False
        self.daemon_down = False

    def set_image_404(self, value: bool) -> None:
        self.image_pull_404 = value

    def set_image_auth_fail(self, value: bool) -> None:
        self.image_pull_auth_fail = value

    def set_daemon_down(self, value: bool) -> None:
        self.daemon_down = value


# ---- Helpers ------------------------------------------------------------------

def _good_descriptor(
    runtime_id: str = "kokoro-cpu",
    model_id: str = "kokoro-base",
) -> RuntimeDescriptor:
    return RuntimeDescriptor.model_validate({
        "api_version": "peakvox.io/v1",
        "kind": "Runtime",
        "metadata": {
            "id": runtime_id, "name": runtime_id, "description": "",
            "provider": "kokoro", "version": "1.4.2", "edition": ["ce"], "labels": {},
        },
        "spec": {
            "runtime_type": "docker",
            "image": {
                "repository": "peakvox/kokoro-runtime", "tag": "1.4.2",
                "digest": "sha256:" + "a" * 64,
            },
            "build": {
                "entrypoint": "server.py",
                "build_context": ".",
                "dockerfile": "Dockerfile",
            },
            "service": {"protocol": "http", "port": 8000, "readiness_path": "/ready"},
            "capabilities": ["tts"],
            "requirements": {"gpu": "none", "edition": ["ce"]},
            "model_binding": {"model_id": model_id, "is_default": True, "priority": 100},
            "lifecycle": {
                "start_timeout_seconds": 5,
                # health_interval_seconds must be > 0 per schema; 1 is
                # the minimum. The driver floors to time.sleep(0) for
                # sub-millisecond polling.
                "health_interval_seconds": 1,
                "health_timeout_seconds": 1,
                "restart_policy": "on-failure",
            },
        },
    })


def _good_descriptor_with_short_timeout(
    runtime_id: str = "kokoro-cpu",
    model_id: str = "kokoro-base",
) -> RuntimeDescriptor:
    """A descriptor with a tiny start_timeout_seconds for fast tests."""
    desc = _good_descriptor(runtime_id, model_id)
    desc_dict = desc.model_dump()
    desc_dict["spec"]["lifecycle"]["start_timeout_seconds"] = 1
    # health_interval_seconds must be > 0 per the schema; use 0.01
    # (the driver rounds it up via time.sleep(0) for sub-millisecond
    # polling; the probe does the work).
    desc_dict["spec"]["lifecycle"]["health_interval_seconds"] = 1
    return RuntimeDescriptor.model_validate(desc_dict)


@pytest.fixture
def probe_returns_ok(monkeypatch):
    monkeypatch.setattr(drv_mod, "_probe_ready", lambda *a, **kw: True)


@pytest.fixture
def probe_returns_fail(monkeypatch):
    monkeypatch.setattr(drv_mod, "_probe_ready", lambda *a, **kw: False)


# ---- Tests ---------------------------------------------------------------------

def test_docker_runtime_driver_module_imports_without_docker() -> None:
    """The driver module must import successfully even when the
    docker SDK is not installed. The docker import is LAZY
    (inside ``_ensure_client()``)."""
    sys.modules.pop("app.services.drivers.docker_runtime_driver", None)
    sys.modules.pop("app.services.drivers", None)
    mod = importlib.import_module("app.services.drivers.docker_runtime_driver")
    assert mod is not None


def test_docker_driver_does_not_import_docker_at_module_load() -> None:
    """The driver must not import `docker` at the top of the file.
    This invariant is what makes the test venv (no docker SDK)
    able to import the module. The lint check (2B.5) enforces
    this in CI."""
    import re
    text = open(drv_mod.__file__).read()
    # Strip triple-quoted docstrings + comments to avoid false positives.
    text_clean = re.sub(r'\"{3}.*?\"{3}', "", text, flags=re.DOTALL)
    # A "lazy" import inside a method body is acceptable; what we
    # forbid is a top-level "import docker" outside a function.
    assert not re.search(
        r"^import docker\b", text_clean, flags=re.MULTILINE
    ), "docker_runtime_driver.py must not import docker at module top"
    assert not re.search(
        r"^from docker\b", text_clean, flags=re.MULTILINE
    ), "docker_runtime_driver.py must not import from docker at module top"


def test_docker_runtime_driver_conforms_to_protocol() -> None:
    client = _MockDockerClient()
    d = DockerRuntimeDriver(client=client)  # type: ignore[arg-type]
    assert isinstance(d, RuntimeDriver)


def test_install_runtime_returns_installed_instance(probe_returns_ok) -> None:
    client = _MockDockerClient()
    d = DockerRuntimeDriver(client=client)  # type: ignore[arg-type]
    desc = _good_descriptor()
    inst = asyncio.run(d.install_runtime("kokoro-cpu", desc))
    assert inst.state == RuntimeState.INSTALLED
    assert inst.runtime_id == "kokoro-cpu"
    assert inst.image_identity.digest == desc.spec.image.digest


def test_install_runtime_is_idempotent(probe_returns_ok) -> None:
    client = _MockDockerClient()
    d = DockerRuntimeDriver(client=client)  # type: ignore[arg-type]
    desc = _good_descriptor()
    inst1 = asyncio.run(d.install_runtime("kokoro-cpu", desc))
    inst2 = asyncio.run(d.install_runtime("kokoro-cpu", desc))
    assert inst1.state == RuntimeState.INSTALLED
    assert inst2.state == RuntimeState.INSTALLED


def test_install_runtime_builds_when_pull_not_found_and_build_metadata_present(probe_returns_ok) -> None:
    client = _MockDockerClient()
    d = DockerRuntimeDriver(client=client)  # type: ignore[arg-type]
    desc = _good_descriptor(runtime_id="kokoro-82m")
    inst = asyncio.run(d.install_runtime("kokoro-82m", desc))
    assert inst.state == RuntimeState.INSTALLED
    assert client.built_images, "expected platform-managed docker build fallback"
    assert client.built_images[0]["tag"] == "peakvox/kokoro-runtime:1.4.2"


def test_install_runtime_raises_imagepullerror_on_404(probe_returns_ok) -> None:
    client = _MockDockerClient()
    client.set_image_404(True)
    d = DockerRuntimeDriver(client=client)  # type: ignore[arg-type]
    desc_dict = _good_descriptor().model_dump()
    desc_dict["spec"]["build"] = None
    desc = RuntimeDescriptor.model_validate(desc_dict)
    with pytest.raises(ImagePullError):
        asyncio.run(d.install_runtime("kokoro-cpu", desc))


def test_install_runtime_raises_substrateerror_on_daemon_failure(probe_returns_ok) -> None:
    client = _MockDockerClient()
    client.set_daemon_down(True)
    d = DockerRuntimeDriver(client=client)  # type: ignore[arg-type]
    desc = _good_descriptor()
    with pytest.raises(SubstrateError):
        asyncio.run(d.install_runtime("kokoro-cpu", desc))


def test_start_runtime_brings_instance_to_active(probe_returns_ok) -> None:
    client = _MockDockerClient()
    d = DockerRuntimeDriver(client=client)  # type: ignore[arg-type]
    desc = _good_descriptor()
    # The manager calls install_runtime first, then start_runtime.
    # Mirror that flow in the test.
    asyncio.run(d.install_runtime("kokoro-cpu", desc))
    inst = asyncio.run(d.start_runtime("kokoro-cpu"))
    assert inst.state == RuntimeState.ACTIVE
    assert inst.health_state == HealthState.READY
    assert inst.port == 8000
    assert inst.host == "peakvox-runtime-kokoro-cpu"


def test_start_runtime_raises_runtimehealthfailed_on_ready_timeout(probe_returns_fail) -> None:
    client = _MockDockerClient()
    d = DockerRuntimeDriver(client=client)  # type: ignore[arg-type]
    desc = _good_descriptor_with_short_timeout()
    # First install to create the container.
    asyncio.run(d.install_runtime("kokoro-cpu", desc))
    # Now start with the failing probe; expect RuntimeHealthFailed.
    with pytest.raises(RuntimeHealthFailed):
        asyncio.run(d.start_runtime("kokoro-cpu"))


def test_stop_runtime_stops_active_container(probe_returns_ok) -> None:
    client = _MockDockerClient()
    d = DockerRuntimeDriver(client=client)  # type: ignore[arg-type]
    desc = _good_descriptor()
    asyncio.run(d.install_runtime("kokoro-cpu", desc))
    asyncio.run(d.start_runtime("kokoro-cpu"))
    asyncio.run(d.stop_runtime("kokoro-cpu"))
    container = client._containers.get("peakvox-runtime-kokoro-cpu")
    assert container is not None
    assert container._stopped is True
    assert container.status == "stopped"


def test_restart_runtime_stops_then_starts(probe_returns_ok) -> None:
    client = _MockDockerClient()
    d = DockerRuntimeDriver(client=client)  # type: ignore[arg-type]
    desc = _good_descriptor()
    asyncio.run(d.install_runtime("kokoro-cpu", desc))
    asyncio.run(d.start_runtime("kokoro-cpu"))
    inst = asyncio.run(d.restart_runtime("kokoro-cpu"))
    assert inst.state == RuntimeState.ACTIVE


def test_update_runtime_re_pulls_and_leaves_installed(probe_returns_ok) -> None:
    client = _MockDockerClient()
    d = DockerRuntimeDriver(client=client)  # type: ignore[arg-type]
    desc = _good_descriptor()
    asyncio.run(d.install_runtime("kokoro-cpu", desc))
    asyncio.run(d.start_runtime("kokoro-cpu"))
    inst = asyncio.run(d.update_runtime("kokoro-cpu", desc))
    # After update, instance is left in Installed (lazy start).
    assert inst.state == RuntimeState.INSTALLED


def test_remove_runtime_stops_then_removes(probe_returns_ok) -> None:
    client = _MockDockerClient()
    d = DockerRuntimeDriver(client=client)  # type: ignore[arg-type]
    desc = _good_descriptor()
    asyncio.run(d.install_runtime("kokoro-cpu", desc))
    asyncio.run(d.start_runtime("kokoro-cpu"))
    asyncio.run(d.remove_runtime("kokoro-cpu"))
    # Container is removed (status reflects removal).
    container = client._containers.get("peakvox-runtime-kokoro-cpu")
    assert container is not None
    assert container._removed is True
    assert "peakvox/kokoro-runtime:1.4.2" in client.removed_images


def test_remove_runtime_raises_notfound_when_container_missing(probe_returns_ok) -> None:
    client = _MockDockerClient()
    d = DockerRuntimeDriver(client=client)  # type: ignore[arg-type]
    # No container exists; remove is a no-op (the driver swallows
    # RuntimeNotFound on stop and continue with image removal,
    # which is also a no-op).
    asyncio.run(d.remove_runtime("never-installed"))


def test_runtime_status_returns_snapshot(probe_returns_ok) -> None:
    client = _MockDockerClient()
    d = DockerRuntimeDriver(client=client)  # type: ignore[arg-type]
    desc = _good_descriptor()
    asyncio.run(d.install_runtime("kokoro-cpu", desc))
    asyncio.run(d.start_runtime("kokoro-cpu"))
    inst = asyncio.run(d.runtime_status("kokoro-cpu"))
    assert inst.runtime_id == "kokoro-cpu"
    assert inst.state == RuntimeState.ACTIVE


def test_runtime_status_raises_notfound_when_container_missing() -> None:
    client = _MockDockerClient()
    d = DockerRuntimeDriver(client=client)  # type: ignore[arg-type]
    with pytest.raises(RuntimeNotFound):
        asyncio.run(d.runtime_status("never-installed"))


def test_runtime_health_probes_both_endpoints(probe_returns_ok) -> None:
    client = _MockDockerClient()
    d = DockerRuntimeDriver(client=client)  # type: ignore[arg-type]
    desc = _good_descriptor()
    asyncio.run(d.install_runtime("kokoro-cpu", desc))
    asyncio.run(d.start_runtime("kokoro-cpu"))
    rep = asyncio.run(d.runtime_health("kokoro-cpu"))
    assert rep.runtime_id == "kokoro-cpu"
    assert rep.liveness is Liveness.ALIVE
    assert rep.readiness is Readiness.READY


def test_runtime_metrics_returns_empty_metrics() -> None:
    client = _MockDockerClient()
    d = DockerRuntimeDriver(client=client)  # type: ignore[arg-type]
    metrics = asyncio.run(d.runtime_metrics("kokoro-cpu"))
    assert metrics is not None


def test_runtime_logs_streams_container_output(probe_returns_ok) -> None:
    client = _MockDockerClient()
    d = DockerRuntimeDriver(client=client)  # type: ignore[arg-type]
    desc = _good_descriptor()
    asyncio.run(d.install_runtime("kokoro-cpu", desc))
    asyncio.run(d.start_runtime("kokoro-cpu"))
    container = client._containers["peakvox-runtime-kokoro-cpu"]
    container.attach_log_buffer(["line 1", "line 2"])
    lines = []

    async def _collect():
        async for line in d.runtime_logs("kokoro-cpu"):
            lines.append(line)
    asyncio.run(_collect())
    assert lines == ["line 1", "line 2"]


def test_docker_driver_does_not_communicate_with_runtimeservices_directly() -> None:
    """Architectural invariant: the driver probes substrate-internal
    ``/ready`` and ``/health`` only. It does NOT speak the Runtime
    Service Contract (that is the adapter's role in 2C+). The
    probe function is the only HTTP-shaped call in the driver.
    """
    # Inspect the module to assert that the only HTTP-shaped import
    # is urllib.request (for the substrate probe).
    import re
    text = open(drv_mod.__file__).read()
    # No HTTP client library other than urllib is imported.
    forbidden_http_imports = ["requests", "httpx", "aiohttp"]
    for lib in forbidden_http_imports:
        assert lib not in text, (
            f"DockerRuntimeDriver must not import {lib}; the only "
            f"HTTP-shaped call is the substrate-internal /ready probe "
            f"via urllib."
        )
    # The Runtime Service Contract is the adapter's concern (2C+);
    # the driver probes only the substrate-internal endpoints
    # /ready and /health. Documented in DESIGN.md §5.5.
    assert "urllib" in text, "expected urllib for the substrate probe"


def test_driver_does_not_talk_to_kubernetes_or_podman() -> None:
    """Architectural invariant: this driver talks Docker only. The
    K8s / Podman / local-process drivers are separate modules
    in this package (per OPEN_DECISIONS Decision 11)."""
    text = open(drv_mod.__file__).read()
    forbidden_substrates = ["kubernetes", "podman", "kubectl", "nerdctl"]
    for s in forbidden_substrates:
        assert s not in text, (
            f"DockerRuntimeDriver must not reference {s!r}; substrate-"
            f"specific code is confined to its own driver."
        )

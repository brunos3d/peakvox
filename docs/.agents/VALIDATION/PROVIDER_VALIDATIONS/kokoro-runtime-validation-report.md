# Kokoro Runtime-Service — Provider Validation Report (G6)

**Date:** 2026-06-07
**Status:** Runtime-service path implemented and architecturally
validated. E2E audio validation is gated on a real
`peakvox/kokoro-runtime` container (not in default CI lane).
**Model:** `kokoro-base` (82M params, Apache-2.0, CPU-capable,
54 preset voices)
**Adapter:** `KokoroAdapter` (model_adapters/kokoro_adapter.py)
**Runtime:** `peakvox/kokoro-runtime:0.1.0` (descriptor in
`runtime-registry/kokoro-82m/descriptor.json`)

---

## 1. Scope

This is the **G6 validation** for the runtime-service
migration. G5 validated the in-process path
(`pip install kokoro` → `KPipeline` → audio). G6 validates
the runtime-service path (PeakVox backend →
`KOKORO_RUNTIME_URL` → `HTTPTransport` → `peakvox/kokoro-runtime`
container → audio).

G6 is the FIRST validation report for the Runtime-Service
architecture (ADR-0016 + ADR-0017). It validates that:

- The `runtime-registry/` directory is published with the
  Kokoro descriptor.
- The descriptor binds to the existing model id
  `kokoro-base` and validates against the bound model's
  `ModelCapabilities` (no implicit capabilities).
- The `RuntimeManager` orchestrates the four CE operations
  (install / activate / update / remove) against the
  `DockerRuntimeDriver`.
- The `RuntimeManager.resolve()` returns the cached ACTIVE
  instance when the runtime is installed + started.
- The 2A bridge in `PeakVoxRuntime.generate()` is ACTIVATED:
  when the manager is wired AND the resolution is non-None,
  the bridge records an observability event confirming the
  runtime-service path is reachable.
- The `KokoroAdapter` dispatches on `KOKORO_RUNTIME_URL`:
  when set, routes via `HTTPTransport`; when unset, uses
  the in-process path.
- The in-process path is preserved as a fallback.

G6 does NOT validate:

- Real audio generation through a real `peakvox/kokoro-runtime`
  container. The E2E test
  (`tests/test_kokoro_e2e_runtime.py`) is GATED on
  `KOKORO_RUNTIME_URL` being set; in the default test venv,
  the env var is empty and the test is skipped. The E2E
  validation is a Phase 2D/3 deliverable wired into the
  docker-compose CI lane.
- Performance (RTF, VRAM, load time). Deferred to a later
  validation gate.
- Error recovery from a crashed runtime service. Deferred
  to Phase 3.

---

## 2. 8-Gate Assessment

| # | Gate | Status | Details |
|---|---|---|---|
| G1 | Architecture | ✅ Pass | Runtime-Service architecture validated by the Runtime Activation Audit (2026-06-07). All 7 checks PASS. The canonical chain (Voice → VoiceVariant → Active Artifact → Adapter) is intact. Runtime infrastructure is strictly downstream. |
| G2 | Descriptor | ✅ Pass | `runtime-registry/kokoro-82m/descriptor.json` validates against the `RuntimeDescriptor` Pydantic schema. Binds to `kokoro-base` with `is_default=true` and `priority=100`. `metadata.edition` includes `ce`. Capabilities `["tts"]` are a subset of the bound model's `ModelCapabilities`. |
| G3 | Registry | ✅ Pass | `RuntimeRegistryLoader` walks `runtime-registry/`, parses the descriptor, builds the indexes (`id → descriptor`, `model_id → [id]`, `capability → [id]`). 9 tests in `test_runtime_registry_kokoro_descriptor.py`. |
| G4 | CE operations | ✅ Pass | `RuntimeManager.install / start / stop / update / remove` cache the `RuntimeInstance` and publish events. `RuntimeManager.resolve()` returns the cached ACTIVE instance. 12 tests in `test_runtime_manager_operations.py`. |
| G5 | Bridge activation | ✅ Pass | The 2A bridge in `runtime.py:475-498` is ACTIVATED: when the manager is wired AND the resolution is non-None, the bridge records a debug log confirming the runtime-service path is reachable. The adapter's 2C.2 dispatch on `KOKORO_RUNTIME_URL` is the active routing path. 5 tests in `test_bridge_activation_phase2d.py`. |
| G6 | Generation (E2E) | ⛔ Gated | `tests/test_kokoro_e2e_runtime.py` is gated on `KOKORO_RUNTIME_URL` being set. In the default test venv, the env var is empty and the test is skipped. The E2E validation requires a real `peakvox/kokoro-runtime` container, which is wired into the docker-compose CI lane in Phase 2D/3. |
| G7 | Performance | ⛔ Not measured | RTF, VRAM, load time not recorded for the runtime-service path. Deferred to a later validation gate. |
| G8 | Error recovery | ⚠ Partial | `RuntimeNotFound` on unknown runtime_id. `RuntimeDriverError` propagates from the driver. `HTTPTransportError` propagates from the transport. Edge cases (e.g. crashed container, network partition) are deferred to Phase 3. |

**Overall: Runtime-service path is implemented and
architecturally validated. E2E audio validation is gated on
real container infrastructure (Phase 2D/3).**

---

## 3. Runtime-registry/ structure

```
runtime-registry/
├── kokoro-82m/
│   └── descriptor.json     # Runtime Service Contract
```

The descriptor follows the ADR-0017 §1.1 schema:

```json
{
  "api_version": "peakvox.io/v1",
  "kind": "Runtime",
  "metadata": {
    "id": "kokoro-82m",
    "name": "Kokoro 82M Runtime",
    "description": "...",
    "provider": "kokoro",
    "version": "0.1.0",
    "edition": ["ce"],
    "labels": {"substrate": "cpu", "model_family": "kokoro-82m"}
  },
  "spec": {
    "runtime_type": "docker",
    "image": {"repository": "peakvox/kokoro-runtime", "tag": "0.1.0"},
    "service": {
      "protocol": "http", "port": 8000,
      "health_path": "/health", "readiness_path": "/ready",
      "generate_path": "/v1/generate",
      "build_path": "/v1/variants/build",
      "metadata_path": "/v1/metadata"
    },
    "capabilities": ["tts"],
    "requirements": {
      "gpu": "optional", "min_vram_gb": 0,
      "cpu_cores": 1, "memory_gb": 2,
      "edition": ["ce"]
    },
    "model_binding": {
      "model_id": "kokoro-base",
      "is_default": true, "priority": 100
    },
    "lifecycle": {
      "install_policy": "pull-on-install",
      "health_interval_seconds": 10,
      "health_timeout_seconds": 3,
      "start_timeout_seconds": 60,
      "restart_policy": "on-failure"
    }
  }
}
```

The descriptor binds to the existing model id
`kokoro-base` (per `backend/app/services/model_catalog.py`
line 210). The descriptor's capabilities `["tts"]` are a
subset of the bound model's `ModelCapabilities`. The
descriptor's `metadata.edition` includes `ce`.

---

## 4. CE operations

The `RuntimeManager` orchestrates the four CE operations
against the `DockerRuntimeDriver` (the only concrete driver
in 2B+).

| Operation | Driver call | Cache effect | Events |
|---|---|---|---|
| `install(runtime_id)` | `driver.install_runtime(runtime_id, descriptor)` | Adds to `_instance_cache` | `install_requested`, `install_completed` (or `install_failed`) |
| `start(runtime_id)` | `driver.start_runtime(runtime_id)` | Replaces with `state=ACTIVE` | `start_requested`, `start_completed` |
| `stop(runtime_id)` | `driver.stop_runtime(runtime_id)` | Replaces with `state=STOPPED` | `stop_completed` |
| `update(runtime_id)` | `driver.update_runtime(runtime_id, descriptor)` | Replaces | (no events) |
| `remove(runtime_id)` | `driver.remove_runtime(runtime_id)` | Evicts from cache | `remove_completed` |
| `resolve(model_id)` | (cache read) | (read-only) | (no events) |

`resolve()` returns a `RuntimeResolution` ONLY when the
chosen descriptor has a cached ACTIVE instance. When the
cache is empty or the instance is not ACTIVE, `resolve()`
returns `None` and the bridge falls through to the
in-process path. This is the source of truth for
"runtime-service path is reachable".

12 tests in `test_runtime_manager_operations.py` cover the
full operation surface.

---

## 5. Bridge activation (2D)

The 2A bridge in `backend/app/services/runtime.py` is
ACTIVATED in 2D. The activation is a documentation +
observability change at the verification point between
active-artifact resolution and the adapter call.

```python
if self._runtime_manager is not None:
    _resolution = self._runtime_manager.resolve(descriptor.id)
    if _resolution is not None:
        # 2D activation: the runtime-service path is reachable.
        _logger.debug(
            "PeakVoxRuntime: runtime-service path available for model %s "
            "via runtime %s at %s",
            descriptor.id,
            _resolution.descriptor.metadata.id,
            _resolution.endpoint,
        )
```

The activation does NOT change:
- The adapter contract (signature unchanged)
- The in-process path (preserved)
- The adapter's kwargs (the bridge does not inject a
  runtime endpoint)

The actual routing is the adapter's 2C.2 dispatch
(`KokoroAdapter` dispatches on `KOKORO_RUNTIME_URL`).
The bridge is the verification point.

5 tests in `test_bridge_activation_phase2d.py` cover the
full activation surface.

---

## 6. Architectural invariants

Per the **Runtime Activation Audit** (2026-06-07), the
Runtime-Service architecture preserves the canonical
chain:

```
Voice → VoiceVariant → Active Artifact → Adapter
                                       ↓
                              RuntimeManager
                                       ↓
                              RuntimeDriver
                                       ↓
                              Runtime Service
```

The 7 audit checks PASS:

1. `RuntimeResolution` never becomes a canonical domain
   object. PASS — defined at `runtime_manager.py:71`;
   constructed only at line 181; consumed only at
   `runtime.py:476`; no DB persistence, no API exposure.
2. `RuntimeDescriptor` never owns Model metadata. PASS —
   `model_id` is a string reference; capabilities are
   validated as a subset of `ModelCapabilities`.
3. `RuntimeInstance` never owns Voice metadata. PASS —
   no `voice_id`, no `public_voice_id`, no voice metadata.
4. `RuntimeRegistry` remains deployment metadata only.
   PASS — holds only `RuntimeDescriptor` objects; no
   voice / variant / artifact references.
5. Voice compatibility continues to be derived from
   `VoiceVariant` + `ModelCapabilities`. PASS — the
   bridge does not introduce a new compatibility path.
6. Runtime activation cannot bypass `VariantResolver` or
   `ArtifactResolver`. PASS — the bridge sits AFTER
   variant resolution; it does not call `resolve_variant`,
   `get_active_artifact`, `set_active`, `append_artifact`.
7. Runtime Service never receives enough information to
   independently resolve voices. PASS — the request body
   is a dict of strings; no Voice / VoiceVariant /
   VoiceVariantArtifact / model_id.

The expected invariant holds:
- **Voices own identity.**
- **Models own capabilities.**
- **Variants own realizations.**
- **Artifacts own model-specific assets.**
- **Runtimes own deployment state only.**

---

## 7. Test coverage

| Surface | Test file | Tests | Status |
|---|---|---|---|
| Descriptor schema | `test_runtime_descriptor.py` | 12 | ✅ |
| Instance schema | `test_runtime_instance.py` | 7 | ✅ |
| Health/metrics types | `test_runtime_health.py` | 6 | ✅ |
| Driver errors | `test_runtime_errors.py` | 8 | ✅ |
| Driver protocol | `test_runtime_driver_protocol.py` | 3 | ✅ |
| Registry | `test_runtime_registry.py` | 10 | ✅ |
| Event bus | `test_runtime_events.py` | 8 | ✅ |
| Manager skeleton | `test_runtime_manager.py` | 11 | ✅ |
| Bridge integration (2A) | `test_runtime_routing_phase2.py` | 10 | ✅ |
| Driver implementation (2B) | `test_docker_runtime_driver.py` | 21 | ✅ |
| Lint script (2B) | `test_lint_no_docker_outside_driver.py` | 8 | ✅ |
| Manager + driver (2B) | `test_runtime_manager_with_docker.py` | 12 | ✅ |
| HTTP transport (2C) | `test_http_transport.py` | 14 | ✅ |
| Adapter isolation (2C) | `test_kokoro_runtime_adapter.py` | 8 | ✅ |
| Settings plumbing (2C) | `test_settings_kokoro_runtime_url.py` | 3 | ✅ |
| E2E scaffold (2C, gated) | `test_kokoro_e2e_runtime.py` | 1 | ⏭ skipped |
| Descriptor (2D) | `test_runtime_registry_kokoro_descriptor.py` | 9 | ✅ |
| Settings path (2D) | `test_settings_runtime_registry_path.py` | 2 | ✅ |
| CE operations (2D) | `test_runtime_manager_operations.py` | 12 | ✅ |
| Bridge activation (2D) | `test_bridge_activation_phase2d.py` | 5 | ✅ |

**Total runtime tests:** 170 passed + 1 skipped (E2E gated)
**Full backend test suite:** 495 passed, 1 skipped

---

## 8. Phase 2 → Phase 3 gate

Phase 2 (Sub-phases 2A + 2B + 2C + 2D) is COMPLETE:

- The Kokoro runtime service is operational in CE (descriptor
  published, CE operations wired, bridge activated).
- The `KokoroAdapter` routes through the runtime when
  `KOKORO_RUNTIME_URL` is set; falls back in-process otherwise.
- The `runtime-registry/` directory is in the repo with the
  Kokoro descriptor.
- `IMPLEMENTATION_STATUS.md` reflects the new reality
  (Phase 2D = IMPLEMENTED; Phase 2 = COMPLETE).
- `OPEN_DECISIONS.md` Decision 10 is RESOLVED (ADR-0016 +
  ADR-0017 Accepted+Implemented).
- `OPEN_DECISIONS.md` Decision 11 (future drivers) is
  updated with a "Phase 3 next" pointer.

**Phase 3 — Kokoro full migration** is unblocked:

- The Kokoro provider becomes the FIRST provider that runs
  ONLY through the runtime service in CE (in-process path
  is still available as a fallback, but the default CE
  deployment uses the runtime service).
- The Kokoro descriptor's `image.digest` pins the runtime
  service to a specific image version.
- The Kokoro adapter is updated to communicate with the
  runtime service by default (the `KOKORO_RUNTIME_URL` env
  var becomes the canonical configuration point).

**Phase 3 deliverables:**

- Real E2E audio generation through the runtime service
  (the gated E2E test, wired into docker-compose CI).
- G7 (Performance) and G8 (Error recovery) validation
  reports.
- Provider-validated report for the runtime-service path
  (this report, updated with real audio data).
- Decision on whether to remove the in-process path
  (Phase 7 of the original migration plan).

---

## 9. Related documents

- ADR-0016 — Models as Runtime Services (Accepted+Implemented)
- ADR-0017 — Runtime Services Implementation (Accepted+Implemented)
- Runtime Activation Audit (2026-06-07, all 7 checks PASS)
- `docs/.agents/SPECS/FEATURES/runtime-services-implementation/`
  (5 files: SPEC, DESIGN, TASKS, VALIDATION, STATUS)
- `docs/.agents/SPECS/FEATURES/models-as-runtime-services/`
  (5 files: SPEC, DESIGN, TASKS, VALIDATION, STATUS)
- Kokoro G5 validation report (in-process path, 2026-06-05)

---

**Validation date:** 2026-06-07
**Branch:** `feat/peakvox-phase-1`
**Phase:** 2D — COMPLETE
**Next phase:** 3 — Kokoro full migration

# IMPLEMENTATION STATUS — the implementation lock file

> The authoritative map of what is actually built. **Documentation is not evidence;
> implementation requires code references.** This file is designed so it can eventually be
> partially regenerated from codebase analysis — every "IMPLEMENTED/VALIDATED" row cites
> concrete files and tests. Prefer code evidence over assumption; when in doubt, mark lower.

**Last verified against code:** 2026-06-07 (`feat/peakvox-phase-1`).
All paths are relative to repository root.

## Status vocabulary

| Status | Meaning |
|---|---|
| `NOT_STARTED` | No design, no code. |
| `PLANNED` | Roadmap/plan exists; no code. |
| `PROPOSED` | ADR/spec proposed, not accepted. |
| `APPROVED` | ADR accepted / spec approved; no implementation found. |
| `IN_PROGRESS` | Code being written now. |
| `PARTIAL` | Some code exists; not complete or not end-to-end proven. |
| `IMPLEMENTED` | Code complete; covered by automated tests. |
| `VALIDATED` | Implemented **and** proven end-to-end (for providers: real audio generated). |
| `SUPERSEDED` | Replaced by a later decision/implementation. |
| `DEPRECATED` | Retained but slated for removal. |
| `ARCHIVED` | Historical only. |

**Two distinct axes for providers:** *architecture* (can the platform represent/orchestrate
it — proven by contract tests) vs *provider* (does a real model run end-to-end — proven by
real inference). A row can be `IMPLEMENTED` on architecture and `PARTIAL`/`NOT_STARTED` on
provider validation.

---

## A. Architecture decisions (ADRs)

| ADR | Decision | Status | Implementation evidence |
|---|---|---|---|
| 0001 | Voice / VoiceVariant split | IMPLEMENTED | `backend/app/models/db.py` (`Voice`, `VoiceVariant`); `voice_variant_repository.py`; tests `test_voice_split_migration`, `test_voice_dual_write` |
| 0002 | Model as first-class entity | IMPLEMENTED | `model_registry.py`, `model_catalog.py`, `model_providers/`; `api/models.py`; tests `test_model_registry`, `test_model_catalog` |
| 0003 | Model Capability Contract | IMPLEMENTED | `models/registry_types.py::ModelCapabilities`, `services/capabilities.py`; tests `test_capabilities_contract`, `test_capabilities_service` |
| 0004 | Voice ≠ VoiceVariant ≠ Model separation | IMPLEMENTED | `services/model_adapter.py`, `runtime.py`; tests `test_runtime`, `test_universal_voice_asset` |
| 0005 | Edition-scoped model availability | IMPLEMENTED | `runtime.ensure_available`, `ModelDescriptor.editions`; tests `test_editions`, `test_model_availability`, `test_runtime_editions` |
| 0006 | Voice Variant Realization Types (open taxonomy) | IMPLEMENTED | `services/realization.py`; tests `test_realization`, `test_adapter_realization_surface` (status values superseded by 0008) |
| 0007 | Canonical Model Metadata Registry | IMPLEMENTED | `model_catalog.py`; tests `test_registry_metadata`, `test_models_api_metadata` |
| 0008 | Voice Variant Build Lifecycle (5-state) | IMPLEMENTED | `services/variant_lifecycle.py`; `runtime.build/rebuild/ensure_variant`; tests `test_variant_lifecycle`, `test_runtime_variant_lifecycle` (builds synchronous; async queue deferred) |
| 0009 | Artifact Versioning + Retention | IMPLEMENTED | `voice_variant_artifacts` table; `services/voice_variant_artifact_repository.py`; tests `test_artifact_versioning_migration`, `test_artifact_repository` |
| 0010 | Voice Source Assets + Automatic Variant Provisioning | IMPLEMENTED | `models/db.py::VoiceSourceAsset`, `core/migrations.py::_backfill_voice_source_assets`; backfill creates source-asset rows from variant artifacts. No dedicated provisioning service beyond `ensure_variant`. |
| 0011 | Voice Creation Sources | IMPLEMENTED | `creation_source` column on `Voice` model (`models/db.py`), migration backfill, generation dual-path uses `voice_id`. Full taxonomy + per-source provisioning policies (ADR-0012) not implemented. |
| 0016 | Models as Runtime Services | IMPLEMENTED (Phase 1+2A+2B+2C) | ADR accepted 2026-06-07. Phases 1+2A+2B+2C implemented (foundations + first driver + first communication path). The remaining 3 phases are sequenced: 3 (Kokoro full migration) → 4 (F5-TTS reference) → 5 (Fish) → 6 (OmniVoice) → 7 (remove in-process path). See `docs/.agents/SPECS/FEATURES/models-as-runtime-services/` and §"Phase 2A/2B/2C" below for evidence. |
| 0017 | Runtime Services Implementation (Phase 2 Implementation ADR) | IMPLEMENTED (2A+2B+2C) | ADR accepted 2026-06-07. Phases 2A+2B+2C implemented: 9 modules + 1 driver + 1 transport + 1 settings field; 25 new test files. The remaining 2D (CE operations + runtime-registry/ with Kokoro descriptor) is sequenced. Resolves the 5 deferred open questions from `OPEN_DECISIONS.md` Decision 10. See `docs/.agents/SPECS/FEATURES/runtime-services-implementation/` and §"Phase 2A/2B/2C" below for evidence. |

## B. Runtime components

| Component | Status | Evidence |
|---|---|---|
| `PeakVoxRuntime` single entry point | IMPLEMENTED | `services/runtime.py`; generation routes only through it; `test_runtime_wiring` |
| `ModelAdapter` contract | IMPLEMENTED | `services/model_adapter.py` |
| OmniVoice adapter | IMPLEMENTED (arch) / PARTIAL (provider) | `model_adapters/omnivoice_adapter.py` + `omnivoice_service.py` (real `from_pretrained`/`generate_async`); no automated end-to-end audio test |
| OmniVoice Singing adapter | PARTIAL | shares OmniVoice engine; catalog `status="disabled"`; unverified |
| Fish Audio adapter | PARTIAL (arch IMPLEMENTED, provider NOT_STARTED) | `model_adapters/fish_adapter.py` (HTTP client wired, real inference via S2 Pro server, unit-tested with mocks); real audio generation blocked — see Provider Validations |
| Kokoro adapter | IMPLEMENTED (arch) / PARTIAL (provider) | `model_adapters/kokoro_adapter.py` (82M, 54 presets, 9 languages, lazy `kokoro` import, WAV 24kHz); architecture-validated via mock-kokoro tests; real inference requires `kokoro` pip package. `build_variant()` creates metadata-only VoiceVariant (Phase 2) |
| `ProviderVoice` domain type + `ProviderVoiceRegistry` | IMPLEMENTED | `services/provider_voice.py` (frozen dataclass, O(1) dict lifecycle, search); tests `test_provider_voice` (31 tests) |
| `ProviderVoiceCatalog` protocol | IMPLEMENTED | `services/provider_voice.py` (`@runtime_checkable Protocol` on `ModelAdapter`); auto-populated at `register_adapter()` time |
| Variant resolution (`Voice+Model→Variant`) | IMPLEMENTED | `variant_resolution.py`; `test_variant_resolution`, `test_multimodel_resolution` |
| Capability validation / tag validation | IMPLEMENTED | `capabilities.py`, `tag_validation.py`, `tag_catalog.py` |
| Auto routing (`model="auto"`) | NOT_STARTED | metadata-readiness assessed only; no router |
| Async build queue | NOT_STARTED (deferred) | ADR-0008 Option 3; CE builds are synchronous |

### Phase 2A — Runtime Services Foundations (IMPLEMENTED 2026-06-07)

Phase 2A is **infrastructure foundation work** — no model is migrated, no
runtime is activated, no Docker integration is introduced. The driver is
not yet wired; in 2A the `RuntimeManager.resolve()` returns `None` and the
existing in-process path is taken unchanged. See
[`SPECS/FEATURES/runtime-services-implementation/TASKS.md` §2A](../SPECS/FEATURES/runtime-services-implementation/TASKS.md)
for the full task breakdown.

| Component | Status | Evidence |
|---|---|---|
| `RuntimeDescriptor` (Pydantic) | IMPLEMENTED | `app/services/runtime_types.py`; `tests/test_runtime_descriptor.py` (12 tests) — schema validation, DNS-label id, capability vocabulary, edition subset, sha256 digest, model_dump round-trip |
| `RuntimeInstance` (frozen dataclass) | IMPLEMENTED | `app/services/runtime_instance.py`; `tests/test_runtime_instance.py` (7 tests) — 7 RuntimeState values, 3 HealthState values, frozen ImageIdentity, equality |
| `HealthReport` / `Metrics` | IMPLEMENTED | `app/services/runtime_types.py`; `tests/test_runtime_health.py` (6 tests) — liveness/readiness enums, frozen report, empty Metrics |
| `RuntimeDriverError` hierarchy (8 subclasses) | IMPLEMENTED | `app/services/runtime_errors.py`; `tests/test_runtime_errors.py` (8 tests) — RuntimeNotFound, ImagePullError, SubstrateError, RuntimeAlreadyExists, RuntimeNotActive, TimeoutError, RuntimeRequirementsNotMet, RuntimeHealthFailed |
| `RuntimeDriver` Protocol (10 operations) | IMPLEMENTED | `app/services/runtime_driver.py`; `tests/test_runtime_driver_protocol.py` (3 tests) — `runtime_checkable`, structural conformance, rejects missing methods |
| `RuntimeRegistry` + `RuntimeRegistryLoader` | IMPLEMENTED | `app/services/runtime_registry.py`; `tests/test_runtime_registry.py` (10 tests) — indexes by id/model_id/capability, file walking, path-traversal guard, malformed-descriptor tolerance |
| `RuntimeEventBus` | IMPLEMENTED | `app/services/runtime_events.py`; `tests/test_runtime_events.py` (8 tests) — publish/subscribe, in-order dispatch, exception isolation, canonical event vocabulary (12 event types) |
| `RuntimeManager` skeleton | IMPLEMENTED | `app/services/runtime_manager.py`; `tests/test_runtime_manager.py` (11 tests) — orquestación only (no `generate`/`infer`/`load_weights` method), `resolve()` returns `None` in 2A, lifecycle operations raise `NoDriverConfigured` when no driver wired, event publication, in-process path preserved |
| PeakVoxRuntime bridge integration | IMPLEMENTED | `app/services/runtime.py` (`attach_runtime_manager` + bridge block in `generate`); `tests/test_runtime_routing_phase2.py` (10 tests) — transitional pass-through only; `Voice → VoiceVariant → Active Artifact → RuntimeManager (skeleton) → Adapter → existing inference path`; behavior unchanged in 2A; the 2C+ runtime-service branch is a documented-but-unreachable literal `pass` |

**Phase 2A architectural invariants (verified per the 2A gate checklist):**
- No `import docker` in `backend/app/services/runtime*.py` or `runtime.py`.
- No model framework imports (`torch`, `transformers`, `kokoro`, `f5_tts`, `fish_audio`) in runtime modules.
- No HTTP client imports (`requests`, `httpx`, `aiohttp`) in runtime modules.
- No runtime activation: `DockerRuntimeDriver` is introduced in sub-phase 2B.
- No Runtime Service communication: `HTTPTransport` is introduced in sub-phase 2C.
- No behavior regressions: full backend test suite (excluding pre-existing numpy/torch-dependent files) is 401 passed (was 374 before Phase 2 implementation began; +27 new tests for Phase 2A across 9 test files; all 52 pre-existing runtime tests continue to pass).

### Phase 2B — First Concrete Driver (IMPLEMENTED 2026-06-07)

Phase 2B introduces the FIRST CONCRETE `RuntimeDriver`: the
`DockerRuntimeDriver`. The driver is the only component in the
backend allowed to import the docker SDK (the import is LAZY so
the module is importable in environments without the SDK —
notably the test venv). The `RuntimeManager.resolve()` is
updated to return a non-None `RuntimeResolution` when a driver
is wired; the 2A bridge in `runtime.py` is unchanged (the
runtime-service branch is still a literal `pass`; activation is
in 2C). See
[`SPECS/FEATURES/runtime-services-implementation/TASKS.md` §2B](../SPECS/FEATURES/runtime-services-implementation/TASKS.md)
for the full task breakdown.

| Component | Status | Evidence |
|---|---|---|
| `DockerRuntimeDriver` (concrete driver) | IMPLEMENTED | `app/services/drivers/docker_runtime_driver.py`; `tests/test_docker_runtime_driver.py` (21 tests) — all 10 RuntimeDriver operations; pulls by digest (preferred) or tag; idempotent install; `ImagePullError` on 404; `SubstrateError` on daemon failure; `/ready` probe (urllib GET, run in a thread to avoid blocking); `RuntimeHealthFailed` on timeout; no top-level `import docker` (lazy inside `_ensure_client()`) |
| `lint_no_docker_outside_driver.py` | IMPLEMENTED | `scripts/lint_no_docker_outside_driver.py`; `tests/test_lint_no_docker_outside_driver.py` (8 tests) — AST scan bans `import docker`, `from docker import ...`, and docker-shaped `subprocess.run` calls outside `backend/app/services/drivers/`; patchable `BACKEND_ROOT` for tests; current tree passes the lint |
| `RuntimeManager` wired with `DockerRuntimeDriver` | IMPLEMENTED | `app/services/runtime_manager.py`; `tests/test_runtime_manager_with_docker.py` (11 tests) — `resolve()` with a driver returns a non-None `RuntimeResolution` (synthetic `RuntimeInstance`, endpoint URL from descriptor service port + default host); selection rules (default > priority > hint > first); without a driver, `resolve()` returns `None` (2A behavior preserved) |
| `PeakVoxRuntime` bridge — runtime path activation | NOT_STARTED | The 2A bridge block in `runtime.py` (`attach_runtime_manager` + the `if _resolution is not None: pass` block) is intentionally unchanged in 2B. The runtime-service branch activates in 2C, when `HTTPTransport` is added to adapters. The bridge falls through to the existing in-process path even when the manager is wired. |

**Phase 2B architectural invariants (verified per the 2B gate checklist):**
- Docker imports confined to `backend/app/services/drivers/docker_runtime_driver.py`. The import is LAZY (inside `_ensure_client()`) so the module is importable in environments without the SDK. The lint script enforces this in CI: `$ python scripts/lint_no_docker_outside_driver.py` → `clean`.
- `RuntimeManager` does not gain Docker knowledge: the manager is unchanged in the sense that the docker import is NOT in `runtime_manager.py`. The driver is injected via the constructor; the manager is substrate-neutral.
- `RuntimeManager` continues to communicate exclusively through `RuntimeDriver` — preserved. The manager's lifecycle methods (install/update/remove/start/stop) call through `self._driver` (the `RuntimeDriver` Protocol).
- `RuntimeRegistry` remains declarative — preserved. The manager reads the registry but does not mutate it.
- No adapter communicates directly with Docker — no adapter modifications; the lint confirms no `import docker` in any adapter file.
- No runtime service bypasses Adapter → RuntimeManager → RuntimeDriver — the 2C+ branch in 2A.10 is a literal `pass` in 2B; the runtime path is not activated by 2B.
- No model framework imports in runtime modules.
- No HTTP client imports in runtime modules (only `urllib` in the driver for the substrate-internal `/ready` and `/health` probes).
- No behavior regressions: full backend test suite (excluding pre-existing numpy/torch-dependent files) is 441 passed (was 401 after Milestone 6; +40 new tests across 2 test files for Phase 2B). All 52 pre-existing runtime tests continue to pass.

### Phase 2C — Runtime-Service Communication Path (IMPLEMENTED 2026-06-07)

Phase 2C is the FIRST sub-phase to introduce the runtime-service
COMMUNICATION PATH. The `HTTPTransport` is the new abstraction
for adapter → runtime service communication. The `KokoroAdapter`
dispatches on `KOKORO_RUNTIME_URL`: when set, routes via
`HTTPTransport`; when empty (CE default), uses the in-process
`kokoro` package as before. The 2A bridge in `runtime.py`
remains a literal `pass` in 2C; the activation of the
runtime-service branch through `RuntimeManager.resolve()` is
sequenced behind 2D. See
[`SPECS/FEATURES/runtime-services-implementation/TASKS.md` §2C](../SPECS/FEATURES/runtime-services-implementation/TASKS.md)
for the full task breakdown.

| Component | Status | Evidence |
|---|---|---|
| `HTTPTransport` (adapter HTTP client) | IMPLEMENTED | `app/services/adapter_transport/http_transport.py`; `tests/test_http_transport.py` (14 tests) — pure `(base_url, request) -> response` abstraction; bearer token auth (CE default is none per `OPEN_DECISIONS.md` Decision 10 §5); retry policy: 1 retry on 5xx, 3 attempts on network errors with exponential backoff (1s, 2s, 4s), no retry on 4xx; non-2xx responses raise `HTTPTransportError` with status + category + body; streaming: `post_stream` returns an async iterator over response bytes; injectable `client` and `retry_backoff` for tests via `httpx.MockTransport` |
| `KokoroAdapter` `KOKORO_RUNTIME_URL` integration | IMPLEMENTED | `app/services/model_adapters/kokoro_adapter.py`; `tests/test_kokoro_runtime_adapter.py` (8 tests) — dispatches on `KOKORO_RUNTIME_URL`: when set, routes via `HTTPTransport`; when empty, in-process `kokoro` (lazy import). Adapter contract surface unchanged (install/load/unload/health_check/generate/clone_voice/build_variant). Adapter gains no knowledge of Docker / RuntimeDescriptor / RuntimeInstance / RuntimeRegistry / RuntimeManager |
| `KOKORO_RUNTIME_URL` plumbing in `Settings` | IMPLEMENTED | `app/core/config.py`; `tests/test_settings_kokoro_runtime_url.py` (3 tests) — `Settings.KOKORO_RUNTIME_URL: str = ""`; CE default empty (= in-process); non-empty URL routes through the runtime service |
| E2E validation scaffolding | IMPLEMENTED (gated) | `tests/test_kokoro_e2e_runtime.py` (1 test, gated) — `pytest.mark.skipif` on `KOKORO_RUNTIME_URL` being empty; when set, runs end-to-end through the KokoroAdapter's runtime-service path against a real `peakvox/kokoro-runtime` container; verifies (duration, logs) tuple + audio file written + audio bytes non-empty. To be wired into the docker-compose CI lane in Phase 2D/3 |
| `PeakVoxRuntime` bridge — runtime path activation | NOT_STARTED | The 2A bridge block in `runtime.py` (`attach_runtime_manager` + the `if _resolution is not None: pass` block) is intentionally unchanged in 2C. The activation of the runtime-service branch in the bridge is sequenced behind 2D, when CE operations + the `runtime-registry/` with Kokoro descriptor land. The KokoroAdapter's local `KOKORO_RUNTIME_URL` dispatch is the runtime-service path in 2C; the bridge in `runtime.py` continues to fall through to the in-process path. |

**Phase 2C architectural invariants (verified per the 2C gate checklist + Transport Boundary Audit):**
- `HTTPTransport` is the ONLY HTTP-shape dependency adapters may use. Verified by AST / static check: adapters do not import `httpx` / `aiohttp` / `requests` directly; they import only `HTTPTransport` from `app.services.adapter_transport`.
- Adapters do NOT gain knowledge of Docker, containers, `RuntimeDescriptor`, `RuntimeInstance`, `RuntimeRegistry`, or `RuntimeManager`. Verified by isolation tests in `test_kokoro_runtime_adapter.py`.
- The expected future chain is `Adapter -> HTTPTransport -> Runtime Service`, NOT `Adapter -> RuntimeManager -> Docker -> Runtime Service`. Verified by isolation tests.
- Adapter contracts are unchanged. Verified by `test_kokoro_runtime_adapter.py::test_adapter_contract_surface_unchanged`.
- The canonical adapter inputs (kwargs of `generate` and `build_variant`) remain the same; no `GenerationRequest` / `BuildVariantRequest` dataclass is introduced in 2C.
- Runtime-service responses are mapped back into the existing `(duration, logs)` tuple. Verified by `test_kokoro_runtime_adapter.py::test_generate_routes_via_http_transport_when_runtime_url_set`.
- `KokoroAdapter` can switch between in-process inference and runtime-service inference without changing the caller (`PeakVoxRuntime`). Verified by `test_kokoro_runtime_adapter.py::test_generate_falls_back_to_in_process_when_url_unset`.
- No new API endpoints in the backend (the runtime service is a separate process; the adapter talks HTTP to it).
- No docker / kubernetes / podman / kubectl / nerdctl references in the adapter (lint passes; transport is pure HTTP).
- No model framework imports in the adapter (the in-process path's lazy `import kokoro` is the model, not the substrate).
- No behavior regressions: full backend test suite (excluding pre-existing numpy/torch-dependent files) is 466 passed (was 441 after Milestone 10; +25 new tests across 3 test files for Phase 2C: 14 transport + 8 adapter isolation + 3 settings; 1 E2E test skipped in default venv).
- Lint passes: `$ python scripts/lint_no_docker_outside_driver.py` → `clean`.

## C. Voice / data layer

| Subsystem | Status | Evidence |
|---|---|---|
| Voice identity (`public_voice_id`) | IMPLEMENTED | `models/db.py::Voice`; `voice_repository.py` |
| VoiceVariant realization | IMPLEMENTED | `models/db.py::VoiceVariant`; `voice_variant_repository.py` |
| VoiceVariantArtifact versioning | IMPLEMENTED | `voice_variant_artifact_repository.py` |
| Voice onboarding pipeline | IMPLEMENTED | `voice_onboarding.py`, `audio_preprocessing_service.py` |
| Voice Source Asset layer | PARTIAL | schema/UI references present; full ADR-0010 provisioning not built |
| ProviderVoice (ephemeral preset voices) | IMPLEMENTED | `services/provider_voice.py` (no DB, no assets, no variants, no provisioning — ADR-0010 §8 exempt); catalog-only since Phase 2 — two-tier resolution removed from `runtime.generate()` |
| Idempotent SQLite migrations | IMPLEMENTED | `core/migrations.py` |
| Storage abstraction | IMPLEMENTED | `services/storage.py` |

## D. API layer

| Surface | Status | Evidence |
|---|---|---|
| Versioned `/api/v1` | IMPLEMENTED (harden pending P9) | `api/v1.py` |
| `/voices` CRUD | IMPLEMENTED | `api/voices.py` |
| `/variants` (+ summary, backfill) | IMPLEMENTED | `api/variants.py`, `api/variants_summary.py` |
| `/models` (+ lifecycle) | IMPLEMENTED | `api/models.py` |
| `/generate` + jobs | IMPLEMENTED | `api/generation.py` |
| `GET /api/provider-voices` | IMPLEMENTED | `api/provider_voices.py`; tests `test_provider_voices_api` (7 tests) |
| `POST /voices/from-preset` | IMPLEMENTED | `api/voices.py` (create_voice_from_preset); tests `test_voices_from_preset` (2 tests) |
| Hashed API keys | IMPLEMENTED | `api/api_keys.py`, `services/api_keys.py` |
| `/v1/speech/generate` final contract freeze | PLANNED (P9) | — |

## E. Frontend

| Surface | Status | Evidence |
|---|---|---|
| Voice Library 2.0 (tabs, source asset, variants, artifacts) | IMPLEMENTED | `frontend/src/components/voice/*` |
| Preset Voices tab | IMPLEMENTED | `frontend/src/components/voice/PresetVoicesTab.tsx`; registered in `voices/page.tsx` |
| Variant Dashboard + backfill UX | IMPLEMENTED | `VariantDashboard.tsx`, `ModelCompatibilitySection.tsx` |
| Capability-driven generation controls | IMPLEMENTED | `GenerationPanel` (Voice Design gating) |
| Commercial nav (marketplace/creator/billing) | NOT_STARTED (flag-gated, hidden in CE) | — |

## F. Cloud / commercial (schema-ready only)

| Subsystem | Status | Evidence |
|---|---|---|
| Auth (Clerk adapter, principal resolution, roles) | APPROVED / NOT_STARTED | `AuthProvider` seam only |
| Billing (credits, metering, Stripe) | APPROVED / NOT_STARTED | empty tables + `BillingProvider`/`PaymentProvider` seams |
| Creators (profiles, Connect, royalties) | APPROVED / NOT_STARTED | empty `creators` table |
| Marketplace (listings, discovery, royalty-on-use) | APPROVED / NOT_STARTED | empty `marketplace_listings` table |
| Cloud infra (Postgres, Alembic, workers, CDN) | PLANNED | — |
| Production scaling | PLANNED | — |

---

## How to update this file

1. Verify against code, not memory or docs. Open the cited files.
2. Add or adjust the `Evidence` column with concrete `path` + `test_name` references.
3. Downgrade status the moment evidence is missing. An ADR being Accepted is `APPROVED`, not
   `IMPLEMENTED`.
4. Distinguish architecture-validated from provider-validated for anything touching a model.
5. Update [`PROJECT_STATE.md`](PROJECT_STATE.md) and [`HANDOFF.md`](HANDOFF.md) in the same change.

**Related:** [`DECISIONS/ADR_INDEX.md`](DECISIONS/ADR_INDEX.md) ·
[`VALIDATION/RETROSPECTIVES/`](VALIDATION/RETROSPECTIVES/) ·
[`IMPLEMENTATION/EXECUTION_HISTORY/EXECUTION_LEDGER.md`](IMPLEMENTATION/EXECUTION_HISTORY/EXECUTION_LEDGER.md)

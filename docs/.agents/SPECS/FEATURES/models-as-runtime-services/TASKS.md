# TASKS — Models as Runtime Services

> **Task-by-task breakdown.** SDD stage 4. Uses TDD per task
> (`superpowers:test-driven-development`). 7-phase migration; this is the
> plan for the entire feature.

> **Phase status:**
> - Phase 1: **READY TO START** (no code; ADR + design docs).
> - Phases 2–7: planned, **do not start** until Phase 1 ADR is accepted and
>   the corresponding implementation-phase ADR is written.

---

## Phase 1 — Architecture (ADR + design docs) — **CURRENT PHASE**

This is the only phase in flight. Phases 2–7 are listed below for
planner visibility only.

- [x] **1.1** — Create feature folder `docs/.agents/SPECS/FEATURES/models-as-runtime-services/`
  · files: folder creation
  · test: N/A (documentation phase)
- [x] **1.2** — Write [`SPEC.md`](./SPEC.md) · files: SPEC.md
  · test: cross-link resolver + constitution alignment check
- [x] **1.3** — Write [`DESIGN.md`](./DESIGN.md) · files: DESIGN.md
  · test: cross-link resolver + no forbidden patterns check
- [x] **1.4** — Write [`TASKS.md`](./TASKS.md) (this file) · files: TASKS.md
  · test: every phase has TDD-shaped tasks
- [x] **1.5** — Write [`VALIDATION.md`](./VALIDATION.md) · files: VALIDATION.md
  · test: architecture vs provider validation distinction preserved
- [x] **1.6** — Write [`STATUS.md`](./STATUS.md) · files: STATUS.md
  · test: status reflects Phase 1 only (APPROVED, not IMPLEMENTED)
- [x] **1.7** — Write [`adr-0016-models-as-runtime-services.md`](../../../DECISIONS/adr-0016-models-as-runtime-services.md)
  · files: adr-0016-…
  · test: ADR template compliance; all 4 required sections (Context,
    Options, Decision, Consequences); cross-link to Constitution + ADRs
- [x] **1.8** — Update [`ADR_INDEX.md`](../../../DECISIONS/ADR_INDEX.md) with the
  new entry · files: ADR_INDEX.md
  · test: ADR is listed; reservations 0013-0015 untouched
- [x] **1.9** — Update [`IMPLEMENTATION_STATUS.md`](../../../IMPLEMENTATION_STATUS.md) with
  ADR-0016 row at status **APPROVED** (not IMPLEMENTED) · files: IMPLEMENTATION_STATUS.md
  · test: no false "IMPLEMENTED" claim
- [x] **1.10** — Update state files: [`PROJECT_STATE.md`](../../../PROJECT_STATE.md),
  [`NEXT_TASK.md`](../../../NEXT_TASK.md), [`CURRENT_CONTEXT.md`](../../../CURRENT_CONTEXT.md),
  [`ACTIVE_WORK.md`](../../../ACTIVE_WORK.md), [`OPEN_DECISIONS.md`](../../../OPEN_DECISIONS.md)
  · test: state files reference the new feature; no contradictions
- [ ] **1.11** — Final verification (TDD) — run cross-link checks; confirm
  no `runtime-registry/` directory created; confirm no code in `backend/`
  or `frontend/`; commit
  · command:
    ```bash
    rg -n "runtime-registry" backend frontend 2>/dev/null || echo "OK: no runtime-registry in code"
    git status --short
    ```
- [ ] **1.12** — Update IMPLEMENTATION_STATUS, PROJECT_STATE, HANDOFF,
  execution ledger

**Definition of done — Phase 1:**

- ADR-0016 is **Accepted** (status visible in `ADR_INDEX.md`).
- All 5 spec files exist in the feature folder.
- No code, no migrations, no `runtime-registry/` directory, no adapter
  changes, no Docker wiring, no F5-TTS implementation.
- Per Constitution §22, the ADR is **APPROVED, not IMPLEMENTED**.

---

## Phase 2 — Runtime Registry + Runtime Manager skeleton (deferred)

**Goal:** Implement the Runtime Registry loader, the Runtime Manager
skeleton, and the `DockerRuntimeDriver`. No model is migrated yet.

- [ ] **2.1** — Define `RuntimeDescriptor` Pydantic model in
  `backend/app/services/runtime_types.py`
  · files: `backend/app/services/runtime_types.py`
  · test: `tests/test_runtime_descriptor.py` — schema validation,
    default values, required fields, image spec, capabilities subset
- [ ] **2.2** — Implement `RuntimeRegistryLoader` to read `runtime.yaml`
  from the future `runtime-registry/` directory (or a configured path)
  · files: `backend/app/services/runtime_registry.py`
  · test: `tests/test_runtime_registry.py` — discover runtimes, parse
    descriptors, handle malformed descriptors, support hot reload
- [ ] **2.3** — Define the `RuntimeDriver` protocol in
  `backend/app/services/runtime_driver.py` (as a `Protocol` with
  required operations from DESIGN §"Runtime Driver — interface contract")
  · files: `backend/app/services/runtime_driver.py`
  · test: `tests/test_runtime_driver_protocol.py` — structural
    conformance check
- [ ] **2.4** — Implement `DockerRuntimeDriver` (first driver) in
  `backend/app/services/drivers/docker_runtime_driver.py`
  · files: `backend/app/services/drivers/__init__.py`,
    `…/docker_runtime_driver.py`
  · test: `tests/test_docker_runtime_driver.py` — install / start /
    stop / status / health with mocked Docker client; never calls
    Docker from outside the driver
- [ ] **2.5** — Add a `lint_no_docker_outside_driver` check
  (a static AST scan that bans `import docker` outside the driver
  package)
  · files: `scripts/lint_no_docker_outside_driver.py`
  · test: N/A; runs in CI
- [ ] **2.6** — Implement `RuntimeManager` skeleton in
  `backend/app/services/runtime_manager.py`
  · files: `backend/app/services/runtime_manager.py`
  · test: `tests/test_runtime_manager.py` — registry-driven discovery,
    delegates install / start / stop / health to the driver
- [ ] **2.7** — Wire `RuntimeManager` into the FastAPI app startup
  (`backend/app/main.py` or wherever the model registry is initialized)
  · files: `backend/app/main.py`
  · test: integration test asserting the manager is registered and
    runtimes are discovered
- [ ] **2.8** — Add a `GET /api/v1/runtimes` endpoint (read-only
  discovery)
  · files: `backend/app/api/runtimes.py`
  · test: `tests/test_runtimes_api.py` — list, get by id, status,
    health
- [ ] **2.9** — Document the runtime endpoint resolution rule in
  ARCHITECTURE · files: ARCHITECTURE/runtime-architecture.md (new
  section §13 "Runtime Layer")
  · test: cross-link check
- [ ] **2.10** — Update IMPLEMENTATION_STATUS, PROJECT_STATE, HANDOFF,
  execution ledger · all status updates

**Definition of done — Phase 2:**

- `RuntimeManager` orchestrates; `DockerRuntimeDriver` executes.
- No Docker import outside the driver package.
- `GET /api/v1/runtimes` returns discovered runtimes.
- Existing in-process model execution **continues to work** unchanged.

---

## Phase 3 — Kokoro migration (deferred, first validation target)

**Goal:** Run Kokoro as a remote runtime service. Validate the full
install → activate → deactivate flow end-to-end against a real model.

- [ ] **3.1** — Build a minimal Kokoro runtime image
  `peakvox/kokoro-runtime` (HTTP server wrapping the existing
  `kokoro` pip package)
  · files: `runtime-registry/kokoro/Dockerfile`,
    `…/docker-compose.yml`, `…/runtime.yaml`, `…/env.example`,
    `…/README.md`
  · test: image builds; container starts; `GET /health` returns 200
- [ ] **3.2** — Implement `HTTPTransport` for adapters
  (request/response + streaming for audio)
  · files: `backend/app/services/adapter_transport/__init__.py`,
    `…/http_transport.py`
  · test: `tests/test_http_transport.py` — request signing, retries,
    timeouts, audio streaming
- [ ] **3.3** — Convert `KokoroAdapter` to use `HTTPTransport` against
  the Kokoro runtime service (gated by `KOKORO_RUNTIME_URL`; falls back
  to in-process when unset)
  · files: `backend/app/services/model_adapters/kokoro_adapter.py`
  · test: `tests/test_kokoro_runtime_adapter.py` — adapter talks to
    the runtime, falls back when env unset
- [ ] **3.4** — Add `Kokoro` model `runtime_binding` (a new column on
  `models`: nullable FK to a runtime descriptor id)
  · files: `backend/app/models/db.py`,
    `backend/app/core/migrations.py`
  · test: `tests/test_runtime_binding_migration.py` — additive +
    idempotent
- [ ] **3.5** — Wire `RuntimeManager.route(model_id)` into the
  generation pipeline; `KokoroAdapter` queries the manager to find
  the runtime endpoint
  · files: `backend/app/services/runtime.py`,
    `backend/app/services/runtime_manager.py`
  · test: `tests/test_runtime_routing.py`
- [ ] **3.6** — E2E validation report:
  `docs/.agents/VALIDATION/PROVIDER_VALIDATIONS/kokoro-runtime-validation-report.md`
  · files: validation report
  · test: real audio generated E2E through the runtime service
- [ ] **3.7** — Update IMPLEMENTATION_STATUS, PROJECT_STATE, HANDOFF,
  execution ledger

**Definition of done — Phase 3:**

- Kokoro runs in a container reachable at `peakvox/kokoro-runtime`.
- `KokoroAdapter` routes through the runtime service.
- Real audio generation works through the new path.
- The in-process fallback still works for environments without
  Docker.

---

## Phase 4 — F5-TTS as Runtime Service (deferred, reference implementation)

**Goal:** Implement F5-TTS as the **reference** runtime service. F5-TTS
becomes the canonical "how to add a new model" example.

- [ ] **4.1** — Build `peakvox/f5-runtime` image (CUDA + CPU variants
  per SPEC §"Critical conceptual distinction")
  · files: `runtime-registry/f5-tts/Dockerfile.cuda`,
    `…/Dockerfile.cpu`, `…/docker-compose.yml`, `…/runtime.yaml`,
    `…/env.example`, `…/README.md`
  · test: image builds; GPU + CPU variants both work
- [ ] **4.2** — Register F5-TTS in the canonical Model registry
  (`model_catalog.py`): `f5-tts` model with declared capabilities
  · files: `backend/app/services/model_catalog.py`
  · test: `tests/test_model_catalog_f5.py`
- [ ] **4.3** — Implement `F5Adapter` using `HTTPTransport` against
  the F5 runtime
  · files: `backend/app/services/model_adapters/f5_adapter.py`
  · test: `tests/test_f5_runtime_adapter.py`
- [ ] **4.4** — `F5Adapter.get_build_strategies()`:
  - `SOURCE_ASSET` → can_build=True, requires=`["source_asset"]`
  - `PRESET_VOICE` → can_build=False (F5-TTS is not a preset provider)
  · files: `…/f5_adapter.py`
  · test: `tests/test_f5_build_strategies.py`
- [ ] **4.5** — Document "Adding a new model" in
  `docs/.agents/ARCHITECTURE/runtime-architecture.md` §14 — the
  authoritative "how to add a runtime" runbook
  · files: ARCHITECTURE/runtime-architecture.md
  · test: cross-link + checklist
- [ ] **4.6** — E2E validation report:
  `docs/.agents/VALIDATION/PROVIDER_VALIDATIONS/f5-validation-report.md`
  · test: real audio generated E2E
- [ ] **4.7** — Update IMPLEMENTATION_STATUS, PROJECT_STATE, HANDOFF,
  execution ledger

**Definition of done — Phase 4:**

- F5-TTS runs as an isolated runtime.
- `F5Adapter` is the canonical example for "how to add a new model".
- Adding a new model requires only: model metadata + runtime
  descriptor + runtime image + adapter. No backend architectural
  changes.

---

## Phase 5 — Fish Audio migration (deferred)

**Goal:** Migrate Fish Audio from the existing in-process adapter
(stub) to a remote runtime service.

- [ ] **5.1** — Build `peakvox/fish-runtime` image
  · files: `runtime-registry/fish-audio/…`
  · test: image builds; `GET /health` returns 200
- [ ] **5.2** — Convert `FishAdapter` to use `HTTPTransport`
  · files: `backend/app/services/model_adapters/fish_adapter.py`
  · test: `tests/test_fish_runtime_adapter.py`
- [ ] **5.3** — E2E validation report (deferred; Fish S2 Pro
  hardware blocker may still apply — see
  `docs/.agents/VALIDATION/PROVIDER_VALIDATIONS/`)
  · files: validation report (or blocker amendment)
  · test: real audio generated if hardware permits; otherwise
    provider-validation blocked, architecture-validated
- [ ] **5.4** — Update IMPLEMENTATION_STATUS, PROJECT_STATE, HANDOFF,
  execution ledger

**Definition of done — Phase 5:**

- Fish Audio runs as an isolated runtime (architecture-validated;
  provider-validated when hardware permits).

---

## Phase 6 — OmniVoice migration (deferred)

**Goal:** Migrate OmniVoice, the original model, to a remote runtime
service. The most demanding migration because OmniVoice is the most
deeply integrated.

- [ ] **6.1** — Build `peakvox/omnivoice-local` and
  `peakvox/omnivoice-cloud` images
  · files: `runtime-registry/omnivoice/…`
  · test: both images build; both serve `GET /health` 200
- [ ] **6.2** — Convert `OmniVoiceAdapter` to use `HTTPTransport`
  · files: `backend/app/services/model_adapters/omnivoice_adapter.py`
  · test: `tests/test_omnivoice_runtime_adapter.py`
- [ ] **6.3** — E2E validation report:
  `docs/.agents/VALIDATION/PROVIDER_VALIDATIONS/omnivoice-runtime-validation-report.md`
  · test: real audio generated E2E through the new path
- [ ] **6.4** — Update IMPLEMENTATION_STATUS, PROJECT_STATE, HANDOFF,
  execution ledger

**Definition of done — Phase 6:**

- OmniVoice runs as an isolated runtime, both Local and Cloud variants.
- All four providers (OmniVoice, Kokoro, F5-TTS, Fish) have remote
  runtime services available.

---

## Phase 7 — Remove direct in-process model execution (deferred)

**Goal:** Now that every model has a remote runtime option, remove the
in-process path. The backend image becomes fully model-agnostic.

- [ ] **7.1** — Remove the in-process imports from
  `backend/app/services/model_adapters/`:
  - `import torch`, `import transformers` (no longer used)
  - `import kokoro` (replaced by HTTP transport)
  - `import f5_tts` (replaced by HTTP transport)
  - `import fish_audio` (replaced by HTTP transport)
  · files: all four adapter files
  · test: `tests/test_backend_image_isolation.py` — `pip list` on the
    backend image no longer includes these packages
- [ ] **7.2** — Remove `omnivoice_service.py`'s `from_pretrained` /
  `generate_async` (now in the runtime)
  · files: `backend/app/services/omnivoice_service.py`
  · test: no remaining direct calls
- [ ] **7.3** — Update the backend `Dockerfile` to remove model
  dependencies from the image
  · files: `backend/Dockerfile`, `docker-compose.yml`
  · test: `tests/test_backend_image_isolation.py` (above)
- [ ] **7.4** — Update `pyproject.toml` / `requirements.txt` to drop
  model packages
  · files: `backend/pyproject.toml`,
    `backend/requirements.txt` (if present)
  · test: lint / pip check
- [ ] **7.5** — Update ARCHITECTURE/runtime-architecture.md to reflect
  the final state — "Backend = orchestration only"
  · files: ARCHITECTURE/runtime-architecture.md
  · test: cross-link + lint
- [ ] **7.6** — Update IMPLEMENTATION_STATUS to mark all adapter
  rows as `IMPLEMENTED (arch) / VALIDATED (provider)`
  · test: status reflects reality
- [ ] **7.7** — Update PROJECT_STATE, NEXT_TASK, CURRENT_CONTEXT,
  ACTIVE_WORK, HANDOFF, execution ledger

**Definition of done — Phase 7:**

- The backend image contains **no** model-specific dependencies.
- All inference is through Runtime Services.
- The architecture matches the spec end-to-end.
- Cloud edition can drop in `KubernetesRuntimeDriver` without
  touching business logic.

---

## Verify (per phase)

Each phase ends with:

```bash
# TDD: full test suite green
docker compose run --rm backend bash -c "python -m pytest tests/ -q"

# Frontend (where applicable)
cd frontend && pnpm lint && pnpm typecheck && pnpm test

# Architecture compliance (after Phase 2)
python scripts/lint_no_docker_outside_driver.py
python scripts/lint_architecture_invariants.py  # constitution checker

# Cross-link resolution
rg -n "\[\[\(|>>|\.md\)" docs/.agents/ | xargs -I{} echo {}  # visual check
```

## Update state files (per phase)

- [ ] `IMPLEMENTATION_STATUS.md` — add new rows / update status
- [ ] `PROJECT_STATE.md` — phase progress
- [ ] `NEXT_TASK.md` — promote next item from backlog
- [ ] `CURRENT_CONTEXT.md` — operational memory
- [ ] `ACTIVE_WORK.md` — in-flight / paused
- [ ] `HANDOFF.md` — agent-to-agent transfer notes
- [ ] `IMPLEMENTATION/EXECUTION_HISTORY/EXECUTION_LEDGER.md` — append entry

---

**Related:** [`SPEC.md`](./SPEC.md) · [`DESIGN.md`](./DESIGN.md) ·
[`VALIDATION.md`](./VALIDATION.md) · [`STATUS.md`](./STATUS.md) ·
[`adr-0016-models-as-runtime-services.md`](../../../DECISIONS/adr-0016-models-as-runtime-services.md)

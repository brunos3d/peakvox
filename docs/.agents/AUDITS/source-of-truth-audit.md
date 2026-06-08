# Runtime Registry Source of Truth Audit (Task 1)

**Date:** 2026-06-08 (refined 2026-06-08 with R9)
**Subject:** Identify every source of model/runtime metadata; classify each; propose the single source of truth.
**Status:** AUDIT COMPLETE + R9 REFINED
**Result:** **The Models page renders a COMPOSED VIEW: Model Catalog + Runtime Registry + Runtime Operational State. The runtime-registry is NOT the sole source of truth for the Models page; it AUGMENTS the model cards with infrastructure metadata. The catalog and the registry are layered, not duplicated. (R9 refinement.)**

---

## Sources of model/runtime metadata (today)

| # | Source | Location | Authoritative? | Status |
|---|---|---|---|---|
| 1 | `BUILTIN_MODELS` (4 entries) | `backend/app/services/model_catalog.py` | **Yes** (catalog) | Authoritative for the **catalog** layer (id, name, capabilities, edition, supported_tags, etc.). |
| 2 | `models` table (DB) | seeded from `BUILTIN_MODELS` in `migrations.py::_seed_builtin_models` | **Yes** (persistence) | The persistence layer; status column reflects the legacy DB-status mock. |
| 3 | `ModelRegistry` (in-memory) | `backend/app/services/model_registry.py` | Cached (DB) | Populated at startup from the DB via `wire_registry_from_database`. The cache the API layer reads. |
| 4 | `runtime-registry/` (file) | `runtime-registry/kokoro-82m/descriptor.json` | **Yes** (runtime) | Authoritative for **runtime** metadata: image, build, port, capabilities subset, requirements, lifecycle, model_binding. |
| 5 | `RuntimeRegistry` (in-memory) | `backend/app/services/runtime_registry.py` | Cached (file) | In-memory index of the on-disk runtime-registry/. Read by `RuntimeManager` only. |
| 6 | `Settings` env vars | `backend/app/core/config.py` | Cached (env) | Adapter data-plane config (`KOKORO_RUNTIME_URL`, `FISH_AUDIO_SERVER_URL`); runtime control plane (`RUNTIME_SERVICE_ENABLED`); legacy model defaults (`OMNIVOICE_MODEL`). |
| 7 | `runtime-registry/kokoro-82m/descriptor.json` (R2 `build` block) | the file | Cached (file) | The CE build metadata; consumed by the build script, not by the manager. |
| 8 | Frontend `useModels()` | `frontend/src/hooks/use-models.ts` | Derived (API) | Reads `/api/models`; the only model data the UI sees. |
| 9 | Frontend `Model` type | `frontend/src/types` | Cached (API) | TypeScript type for the API response. |
| 10 | Frontend hardcoded model ids (e.g. `kokoro-base`, `omnivoice-base`) | search results: `Kokoro 82M`, `OmniVoice Base`, `Fish Audio S2 Pro` are baked into Models page UI labels and the legacy mock. | Cached (legacy) | These need to be removed; the UI must render from runtime-registry data. |
| 11 | `models.legacy_status_mock` (`model_lifecycle.py` docstring) | `backend/app/services/model_lifecycle.py:56-62` | Deprecated (post-P4) | The "real artifact download is intentionally mocked for now" comment. P4 has replaced it with `RuntimeManager.install/start`. The mock is now the fallback when no manager is attached. |

## Classification summary

| Class | Sources | Authority |
|---|---|---|
| **Authoritative — catalog (domain)** | `BUILTIN_MODELS` (the seed), the `models` table | `BUILTIN_MODELS` is the source; the DB is the persistence. |
| **Authoritative — runtime (infrastructure)** | `runtime-registry/<id>/descriptor.json` | The on-disk descriptor is the source; `RuntimeRegistry` is the in-memory index. |
| **Cached — DB → memory** | `ModelRegistry` | Cached view of the DB. |
| **Cached — file → memory** | `RuntimeRegistry` | Cached view of the on-disk registry. |
| **Derived — env / config** | `Settings` | Adapter URLs, runtime subsystem flag, model defaults. |
| **Derived — UI** | `useModels()`, `Model` type, `FALLBACK_TAGS` | React Query wrappers; type mirrors the API response. |
| **Deprecated** | Legacy `models.legacy_status_mock`, the `OmniVoice Singing + Emotion` and `Fish Audio S2 Pro` hardcoded catalog entries with no runtime descriptor | The legacy path; replaced by the runtime path. |

## The current mismatch (the audit's headline finding)

The **Models page** renders from the **DB-backed catalog** (`BUILTIN_MODELS` seeded into the `models` table). The Models page therefore shows four models:

  - `omnivoice-base` (OmniVoice Base)
  - `omnivoice-singing` (OmniVoice Singing + Emotion)
  - `kokoro-base` (Kokoro 82M)
  - `fish-audio-s2` (Fish Audio S2 Pro)

The **Runtime Registry** contains only:

  - `kokoro-82m` (Kokoro 82M Runtime)

The other three catalog entries have **no runtime descriptor**. The Models page therefore shows three "runtimes" that do not exist in the runtime-registry/, and only one that does.

This is the **mismatch** the user is calling out. The fix (per the original audit) was to make the Models page render from the runtime-registry when the runtime subsystem is enabled. **R9 REJECTS this fix:** the runtime-registry is infrastructure metadata that AUGMENTS the model cards, not the source of truth that REPLACES them. See [`r9-models-page-composition.md`](r9-models-page-composition.md) for the architectural clarification. The right fix is the **composed view**: Catalog + Registry + State, with the catalog as the primary entity and the runtime as an infrastructure section of the model card.

## The single source of truth (proposed)

| Concern | Authoritative source | Reason |
|---|---|---|
| **Catalog entity** (Model: id, name, capabilities, supported_tags, edition) | `BUILTIN_MODELS` → `models` table | Models are domain entities (ADR-0003). They are the catalog, not the runtime. |
| **Runtime entity** (RuntimeDescriptor: image, build, port, lifecycle, model_binding) | `runtime-registry/<id>/descriptor.json` | Runtimes are infrastructure (ADR-0016). They are deployment units, not the catalog. |
| **Runtime operational state** (state, host, port, last_request_at) | `RuntimeManager._instance_cache` | The manager is the only owner of operational state (Runtime Activation Audit). |
| **Runtime control** (install/start/stop/etc.) | `RuntimeManager` | The manager is the orchestration boundary. |
| **Adapter data-plane** (KOKORO_RUNTIME_URL, FISH_AUDIO_SERVER_URL) | `Settings` | Adapter routing is independent of infrastructure. |
| **Runtime subsystem opt-in** (RUNTIME_SERVICE_ENABLED) | `Settings` | The flag is infrastructure wiring (control plane). |

**The two layers are:**
  - **Domain layer:** Models. Owned by `BUILTIN_MODELS` (seed) → `models` table (persistence).
  - **Infrastructure layer:** Runtimes. Owned by `runtime-registry/<id>/descriptor.json`.

**A Model maps to one or more Runtimes** via the descriptor's `spec.model_binding.model_id`. The Models page's "this model is installed / running" status is **derived from the runtime state of the runtimes that serve it**.

## The composed view (R9)

Per R9, the Models page renders a **composed view** from the three sources:

| Input | Layer | Visibility |
|---|---|---|
| Model Catalog | Domain | **Always visible** (catalog is the primary entity). |
| Runtime Registry | Infrastructure | **Augments** the model card. A model may exist without a runtime. |
| Runtime Operational State | Live | **Augments** the runtime section. A model without a runtime has no state. |

The endpoint that joins these is `GET /api/models/with-runtimes` (available whether or not the runtime subsystem is enabled; the catalog portion is always present, the runtime portion is the augmentation).

The previous fix (per the original audit) was to make the Models page render from the runtime-registry. R9 REJECTS that fix. See [`r9-models-page-composition.md`](r9-models-page-composition.md) for the full reasoning.

## What the Models page should render (proposed)

The Models page should query the **runtime-registry** when the runtime subsystem is enabled. The rendered list is the set of runtimes in the registry, joined with their cached state from the manager.

When the runtime subsystem is disabled (CE default, `RUNTIME_SERVICE_ENABLED=false`):
  - The Models page renders the legacy catalog from `/api/models` (BUILTIN_MODELS).
  - Install/Activate are pure DB-status transitions.
  - This is the fallback path; documented in `model_lifecycle.py`.

When the runtime subsystem is enabled (`RUNTIME_SERVICE_ENABLED=true`):
  - The Models page renders from `/api/runtimes` (the new endpoint).
  - The list contains exactly the runtimes in the registry, joined with their cached state.
  - Install/Activate/Deactivate/Update/Remove delegate to `RuntimeManager`.
  - Model status is **derived** from the runtime state.

## Open questions for the convergence (Tasks 2-7)

1. Should the Models page render from `/api/runtimes` (infrastructure view) or from a joined view (`/api/models?include=runtimes`)?
   - **Recommendation:** the new `/api/runtimes` endpoint is the infrastructure view; `/api/models` stays as the catalog view. The Models page, when RUNTIME_SERVICE_ENABLED=true, calls `/api/runtimes`; otherwise `/api/models`. The two are layered, not duplicated.

2. Should the catalog's `OmniVoice Singing + Emotion` (id=`omnivoice-singing`) be removed from `BUILTIN_MODELS` since no runtime descriptor exists for it?
   - **Recommendation:** yes. The catalog should match the runtime-registry. Models without a runtime are either:
     - Deprecated (no longer supported), or
     - On the roadmap (descriptor pending).
   - The list of unsupported models belongs in `OPEN_DECISIONS.md` as a separate ADR, not in the seed.

3. Should the seed's "Kokoro 82M" (id=`kokoro-base`) be unified with the runtime-registry's `kokoro-82m`?
   - **Yes:** the catalog id `kokoro-base` (Model.id) and the runtime id `kokoro-82m` (RuntimeDescriptor.metadata.id) are two different identifiers. The relationship is `RuntimeDescriptor.spec.model_binding.model_id == "kokoro-base"`. The Models page can show one card per model, with the runtime state joined in.

## Deliverables for Tasks 2-7 (this audit's follow-ups)

- **Task 2:** Models page backend integration audit. Trace UI → API → Manager → Registry.
- **Task 3:** Models page convergence. New `/api/runtimes` endpoint; new `useRuntimes()` hook; Models page renders from runtime-registry.
- **Task 4:** Runtime lifecycle visibility. New `/api/runtimes/{id}/state` endpoint; UI surfaces real state.
- **Task 5:** Installation progress. Long-poll / SSE endpoint for install progress; UI shows step-by-step state.
- **Task 6:** Activation visibility. Long-poll / SSE endpoint for activate progress; UI shows "Starting runtime..." → "Waiting for readiness..." → "Runtime ready".
- **Task 7:** Runtime Operations Panel. Expanded UI with runtime_id, image_tag, image_digest, runtime_version, readiness, uptime, health.

## The fix, in one sentence (R9 updated)

The Models page must render the **composed view** from `GET /api/models/with-runtimes`: Model Catalog + Runtime Registry + Runtime Operational State. The catalog is the primary entity; the runtime-registry augments the model card with infrastructure metadata; the runtime state is the live view. A model may exist without a runtime; a runtime's lifecycle actions only appear when a runtime descriptor exists. The runtime-registry is **not** the source of truth for the Models page.

---

**See also:**
[`docs/.agents/AUDITS/models-page-integration-audit.md`](models-page-integration-audit.md) (Task 2)
·
[`docs/.agents/SPECS/FEATURES/runtime-services-implementation/SPEC.md`](../SPECS/FEATURES/runtime-services-implementation/SPEC.md) (R1-R8)
·
[`runtime-registry/kokoro-82m/`](../../../runtime-registry/kokoro-82m/) (R8 reference)

# Audit — "Runtime == Variant" Assumptions (Task 26, Phase B)

> **Purpose.** Inventory every place in the codebase that assumes a runtime is
> a single, indivisible (runtime + weights + checkpoint) unit, so the
> [ADR-0018](../../DECISIONS/adr-0018-runtime-variants-architecture.md)
> migration is grounded in code reality, not intent. Each finding cites
> `file:line` evidence.
>
> **Scope.** Backend runtime subsystem, runtime-registry descriptors, runtime
> services (`server.py`), the runtime API, and the frontend runtime/models
> surface.
>
> **Verdict at a glance.** The assumption "runtime == variant" is **pervasive
> but shallow**: it lives almost entirely in *data shape and directory
> convention*, not in deep control flow. The `RuntimeRegistry` already indexes
> `model_id → [runtime_ids]` (many-to-one), and `RuntimeManager.resolve` is
> keyed on `model_id`, so the resolution spine can absorb variants additively.
> No destructive refactor is required for Phases 1–2.

---

## Legend

- 🟥 **Hard assumption** — actively encodes runtime == variant; must change to
  support variants (but can be changed additively).
- 🟧 **Soft assumption** — convention/shape that *implies* the collapse; needs
  extension, not replacement.
- 🟩 **Already variant-ready** — supports a Runtime → many bindings shape today.
- ⚠️ **Collision risk** — "variant" already means **VoiceVariant** here;
  naming must stay disjoint.

---

## 1. Runtime Descriptor (`backend/app/services/runtime_types.py`)

| # | Finding | Evidence | Class |
|---|---|---|---|
| 1.1 | `RuntimeModelBinding` binds a runtime to **exactly one** `model_id`. | `runtime_types.py:234-239` | 🟧 |
| 1.2 | `RuntimeImage` is the only weights-bearing concept; there is no checkpoint/variant field. Weights are implicitly the image (or downloaded at boot). | `runtime_types.py:138-162`, `RuntimeDescriptorSpec` `runtime_types.py:370-395` | 🟥 |
| 1.3 | `metadata.id` is a single DNS-label per runtime directory; `f5-tts-base` encodes the variant into the runtime id. | `runtime_types.py:281-291`; descriptors `runtime-registry/f5-tts-base/descriptor.json` | 🟧 |
| 1.4 | Capabilities are declared on the runtime and validated as a subset of the **bound model's** caps — there is no per-variant capability surface. | `runtime_types.py:337-367` | 🟧 |
| 1.5 | The descriptor schema is a **closed** Pydantic model (no `extra` allowed); a `variants` field cannot sneak in untyped — it must be added explicitly. | `RuntimeDescriptorSpec` `runtime_types.py:370-395` | 🟧 |

**Migration note.** Adding an **optional** `RuntimeVariantDescriptor`
(`kind: RuntimeVariant`) and an optional `variants` reference is purely
additive: existing descriptors validate unchanged. This is exactly the
Phase D primitive shipped with ADR-0018.

---

## 2. Runtime Registry loader (`backend/app/services/runtime_registry.py`)

| # | Finding | Evidence | Class |
|---|---|---|---|
| 2.1 | Discovery walks `<root>/<id>/descriptor.json` — **one descriptor per directory**. A `variants/` subfolder is invisible to the loader today. | `runtime_registry.py:104-129`, `_DESCRIPTOR_FILENAME = "descriptor.json"` `:99` | 🟥 |
| 2.2 | The registry **already** indexes `model_id → [runtime_ids]` and exposes `list_for_model` returning a **list** — the spine is many-to-one ready. | `runtime_registry.py:51,60,70-74` | 🟩 |
| 2.3 | Indexes are id/model/capability only; no variant index exists. | `runtime_registry.py:49-62` | 🟧 |
| 2.4 | Loader is JSON-only for now (YAML deferred per ADR-0017); a variants loader must follow the same format-agnostic pattern. | `runtime_registry.py:17-21,131-159` | 🟧 |

**Migration note.** A variant loader (`<root>/<id>/variants/*.json`) slots in
beside `_load_one` without touching the runtime walk. Bad variant files must
be skipped-and-logged exactly like bad descriptors (`:117-125`).

---

## 3. Runtime Manager (`backend/app/services/runtime_manager.py`)

| # | Finding | Evidence | Class |
|---|---|---|---|
| 3.1 | `resolve(model_id, hint)` is keyed on **model_id**, sorts runtimes by default/priority, and returns one endpoint. It has no variant dimension. | `runtime_manager.py:213-271` | 🟧 |
| 3.2 | The instance cache is keyed by **`runtime_id`** (`dict[str, RuntimeInstance]`). A loaded-variant dimension does not exist at the manager level. | `runtime_manager.py:123,135-143,263-266` | 🟧 |
| 3.3 | All lifecycle ops (install/update/remove/start/stop/status) are keyed by `runtime_id`; there is no "add variant" / "load variant" operation. | `runtime_manager.py:339-570` | 🟥 |
| 3.4 | Operation state (`RuntimeOperation`) is per-runtime; `RuntimeOperationType` has no variant verbs. | `runtime_manager.py:124-126`; `runtime_operation.py` | 🟧 |
| 3.5 | The manager correctly **never** references Voice/VoiceVariant/Artifact (per the Runtime Activation Audit) — variants must preserve this; a RuntimeVariant load is infrastructure only. | `runtime_manager.py:119-123` (comment) | 🟩 |

**Migration note.** Variant selection belongs **inside** resolution: once a
`model_id` picks a descriptor, the chosen model's variant binding selects the
`runtime_variant` to pass downstream. `resolve()` can return the variant id on
`RuntimeResolution` additively (new optional field). No signature break.

---

## 4. Docker Runtime Driver (`backend/app/services/drivers/docker_runtime_driver.py`)

| # | Finding | Evidence | Class |
|---|---|---|---|
| 4.1 | Container labels carry `peakvox.runtime.model_id` (single model) — encodes the 1:1 binding into the substrate. | `docker_runtime_driver.py:191` | 🟧 |
| 4.2 | The driver **already shares the backend's named `/data` volume** with every runtime container — the weights-cache mechanism for variants exists today. | `docker_runtime_driver.py:237-255,609-625` | 🟩 |
| 4.3 | `_environment(desc)` builds container env from the descriptor; a variant could be passed via env or a `/data` mount without a new mechanism. | `docker_runtime_driver.py:197-235` | 🟩 |
| 4.4 | The driver is substrate-only and reads no weights/checkpoint concept — variant download is **not** the driver's job (it belongs to a variant-provisioning service / the runtime service itself). | whole file; ADR-0016 invariant 8 | 🟩 |

**Migration note.** The shared `/data` volume + `/data/runtime-weights/<rt>/<variant>/`
convention (ADR-0018 storage model) needs **no driver change** for CE.

---

## 5. Runtime Service Contract / `server.py` (all three runtimes)

| # | Finding | Evidence | Class |
|---|---|---|---|
| 5.1 | The service loads **one** model singleton (`_load_state: unloaded→loading→ready→failed`, one `_load_lock`). No keyed multi-checkpoint registry. | `runtime-registry/f5-tts-base/server.py:53-169` | 🟥 |
| 5.2 | `GenerateRequest.variant_id` **already exists and means VoiceVariant** (voice realization). The RuntimeVariant selector must use a **different** field name. | `f5-tts-base/server.py:88-91` | ⚠️ |
| 5.3 | `POST /v1/variants/build` exists and is the **VoiceVariant** build path (returns 501, deferred to in-process adapter). Must **not** be overloaded for RuntimeVariant. | `f5-tts-base/server.py:28,102`; descriptor `service.build_path` | ⚠️ |
| 5.4 | `GET /v1/metadata` advertises capabilities/supported surface but no `variants` list. | `f5-tts-base/server.py:10-11` | 🟧 |
| 5.5 | F5 serializes inference behind a module-level lock and clears the DiT text-embed cache per call (Task 24, commit `0370ddd`). Variant switching must respect this lock and clear cache on variant change. | `server.py` inference path; ADR-0018 §"Note for F5-TTS" | 🟥 (constraint) |

**Migration note.** Generalize the singleton to a keyed, LRU-bounded
`_variants` registry with a `_default_variant_id` eager-loaded on `/ready`
(ADR-0018 §"In-process variant switching"). Add `runtime_variant` to
`GenerateRequest` **alongside** the existing `variant_id`.

---

## 6. Runtime API (`backend/app/api/runtime_api.py`)

| # | Finding | Evidence | Class |
|---|---|---|---|
| 6.1 | All lifecycle routes are `/{runtime_id}/...` — install/start/stop/update/remove. No variant routes. | `runtime_api.py:383-511` | 🟧 |
| 6.2 | `GET /models/with-runtimes` is the Models page source of truth: `model → [runtimes]`. Variant-family models (`omnivoice-singing`) render as **separate top-level models** today. | `runtime_api.py:540-617` | 🟧 |
| 6.3 | `RuntimeOperationType` includes `build` (VoiceVariant build), reinforcing that "variant" already means VoiceVariant in this layer. | `runtime_api.py` operation payloads; frontend `types/index.ts:485` | ⚠️ |
| 6.4 | The composed view sorts runtimes by `model_binding.is_default`/`priority` — the same selection logic as `resolve`; a variant grouping can reuse it. | `runtime_api.py:582-602` | 🟩 |

**Migration note.** Phase 3 adds an optional `variants` array to each runtime
in the composed payload (additive). Grouping models by runtime family is a
**presentation** change, not an API dimension change.

---

## 7. Catalog (`backend/app/services/model_catalog.py`) — the live evidence

| # | Finding | Evidence | Class |
|---|---|---|---|
| 7.1 | Variant-family models already exist as **distinct catalog rows**: `omnivoice-base`+`omnivoice-singing`, `f5-tts-base`+`f5-tts-research`, `fish-audio-s2`+`fish-audio-research`. | `model_catalog.py:64,69,153,158,271,275,315,342,348,366` | 🟩 |
| 7.2 | Models carry a `provider`/family field (`omnivoice`, `f5-tts`, `fish-audio`, `kokoro`) — the natural grouping key for the variant UI. | `model_catalog.py:69,215,275,348` | 🟩 |

**Implication.** ADR-0018's chosen binding ("variant realizes a model
binding; Model stays the public selector") is the **lowest-friction** path:
the catalog already represents variant-family models as cheap rows. The only
expensive duplication today is the *runtime image*, which is exactly what the
migration removes.

---

## 8. Frontend (`frontend/src/types/index.ts`, `hooks/use-runtimes.ts`, `components/models/`)

| # | Finding | Evidence | Class |
|---|---|---|---|
| 8.1 | `RuntimeModelBinding` (TS) mirrors the backend's single `model_id`. | `types/index.ts:534-538` | 🟧 |
| 8.2 | "Variant" already means **VoiceVariant** in the frontend (`VariantListItem`, `VariantSummaryItem`, ADR-0008/0009). New UI must label RuntimeVariants distinctly (e.g. "model variant" / runtime-family chip). | `types/index.ts:369-396` | ⚠️ |
| 8.3 | `RuntimeCard` / `RuntimeStatePayload` are per-runtime; the Models page query key is `["models-with-runtimes"]`. | `types/index.ts:549-563`; `hooks/use-runtimes.ts:104,183` | 🟧 |
| 8.4 | Comment in types already states a Runtime "is NOT a Voice and is NOT a Model … `model_binding.model_id` joins a runtime to the catalog" — the variant axis is simply absent, not contradicted. | `types/index.ts:457-468` | 🟩 |

---

## Summary of required changes (by phase, see migration plan)

| Layer | Today | Change needed | Disruption |
|---|---|---|---|
| Descriptor | 1.1, 1.2 single model/no checkpoint | + optional `RuntimeVariantDescriptor` | additive ✅ |
| Registry loader | 2.1 one descriptor/dir | + `variants/*.json` loader | additive ✅ |
| Registry index | 2.3 no variant index | + variant index | additive ✅ |
| Manager resolve | 3.1 model-keyed | + variant on `RuntimeResolution` | additive ✅ |
| Manager lifecycle | 3.3 no add/load variant | + variant ops | additive ✅ |
| Driver | 4.2 already shares `/data` | none for CE | none ✅ |
| `server.py` | 5.1 single singleton | keyed LRU + `/v1/variants*` | per-runtime, isolated ✅ |
| Runtime API | 6.1/6.2 runtime-keyed | + variant fields/routes | additive ✅ |
| Frontend | 8.x runtime-keyed | + variant grouping/chips | additive ✅ |

**Conclusion.** Every required change is **additive and backward-compatible**.
No table is dropped, no public API field is removed, no existing runtime
directory stops working. The two highest-care items are the **VoiceVariant
naming collision** (§5.2, §5.3, §8.2 — keep fields/types disjoint) and the
**F5 inference serialization constraint** (§5.5 — variant switching must
respect the lock + cache clear). Both are documented in ADR-0018 and the
migration plan.

---

**Related:** [ADR-0018](../../DECISIONS/adr-0018-runtime-variants-architecture.md) ·
[ADR-0016](../../DECISIONS/adr-0016-models-as-runtime-services.md) ·
[ADR-0017](../../DECISIONS/adr-0017-runtime-services-implementation.md) ·
[runtime-activation-audit.md](runtime-activation-audit.md) ·
[runtime-service-readiness-audit.md](runtime-service-readiness-audit.md)

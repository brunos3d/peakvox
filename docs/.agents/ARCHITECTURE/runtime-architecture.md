# PeakVox — Runtime Architecture

**Owns:** the **Runtime Layer** — the core differentiator of PeakVox. The runtime is the
component that turns "a request for a voice + a model + text" into rendered speech, while
abstracting away which model, which provider, which device, and (later) which machine. It is
a **first-class architectural component**, not an implementation detail.

> This document realizes the [Vision](../CONTEXT/VISION.md): *OpenRouter for Voice + Ollama for
> Voice*. See also [Domain](domain-architecture.md), [ADR-0002](../DECISIONS/adr-0002-model-as-first-class-entity.md),
> [ADR-0003](../DECISIONS/adr-0003-model-capability-contract.md), [Cloud](cloud-architecture.md).
>
> **Status — implemented (Phases 3.5–3.7) + Runtime-Service architecture accepted (ADR-0016, 2026-06-07).**
> The runtime core exists in code: the
> `ModelAdapter` contract (`backend/app/services/model_adapter.py`), `PeakVoxRuntime`
> (`backend/app/services/runtime.py`), the capability contract
> (`backend/app/services/capabilities.py`), and the OmniVoice/OmniVoiceSinging adapters
> (`backend/app/services/model_adapters/`). The single Voice ID → many variants → one runtime
> property is validated by `backend/tests/test_multimodel_resolution.py`. Distributed/cloud
> execution (§9.2) is **formalized** by [ADR-0016 — Models as Runtime Services](../DECISIONS/adr-0016-models-as-runtime-services.md);
> see also [`../SPECS/FEATURES/models-as-runtime-services/`](../SPECS/FEATURES/models-as-runtime-services/).
> Existing in-process model execution continues unchanged; the 7-phase migration in ADR-0016
> replaces it across Phases 2–7.

---

### Frontend→Backend generation contract

The generation POST body is the **frontend→backend contract** and must include every field
the backend needs to route correctly:

```
POST /generate  { text, model_id?, voice_profile_id?, … }
```

- `model_id`: **MUST** be included when the user has explicitly selected a model. When
  `null`/absent the backend falls back to the platform default. The frontend MUST read the
  selected model from the UI state (e.g. Zustand `selectedModelId`) and pass it as `model_id`.
  Forgetting this field causes the backend to validate tags/capabilities against the wrong
  model — the default instead of the user's selection.

This contract is separate from the backend capability validation (which is always correct per
the model that arrives). The integration point is the frontend → backend payload.

## 1. Why the runtime is the product

Applications, the public API, the marketplace, and developer SDKs all depend on **one stable
surface**: address a `Voice` + a `Model`, get speech. Everything that makes that surface
stable while models churn underneath — resolution, routing, loading, VRAM, orchestration — is
the runtime. PeakVox's defensibility is the runtime, not any single model. Models are
commodities that plug into it.

## 2. The layered flow

```
        User / API / SDK / Marketplace
                    │  voice_id + model + text + params
                    ▼
        ┌───────────────────────────────┐
        │        PeakVox Runtime        │   resolution · routing · orchestration
        │  (model-agnostic core)        │   lifecycle · GPU/VRAM · caching · async
        └───────────────┬───────────────┘
                        │  ModelAdapter contract (stable)
                        ▼
        ┌───────────────────────────────┐
        │         Model Adapter         │   per-model translation to/from PeakVox concepts
        │  OmniVoice | Fish | Kokoro …  │
        └───────────────┬───────────────┘
                        │  provider/library calls
                        ▼
        ┌───────────────────────────────┐
        │        Model Provider         │   the actual engine/library + weights
        └───────────────┬───────────────┘
                        ▼
                    Inference  →  audio
```

**Boundary rule:** everything above the `ModelAdapter` line is model-agnostic and must never
import a model implementation. Everything below the line is model-specific and must never know
about Voices, marketplace, billing, or HTTP. The adapter is the only translation point.

**Mapping to today's code:** the existing `app/services/model_registry.py` is the runtime
core; `app/services/model_providers/base.py::ModelProvider` is the **first, partial instance
of the `ModelAdapter` contract** (it implements `load`/`offload`/`generate`/`is_loaded`).
Phases 2–3 grow it toward the full adapter surface in §6 without changing call sites.

## 3. Runtime responsibilities & boundaries

| Responsibility | In scope | Out of scope (delegated) |
|---|---|---|
| Voice resolution (`public_voice_id` → Voice) | ✅ | persistence → repositories |
| Variant resolution (`Voice + Model` → VoiceVariant) | ✅ | artifact storage → object storage |
| Variant provisioning + synchronization ([ADR-0010](../DECISIONS/adr-0010-voice-source-assets-and-automatic-variant-provisioning.md)) | ✅ | artifact production → adapter `build_variant()` |
| Model routing (explicit + `auto`) | ✅ | capability truth → [ADR-0003](../DECISIONS/adr-0003-model-capability-contract.md) |
| Adapter lifecycle (install/load/unload/health) | ✅ | weights/inference → adapter/provider |
| GPU allocation + VRAM management | ✅ | hardware provisioning → Cloud infra |
| Model caching (load/offload policy) | ✅ | — |
| Generation pipeline + async jobs | ✅ | job persistence → DB |
| Distributed execution (future) | ✅ | scheduling substrate → Cloud queue/workers |
| Usage/royalty events | emits | accounting → Monetization |

The runtime **emits** domain events (`variant.requested`, `generation.completed`) and depends
on **none** of the commercial contexts ([Domain §9](domain-architecture.md)).

## 4. Interaction with Voice, VoiceVariant, and Model

The runtime is the place where the [Vision's](../CONTEXT/VISION.md) core principle becomes executable:

```
resolve(public_voice_id) ───────────────► Voice        (universal identity; ADR-0001)
route(model | "auto", Voice, request) ──► Model         (first-class entity; ADR-0002)
realize(Voice, Model) ──────────────────► VoiceVariant  (build if missing/deprecated — see [ADR-0008](../DECISIONS/adr-0008-voice-variant-build-lifecycle.md))
run(adapter(Model), VoiceVariant, text) ► audio
```

- **Voice** is resolved once and is engine-independent.
- **Model** is selected by the router (explicit id, or `auto` via capabilities).
- **VoiceVariant** is the `(Voice, Model)` realization; if absent the runtime invokes the
  variant build pipeline ([ADR-0008](../DECISIONS/adr-0008-voice-variant-build-lifecycle.md)) to **build** it
  (or **rebuild** if the existing variant is deprecated) — all keyed by the same
  `public_voice_id`. This is why changing the engine never changes the voice.

## 5. Runtime lifecycle

### 5.1 Model/adapter lifecycle

```
discover ─► install ─► (register adapter) ─► activate
                                              │
                                  ┌───────────┴───────────┐
                                  ▼                       ▼
                            load (on demand)         deactivate
                                  │                       │
                              generate                 deprecate
                                  │
                              unload / offload (VRAM reclaim)
```

`install`, `activate`/`deactivate`, `deprecate`, and HF-based discovery are the persisted
lifecycle from [ADR-0002](../DECISIONS/adr-0002-model-as-first-class-entity.md) (Phase 2). `load`/`unload`
are runtime-only memory operations.

### 5.2 Load / unload / GPU / VRAM

The runtime enforces a **VRAM contract**: only one (or a bounded set of) adapters hold GPU
memory at a time on a single device.

- **Load on demand:** an adapter loads weights to GPU on first use for its model.
- **Offload after use:** to free VRAM, the runtime offloads (move to CPU / empty cache) — the
  current single-GPU service already does this; the runtime generalizes the policy.
- **Eviction policy:** when a new model is requested and VRAM is insufficient, the runtime
  evicts by an LRU-of-loaded-adapters policy (configurable), respecting `models.requirements`
  (`min_vram_gb`, `gpu_required`) from [Data §3.1](data-architecture.md).
- **CPU fallback:** when no GPU is available, adapters that support CPU run there (slower);
  `gpu_required` models are rejected with a clear error rather than silently failing.

### 5.3 Voice Variant Build Lifecycle

**Introduced by [ADR-0008](../DECISIONS/adr-0008-voice-variant-build-lifecycle.md).** VoiceVariants are
first-class buildable runtime assets. A variant may require a provider-specific build process
(e.g. encoding a speaker embedding, fine-tuning a checkpoint) before it can be used for
inference. The Runtime owns variant orchestration; adapters implement provider-specific build
logic.

**Variant states (five-value lifecycle, supersedes the earlier set from ADR-0006):**

```
pending → building → ready
               ↘ failed
ready   → deprecated → building (rebuild)
failed  → building (retry)
```

See ADR-0008 for the full state machine, transition rules, and failure recovery.

**Runtime variant methods:**

- `build_variant(voice, model)` — trigger a variant build, returns job_id.
- `rebuild_variant(voice, model)` — rebuild an existing variant.
- `get_variant_status(voice, model)` — return current state + metadata.
- `ensure_variant(voice, model)` — return a ready variant or raise/take an actionable path
  (trigger build on `pending`, return 202 on `building`, return error on `failed`/`deprecated`).

**Build pipeline:**

```
Voice
  │  (identity: reference_audio, params)
  ▼
Source Asset
  ▼
Variant Builder (adapter.build_variant())
  ▼
Provider-specific Artifact
  ▼
VoiceVariant (status=ready, artifacts=storage keys)
  ▼
Runtime (adapter.generate(variant, text, params) → audio)
```

Simple realizations (`reference_sample`) build synchronously; compute-heavy realizations
(`speaker_embedding`, `checkpoint`) are async jobs. The Runtime handles both transparently.

**Build-trigger policy — Automatic Variant Provisioning ([ADR-0010](../DECISIONS/adr-0010-voice-source-assets-and-automatic-variant-provisioning.md)).**
Variants are provisioned **proactively**, not lazily at generation time: when a **Voice Source
Asset** (the canonical, model-independent source of truth) is accepted, and when a new compatible
model is installed, the Runtime detects missing variants and schedules builds for every compatible
installed model. Every variant builds from the Source Asset — never from another variant. The
Runtime owns provisioning, synchronization, missing-variant detection, and rebuild orchestration;
adapters still only `build_variant()`. **CE generation blocks on a missing variant** (explicit
"build in Voice Library" guidance — no generation-time builds, no hidden behavior); **Cloud**
provisions transparently behind "Processing Voice…". Preset-only providers (`voice_pack`, e.g.
Kokoro) are excluded from clone-based provisioning. *(Architecture accepted; implementation
deferred — current CE code still builds lazily via `ensure_variant`.)*

The provisioning *strategy* depends on the Voice's **Creation Source**
([ADR-0011](../DECISIONS/adr-0011-voice-creation-sources.md)): `SOURCE_ASSET` → auto-provision by building
from the source; `PRESET_VOICE` → **no build** (wrap the provider preset); `MARKETPLACE_VOICE` →
artifacts may already exist (import/verify); `TRAINED_VOICE` → provider-specific build. Origin
(Creation Source) and realization (VoiceVariant) stay orthogonal. The per-source policy itself is
reserved for ADR-0012 (Variant Provisioning Policies).

### 5.4 Artifact versioning (artifact-level lifecycle)

**Introduced by [ADR-0009](../DECISIONS/adr-0009-artifact-versioning-and-retention.md).** Each variant
build produces a new artifact version. The variant's active artifact is a pointer into the
`voice_variant_artifacts` table; previous versions are retained per edition policy.

**Runtime artifact methods:**

- `get_active_artifact(voice, model)` — return the currently active artifact version metadata.
- `list_artifact_versions(voice, model)` — ordered list of all versions with metadata.
- `rollback_artifact(voice, model, version)` — set the active pointer to a prior version
  (no rebuild required).
- `prune_artifacts(voice, model)` — enforce edition retention policy.

**Resolution flow (artifact-aware):**

```
ensure_variant(voice, model)
  └── variant ready → resolve active artifact version
                       └── return variant + active artifact metadata
```

The adapter interface is unchanged — versioning is a Runtime + Data concern above the adapter
line. The adapter's `build_variant()` produces an artifact; the Runtime wraps it in a versioned
row and manages the active pointer.

See ADR-0009 for retention policies (CE: keep active + N-1 previous; Cloud: marketplace-grade
indefinite retention), rollback semantics, generation reproducibility (pin-by-variant vs
pin-by-artifact-version), and model-upgrade impact.

### 5.5 Caching

- **Adapter/weight cache:** loaded adapters are kept resident until evicted (avoids reload
  cost). Weights live in the `HF_HOME` model cache on disk.
- **Variant cache:** resolved `VoiceVariant` artifacts (embeddings/reference samples) are
  cached so repeated generations for the same `(Voice, Model)` skip re-resolution.
- **Clone-prompt cache:** the existing per-profile clone-prompt cache becomes a per-variant
  cache.

## 6. The ModelAdapter standard (extensibility)

Every model integrates through **one contract**. The runtime depends only on this interface —
**PeakVox APIs never depend on a model implementation.** Adding a model = writing an adapter.

```
ModelAdapter
├── install()                 # fetch weights/manifest into the model cache (idempotent)
├── load()                    # bring weights resident (GPU/CPU); honor VRAM contract
├── unload()                  # release device memory; safe when not loaded
├── generate()                # run inference → audio (+ duration, logs)
├── clone_voice()             # build clone artifacts from reference audio
├── build_variant()           # produce this model's VoiceVariant for a Voice  [ADR-0008]
├── supported_realization_types()  # realization types this adapter can build  [ADR-0008]
├── get_capabilities()        # the ModelCapabilities contract (ADR-0003)
├── get_supported_languages() # language coverage
├── get_supported_tags()      # emotion/reaction/style tag vocabulary
└── health_check()            # readiness/liveness for the runtime + Cloud workers
```

**Contract rules:**
- The interface is **torch-free at import**; heavy runtimes are imported lazily inside methods
  (the existing provider base already follows this, so the registry imports without a GPU stack).
- Capabilities are **declared, not inferred** — `get_capabilities()` returns the frozen
  contract from [ADR-0003](../DECISIONS/adr-0003-model-capability-contract.md); the runtime/API/UI/marketplace
  read it, never guess.
- An adapter that lacks a capability **omits** it (returns `False`); the runtime rejects
  requests for unsupported capabilities up front (e.g. singing on a TTS-only model → `422`).
- **Realization types are declared** via `supported_realization_types()` ([ADR-0008](../DECISIONS/adr-0008-voice-variant-build-lifecycle.md)).
  The Runtime dispatches builds by matching the adapter's declared types against the desired
  realization — it never interprets realization types itself.

### 6.1 Adapter responsibilities (per provider)

| Adapter | Backs | Notable capabilities | Variant artifacts | Realization types [ADR-0008] |
|---|---|---|---|---|
| **OmniVoiceAdapter** | OmniVoice Base | tts, voice_cloning, emotion_tags, voice_design, multilingual, reference_audio | reference sample + transcript + voice_design params | `reference_sample` |
| **OmniVoiceSingingAdapter** | OmniVoice Singing | + singing, emotion_tags (rich) | reference sample + singing params | `reference_sample` |
| **FishAudioAdapter** | Fish Audio / S2 | tts, voice_cloning, speaker_embeddings, (speech-to-speech) | speaker embedding / checkpoint | `speaker_embedding` |
| **KokoroAdapter** | Kokoro | tts, multilingual, (preset voices) | preset/voice pack reference | `voice_pack` |
| **OpenVoiceAdapter** | OpenVoice | tts, voice_cloning, voice_conversion, reference_audio | tone-color embedding | `conversion_profile` |

These descriptions are the **integration contract**, not commitments to enablement order;
each adapter ships behind its model's `status` (e.g. `disabled` until its repo/capabilities are
verified, as the catalog already does). Future adapters (Chatterbox, Orpheus, …) implement the
same `ModelAdapter` surface.

The "Variant artifacts" column is the adapter's **realization type** — how that model stores the
voice (`reference_sample`, `embedding`, `checkpoint`, `lora`, `voice_pack`, …). Realization is an
implementation detail owned by the adapter + Runtime and **never exposed publicly**; the open
taxonomy is defined in [ADR-0006](../DECISIONS/adr-0006-voice-variant-realization-types.md)
(`backend/app/services/realization.py`). The build strategy for each type is defined by
[ADR-0008](../DECISIONS/adr-0008-voice-variant-build-lifecycle.md).

## 7. Model routing

- **Explicit:** `model="omnivoice-singing"` → that adapter (validated against capabilities +
  the request, e.g. the voice must have or be able to build that variant).
- **Default:** `model` omitted → the registry's default model.
- **Auto (future):** `model="auto"` → the router scores eligible models by capability fit
  (must support what the request needs), then by quality / cost / latency / language / user
  preference, and picks one. The application code is unchanged ([Vision §Future](../CONTEXT/VISION.md)).
  Auto-routing is **only possible** because capabilities are a stable, declared contract
  ([ADR-0003](../DECISIONS/adr-0003-model-capability-contract.md)).

## 8. Generation pipeline (end to end)

```
1. authenticate            → principal (CE: local owner)            [Auth seam]
2. resolve voice           → Voice by public_voice_id
3. route model             → Model (explicit | default | auto)
4. validate capabilities   → request vs ModelCapabilities (ADR-0003) → 422 on mismatch
5. ensure variant          → VoiceVariant(Voice, Model)              [ADR-0008]
     ├─ ready              → use
     ├─ pending            → trigger build → 202
     ├─ building           → return 202 (in progress)
     ├─ failed             → 409 + retry guidance
     └─ deprecated         → 409 + rebuild suggestion
6. acquire adapter         → load weights (VRAM contract; evict if needed)
7. generate                → adapter.generate(variant, text, params) → audio
8. deliver                 → stream | store + URL
9. emit generation.completed → metering + royalties (Cloud)         [emit only]
```

### 8.1 Async generation

Generation is already **job-based and fire-and-forget**: a request creates a `GenerationJob`
and returns a `job_id`; status is polled. The runtime owns step 5–8 of the pipeline per job.
This async shape is what makes the distributed future (below) a deployment change, not a
redesign.

## 9. Execution models

### 9.1 Local execution (Community Edition) — "Ollama for Voice"

CE runs the **entire runtime in-process** on the user's hardware: install models (incl. from
Hugging Face), load on demand, generate locally, offload to reclaim VRAM. No accounts, no
network dependency for inference. This is the self-hosted infrastructure layer — a complete,
local universal voice runtime.

### 9.2 Distributed execution (Cloud, future) — "OpenRouter for Voice"

The same runtime + adapters run inside a **horizontally scaled GPU worker pool behind a
queue** ([Cloud §4](cloud-architecture.md)):

```
API ──enqueue──► queue ──► [ runtime worker ]  (GPU)   ← model registry + adapters
                           [ runtime worker ]  (GPU)
                           [ runtime worker ]  (GPU)
```

- **Scheduling:** jobs route to workers by `model` + `requirements` (VRAM-aware placement);
  per-model GPU pools; variant-build jobs share the pool.
- **Worker = runtime:** a worker is the very same runtime core + adapters used locally, so
  there is **no separate Cloud inference codebase** — only a different execution substrate.
- **Cloud worker integration:** workers expose `health_check()` for pool management; the
  router/scheduler treats unhealthy or VRAM-saturated workers accordingly.
- **Scaling:** workers autoscale on queue depth (Phase 10).

The boundary that makes this clean: the runtime depends only on the `ModelAdapter` contract
and a queue abstraction — neither of which knows whether it is running on a laptop or a fleet.

## 10. Where the runtime is built (roadmap mapping)

| Runtime concern | Phase |
|---|---|
| Adapter contract hardening; capability contract; lifecycle; HF install | [Phase 2](../ROADMAP/ROADMAP.md) |
| Voice/Variant resolution in the pipeline | [Phase 3](../ROADMAP/ROADMAP.md) |
| Distributed runtime: queue + GPU worker pool; VRAM-aware scheduling | [Phase 8](../ROADMAP/ROADMAP.md) |
| `auto` routing | post-foundation (capability contract enables it) |
| Autoscaling, caching, multi-region | [Phase 10](../ROADMAP/ROADMAP.md) |

## 11. Invariants (the runtime must always uphold)

1. **Model-agnostic core.** Nothing above the adapter line imports a model implementation.
2. **Stable surface.** Adding/removing/updating a model never changes public APIs, Voice IDs,
   Voice Library, marketplace, or integrations.
3. **One voice, many engines.** The same `public_voice_id` renders through any adapter via its
   VoiceVariant.
4. **Declared capabilities.** The runtime acts only on `get_capabilities()` truth; it never
   infers a model's features.
5. **VRAM safety.** Generate only while loaded; reclaim memory deterministically.
6. **Same runtime, local and distributed.** CE in-process and Cloud worker run identical
   runtime + adapter code.

## 12. Model classification

PeakVox is not limited to traditional TTS. The runtime is designed so **multiple model
categories** coexist behind the same `ModelAdapter` contract and the same
`Voice + Model → VoiceVariant` resolution — the category a model belongs to is expressed
through its [declared capabilities](../DECISIONS/adr-0003-model-capability-contract.md), not through a
separate code path.

| Category | What it does | Key capabilities | Notes |
|---|---|---|---|
| **Text-to-Speech** | text → speech | `supports_tts`, `supports_multilingual` | the baseline category |
| **Voice Cloning** | reference audio → a voice's variant | `supports_voice_cloning`, `supports_reference_audio`, `supports_speaker_embeddings` | feeds the onboarding pipeline / `build_variant()` |
| **Voice Conversion** | source speech → target voice | `supports_voice_conversion` | input is audio, not text |
| **Singing** | sung delivery | `supports_singing`, `supports_emotion_tags` | e.g. OmniVoice Singing |
| **Emotion Generation** | expressive/emotive delivery | `supports_emotion_tags`, `supports_voice_design` | tag-driven |
| **Realtime Voice** | low-latency / streaming | `supports_streaming` | latency-sensitive routing |
| **Speech-to-Speech** | speech → speech (style/voice transfer) | `supports_voice_conversion` (+ streaming) | audio-in / audio-out |

**How the runtime supports multiple categories simultaneously:**

- The **request shape** declares its inputs (text and/or reference/source audio); the runtime
  validates them against the model's declared capabilities before routing
  ([§7](#7-model-routing), [ADR-0003](../DECISIONS/adr-0003-model-capability-contract.md)).
- A single **Voice** can have variants across categories (a TTS variant, a singing variant, a
  conversion variant) — all under one `public_voice_id`. The category is a property of the
  **Model**, never of the **Voice** ([ADR-0004](../DECISIONS/adr-0004-voice-variant-model-separation.md)).
- New categories arrive as **new capabilities + adapters**, not new public APIs. The platform
  evolving "beyond traditional TTS" (e.g. realtime, speech-to-speech) is an additive,
  capability-driven change — the developer contract (`voice_id + model + …`) is unchanged.

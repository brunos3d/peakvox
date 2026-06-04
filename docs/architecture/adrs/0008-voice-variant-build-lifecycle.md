# ADR-0008: Voice Variant Build Lifecycle

- **Status:** Accepted
- **Date:** 2026-06-04
- **Deciders:** Bruno Silva (product owner), architecture planning
- **Supersedes:** ADR-0006 §VoiceVariant lifecycle status values

## Context

The Runtime Architecture has been validated across three providers (OmniVoice Base, OmniVoice
Singing, Fish Audio S2 Pro) and proves the resolution chain:

```
Voice ID → Model → VoiceVariant → Adapter → Runtime → inference
```

However, Fish Audio exposed an architectural gap. Current VoiceVariants assume a
`realization_type = reference_sample` because OmniVoice and OmniVoice Singing both operate
directly from a WAV reference. Fish Audio does not — it requires a provider-specific speaker
embedding. Future models will require fine-tuned checkpoints, LoRAs, latent representations,
conversion profiles, and proprietary runtime assets.

Today a VoiceVariant is treated largely as metadata — a row that records which reference audio
to use for which model. This is insufficient when the variant requires **a build process**:
computation, state tracking, and an artifact that must exist before inference can proceed.

Three binding architectural principles must be preserved ([ADR-0004](0004-voice-variant-model-separation.md)):

1. **Voice = identity**, stable and model-independent.
2. **VoiceVariant = provider-specific realization**, encapsulated behind the Runtime.
3. **Model = engine**, interchangeable without changing the Voice.

The gap is that principle 2 currently lacks a formal lifecycle. A variant cannot simply be "a
row with some fields" — it must be a **first-class buildable runtime asset**.

## Options considered

1. **Keep variants as metadata; embed build logic inside each adapter ad-hoc.**
   Lowest upfront cost. Each adapter invents its own build path, status tracking, and error
   handling. The Runtime cannot reason about variant availability. Adding a new provider means
   reinventing build orchestration. Variant status is inconsistent across providers. Rejected.

2. **A formal Voice Variant Build Lifecycle, governed by the Runtime, executed by adapters.**
   The Runtime owns variant orchestration (check, build, rebuild, track, fail). Adapters
   implement `build_variant()`. The lifecycle is a first-class concept with defined states,
   transitions, and recovery. Higher upfront design; permanent structural guarantee. **Chosen.**

3. **Separate variant-build into an independent microservice/queue.**
   Maximum isolation — build jobs are async, queued, parallelizable. But adds a service
   boundary, deployment complexity, and serialization overhead before it is justified by scale.
   Premature for the current CE-focused phase. The Runtime already owns job-based async
   generation (§8); variant builds are a natural extension of the same in-process async pattern.
   Deferred until platform scale demands it (Phase 10+).

## Decision

Adopt **Option 2**. A Voice Variant is a **first-class buildable runtime asset** with a formal
lifecycle. The Runtime orchestrates variant existence; adapters implement provider-specific
build logic. Variant builds are async, job-based, and owned by the same Runtime that owns
generation.

### Voice Variant States (supersedes ADR-0006 status values)

This ADR **supersedes** the VoiceVariant lifecycle terminology introduced by ADR-0006.
ADR-0006's earlier set of status values (`processing`, `stale`, `ready`, `failed`) is replaced
by the five-value lifecycle defined here. ADR-0006 remains authoritative for realization types,
artifact encapsulation, and the open-taxonomy rules — only the lifecycle status vocabulary is
superseded.

The `voice_variants.status` column uses these values:

| State | Meaning | Can generate? |
|---|---|---|
| `pending` | Variant record exists; no artifact has been built. | No |
| `building` | Build is in progress (async job). | No (poll for completion) |
| `ready` | Artifact exists and is usable for inference. | Yes |
| `failed` | Build failed. Artifact may be partial or absent. | No |
| `deprecated` | Artifact exists but should no longer be used. Manual rebuild or removal required. | No |

**Mapping from ADR-0006 values:**
- `processing` → `building`
- `stale` → `deprecated`
- `ready` and `failed` unchanged
- `pending` is new

**State transition diagram:**

```
              ┌──────────────────────────────────────┐
              │                                      │
              ▼                                      │
         ┌─────────┐    build()    ┌──────────┐      │
         │ pending │ ────────────► │ building │      │
         └─────────┘              └──────────┘      │
              ▲                       │    │        │
              │              success  │    │ fail   │
              │                       ▼    ▼        │
              │                 ┌──────────┐        │
              │          ┌─────│  ready   │◄───────┘
              │          │     └──────────┘   (rebuild)
              │          │           │
              │          │  deprecate│
              │          │           ▼
              │          │    ┌──────────────┐
              │          └──► │  deprecated  │
              │               └──────────────┘
              │                     │
              └─────────────────────┘
                  (build after fix / rebuild)
```

**Transition rules:**

- `pending → building`: triggered by `build_variant()`. The variant record exists but has never
  been built.
- `building → ready`: build completed successfully. Artifact is stored; the variant is usable.
- `building → failed`: build errored. Error details recorded on the variant record (or
  associated job). Retry resets to `building`.
- `ready → building`: triggered by `rebuild_variant()`. Existing artifact is preserved until
  the new build succeeds; on success it replaces the old artifact.
- `ready → deprecated`: variant is superseded (e.g. source model changed, migration). Not
  automatic — set by a lifecycle event or manual intervention.
- `deprecated → building`: triggered by `rebuild_variant()` or a rebuild-after-fix flow.
- `failed → building`: retry. The same as a fresh build; no artifact expected.

**Failure recovery:**

- A failed build leaves the variant in `failed`. The error message and job id are accessible via
  `GET /voices/{id}/variants/{variant_id}`.
- Retrying (POST `/voices/{id}/variants/build`) transitions `failed → building`.
- A variant in `failed` does not block builds for other models.
- Repeated failures after N retries should flag the variant for manual inspection (no automatic
  circuit-breaker in the initial design — N is configurable later).

### Realization types determine build strategy

Expanding ADR-0006: a realization type is not merely a format label — it determines **how a
variant is built**:

| Realization | Build strategy | Example provider |
|---|---|---|
| `reference_sample` | Copy/validate reference audio. No compute. | OmniVoice, OmniVoice Singing |
| `speaker_embedding` | Run reference audio through an embedding encoder. | Fish Audio |
| `fine_tuned_checkpoint` | Fine-tune on reference audio. Long-running; GPU required. | Future Kokoro |
| `lora` | Train a LoRA adapter on reference audio. | Future lightweight adapters |
| `conversion_profile` | Extract voice conversion profile from reference audio. | Future OpenVoice |
| `latent_representation` | Encode reference audio into a latent space. | Future providers |
| `voice_pack` | Select/download a preset pack. No build (metadata-only). | Kokoro-style presets |
| `metadata` | No artifact; variant carries params only. Build = validate. | Lightweight cases |
| `future_provider_asset` | Arbitrary provider-specific format. Adapter defines build. | Future |

The set remains open (ADR-0006 rule 3). The strategy is declared by the adapter via
`supported_realization_types`. The Runtime does not interpret build strategy — it delegates to
the adapter's `build_variant()`.

### Voice, VoiceVariant, and Artifact — clarified

The three-layer model is now fully explicit:

```
Voice           = identity, portable asset.
VoiceVariant    = provider-specific realization row (voice_id × model_id).
Artifact        = generated asset used by inference (the output of a build).
```

A VoiceVariant may exist without an artifact (`pending`, `failed`). An artifact is the
operational output of a successful build. The VoiceVariant row links them: it records the
`realization_type`, and the artifact's storage keys live in `voice_variants.artifacts` (JSON).

### Variant Builder Pipeline

```
Voice
  │  (identity: name, reference_audio, language, characteristics)
  ▼
Source Asset
  │  (the raw input: reference_sample.wav, transcript, design params)
  ▼
Variant Builder  (adapter.build_variant())
  │  - OmniVoice:     validate + copy reference sample
  │  - OmniVoice Singing: validate + copy reference sample + singing params
  │  - Fish Audio:    encode reference → speaker embedding
  │  - Future Kokoro: fine-tune checkpoint on reference
  │  - Future OpenVoice: extract conversion profile
  ▼
Provider-specific Artifact
  │  (stored in /data/voices/{voice_id}/variants/{model_id}/)
  ▼
VoiceVariant  (row: voice_id × model_id, status=ready, artifacts=keys)
  │
  ▼
Runtime  (adapter.generate(variant, text, params) → audio)
```

The pipeline is **asymmetric**: simple realizations (`reference_sample`) are instant;
compute-heavy realizations (`speaker_embedding`, `checkpoint`) are async jobs. The Runtime
handles both transparently — the caller sees only `ready` or a `202` job.

### Runtime responsibilities (extended)

The Runtime gains explicit variant lifecycle ownership:

```
runtime.build_variant(voice, model)                trigger build → returns job_id
runtime.rebuild_variant(voice, model)              rebuild existing variant
runtime.get_variant_status(voice, model)           returns current state + metadata
runtime.ensure_variant(voice, model)               returns ready variant or raises actionable error
```

**Runtime resolution flow (extended from ADR-0004 §4):**

```
resolve(voice_id)          → Voice
route(model, request)      → Model
ensure_variant(voice, model)
  ├── variant exists + ready       → return variant
  ├── variant exists + building    → return 202 + job_id (in progress)
  ├── variant exists + failed      → return actionable error with retry guidance
  ├── variant exists + deprecated  → return warning + deprecated artifact (opt-in) or error
  └── variant exists + pending     → trigger build → return 202 + job_id
run(adapter, variant, text, params) → audio
```

The Runtime **never** directly mutates Voice entities. It calls `adapter.build_variant()` and
writes the result to the variant repository. The adapter is the only entity that produces
provider-specific artifacts.

### ModelAdapter contract extension

The `ModelAdapter` contract (Runtime §6) gains:

```python
class ModelAdapter:
    # Existing methods (install, load, unload, generate, ...)

    def build_variant(self, voice: Voice, params: dict | None = None) -> VariantBuildResult:
        """Produce this model's VoiceVariant artifact for a Voice.

        Returns a VariantBuildResult with:
        - status: "success" | "failure"
        - artifacts: dict of storage keys (or None on failure)
        - error_message: str | None
        - job_type: "sync" | "async"

        For sync builds (reference_sample), the artifact is produced inline.
        For async builds (speaker_embedding, checkpoint), the adapter may
        enqueue work and return job_type="async" with a reference.
        """
```

The adapter also declares which realization types it supports via a new surface property,
enabling the Runtime to preflight-check before dispatching a build:

```python
@property
def supported_realization_types(self) -> list[str]:
    """Realization types this adapter can build. E.g. ["reference_sample"]"""
```

**Provider examples:**

| Adapter | `supported_realization_types` | Build behavior |
|---|---|---|
| OmniVoiceAdapter | `["reference_sample"]` | Sync — validate + copy reference WAV |
| OmniVoiceSingingAdapter | `["reference_sample"]` | Sync — validate + copy reference WAV + singing params |
| FishAudioAdapter | `["speaker_embedding"]` | Async — encode reference through embedding model |
| KokoroAdapter (future) | `["fine_tuned_checkpoint"]` | Async — fine-tune checkpoint |
| OpenVoiceAdapter (future) | `["conversion_profile"]` | Async — extract voice conversion profile |

The Runtime dispatches builds by matching the adapter's `supported_realization_types` against
the desired realization for the variant. It never interprets realization types itself.

### API implications (future endpoints, documented now)

New endpoints — **not implemented**, reserved for Phase 4+:

```
GET    /voices/{id}/variants               list variants for a voice
POST   /voices/{id}/variants/build         build variant for specified model
POST   /voices/{id}/variants/rebuild       rebuild existing variant
GET    /voices/{id}/variants/{variant_id}  variant detail + status + artifact info
```

**Expected shapes (conceptual, not wire-contract):**

```json
POST /voices/{id}/variants/build
{ "model": "fish-audio-s2" }

→ 202
{ "job_id": "variant_build_job_abc123",
  "variant_id": "vvar_xyz",
  "status": "building" }

GET /voices/{id}/variants/{variant_id}
→ 200
{ "voice_id": "voice_8JXQ29K4L3",
  "model_id": "fish-audio-s2",
  "status": "ready",
  "realization_type": "speaker_embedding",
  "created_at": "...",
  "updated_at": "...",
  "last_build_job_id": "variant_build_job_abc123" }
```

The core generation endpoint's `VoiceVariant` resolution (API §3) is updated to reflect the
ensure-or-build flow:

```
resolve VoiceVariant(voice, model)
  ├─ ready     → generate
  ├─ pending   → trigger build → 202 + job_id (generation job that includes build)
  ├─ building  → 202 + job_id (build already in progress)
  ├─ failed    → 409 with retry guidance
  └─ deprecated → 409 with rebuild suggestion
```

### Voice Library and onboarding UX implications (documented only, not implemented)

**Voice Library** — variants per voice are displayed with status indicators:

```
Larissa
  Variants
  ✓ OmniVoice         (ready)
  ✓ OmniVoice Singing (ready)
  ⚠ Fish Audio        (pending — build required)
  ✗ Kokoro            (not available in CE)
```

Each variant row offers contextual actions: Build (pending/failed), Rebuild (ready/deprecated),
Retry (failed), Inspect (any).

**Voice onboarding** — after creating a voice, the user is offered a variant build step:

```
Voice created successfully.

Build variants for your new voice:
  ☑ OmniVoice          (builds automatically — reference_sample)
  ☑ OmniVoice Singing  (builds automatically — reference_sample)
  ☐ Fish Audio         (requires build — speaker_embedding)
  [Build Selected]  [Build Later]
```

Voice creation and variant creation are separate concerns. The user may leave variants
`pending` and build on demand at generation time (the Runtime's `ensure_variant` handles this).

## Consequences

- **Positive:**
  - Variants are first-class buildable assets, not passive metadata rows.
  - The Runtime can reason about variant availability before dispatching generation.
  - New providers with compute-heavy realization types (embeddings, checkpoints, LoRAs) fit
    naturally — the Runtime already handles variant orchestration.
  - Build failure is a tracked, recoverable state rather than a silent gap.
  - The ModelAdapter extension is minimal and backward-compatible.
  - The status enum is now expressive enough for all lifecycle phases.
  - Voice creation and variant building are separated into distinct concerns, enabling
    build-later and build-on-demand workflows.
  - The future Voice Library UI can display variant health per provider.

- **Negative / costs:**
  - Variant build adds an orchestration path to the Runtime (check → build → track → handle
    failure) that is not yet implemented.
  - `build_variant()` adds one method to every adapter; for simple providers (OmniVoice) this
    is trivial, but the contract must be implemented.
  - The async build + job pattern adds complexity compared to the current assumption that a
    variant exists at generation time.
  - Requires a `variant_build_jobs` tracking mechanism (reuses the existing `generation_jobs`
    pattern or adds a lightweight parallel table — deferred to implementation).

- **Follow-ups:**
  - ADR-0008 builds directly on ADR-0001 (variant split), ADR-0004 (three-way separation),
    and ADR-0006 (realization types whose build strategies are now formalized).
  - The status enum in ADR-0006 is superseded by this ADR's values — any implementation of
    `voice_variants.status` should use the five-value set.
  - Implementation should reuse the existing async job infrastructure (`GenerationJob`, job
    polling) for variant builds rather than duplicating it.
  - Future: auto-routing may need variant availability as a routing signal ("model X supports
    this request but has no variant for this voice — skip or build").

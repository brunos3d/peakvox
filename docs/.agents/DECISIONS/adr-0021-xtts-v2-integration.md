# ADR-0021: XTTS v2 First-Class Runtime Integration

- **Status:** Accepted (implemented)
- **Date:** 2026-06-12
- **Deciders:** PeakVox architecture (Task 30).
- **Supersedes:** none.
- **Amends:** none. XTTS integrates through the existing contracts unchanged
  ([ADR-0003](adr-0003-model-capability-contract.md) capabilities,
  [ADR-0004](adr-0004-voice-variant-model-separation.md) adapter seam,
  [ADR-0016](adr-0016-models-as-runtime-services.md)/[ADR-0017](adr-0017-runtime-services-implementation.md)
  runtime services, [ADR-0018](adr-0018-runtime-variants-architecture.md)/[ADR-0019](adr-0019-variant-trust-and-community-imports.md)
  runtime variants).
- **Superseded by:** none.
- **Discovery:** [`../VALIDATION/RESEARCH/task-30-xtts-discovery.md`](../VALIDATION/RESEARCH/task-30-xtts-discovery.md)
- **Validation:** [`../VALIDATION/PROVIDER_VALIDATIONS/task-30-xtts-validation.md`](../VALIDATION/PROVIDER_VALIDATIONS/task-30-xtts-validation.md)

---

## Context

After OmniVoice, Kokoro, and F5-TTS, **Coqui XTTS v2** (`coqui/XTTS-v2`) is the
next model PeakVox integrates. XTTS v2 is a multilingual (17 languages),
zero-shot voice-cloning TTS that clones a voice from ~6 seconds of reference
audio. It is a strong fit for the PeakVox thesis: it is voice-first
(reference-audio cloning), has an active fine-tuned/community **checkpoint
ecosystem** (the best validation target yet for Runtime Variants), and — unlike
F5-TTS — is **CPU-capable**, which exercises the platform's GPU/CPU contract
end-to-end.

The goal is **first-class parity**, not "make XTTS work": XTTS must feel
identical to the other native runtimes (registry, lifecycle, Voice
compatibility, variants, Models page, Public API) and introduce **no
model-specific architectural exception** (Constitution Art. I §2–3, Art. III).

## Decision

Integrate XTTS v2 as a first-class runtime **through the existing contracts,
inventing nothing new**:

1. **Runtime Registry entry** — `runtime-registry/xtts-v2/` (descriptor,
   Dockerfile, `server.py`, requirements, `variants/base.json`, README, tests).
   File-based discovery (ADR-0017 §2) picks it up with no central registration.
2. **Runtime Service** — `peakvox/xtts-runtime`, the 5-endpoint Runtime Service
   Contract (ADR-0017 §6) over HTTP/JSON, engine `coqui-tts`
   (`tts_models/multilingual/multi-dataset/xtts_v2`).
3. **Adapter** — `XTTSAdapter` (`backend/app/services/model_adapters/xtts_adapter.py`),
   a sibling of `F5TTSAdapter`: `reference_sample` realization, runtime-routed
   generation via `HTTPTransport` (**no in-process inference** — Constitution
   Art. III §9), `SOURCE_ASSET` build strategy.
4. **Model registration** — `xtts-v2` `ModelDescriptor` in `BUILTIN_MODELS`,
   `provider="xtts"`, wired in `_ADAPTER_BY_PROVIDER`. Seeded idempotently into
   the `models` table by the existing migration. Capabilities **declared**
   (ADR-0003), never inferred.
5. **Runtime Variant** — `variants/base.json` formalizes the bundled
   `coqui/XTTS-v2` checkpoint as the explicit, default, `verified` base; future
   fine-tuned/community/HF checkpoints attach as siblings (ADR-0018/0019).

### Declared capabilities (ADR-0003 — declared, never inferred)

`tts`, `voice_cloning`, `multilingual`, `reference_audio`, and the
`supports_voice_optional` flag. **Deliberately NOT declared** (no over-claim):
`streaming` (upstream `inference_stream` exists but the contract returns a full
WAV — documented future), `emotion_tags`/`emotions` (v2 dropped explicit emotion
tokens), `voice_conversion`, `voice_design`, `singing`, `custom_training`,
`speaker_embeddings`. This is identical to F5-TTS's surface; the capability-driven
UI therefore renders XTTS controls with zero special-casing.

### GPU/CPU contract — the one deliberate divergence from F5-TTS

F5-TTS is CUDA-only and **raises** `cuda_unavailable` with no GPU. XTTS is
**CPU-capable**, so:

- The descriptor declares `requirements.gpu: "optional"`, `min_vram_gb: 4`; the
  catalog declares `gpu_required=False`.
- `server.py` selects the device at load (`torch.cuda.is_available()`) and
  **never raises** for a missing GPU — it falls back to CPU.
- The existing `DockerRuntimeDriver` plumbing makes **Settings → Use GPU (CUDA)**
  authoritative: with it OFF the driver hides the device
  (`NVIDIA_VISIBLE_DEVICES=void`, `CUDA_VISIBLE_DEVICES=""`), so the server
  transparently runs on CPU. `/v1/metadata` reports the live `substrate`.

| Use GPU (CUDA) | Host CUDA | XTTS device |
|---|---|---|
| ON | yes | CUDA |
| ON | no | CPU |
| OFF | yes | CPU (setting is authoritative) |
| OFF | no | CPU |

No setting is silently ignored; behavior is explicit and tested.

### Concurrency

The XTTS GPT backbone is not concurrency-safe; the server serializes inference
behind a module-level lock and declares `max_concurrent_requests: 1` (same
posture as F5-TTS). The adapter uses a 600 s transport timeout so a slow CPU run
is not killed mid-inference.

### Licensing & edition scope

XTTS weights are under the **Coqui Public Model License (CPML)** — **non-commercial**.
Per ADR-0005/0017, the model is CE-disabled by default (`status="disabled"`),
`editions=["community","cloud"]`, `commercial_use=False`, enabled per deployment
after license review (same posture as F5-TTS). The Dockerfile/server set
`COQUI_TOS_AGREED=1` so the container starts non-interactively; the operator
accepts CPML by enabling the model.

## Voice domain compatibility (Constitution Art. II)

XTTS uses the **canonical Voice entity** — no separate voice system.
Realization is `reference_sample` (clone at inference from the voice's Source
Asset reference audio); the build strategy `SOURCE_ASSET → can_build=True` makes
**every existing `SOURCE_ASSET` voice immediately compatible** with XTTS via the
`CompatibilityResolver` — no backfill, no new asset type. `public_voice_id` is
untouched; selecting XTTS changes nothing about a voice's identity.

## Runtime Variants implications (ADR-0018/0019)

XTTS is the strongest validation target for the checkpoint ecosystem: a new
checkpoint (fine-tuned, community, imported HF) attaches as an **additional
RuntimeVariant of the same `xtts-v2` runtime — no new Docker image, no new model
id**. `variants/base.json` makes the bundled checkpoint the explicit default so
future imports are siblings, not special cases. Precomputing XTTS speaker
latents (`gpt_cond_latent` + `speaker_embedding`) as a variant artifact is a
documented **future** optimization; the first integration uses the simpler
`reference_sample`-at-inference path for parity with F5-TTS.

## Community Edition implications

XTTS ships in CE as a **CPU-capable, locally-runnable** voice-cloning runtime —
genuinely useful self-hosted infrastructure (CE thesis). Lifecycle (install,
start, stop, restart, update, remove, reinstall) is managed from the Models page
via RuntimeManager → DockerRuntimeDriver, identical to the other runtimes. The
CPML non-commercial gate keeps it disabled by default; a CE operator enables it
explicitly.

## Future checkpoint ecosystem

XTTS's active fine-tuning ecosystem is the first real test of ADR-0019 community
imports for a checkpoint-based model: language/style fine-tunes can be imported
(validate-only today) as `community`/`private` RuntimeVariants of `xtts-v2`,
each a sibling of `base`, governed by the trust tiers — with no new image and the
same `public_voice_id` contract for any voice used with them.

## Consequences

**Positive:** fourth native runtime with full parity; first CPU-capable
voice-cloning runtime (clean GPU/CPU validation); validates the variant
checkpoint ecosystem; zero frontend changes (capability-driven UI); no new
contract.

**Negative / trade-offs:** CPU inference is slow (documented, not hidden); CPML
non-commercial blocks default-on and Cloud commercial use until license review;
streaming/emotion/training are not exposed (honest under-claim); the bundled
checkpoint download (~1.8 GB) happens on first inference (cached on `/data`).

**Neutral:** XTTS joins F5-TTS as a CE-disabled, license-gated provider — the
edition-scoping machinery (ADR-0005) already handles it.

## Validation status

**Architecture-validated** by Task 30: XTTS integrates through the same Runtime
Service Contract, adapter seam, capability contract, variant architecture, and
Public API as the existing runtimes, proven by the unit/contract test suites
(runtime server, descriptor, adapter, registry discovery, catalog/wiring).
**Provider-validation** (a real XTTS container generating audio on GPU and CPU)
is recorded separately in
[`../VALIDATION/PROVIDER_VALIDATIONS/task-30-xtts-validation.md`](../VALIDATION/PROVIDER_VALIDATIONS/task-30-xtts-validation.md)
(Constitution Art. VII §23 — the two are never conflated).

---

**Related:** [ADR-0003](adr-0003-model-capability-contract.md) ·
[ADR-0004](adr-0004-voice-variant-model-separation.md) ·
[ADR-0005](adr-0005-edition-scoped-model-availability.md) ·
[ADR-0016](adr-0016-models-as-runtime-services.md) ·
[ADR-0017](adr-0017-runtime-services-implementation.md) ·
[ADR-0018](adr-0018-runtime-variants-architecture.md) ·
[ADR-0019](adr-0019-variant-trust-and-community-imports.md) ·
[Discovery](../VALIDATION/RESEARCH/task-30-xtts-discovery.md)

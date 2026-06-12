# Task 30 — XTTS v2 First-Class Integration: Discovery & Capability Analysis

> Phase A (Repository Discovery) + Phase B (Capability Analysis) deliverable.
> Status: **research complete**, drives the implementation in
> `runtime-registry/xtts-v2/`, `backend/app/services/model_adapters/xtts_adapter.py`,
> the catalog entry, and ADR-0021.
>
> Authority note (CONSTITUTION Art. VII): this is **intent/research**, not proof.
> Code references in `IMPLEMENTATION_STATUS.md` are the proof. XTTS is
> **architecture-validated** by this task (it integrates through the same Runtime
> Service Contract, adapter seam, and capability contract as Kokoro/F5/OmniVoice);
> a real end-to-end audio generation on GPU/CPU is the **provider-validation** step,
> recorded separately under `VALIDATION/PROVIDER_VALIDATIONS/`.

---

## 1. How the existing runtimes work (the pattern XTTS must follow)

Established by reading the live code, not docs:

| Layer | File | Role |
|---|---|---|
| Runtime Registry | `backend/app/services/runtime_registry.py` | **File-based auto-discovery.** `RuntimeRegistryLoader.load_from_directory` walks `runtime-registry/<id>/descriptor.json` and `variants/*.json`. **No central registration list** — dropping a new directory is the registration. |
| Runtime descriptor schema | `backend/app/services/runtime_types.py` | `RuntimeDescriptor` (pydantic). Capabilities are validated against `RUNTIME_CAPABILITY_VOCABULARY` and must be a subset of the bound model's `ModelCapabilities` (`validate_capabilities_subset_of`, ADR-0017 §1.5 — "the runtime cannot exceed the model"). |
| Runtime Service Contract | `runtime-registry/*/server.py` | 5 HTTP endpoints: `GET /health`, `GET /ready`, `POST /v1/generate`, `POST /v1/variants/build`, `GET /v1/metadata` (ADR-0017 §6). FastAPI + uvicorn on `0.0.0.0:8000`. |
| Runtime Driver | `backend/app/services/drivers/docker_runtime_driver.py` | Builds/pulls the image, runs the container, plumbs **GPU** via `spec.requirements.gpu` + the global `use_gpu` setting (see §5). |
| Adapter seam | `backend/app/services/model_adapter.py` | `ModelAdapter` ABC — the single model-agnostic seam. Concrete adapters route generation via `HTTPTransport` to the runtime container; **no in-process inference** (Constitution Art. III §9). |
| Adapter wiring | `backend/app/services/model_wiring.py` | `_ADAPTER_BY_PROVIDER` maps `descriptor.provider` → adapter class. One line per provider. |
| Model catalog | `backend/app/services/model_catalog.py` | `BUILTIN_MODELS` list of `ModelDescriptor`. Seeded idempotently into the `models` table by `_seed_builtin_models` (`backend/app/core/migrations.py`); built-in fields refresh on every boot, lifecycle status is preserved. |
| Runtime Variants | `runtime-registry/*/variants/base.json` | ADR-0018: `RuntimeVariantDescriptor`. `RuntimeRegistry.select_variant` resolves a checkpoint per (runtime, model). Absent `variants/` ⇒ implicit base; behavior unchanged. |

**The reference shape (R8):** Kokoro is the canonical template (CPU-capable). F5-TTS is the
GPU voice-cloning template. **XTTS sits between them** — it is a voice-cloning, multilingual
model like F5, but it is CPU-capable like Kokoro. The integration therefore copies the F5
adapter/server almost verbatim and adopts Kokoro's `gpu: "optional"` substrate posture.

### Generation flow (unchanged for XTTS)
```
POST /api/.../generate
  → PeakVoxRuntime.generate (resolves Voice + Model → VoiceVariant)
  → RuntimeManager: is there an ACTIVE instance for model_id? inject runtime_endpoint
  → XTTSAdapter.generate(runtime_endpoint=...) → HTTPTransport POST /v1/generate
  → xtts-v2 container: TTS.tts_to_file(speaker_wav=ref, language=...) → audio/wav
```

---

## 2. XTTS v2 capability analysis (declared, never inferred — ADR-0003)

Source: `coqui/XTTS-v2` (Hugging Face), the Coqui TTS engine, maintained PyPI fork
`coqui-tts` (the original `TTS` package is unmaintained; the Idiap fork is canonical).

| Question (Phase B) | Answer | Declared as |
|---|---|---|
| TTS? | **Yes** | `supports_tts=True` / descriptor `tts` |
| Voice cloning? | **Yes** — zero-shot from ~6 s of reference audio (`speaker_wav`) | `supports_voice_cloning=True` / `voice_cloning` |
| Multilingual? | **Yes** — 17 languages | `supports_multilingual=True` / `multilingual` |
| Reference audio? | **Yes** — conditioning latents computed from the clip at inference | `supports_reference_audio=True` / `reference_audio` |
| Voice conversion? | Partial (speaker-cond resynthesis), **not exposed as a distinct VC API in our contract** | **not declared** (no over-claim) |
| Streaming? | Upstream `inference_stream` exists, **but the PeakVox Runtime Service Contract returns a full WAV** — not wired | **not declared** (documented future) |
| Emotion control? | v2 **dropped** v1's explicit emotion/style tokens; emotion is implicit via the reference | **not declared** |
| Style transfer? | Only implicit prosody transfer from `speaker_wav` | **not declared** |
| Custom checkpoints? | **Yes** — fine-tuning is officially supported; community checkpoints exist on HF | surfaced via **Runtime Variants** (ADR-0018/0019), not a capability flag |
| Voice-optional (generate with no user voice)? | **Yes** — XTTS ships built-in studio speakers; server falls back to one when no ref is supplied | `supports_voice_optional=True` |
| Runtime Variants? | **Yes — XTTS is the strongest validation target so far** (see §6) | `variants/base.json` + future imports |

**Net declared surface (mirrors F5 exactly):** descriptor capabilities
`["tts", "voice_cloning", "multilingual", "reference_audio"]`; model capability flags add
`supports_voice_optional=True`. Nothing else is claimed. `custom_training`,
`speaker_embeddings`, `streaming`, `emotion_tags`, `voice_design`, `singing`,
`voice_conversion` are **deliberately False** — the platform does not wire them, so the UI
must not render controls for them.

---

## 3. Runtime implications

- **Engine package:** `coqui-tts` (maintained fork). Model id
  `tts_models/multilingual/multi-dataset/xtts_v2`. Weights (~1.8 GB) download on first
  inference into `HF_HOME=/data/hf-cache` (already plumbed by the driver, survives
  GPU↔CPU restarts and remove/reinstall).
- **License gate:** XTTS weights are under the **Coqui Public Model License (CPML)**,
  non-commercial. The engine requires interactive ToS acceptance unless
  `COQUI_TOS_AGREED=1` is set — the Dockerfile and server set it so the container can
  start non-interactively. `commercial_use=False`; CE-disabled by default (`status="disabled"`),
  enabled per-deployment after license review (same posture as F5).
- **Concurrency:** the XTTS GPT backbone is **not safe for concurrent inference** in one
  process (shares conditioning state). The server serializes inference behind a module-level
  lock and declares `max_concurrent_requests: 1`, exactly like F5.
- **Sample rate:** 24 kHz mono, 16-bit PCM WAV (same encoder as F5/Kokoro servers).

---

## 4. Compatibility implications (Voice domain — Phase G)

XTTS uses **the canonical Voice entity** — no separate voice system (Constitution Art. II).
- Realization type: **`reference_sample`** (clone at inference time from the voice's Source
  Asset reference audio). Same as F5 and OmniVoice — the `VoiceVariant` stores the reference
  audio storage key + transcript; no pre-computation.
- Build strategy: `SOURCE_ASSET → can_build=True, requires=["source_asset"]`. This makes every
  existing `SOURCE_ASSET` PeakVox voice **immediately compatible** with XTTS via the
  `CompatibilityResolver` — no backfill, no new asset type.
- `public_voice_id` is untouched; selecting XTTS for an existing voice changes nothing about
  the voice's identity (Constitution Art. II §5).

---

## 5. GPU requirements & behavior (Phase K) — the key divergence from F5

XTTS is **CPU-capable** (slow but functional), unlike F5 (CUDA-only). This is declared
honestly and exploits the existing driver plumbing:

- Descriptor `spec.requirements.gpu = "optional"`, `min_vram_gb = 4`.
- `docker_runtime_driver._build_env` / `_device_requests`: when `use_gpu` is OFF **or** the
  runtime declares no GPU need, the driver sets `NVIDIA_VISIBLE_DEVICES=void` +
  `CUDA_VISIBLE_DEVICES=""` and omits `device_requests` — the container genuinely sees no GPU.
- **server.py selects the device at load:** `torch.cuda.is_available()` → `cuda` else `cpu`.
  It **never raises** on missing CUDA (that is F5's contract, not XTTS's). `/v1/metadata`
  reports the live `substrate` (`gpu`/`cpu`).

Resulting, explicit Phase-K behavior:

| Settings → Use GPU (CUDA) | Host has CUDA | XTTS device |
|---|---|---|
| ON | yes | **CUDA** (fast) |
| ON | no | CPU (driver requested GPU, none present; torch falls back) |
| OFF | yes | **CPU** (driver hides the GPU; setting is authoritative) |
| OFF | no | CPU |

No setting is silently ignored; the runtime behavior is explicit and testable.

---

## 6. Runtime Variant opportunities (Phase H — ADR-0018/0019 validation)

XTTS is the **best validation target yet** for the Runtime Variants architecture because the
checkpoint ecosystem is real and active:

| Variant kind | Source | Trust tier (ADR-0019) | Status |
|---|---|---|---|
| **Base** | bundled `coqui/XTTS-v2` checkpoint in the image | `verified` | shipped: `variants/base.json` |
| Fine-tuned checkpoint | a `peakvox`-trained or partner checkpoint | `verified` | future |
| Community checkpoint | HF community fine-tunes (language/style) | `community` | future (import via ADR-0019 validate-only endpoint) |
| Imported HF checkpoint | arbitrary HF `xtts`-format checkpoint | `community`/`private` | future |

The key property XTTS proves: **a new checkpoint attaches as a RuntimeVariant of the same
`xtts-v2` runtime — no new Docker image, no new model id** (ADR-0018). `variants/base.json`
formalizes the bundled checkpoint as the explicit, default, `verified` base, so future
imports are siblings rather than special cases. Speaker-latent caching (precomputing XTTS
`gpt_cond_latent` + `speaker_embedding` as a variant artifact) is a documented **future**
optimization; the first integration uses the simpler `reference_sample`-at-inference path for
parity with F5.

---

## 7. Decisions locked by this discovery

1. `runtime_id = model_id = "xtts-v2"`, `provider = "xtts"` (F5's same-id convention).
2. Capability surface = F5's surface (no streaming/emotion/training/VC over-claim).
3. `gpu: "optional"` + real CPU fallback in `server.py` (the deliberate divergence from F5).
4. `reference_sample` realization; `/v1/variants/build` returns 501 (in-process adapter owns build).
5. CE-disabled by default (`status="disabled"`), `editions=["community","cloud"]`, CPML non-commercial.
6. `variants/base.json` ships; checkpoint ecosystem documented as future variants.
7. ADR-0021 records the integration; no new contract is invented.

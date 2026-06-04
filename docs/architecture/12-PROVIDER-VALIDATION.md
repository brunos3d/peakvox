# 12 — Provider Validation Program

**Status:** Active validation framework · **Date:** 2026-06-04
**Companion to:** [`11-PHASE-1-RETROSPECTIVE`](11-PHASE-1-RETROSPECTIVE.md)

> **Purpose.** Define the process a model provider must pass before PeakVox may claim to
> *support* it, then apply that process to every registered provider and to the two candidate
> providers (Fish Audio S2 Pro, Kokoro). "Supported" is a high bar: it means a real model runs
> end-to-end through the Runtime, not that an adapter exists. This document distinguishes
> **integrated** (an adapter + metadata exist) from **validated** (the model actually works).

---

## 1. The eight validation gates

A provider is **supported** only after all eight gates pass against real weights. Each gate has
an explicit pass condition; a provider's status is the lowest gate it has not cleared.

| # | Gate | Pass condition |
|---|---|---|
| G1 | **Installation** | Weights/manifest fetch into the model cache (real `snapshot_download` or provider installer); idempotent; resumable-or-documented. |
| G2 | **Lifecycle** | `install → activate → deactivate → update → remove` mutate persisted `models.status`, sync the in-memory registry, and survive restart. |
| G3 | **Variant build** | `adapter.build_variant()` produces a real provider artifact (not a stub) from a Voice's source; status → `ready`; an artifact version row is written. |
| G4 | **Runtime resolution** | `runtime.resolve(public_voice_id, model)` returns the correct adapter + variant; edition/availability/active checks enforced. |
| G5 | **Generation** | `runtime.generate(...)` writes real audio of the requested text in the requested voice. |
| G6 | **Capability** | Declared `ModelCapabilities` match observed behaviour (no over-claim); capability-gated controls render correctly. |
| G7 | **Performance** | Load time, VRAM, and RTF measured on reference hardware; recorded in `provider_metadata`. |
| G8 | **Error recovery** | Failed build → `failed` + retry; OOM/load failure surfaces a clean error; offload/VRAM discipline holds across model switches. |

**Status vocabulary used below:** ✅ pass · ⚠ partial · ⛔ not started · n/a.

---

## 2. Provider scorecard (current, honest)

| Gate | OmniVoice Base | OmniVoice Singing | Fish Audio S2 Pro | Kokoro |
|---|---|---|---|---|
| G1 Installation | ⚠ real loader, no install test | ⚠ disabled | ⛔ HF install rejects provider | ⛔ no adapter |
| G2 Lifecycle (state) | ✅ tested | ✅ tested | ✅ tested (state only) | ⛔ |
| G3 Variant build | ✅ reference_sample | ✅ reference_sample | ⚠ stub (no embedding) | ⛔ |
| G4 Runtime resolution | ✅ | ✅ | ✅ | ⛔ |
| G5 Generation | ⚠ real code, no e2e test | ⛔ unverified | ⛔ `NotImplementedError` | ⛔ |
| G6 Capability match | ⚠ unverified vs real output | ⛔ | ⛔ | ⛔ |
| G7 Performance | ⛔ not measured here | ⛔ | ⛔ | ⛔ |
| G8 Error recovery | ⚠ offload discipline real | ⛔ | ⚠ raises cleanly | ⛔ |
| **Overall** | **Partially validated** | **Integrated, unverified** | **Integrated, not validated** | **Research only** |

**No provider currently passes all eight gates.** OmniVoice Base is closest (real engine, proven
in the original product) but lacks an automated end-to-end generation test and measured
performance numbers in this suite.

---

## 3. Fish Audio S2 Pro — findings

**Source of truth:** <https://huggingface.co/fishaudio/s2-pro> ·
license <https://huggingface.co/fishaudio/s2-pro/blob/main/LICENSE.md>

### 3.1 Canonical metadata (fetched 2026-06-04)

| Field | Canonical value |
|---|---|
| Name / author | Fish Audio S2 Pro / Fish Audio |
| License | Fish Audio Research License — research/non-commercial free; commercial requires a separate license (`business@fish.audio`) |
| Architecture | Dual-AR (Dual-Autoregressive) decoder-only transformer + RVQ codec; Slow AR ~4B + Fast AR ~400M; 10 RVQ codebooks, ~21 Hz |
| Size / dtype | 5B params, BF16 |
| Languages | 80+ (Tier-1: JA/EN/ZH; Tier-2: KO/ES/PT/AR/RU/FR/DE) |
| Control | 15,000+ free-form inline textual tags (`[whisper]`, `[excited]`, `[pause]`) |
| Runtime | SGLang streaming inference engine |
| Performance | RTF 0.195, ~100 ms first-audio, 3,000+ tokens/s on a single NVIDIA H200 |
| Paper / repo | <https://huggingface.co/papers/2603.08823> · <https://github.com/fishaudio/fish-speech> |
| **Voice-cloning method** | **NOT STATED on the model card** |

**Registry updated** (`model_catalog.py`): license URL → the canonical `LICENSE.md`; languages
80+; architecture + performance recorded; paper → HF papers URL. Per ADR-0007 rule 6, the
unknown cloning method is now an **explicit assumption note**, not a silent claim.

### 3.2 The critical finding — the speaker-embedding assumption is unverified

PeakVox models Fish as `realization_type = "embedding"` and declares
`supports_speaker_embeddings = True`. **The canonical model card does not document the
voice-conditioning mechanism at all.** The embedding realization is a *PeakVox integration
assumption*, not a canonical fact. Validation must confirm one of:

- Fish conditions on a **precomputed speaker embedding** (current assumption → `embedding`); or
- Fish conditions on a **raw reference clip + transcript** (→ `reference_sample`, like OmniVoice); or
- Fish uses a **prompt/voice-id** scheme (→ `prompt` / `speaker_token`).

This is the single highest-value Fish validation task: until it is confirmed against the real
`fish-speech` API, the realization type may be wrong.

### 3.3 Task checklist status

| Task | Status |
|---|---|
| 1. Fetch canonical metadata | ✅ done |
| 2. Update registry metadata | ✅ done (`model_catalog.py`) |
| 3. Add source URL | ✅ (HF page + repo in `metadata_sources`) |
| 4. Add license URL | ✅ (canonical `LICENSE.md`) |
| 5. Add provider metadata | ✅ (architecture, performance, assumption notes) |
| 6. Validate install lifecycle | ⛔ `_KNOWN_PROVIDERS` excludes `fish-audio`; HF install rejects it |
| 7. Validate runtime loading | ⛔ `load()` raises `NotImplementedError` |
| 8. Validate actual inference | ⛔ `generate()` raises `NotImplementedError` |
| 9. Validate speaker-embedding generation | ⛔ embedding never computed (`computed: false`) |
| 10. Validate VoiceVariant creation | ⚠ row created, but artifact is a stub |
| 11. Validate Artifact version creation | ⚠ versioning works generically; no real Fish artifact |
| 12. Validate Runtime resolution | ✅ `test_fish_adapter`, `test_universal_voice_asset` |
| 13. Validate generation output | ⛔ blocked by 7–9 |

### 3.4 Conclusions

- **Production-viable as a CE provider?** **No, not yet.** Inference is unwired and the
  conditioning mechanism is unconfirmed. Licensing makes it **CE-only** (non-commercial) — it can
  never be a Cloud provider without a commercial Fish license (already encoded:
  `editions=["community"]`, `commercial_use=False`).
- **Additional realization types required?** **Undetermined** until §3.2 is resolved. If Fish
  turns out to be reference-sample based, no new type is needed; if embedding-based, the existing
  `embedding` type suffices. **No new abstraction is justified yet** — validate first.
- **Additional Runtime abstractions required?** **None identified.** The SGLang runtime and the
  `torch/sglang` requirement fit the existing adapter seam; integration is an adapter-internal
  concern. If real inference needs a streaming response, that is an adapter/Runtime generation
  extension to evaluate *after* G5, not now.

**Recommended next step for Fish:** wire `load()`/`generate()` against `fish-speech` behind the
existing adapter, add `fish-audio` to `_KNOWN_PROVIDERS` (or give Fish its own installer), and
confirm the conditioning mechanism — then re-run gates G1, G3, G5, G7, G8.

---

## 4. Kokoro — provider research (not integrated)

**Source of truth:** <https://huggingface.co/hexgrad/Kokoro-82M> · license Apache-2.0

> **Do not implement.** This is a compatibility analysis to answer: does ADR-0006 already cover
> Kokoro, and does the Universal Voice Runtime thesis survive a *non-cloning* provider?

### 4.1 Canonical facts

| Field | Value |
|---|---|
| Name / author | Kokoro-82M / hexgrad |
| License | **Apache-2.0** (permissive — CE *and* Cloud eligible) |
| Architecture | StyleTTS 2 + ISTFTNet (decoder-only, no diffusion) |
| Size | **82M params** (tiny vs OmniVoice 0.6B, Fish 5B) |
| Runtime | `kokoro` Python library (≥0.9.2) + `misaki` G2P + `espeak-ng` |
| GPU | Not required to be stated; trained on A100 (runs CPU-capably given 82M size) |
| Voices | **54 preset voices** (e.g. `af_heart`); selected by id |
| **Voice mechanism** | **Preset voice packs — NO cloning, NO reference audio, NO user embeddings** |
| Papers | StyleTTS2 [2306.07691], iSTFTNet [2203.02395] |
| Repo | <https://github.com/hexgrad/kokoro> |

### 4.2 Architecture compatibility analysis

| Question (from the program) | Answer |
|---|---|
| Realization type? | **`voice_pack`** — a Kokoro "voice" is a bundled preset id, not a built artifact. |
| Training requirements? | **None** — no per-voice training; voices ship with the model. |
| Voice asset format? | A **preset identifier string** (`af_heart`), not audio/embedding/checkpoint. |
| Runtime requirements? | `kokoro` lib + `misaki` + `espeak-ng` (system dep) — a **new provider/runtime**, not torch-direct. |
| GPU requirements? | Light; CPU-viable (82M). Good CE fit. |
| Inference workflow? | `KPipeline(lang_code)(text, voice='af_heart')` → audio. |
| Installation workflow? | `pip install kokoro>=0.9.2 soundfile` + `apt-get install espeak-ng`; weights via HF. |
| Capability mapping? | `supports_tts`, `supports_multilingual`, **`supports_voice_design`** (voice = preset choice); **`supports_voice_cloning = False`**, `supports_reference_audio = False`. |

### 4.3 Does ADR-0006 cover Kokoro?

**Format: yes. Build semantics: not fully — a refinement is warranted (documented, not built).**

- ADR-0006's open taxonomy already lists **`voice_pack`** and ADR-0008 lists it as a build
  strategy ("select/download a preset pack. No build (metadata-only)"). So the *artifact format*
  is covered.
- The gap is in ADR-0008's **build-pipeline assumption**: every documented strategy starts from
  *"the Voice's canonical reference audio"* and the onboarding flow is "user uploads samples →
  build variant." **Kokoro cannot realize an arbitrary user Voice at all** — it has no cloning.
  A Kokoro "variant" is the *selection of a model-owned preset*, which inverts the Voice→Variant
  direction: the preset exists first; the Voice is a thin identity wrapping it.

### 4.4 Proposed architectural refinement (NOT to be implemented now)

Two distinct Voice origins must be acknowledged before integrating any preset-only provider:

1. **User-cloned Voice** (current model): identity → built variants from reference audio.
   Applies to OmniVoice and (assumed) Fish.
2. **Preset-backed Voice** (new): a Voice whose realization for a given model is a **fixed
   provider preset**, with `realization_type = voice_pack`, no build step, and
   `source = "preset"`. The `Voice` row already has `is_preset_voice` — this is the hook.

`ensure_variant()` (ADR-0008) would gain a **non-buildable** branch: for `voice_pack` realization
on a preset Voice, "ensure" = *verify the preset id resolves*, not *build from audio*. The
five-state lifecycle still applies (`ready` = preset present; `deprecated` = preset removed
upstream), but `pending → building` is replaced by `pending → ready` on selection.

> **Recommendation:** capture this as a future **ADR-0010 "Preset-backed Voices / non-cloning
> providers"** when (and only when) a preset provider is actually integrated. Do not add the
> abstraction speculatively. The current taxonomy is *sufficient to integrate Kokoro*; the
> refinement is about onboarding/UX semantics, not the data model.

### 4.5 The thesis stress-test verdict

Kokoro is the **first provider that breaks the "clone my voice everywhere" intuition**. The
Universal Voice Runtime survives it **only if** PeakVox accepts that *not every Voice is
realizable on every Model* — which the architecture already allows (a missing/incompatible
variant is a first-class state). Kokoro is therefore **architecture-compatible** but expands the
product's mental model from "one voice, many model realizations" to "one voice library that
includes both clonable identities and model-native preset voices."

---

## 5. Model Registry audit

Every registered built-in verified against canonical sources on 2026-06-04. **No fictional models;
no placeholder metadata remains.**

| Field | OmniVoice Base | OmniVoice Singing | Fish Audio S2 Pro |
|---|---|---|---|
| Page exists | ✅ k2-fsa/OmniVoice | ✅ ModelsLab/omnivoice-singing | ✅ fishaudio/s2-pro |
| Name | ✅ canonical | ✅ canonical | ✅ canonical |
| Provider/author | ✅ k2-fsa | ✅ ModelsLab | ✅ Fish Audio |
| License + URL | ✅ Apache-2.0 | ✅ Apache-2.0 | ✅ Fish Research → `LICENSE.md` (corrected) |
| Source URL | ✅ HF + GitHub | ✅ HF | ✅ HF + GitHub |
| Documentation URL | ✅ added | ✅ added | ✅ added |
| Paper | ✅ 2604.00688 (real, Apr-2026) | n/a (finetune) | ✅ 2603.08823 |
| Requirements | ✅ torch; VRAM unknown (explicit) | ✅ torch+GPU; VRAM unknown | ✅ torch/sglang; H200-tested |
| Languages | ✅ 646 | ✅ 11 (listed) | ✅ 80+ (corrected up from "unknown") |
| Capabilities | ✅ declared | ✅ declared | ✅ declared (embedding = assumption) |
| Realization types | reference_sample (adapter) | reference_sample (adapter) | embedding *(unverified — §3.2)* |
| Edition availability | ✅ CE+Cloud | ✅ CE+Cloud (review) | ✅ CE-only |

**Audit conclusion:** the registry honours ADR-0007. The only outstanding canonical-truth gap is
Fish's voice-conditioning mechanism, now flagged explicitly rather than asserted.

---

## 6. Models page validation

**Backend** (`api/models.py` + `model_lifecycle.py`): routes exist for
`activate / deactivate / deprecate / install / update / remove`, covered by
`test_model_lifecycle`, `test_model_management`, `test_models_api_routes`.

| Operation | State machine | Persistence | Registry sync | Real effect |
|---|---|---|---|---|
| Install | ✅ → `inactive` | ✅ `models.status` | ✅ `set_status` | ⛔ **download mocked** |
| Update | ✅ preserves activation | ✅ | ✅ | ⛔ re-fetch mocked |
| Activate | ✅ → `available` | ✅ | ✅ | ✅ (registry) |
| Deactivate | ✅ → `inactive` | ✅ | ✅ | ✅ |
| Remove | ✅ builtin→`disabled`, community→deleted | ✅ | ✅ `registry.remove` | ✅ |

- **State transitions / persistence / registry sync / restart:** validated — status is persisted
  in `models.status` and re-seeded idempotently on startup (`_seed_builtin_models` preserves
  lifecycle state; ADR-0007 rule 4). Restart behaviour is covered structurally by the migration
  idempotency tests.
- **Gap:** Install/Update do **not** download weights. The Models page can drive the *lifecycle*
  of a model truthfully, but "Install" does not yet make an un-shipped model runnable. This must
  be wired (real `snapshot_download` + provider readiness) before the page can claim functional
  install for community models.
- **Frontend** (`app/models/page.tsx`, `use-models.ts`): renders registry metadata and lifecycle
  actions. UI-level interaction validation (click-through of each action, refresh behaviour) is a
  manual/browser check not covered by the backend suite — recorded here as an open QA item.

---

## 7. Voice → Variant → Artifact → Generation validation

| Stage | OmniVoice Base | OmniVoice Singing | Fish S2 Pro | Kokoro |
|---|---|---|---|---|
| Voice identity | ✅ | ✅ | ✅ | n/a |
| Variant creation | ✅ reference_sample | ✅ reference_sample | ⚠ stub embedding | ⛔ |
| Artifact version (v1…vN) | ✅ | ✅ | ✅ generic | ⛔ |
| Rollback / retention / rebuild | ✅ (`test_runtime_variant_lifecycle`) | ✅ | ✅ generic | ⛔ |
| **Generation** | ⚠ real code, no e2e test | ⛔ | ⛔ | ⛔ |

**Same `public_voice_id` → multiple provider variants:** ✅ proven for OmniVoice Base / Singing /
Fish through one Runtime (`test_universal_voice_asset`). The identity is constant; only the
realization differs — but only OmniVoice's realization can actually *generate* today.

---

## 8. Auto-routing preparation (`model="auto"` — do not implement)

**Question:** does the Runtime hold enough metadata to choose a model automatically in future?

**Present (sufficient signals):**
- Per-model **capabilities** (`ModelCapabilities`) — can filter models that support a requested
  feature (singing, voice design, multilingual, streaming).
- **Edition availability** (`editions`) and **activation status** — can exclude unavailable models.
- **Supported tags / languages** — can match request content to a model.
- **Variant availability** — `get_variant_status` tells whether a Voice has a ready variant per
  model (ADR-0008 already flags this as a future routing signal).
- **Realization compatibility** — `adapter.supported_realization_types` vs the Voice's origin
  (clonable vs preset).

**Gaps (must exist before `model="auto"`):**
1. **No routing policy/scoring** — there is no cost/quality/latency ranking. Performance metadata
   (RTF, VRAM, load time) is partially recorded but not normalized into a comparable score (G7 is
   unmet for every provider).
2. **No "can this Voice run on this Model?" precheck in routing** — the data exists
   (`get_variant_status`, realization match) but is not aggregated into a routability function.
3. **No language/voice-origin → model capability map** — e.g. routing a clone request away from
   Kokoro (which cannot clone) requires a declared rule, not name-branching.
4. **No fallback chain semantics** — what happens when the top choice is unavailable/over budget.
5. **Performance/health telemetry** — load state and health exist; sustained latency/throughput
   metrics for ranking do not.

**Recommendation:** auto-routing is a **post-validation** feature. It should be its own ADR built
on (a) measured G7 performance numbers for ≥2 real providers and (b) a declared routing policy
that consumes capabilities + variant availability + realization compatibility. Do not build it
until at least one non-OmniVoice provider passes G5.

---

## 9. Go / no-go summary

| Provider | Verdict | Blocking gate |
|---|---|---|
| OmniVoice Base | **Ship-capable** (original product); add e2e generation test + G7 numbers to fully validate | G5 test, G7 |
| OmniVoice Singing | **Enable after verifying singing generation** | G5, G1 (enable) |
| Fish Audio S2 Pro | **Hold** — wire inference, confirm conditioning mechanism; CE-only forever (license) | G1, G3, G5 |
| Kokoro | **Architecture-compatible, not integrated** — needs an adapter + the preset-Voice refinement | G1–G5 (all) |

**Phase exit criterion (per the program):** prove the Universal Voice Runtime against at least
**one real non-OmniVoice provider end-to-end** before starting Clerk / Stripe / Billing /
Marketplace / Creator / Cloud work. That criterion is **not yet met**.

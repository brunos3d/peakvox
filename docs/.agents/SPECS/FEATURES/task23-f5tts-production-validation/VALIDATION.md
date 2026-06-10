# Task 23 — Validation Report

> **Verdict: VALIDATED.** F5-TTS reached Kokoro-level operational maturity: installed,
> started, used (voice-optional + voice-cloning), stopped, and removed entirely through
> the browser from a clean Community Edition state. Date: 2026-06-10.

## 1. Root cause analysis

### 1.1 Original blocker (stale, fixed in Task 20)
`pytorch/pytorch:2.4.0-cuda12.1-cudnn8-runtime` manifest not found — the tag never
existed upstream. Task 20 corrected the base image to
`pytorch/pytorch:2.4.0-cuda12.4-cudnn9-runtime`. Not the active blocker for this task.

### 1.2 Active blocker #1 — torch ABI mismatch baked into the image
`f5-tts==1.0.3` upgrades **torch 2.4.0 → 2.12.0+cu130** during `pip install` (via
transitive deps `bitsandbytes>=0.49` and `accelerate`, which require `torch>=2.3` and
resolve to the newest wheel). torchaudio (2.4.0) and torchvision (0.19) from the base
image remain compiled against the **old** torch C++ ABI:

```
OSError: libtorchaudio.so: undefined symbol: _ZNK5torch8autograd4Node4nameEv
```

Every container started from the image failed `/v1/generate` with
`Could not load this library: …/libtorchaudio.so`.

**Fix (Dockerfile):** after the requirements install, detect the CUDA tag from the
torch that actually got installed and re-install torchaudio + torchvision from the
matching index, plus `torchcodec` (required by f5-tts audio loading on torch ≥ 2.9).
The layer ends with an import check (`import torch, torchaudio`) so a future ABI
regression **fails the build**, not the first user generation.

### 1.3 Active blocker #2 — `pip install` without `--upgrade` is a no-op
The first version of the fix failed in the platform build: `pip install torchaudio`
sees torchaudio 2.4.0 already installed → "Requirement already satisfied" → does
nothing → the import check correctly failed the build (verified empirically in the
base image). Fixed with `--upgrade`.

### 1.4 f5-tts 1.0.3 API drift (server.py)
- `F5TTS(vocoder=…)` removed; `device` must be a **string** (`"cuda:0"`), not `torch.device`.
- `infer(ref_audio=…)` renamed to `infer(ref_file=…)`.
- `ref_file=None` crashes — voice-optional mode now falls back to the bundled
  `basic_ref_en.wav` + its transcript.
- Empty `ref_text` triggers f5-tts's Whisper ASR auto-transcription, which crashes on
  torch 2.12 ("Cannot copy out of meta tensor"). The server now falls back to the
  stored variant `transcript` param, bypassing ASR entirely.
- Generation params arriving as explicit `null` (e.g. `"speed": null`) crashed
  `float(None)` — guards changed from `in params` to `params.get(...) is not None`.

## 2. Runtime installation report (Phases 2–3)

Clean state verified before install: no `peakvox/f5-tts-runtime` image, no f5
containers, model status `available`. Install triggered **only** by the Models-page
Install button → `RuntimeManager` → `DockerRuntimeDriver` → registry build
(pull attempt first, platform Dockerfile build fallback).

| Check | Result |
|---|---|
| Progress visible | ✅ "Pulling runtime image (30%)" → "Install completed (100%)" |
| State visible | ✅ Available → Installing → Installed (badge + counters update live) |
| Errors surfaced | ✅ the intermediate build failure (§1.3) was rendered verbatim in the runtime panel with a Remove recovery action |
| Duplicate clicks blocked | ✅ Install button disabled while the operation runs |
| Result | ✅ `peakvox/f5-tts-runtime:0.1.0` (14.9 GB) built by the platform; in-image ABI check passed |

## 3. Start flow report (Phase 4)

Installed → Starting ("Booting runtime container", 50%) → **Active** in ~30 s.
Endpoint `http://peakvox-runtime-f5-tts-base:8000`, container healthy (`/health` 200),
health `ready`, RuntimeManager the sole state owner. The driver's new
`_data_volume_mounts()` attached the backend's `omnivoice-app_omnivoice_data` volume at
`/data` automatically — required for reference-audio handoff (§4.2).

## 4. F5 generation report (Phases 5–6)

### 4.1 Scenario A — voice-optional (no voice selected)
- TTS page auto-selected F5-TTS; hint shown: "No voice selected — F5-TTS will use its
  built-in default voice" (capability-driven, `supports_voice_optional`).
- First generation lazy-loaded weights (~1.4 GB from HF) then produced audio.
- Browser E2E job `c39d965d`: `model_id=f5-tts-base`, `voice=None`, **completed**;
  7 s waveform playable in the bottom player.

### 4.2 Scenario B — voice cloning (Bruno PT-BR)
- Job `f452df54`: `model_id=f5-tts-base`, voice `2b691c5b…` (Bruno PT-BR), variant
  `cd7e1075…`, **completed**; 6 s PT-BR audio playable.
- Chain proven on the clean image: variant resolution → reference audio staged to the
  shared `/data` volume → stored transcript passed as `ref_text` → inference.

### 4.3 Bug found & fixed by this E2E (the reason Phase 5 exists)
First browser generation returned **409 Conflict**: the UI displayed F5-TTS as
selected, but `GenerationPanel` submitted the raw store value `selectedModelId`
(`null`) instead of the resolved id — the backend resolved `null` to the catalog
default (omnivoice-base, not installed). The readiness/capability gates were already
evaluated against the resolved `useActiveModel()` value, so display and payload
disagreed. Fixed: the panel now submits `activeModelId` (selected → active → default
resolution), keeping payload and gates consistent.
`frontend/src/components/generation/GenerationPanel.tsx`.

## 5. Compatibility matrix report (Phase 7)

Voice selector and Voice Library, with only F5-TTS active:
- "Showing **17 compatible** with F5-TTS · **1 hidden**".
- Bruno PT-BR → **Compatible** (ready f5 variant exists).
- All other SOURCE_ASSET clones (Lucas Montano, Larissa, Jarvis, Theo, …) →
  **Build needed** (buildable: reference audio exists, variant not yet built).
- Alloy (PRESET_VOICE, kokoro-only) → **Not compatible** / hidden in the selector.
- Voice detail panel: "COMPATIBLE MODELS — 1 ready · 0 buildable · 0 not available —
  F5-TTS Ready" (runtime-aware, not declared-only).

Derivation is capability-based (creation source × model capabilities × runtime state);
no hardcoded voice-to-model lists found.

## 6. Model selector report (Phase 8)

With F5-TTS as the only installed/active model:
- Fresh navigation, hard refresh, and route transitions all auto-select **F5-TTS**.
- OmniVoice Base (catalog default) is **not** selected — runtime-aware resolution
  (`useActiveModel`: selected → active → default) wins over the catalog default.
- After the §4.3 fix the submitted payload matches the displayed selection.

## 7. Use in TTS report (Phase 9)

**Bug found:** the Voice Library's "Use in TTS" action only stored the selection —
it never navigated, so the click appeared dead. The preset tab's equivalent action
already navigated (`router.push("/")`). Fixed in `frontend/src/app/voices/page.tsx`
to match. Re-validated: Voice Library → Bruno PT-BR → Use in TTS lands on the TTS
page with **Voice = Bruno PT-BR, Model = F5-TTS, Language = Portuguese**, no manual
intervention.

## 8. Runtime Registry audit (Phase 10)

| Surface | Metadata origin | Verdict |
|---|---|---|
| Models page RUNTIME / SERVICE / REQUIREMENTS panels | `runtime-registry/f5-tts-base/descriptor.json` via RuntimeRegistry (image ref, ports, contract endpoints, image size, VRAM, edition) | ✅ registry-driven |
| Model domain metadata (capabilities, languages, license, editions) | `model_catalog.py` BUILTIN_MODELS → normalized once into the `models` table by migrations → registry hydrated from DB | ✅ ADR-0007-compliant (canonical, normalized once); not a violation — model catalog and runtime registry are distinct layers |
| Compatibility matrix | derived (creation source × `ModelCapabilities` × runtime state) | ✅ capability-driven |
| Model selector | live registry + runtime state (`useModels` polling) | ✅ |
| Generation settings | per-model `settings_schema` with unknown-key filtering | ✅ |

Minor findings (not blocking, recorded for follow-up):
- `frontend/src/editor/extensions/tagSuggestionPlugin.ts:48` and
  `EmotionToolbar.tsx:51` hardcode `modelId: "omnivoice-base"` on emotion-tag nodes —
  tag attribution, not selection; should derive from the active model.
- `NotMigratedEmptyState.tsx` carries a static phase-label map keyed by model id (UI copy only).
- `GET /settings/device` 404s repeatedly in the console — legacy endpoint still polled.

## 9. Cleanup lifecycle report (Phase 11)

- **Stop** (UI): Active → Stopped. Container `Exited (0)`, image retained —
  "Installed (image present, container stopped)". Remove is disabled while Active (guard).
- **Remove** (UI): Stopped → notInstalled. Verified: **no** f5 container in
  `docker ps -a`, **no** `peakvox/f5-tts-runtime` image in `docker images`, model
  status back to `available`, Models page back to "Not Installed", INSTALLED counter 0.
- System then **restored** by re-running Install + Start through the UI (layer-cached).

## 10. Files changed by this task

| File | Change |
|---|---|
| `runtime-registry/f5-tts-base/Dockerfile` | torchaudio/torchvision ABI re-pin layer (`--upgrade`, CUDA-tag autodetect, torchcodec, in-build import check) |
| `runtime-registry/f5-tts-base/server.py` | f5-tts 1.0.3 API fixes, voice-optional default-ref fallback, transcript→ref_text fallback, null-param guards |
| `backend/app/services/drivers/docker_runtime_driver.py` | `_data_volume_mounts()` — share backend named volumes (`/data`) with runtime containers |
| `backend/app/services/runtime.py` | `is_ready()` checks all adapters via RuntimeManager (runtime-container models) before falling back to default-adapter health |
| `frontend/src/components/generation/GenerationPanel.tsx` | submit resolved `activeModelId`, not raw store value (§4.3) |
| `frontend/src/app/voices/page.tsx` | "Use in TTS" now navigates to the TTS page (§7) |

## Evidence index

- Jobs: `c39d965d` (voice-optional, completed), `f452df54` (cloning, completed),
  plus API-path job `1c68e4b2` (voice-optional warm-up, completed).
- 409 request/response captured from the browser network panel (§4.3).
- Screenshots taken at: install progress, install-failure error surface, Active runtime
  panel, voice-optional playback, cloning playback (Bruno PT-BR), Use-in-TTS landing.
- Lifecycle states confirmed via `GET /runtimes/f5-tts-base/state` at every transition.

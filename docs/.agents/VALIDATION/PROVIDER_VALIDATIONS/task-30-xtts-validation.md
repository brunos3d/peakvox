# Provider Validation — XTTS v2 (Task 30, ADR-0021)

> Constitution Art. VII §23: **architecture-validated ≠ provider-validated.**
> This report states precisely which is which for XTTS v2 and never conflates them.

| Dimension | Status |
|---|---|
| **Architecture-validated** (the platform can represent & orchestrate XTTS, proven by tests) | ✅ **DONE** |
| **Provider-validated** (a real XTTS container generates audio end-to-end on GPU and CPU) | ⏳ **PENDING** (requires building the ~9 GB image + GPU host; procedure below) |

---

## 1. Architecture-validated — evidence (DONE)

XTTS integrates through the **existing** contracts with no model-specific
exception. Proven by automated tests:

| Claim | Evidence |
|---|---|
| Runtime descriptor validates + capabilities ⊆ bound model (ADR-0017 §1.5) | `runtime-registry/xtts-v2/tests/test_descriptor.py` (≈30 cases) |
| File-based registry auto-discovers `xtts-v2` + its `base` variant | `runtime-registry/xtts-v2/tests/test_descriptor.py::test_base_variant_*`; `backend/tests/test_runtime_registry_three_descriptors.py` (now 4 runtimes, parametrized over xtts-v2) |
| 5-endpoint Runtime Service Contract (health/ready/metadata/generate/build) | `runtime-registry/xtts-v2/tests/test_server.py` |
| **CPU fallback** — missing GPU is a fallback, not a failure (the F5 divergence) | `test_server.py::test_select_device_returns_cpu_without_cuda`, `::test_lazy_load_succeeds_on_cpu` |
| Voice cloning forwards `ref_audio_path`→`speaker_wav`; voice-optional uses a built-in speaker | `test_server.py::test_cloning_forwards_*`, `::test_voice_optional_uses_builtin_speaker` |
| Unsupported language → 422 (clear validation, not engine crash) | `test_server.py::test_unsupported_language_returns_422` |
| Inference serialized (`max_concurrent_requests: 1`) | `test_server.py::test_concurrent_generates_never_overlap` |
| Adapter routes via runtime only (no in-process exec); 600 s timeout | `backend/tests/test_xtts_adapter.py` (11 cases) |
| Catalog/wiring: `xtts-v2` present, `provider="xtts"`→`XTTSAdapter`, capabilities declared | `backend/tests/test_xtts_adapter.py`, full backend suite (765 passed) |
| Composed view (`/api/models/with-runtimes`) surfaces XTTS to API/UI | `backend/tests/test_runtime_registry_authority_t13.py`, `test_api_models_with_runtimes.py` (assert `len(BUILTIN_MODELS)`) |
| Voice compatibility: `SOURCE_ASSET → can_build` makes existing voices usable | `XTTSAdapter.get_build_strategies()`; `test_xtts_adapter.py::test_build_strategy_declares_source_asset` |

Backend suite: **765 passed, 1 skipped**. Runtime suite (per-directory):
**xtts-v2 48 passed**, f5 44, kokoro 19, omnivoice 41.

## 2. Provider-validation — procedure (PENDING)

Not run here: it needs Docker to build `peakvox/xtts-runtime:0.1.0` (~9 GB:
CUDA torch base + `coqui-tts` + ~1.8 GB weights on first inference) and a CUDA
host for the GPU leg. Steps for the validating operator:

1. **Enable** XTTS in the catalog (accepts CPML; `status` flips from `disabled`).
2. **Install** the runtime from the Models page (builds the image; `build-on-install`).
3. **GPU leg** — Settings → Use GPU (CUDA) **ON**; generate with a SOURCE_ASSET
   voice. Expect: `/v1/metadata.substrate == "gpu"`, cloned audio, RTF well < 1.
4. **CPU leg** — Settings → Use GPU (CUDA) **OFF**; restart; generate again.
   Expect: `/v1/metadata.substrate == "cpu"`, audio still produced (slower). This
   confirms the setting is authoritative (driver hides the GPU; server falls
   back). **This is the test F5-TTS cannot pass** — F5 reports `cuda_unavailable`.
5. **Voice-optional** — generate with no voice selected; expect audio via a
   built-in studio speaker.
6. **Multilingual** — generate `pt`/`es`/`ja`; expect correct-language audio.
7. **Lifecycle** — exercise stop/start/restart/update/remove/reinstall from the
   Models page; expect registry state to stay in sync (same as F5/Kokoro).

Record results here (substrate, RTF, sample artifacts) to flip
provider-validation to ✅.

## 3. Known constraints

- **License:** CPML non-commercial — CE-disabled by default; no Cloud commercial
  use until license review (ADR-0005/0021).
- **CPU speed:** functional but slow; the 600 s adapter timeout accommodates it.
- **Streaming/emotion/training:** not exposed (honest under-claim, ADR-0003).

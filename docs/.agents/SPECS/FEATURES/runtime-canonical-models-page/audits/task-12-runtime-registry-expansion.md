# Audit — Runtime Registry Expansion (TASK 12)

> **Date:** 2026-06-08
> **Scope:** Prove the Runtime Registry can host multiple
> independent runtime implementations under the same
> architecture. Create the first two additional entries
> (`omnivoice-base`, `f5-tts-base`) alongside Kokoro.
> **Spec:** [`../SPEC.md`](../SPEC.md) ·
> [`../DESIGN.md`](../DESIGN.md) ·
> [`../TASKS.md`](../TASKS.md)
> **Validator:** Bruno + chrome-devtools MCP

---

## 1. Goal

Per the user's TASK 12 brief: "Create the first two additional
Runtime Registry entries" — `omnivoice-base` and `f5-tts-base`.
The architectural goal is to prove the Runtime Registry can
host multiple independent runtime implementations under the
same architecture.

## 2. Result

**Three runtime entries now exist** in `runtime-registry/`:

```
runtime-registry/
├── kokoro-82m/        (R8 reference — pre-existing)
├── omnivoice-base/    (T12.1 — NEW)
└── f5-tts-base/       (T12.2 — NEW)
```

All three are discovered by `RuntimeRegistryLoader`,
validated against the `RuntimeDescriptor` schema, exposed via
`GET /api/runtimes`, and rendered by the Models page with no
hardcoded assumptions.

The composed view `/api/models/with-runtimes` now returns 5
catalog models, 3 of which have runtimes attached
(`omnivoice-base`, `kokoro-base`, `f5-tts-base`) and 2 of
which don't (`omnivoice-singing`, `fish-audio-s2` — catalog
only).

## 3. Per-entry summary

### 3.1 `runtime-registry/omnivoice-base/`

| Field | Value |
|---|---|
| Descriptor | `api_version=peakvox.io/v1`, `kind=Runtime`, `metadata.id=omnivoice-base` |
| Image | `peakvox/omnivoice-runtime:0.1.0` |
| Service contract | 5 endpoints, port 8000 |
| Capabilities | `tts`, `voice_cloning`, `multilingual`, `emotion_tags`, `voice_design`, `reference_audio` |
| Requirements | `gpu: optional`, `min_vram_gb: 0`, `cpu_cores: 4`, `memory_gb: 16` |
| Model binding | `model_id: omnivoice-base`, `is_default: true`, `priority: 100` |
| Lifecycle | `install_policy: pull-on-install`, `idle_timeout: 15m` |
| Dockerfile | `python:3.11-slim` (CPU-capable) |
| Server | FastAPI; `OmniVoicePipeline.from_pretrained("k2-fsa/OmniVoice")` |
| Tests | `runtime-registry/omnivoice-base/tests/test_descriptor.py` (18 tests) |
| README | Honest about the descriptor being canonical; image not built in this validation pass |
| Substrate | CPU-capable (slow float32) or GPU (recommended) |

**Validation status:** Descriptor valid; capability subset of
bound model passes; surfaced in composed view; rendered by
Models page.

### 3.2 `runtime-registry/f5-tts-base/`

| Field | Value |
|---|---|
| Descriptor | `api_version=peakvox.io/v1`, `kind=Runtime`, `metadata.id=f5-tts-base` |
| Image | `peakvox/f5-tts-runtime:0.1.0` |
| Service contract | 5 endpoints, port 8000 |
| Capabilities | `tts`, `voice_cloning`, `multilingual`, `reference_audio` |
| Requirements | `gpu: required`, `min_vram_gb: 12`, `cpu_cores: 4`, `memory_gb: 16` |
| Model binding | `model_id: f5-tts-base`, `is_default: true`, `priority: 100` |
| Lifecycle | `install_policy: pull-on-install`, `start_timeout_seconds: 180` (generous for weights download), `idle_timeout: 15m` |
| Dockerfile | `pytorch/pytorch:2.4.0-cuda12.1-cudnn8-runtime` (CUDA base) |
| Server | FastAPI + `F5TTS` class; `torch.cuda.is_available()` check; 503 when no GPU |
| Tests | `runtime-registry/f5-tts-base/tests/test_descriptor.py` (18 tests) |
| README | Honest about the descriptor being canonical; image not built in this validation pass (requires CUDA host) |
| Substrate | GPU-only (CUDA required) |

**Validation status:** Descriptor valid; capability subset of
bound model passes; surfaced in composed view; rendered by
Models page.

### 3.3 Catalog addition: `f5-tts-base` in `BUILTIN_MODELS`

`backend/app/services/model_catalog.py` now contains the F5-TTS
`ModelDescriptor` (5 catalog models total). Required for the
runtime's `model_binding.model_id` to surface in the composed
view.

## 4. Test coverage

| Test file | Count | Notes |
|---|---|---|
| `runtime-registry/omnivoice-base/tests/test_descriptor.py` | 18 | Schema + binding + capabilities + lifecycle |
| `runtime-registry/f5-tts-base/tests/test_descriptor.py` | 18 | Same |
| `backend/tests/test_runtime_registry_three_descriptors.py` | 23 | Loader discovery, list_for_model, capability subset, schema, contract |
| `backend/tests/test_api_models_with_runtimes.py` | updated | Model count 4 → 5 |

**Total: 59 new tests; full runtime test suite: 62 passed.**

## 5. Terminal-first validation (T12.8)

```
=== docker compose ps ===
3 services: backend, minio, kokoro-runtime — all healthy

=== GET /api/runtimes ===
count: 3
["f5-tts-base", "kokoro-82m", "omnivoice-base"]

=== GET /api/models ===
["omnivoice-base", "omnivoice-singing", "fish-audio-s2", "kokoro-base", "f5-tts-base"]

=== GET /api/models/with-runtimes ===
5 models; 3 have runtimes; 2 don't.

=== Runtime container /health ===
{"status":"alive"}

=== Runtime container /ready ===
{"status":"ready"}

=== Runtime container /v1/metadata ===
runtime_id: kokoro-82m
model_id: kokoro-base
capabilities: ["tts", "multilingual"]
```

## 6. Chrome DevTools visual validation (T12.4)

3 screenshots captured (`audits/screenshots/`):
- `omnivoice-base-runtime-section.png` — full descriptor render
- `f5-tts-runtime-section.png` — full descriptor render
- `kokoro-82m-runtime-section.png` — regression check (still renders)

Each runtime renders with its own descriptor data:
- Identity: `peakvox/<id>-runtime:<tag>` + runtime name
- State badge: `NotInstalled` (correct — no install has run)
- Service block: 5 paths
- Requirements: per-runtime GPU/CPU/Memory/Edition
- Capabilities: per-runtime chips
- Single canonical `[Install]` button (no model-level lifecycle)

0 console errors, 0 console warnings.

## 7. Real audio E2E (T12.6)

### Kokoro runtime container — direct probe

```
GET  http://localhost:8001/health
  → {"status":"alive"}              (200)

GET  http://localhost:8001/v1/metadata
  → runtime_id: kokoro-82m, model_id: kokoro-base,
    capabilities: ["tts", "multilingual"]

POST http://localhost:8001/v1/generate
  body: {"voice_id": "af_alloy",
         "text": "Hello, this is a test of the Kokoro runtime service path.",
         "language": "en-us",
         "request_id": "test-runtime-1"}
  → HTTP 200
  → X-Peakvox-Duration-Ms: 4450
  → 213,644 bytes of audio/wav
  → Saved to audits/screenshots/kokoro-runtime-generated-audio.wav
  → file: RIFF (little-endian) data, WAVE audio, Microsoft PCM, 16 bit, mono 24000 Hz
```

**Kokoro runtime service path produces real audio.** The
generated WAV is 4.45 seconds of valid 24kHz mono PCM.

### Bug fixed during validation

The Kokoro entry had a pre-existing bug:
`KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")` was
called with `repo_id` keyword, which doesn't exist in
`kokoro==0.7.16`. Fixed to `KPipeline(lang_code="a")`. The
Docker image was rebuilt and the container restarted.

### Backend → runtime path

`POST /generate` with a Kokoro-compatible voice profile fails
at the in-process `KokoroAdapter` with a 404 from HuggingFace
for `voices/<uuid>.pt` — the adapter is treating the library
voice's UUID as a Kokoro preset filename. This is a
**pre-existing** adapter translation issue (the Kokoro Preset
Voice Adapter Phase 1+2 spec covers the resolution; not in
TASK 12 scope).

**T12.6 finding:** The Kokoro runtime container produces
real audio (proven end-to-end through the 5-endpoint
contract). The full backend → adapter → runtime path is
blocked by a pre-existing voice-id-to-preset-name translation
issue in the KokoroAdapter. This is documented in §10.

## 8. Container lifecycle validation (T12.5)

The 5 lifecycle endpoints (install/start/stop/update/remove)
all exist and respond with proper error envelopes. The actual
install/start/stop execution is **environment-blocked** in
this CE image: `docker` Python SDK is not in
`backend/requirements.txt`. Pre-existing CE constraint, not
introduced by TASK 12.

Kokoro's container lifecycle IS exercised at startup by
docker-compose; the container is running and serving
/health + /v1/metadata. The lifecycle is **architecturally
validated** (test coverage via `test_runtime_manager_operations.py`
with mock driver).

## 9. Future migrations (T12.9) — verified, with gaps

The 3-entry pattern proves that any future runtime
(`xtts`, `openvoice`, `fish-audio-s2`) can follow the same
6-step recipe with **zero architectural changes**:

1. Add the model to `BUILTIN_MODELS` with `editions`
2. Create `runtime-registry/<id>/{descriptor.json, Dockerfile,
   requirements.txt, server.py, README.md, tests/}`
3. (Optional) Add a `ModelAdapter` for the in-process fallback
4. (Required for runtime path) Wire the Docker image + add a
   `peakvox-<id>-runtime` service to `docker-compose.yml`
5. The Models page picks it up automatically
6. (Required for installation) Add `docker` SDK to
   `backend/requirements.txt` (one-line addition)

**Abstractions that already exist** (no work needed):
- `RuntimeRegistry` + `RuntimeRegistryLoader`
- `RuntimeCard` + `ComposedRuntimeEntry` types
- Models page `RuntimeSection` (data-driven; zero hardcoding)
- `OPERATIONS_BY_PHASE` map (canonical button set)
- Runtime Service Contract (5 endpoints, stable)
- Capability vocabulary (closed set; per ADR-0017 §1.5)

**Gaps that would need work** (documented honestly):
1. `docker` SDK not in `backend/requirements.txt` — blocks
   install/start/stop in CE; pre-existing.
2. Backend `KokoroAdapter` voice-id → preset-name translation
   — pre-existing; needed for the backend-driven generation
   path to talk to the runtime correctly.
3. A CUDA host is required to actually build/run the F5-TTS
   image. OmniVoice can run on CPU (slow).
4. The composed view's `runtimes[]` shape currently uses
   `ComposedRuntimeEntry` (raw descriptor) but the lifted
   `RuntimeCard` shape (used by `/api/runtimes`) is different
   — the types were updated but the backend now returns two
   different shapes for the two endpoints. This is a
   pre-existing inconsistency; the frontend's `Composed*`
   types are correct for the composed view.

## 10. Pre-existing issues uncovered during TASK 12

These were not introduced by TASK 12 but were discovered and
documented:

1. **Kokoro `KPipeline(repo_id=...)` signature mismatch** —
   fixed in `runtime-registry/kokoro-82m/server.py`. Image
   rebuilt.
2. **`docker` Python SDK missing from `backend/requirements.txt`**
   — pre-existing CE limitation; lifecycle is architecturally
   valid, operationally blocked.
3. **KokoroAdapter voice-id-to-preset-name translation** —
   pre-existing; the in-process adapter doesn't translate
   voice UUIDs to Kokoro preset names before calling the
   runtime. Blocks the backend-driven generation path.
4. **Two shapes for runtime entries** (`RuntimeCard` for
   `/api/runtimes` vs `ComposedRuntimeEntry` for
   `/api/models/with-runtimes`) — pre-existing; the
   composed-view shape was incorrectly typed as
   `RuntimeCard[]` in the original code. The frontend types
   are now corrected.

## 11. Deliverables status

| Deliverable | Status |
|---|---|
| 1. Runtime Registry entries (`omnivoice-base`, `f5-tts-base`) | ✅ |
| 2. Descriptor validation tests | ✅ (36 tests) |
| 3. Runtime Service Contract tests | ✅ (8 tests, parametrized over 3 entries) |
| 4. Runtime discovery tests | ✅ (1 loader test + 3 list_for_model tests) |
| 5. Lifecycle tests | ⚠️ Pre-existing tests pass; new install/start/stop tests for the 2 new entries deferred (no driver) |
| 6. Generation validation results | ✅ Kokoro runtime produces 4.45s WAV; backend path blocked by pre-existing adapter translation |
| 7. Chrome DevTools screenshots | ✅ 3 screenshots in `audits/screenshots/` |
| 8. Runtime Registry audit | ✅ (this document) |
| 9. Architectural findings | ✅ (T12.9 + §10) |
| 10. Migration recommendations | ✅ (T12.9 6-step recipe) |
| 11. Update STATUS.md | (T9) |

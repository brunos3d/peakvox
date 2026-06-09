# VALIDATION — Runtime TTS End-to-End Validation (Task 16)

Status: VALIDATED — 2026-06-09

## Phase 1 (partial — activation gate blocked)

Executed browser validation:
- Text To Speech page flow executed in browser with text + selected voice.
- Generate request reached backend POST /generate.
- Frontend diagnostics captured 409 response:
	- message: Model 'omnivoice-base' is not active (status: inactive)
	- category: conflict
	- request_id: 470e1706413a
- Backend logs confirm POST /generate 409 Conflict for the same run.

Outcome: blocked at model activation/state gating. Unblocked by Task 17.

## Phase 2 (final — full browser audio validation)

**Date:** 2026-06-09
**Branch:** feat/peakvox-phase-1

Architectural corrections applied before validation (this session):
- Removed `peakvox-kokoro-runtime` from docker-compose — runtimes are user-installed, not platform infrastructure.
- Removed `KOKORO_RUNTIME_URL` env var from backend — endpoint is injected by RuntimeManager, not env.
- Removed `backend depends_on: peakvox-kokoro-runtime` — platform boots with only frontend, backend, minio.
- KokoroAdapter.generate() dispatch changed from env var check to `runtime_endpoint is not None`.
- HTTPTransport.post_binary() added — returns (bytes, headers) for audio/wav responses.
- request_id always provided (job_id or uuid.uuid4()) — Kokoro runtime requires non-empty string.

Full user flow validated in browser:
1. Platform booted — 0 runtimes installed (clean state).
2. Models page → Kokoro 82M → Install → "Installed (image present, container stopped)".
3. Models page → Kokoro 82M → Start → "Active (container running, /health 200)".
   - Container: peakvox-runtime-kokoro-82m:8000
   - Endpoint: http://peakvox-runtime-kokoro-82m:8000
4. Text to Speech → Voice: Alloy (en-us · Preset) + Model: Kokoro 82M.
5. Generate → backend job dispatched → KokoroAdapter POSTs /v1/generate → WAV bytes received.
6. Browser audio player rendered waveform, duration 0:06.
7. Backend logs: GET /audio/2d9a0bf7791191b6.wav — 200 OK + 206 Partial Content (browser range request).

Runtime resolution chain confirmed:
- RuntimeManager.resolve("kokoro-base") → RuntimeResolution(endpoint="http://peakvox-runtime-kokoro-82m:8000")
- PeakVoxRuntime.generate() → injects runtime_endpoint → KokoroAdapter._generate_via_runtime()
- HTTPTransport.post_binary("/v1/generate", body) → (wav_bytes, headers)
- output_path.write_bytes(wav_bytes) → MinIO upload → audio served to browser

Test suite: 665/665 pass (0 fail) — all existing tests preserved.

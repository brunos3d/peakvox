# VALIDATION — Runtime/Generation Activation Unification (Task 17)

Status: VALIDATED — 2026-06-09

## Phase 1 — Root cause + fix

Root cause identified:
- Request path: Text To Speech UI -> POST /generate -> create_generation_job -> runtime.ensure_active -> PeakVoxRuntime.ensure_active
- Exact pre-fix gate:
	- file: backend/app/api/generation.py
	- function: create_generation_job
	- condition: runtime.ensure_active(model.id)
- Exception source:
	- file: backend/app/services/runtime.py
	- function: PeakVoxRuntime.ensure_active
	- condition: descriptor.activation_status != "active"
	- source of truth used before fix: legacy ModelDescriptor.status / activation_status

Fix validated:
- When runtime manager is attached and runtime descriptors exist, generation eligibility now uses RuntimeManager.resolve(model_id) / active RuntimeInstance state.
- Direct API validation:
	- POST /generate for omnivoice-base returns 200 and creates a job instead of 409 inactive.
- Browser validation:
	- Kokoro UI request captured with POST /generate status 200 using model_id=kokoro-base.
	- The original inactive 409 is eliminated.

Downstream blockers discovered after fix (Phase 1):
- Kokoro browser job now fails after dispatch, not at activation gate:
	- backend job error: runtime path attempts to resolve preset voice UUID as Hugging Face `.pt` asset.
- OmniVoice generation also advances past activation gate, but blocked by GPU/CPU inference issues.

## Phase 2 — Architecture corrections + full browser validation

**Date:** 2026-06-09

Additional violations corrected:
- `KOKORO_RUNTIME_URL` env var removed from entire codebase — env-based endpoint discovery is an architecture violation.
- `peakvox-kokoro-runtime` removed from docker-compose — runtime is user-installed, not platform infrastructure.
- Endpoint injection path: PeakVoxRuntime.generate() now passes RuntimeResolution.endpoint as runtime_endpoint kwarg.
- KokoroAdapter dispatch changed from `os.environ.get(KOKORO_RUNTIME_URL_ENV)` to `runtime_endpoint is not None`.
- HTTPTransport.post_binary() added for WAV binary responses (server returns audio/wav, not JSON).
- request_id always provided (UUID generated when job_id is None) — Kokoro server requires min_length=1.

Final state:
- Browser: Alloy (Kokoro preset) → Generate → waveform rendered → audio plays. Duration: 0:06.
- Backend logs: GET /audio/2d9a0bf7791191b6.wav 200 OK + 206 Partial Content.
- 665/665 tests pass.

Ownership audit (finalized):
- Runtime active state owner: RuntimeManager + RuntimeInstance cache
- Runtime activation owner: RuntimeManager lifecycle / runtime driver
- Generation eligibility owner: PeakVoxRuntime.ensure_active delegating to RuntimeManager
- Endpoint discovery owner: RuntimeManager.resolve() → RuntimeResolution.endpoint
- Adapter HTTP transport owner: HTTPTransport (post_binary for binary audio responses)
- Legacy model status: compatibility/fallback metadata only; not authoritative for runtime-enabled generation

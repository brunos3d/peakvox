# HANDOFF

> Agent-to-agent transfer document. Goal: minimize context loss between agents. The incoming
> agent reads this after [`PROJECT_STATE.md`](PROJECT_STATE.md) to know exactly where the
> previous agent stopped. Overwrite the "Current handoff" section each session; append a dated
> line to the log.

---

## Current handoff

**From:** Task 24 — TTS Generation Regression Investigation · **Date:** 2026-06-10 ·
**Branch:** `feat/peakvox-phase-1`

### Last completed work

- **T24 complete and VALIDATED.** Both real TTS providers (OmniVoice, F5-TTS) generate
  reliably through the Runtime Registry architecture. Five root causes fixed:
  1. **OmniVoice adapter never routed to the runtime** — `generate()` unconditionally
     raised the "in-process execution not available" error even with the container
     Active (T21 decontamination removed torch but never added the HTTP path). Now
     routes via `HTTPTransport.post_binary("/v1/generate", …)`.
  2. **30 s transport timeout vs ~3.5 min CPU inference** — OmniVoice adapter now
     constructs its transport with `timeout_seconds=600.0`.
  3. **F5-TTS meta-tensor crash** — `transcript: null` variants sent `ref_text=""`,
     which makes f5-tts 1.0.3 run Whisper ASR (crashes on torch 2.12). Fixed twice:
     adapter resolves an effective ref_text (arg → variant transcript → upstream
     param → placeholder); the f5 runtime server applies the same placeholder fallback.
  4. **OmniVoice runtime server used a nonexistent API** — `OmniVoicePipeline` → real
     class `OmniVoice` (`from_pretrained("k2-fsa/OmniVoice")`), `generate()` surface,
     voice_design tag lists joined into one instruct string (arity rule).
  5. **Duration 0.0 for valid OmniVoice audio** — `(1, N)` batch tensors squeezed
     before WAV encoding so `X-Peakvox-Duration-Ms` is correct.
- **Issues 3–4 from the task confirmed by-design:** voice-optional UI differences are
  capability-driven (`supports_voice_optional` on F5-TTS only, Constitution Art. III
  §10); sample-voice compatibility already reports `['f5-tts-base']` for all
  SOURCE_ASSET voices.
- **Live validation:** F5-TTS — Fireship 8.10 s (the crashing voice), Donald Trump
  6.87 s, Bruno PT-BR 3.46 s, voice-optional 5.75 s; OmniVoice — 5.92 s via container
  with correct duration. Consecutive generations succeeded.
- **Tests:** 53 new regression tests across 4 suites; backend full suite 680 passed,
  1 skipped; runtime suites 41/41/19 passed.

### Files changed (this session)

- **Modified (backend):** `app/services/model_adapters/omnivoice_adapter.py`,
  `app/services/model_adapters/f5_adapter.py`
- **Modified (runtime-registry):** `omnivoice-base/server.py`, `f5-tts-base/server.py`
- **New (tests):** `backend/tests/test_t24_omnivoice_adapter_routing.py`,
  `backend/tests/test_t24_f5_adapter_ref_text.py`,
  `runtime-registry/omnivoice-base/tests/test_server.py`,
  `runtime-registry/f5-tts-base/tests/test_server.py`
- **Docs:** `SPECS/FEATURES/task24-tts-generation-regression/` (SPEC/DESIGN/TASKS/
  VALIDATION/STATUS), `CURRENT_CONTEXT.md`, `HANDOFF.md`

### Architectural decisions taken

- The cloning-without-transcript path injects a neutral placeholder ref_text rather
  than depending on any ASR — ASR is the crashing component, and a transcription
  dependency would reintroduce the failure class. Stored real transcripts always win
  the precedence chain and remain the quality-preferred path.
- Per-model latency knowledge lives in the adapter (600 s OmniVoice timeout), not in
  the shared HTTPTransport default.
- Runtime server tests load `server.py` via `importlib` under unique module names and
  stub `torch` in `sys.modules` — runnable in the torch-free backend venv, no
  cross-suite `import server` collisions.

### Risks (updated)

- **Running containers carry server fixes via `docker commit`**, not a rebuilt image.
  The registry sources contain the canonical fixes; the next image rebuild supersedes
  the committed layers. Until then, removing + reinstalling a runtime through the UI
  rebuilds from sources and keeps the fixes.
- Placeholder ref_text slightly weakens cloning conditioning vs a true transcript
  (validated acceptable by ear on Fireship/Trump).
- Fish Audio real inference still blocked (24 GB+ VRAM). No GPU in CI.

### Open issues

- Jarvis / Lucas Montano have no F5-TTS variant yet — build via Voice Library UI.
- Rebuild `peakvox/omnivoice-runtime` + `peakvox/f5-tts-runtime` images from registry
  sources and re-run the T24 live matrix.
- Two `runtime-registry/*/tests/test_descriptor.py` tests need the backend on
  `PYTHONPATH` (pre-existing harness property).

### Recommended next task

**Rebuild both runtime images from `runtime-registry/` sources and re-validate the T24
live matrix**, then build the missing F5-TTS variants (Jarvis, Lucas Montano) through
the Voice Library. After that, return to the roadmap queue
([`ROADMAP/BACKLOG.md`](ROADMAP/BACKLOG.md)).

---

## Handoff log

- 2026-06-05 — Kokoro Preset Voice Adapter Phase 1 complete. 81 tests, 339/339 all pass.
- 2026-06-05 — Documentation Operating System created under `docs/.agents/`; `AGENTS.md` updated. Application code unchanged. Next: stabilize the dirty working tree.
- 2026-06-05 — Kokoro Preset Voice Phase 2 complete. 8 new tests, 347/347 all pass. Frontend Preset Voices tab added.
- 2026-06-05 — **Kokoro provider validation complete (G5 passed).** Real audio E2E through Runtime. `kokoro` added to requirements.txt. Cloud readiness gate open.
- 2026-06-10 — **T24 TTS generation regression complete (VALIDATED).** OmniVoice routed through its runtime container; F5-TTS meta-tensor crash eliminated (ASR bypass at adapter + server); OmniVoice server API corrected. 53 new regression tests; backend 680 passed.

# CURRENT CONTEXT

> Operational memory. Changes frequently — update at the start and end of every working
> session. Keep it short and current; move history to the execution ledger.

**As of:** 2026-06-10

- **Current focus:** **T24 (TTS Generation Regression
  Investigation — OmniVoice + F5-TTS)** is **VALIDATED**
  (2026-06-10). Both real providers generate reliably
  through the Runtime Registry architecture. Root causes
  fixed: the OmniVoice adapter never consumed
  `runtime_endpoint` (T21 left it without the HTTP path —
  now routes via HTTPTransport, 600 s timeout for CPU
  inference); the F5-TTS "meta tensor" crash was empty
  `ref_text` triggering f5-tts's Whisper ASR on torch 2.12
  (fixed at adapter + runtime server with an
  effective-ref_text chain and a neutral placeholder); the
  OmniVoice runtime server shipped against a nonexistent
  API (`OmniVoicePipeline` → `OmniVoice`, `generate()`
  surface, instruct list→string join, batch-dim squeeze
  for correct duration). Issues "voice-optional
  inconsistency" and "sample-voice compatibility" were
  confirmed by-design (capability contract). 53 new
  regression tests; backend 680 passed. See
  `SPECS/FEATURES/task24-tts-generation-regression/`.
  Predecessors T17–T23 (activation unification, F5-TTS
  install/integration/production-validation) are VALIDATED
  in their spec folders.
- **Current branch:** `feat/peakvox-phase-1`
- **Current ADRs in play:** ADR-0016/0017 (runtime
  services — implemented and refined), ADR-0003
  (capability contract — governs voice-optional UI),
  ADR-0008/0009/0010/0011 (variants, artifacts, sources).
- **Current specs:**
  `docs/.agents/SPECS/FEATURES/task24-tts-generation-regression/`
  (latest), plus task17–task23 folders for the runtime
  activation + F5-TTS lineage.
- **Current blockers:** none for CE generation. Running
  OmniVoice/F5-TTS containers carry the T24 server fixes
  via `docker commit`; the next image rebuild from
  `runtime-registry/` sources supersedes them. Fish Audio
  real inference still deferred (codec/VRAM); no GPU in CI.
- **Current validation goal:** rebuild the two runtime
  images from registry sources and re-run the T24 live
  matrix; build F5-TTS variants for the remaining sample
  voices (Jarvis, Lucas Montano) via the Voice Library.

---

**Related:** [`ACTIVE_WORK.md`](ACTIVE_WORK.md) · [`NEXT_TASK.md`](NEXT_TASK.md) ·
[`HANDOFF.md`](HANDOFF.md) · [`PROJECT_STATE.md`](PROJECT_STATE.md) ·
[`SPECS/FEATURES/task24-tts-generation-regression/`](SPECS/FEATURES/task24-tts-generation-regression/) ·
[`SPECS/FEATURES/task23-f5tts-production-validation/`](SPECS/FEATURES/task23-f5tts-production-validation/) ·
[`DECISIONS/adr-0017-runtime-services-implementation.md`](DECISIONS/adr-0017-runtime-services-implementation.md) ·
[`DECISIONS/adr-0003-model-capability-contract.md`](DECISIONS/adr-0003-model-capability-contract.md)

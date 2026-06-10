# ACTIVE WORK

> Only work that is **actively being executed right now**. No roadmap, no future ideas, no
> speculative work — those live in [`ROADMAP/BACKLOG.md`](ROADMAP/BACKLOG.md) and
> [`OPEN_DECISIONS.md`](OPEN_DECISIONS.md). When an item is no longer being worked, move it
> to the execution ledger or remove it.

**As of:** 2026-06-10 · **Branch:** `feat/peakvox-phase-1`

## In flight

*(nothing — T24 closed; pick up [`NEXT_TASK.md`](NEXT_TASK.md))*

## Not in flight (recently completed)

- **T24 — TTS Generation Regression Investigation (OmniVoice + F5-TTS).** ✅ **VALIDATED
  2026-06-10.** OmniVoice adapter now routes generation through its runtime container
  via HTTPTransport (600 s timeout for CPU inference); F5-TTS meta-tensor crash
  eliminated by an effective-ref_text chain + placeholder (ASR bypass) at both the
  adapter and the runtime server; OmniVoice runtime server corrected to the real
  upstream API (`OmniVoice`, `generate()`, instruct list→string, batch-dim squeeze).
  Voice-optional UI differences and sample-voice compatibility confirmed by-design
  under the capability contract. 53 new regression tests; backend 680 passed. See
  [`SPECS/FEATURES/task24-tts-generation-regression/`](SPECS/FEATURES/task24-tts-generation-regression/).
- **T23 — F5-TTS production validation.** ✅ VALIDATED 2026-06-10. Clean-install
  lifecycle through the UI, torch ABI fix baked into the Dockerfile, f5-tts 1.0.3 API
  drift absorbed. See [`SPECS/FEATURES/task23-f5tts-production-validation/`](SPECS/FEATURES/task23-f5tts-production-validation/).
- **T22 — F5-TTS first-class integration.** ✅ Capability-driven platform evolution
  (`supports_voice_optional`, compatibility resolver, runtime-aware selectors).
- **T21 — Backend decontamination.** ✅ In-process model execution removed; adapters
  are torch-free and route through runtime containers only.
- **T17–T20.** ✅ Runtime activation/generation state unification; F5-TTS runtime
  install + base-image fix; voice–model compatibility (T19).
- **Phase 2 + Phase 3 runtime-service foundation (ADR-0016/0017).** ✅ Complete —
  registry, drivers, transport, runtime-canonical Models page, T13 functional
  lifecycle. Earlier entries preserved in the execution ledger.

## Not in flight (explicitly paused)

- **Runtime image rebuilds** for omnivoice-base / f5-tts-base from registry sources
  (running containers carry T24 fixes via `docker commit`; sources are canonical).
- **Fish Audio real inference** — blocked on hardware (24 GB+ VRAM).
- **Cloud phases** (auth/billing/creators/marketplace) — held behind the deliberate
  Cloud-planning decision; provider-validation gate is open.
- **Runtime Persistence ADR** (Decision 12) — future ADR, non-blocking.

---

**Related:** [`NEXT_TASK.md`](NEXT_TASK.md) · [`CURRENT_CONTEXT.md`](CURRENT_CONTEXT.md) ·
[`IMPLEMENTATION/EXECUTION_HISTORY/EXECUTION_LEDGER.md`](IMPLEMENTATION/EXECUTION_HISTORY/EXECUTION_LEDGER.md) ·
[`SPECS/FEATURES/task24-tts-generation-regression/`](SPECS/FEATURES/task24-tts-generation-regression/)

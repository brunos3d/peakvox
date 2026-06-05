# CURRENT CONTEXT

> Operational memory. Changes frequently — update at the start and end of every working
> session. Keep it short and current; move history to the execution ledger.

**As of:** 2026-06-05

- **Current focus:** CE hardening after the Phase 3 spine — Voice Library 2.0, variant
  backfill UX, and Fish Audio provider wiring.
- **Current branch:** `feat/peakvox-phase-1`
- **Working tree:** clean — 4 commits this session landed the Fish-adapter expansion,
  variant schemas, VoiceSourceAsset model, migration fixes, and tests (262/262 passing).
- **Current ADR in play:** ADR-0011 (Voice Creation Sources) and ADR-0008/0009 (build
  lifecycle + artifacts) — the surfaces touched by backfill/variant work.
- **Current spec:** `docs/.agents/SPECS/FEATURES/2026-06-04-voice-library-2-design.md`
  and `docs/.agents/IMPLEMENTATION/PLANS/2026-06-04-variant-backfill-ux.md`.
- **Current blockers:** Fish Audio real inference deferred (codec/VRAM); no GPU in CI.
- **Current validation goal:** prove one non-OmniVoice provider end-to-end through the
  Runtime — this is the gate before any Cloud work.

---

**Related:** [`ACTIVE_WORK.md`](ACTIVE_WORK.md) · [`NEXT_TASK.md`](NEXT_TASK.md) ·
[`HANDOFF.md`](HANDOFF.md) · [`PROJECT_STATE.md`](PROJECT_STATE.md)

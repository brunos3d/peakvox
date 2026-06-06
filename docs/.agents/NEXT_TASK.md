# NEXT TASK

> Exactly one highest-priority task — the execution queue head. When this task is done, move
> it to the execution ledger and promote the next item from [`ROADMAP/BACKLOG.md`](ROADMAP/BACKLOG.md).

**As of:** 2026-06-05

## Task: Provider-validation done — unblock Cloud planning

- **Priority:** P0 (was blocking Cloud phases — now resolved).
- **Status:** ✅ **Kokoro G5 confirmed** — real audio generated E2E through the Runtime.
  The `kokoro` pip package is installed, the adapter produces real WAV output, and
  347/347 backend tests pass. See `VALIDATION/PROVIDER_VALIDATIONS/kokoro-validation-report.md`.
- **Decision (OPEN_DECISIONS.md Decision 1):** Option 3 chosen — Kokoro validated as the
  first non-OmniVoice provider. The Cloud readiness gate is now open.
- **Remaining provider gaps (not blocking):**
  - Fish Audio S2 Pro — still blocked on hardware (24GB+ VRAM). Not a P0 concern.
  - Kokoro G7 (performance) and G8 (error recovery) — not measured; low priority.
  - OmniVoice Base E2E audio test — would be nice to have; no GPU in CI.
- **Next:** Cloud architecture planning (ADR work for auth, billing, marketplace), or
  CE hardening (error recovery tests, performance measurement, Fish server deployment).

---

**Related:** [`ACTIVE_WORK.md`](ACTIVE_WORK.md) · [`ROADMAP/CURRENT_PHASE.md`](ROADMAP/CURRENT_PHASE.md)

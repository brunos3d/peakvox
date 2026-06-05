# NEXT TASK

> Exactly one highest-priority task — the execution queue head. When this task is done, move
> it to the execution ledger and promote the next item from [`ROADMAP/BACKLOG.md`](ROADMAP/BACKLOG.md).

**As of:** 2026-06-05

## Task: Provider-validation gate — close the gap

- **Priority:** P0 (blocks all Cloud phases — no SaaS work until at least one foreign
  provider generates real audio end-to-end through the Runtime).
- **Objective:** Get one non-OmniVoice provider generating real audio end-to-end.
  The Fish Audio adapter is wired, unit-tested, and committed, but real inference via
  S2 Pro HTTP server is blocked on hardware (codec.pth / 24GB+ VRAM).
- **Options (from [`OPEN_DECISIONS.md`](OPEN_DECISIONS.md) Decision 1):**
  1. Acquire or rent GPU hardware capable of running the Fish S2 Pro server.
  2. Switch to a different foreign provider with lighter hardware requirements.
  3. Partner with a Fish-gated inference provider.
- **Dependencies:** hardware or provider decision.
- **Expected output:** at least one end-to-end test that passes through the full
  Runtime chain with a non-OmniVoice provider, producing real audio.

---

**Related:** [`ACTIVE_WORK.md`](ACTIVE_WORK.md) · [`ROADMAP/CURRENT_PHASE.md`](ROADMAP/CURRENT_PHASE.md)

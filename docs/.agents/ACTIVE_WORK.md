# ACTIVE WORK

> Only work that is **actively being executed right now**. No roadmap, no future ideas, no
> speculative work — those live in [`ROADMAP/BACKLOG.md`](ROADMAP/BACKLOG.md) and
> [`OPEN_DECISIONS.md`](OPEN_DECISIONS.md). When an item is no longer being worked, move it
> to the execution ledger or remove it.

**As of:** 2026-06-05 · **Branch:** `feat/peakvox-phase-1`

## Not in flight

The previous in-flight work (Fish adapter expansion, variant schema, migrations, tests) has
been committed. 4 commits landed; 262/262 backend tests passing.

## In flight

1. **Provider validation.** Get at least one non-OmniVoice provider generating real audio
   end-to-end through the Runtime. Fish Audio is wired at the adapter level but blocked on
   inference hardware (codec/VRAM).

## Not in flight (explicitly paused)

- Cloud phases (auth/billing/creators/marketplace) — held behind the provider-validation
  readiness gate. Do not start.

---

**Related:** [`NEXT_TASK.md`](NEXT_TASK.md) · [`CURRENT_CONTEXT.md`](CURRENT_CONTEXT.md) ·
[`IMPLEMENTATION/EXECUTION_HISTORY/EXECUTION_LEDGER.md`](IMPLEMENTATION/EXECUTION_HISTORY/EXECUTION_LEDGER.md)

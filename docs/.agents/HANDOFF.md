# HANDOFF

> Agent-to-agent transfer document. Goal: minimize context loss between agents. The incoming
> agent reads this after [`PROJECT_STATE.md`](PROJECT_STATE.md) to know exactly where the
> previous agent stopped. Overwrite the "Current handoff" section each session; append a dated
> line to the log.

---

## Current handoff

**From:** working-tree stabilisation session · **Date:** 2026-06-05 ·
**Branch:** `feat/peakvox-phase-1`

### Last completed work

- **Stabilised and committed the in-flight working tree.** 4 commits landed:
  1. `feat(db):` VoiceSourceAsset model, creation_source column, source-entity migrations
  2. `feat(api):` variant schemas + dual-path voice_id/voice_profile_id in generation
  3. `feat(fish):` real Fish Audio HTTP inference wiring + adapter contract refactor
  4. `test:` variant API tests + Fish adapter tests
- **Fixed bug:** missing `creation_source` column in `_backfill_voice_split` INSERT (caused
  NOT NULL constraint failure in the 6 migration/backfill tests).
- **Test suite:** 262/262 passing (full backend suite green).
- Prior product work on this branch (already committed): Voice Library 2.0, Variant
  Dashboard, `/variants/backfill` endpoint and "Backfill Missing" UI, `expire_on_commit=False`
  fix.

### Files changed (this session)

- `backend/app/core/migrations.py`, `backend/app/models/db.py`
- `backend/app/schemas/variant.py` (new), `backend/app/schemas/job.py`
- `backend/app/api/generation.py`, `backend/app/core/config.py`
- `backend/app/services/model_adapter.py`, `model_adapters/fish_adapter.py`,
  `model_adapters/omnivoice_adapter.py`, `model_catalog.py`, `runtime.py`,
  `voice_onboarding.py`
- `backend/tests/test_variants_api.py` (new) + 4 updated test files
- `docs/.agents/` state files (CURRENT_CONTEXT, PROJECT_STATE, HANDOFF, EXECUTION_LEDGER)

### Architectural decisions taken

- None. This session implements previously-accepted ADRs (0008, 0009, 0010, 0011).

### Risks

- **Fish Audio real inference still deferred.** Adapter is wired as HTTP client and
  unit-tested, but the S2 Pro server (codec.pth / 24GB+ VRAM) remains blocked.
- Provider validation gap (OmniVoice-only real inference) is unchanged.

### Open issues

- See [`OPEN_DECISIONS.md`](OPEN_DECISIONS.md) (Decision 1 is the gating item).
- Fish Audio inference blocked (codec/VRAM) — see provider validation index.

### Recommended next task

[`NEXT_TASK.md`](NEXT_TASK.md): after this stabilisation, the next priority is the
**provider-validation gate** — get one non-OmniVoice provider generating real audio
end-to-end through the Runtime. See [`OPEN_DECISIONS.md`](OPEN_DECISIONS.md) Decision 1.

---

## Handoff log

- 2026-06-05 — Documentation Operating System created under `docs/.agents/`; `AGENTS.md`
  updated. Application code unchanged. Next: stabilize the dirty working tree.

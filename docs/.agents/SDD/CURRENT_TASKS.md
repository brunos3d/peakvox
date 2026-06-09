# Current Tasks (SDD working set)

> Task breakdown for the active design. Template:
> [`../SPECS/TEMPLATES/TASKS.md`](../SPECS/TEMPLATES/TASKS.md). Use TDD per task.

**As of:** 2026-06-09

## Completed this session (Task 18 — browser audio validation)

- [x] Remove `KOKORO_RUNTIME_URL` env var from backend (architecture violation).
- [x] Remove `peakvox-kokoro-runtime` from docker-compose (platform boots with no runtimes).
- [x] Fix HTTPTransport.post_binary() for WAV binary responses.
- [x] Fix KokoroAdapter dispatch: `runtime_endpoint is not None` (not env var).
- [x] Fix request_id always provided to Kokoro server (UUID when job_id is None).
- [x] All 665 tests pass.
- [x] Browser validation: Models → Install Kokoro → Start → TTS → Alloy → Generate → audio plays (0:06).
- [x] Update Task 16 and Task 17 VALIDATION.md + STATUS.md → VALIDATED.
- [x] Update NEXT_TASK.md: P5 corrected, P6 ✅.

## Open

- [ ] Commit all changes with Conventional Commit messages.
- [ ] Update `IMPLEMENTATION_STATUS`, `PROJECT_STATE`, `CURRENT_CONTEXT`, `HANDOFF`, ledger.
- [ ] Fix `voice_resource_service._build_library_map`: Python `and` → SQLAlchemy `and_()` (known bug).
- [ ] Most Kokoro preset voices show "not compatible" in TTS UI (only 1 of 18 has proper variant). Root cause: ImportResolver creates variants with empty `model_id`. Fix needed.
- [ ] Task 14 browser validation pass for OmniVoice and F5-TTS runtimes.

---

**Related:** [`CURRENT_VALIDATION.md`](CURRENT_VALIDATION.md) · [`../ACTIVE_WORK.md`](../ACTIVE_WORK.md) · [`../NEXT_TASK.md`](../NEXT_TASK.md)

# STATUS — Runtime Clean Install Lifecycle (Task 14)

- Status: PARTIAL
- Last Updated: 2026-06-08

## Completed

- Backend install/remove lifecycle correctness fixes.
- Runtime descriptor image size metadata support.
- API and frontend contract updates.
- Regression test additions for key Task 14 risks.
- Clean baseline + full install/start/stop/remove evidence captured for `kokoro-82m`.
- Frontend-to-backend communication hardening in runtime API base resolution and lifecycle query re-sync.
- Browser DevTools lifecycle validation completed for `kokoro-82m` (install -> start -> stop -> remove).
- Browser DevTools lifecycle continuation completed for `omnivoice-base` (start -> stop -> remove) with container/image cleanup evidence.

## Remaining

- Resolve `f5-tts-base` install blocker (`install_failed`: missing base image manifest).
- Complete browser click lifecycle evidence for `f5-tts-base` after install readiness.

## References

- Related ADRs:
  - `docs/.agents/DECISIONS/adr-0016-models-as-runtime-services.md`
  - `docs/.agents/DECISIONS/adr-0017-runtime-services-implementation.md`
- Related architecture:
  - `docs/.agents/ARCHITECTURE/runtime-architecture.md`
- Related existing spec:
  - `docs/.agents/SPECS/FEATURES/runtime-canonical-models-page/SPEC.md`

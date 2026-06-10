# Task 23 — F5-TTS Production Validation, Frontend E2E Certification, and Runtime Registry Compliance

## Intent

Task 22 delivered the architectural integration of F5-TTS (adapter, voice-optional
capability, capability-driven compatibility, runtime-aware selectors). Task 23 certifies
that integration **operationally**: the F5-TTS runtime must reach the same maturity level
as Kokoro, exercised end-to-end from the browser exactly as a Community Edition user
would experience it.

## Scope

1. Root-cause the clean-install failure (`pytorch/pytorch:2.4.0-cuda12.1-cudnn8-runtime`
   manifest not found → superseded by the torch ABI mismatch discovered during this task).
2. Clean-install lifecycle through the UI only (no terminal builds, no cache pre-seeding):
   Available → Installing → Installed → Starting → Active.
3. Generation validation: voice-optional (Scenario A) and voice-cloning (Scenario B).
4. Compatibility matrix, model selector, and Use-in-TTS flow validation.
5. Runtime Registry metadata audit (descriptor.json vs legacy constants).
6. Cleanup lifecycle: Active → Stop → Installed → Remove → Available, with no artifacts left.

## Non-goals

- New F5-TTS features (controls, streaming, fine-tuning).
- Other providers' validation (Kokoro is the reference, not a subject).
- Cloud-edition work.

## References

- Task definition: `.vscode/agent-docs/TASK-23.md`
- Predecessor: `docs/.agents/SPECS/FEATURES/task22-f5tts-integration/`
- ADR-0017 (Runtime Service Contract), ADR-0003 (Capability Contract)
- `docs/.agents/ARCHITECTURE/10-RUNTIME_ARCHITECTURE.md`

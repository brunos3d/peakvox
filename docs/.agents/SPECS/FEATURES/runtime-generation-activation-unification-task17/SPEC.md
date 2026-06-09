# SPEC — Runtime/Generation Activation Unification (Task 17)

## Objective
Unify generation eligibility with runtime activation state so active runtimes can always generate and legacy model-status gates do not block runtime-enabled paths.

## Problem
Browser generation fails with 409 conflict (`Model 'omnivoice-base' is not active`) even when runtime lifecycle reports active.

## Scope
- Trace Text to Speech -> /generate -> runtime gate.
- Identify exact inactive condition and owner.
- Make runtime activation authoritative for generation when Runtime Services are enabled.
- Validate browser E2E generation/playback for kokoro-82m and omnivoice-base.

## Acceptance Criteria
- 409 inactive gate removed for runtime-active models.
- Generation eligibility derives from RuntimeManager + RuntimeInstance ACTIVE state when runtime descriptors exist.
- Kokoro and OmniVoice generate playable audio through browser UI.
- Runtime ↔ generation ownership contract is documented.

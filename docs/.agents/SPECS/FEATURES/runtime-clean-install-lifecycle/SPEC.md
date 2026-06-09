# SPEC — Runtime Clean Install Lifecycle (Task 14)

## Summary

Task 14 closes a validation gap: runtime lifecycle appeared functional only when images were already present locally. This produced false positives for first-time Community Edition users.

This feature requires a true clean-machine lifecycle from UI only:

1. Discover runtime
2. Install runtime
3. Start runtime
4. Generate audio
5. Stop runtime
6. Remove runtime completely

No manual docker pull/build/compose commands are allowed for end users.

## Problem Statement

Observed:

- `kokoro-82m` often worked because image existed locally.
- `omnivoice-base`/`f5-tts-base` failed on clean hosts.
- Remove operation did not reliably remove images.
- Runtime descriptors had no user-visible image size metadata.

Result:

- Runtime Registry deployment contract was not fully validated.
- Community onboarding experience was not deterministic.

## Goals

- Runtime install works from clean host state.
- Install is manager/driver owned (platform-managed pull/build behavior).
- Remove cleans container + image.
- Runtime descriptors expose image size metadata.
- UI surfaces lifecycle progress states and image size/source details.

## Non-Goals

- Introduce runtime-specific UI branches.
- Require terminal operations from the user.
- Replace composed models view architecture.

## References

- ADR-0016: Models as Runtime Services
- ADR-0017: Runtime Services Implementation
- Existing feature spec: `runtime-canonical-models-page`

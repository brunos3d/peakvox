# TASKS — Runtime Clean Install Lifecycle (Task 14)

## Task List

- [x] Add descriptor schema support for `spec.image.image_size_mb`.
- [x] Add image size metadata to runtime descriptors:
  - `kokoro-82m`
  - `omnivoice-base`
  - `f5-tts-base`
- [x] Expose `image_size_mb` via runtime API payload.
- [x] Update frontend runtime types and Runtime section rendering.
- [x] Add optimistic UI lifecycle phases for action feedback.
- [x] Update DockerRuntimeDriver install behavior to support pull-or-build fallback.
- [x] Fix remove behavior to remove image reliably.
- [x] Add regression tests for build fallback and image removal.
- [x] Add descriptor tests for image size metadata.
- [ ] Run clean-install lifecycle validation in dev environment.
- [ ] Capture browser E2E evidence and docker before/after evidence.

## Validation Checklist (Task 14)

- [ ] Before install: image absent + container absent.
- [ ] Install: image appears (pulled or built by platform).
- [ ] Start: container appears and runtime becomes active.
- [ ] Generate: audio generation succeeds.
- [ ] Stop: runtime returns to installed/stopped.
- [ ] Remove: container and image removed.

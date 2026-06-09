# DESIGN — Runtime Clean Install Lifecycle (Task 14)

## Architecture

The lifecycle path remains:

Browser UI -> Runtime API -> RuntimeManager -> DockerRuntimeDriver -> Docker Engine

Task 14 hardens two key edges:

1. Install strategy:
- Try local image first.
- If missing, pull from registry.
- If pull fails with image-not-found and descriptor has `spec.build`, perform platform-managed docker build.

2. Remove strategy:
- Stop and remove runtime container (if present).
- Remove runtime image using descriptor/container image references.
- Clear manager/driver cache state.

## Descriptor Contract Additions

`spec.image.image_size_mb` (optional positive number)

- Source of truth for estimated download and disk footprint.
- Exposed through runtime APIs and rendered in Runtime section UI.

## UI Behavior

- Optimistic lifecycle phases on action click:
  - `installing`, `starting`, `stopping`, `updating`, `removing`
- Operation row disables duplicate actions while mutation is pending.
- Runtime section displays:
  - image size
  - install source hint (`Download image` or `Download image (fallback to platform build)`)
  - build source path when descriptor includes `spec.build`

## Compatibility

- Existing phases (`notInstalled`, `pulling`, `installed`, `active`, etc.) remain valid.
- `image_size_mb` is optional and backward compatible.

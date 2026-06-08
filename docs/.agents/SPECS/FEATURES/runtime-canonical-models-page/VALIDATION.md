# VALIDATION — Runtime-Canonical Models Page

> **Companion to:** [`SPEC.md`](./SPEC.md) · [`DESIGN.md`](./DESIGN.md) ·
> [`TASKS.md`](./TASKS.md)
> **Date:** 2026-06-08

This document is filled in after implementation completes. See
TASKS §T6–T9 for the evidence required.

---

## Pre-conditions verified

- [x] T0: backend coverage confirmed
  (`/api/models/with-runtimes` returns 5 catalog models when
  no manager is attached, 3 when manager attached + T13.2 filter
  enabled, with the 3 runtime entries bound to their models)
- [x] T6: `tsc --noEmit` passes (0 errors)
- [x] T6: `eslint src/app/models src/components/models` passes
  (0 errors, 0 warnings)
- [x] T6: backend logs clean during page load
- [x] T6: `docker compose ps` shows services healthy
  (`backend`, `minio`; `kokoro-runtime` removed from compose —
  the driver owns the lifecycle now)
- [x] T6: API responses correct after T13 —
  `/api/models/with-runtimes` returns 3 cards (kokoro, omnivoice, f5-tts)
  with `default_runtime_id` set per card
- [x] T13.5: docker SDK 7.1.0 installed in backend image
- [x] T13.5: `/var/run/docker.sock` mounted in compose
- [x] T13.5: `docker.from_env()` works from inside the backend container

## Behavior verification

- [x] T7: `Kokoro 82M` right panel shows the full Runtime section
      (image `peakvox/kokoro-runtime:0.1.0`, runtime name
      `Kokoro 82M Runtime`, SERVICE block with all 5 paths,
      REQUIREMENTS block, CAPABILITIES chip `tts`)
- [x] T7: Runtime operations (Install / Start / Stop / Update /
      Remove) render in the TOP portion of the Runtime Section,
      immediately after the identity header
- [x] T7: `omniVoice-base` and `f5-tts-base` (with runtimes)
      render with the OperationsRow at the top
- [x] T7: catalog-only models (`omnivoice-singing`, `fish-audio-s2`)
      are excluded from the composed view when T13.2 filter is
      enabled (RUNTIME_SERVICE_ENABLED=true + manager attached)
- [x] T7: only one `GET /models/with-runtimes` fires on initial
      load (no legacy `GET /models` call)
- [x] T7: 0 console errors, 0 console warnings in Chrome DevTools
- [x] T13.7: browser-driven Install/Start/Stop/Remove transitions
      all confirmed via Chrome DevTools network panel + docker ps
- [x] T13.8: 266,444 bytes of valid WAV generated from runtime
      `/v1/generate` after the browser-driven install+start

## Screenshots

- [x] `audits/screenshots/omnivoice-base-not-migrated.png`
- [x] `audits/screenshots/kokoro-runtime-section.png`
- [x] `audits/screenshots/fish-s2-pro-not-migrated.png`
- [x] `audits/screenshots/omnivoice-base-runtime-section.png`
- [x] `audits/screenshots/f5-tts-runtime-section.png`
- [x] `audits/screenshots/t13-kokoro-active.png` (T13 active state)
- [x] `audits/screenshots/t13-kokoro-notinstalled-check.png` (T13 NotInstalled)
- [x] `audits/screenshots/t13-kokoro-runtime-generated-audio.wav`
  (5.55s of valid audio from runtime)
- [x] `audits/screenshots/kokoro-runtime-generated-audio.wav` (T12)

## Behavior changes (acknowledged)

- The legacy Activate / Deactivate buttons are removed. The
  runtime's `Active` phase is the new "activated" state. This is
  the intended architectural change; documented here so the change
  is traceable.
- The `useModels()` (legacy catalog) call is removed from the
  Models page. The page now depends solely on
  `useModelsWithRuntimes()`. The terminal check (T0) confirmed
  the backend returns the catalog model in the composed view
  even when `runtimes[]` is empty.
- The composed view's `runtimes[]` field is filtered when
  RUNTIME_SERVICE_ENABLED=true and a manager is attached:
  catalog-only models without a runtime descriptor are excluded.
  This is the T13.2 "Runtime Registry Authority" semantic.
- The runtime lifecycle endpoints (`/runtimes/<id>/{install,start,
  stop,update,remove,state}`) are now reachable without the
  `/api` prefix per the project convention. The backend exposes
  both the `/api/runtimes/...` and `/runtimes/...` aliases.
- The phase enum is now lowercase throughout the stack
  (`"notInstalled"`, `"active"`, `"stopped"`, …) to match the
  `RuntimeState` enum values. Frontend types and maps
  were updated to lowercase.

## Audit report

See
[`audits/models-page-canonical-control-surface.md`](./audits/models-page-canonical-control-surface.md)
for the full narrative audit with before/after screenshots.

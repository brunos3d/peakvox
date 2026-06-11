# Implementation Plan — Runtime Variants Migration

> **ADR:** [ADR-0018 Runtime Variants Architecture](../../DECISIONS/adr-0018-runtime-variants-architecture.md)
> **Spec:** [`../../SPECS/FEATURES/runtime-variants/`](../../SPECS/FEATURES/runtime-variants/)
> **Audit:** [`../../VALIDATION/AUDITS/runtime-variants-assumptions-audit.md`](../../VALIDATION/AUDITS/runtime-variants-assumptions-audit.md)
> **Date:** 2026-06-11
> **Status:** Phase 0 (primitive) shipped with ADR-0018; Phases 1–6 PLANNED.

The goal of this plan is **not** to implement everything now. It is to define
a **safe, additive, reversible** path from runtime-per-variant to
runtime + RuntimeVariants. Every phase is independently shippable, leaves the
system working, and can be reverted by deleting additive code/files. No phase
removes a public API field, drops a table, or breaks an existing runtime
directory.

## Guiding constraints (carried from ADR-0018 + the audit)

1. **Additive only.** Existing `f5-tts-base/`, `kokoro-82m/`, `omnivoice-base/`
   directories keep working as single-`base` runtimes throughout.
2. **No VoiceVariant collision.** `variant_id` (`/v1/generate`) and
   `/v1/variants/build` remain VoiceVariant. RuntimeVariant uses
   `runtime_variant` and `/v1/variants/load`. Keep types/fields disjoint.
3. **Public API stable.** Generation stays `voice + model + text`. The
   `model_id` remains the public selector; variant selection happens inside
   resolution.
4. **Manager stays domain-free.** No Voice/VoiceVariant references leak into
   the runtime subsystem (Runtime Activation Audit).
5. **Capabilities declared, not inferred** (ADR-0003) — including checkpoint
   compatibility on HF import.

---

## Phase 0 — Descriptor primitive (SHIPPED with ADR-0018)

**Scope (done):** an additive, **non-wired** `RuntimeVariantDescriptor`
Pydantic schema + optional `variants/*.json` loader support, with unit tests.
Nothing reads it yet (no resolution/lifecycle change).

- `RuntimeVariantDescriptor` (`kind: RuntimeVariant`): `id`, `name`,
  `runtime_id`, `model_binding`, `checkpoint`, `is_default`, optional
  `capabilities`, optional edition/licensing (inert in CE).
- `RuntimeRegistryLoader` optionally loads `<root>/<id>/variants/*.json`;
  bad files skipped-and-logged like bad descriptors.
- Registry gains a variant index + `list_variants_for_runtime(runtime_id)`.

**Exit criteria:** tests green; existing descriptor tests unchanged; loading a
registry with no `variants/` folders behaves identically to before.

**Rollback:** delete the new schema/index/tests; zero blast radius.

---

## Phase 1 — Introduce the RuntimeVariant domain (descriptor + resolution wiring)

**Goal:** make the system *aware* of variants end-to-end in resolution,
without changing on-disk runtime layout or the public API.

**Backend**
- Wire `RuntimeVariantDescriptor` into `RuntimeManager.resolve`:
  - resolve `model_id → descriptor` (unchanged), then map the chosen model to
    its RuntimeVariant (the variant whose `model_binding.model_id` matches, or
    the runtime's default variant).
  - add optional `runtime_variant_id` to `RuntimeResolution` (additive field).
- Backfill **implicit base variants**: a runtime with no `variants/` is
  treated as having one synthetic `base` variant bound to its
  `model_binding.model_id`. No file changes required.
- The adapter passes `runtime_variant` to `/v1/generate` when present;
  omitting it is valid (service falls back to default).

**Tests:** resolution picks the right variant for variant-family models;
implicit-base behavior identical to today; no Voice references introduced.

**Exit criteria:** with zero registry changes, generation behaves exactly as
today; with a hand-authored `variants/` folder, resolution selects the variant
internally. Public API byte-identical.

**Risk:** Low. All changes are additive fields + a synthetic default.

---

## Phase 2 — Registry structure evolution (consolidate directories)

**Goal:** move from `f5-tts-base/` to `f5-tts/ + variants/base.json` — the
target storage model — **without** breaking installs in flight.

**Steps**
1. Create `runtime-registry/f5-tts/` with the shared `Dockerfile`/`server.py`/
   `descriptor.json` (provider-level id `f5-tts`) and
   `variants/base.json` (the current base checkpoint).
2. Keep `runtime-registry/f5-tts-base/` as a **thin alias** for one release
   (its descriptor `metadata.id` stays `f5-tts-base`; the registry dedupes by
   image digest so no double build). Mark it deprecated in its README.
3. Switch the weights source from "baked/boot-download into image" to the
   shared cache `/data/runtime-weights/f5-tts/base/` (driver already mounts
   `/data`; see audit §4.2).
4. Repeat for `omnivoice/` (+ `variants/base.json`, `singing.json`) and
   `kokoro/`.
5. Next release: delete the `*-base/` aliases.

**Tests/validation:** install from the consolidated dir produces a working
runtime; image is built/pulled once; adding `singing.json` adds no image.

**Exit criteria:** consolidated directories are authoritative; image count per
family = 1; checkpoints live in the shared cache.

**Risk:** Medium (touches install paths + image identity). Mitigated by the
one-release alias window and digest dedupe. **Reversible** by restoring the
`*-base/` dirs (kept in git history).

---

## Phase 3 — UI support (group by runtime family + variant chips)

**Goal:** present `F5-TTS` once, with an installed-runtime state and variant
chips — a **presentation** change, no API dimension change.

**Backend (additive)**
- `GET /models/with-runtimes`: add an optional `variants` array per runtime
  (id, name, default, installed/loaded state) and a `family`/`runtime_family`
  grouping key. Existing fields untouched.
- Add `POST /{runtime_id}/variants/{variant_id}/add` and `/remove`
  (download/delete checkpoint; never an image build) → new
  `RuntimeOperationType` values `variant_add`/`variant_remove`.

**Frontend**
- Group model cards by runtime family; render runtime install/start/stop at
  the family level and variant chips with their own Add/Remove.
- Capability-driven controls read the **selected variant-model's**
  `ModelCapabilities` (ADR-0003; `frontend/AGENTS.md` rule 3). Never surface
  checkpoint paths/formats (ADR-0004 §6; rule 2).
- Label RuntimeVariant chips distinctly from VoiceVariants (audit §8.2).

**Exit criteria:** Models page shows one F5-TTS card with Base/PT-BR/Narrator
chips; generation still sends `model_id`; no model internals leak.

**Risk:** Low–Medium (UI + additive API).

---

## Phase 4 — Runtime Service support (load/switch variants without restart)

**Goal:** the service hosts multiple checkpoints and switches between them with
no container recreation / reinstall / rebuild.

**Per `server.py`**
- Replace the single `_load_state` singleton with a keyed, **LRU-bounded**
  `_variants` registry + `_default_variant_id` (eager-loaded on `/ready`).
- New endpoints: `GET /v1/variants`, `POST /v1/variants/load` (`{variant_id}`).
- `GenerateRequest`: add optional `runtime_variant` **alongside** the existing
  `variant_id` (VoiceVariant). `/v1/metadata`: add `variants` + `loaded_variant`.
- **F5-TTS guard (audit §5.5):** variant switching respects the module-level
  inference lock and clears the DiT text-embed cache on variant change; the LRU
  never holds two variants live during a single inference. Add a regression
  test mirroring Task 24's concurrency tests.

**Exit criteria:** load a second variant on a running container; generate with
each; no restart; F5 concurrency/cache regression tests still green.

**Risk:** Medium (per-runtime, isolated). Each runtime ports independently;
Kokoro first (cheapest), then OmniVoice, then F5 (strictest constraints).

---

## Phase 5 — Marketplace support (publish/consume variants)

**Goal:** variants become publishable registry artifacts (checkpoint +
descriptor), Cloud-scoped, mirroring the voice marketplace.

- Variant descriptors gain edition/licensing scoping (extends ADR-0005 to
  variant granularity); CE leaves these empty (Constitution V §15).
- Checkpoint versioning/retention specified in a **future ADR** (the Cloud
  `RuntimeArtifact` reserved by ADR-0018) — distinct from `VoiceVariantArtifact`.
- Publish flow: package checkpoint + descriptor; consume flow: same as HF
  import (Phase 6) but from the PeakVox registry.

**Exit criteria:** a Cloud-only/licensed variant is installable in Cloud,
hidden in CE; CE tables remain empty.

**Risk:** Cloud-only; gated behind feature flags; no CE behavior change.

---

## Phase 6 — Hugging Face variant imports

**Goal:** `firstpixel/F5-TTS-pt-br`-style imports as a checkpoint download +
descriptor registration, **no Docker build**.

**Flow (ADR-0018 §HF import):**
```
Add Variant → paste HF URL → validate (provider/arch/caps compatibility with the runtime)
            → download to /data/runtime-weights/<rt>/<variant>/
            → write variants/<id>.json (+ optional catalog Model row)
            → available for generation
```

- **Validation gates:** reject if the checkpoint's declared architecture/
  provider mismatches the runtime's `provider`/`model_family` labels, or if its
  declared capabilities exceed the runtime's. Compatibility is **declared and
  checked**, never inferred from the repo name (ADR-0003 applied to checkpoints).
- New endpoint: `POST /{runtime_id}/variants/import` `{source: "hf", url}`.
- Surfaces the existing `variant_add` operation type for progress.

**Exit criteria:** the firstpixel PT-BR checkpoint imports onto the shared
F5-TTS runtime and generates, with no new image.

**Risk:** Medium (download + validation surface); fully additive; Cloud may
restrict sources by policy.

---

## Sequencing & dependencies

```
Phase 0 (done) ─▶ Phase 1 ─▶ Phase 2 ─▶ Phase 3
                                  └─────▶ Phase 4 ──▶ Phase 6
                                              └─────▶ Phase 5 (Cloud)
```

- Phases 1–3 deliver the architecture + UX with **no** image duplication for
  pre-authored variants and are the highest-value CE slice.
- Phase 4 unlocks restart-free switching (Kokoro → OmniVoice → F5).
- Phase 6 (HF import) depends on Phase 4 (runtime can load a freshly downloaded
  checkpoint) and Phase 2 (consolidated runtime + weights cache).
- Phase 5 is Cloud-only and independent of Phase 6.

## Definition of done (whole migration)

- F5-TTS PT-BR / Narrator, OmniVoice Singing installable as **variants** of a
  shared runtime image — no per-variant Docker image.
- `GET /models/with-runtimes` groups by runtime family with variant chips.
- A running runtime loads/switches variants without restart.
- HF checkpoint import works with no image build.
- Public `/api/v1` contract and `public_voice_id` unchanged throughout
  (Constitution VIII §26); VoiceVariant untouched.
- Each phase has its own validation note under
  [`../../VALIDATION/`](../../VALIDATION/).

---

**Related:** [ADR-0018](../../DECISIONS/adr-0018-runtime-variants-architecture.md) ·
[ADR-0016](../../DECISIONS/adr-0016-models-as-runtime-services.md) ·
[ADR-0017](../../DECISIONS/adr-0017-runtime-services-implementation.md) ·
[Discovery audit](../../VALIDATION/AUDITS/runtime-variants-assumptions-audit.md) ·
[Feature spec](../../SPECS/FEATURES/runtime-variants/)

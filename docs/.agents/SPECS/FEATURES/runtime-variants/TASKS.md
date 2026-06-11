# TASKS — Runtime Variants

> **Spec:** [SPEC.md](./SPEC.md) · **Design:** [DESIGN.md](./DESIGN.md) ·
> **Migration plan (authoritative phasing):**
> [`../../../IMPLEMENTATION/PLANS/2026-06-11-runtime-variants-migration.md`](../../../IMPLEMENTATION/PLANS/2026-06-11-runtime-variants-migration.md)

This file tracks the executable task breakdown. The migration plan owns the
phase rationale; this is the checklist.

## Phase 0 — Descriptor primitive (SHIPPED with ADR-0018)

- [x] **P0.1** Add `RuntimeCheckpoint` + `RuntimeVariantDescriptor` to
  `runtime_types.py` (closed schema, reuses `RuntimeModelBinding`,
  capability-vocabulary validation).
- [x] **P0.2** Extend `RuntimeRegistry` with a variant index +
  `list_variants_for_runtime` / `get_variant`.
- [x] **P0.3** Extend `RuntimeRegistryLoader` to optionally load
  `<root>/<id>/variants/*.json` (skip-and-log on error).
- [x] **P0.4** Unit tests: schema validation (good/bad), loader with & without
  `variants/`, skip-and-log, existing-descriptor parity.
- [x] **P0.5** Non-wiring guarantee: no resolution/lifecycle path reads the
  variant index; existing tests unchanged.

## Phase 1 — RuntimeVariant domain wiring (PLANNED)

- [ ] **P1.1** `choose_variant(descriptor, model_id)` + synthetic `base`.
- [ ] **P1.2** Optional `runtime_variant_id` on `RuntimeResolution`.
- [ ] **P1.3** Adapter forwards `runtime_variant` to `/v1/generate` when present.
- [ ] **P1.4** Tests: variant-family resolution; implicit-base parity; no Voice refs.

## Phase 2 — Registry structure evolution (PLANNED)

- [ ] **P2.1** `runtime-registry/f5-tts/` + `variants/base.json`; alias old dir.
- [ ] **P2.2** Move weights to `/data/runtime-weights/...`; digest-dedupe builds.
- [ ] **P2.3** Repeat for `omnivoice/` (+ `singing.json`), `kokoro/`.
- [ ] **P2.4** Next release: delete `*-base/` aliases.

## Phase 3 — UI support (PLANNED)

- [ ] **P3.1** `with-runtimes`: optional `variants` array + `family` key.
- [ ] **P3.2** `variant_add`/`variant_remove` operations (no image build).
- [ ] **P3.3** FE: group by family; runtime controls at family level; variant chips.
- [ ] **P3.4** Capability-driven controls from the selected variant-model; no internals leak.

## Phase 4 — Runtime service support (PLANNED)

- [ ] **P4.1** Keyed LRU `_variants` registry + `_default_variant_id`.
- [ ] **P4.2** `GET /v1/variants`, `POST /v1/variants/load`; `runtime_variant` on generate.
- [ ] **P4.3** F5 lock/cache guard + concurrency regression test.
- [ ] **P4.4** Port order: Kokoro → OmniVoice → F5.

## Phase 5 — Marketplace (PLANNED, Cloud)

- [ ] **P5.1** Edition/licensing scoping on variant descriptors (inert in CE).
- [ ] **P5.2** Publish/consume flow; future ADR for Cloud `RuntimeArtifact` versioning.

## Phase 6 — Hugging Face imports (PLANNED)

- [ ] **P6.1** `POST /{runtime_id}/variants/import {source:"hf", url}`.
- [ ] **P6.2** Compatibility validation (provider/arch/caps, declared not inferred).
- [ ] **P6.3** Download → register descriptor → optional catalog Model row.
- [ ] **P6.4** E2E: `firstpixel/F5-TTS-pt-br` onto shared F5 runtime, no image build.

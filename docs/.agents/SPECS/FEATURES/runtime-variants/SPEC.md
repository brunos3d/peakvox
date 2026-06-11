# SPEC — Runtime Variants

> **Status:** ACCEPTED (architecture only)
> **Date:** 2026-06-11
> **ADR:** [`adr-0018-runtime-variants-architecture.md`](../../../DECISIONS/adr-0018-runtime-variants-architecture.md)
> **Parents:** [`adr-0016`](../../../DECISIONS/adr-0016-models-as-runtime-services.md) ·
> [`adr-0017`](../../../DECISIONS/adr-0017-runtime-services-implementation.md)
> **Method:** Architecture + one additive, non-wired descriptor primitive
> (Phase 0). No registry restructure, no public API change, no runtime-service
> change in this spec.

---

## Problem

The Runtime Registry collapses *runtime* (image + Python/CUDA env + service
contract) and *checkpoint* (weights/config/tokenizer) into one indivisible
unit. Supporting a model variation (F5-TTS PT-BR, OmniVoice Singing, an XTTS
fine-tune, a community/marketplace variant) therefore requires a whole new
runtime directory + Dockerfile + image + build, duplicating multi-GB images to
change a few-hundred-MB checkpoint. This blocks: CE "Add Variant without
Docker," Hugging Face checkpoint imports, and a variant marketplace.

## Goal

Evolve the registry from **runtime-per-variant** to **runtime +
RuntimeVariants**, where one runtime image hosts many interchangeable
checkpoints, **without**:

- changing the public `/api/v1` contract (generation stays `voice + model + text`),
- touching the Voice domain or `VoiceVariant`,
- violating ADR-0016's "runtime infrastructure is not a domain concept."

## Definitions

- **RuntimeVariant** — an **infrastructure descriptor concept**: a
  sub-descriptor of a `Runtime` binding a checkpoint to that runtime. Never a
  domain entity, never persisted as a domain row, never on the public API.
- **NOT VoiceVariant** — VoiceVariant is `Voice × Model` (domain, persisted,
  ADR-0001/0004/0008/0009). RuntimeVariant is `Runtime × Checkpoint`
  (infrastructure). They share no table, type, repository, or API field.

## Requirements

| # | Requirement | Source |
|---|---|---|
| R1 | A RuntimeVariant is an infrastructure descriptor (`kind: RuntimeVariant`), stored under `runtime-registry/<runtime>/variants/<id>.json`. | ADR-0018 Decision 1 |
| R2 | A Runtime owns image/env/contract; a RuntimeVariant owns checkpoint/config/tokenizer/metadata. | ADR-0018 Decision 2 |
| R3 | Checkpoints download to a shared weights cache (`/data/runtime-weights/<rt>/<variant>/`), not baked into images. | ADR-0018 Decision 3 |
| R4 | The catalog Model stays the public selector; `resolve(model_id)` selects runtime **and** variant. | ADR-0018 Decision 4 |
| R5 | The Runtime Service Contract gains `/v1/variants`, `/v1/variants/load`, `runtime_variant` on `/v1/generate`, variants in `/v1/metadata`. Restart-free switching. | ADR-0018 Decision 5 |
| R6 | `variant_id` (VoiceVariant) and `/v1/variants/build` (VoiceVariant build) are untouched and must not be overloaded. | Audit §5.2/§5.3 |
| R7 | A runtime with no `variants/` folder is a valid single-`base` runtime. | ADR-0018 storage model |
| R8 | HF import = checkpoint download + descriptor registration; **no Docker build**; compatibility declared and checked. | ADR-0018 §HF import |
| R9 | ADR-0016's `RuntimeVariant` forbidden-pattern entry is narrowed (infrastructure descriptor permitted; domain entity/repository still forbidden). | ADR-0018 §Amendment |

## Non-goals (this spec)

- Restructuring `runtime-registry/` directories (migration Phase 2).
- Any public API change or a first-class public `runtime_variant` selector
  (would need `/api/v2`).
- Cloud checkpoint versioning/`RuntimeArtifact` (future ADR).
- Wiring variants into resolution/lifecycle (migration Phases 1+).

## Acceptance criteria

1. ADR-0018 accepted; RuntimeVariant formally defined and distinguished from
   VoiceVariant.
2. Storage, CE, Cloud, HF, UX, and migration implications documented.
3. Repository assumptions audited with `file:line` evidence.
4. Phase 0 primitive (`RuntimeVariantDescriptor` + optional loader) shipped,
   additive, tested, non-wired — existing behavior byte-identical.

See [DESIGN.md](./DESIGN.md), [TASKS.md](./TASKS.md),
[VALIDATION.md](./VALIDATION.md), [STATUS.md](./STATUS.md).

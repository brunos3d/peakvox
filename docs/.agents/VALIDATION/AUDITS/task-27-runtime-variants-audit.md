# Task 27 — Phase A Audit: Task 26 RuntimeVariant Implementation

> **Date:** 2026-06-11 · **Auditor:** Task 27 · **Subject:** ADR-0018 / Task 26
> **Verdict:** Task 26 delivered **exactly Phase 0** of the migration plan — a
> correct, additive, well-tested descriptor primitive — and **nothing more**.
> The "partially implemented" concern is accurate and *by design*: Phases 1–6
> were always PLANNED, not built. No misrepresentation was found.

## Method

Read the artifacts and the code, not the claims:

- ADR-0018 (`DECISIONS/adr-0018-runtime-variants-architecture.md`)
- Migration plan (`IMPLEMENTATION/PLANS/2026-06-11-runtime-variants-migration.md`)
- STATUS / SPEC / DESIGN / VALIDATION under `SPECS/FEATURES/runtime-variants/`
- Code: `backend/app/services/runtime_types.py`, `runtime_registry.py`,
  `runtime_manager.py`, `api/runtime_api.py`
- Tests: `backend/tests/test_runtime_variant_descriptor.py`
- Registry: `runtime-registry/{omnivoice-base,f5-tts-base,kokoro-82m}/`
- Frontend: `components/models/RuntimeSection.tsx`, `types/index.ts`

## Findings (answers to the nine audit questions)

| # | Question | Finding |
|---|---|---|
| 1 | What was actually implemented? | `RuntimeVariantDescriptor` + sub-models (`RuntimeCheckpoint`, `RuntimeVariantMetadata`, `RuntimeVariantSpec`), an additive variant index on `RuntimeRegistry` (`list_variants_for_runtime`, `get_variant`), loader support for `<runtime>/variants/*.json`, and 16 unit tests. All green. |
| 2 | What remains conceptual only? | Everything past the schema: resolution wiring, registry consolidation, UI, runtime-service multi-checkpoint loading, marketplace, HF import. These are migration Phases 1–6, all PLANNED. |
| 3 | Is RuntimeVariant fully represented in code? | **As a descriptor, yes.** As a *resolved, lifecycled concept, no.* The schema is complete and disjoint from the domain `VoiceVariant`. But no runtime directory ships a `variants/` folder, so the index is empty at runtime, and nothing reads it. |
| 4 | Did the registry structure evolve? | **No.** Still `omnivoice-base/`, `f5-tts-base/`, `kokoro-82m/` — one directory and one image per (runtime, checkpoint). The `*-base` naming still conflates Runtime with its base RuntimeVariant. This is the central gap. |
| 5 | Do descriptors support variants correctly? | **Yes, schema-wise.** The loader correctly reads `variants/*.json`, validates each against the closed schema, skips-and-logs bad files, and rejects a variant whose `runtime_id` ≠ its directory. There are simply no variant files on disk. |
| 6 | Does RuntimeManager understand variants? | **No.** `resolve()` (runtime_manager.py:213) maps `model_id → descriptor → ACTIVE instance`. It never consults the variant index. `RuntimeResolution` has no variant field. |
| 7 | Does RuntimeDriver understand variants? | **No, and correctly so.** The driver is image-agnostic (ADR-0017); it has no reason to. Variant *checkpoint* provisioning (download to the shared cache) is the missing piece, not a driver change. |
| 8 | Does the frontend understand variants? | **No.** `with-runtimes` returns no `variants`; `ComposedRuntimeEntry` has no `variants` field; `RuntimeSection.tsx` renders a single runtime with no variant concept. |
| 9 | Are future HF imports realistically possible? | **Yes** — the schema already models `RuntimeCheckpoint{source_type: hf, source_ref}`. The missing parts are a validate→download→register service and a runtime service that can load a freshly-downloaded checkpoint. Both are additive. |

## Assessment

**No false claims.** STATUS.md honestly reports `PARTIAL` with Phase 0
IMPLEMENTED+VALIDATED and Phases 1–6 PLANNED. The ADR and migration plan are
unusually rigorous and explicitly stage the work. The concern that "Runtime and
RuntimeVariant may still be treated as the same concept" is true *only* at the
**registry-directory + naming** layer (`*-base/`) and in **resolution/UI**,
which Phase 0 deliberately did not touch.

**One real schema gap for the ecosystem goal:** the variant descriptor models
*compatibility* (checkpoint + model binding + capabilities) but not *trust
provenance*. There is no way to mark a variant Verified vs Community
(Task 27 Phase H). That is the one schema addition this task makes.

## Task 27 → migration-phase mapping

| Task 27 phase | Migration phase | This task's action |
|---|---|---|
| A (audit) | — | This document. |
| B (registry structure) | Phase 2 | Add `variants/base.json` to each runtime (additive); document the consolidation path. Keep `*-base/` dirs (no breaking rename this task). |
| C (frontend workflow) | Phases 1+3 | Wire resolution (implicit base), add `variants` to API + types, render variant chips with trust badges. |
| D (community imports) | Phase 6 | Add a **validate-only** HF import resolver + endpoint (no download yet). |
| E (generic import path) | — | Findings doc: what is auto-discoverable vs declared. |
| F (shared images) | Phase 2/4 | Findings doc: feasibility of base/family images + variant-only downloads. |
| G (capability discovery) | — | Findings doc + the import validator enforces *declared* caps (ADR-0003). |
| H (verified vs community) | — | Add `trust` to the variant schema + UI badge. |
| I (UX review) | Phase 3 | DESIGN.md ecosystem section. |

## Conclusion

Build *on* Phase 0; do not redo it. The safe, high-value, additive slice for
this session is: **trust field → implicit-base resolution wiring → concrete
`variants/base.json` files → composed-view `variants` array → frontend variant
chips with Verified/Community badges → validate-only HF import foundation**,
each unit-tested, plus feasibility findings for the investigation-only phases.

# VALIDATION — Runtime Variants

> **Spec:** [SPEC.md](./SPEC.md) · **ADR:** [ADR-0018](../../../DECISIONS/adr-0018-runtime-variants-architecture.md)
> Validation is part of implementation (Constitution Article VII §24). This
> records what was actually verified for the Phase 0 primitive — code, not
> intent.

## Scope of this validation

Architecture (ADR-0018) + **Phase 0** code only: the additive, non-wired
`RuntimeVariantDescriptor` schema and the optional `variants/*.json` loader.
Phases 1–6 are PLANNED and validated in their own future reports.

## Architecture acceptance (ADR-0018 success criteria)

| Criterion (Task 26) | Status | Evidence |
|---|---|---|
| ADR created | ✅ | `adr-0018-runtime-variants-architecture.md` |
| RuntimeVariant formally defined | ✅ | ADR §"The three infrastructure axes", §Decision |
| RuntimeVariant ≠ VoiceVariant | ✅ | ADR §"The two 'variants' are different domains"; audit §5.2/§5.3/§8.2 |
| Storage model documented | ✅ | ADR §"Storage model" (registry + weights cache + savings table) |
| Community Edition flow documented | ✅ | ADR §"Community Edition implications" |
| Cloud implications documented | ✅ | ADR §"Cloud implications" |
| HuggingFace import flow documented | ✅ | ADR §"Hugging Face variant import flow" |
| Migration strategy documented | ✅ | Plan `2026-06-11-runtime-variants-migration.md` (Phases 0–6) |
| Repository assumptions audited | ✅ | `VALIDATION/AUDITS/runtime-variants-assumptions-audit.md` (file:line) |
| Implementation roadmap created | ✅ | Plan + TASKS.md |
| Future F5-TTS PT-BR-style variants supported | ✅ | ADR worked example; HF flow; Phase 0 schema models the binding |

## Constitution / ADR-0016 compliance

- **Public API unchanged** — generation stays `voice + model + text`; no
  `/api/v1` field added or removed. (Article I §2, III, VIII §26.)
- **Voice domain untouched** — no Voice/VoiceVariant/Artifact reference in the
  new code; `RuntimeVariantDescriptor` is infrastructure-only.
- **ADR-0016 amended, not violated** — the `RuntimeVariant` forbidden-pattern
  entry is narrowed to permit the *infrastructure descriptor* form; the domain
  entity/repository prohibition stands. Invariants 1–12 preserved.
- **Capabilities declared, not inferred** — variant capabilities validate
  against the closed runtime vocabulary (ADR-0003).

## Phase 0 code validation (test evidence)

Command (from `backend/`):

```
python -m pytest tests/test_runtime_variant_descriptor.py \
  tests/test_runtime_registry.py tests/test_runtime_descriptor.py \
  tests/test_runtime_descriptor_kokoro.py \
  tests/test_runtime_registry_three_descriptors.py \
  tests/test_runtime_registry_kokoro_descriptor.py \
  tests/test_runtime_registry_authority_t13.py \
  tests/test_settings_runtime_registry_path.py -q
→ 98 passed
```

New tests (`tests/test_runtime_variant_descriptor.py`, 13 cases):

- schema: validates good payload; rejects wrong `kind`, missing `runtime_id`,
  unknown capability, bad checkpoint digest, unknown edition.
- registry index: indexes variants by runtime; rejects duplicate variant id;
  empty list when no variants.
- loader: reads `variants/*.json`; runtime **without** `variants/` is
  unchanged; skips bad variant (malformed JSON + wrong kind) while keeping the
  runtime and good variants; skips variant whose `runtime_id` mismatches its
  directory.

**Additivity proven:** the existing 84 runtime registry/descriptor tests pass
unchanged alongside the 14 new ones (98 total). A registry built without
variants behaves identically to before.

## Known pre-existing failure (out of scope, flagged)

The full `-k runtime` sweep shows **330 passed, 1 failed, 1 skipped**. The one
failure — `test_docker_runtime_driver.py::test_docker_driver_does_not_communicate_with_runtimeservices_directly`
— is **pre-existing and unrelated to this work**:

- It is a brittle *source-substring* lint asserting the driver does not import
  `requests`/`httpx`/`aiohttp`. It matches the substring `requests` inside
  Docker's GPU API call `device_requests` (`docker_runtime_driver.py:565,614`),
  introduced by commit `21d2349` ("restore OmniVoice GPU acceleration").
- Task 26 modified only `runtime_types.py` and `runtime_registry.py` (verified
  via `git diff --name-only`); the driver is untouched.
- **Recommendation (separate fix):** tighten the test to match an actual import
  statement (e.g. `^import requests`/`^from requests`) rather than a bare
  substring, so legitimate uses of Docker's `device_requests` GPU parameter do
  not trip it.

## Verdict

Phase 0 is **VALIDATED**: additive, backward-compatible, tested, non-wired.
The architecture (ADR-0018) meets every Task 26 success criterion.

---

## Task 27 increment (2026-06-11) — Phases 1, 3 (partial), trust, import

> **Audit:** [`../../../VALIDATION/AUDITS/task-27-runtime-variants-audit.md`](../../../VALIDATION/AUDITS/task-27-runtime-variants-audit.md)
> **Findings (E/F/G):** [`../../../VALIDATION/RESEARCH/task-27-model-ecosystem-findings.md`](../../../VALIDATION/RESEARCH/task-27-model-ecosystem-findings.md)
> **ADR:** [ADR-0019 Variant Trust Tiers & Community Imports](../../../DECISIONS/adr-0019-variant-trust-and-community-imports.md)

The pre-existing `device_runtime_driver` substring-lint failure flagged above
was **fixed** this session (match real import statements, not the
`device_requests` substring) — see commit `fix(runtime): persist HF cache and
enforce GPU/CPU execution contract`.

What Task 27 added on top of Phase 0 (all additive, all unit-tested):

| Item | Migration phase | Evidence |
|---|---|---|
| `select_variant()` resolver (model-bound → default → implicit base) | 1 | `runtime_registry.py`; `tests/test_runtime_variant_resolution.py` |
| `RuntimeResolution.runtime_variant_id` (additive, `None` = implicit base) | 1 | `runtime_manager.py` |
| `trust` (verified\|community) + `source_url` on variant metadata | H | `runtime_types.py`; resolution tests |
| Concrete `variants/base.json` for all 3 runtimes | 2 (repr.) | `runtime-registry/*/variants/base.json` |
| Public-safe `variants[]` in `/models/with-runtimes` (no checkpoint internals) | 3 | `runtime_api.py`; `tests/test_api_models_with_runtimes.py` |
| Validate-only HF import + `POST …/variants/validate-import` | 6 (validate) | `runtime_variant_import.py`; `tests/test_runtime_variant_import.py` |
| Frontend Variants section + trust badges + import dialog | 3 | `components/models/VariantsSection.tsx` |

**Test evidence:** `732 passed, 1 skipped` (full backend suite, +29 new); frontend
`tsc --noEmit` and `eslint` clean.

**Invariants preserved:** public `/api/v1` byte-identical; generation stays
`voice + model + text`; no Voice/VoiceVariant reference in runtime code; variant
capabilities ⊆ runtime capabilities (ADR-0003); no checkpoint internals on the
public surface (ADR-0004 §6); implicit-base runtimes resolve byte-identically.

**Still PLANNED:** download+register (Phase 6 tail), runtime-service multi-checkpoint
load/switch (Phase 4), registry directory consolidation + shared base image
(Phase 2 image work), marketplace (Phase 5). Phases 4/6-tail require a no-GPU
session's out-of-scope Docker rebuilds; the path is recorded in the findings doc.

# STATUS — Runtime Variants

Lifecycle position in the SDD flow:
`Brainstorm → Specification → Design → Tasks → Implementation → Validation → Review → Merge`

- **Feature status:** `PARTIAL` — architecture ACCEPTED; Phase 0 + Phase 1 +
  Phase 3 (presentation) IMPLEMENTED + VALIDATED; Phase 6 *validate* shipped;
  Phases 2 (image work), 4, 5, 6-tail PLANNED.
- **ADR:** [ADR-0018](../../../DECISIONS/adr-0018-runtime-variants-architecture.md)
  — Accepted (architecture only), 2026-06-11. Amends ADR-0016's `RuntimeVariant`
  forbidden-pattern entry. Extended by
  [ADR-0019](../../../DECISIONS/adr-0019-variant-trust-and-community-imports.md)
  (trust tiers + community imports), 2026-06-11.
- **Owner / last update:** Task 27, 2026-06-11 (built on Task 26).

| Allowed status | This feature |
|---|---|
| NOT_STARTED / PLANNED / APPROVED / IN_PROGRESS / **PARTIAL** / IMPLEMENTED / VALIDATED / SUPERSEDED / ARCHIVED | **PARTIAL** |

## Phase status

| Phase | Scope | Status |
|---|---|---|
| 0 | Descriptor primitive (`RuntimeVariantDescriptor` + loader + tests, non-wired) | **IMPLEMENTED + VALIDATED** |
| 1 | RuntimeVariant resolution wiring (`select_variant`, `runtime_variant_id`, implicit base) | **IMPLEMENTED + VALIDATED** (Task 27) |
| 2 | Registry structure evolution (`<runtime>/variants/`) | **PARTIAL** — `variants/base.json` shipped per runtime; directory consolidation + shared base image PLANNED |
| 3 | UI support (variant chips + trust badges + import dialog) | **IMPLEMENTED + VALIDATED** (Task 27); family grouping PLANNED |
| 4 | Runtime service (load/switch without restart) | PLANNED |
| 5 | Marketplace (Cloud) | PLANNED |
| 6 | Hugging Face imports | **PARTIAL** — validate-only shipped; download+register PLANNED |
| H | Verified vs Community trust tiers (`trust` field + badge + import gate) | **IMPLEMENTED + VALIDATED** (Task 27; [ADR-0019](../../../DECISIONS/adr-0019-variant-trust-and-community-imports.md)) |

## Evidence

- ADR: `docs/.agents/DECISIONS/adr-0018-runtime-variants-architecture.md`
- Audit: `docs/.agents/VALIDATION/AUDITS/runtime-variants-assumptions-audit.md`
- Plan: `docs/.agents/IMPLEMENTATION/PLANS/2026-06-11-runtime-variants-migration.md`
- Code (Phase 0): `backend/app/services/runtime_types.py`,
  `backend/app/services/runtime_registry.py`
- Tests (Phase 0): `backend/tests/test_runtime_variant_descriptor.py`
- Validation: [VALIDATION.md](./VALIDATION.md)

## Constitution check

- Article I/II/III/VIII — preserved (public API + Voice domain untouched).
- ADR-0016 invariants 1–12 — preserved; forbidden-pattern entry for
  `RuntimeVariant` narrowed (infrastructure descriptor permitted; domain
  entity/repository still forbidden).
- No VoiceVariant collision — RuntimeVariant fields/types kept disjoint.

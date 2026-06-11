# STATUS — Runtime Variants

Lifecycle position in the SDD flow:
`Brainstorm → Specification → Design → Tasks → Implementation → Validation → Review → Merge`

- **Feature status:** `PARTIAL` — architecture ACCEPTED; Phase 0 primitive
  IMPLEMENTED + VALIDATED; Phases 1–6 PLANNED.
- **ADR:** [ADR-0018](../../../DECISIONS/adr-0018-runtime-variants-architecture.md)
  — Accepted (architecture only), 2026-06-11. Amends ADR-0016's `RuntimeVariant`
  forbidden-pattern entry.
- **Owner / last update:** Task 26, 2026-06-11.

| Allowed status | This feature |
|---|---|
| NOT_STARTED / PLANNED / APPROVED / IN_PROGRESS / **PARTIAL** / IMPLEMENTED / VALIDATED / SUPERSEDED / ARCHIVED | **PARTIAL** |

## Phase status

| Phase | Scope | Status |
|---|---|---|
| 0 | Descriptor primitive (`RuntimeVariantDescriptor` + loader + tests, non-wired) | **IMPLEMENTED + VALIDATED** |
| 1 | RuntimeVariant domain wiring (resolution) | PLANNED |
| 2 | Registry structure evolution (`<runtime>/variants/`) | PLANNED |
| 3 | UI support (family grouping + variant chips) | PLANNED |
| 4 | Runtime service (load/switch without restart) | PLANNED |
| 5 | Marketplace (Cloud) | PLANNED |
| 6 | Hugging Face imports | PLANNED |

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

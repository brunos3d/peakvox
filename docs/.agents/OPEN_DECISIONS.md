# OPEN DECISIONS

> Unresolved architectural decisions. When one is resolved, write an ADR (or amend the
> relevant one), then move the entry to [`DECISIONS/ADR_INDEX.md`](DECISIONS/ADR_INDEX.md).
> These mirror the "Candidate future ADRs" in `../architecture/adrs/README.md` plus active
> open questions.

**Last update:** 2026-06-05

---

## Decision 1 — How to achieve first non-OmniVoice provider validation

- **Status:** ✅ **RESOLVED** (2026-06-05).
- **Decision:** Option 3 — **Kokoro validated as the first non-OmniVoice provider.**
  The `kokoro` pip package was installed (82M, Apache-2.0, CPU-capable), and real audio
  was generated end-to-end through the PeakVox Runtime. All 347 backend tests pass.
- **Context:** The Universal Voice Runtime thesis was architecture-validated but
  provider-validated only for OmniVoice. Fish Audio real inference was blocked (codec/VRAM).
- **Result:** The Cloud readiness gate is now open. The multi-provider thesis is no longer
  architecture-only — Kokoro proves the runtime works with a real non-OmniVoice provider.
- **Related ADRs:** ADR-0008, ADR-0010, ADR-0011; reserved ADR-0012 (provisioning policies),
  ADR-0013 (model categories).
- **See:** `VALIDATION/PROVIDER_VALIDATIONS/kokoro-validation-report.md`

## Decision 2 — Variant provisioning policies per Creation Source (reserved ADR-0012)

- **Status:** OPEN.
- **Context:** ADR-0010's "rebuild every variant from the Source Asset" applies only to
  `SOURCE_ASSET` voices. Other origins (`PRESET_VOICE`, etc.) need their own strategy.
- **Impact:** Provisioning pipeline correctness across origin types.
- **Related ADRs:** ADR-0010, ADR-0011.

## Decision 3 — Model categories (reserved ADR-0013)

- **Status:** OPEN.
- **Context:** Classifying providers — cloning vs preset vs training — to drive provisioning
  and capability expectations.
- **Related ADRs:** ADR-0011.

## Decision 4 — Auth vendor seam (Clerk)

- **Status:** OPEN (Phase 4, Cloud).
- **Context:** First `AuthProvider` adapter choice and principal-resolution wiring.
- **Impact:** Cloud multi-tenancy.

## Decision 5 — Payments/payouts vendor seam (Stripe + Connect)

- **Status:** OPEN (Phases 5–6, Cloud).
- **Context:** First `BillingProvider`/`PaymentProvider`/`PayoutProvider` adapters.

## Decision 6 — SQLite→Postgres cut-over and Alembic adoption

- **Status:** OPEN (Phase 8, Cloud).
- **Context:** Alembic is adopted only at the Cloud Postgres cut-over; CE stays on the
  idempotent SQLite runner.
- **Related:** `../architecture/08-MIGRATION_ARCHITECTURE.md`.

## Decision 7 — pgvector reconsideration

- **Status:** OPEN, current verdict NO.
- **Context:** Only if semantic voice-similarity becomes a product feature; would need its own
  ADR. Today search runs on derived `characteristics`.
- **Related:** `../architecture/03-DATA_ARCHITECTURE.md` §6.

## Decision 8 — Marketplace search backend

- **Status:** OPEN (Phase 7, Cloud).
- **Context:** Postgres FTS vs external index for marketplace discovery at scale.

---

**Related:** [`DECISIONS/ADR_INDEX.md`](DECISIONS/ADR_INDEX.md) · [`ROADMAP/ROADMAP.md`](ROADMAP/ROADMAP.md)

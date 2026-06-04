# Architecture Decision Records (ADRs)

This directory records **expensive-to-reverse** architectural decisions for PeakVox. Each ADR
captures one decision: its context, the options weighed, what was chosen, and the consequences.

> ADRs are immutable once accepted. To change a decision, write a new ADR that supersedes the
> old one (link both ways) — don't edit history.

## Index

| ADR | Title | Status |
|---|---|---|
| [0001](0001-voice-variant-split.md) | Voice / VoiceVariant split as the core domain spine | Accepted |
| [0002](0002-model-as-first-class-entity.md) | Model as a first-class persisted entity | Accepted |

## Conventions

- Filename: `NNNN-short-slug.md` (zero-padded, sequential).
- Status: `Proposed` → `Accepted` → (`Superseded by NNNN` / `Deprecated`).
- Keep each ADR short and decision-focused. Use [`_TEMPLATE.md`](_TEMPLATE.md).

## Candidate future ADRs

Reserved for decisions expected as the roadmap progresses — write them when the decision is
actually made, not before:

- Auth vendor adapter choice (Clerk) and the `AuthProvider` seam.
- Payments/payouts vendor choice (Stripe + Stripe Connect) and the provider seams.
- SQLite→Postgres cut-over and Alembic adoption.
- pgvector reconsideration **iff** semantic voice-similarity search becomes a product feature
  (the current verdict is *no* — see [Data §6](../03-DATA_ARCHITECTURE.md)).
- Search backend for the marketplace (Postgres FTS vs external index).

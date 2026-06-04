# PeakVox — Data Architecture

**Owns:** the physical data model — tables, keys, the schema-ready commercial entities, the
SQLite→Postgres path, and the **pgvector verdict**. Implements the
[Domain Architecture](02-DOMAIN_ARCHITECTURE.md).

> All new tables follow the existing conventions: string UUID PKs, `owner_id` for tenancy,
> JSON columns for flexible attributes, UTC timestamps, additive idempotent migrations.

---

## 1. Entity-relationship overview

```
User ──< ApiKey
 │ └──< Creator ──< Voice ──< VoiceVariant >── Model
 │                   │            │
 │                   │            └── artifacts (object storage)
 │                   ├──< MarketplaceListing
 │                   └──< Royalty
 ├──< CreditLedger ──< Transaction
 ├──< GenerationJob >── Voice, Model
 └──< Payout
```

Legend: `──<` one-to-many, `>──` many-to-one. Commercial tables (Creator, Marketplace,
Credit/Transaction/Royalty/Payout) are **created in CE, populated only in Cloud**.

## 2. Existing tables (today, on `main`)

| Table | Status under PeakVox |
|---|---|
| `users` | Kept. Add `Role` association (additive). |
| `api_keys` | Kept. Rename prefix `ov_live_…` → `pv_live_…` going forward (back-compat accepted). |
| `models` | Kept and extended — already first-class (versioning, `editions`, `capabilities`). |
| `voice_profiles` | **Split** into `voices` + `voice_variants` (migration, preserves `public_voice_id`). |
| `generation_jobs` | Kept and extended (`voice_id`, variant resolution; already has `model_id`). |

## 3. Core tables (CE + Cloud)

### 3.1 `models` (extend existing)

Add columns (all nullable/defaulted — additive):

| Column | Type | Notes |
|---|---|---|
| `requirements` | JSON | VRAM/GPU/runtime needs (Cloud scheduling, capacity) |
| `license` | JSON | `{ code, weights_license, commercial_use, url }` |
| `provider_metadata` | JSON | author, homepage, citation, source |
| `deprecated_at` | datetime? | Lifecycle; supersedes via `version` |

Versioning rule: an **update installs a new row** (or a `model_versions` child table if many
versions per line become common) — never mutate artifacts under a pinned variant.

### 3.2 `voices` (new — from the identity half of `voice_profiles`)

| Column | Type | Notes |
|---|---|---|
| `id` | str(36) PK | |
| `public_voice_id` | str(32) unique | **Permanent** external id (carried over unchanged) |
| `creator_id` | str(36)? FK→creators | NULL in CE (local owner) |
| `owner_id` | str(36) | tenancy (default local owner) |
| `name`, `description` | str / text | |
| `language`, `language_code` | str? | |
| `preview_audio` | str? | storage key for canonical preview |
| `meta`, `characteristics` | JSON | free-form + derived snapshot |
| `royalty_config` | JSON? | **schema-ready**, Cloud-only semantics |
| `is_public`, `is_community_voice`, `is_preset_voice`, `is_favorite` | bool | exist today |
| `status`, `usage_count` | str / int | |
| `created_at`, `updated_at`, `last_used_at` | datetime | |

### 3.3 `voice_variants` (new — the realization layer)

| Column | Type | Notes |
|---|---|---|
| `id` | str(36) PK | |
| `voice_id` | str(36) FK→voices | |
| `model_id` | str(64) FK→models | |
| `model_version` | str? | pin; enables stale detection on model update |
| `artifact_type` | str | `reference_sample`/`embedding`/`checkpoint`/`adapter`/`finetune`/`metadata` |
| `artifacts` | JSON | storage keys for files |
| `params` | JSON | model-specific (OmniVoice: `transcript`, `voice_design`, `generation_defaults`) |
| `source` | str | `cloned`/`designed`/`uploaded`/`regenerated` |
| `status` | str | `pending`/`building`/`ready`/`failed`/`deprecated` — see [ADR-0008](adrs/0008-voice-variant-build-lifecycle.md) for lifecycle |
| `created_at`, `updated_at` | datetime | |

**Constraint:** `UNIQUE(voice_id, model_id)`. Storage paths move under
`/data/voices/{voice_id}/variants/{model_id}/…`.

### 3.4 `generation_jobs` (extend existing)

Add `voice_id` (str(36)?, FK→voices) and `voice_variant_id` (str(36)?) alongside the existing
`model_id`. `voice_profile_id` is kept transitionally and backfilled to the new `voice_id`.

## 4. Schema-ready commercial tables (created in CE, active in Cloud)

These are **created by migrations in every edition** but only written/read when the
corresponding feature flag is on. This is the mechanism that avoids a future domain redesign.

### 4.1 `creators`

`id`, `user_id` FK→users, `display_name`, `bio`, `avatar`, `verification_status`
(`unverified`/`pending`/`verified`), `payout_account_ref` (Stripe Connect account id),
`royalty_defaults` JSON, `created_at`.

### 4.2 `marketplace_listings`

`id`, `voice_id` FK→voices, `status` (`draft`/`published`/`unlisted`/`removed`), `category`,
`tags` JSON, `pricing` JSON (`{ model, rate }`), `preview_audio`, `stats` JSON
(plays/uses/favorites), `published_at`, timestamps. See
[Marketplace](05-MARKETPLACE_ARCHITECTURE.md).

### 4.3 `credit_ledgers`

`id`, `owner_id` FK→users, `balance` (integer credits), `currency`/`unit` metadata,
`updated_at`. One row per owner; the authoritative balance is derived from `transactions`
(ledger is a cached projection).

### 4.4 `transactions` (append-only)

`id`, `owner_id`, `type` (`purchase`/`consume`/`royalty_accrual`/`payout`/`adjustment`),
`amount` (signed integer credits), `balance_after`, `ref` JSON (links to job/listing/payout),
`created_at`. **Never updated or deleted** — corrections are new rows. This ledger is the
source of truth for billing and revenue split.

### 4.5 `royalties`

`id`, `creator_id`, `voice_id`, `generation_job_id`, `model_id`, `gross_amount`,
`creator_amount`, `platform_amount`, `infra_amount`, `status`
(`accrued`/`settled`/`reversed`), `created_at`. One row per royalty-bearing generation. See
[Monetization](07-MONETIZATION_ARCHITECTURE.md).

### 4.6 `payouts`

`id`, `creator_id`, `period`, `amount`, `currency`, `provider` (`stripe_connect`),
`provider_ref`, `status` (`pending`/`paid`/`failed`), `created_at`, `settled_at`.

### 4.7 Identity additions

`roles` (or a `user_roles` association): `user_id`, `role` (`user`/`creator`/`admin`),
`scope` (future org id). CE seeds the local owner with all roles collapsed.

## 5. SQLite → Postgres

| Aspect | CE (now) | Cloud |
|---|---|---|
| Engine | SQLite via `aiosqlite` | PostgreSQL |
| Migrations | idempotent startup runner | **Alembic** (replaces the runner at this point) |
| JSON | SQLite JSON | `jsonb` |
| Concurrency | single-node | pooled, multi-writer |

The SQLAlchemy models are **portable** — JSON columns and the queries in use are
Postgres-compatible. The migration to Postgres is a **Cloud trigger** (multi-tenancy /
concurrency), not a CE requirement; single-node CE stays on SQLite indefinitely. See
[Migration §DB](08-MIGRATION_ARCHITECTURE.md) and the existing
[DATA_MODEL](../DATA_MODEL.md).

**Append-only `transactions` integrity:** in Postgres, enforce immutability with a trigger /
revoked UPDATE-DELETE grants; in SQLite (CE, where billing is off) it is simply never written.

## 6. The pgvector verdict — **NOT NOW**

PeakVox does **not** adopt `pgvector` in the foreseeable phases.

- Voice **discovery, search, and filtering** run on the **derived structured
  `characteristics`** (gender, age, accent, pitch, style, language) — ordinary indexed
  columns / JSON queries. No embeddings required. This already works today and scales to the
  marketplace with conventional indexing + a search service (e.g. Postgres FTS or an external
  search index) for text.
- Introducing `pgvector` adds an extension dependency, ANN index tuning, and an embedding
  pipeline — cost with no current product payoff.

**The only justification that would reopen this:** a concrete product feature for *semantic
voice similarity search by audio embedding* ("find voices that sound like this clip"). If and
when that ships, it gets its **own ADR** weighing pgvector vs an external vector store. Until
then: **no pgvector.** (Consistent with the explicit instruction not to add it without strong
justification.)

## 7. Data ownership & retention

- Every owned row carries `owner_id`; deletion of a Voice cascades to its Variants and storage
  prefix (as today). Marketplace listings are unlisted, not hard-deleted, to preserve royalty
  history.
- `transactions`, `royalties`, `payouts` are **retained** (financial records); voices/variants
  they reference are soft-handled so historical accounting stays intact.

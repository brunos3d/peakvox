# PeakVox — Migration Architecture

**Owns:** how the codebase moves from today's state to PeakVox **without domain redesigns or
breaking changes** — the rename, the `VoiceProfile → Voice + VoiceVariant` split, edition
flags, vendor seams, and the SQLite→Postgres path. Every migration is **additive and
idempotent** (the existing runner's contract).

> See also: [Data](03-DATA_ARCHITECTURE.md) · [Roadmap](09-ROADMAP.md) ·
> [ADR-0001](adrs/0001-voice-variant-split.md)

---

## 1. Principles

1. **Additive, idempotent migrations** — no destructive column changes; safe to re-run (the
   pattern already used by `app/services/migration.py`).
2. **Preserve external contracts** — `public_voice_id` never changes; `/api/v1` stays stable;
   old key prefixes keep working during transition.
3. **Backfill, don't break** — new columns are nullable + backfilled; old columns are kept
   transitionally and removed only after consumers move.
4. **One change at a time** — each migration slice is independently shippable and reversible
   in effect (forward-fix, not down-migrations, in CE).

## 2. The Voice / VoiceVariant split (the central migration)

Today `voice_profiles` fuses identity + OmniVoice artifacts. Target: `voices` (identity) +
`voice_variants` (per-model artifacts). See [ADR-0001](adrs/0001-voice-variant-split.md).

**Steps (each idempotent):**

```
1. CREATE TABLE voices, voice_variants               (additive)
2. Backfill: for each voice_profiles row →
     • INSERT voices(id=<new>, public_voice_id=<carried over UNCHANGED>, name, language,
                     characteristics, visibility flags, owner_id, timestamps…)
     • INSERT voice_variants(voice_id, model_id='omnivoice-base',
                     artifact_type='reference_sample',
                     artifacts={ audio: audio_filename },
                     params={ transcript, voice_design, generation_defaults },
                     source='cloned', status='ready')
3. Add generation_jobs.voice_id + voice_variant_id   (nullable); backfill from voice_profile_id
4. Repoint reads: voice_repository + /api/v1 + frontend read voices/voice_variants
5. (later, after all consumers move) retire voice_profiles writes; keep table read-only, then drop
```

**Storage:** move `/data/voices/{id}/voice.wav` →
`/data/voices/{voice_id}/variants/omnivoice-base/reference.wav` (copy, verify, then remove old
prefix) — or keep old paths in `artifacts` to avoid moving bytes initially.

**Guarantee:** `public_voice_id` is carried across **unchanged**, so every API client, SDK,
and stored reference keeps working. No external breakage.

## 3. The rename (OmniVoice App → PeakVox)

A bounded, mostly-cosmetic slice — the domain is already model-agnostic:

| Layer | Change | Compatibility |
|---|---|---|
| Product/docs | "OmniVoice App" → "PeakVox" (this suite already does) | n/a |
| API key prefix | `ov_live_…` → `pv_live_…` for **new** keys | old prefix **still accepted**; verified by hash, not prefix |
| Package/module names | optional internal rename | internal only; do last, low priority |
| Env vars | `OMNIVOICE_*` → `PEAKVOX_*` | accept both during transition |
| Default model id | `omnivoice-base` stays (it *is* an OmniVoice model) | unchanged |

The rename touches **no domain table semantics**. `OmniVoice` survives as the name of the
first **model provider**, not the product.

## 4. Edition flags & vendor seams

- **Feature flags:** introduce `settings.features` derived from `settings.EDITION`
  ([Product §4.1](01-PRODUCT_ARCHITECTURE.md)). CE = all commercial flags off. This is a config
  addition — no schema change.
- **Schema-ready commercial tables** (`creators`, `marketplace_listings`, `credit_ledgers`,
  `transactions`, `royalties`, `payouts`, `roles`) are created by migrations in **both**
  editions but written only when their flag is on ([Data §4](03-DATA_ARCHITECTURE.md)).
- **Vendor seams:** `AuthProvider`, `BillingProvider`, `PaymentProvider`, `PayoutProvider`
  interfaces with **Null/Local adapters in CE** and **Clerk/Stripe adapters in Cloud**. Adding
  a vendor = adding an adapter; the call sites depend only on the interface (mirrors the
  existing `get_current_owner_id()` seam).

## 5. Model as first-class (already mostly done)

`models` is already a persisted table. Migration adds the new metadata columns
(`requirements`, `license`, `provider_metadata`, `deprecated_at`) — additive — and establishes
the **versioning rule**: model updates **insert a new version**, never mutate artifacts a
variant pins. See [ADR-0002](adrs/0002-model-as-first-class-entity.md).

## 6. SQLite → Postgres (Cloud trigger)

| Phase | DB | Migrations |
|---|---|---|
| CE today / always | SQLite | idempotent startup runner |
| Cloud launch | PostgreSQL | **Alembic** (adopt at the cut-over; baseline = current schema) |

- SQLAlchemy models are portable; JSON → `jsonb`; queries in use are Postgres-compatible.
- Cut-over: stand up Postgres, run the Alembic baseline (= the additive schema), import data,
  switch the connection. CE instances are unaffected and stay on SQLite.
- Adopt Alembic **only at the Postgres cut-over** to avoid dual migration systems before then.

## 7. Sequencing & safety

Recommended order (also reflected in the [Roadmap](09-ROADMAP.md)):

```
1. Feature flags + schema-ready commercial tables   (additive; unlocks everything, breaks nothing)
2. Model metadata columns + versioning rule         (additive)
3. Voice / VoiceVariant split                        (the central migration; backfill + repoint)
4. Rename (prefixes/env/docs, back-compat retained)
5. Auth seam + Clerk adapter (Cloud)                 (CE unchanged: local owner)
6. Billing/credits + Stripe adapters (Cloud)
7. Creator + marketplace wiring (Cloud)
8. Postgres + Alembic (Cloud)
```

Each step is independently shippable, keeps CE working, and preserves the `public_voice_id`
and `/api/v1` contracts throughout. **No big-bang migration.**

## 8. Rollback posture

- CE uses **forward-fix** (no down-migrations): additive columns/tables are harmless if a
  feature is reverted (flag off).
- The Voice split keeps `voice_profiles` intact until all consumers move, so a regression can
  fall back to reading the old table.
- Cloud (Alembic) supports conventional down-migrations for the Postgres era.

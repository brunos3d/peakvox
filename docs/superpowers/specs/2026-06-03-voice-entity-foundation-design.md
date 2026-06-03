# Voice Entity Foundation — Design Spec

**Date:** 2026-06-03
**Status:** Approved (pending implementation plan)
**Sub-project:** A of the OmniVoice Phase 2 platform initiative

---

## Context

OmniVoice Phase 2 transforms the app from a local voice generator into a complete,
ElevenLabs-style voice platform (18 phases: voice identity, metadata, 646-language
registry, library redesign, community voices, public REST API, API keys, SaaS-edition
architecture, docs).

That scope spans several independent subsystems and was decomposed into sub-projects,
each with its own spec → plan → build cycle:

| # | Sub-project | Source phases | Depends on |
|---|---|---|---|
| **A** | **Voice entity + metadata + local-owner model + migration** (this spec) | 1, 2, 16 | — |
| B | Language registry (646 languages, searchable combobox) | 3 | — |
| C | Voice Library redesign (tabs, search, filters, pagination, details) | 4–9 | A, B |
| D | API platform (API keys, `/api/v1`, TTS API, dashboard, Voice-ID UX) | 10–14 | A |
| E | TTS screen auto-config from voice metadata | 15 | A, B |
| F | SaaS edition architecture (design only, no billing) | 17 | A, D |
| G | Documentation suite | 18 | all |

This spec covers **Sub-project A only** — the data-model bedrock every other
sub-project reads from.

### Critical premise correction

The Phase 2 brief repeatedly references an "existing authentication system" and
per-user identity (Owner User ID, My/Community voices, per-user API keys). **No such
system exists.** The codebase is a single-user, self-hosted, local tool:

- [backend/app/models/db.py](../../../backend/app/models/db.py) defines only
  `VoiceProfile` and `GenerationJob` — no `User`, no `owner_id`.
- No login / JWT / session / `current_user` anywhere; every route depends only on
  `get_db`.
- No auth in the frontend.

**Decision (approved):** Build the schema **SaaS-ready** but ship **no authentication**.
Use a single seeded implicit local owner. Community/Publish UIs stay disabled; preset
voice seeding is deferred. Real auth can later be layered in by adding user rows + a
`current_user` dependency, with **no schema redesign**.

---

## Goals

- Every voice gets a **stable, never-changing `public_voice_id`** (e.g. `voice_8JXQ29K4L3`),
  separate from the internal UUID primary key.
- Expand voice metadata: language code, preset tags, derived characteristics, visibility
  flags, status, usage analytics, owner.
- Introduce a minimal `users` table seeded with one system local owner.
- All evolution via an **idempotent, SQLite-safe, no-data-loss startup migration**.
- Existing voice profiles **and existing voice clones keep working unchanged**.

## Non-goals (explicitly out of scope this cycle)

- No authentication of any kind: no login, sessions, JWT, auth middleware, or
  user-facing account system.
- No cloud, billing, or multi-tenant features.
- No Community UI, no Publish UI, no preset-voice seeding (audio sourcing).
- No Voice Library redesign, language registry, or public API (later sub-projects).
- No manual editing of `characteristics`.

---

## Data model

### 1. `voice_profiles` — extended in place

Strategy: **extend the existing table** (no new table, no data copy). `id` (existing
UUID PK) remains the **Internal UUID**. All new columns are nullable or safe-defaulted
for backward compatibility.

Existing columns retained: `id`, `name`, `description`, `language`, `transcript`,
`audio_filename`, `audio_duration`, `meta`, `generation_defaults`, `created_at`,
`last_used_at`.

New columns:

| Column | Type | Default | Notes |
|---|---|---|---|
| `public_voice_id` | String(32), UNIQUE index | generated | **Public Voice ID**, e.g. `voice_8JXQ29K4L3`. Stable, never mutated. The external identifier for APIs/SDKs/UI/Copy-Voice-ID/community/import-export/cloud sync. |
| `owner_id` | String(36), index | `LOCAL_OWNER_ID` | Owner reference (users table). |
| `language_code` | String(16) | NULL | ISO-style code (`pt`). Coexists with display `language` (`Portuguese`). Nullable during migration. |
| `preset_tags` | JSON (list) | NULL | Explicit tags. |
| `characteristics` | JSON | NULL | **Derived snapshot** — see below. |
| `is_public` | Boolean | False | Schema only; Publish UI disabled. |
| `is_community_voice` | Boolean | False | Schema only; Community UI disabled. |
| `is_preset_voice` | Boolean | False | Schema only; seeding deferred. |
| `is_favorite` | Boolean | False | |
| `status` | String(32) | `"ready"` | `ready` / `archived` / `processing` / `failed`. |
| `usage_count` | Integer | 0 | Incremented on generation. |
| `updated_at` | DateTime(tz) | now, onupdate now | (`created_at`, `last_used_at` already exist). |

### 2. `users` — minimal, SaaS-ready, no auth

| Column | Type | Notes |
|---|---|---|
| `id` | String(36) PK | |
| `handle` | String(64), unique | e.g. `local` |
| `display_name` | String(255) | |
| `email` | String(255), nullable | |
| `is_system` | Boolean | True for the seeded local owner |
| `created_at` | DateTime(tz) | |

One seeded row: `LOCAL_OWNER_ID` (fixed constant UUID, handle `local`,
`is_system=True`), created idempotently at startup. Every voice/resource is owned by it.

---

## Identifiers

- **Internal UUID** = `id` (existing PK). Used internally and for storage paths
  (`/data/voices/{id}/...`) — unchanged, so existing clone audio keeps resolving.
- **Public Voice ID** = `public_voice_id`. The contract for all future external
  surfaces: public APIs, SDKs, Copy-Voice-ID, community voices, import/export, cloud sync.
  **Generated once at creation, never changed.**

`generate_public_voice_id()` → `"voice_" + 10 × Crockford-base32` (alphabet excludes
I/L/O/U to avoid visual ambiguity). Uniqueness checked against the DB with
retry-on-collision. Pure and unit-tested.

Helper accessors added now for future API work:
- `get_voice_by_public_id(db, public_voice_id)` — primary external lookup.
- `get_voice_by_internal_id(db, id)` — internal lookup.

---

## Characteristics derivation (single source of truth)

- `voice_design` (existing structured attributes from the VoiceDesignBuilder) is the
  **source of truth**.
- `characteristics` is a **derived, denormalized snapshot**:
  `{ gender, age_group, accent, pitch, style_tags[], speaking_speed, emotional_range }`.
- Pure function `derive_characteristics(voice_design, preset_tags, language) -> dict`
  maps known attributes/tags to characteristic fields; unknown → null.
- **Any change to `voice_design` automatically regenerates `characteristics`** (on
  create / update / defaults-save). No manual editing of `characteristics`.
- **Filtering, searching, pagination, and future recommendation systems read
  `characteristics` only**, never recompute.

---

## Migration — `core/migrations.py` startup runner

Replaces the ad-hoc `ALTER` currently inline in `init_db()`
([database.py:33-40](../../../backend/app/core/database.py#L33)) with an ordered list of
**idempotent** steps. Satisfies the "migration scripts" requirement without Alembic
(correct choice for self-hosted Community Edition / SQLite).

Ordered steps:

1. `create_all` (creates `users`, and `voice_profiles` on fresh installs).
2. `ADD COLUMN` for each new `voice_profiles` field, each wrapped in try/except
   (SQLite raises on duplicate column — safe to ignore; matches existing house style).
3. Seed `LOCAL_OWNER` user if absent.
4. **Backfill** legacy rows: `public_voice_id` (generate where NULL), `owner_id`,
   `status="ready"`, `updated_at=created_at`, `usage_count=0`. Only touches rows whose
   values are NULL — already-migrated rows are untouched.
5. `CREATE UNIQUE INDEX IF NOT EXISTS` on `public_voice_id` **after** backfill (ordering
   matters; SQLite can't `ADD COLUMN ... UNIQUE`).

Guarantees: fully idempotent (re-runnable with no changes to migrated rows), SQLite-safe,
no data loss, no voice recreation, storage paths unchanged so existing clones keep working.

---

## API & schema changes (kept tight this cycle)

- `VoiceProfileResponse` enriched with all new fields (additive — no breakage).
- New Pydantic types: `VoiceCharacteristics`, `VoiceStatus` literal.
- `VoiceProfileCreate` / `VoiceProfileUpdate` accept optional `language_code`,
  `preset_tags`.
- `create_voice` / `update_voice` populate new fields and derive `characteristics`.
- Generation submit increments `usage_count` and sets `last_used_at` on the referenced
  voice (powers Recently-Used / Popular / Trending / analytics later).
- Add `get_voice_by_public_id()` / `get_voice_by_internal_id()` helpers.
- **Deferred to C/D:** favorite/publish toggle endpoints, library tabs, Copy-Voice-ID UI.

## Frontend (minimal this cycle)

- Extend the `VoiceProfile` TypeScript type
  ([frontend/src/types/index.ts](../../../frontend/src/types/index.ts)) with the new
  optional fields only.
- **No UI work** — the library redesign is sub-project C. The existing voices page keeps
  working because all additions are optional.

---

## Constants

- `LOCAL_OWNER_ID` — fixed constant UUID (config).
- `VOICE_ID_PREFIX = "voice_"`.
- Crockford base32 alphabet for ID generation.

---

## Testing

Unit:
- `generate_public_voice_id()` format + collision-retry.
- `derive_characteristics()` mapping (incl. unknown → null).

Migration (explicit, required):
- old database → migrate (columns added, backfill correct).
- migrated database → migrate again (idempotent; no record modified).
- voice generation works after migration.
- legacy voices retain functionality (clone audio still resolves).
- `public_voice_id` uniqueness (unique index enforced; generator avoids collisions).

API:
- create voice returns `public_voice_id` and `owner_id == LOCAL_OWNER_ID`.
- migrated legacy row exposes a stable `public_voice_id`.

---

## Risks & mitigations

- **SQLite `ADD COLUMN` can't be UNIQUE** → separate `CREATE UNIQUE INDEX` after backfill
  (step 5).
- **Backfill ordering** → `public_voice_id` generated before unique index creation.
- **`language_code` backfill** is best-effort/nullable until the language registry
  (sub-project B) lands.
- **`voice_design`→characteristics completeness** → unknown attributes map to null;
  acceptable, snapshot regenerates as the vocabulary grows.

---

## Success criteria

- Existing voice profiles remain usable.
- Existing voice clones remain usable.
- No user data is lost.
- Every voice receives a stable `public_voice_id`.
- Schema becomes SaaS-ready without introducing authentication.
- Foundation is ready for the upcoming Voice Library, Public API, and Language Registry
  sub-projects.

---

## Execution order (within sub-project A)

1. Add `User` model + `LOCAL_OWNER_ID` constant + seed.
2. Extend `VoiceProfile` ORM with new columns + helpers.
3. `core/migrations.py` runner (idempotent ALTERs + backfill + unique index), wired into
   startup.
4. `public_voice_id` generator util.
5. `characteristics` derivation service.
6. Update Pydantic schemas.
7. Wire create/update to populate new fields + derive characteristics.
8. Increment `usage_count` / `last_used_at` on generation submit.
9. Add `get_voice_by_public_id()` / `get_voice_by_internal_id()` helpers.
10. Update frontend `VoiceProfile` TS type.
11. Tests (unit + migration + API).

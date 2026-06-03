# Data Model

The backend uses async SQLAlchemy over SQLite (Community Edition). All paths derive from
`DATA_DIR`; audio lives in S3-compatible object storage (MinIO locally).

> See also: [Voice Model](VOICE_MODEL.md) · [Architecture](ARCHITECTURE.md) · [SaaS Architecture](SAAS_ARCHITECTURE.md)

---

## Tables

### `users`
The minimal account record. SaaS-ready; **no authentication exists** in Community
Edition — a single seeded system user owns everything.

| Column | Type | Notes |
|---|---|---|
| `id` | str (PK) | `LOCAL_OWNER_ID` for the seeded owner |
| `handle` | str (unique) | `local` |
| `display_name` | str? | |
| `email` | str? | |
| `is_system` | bool | True for the seeded owner |
| `created_at` | datetime | |

### `voice_profiles`
The Voice entity. See [Voice Model](VOICE_MODEL.md) for field semantics. Key columns:
`id` (internal UUID), `public_voice_id` (unique, stable), `owner_id`, `name`,
`language`, `language_code`, `transcript`, `audio_filename`, `audio_duration`,
`generation_defaults` (json), `preset_tags` (json), `characteristics` (json),
`is_public` / `is_community_voice` / `is_preset_voice` / `is_favorite`, `status`,
`usage_count`, `created_at` / `updated_at` / `last_used_at`.

### `api_keys`
Hashed credentials for the public API. The raw key is shown once; only its hash is stored.

| Column | Type | Notes |
|---|---|---|
| `id` | str (PK) | |
| `name` | str | |
| `prefix` | str (indexed) | Display prefix, e.g. `ov_live_1a2b3c4d` |
| `secret_hash` | str (unique) | sha256 of the full key |
| `owner_id` | str (indexed) | |
| `status` | str | `active` / `revoked` |
| `created_at` / `last_used_at` | datetime | |

### `generation_jobs`
Fire-and-forget TTS jobs (status polled by the UI; awaited by the public API).
Columns: `id`, `status`, `text`, `voice_profile_id`, `ref_audio_path`, `ref_text`,
`language`, `instruct`, `generation_params` (json), `output_path`, `audio_duration`,
`error_message`, `logs` (json), `created_at` / `started_at` / `completed_at`.

---

## Relationships

```
users(1) ──< voice_profiles(owner_id)
users(1) ──< api_keys(owner_id)
voice_profiles(1) ──< generation_jobs(voice_profile_id)   # nullable: ad-hoc refs allowed
```

In Community Edition there is exactly one `users` row, so everything is implicitly owned
by it. `owner_id` makes multi-tenancy (Cloud/Enterprise) additive — see
[SaaS Architecture](SAAS_ARCHITECTURE.md).

---

## Migrations

There is **no Alembic**. Schema evolution runs at startup via an idempotent runner:
`backend/app/core/migrations.py::run_migrations`.

Properties:
- **Idempotent** — safe to run on every boot; already-migrated rows are untouched.
- **SQLite-safe** — `ADD COLUMN` per new field wrapped in try/except; unique constraints
  added via `CREATE UNIQUE INDEX IF NOT EXISTS` after backfill.
- **No data loss / no voice recreation** — existing voices keep their internal `id` and
  storage paths; legacy rows are backfilled (e.g. a generated `public_voice_id`, default
  `owner_id`, `status`, `usage_count`).
- **New tables** (`users`, `api_keys`) are created by `create_all` automatically.

Migration behavior is covered by tests in `backend/tests/test_migrations.py`
(old→migrate, migrate-again idempotency, fresh DB, legacy preservation, id uniqueness).

### Adding a column (pattern)

1. Add the field to the ORM model in `models/db.py`.
2. Append an idempotent `ADD COLUMN` (with a safe default) to `_NEW_VOICE_COLUMNS` in
   `migrations.py`, and backfill if needed.
3. Add/extend a test in `test_migrations.py`.

When the Cloud Edition moves to Postgres, this runner is replaced by Alembic; the models
are already portable.

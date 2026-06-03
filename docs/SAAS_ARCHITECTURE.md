# OmniVoice SaaS Architecture

**Status:** Design / forward-compatibility blueprint (Phase 2, sub-project F)
**Scope:** Architecture only. No authentication, billing, or cloud infrastructure is
implemented in the Community Edition. This document describes how those layers attach
later **without a database redesign or breaking changes.**

---

## 1. Editions

OmniVoice follows an **open-core** model with three editions that share one codebase and
one schema. Editions differ only by which optional extensions are wired in.

| Capability | Community (now) | Cloud (future) | Enterprise (future) |
|---|---|---|---|
| Hosting | Self-hosted | Anthropic-style managed | Self-hosted or managed |
| Authentication | None (local owner) | Hosted accounts + sessions | SSO / SAML / OIDC |
| Tenancy | Single implicit owner | Multi-tenant | Multi-tenant + orgs |
| API keys | Local, unscoped quotas | Per-account, metered | Per-org, RBAC-scoped |
| Voice library | Local | Per-account + Community | Team / shared voices |
| Billing | None | Subscription + usage metering | Contracts |
| Usage metering | Key activity only | Full per-request metering | Full + export |
| RBAC | None | Basic roles | Fine-grained roles |
| Voice publishing | Schema only (disabled) | Community voices | Org-internal sharing |

`settings.EDITION` (default `"community"`) selects the active profile. It only toggles
which extensions load — it never changes the core schema.

---

## 2. What is already SaaS-ready

Phase 2 deliberately built the foundation so the Cloud/Enterprise layers are additive:

- **`users` table + `owner_id` everywhere.** Voices and API keys carry `owner_id`,
  defaulted to the seeded local owner. Multi-tenancy = populate real users and resolve
  `owner_id` per request.
- **Stable `public_voice_id`.** The external contract for APIs, SDKs, community voices,
  import/export, and cloud sync — independent of internal UUIDs and storage paths.
- **Hashed API keys** (`ov_live_…`, sha256, never stored raw) with `owner_id`, `status`,
  and `last_used_at`. Per-account/per-org scoping is a query filter, not a redesign.
- **Identity seam** (`app/core/identity.py::get_current_owner_id`). The single function
  to override when auth arrives.
- **Visibility flags** (`is_public`, `is_community_voice`, `is_preset_voice`) present but
  disabled — community/publishing UIs activate without migration.
- **Rate-limit hook** (`app/api/v1.py::enforce_rate_limit`) — a no-op seam for quotas.
- **Idempotent migration runner** — safe, additive schema evolution with no Alembic.
- **Object storage abstraction** (MinIO/S3) — already cloud-shaped.

---

## 3. Extension points

| Concern | Seam (today) | Cloud/Enterprise implementation |
|---|---|---|
| Identity | `core/identity.get_current_owner_id()` → local owner | Resolve session/JWT/API-key principal; inject as a FastAPI dependency on every router |
| API auth | `api/v1.require_api_key` (verifies key, returns `ApiKey`) | Add account/org scoping + quota lookup on the returned key |
| Rate limiting | `api/v1.enforce_rate_limit(key)` no-op | Token-bucket / Redis limiter keyed by `owner_id` + plan |
| Usage metering | `api_keys.last_used_at` updated per call | Append usage events to a metering store; aggregate for billing |
| Tenancy filter | repository queries filter `owner_id == LOCAL_OWNER_ID` | Filter by the resolved principal's `owner_id` / org id |
| Billing | none | Subscription service reads metering; gates quotas |
| Voice publishing | `is_public` / `is_community_voice` flags | Publish flow + Community browse (schema ready) |
| RBAC | none | Role table + permission checks in the identity dependency |
| Cloud sync | `public_voice_id` + storage keys | Sync engine reconciles by `public_voice_id` |

**Design rule:** new multi-tenant-aware code depends on `get_current_owner_id()` and
filters by the returned id, so flipping editions is a change at the seam, not the call
sites.

---

## 4. Tenancy model

```
User (owner)
  └── owns ──> VoiceProfile (owner_id)
  └── owns ──> ApiKey (owner_id)
  └── owns ──> GenerationJob (via voice / future owner_id)
```

- **Community:** exactly one system `User` (`LOCAL_OWNER_ID`); everything belongs to it.
- **Cloud:** many `User`s; `owner_id` scopes every query; the identity seam resolves the
  caller from a session or API key.
- **Enterprise:** add an `Organization` layer (an additive table) and an `org_id` column
  (additive, nullable, backfilled to a default org) — the same idempotent-migration
  pattern used in sub-project A. RBAC roles attach to the membership edge.

No existing column changes meaning across editions; growth is additive.

---

## 5. API evolution

- `/api/v1` is versioned from day one. Breaking changes ship under `/api/v2`; `/api/v1`
  stays stable for existing SDKs.
- Auth is already header-based (`Authorization: Bearer` / `X-API-Key`), so Cloud only
  changes **what a key resolves to** (account/org + plan), not the wire contract.
- Responses use stable `public_voice_id` and camelCase fields — SDK-friendly and stable
  across editions.
- TTS supports both streaming and download-URL responses, so a future signed-URL/CDN
  delivery path drops in behind the same endpoint.

---

## 6. Deployment topology (future Cloud)

```
            ┌────────────┐     ┌─────────────┐
  client ──▶│  Edge/CDN  │────▶│  API (FastAPI)│──▶ identity/auth ──▶ owner_id
            └────────────┘     │  + rate limit │
                               │  + metering   │──▶ metering store ──▶ billing
                               └──────┬────────┘
                                      ▼
                           inference workers (GPU pool)
                                      ▼
                          object storage (S3) + DB (Postgres)
```

- **DB:** SQLite (Community) → Postgres (Cloud). SQLAlchemy models are portable; the
  JSON columns and queries used are Postgres-compatible. Alembic would replace the
  startup runner at that point.
- **Inference:** the single-GPU, offload-after-use service becomes a horizontally scaled
  worker pool behind a queue; the job-based pipeline already models async generation.
- **Storage:** already S3-compatible (MinIO locally).

---

## 7. Explicitly out of scope (now)

No authentication, sessions, JWT, OAuth/SSO, billing, metering backend, multi-tenant
query rewiring, organizations, RBAC, or cloud infrastructure is implemented. This document
plus the seams above are the preparation; implementation belongs to the Cloud/Enterprise
editions.

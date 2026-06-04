# PeakVox — Cloud Architecture

**Owns:** the managed, multi-tenant deployment — tenancy, the auth seam, inference workers,
storage, request topology, and observability. **Cloud-only**; CE remains a single-node
self-hosted deployment.

> See also: [Product](01-PRODUCT_ARCHITECTURE.md) · [Data §5](03-DATA_ARCHITECTURE.md) ·
> [Migration](08-MIGRATION_ARCHITECTURE.md) · existing [SAAS_ARCHITECTURE](../SAAS_ARCHITECTURE.md)

---

## 1. Topology

```
                ┌────────────┐    ┌──────────────────────────┐
   client ─────▶│  Edge/CDN  │───▶│  API gateway (FastAPI)    │
                └────────────┘    │  • AuthProvider (Clerk)   │──▶ principal (owner/org+plan)
                                  │  • rate limit (Redis)      │
                                  │  • metering                │──▶ usage store ──▶ billing
                                  │  • Voice+Model resolution  │
                                  └───────┬───────────┬────────┘
                                          │           │
                                  enqueue │           │ sync (fast paths)
                                          ▼           ▼
                              ┌────────────────────────────┐
                              │  inference worker pool (GPU)│  ← model registry + providers
                              │  load-on-demand, offload    │
                              └───────────┬────────────────┘
                                          ▼
                      object storage (S3)        Postgres (primary + replicas)
                      voices/variants/outputs     domain + ledger + metering
```

## 2. Multi-tenancy

- Every owned row carries `owner_id` (exists today). Cloud resolves the principal per request
  via the **`AuthProvider`** adapter and **filters every repository query by the resolved
  `owner_id`** — the seam (`get_current_owner_id()`) already exists; Cloud changes only what it
  returns.
- **Organizations/Teams** are an additive layer (`org_id`, nullable, backfilled to a default
  org) introduced when needed — no change to existing column meaning. RBAC roles attach to the
  membership edge.
- **Isolation:** tenant data is logically isolated by `owner_id`/`org_id`; storage keys are
  namespaced per owner. Enterprise may add physical isolation later.

## 3. Auth seam → Clerk adapter

Auth is an **interface**, not a vendor lock-in (the chosen stance):

```
AuthProvider (interface)
  ├─ resolve_principal(request) -> Principal{ owner_id, org_id?, roles, plan }
  └─ require_role(role)
        │
        ├─ CE:    LocalOwnerAuthProvider   (always the seeded owner, all roles)
        └─ Cloud: ClerkAuthProvider        (sessions for Studio, API keys for API)
```

Clerk handles sessions, sign-in/up, social, and (later) orgs/SSO; the platform maps Clerk
identities to `users.owner_id`. Swapping Clerk for Auth0/Supabase/self-hosted is a new adapter,
not a domain change. See [Migration §Auth](08-MIGRATION_ARCHITECTURE.md).

## 4. Inference workers

The current in-process, single-GPU, offload-after-use service becomes a **horizontally scaled
worker pool behind a queue** — the job-based pipeline already models async generation, so this
is a deployment change, not a redesign.

- **Queue:** API enqueues generation jobs; workers consume. Fast paths may run sync.
- **Model loading:** workers use the **same model registry + providers** as CE; models load on
  demand and offload to free VRAM (existing behavior), now per-worker.
- **Scheduling:** jobs route to workers by **model + `requirements`** (the new `models.requirements`
  field drives VRAM-aware placement). Variant-build jobs (onboarding pipeline) share the pool.
- **Scaling:** workers scale on queue depth; GPU pools per model class. See
  [Roadmap — Phase 10 (Production Scaling)](09-ROADMAP.md).

## 5. Storage

- **Object storage** is already S3-compatible (MinIO locally). Cloud uses S3 with
  per-owner-namespaced keys for voices, variants, and generated outputs.
- **Delivery:** generated audio served via signed URLs / CDN — drops in behind the existing
  download-URL response shape (the API already supports stream + download-URL).
- **Lifecycle:** generated outputs have TTL/retention policy; voice + variant artifacts are
  durable.

## 6. Database

- **Postgres** (primary + read replicas) replaces SQLite for Cloud; **Alembic** replaces the
  idempotent startup runner. Models are portable (see [Data §5](03-DATA_ARCHITECTURE.md)).
- **Ledger integrity:** `transactions` immutability enforced via trigger/revoked grants.
- **Connection pooling** (e.g. PgBouncer) for the worker + API fan-out.

## 7. Observability & ops

- **Metrics:** request latency, queue depth, GPU utilization, model load times, generation
  success rate, credits consumed, royalties accrued.
- **Tracing:** request → resolution → enqueue → worker → storage, correlated by `jobId`.
- **Audit:** auth events, key usage, payouts, moderation actions (Enterprise-grade later).
- **Health:** existing `/health` extended with worker-pool + queue + DB checks.

## 8. Edition separation in deployment

Cloud-only services (`app/cloud/…`: billing, marketplace publishing, creator verification,
metering, Clerk/Stripe adapters) are **physically separate modules** CE never imports
([Product §4.2](01-PRODUCT_ARCHITECTURE.md)). This keeps the open-core license boundary clean
and lets Cloud deploy/scale those services independently of the core generation path.

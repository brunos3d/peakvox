# PeakVox — API Architecture

**Owns:** the public API contract — versioning, the `Voice + Model → VoiceVariant` resolution
at the wire level, key namespacing, auth/metering seams, and stability guarantees.

> See also: [Domain](02-DOMAIN_ARCHITECTURE.md) · [Monetization](07-MONETIZATION_ARCHITECTURE.md)
> · existing [API.md](../API.md) (current `/api/v1`)

---

## 1. Principles

1. **The contract is `Voice` + `Model`, never artifacts.** Callers reference a stable
   `public_voice_id` and a `model` id; the platform resolves the `VoiceVariant`. This is what
   keeps the API stable when models or artifacts change.
2. **Versioned from day one.** `/v1` is frozen; breaking changes ship under `/v2`. `/v1`
   stays alive for existing SDKs.
3. **One contract, two editions.** CE and Cloud expose the *same* endpoints. Cloud only
   changes **what a key resolves to** (account/org + plan + quota) and adds metering —
   not the wire shape.
4. **Stable, SDK-friendly responses.** `public_voice_id`, model ids, camelCase fields.

## 2. Surface

```
/v1
├── /speech
│   └── POST /generate            # the core endpoint
├── /voices                       # list / get / create / update / delete (by public_voice_id)
│   ├── GET  /voices
│   ├── POST /voices              # create (upload/record/design → onboarding pipeline)
│   ├── GET  /voices/{public_voice_id}
│   └── ...
├── /models                       # discover / inspect models + capabilities
│   ├── GET  /models
│   └── GET  /models/{model_id}
├── /jobs/{id}                    # async job status + audio (exists today)
└── /marketplace   (Cloud)        # browse / search / preview / use
    ├── GET  /marketplace/voices
    └── GET  /marketplace/voices/{public_voice_id}
```

Creator/billing/payout management endpoints live under Cloud-only routers
(`/creator`, `/billing`) and are never mounted in CE.

## 3. The core endpoint

```http
POST /v1/speech/generate
Authorization: Bearer pv_live_…
Content-Type: application/json

{
  "model": "omnivoice-base",      // optional → platform default
  "voice": "voice_8JXQ29K4L3",    // public_voice_id  (or inline ref for ad-hoc cloning)
  "text": "...",
  "language": "pt",               // optional → voice default
  "params": { "num_step": 32, "guidance_scale": 2.0 },   // model-specific, validated
  "stream": false,
  "format": "wav"                 // wav | mp3
}
```

**Resolution (server side):**

```
auth → principal (owner/account + plan)         [CE: local owner]
  ▼
resolve model  → validate request vs ModelCapabilities (e.g. singing/emotions supported?)
  ▼
resolve voice  → Voice by public_voice_id  (+ authorize: owned | public | marketplace)
  ▼
resolve VoiceVariant(voice, model)
  ├─ ready    → use
  ├─ missing  → build via onboarding pipeline (sync if fast, else 202 + job)
  └─ stale    → rebuild
  ▼
[Cloud] check credits / quota  → reserve
  ▼
run inference (provider) → audio
  ▼
emit generation.completed → [Cloud] meter usage + accrue royalty to voice's creator
```

**Responses:**
- Sync: `200` with `{ jobId, audioUrl | audioBase64, durationSec, model, voice }`.
- Async / building variant: `202` with `{ jobId, status: "processing" }`; poll
  `GET /v1/jobs/{id}` (existing pattern).
- Capability mismatch: `422` (`model does not support 'singing'`).
- Variant not buildable for that model: `409`.
- Out of credits (Cloud): `402`.

## 4. Stability guarantees

| Guarantee | Mechanism |
|---|---|
| A `public_voice_id` keeps working across model/artifact changes | Variant resolution hides realization |
| Switching the default model doesn't break callers | `model` defaults are server-resolved; callers may pin |
| A model update doesn't break pinned callers | Variants pin `model_version`; updates create new versions |
| `/v1` never breaks | Additive only; breaking changes → `/v2` |
| CE → Cloud needs no client change | Same endpoints; only key resolution + metering differ |

## 5. Authentication & keys

- **Wire format unchanged:** `Authorization: Bearer <key>` / `X-API-Key`.
- **Key namespace:** `pv_live_…` / `pv_test_…` (renamed from `ov_live_…`; old prefix accepted
  during transition — see [Migration](08-MIGRATION_ARCHITECTURE.md)). Hashed (sha256), display
  prefix only, never stored raw — as today.
- **CE:** keys belong to the local owner, unmetered.
- **Cloud:** the `AuthProvider` (Clerk) adapter resolves the principal for **session-based**
  Studio calls; **API keys** resolve to an account/org + plan. The key carries scope + quota;
  the *handler code is identical* — only the resolved principal differs. This is the existing
  `require_api_key` / `get_current_owner_id` seam, extended.

## 6. Metering & rate limiting (Cloud)

- The existing `enforce_rate_limit(key)` no-op becomes a token-bucket/Redis limiter keyed by
  `owner_id` + plan.
- `generation.completed` events append **usage records**; aggregation drives billing and the
  credit ledger. CE updates only `last_used_at` (no metering store), preserving the seam.
- Quotas/credits are checked **before** reserving inference; royalties accrue **after**
  success. See [Monetization](07-MONETIZATION_ARCHITECTURE.md).

## 7. SDKs

A thin official SDK wraps `/v1` (`generate`, `voices`, `models`, `marketplace`). Because the
contract is `Voice + Model`, the SDK surface is stable across editions and model changes. SDK
versioning tracks the API major version, not model versions.

## 8. Versioning & deprecation policy

- Additive changes (new fields, new optional params, new endpoints) ship in `/v1`.
- Breaking changes (removed/renamed fields, changed semantics) require `/v2`; `/v1` is
  supported for a published deprecation window.
- Model deprecation is **independent** of API versioning: a deprecated model returns `410`/a
  documented fallback, but the endpoint contract is unchanged.

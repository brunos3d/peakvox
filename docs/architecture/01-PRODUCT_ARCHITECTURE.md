# PeakVox — Product Architecture

**Owns:** editions, personas/roles, the capability matrix, how features are gated
(feature flags + deployment boundaries), and the CE↔Cloud boundary as a product contract.

> See also: [Overview](00-OVERVIEW.md) · [Domain](02-DOMAIN_ARCHITECTURE.md) ·
> [Monetization](07-MONETIZATION_ARCHITECTURE.md) · [COMMERCIAL_MODEL](../COMMERCIAL_MODEL.md)

---

## 1. Product surfaces

PeakVox exposes four surfaces over one shared core:

1. **Studio** — the interactive app (today's frontend): generate speech, clone/design
   voices, manage models, manage a voice library. Present in **CE and Cloud**.
2. **Voice Marketplace** — browse, search, preview, and use voices published by creators.
   **Cloud only** (CE may browse read-only later; see roadmap).
3. **Creator Console** — creator profiles, voice catalog, verification, royalties,
   analytics, payouts. **Cloud only.**
4. **Public API** — programmatic speech generation and voice/model management for external
   integrators and SDKs. Present in **CE** (local, unmetered) and **Cloud** (metered,
   billed).

## 2. Personas & roles

| Role | Description | CE | Cloud |
|---|---|---|---|
| **Owner** (implicit) | The single local owner of a self-hosted instance | ✅ (only role) | — |
| **User** | An authenticated account that generates speech and manages its own voices | — | ✅ |
| **Creator** | A user who publishes voices, owns them as economic assets, and earns royalties | schema-ready | ✅ |
| **Admin** | Platform operator: model lifecycle, moderation, payouts oversight | schema-ready | ✅ |
| **Team / Organization** | (future) a tenancy grouping users with shared voices + RBAC | schema seam only | future |

Roles are an **additive layer** on the existing `users` table; CE collapses every role into
the single seeded local owner. See [Domain §Identity](02-DOMAIN_ARCHITECTURE.md) and
[Migration §Auth seam](08-MIGRATION_ARCHITECTURE.md).

## 3. Capability matrix

| Capability | CE | Cloud | Gated by |
|---|:--:|:--:|---|
| TTS / voice cloning / voice design | ✅ | ✅ | always on |
| Multi-model generation | ✅ | ✅ | model registry |
| Model install / activate / deactivate / update | ✅ | ✅ (admin) | `models` lifecycle |
| Singing & emotion (capability-gated) | ✅ | ✅ | `ModelCapabilities` |
| Voice library (My / favorites / recent) | ✅ | ✅ | always on |
| Local API keys + `/v1` | ✅ | ✅ | always on |
| Accounts, sessions, roles | — | ✅ | `AuthProvider` adapter |
| Usage metering + credits | — | ✅ | `feature.billing` |
| Marketplace (publish/browse/use) | schema-ready | ✅ | `feature.marketplace` |
| Creator profiles + verification | schema-ready | ✅ | `feature.creators` |
| Royalties + payouts | schema-ready | ✅ | `feature.payouts` |
| Multi-tenancy + RBAC | seam only | ✅ | `feature.tenancy` |

"schema-ready" = the tables, domain types, and API boundaries exist in CE but the routers /
services / UI are not wired and the feature flag is off.

## 4. How features are gated

Two complementary mechanisms — never a fork of the core schema:

### 4.1 Feature flags (`settings.features`)

A typed set of booleans derived from `settings.EDITION` plus explicit overrides:

```
EDITION=community  → features = { marketplace:false, creators:false, billing:false,
                                   payouts:false, tenancy:false, auth:false }
EDITION=cloud      → features = { marketplace:true,  creators:true,  billing:true,
                                   payouts:true,  tenancy:true,  auth:true  }
```

Flags gate **router registration**, **service wiring**, and **UI navigation** — not table
existence. A disabled feature means its endpoints are never mounted, not that they 404 from
inside a half-built handler.

### 4.2 Deployment boundaries

Cloud-only concerns live in **separately mountable modules** (e.g. `app/cloud/…` routers,
`peakvox-cloud` services) that CE simply never imports. This keeps commercial code physically
separable for the open-core license boundary, while the **shared domain + schema** live in
the core package both editions depend on.

```
core (open, both editions)        cloud (commercial, Cloud only)
├── domain models / schema         ├── billing / credits / payouts
├── model registry                 ├── marketplace publishing
├── voice + variant pipeline       ├── creator verification + analytics
├── generation                     ├── multi-tenant auth (Clerk adapter)
└── public API (/v1)               └── metering + rate limiting
```

## 5. The CE↔Cloud boundary as a product contract

- **CE is the infrastructure layer.** It must be a complete, valuable local product:
  generate, clone, design, manage models, use the API — forever, for free, self-hosted.
- **Cloud is the ecosystem layer.** It adds *not-self-hosting convenience* plus the
  *network effects*: a shared marketplace, a creator economy, monetization, and scale.
- **No crippling.** Cloud never removes a CE capability to upsell. Cloud features are
  additive (accounts, marketplace, money), not subtractions from CE.
- **One schema, one domain.** Because commercial entities are schema-ready in CE, a self-host
  → Cloud migration (or a Cloud feature launch) is configuration + wiring, never a domain
  rewrite. This is the core product promise of the architecture.

## 6. Product-level success criteria

1. A new model can be added without touching the Voice, marketplace, or billing domains.
2. A Voice published by a creator earns royalties on every generation across **any** model
   variant, without the caller knowing which variant ran.
3. CE and Cloud build from one codebase; the difference is `EDITION` + which modules mount.
4. Turning on a Cloud feature requires no migration of existing CE data.

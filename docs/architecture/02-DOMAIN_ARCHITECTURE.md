# PeakVox — Domain Architecture

**Owns:** the bounded contexts and the core domain entities — above all the
**Model / Voice / VoiceVariant** spine — plus their relationships, invariants, and
lifecycles. This is the conceptual model the rest of the suite implements.

> See also: [Data](03-DATA_ARCHITECTURE.md) (physical schema) ·
> [ADR-0001](adrs/0001-voice-variant-split.md) · [ADR-0002](adrs/0002-model-as-first-class-entity.md)

---

## 1. The core spine

```
        ┌─────────┐                 ┌─────────┐
        │  Voice  │  identity        │  Model  │  inference engine
        └────┬────┘                 └────┬────┘
             │  (voice_id)               │  (model_id)
             └───────────┬───────────────┘
                         ▼
                 ┌───────────────┐
                 │ VoiceVariant  │  the (Voice × Model) realization
                 │  artifacts    │  embeddings / refs / adapters / checkpoints
                 └───────────────┘
                         ▼
                 generated speech
```

**Voice** is the model-agnostic identity and the long-term **economic asset**.
**Model** is the inference engine. **VoiceVariant** is the model-specific realization that
holds whatever artifacts a given engine needs to render that voice. A `VoiceVariant` is
uniquely keyed by `(voice_id, model_id)`.

The **stable public contract** is `Voice + Model → VoiceVariant`. Callers name a Voice and a
Model; the platform resolves (or lazily produces) the Variant. See
[ADR-0001](adrs/0001-voice-variant-split.md) for why this is the primary spine and not a
side-table.

## 2. Bounded contexts

| Context | Core entities | Edition | Responsibility |
|---|---|---|---|
| **Model Registry** | `Model`, `ModelProvider` | CE + Cloud | Catalog, lifecycle, capabilities, licensing/provider metadata |
| **Voice Identity** | `Voice` | CE + Cloud | The stable, ownable identity + metadata + preview |
| **Voice Realization** | `VoiceVariant`, onboarding pipeline | CE + Cloud | Per-model artifacts; build/regenerate them |
| **Generation** | `GenerationJob` | CE + Cloud | Resolve `Voice+Model→Variant`, run inference, emit usage |
| **Identity & Access** | `User`, `Role`, `ApiKey` | CE (local owner) / Cloud (full) | Who is calling; what they may do |
| **Creator** | `Creator`, verification | schema-ready / Cloud | Creator profiles, ownership, payout identity |
| **Marketplace** | `MarketplaceListing` | schema-ready / Cloud | Publish, discover, price, preview |
| **Monetization** | `CreditLedger`, `Transaction`, `Royalty`, `Payout` | schema-ready / Cloud | Credits, billing, revenue split, payouts |

Contexts communicate through **IDs and domain events**, never by reaching into each other's
tables. The Generation context, for example, references a `voice_id` + `model_id` and emits a
`generation.completed` event carrying enough to drive metering and royalties — it does not
know about credits or creators.

## 3. Model (first-class, persisted)

A **Model** is an inference engine, persisted (already a real table today), not merely a
runtime registry object. It must support **versioning, lifecycle, licensing, and provider
metadata** because future phases (updates, marketplace of models, multi-provider) depend on
it. See [ADR-0002](adrs/0002-model-as-first-class-entity.md).

| Property | Purpose |
|---|---|
| `id`, `name`, `description` | Identity and display |
| `provider` | Names a registered `ModelProvider` plugin (load/run strategy) |
| `version` | Semver; multiple versions of the same model line can coexist |
| `repo_id` / `model_path` | Load coordinates (e.g. Hugging Face repo) |
| `capabilities` | `ModelCapabilities` — tts / cloning / emotions / singing / streaming / api |
| `supported_languages`, `supported_tags`, `supported_voice_design` | Capability surface for validation + UI |
| `requirements` *(new)* | VRAM / GPU / runtime requirements (capacity planning, Cloud scheduling) |
| `license` *(new)* | Licensing metadata (e.g. Apache-2.0, weights license, commercial-use flag) |
| `provider_metadata` *(new)* | Provider/author, homepage, citation, source URL |
| `status` | `available` / `loading` / `loaded` / `error` / `disabled` |
| `is_default`, `is_builtin`, `editions` | Defaulting + open-core gating |
| `owner_id` | NULL for built-ins; set for user/community-installed models |

**Lifecycle:** `discover → install → activate → (load on demand) → deactivate → update →
deprecate`. The registry orchestrates this; providers implement load/run. Versioning means an
**update** installs a new `version` row rather than mutating artifacts in place, so existing
variants pinned to an old version keep working.

## 4. Voice (identity & economic asset)

A **Voice** is a reusable identity, independent of any model. It is what a creator owns,
publishes, and earns on; what an API caller references; what the marketplace lists.

| Property | Notes |
|---|---|
| `id` (UUID) | Internal PK / storage prefix |
| `public_voice_id` (`voice_…`) | The permanent external contract (exists today) |
| `creator_id` | Owning creator (Cloud); the local owner in CE |
| `owner_id` | Tenancy scope (exists today) |
| `name`, `description`, `language`, `language_code` | Display + default language |
| `preview_audio` | Canonical preview clip (model-agnostic, for marketplace/listing) |
| `metadata`, `characteristics` | Free-form + derived structured snapshot (drives search/filter) |
| `royalty_config` *(new, Cloud)* | Per-voice royalty rate / terms (schema-ready in CE) |
| `visibility` | `is_public` / `is_community_voice` / `is_preset_voice` (exist today) |
| `status`, `usage_count`, timestamps | Lifecycle + metering |

**Invariant:** `public_voice_id` never changes — not on rename, re-record, re-train, or
republish. External systems store only `public_voice_id`. See [VOICE_MODEL](../VOICE_MODEL.md).

**Note on today's `VoiceProfile`:** it fuses identity with OmniVoice artifacts. PeakVox splits
it: identity fields → `Voice`; `audio_filename` / `transcript` / `voice_design` /
`generation_defaults` → an **OmniVoice `VoiceVariant`**. See
[Migration §Voice split](08-MIGRATION_ARCHITECTURE.md).

## 5. VoiceVariant (model-specific realization)

A **VoiceVariant** is the realization of one Voice for one Model: the artifacts that engine
needs to render that identity.

| Property | Notes |
|---|---|
| `id` | PK |
| `voice_id` → Voice | The identity it realizes |
| `model_id` → Model | The engine it targets (may pin a `version`) |
| `artifact_type` | `reference_sample` / `embedding` / `checkpoint` / `adapter` / `finetune` / `metadata` |
| `artifacts` | Storage keys for the actual files (S3/MinIO/local) |
| `params` | Model-specific config (e.g. OmniVoice `transcript`, `voice_design`, defaults) |
| `status` | `ready` / `processing` / `failed` / `stale` |
| `source` | `cloned` / `designed` / `uploaded` / `regenerated` |
| timestamps | Build + freshness tracking |

**Invariants:**
- Exactly one `VoiceVariant` per `(voice_id, model_id)` (unique constraint).
- A Variant is **derivable**: if its model updates, the Variant can be marked `stale` and
  **regenerated** from the Voice's canonical sources by the onboarding pipeline — without a
  new `public_voice_id`.
- A Voice with zero Variants is still a valid identity (e.g. freshly published, variants built
  lazily on first use for a given model).

## 6. Voice onboarding pipeline

The pipeline turns creator/user inputs into Voices + Variants:

```
Creator/User
   └─ upload samples / record / design
        ▼
   validate samples ──► (length, quality, consent/ownership)
        ▼
   process audio ──► normalize, denoise, derive characteristics, build preview
        ▼
   create/locate Voice (assign public_voice_id, derive characteristics)
        ▼
   generate model-specific VoiceVariant(s)  ◄── per active/target Model
        ▼
   publish (Cloud: listing + royalty_config; CE: local library)
```

**Lazy variant build:** in the common path a Voice is created with the OmniVoice variant; a
variant for another model is built on demand the first time that `Voice+Model` is requested
(or eagerly for published marketplace voices). **Automated retraining / artifact regeneration**
on model updates reuses this same pipeline.

## 7. Generation (resolution)

`POST /v1/speech/generate { model, voice, text, … }`:

```
1. resolve model_id   (default if omitted; validate capabilities vs request, e.g. singing)
2. resolve voice_id    (public_voice_id → Voice)
3. resolve VoiceVariant(voice_id, model_id)
      └─ if missing/stale → onboarding pipeline builds it (or 409/async if not buildable)
4. run inference via the Model's provider
5. emit generation.completed event  → usage metering (Cloud) + royalty accrual (Cloud)
```

The caller never sees variants or artifacts — only `Voice` and `Model`. This is what keeps the
public API stable across model changes.

## 8. Identity, Creator, Marketplace, Monetization (summary)

These contexts are detailed in their own docs; their domain shape:

- **Identity:** `User` (exists) + additive `Role` (`user`/`creator`/`admin`) and tenancy seam.
  CE = one local owner; Cloud resolves the principal via the `AuthProvider` (Clerk) adapter.
- **Creator:** a `User` with a `Creator` profile — display identity, verification status,
  payout identity (Stripe Connect account ref), royalty defaults. Owns Voices.
- **Marketplace:** a `MarketplaceListing` references a `Voice` and adds discovery + pricing +
  preview + stats. See [Marketplace](05-MARKETPLACE_ARCHITECTURE.md).
- **Monetization:** `CreditLedger` (balance per owner), `Transaction` (append-only ledger:
  purchase / consume / royalty_accrual / payout), `Royalty` (per-use accrual to a creator),
  `Payout` (settlement via Stripe Connect). See [Monetization](07-MONETIZATION_ARCHITECTURE.md).

All four are **schema-ready in CE** and **active only in Cloud**.

## 9. Domain events (the seams between contexts)

| Event | Emitted by | Consumed by |
|---|---|---|
| `voice.created` / `voice.published` | Voice / Marketplace | Marketplace, search index |
| `variant.requested` / `variant.ready` / `variant.stale` | Generation / Onboarding | Onboarding, cache |
| `model.updated` | Model Registry | Onboarding (mark variants stale) |
| `generation.completed` | Generation | Metering, Royalties, usage_count |
| `credits.consumed` / `royalty.accrued` | Monetization | Ledger, creator analytics |
| `payout.settled` | Monetization | Creator console, ledger |

In CE these are in-process/no-op; in Cloud they back metering, royalties, and analytics. The
key property: **Generation depends on none of the commercial contexts** — it only emits an
event they may consume.

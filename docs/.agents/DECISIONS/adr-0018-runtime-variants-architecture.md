# ADR-0018: Runtime Variants Architecture

- **Status:** Accepted (architecture only)
- **Date:** 2026-06-11
- **Deciders:** PeakVox architecture (Task 26). This ADR formalizes the
  Runtime → RuntimeVariant split that emerged during validation of the
  Runtime Registry ([ADR-0016](adr-0016-models-as-runtime-services.md),
  [ADR-0017](adr-0017-runtime-services-implementation.md)).
- **Supersedes:** none.
- **Amends:** [ADR-0016 §"Domain boundary (explicit)"](adr-0016-models-as-runtime-services.md)
  — narrows the forbidden pattern `RuntimeVariant` (see
  [Decision → §"Amendment to ADR-0016"](#amendment-to-adr-0016)). ADR-0016
  otherwise stands in full.
- **Superseded by:** none.
- **Spec:** [`../SPECS/FEATURES/runtime-variants/`](../SPECS/FEATURES/runtime-variants/)
- **Migration plan:** [`../IMPLEMENTATION/PLANS/2026-06-11-runtime-variants-migration.md`](../IMPLEMENTATION/PLANS/2026-06-11-runtime-variants-migration.md)
- **Discovery audit:** [`../VALIDATION/AUDITS/runtime-variants-assumptions-audit.md`](../VALIDATION/AUDITS/runtime-variants-assumptions-audit.md)

---

## Context

ADR-0016 established that **PeakVox installs runtimes, not models**, and that
one Model may have many Runtimes (CUDA / CPU / local / cloud). ADR-0017
implemented the descriptor schema (`RuntimeDescriptor`), the file-based
`RuntimeRegistry`, the orchestration-only `RuntimeManager`, the
`RuntimeDriver` seam, and `DockerRuntimeDriver`. That architecture is built
and validated (Kokoro, F5-TTS, OmniVoice runtimes ship today).

During validation of the published `runtime-registry/`, a new limitation
became evident. The current registry collapses several distinct concepts
into a single unit (the runtime directory + image):

- runtime (Python/CUDA environment, service contract)
- model weights / checkpoint
- fine-tune artifacts
- tokenizer + config metadata

These are not the same thing. The clearest live evidence is in the
**catalog itself**: `app/services/model_catalog.py` already defines
variant-family models — `omnivoice-base` **and** `omnivoice-singing`,
`f5-tts-base` **and** `f5-tts-research`, `fish-audio-s2` **and**
`fish-audio-research`. Each of these shares almost all runtime
infrastructure with its sibling. What actually differs between
"F5-TTS Base" and a future "F5-TTS PT-BR" is typically only:

- weights / checkpoint
- config
- tokenizer metadata
- fine-tuning artifacts

The runtime — the image, the Python deps, the CUDA stack, the service
contract — is **identical**.

Yet today, supporting a new model variation requires a **new runtime
folder**, a **new Dockerfile**, a **new image**, a **new build**, and **new
lifecycle management**. The current on-disk shape proves it:

```
runtime-registry/
├── f5-tts-base/        Dockerfile · server.py · descriptor.json · requirements.txt
├── kokoro-82m/         Dockerfile · server.py · descriptor.json · requirements.txt
└── omnivoice-base/     Dockerfile · server.py · descriptor.json · requirements.txt
```

The F5-TTS image is **~12.7 GB** (`f5-tts-base/descriptor.json →
spec.image.image_size_mb: 12697.6`). An F5-TTS PT-BR runtime built the same
way would duplicate all 12.7 GB to change a checkpoint of a few hundred MB.
This produces:

- duplicated images and dependencies
- larger storage usage, longer installs, larger downloads
- unnecessary runtime proliferation

The problem compounds as XTTS variants, F5-TTS variants, OmniVoice variants,
marketplace variants, and community-created variants appear. The immediate
forcing motivation: the user found
[`firstpixel/F5-TTS-pt-br`](https://huggingface.co/firstpixel/F5-TTS-pt-br)
on Hugging Face. It should be installable as **"F5-TTS Runtime + PT-BR
variant"** — a checkpoint download — **without creating a new runtime image**.

### The force in one sentence

> The runtime image is the expensive, slow-changing thing; the checkpoint is
> the cheap, fast-multiplying thing. The registry currently makes you pay the
> runtime cost every time you pay the checkpoint cost.

### Constraint: ADR-0016 forbids `RuntimeVariant`

ADR-0016 §"Domain boundary (explicit)" lists `RuntimeVariant` as a
**forbidden future pattern**. This ADR must therefore either honor that
prohibition or amend it through the documented mechanism (a new ADR that
explicitly names the clause it revises; Constitution Article VII amendment
rule, applied here to an ADR rather than a constitutional article). It does
the latter — narrowly. See [§Amendment to ADR-0016](#amendment-to-adr-0016).
The reason the amendment is sound: ADR-0016's prohibition exists to keep
runtime infrastructure **out of the domain model** (no `*Entity`,
no `*Repository`, no Voice-domain coupling). A RuntimeVariant defined as an
**infrastructure descriptor concept** — a sub-descriptor in the registry,
never persisted as a domain entity, never on the public API — does not
violate that intent. It is the same *kind* of thing as `RuntimeDescriptor`
itself, which ADR-0017 already introduced without becoming a domain entity.

### Constraint: do not collide with VoiceVariant

`VoiceVariant` is a load-bearing domain concept (ADR-0001, ADR-0004,
ADR-0008, ADR-0009). The Runtime Service Contract already carries a
`variant_id` field on `POST /v1/generate` — **that is the VoiceVariant**
(`runtime-registry/f5-tts-base/server.py` `GenerateRequest.variant_id`).
The new concept must be named and routed so it is impossible to confuse the
two. See [§The two "variants" are different domains](#the-two-variants-are-different-domains).

---

## The two "variants" are different domains

| | **VoiceVariant** (existing) | **RuntimeVariant** (new) |
|---|---|---|
| Definition | Voice × Model realization | Runtime × Checkpoint realization |
| Domain | **Voice domain** (ADR-0001/0004) | **Runtime infrastructure** (ADR-0016/0017) |
| Identity | `public_voice_id` + model | runtime id + variant id |
| Persisted? | Yes — `voice_variants`, `voice_variant_artifacts` | **No** — registry descriptor file |
| Public API? | Never exposed directly (ADR-0004 §6); the Voice is | **Never** — internal infrastructure |
| Owns | embeddings / refs / speaker artifacts for **one voice** | checkpoint / weights / config / tokenizer for **one model build** |
| Built by | `PeakVoxRuntime.ensure_variant` (ADR-0008) | runtime image build (CE) / checkpoint download (variant add) |
| Versioned by | `VoiceVariantArtifact` (ADR-0009) | runtime checkpoint versioning (this ADR, §Cloud) |
| Lives at generation as | `variant_id` on `POST /v1/generate` | (proposed) `runtime_variant` on `POST /v1/generate` |

**One-line mnemonic, extending ADR-0016's final statement:**

> Voices are assets. Models are engines. **Runtimes are infrastructure;
> RuntimeVariants are the interchangeable weights that infrastructure loads.**
> Adapters are translators. The Runtime is orchestration.

These two never share a table, a type, a repository, or an API field name.

---

## The three infrastructure axes (the conceptual core)

ADR-0016 named two axes. This ADR adds the third and names all three so they
never blur again:

```
Axis 1 — Model        the WHAT     domain/catalog entity, public, has ModelCapabilities (ADR-0002/0003)
Axis 2 — Runtime      the HOW       image + Python/CUDA env + service contract       (ADR-0016/0017)
                                    └─ ADR-0016's substrate variation (CUDA/CPU/cloud) lives here
Axis 3 — RuntimeVariant  the WHICH-WEIGHTS   checkpoint + config + tokenizer inside a Runtime   (THIS ADR)
```

Axis 2 (Runtime, substrate) and Axis 3 (RuntimeVariant, weights) are
**orthogonal**, exactly as Creation Source and Variant are orthogonal in the
Voice domain (ADR-0011). A single Runtime image (say `peakvox/f5-tts-runtime`)
can be deployed on CUDA **or** CPU (Axis 2) **and** load Base, PT-BR, or
Narrator weights (Axis 3) — four combinations, one image.

### Domain model: before and after

```
BEFORE (ADR-0016/0017)                AFTER (ADR-0018)
─────────────────────                 ────────────────
Runtime                               Runtime
 └── Docker Image                      ├── Docker Image
     (weights baked or                 ├── service contract
      downloaded at boot)              ├── RuntimeVariant ── checkpoint A
                                       ├── RuntimeVariant ── checkpoint B
                                       └── RuntimeVariant ── checkpoint C

The Runtime owns:                      A RuntimeVariant owns:
 - dependencies                         - checkpoint / weights
 - Python environment                   - config
 - CUDA environment                     - tokenizer
 - service contract                     - metadata
 - API surface                          - (Cloud) licensing / edition scope
```

### Worked example

```
Runtime: F5-TTS  (image: peakvox/f5-tts-runtime, 12.7 GB, built/pulled ONCE)
├── RuntimeVariant: base        (checkpoint: SWivid/F5-TTS, default)
├── RuntimeVariant: pt-br       (checkpoint: firstpixel/F5-TTS-pt-br)   ← HF import, no rebuild
├── RuntimeVariant: narrator    (checkpoint: marketplace/...)
└── RuntimeVariant: user-import (checkpoint: local upload)

Runtime: OmniVoice  (image: peakvox/omnivoice-runtime, 8.7 GB, built/pulled ONCE)
├── RuntimeVariant: base        (default)
└── RuntimeVariant: singing
```

Storage: **one** 12.7 GB image + N small checkpoints, instead of **N ×
12.7 GB** images.

---

## How RuntimeVariant relates to the Model (the load-bearing decision)

This is the decision that keeps the public contract stable. There are two
candidate bindings; we choose the first and document the second as a
deliberately deferred future.

### Decision: a RuntimeVariant realizes a *model binding*; the Model stays the public selector

Each RuntimeVariant declares its own `model_binding.model_id`. The **catalog
Model remains the public "what"** the API and UI select. Variant-family
models (`omnivoice-singing`, a future `f5-tts-pt-br`) remain **distinct
catalog Models** — which are cheap rows in the `models` table (ADR-0002), not
expensive images — but they are **served by RuntimeVariants of a shared
Runtime image** instead of by separate runtime images.

Consequences of this binding:

- **Public API is unchanged.** Generation stays `voice + model + text`
  (Constitution Article I §2, III, VIII §26). `model_id` continues to resolve
  to a runtime endpoint via `RuntimeManager.resolve(model_id)`; resolution
  additionally selects the RuntimeVariant the chosen model maps to.
- **Domain is unchanged.** `VoiceVariant = Voice × Model` still holds; the
  Active Artifact step (ADR-0009) is preserved and may not be bypassed.
- **Capabilities stay per-Model and declared, not inferred** (ADR-0003). A
  PT-BR variant-model declares its own `ModelCapabilities`; the UI renders
  controls from those, never from the variant name.
- **The only thing that changes is infrastructure**: the registry gains a
  Runtime → RuntimeVariant layer so multiple model bindings share one image
  and differ only by checkpoint. This is precisely the stated pain, and only
  that.

### Deferred alternative: variant as a first-class generation selector

The Task 26 UI sketch shows `Model: F5-TTS` + `Variant: PT-BR` as two
selectors. Exposing `runtime_variant` as a **public generation dimension**
(`voice + model + variant + text`) is a real option, but it changes the
public `/api/v1` contract and therefore requires a `/v2` and a deprecation
policy (Constitution Article VIII §26). We **defer** it.

Crucially, the desired UX is achievable **without** the API change: the UI
may **group/present** catalog models by runtime family and render variant
chips, where each chip simply resolves to a `model_id`. "Model: F5-TTS /
Variant: PT-BR" in the UI sends `model_id = f5-tts-pt-br` on the wire. UI
grouping ≠ API dimension. See [§UX implications](#ux-implications).

---

## Storage model

### On-disk registry (target)

```
runtime-registry/
├── f5-tts/
│   ├── Dockerfile
│   ├── server.py
│   ├── requirements.txt
│   ├── descriptor.json            ← kind: Runtime
│   └── variants/
│       ├── base.json              ← kind: RuntimeVariant
│       ├── pt-br.json
│       └── narrator.json
├── omnivoice/
│   ├── Dockerfile
│   ├── server.py
│   ├── descriptor.json
│   └── variants/
│       ├── base.json
│       └── singing.json
└── kokoro/
    ├── …
    └── variants/
        └── base.json
```

A runtime directory with **no** `variants/` folder is still valid: it is a
runtime with a single implicit `base` variant (this is what `f5-tts-base/`
is today — see [§Migration](#migration-strategy-additive-and-reversible) for
why renaming is deferred).

### Weights cache (runtime, shared)

Checkpoints are **not** baked into images going forward. They are downloaded
into a shared, named volume that already exists in the driver
(`DockerRuntimeDriver._data_volume_mounts` re-uses the backend's `/data`
named volume for every runtime container):

```
/data/runtime-weights/<runtime_id>/<variant_id>/   ← checkpoint, config, tokenizer
```

- The image build is paid **once per runtime**.
- A variant add downloads **only** the checkpoint into the cache.
- Multiple runtime containers (CUDA/CPU) of the same runtime share the same
  cache by `runtime_id`.

### Storage savings (illustrative, F5-TTS)

| Scenario | Today (runtime-per-variant) | ADR-0018 (variant-per-runtime) |
|---|---|---|
| Base only | 12.7 GB | 12.7 GB |
| Base + PT-BR | 25.4 GB | 12.7 GB + ~0.5 GB |
| Base + PT-BR + Narrator | 38.1 GB | 12.7 GB + ~1.0 GB |
| Base + 5 community variants | 76.2 GB | 12.7 GB + ~2.5 GB |

---

## Runtime Service Contract evolution

The contract (ADR-0017 §6) gains variant awareness. All additions are
backward compatible; a runtime that ignores variants behaves exactly as
today (single `base`).

### New / changed endpoints

| Endpoint | Change |
|---|---|
| `GET /v1/metadata` | adds `variants: [{id, name, default, loaded, checkpoint_ref, capabilities}]` and `loaded_variant` |
| `GET /v1/variants` | **new** — list installed variants + load state |
| `POST /v1/variants/load` | **new** — `{variant_id}` → ensure checkpoint resident; warm a variant without restart |
| `POST /v1/generate` | adds optional `runtime_variant` selector (distinct from the existing `variant_id`, which remains the **VoiceVariant**) |
| `POST /v1/variants/build` | unchanged — this is the **VoiceVariant** build path (ADR-0008), not RuntimeVariant. **Do not overload it.** |

> **Naming guard.** `variant_id` on `/v1/generate` = VoiceVariant (voice
> realization). `runtime_variant` = RuntimeVariant (checkpoint). The two
> fields coexist and mean different things. Reviewers must reject any PR that
> conflates them.

### In-process variant switching (no container restart)

Today `server.py` lazy-loads one model singleton (`_load_state:
unloaded → loading → ready → failed`, guarded by `_load_lock`). The variant
model generalizes this to a **keyed, LRU-bounded registry of loaded
checkpoints**:

```
_variants: dict[variant_id -> LoadedCheckpoint]   # bounded by VRAM/RAM budget (LRU)
_default_variant_id: str                           # eager-loaded on /ready

load_variant(variant_id):
    if variant_id in _variants: return            # already resident
    ckpt = resolve_checkpoint(variant_id)          # /data/runtime-weights/<rt>/<variant>/
    evict_lru_if_over_budget()
    _variants[variant_id] = load(ckpt)             # under _load_lock

generate(req):
    vid = req.runtime_variant or _default_variant_id
    load_variant(vid)                              # idempotent, on demand
    return _variants[vid].infer(req)
```

Goal achieved: **switching variants requires neither container recreation,
runtime reinstall, nor image rebuild** — only an on-demand checkpoint load
(and, for a cold variant, a one-time download). Readiness (`/ready`) means
"the default variant is loaded"; a non-default variant load is reported via
`/v1/variants`.

> **Note for F5-TTS specifically:** the runtime serializes inference behind a
> module-level lock and clears the DiT text-embed cache per call (commit
> `0370ddd`, Task 24). Variant switching must respect that lock and clear the
> cache on variant change; the LRU must not hold two variants live during a
> single inference. This is called out in the migration plan, Phase 4.

---

## Community Edition implications

The CE north star from Task 26:

```
Install Runtime          → build/pull the runtime image ONCE
   ↓
Add Variant              → download checkpoint only (no Docker)
   ↓
Use Variant              → generate, no rebuild
```

- CE keeps `DockerRuntimeDriver`. Installing a runtime is unchanged
  (`build-on-install` / `pull-on-install`).
- "Add Variant" is a **new lifecycle operation that touches no image**: it
  validates the checkpoint source, downloads to the weights cache, writes a
  `variants/<id>.json` descriptor, and (optionally) seeds a catalog Model row.
- Commercial concepts stay schema-ready but inert in CE (Constitution Article
  V §15): a RuntimeVariant descriptor carries optional licensing/edition
  fields that CE leaves empty.

---

## Cloud implications

- **Checkpoint versioning & retention.** RuntimeVariant checkpoints are
  versioned and retained in Cloud, mirroring the *shape* of ADR-0009 artifact
  versioning — but they are a **separate concern** from `VoiceVariantArtifact`
  and must not reuse that table or type. (A future ADR specifies the Cloud
  checkpoint store; CE keeps the latest checkpoint per variant.)
- **Edition & licensing scoping.** A variant's availability is a declared
  property (extends ADR-0005's edition scoping to the variant granularity): a
  marketplace variant may be `cloud`-only or license-gated while its runtime
  is `["ce","cloud"]`.
- **Autoscaling.** The Kubernetes driver (future) can pin hot variants to warm
  pools and treat `load_variant` as a pool-warm signal; idle variants evict
  from VRAM via the same LRU, independent of container lifecycle.
- **Marketplace.** Community/marketplace variants are registry artifacts
  (checkpoint + descriptor), published once, consumed everywhere — the voice
  marketplace's runtime-side analogue.

---

## Hugging Face variant import flow

```
Add Variant
   ↓  paste HuggingFace URL (e.g. firstpixel/F5-TTS-pt-br)
Validate          → provider/arch compatibility with the target Runtime
   ↓                 (does this checkpoint fit peakvox/f5-tts-runtime?)
Download weights  → /data/runtime-weights/f5-tts/pt-br/
   ↓
Register RuntimeVariant   → runtime-registry/f5-tts/variants/pt-br.json
   ↓                        (+ optional catalog Model row: f5-tts-pt-br)
Available for generation   → model select shows it; no Docker build, no image dup
```

Validation gates (Phase 6 of the migration plan): the import is **rejected**
if the checkpoint's declared architecture/provider is not compatible with the
runtime's `provider`/`model_family` labels, or if its declared capabilities
exceed the runtime's. Compatibility is **declared and checked**, never
inferred from the repo name (ADR-0003 discipline applied to checkpoints).

---

## UX implications

Current Models page: one card per catalog model, each joined to its runtimes
(`GET /api/models/with-runtimes`). F5-TTS Base, F5-TTS PT-BR, F5-TTS Narrator
would each render as a **separate top-level card** today.

Target presentation (no API contract change — pure grouping):

```
Models
└── F5-TTS                         ← grouped by runtime family (provider/runtime id)
    Runtime    ✓ Installed         ← single runtime install state
    Variants
      ✓ Base                       ← installed RuntimeVariants
      ✓ PT-BR
      ○ Narrator   [Add]           ← available, not yet downloaded

Generation
  Model:   F5-TTS                  ← UI label
  Variant: PT-BR                   ← chip; resolves to model_id on the wire
```

- The runtime install/start/stop controls move to the **family** (runtime)
  level; variant chips have their own lightweight Add/Remove (download/delete
  checkpoint), never an image build.
- Capability-driven controls (ADR-0003, `frontend/AGENTS.md` rule 3) read the
  **selected variant-model's** `ModelCapabilities`. Selecting a different
  variant may change which controls render (e.g. a singing variant exposes
  singing controls) — still capability-driven, never name-driven.
- No model internals (checkpoints, weights, formats) surface in the UI
  (ADR-0004 §6, `frontend/AGENTS.md` rule 2). A variant shows a name, a state,
  and declared capabilities — never a checkpoint path or tensor format.

---

## Amendment to ADR-0016

ADR-0016 §"Domain boundary (explicit)" reads:

> **Forbidden future patterns:** `RuntimeServiceEntity`,
> `RuntimeServiceRepository`, `RuntimeVariant`, `RuntimeArtifact`, Any
> `*Entity` / `*Repository` that names a runtime concept.

**This ADR narrows the `RuntimeVariant` entry** as follows (all other entries
stand unchanged):

> `RuntimeVariant` is permitted **only** as an *infrastructure descriptor
> concept* in the Runtime Registry — a sub-descriptor of a `Runtime`,
> parallel to `RuntimeDescriptor`. It remains forbidden as a **domain entity**
> or **persisted domain row** and forbidden to acquire a `*Repository`. It
> must never appear on the public `/api/v1` surface, never reference Voice /
> VoiceVariant / VoiceVariantArtifact, and never be confused with
> `VoiceVariant`. `RuntimeArtifact` (a runtime checkpoint *version* record, a
> Cloud concern) remains reserved to a future ADR and is **not** introduced
> here.

Rationale: the prohibition's purpose — keep runtime infrastructure out of the
domain model — is fully preserved. The amendment only acknowledges that a
descriptor-level RuntimeVariant is the same category of thing as
`RuntimeDescriptor`, which ADR-0017 already shipped as infrastructure without
domain coupling.

ADR-0016's "Architectural invariants" 1–12 all continue to hold. In
particular: invariant 11 ("runtime infrastructure is not a domain concept")
and invariant 12 ("Active Artifact resolution is preserved") are unaffected.

---

## Options considered

### Option A — Keep runtime-per-variant; accept duplication

Status quo. Each model variation gets its own runtime directory + image.

- **Pros:** zero new concepts; nothing to amend; total isolation.
- **Cons:** N × image size; slow installs; huge downloads; runtime
  proliferation; makes HF imports and a marketplace economically absurd
  (every community fine-tune is a 12.7 GB image). Directly blocks the Task 26
  goal.
- **Rejected.**

### Option B — Bake all variants into one fat image

Ship one F5-TTS image containing base + PT-BR + narrator checkpoints.

- **Pros:** one image; no new registry concept.
- **Cons:** image grows without bound; every new community variant requires a
  rebuild + redeploy of a multi-GB image; can't add a variant at runtime; no
  per-variant licensing; defeats CE "Add Variant without Docker." 
- **Rejected.**

### Option C — RuntimeVariant as a domain entity (`runtime_variants` table + repository)

Persist variants as first-class domain rows with a repository.

- **Pros:** queryable; familiar CRUD.
- **Cons:** **violates ADR-0016** invariant 11 and the (un-amended)
  forbidden-pattern list in spirit and letter; pollutes the domain with
  infrastructure; risks colliding with VoiceVariant; over-engineers CE (a
  file descriptor is enough).
- **Rejected.**

### Option D — RuntimeVariant as an infrastructure descriptor; Model stays the public selector (chosen)

Variants are `variants/*.json` sub-descriptors in the registry; checkpoints
download to a shared cache; the runtime service loads them on demand; the
catalog Model remains the public selector.

- **Pros:** solves the exact stated pain (image duplication) and nothing else;
  public API and domain unchanged; honors ADR-0016 intent with a minimal,
  documented amendment; enables CE "Add Variant," HF imports, and a variant
  marketplace; additive and reversible migration.
- **Cons:** introduces a new (infrastructure-only) concept and a registry
  layer; runtime service must manage multiple loaded checkpoints (LRU); a
  narrow ADR-0016 amendment is required.
- **Chosen.**

---

## Decision

PeakVox adopts **Option D**. The Runtime Registry evolves from
**runtime-per-variant** to **runtime + RuntimeVariants**:

1. **`RuntimeVariant` is an infrastructure descriptor concept** — a
   sub-descriptor of a `Runtime`, stored as `runtime-registry/<runtime>/variants/<id>.json`,
   `kind: RuntimeVariant`. It is never a domain entity, never persisted as a
   domain row, never on the public API, and never named or shaped like
   `VoiceVariant`.
2. **A Runtime owns** the image, Python/CUDA environment, service contract,
   and API surface. **A RuntimeVariant owns** a checkpoint, config, tokenizer,
   and metadata.
3. **Checkpoints are not baked into images.** They download to a shared
   weights cache (`/data/runtime-weights/<runtime>/<variant>/`). The image is
   paid once per runtime; a variant add downloads only the checkpoint.
4. **The catalog Model remains the public selector.** Generation stays
   `voice + model + text`. Each RuntimeVariant declares a `model_binding`;
   `RuntimeManager.resolve(model_id)` selects the runtime **and** the variant.
5. **The Runtime Service Contract gains variant awareness** (`/v1/variants`,
   `/v1/variants/load`, `runtime_variant` on `/v1/generate`, variants in
   `/v1/metadata`) with in-process, restart-free variant switching. The
   existing `variant_id` (VoiceVariant) and `/v1/variants/build` (VoiceVariant
   build) are untouched.
6. **ADR-0016's forbidden-pattern entry for `RuntimeVariant` is narrowed** as
   specified above; all other ADR-0016 decisions and invariants stand.

This ADR is **architecture only** — it changes no behavior on its own. The
sole code introduced alongside it is a **non-wired, additive descriptor
primitive** (`RuntimeVariantDescriptor` + optional `variants/` loader
support) with tests, which no resolution or lifecycle path reads yet. See the
[migration plan](../IMPLEMENTATION/PLANS/2026-06-11-runtime-variants-migration.md)
for the phased rollout (Phases 1–6).

---

## Consequences

### Positive

- **Storage collapses** from N × image to 1 image + N checkpoints.
- **CE "Add Variant" without Docker** becomes possible.
- **HF imports** become a checkpoint download + descriptor registration.
- **A variant marketplace** becomes economically viable (publish a checkpoint,
  not a 12.7 GB image).
- **Public API and Voice domain are untouched** — Constitution Articles I, II,
  III, VIII preserved.
- **No VoiceVariant collision** — the two are kept rigorously distinct.
- **Additive, reversible migration** — today's runtimes keep working as
  single-`base` runtimes.

### Negative / costs

- A new infrastructure concept + registry layer to maintain.
- The runtime service must manage multiple loaded checkpoints (LRU, VRAM
  budget, F5's serialization/cache constraints).
- A narrow ADR-0016 amendment (documented here).
- Variant-family models still need a catalog Model row each (cheap, but a
  step in "Add Variant").

### Follow-ups / what this enables or forecloses

- **Enables:** F5-TTS PT-BR / Narrator, OmniVoice Singing, XTTS fine-tunes,
  marketplace variants, and user-imported variants — all without duplicating
  images.
- **Reserves:** `RuntimeArtifact` (Cloud checkpoint *version* record) to a
  future ADR; the first-class `runtime_variant` **public** generation selector
  (would need `/api/v2`, Article VIII).
- **Forecloses:** baking checkpoints into images as the standard pattern after
  Phase 2; runtime-per-variant as the way to add a fine-tune.

---

**Related:** [ADR-0016](adr-0016-models-as-runtime-services.md) ·
[ADR-0017](adr-0017-runtime-services-implementation.md) ·
[ADR-0002](adr-0002-model-as-first-class-entity.md) ·
[ADR-0003](adr-0003-model-capability-contract.md) ·
[ADR-0005](adr-0005-edition-scoped-model-availability.md) ·
[ADR-0009](adr-0009-artifact-versioning-and-retention.md) ·
[`../CONSTITUTION.md`](../CONSTITUTION.md) ·
[`../SPECS/FEATURES/runtime-variants/`](../SPECS/FEATURES/runtime-variants/) ·
[`../IMPLEMENTATION/PLANS/2026-06-11-runtime-variants-migration.md`](../IMPLEMENTATION/PLANS/2026-06-11-runtime-variants-migration.md)

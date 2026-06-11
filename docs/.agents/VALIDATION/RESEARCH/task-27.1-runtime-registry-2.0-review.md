# Task 27.1 — Runtime Registry 2.0 Review & Refinement

> **Date:** 2026-06-11 · **Author:** Task 27.1 · **Type:** Review + roadmap (additive impl only)
> **Builds on:** [Task 27 audit](../AUDITS/task-27-runtime-variants-audit.md),
> [Task 27 findings](./task-27-model-ecosystem-findings.md),
> [ADR-0018](../../DECISIONS/adr-0018-runtime-variants-architecture.md),
> [ADR-0019](../../DECISIONS/adr-0019-variant-trust-and-community-imports.md)

This review answers: is the RuntimeVariant implementation complete, does the
**physical** registry still carry legacy assumptions, and what is **Runtime
Registry 2.0**? It implements only the safe, additive slice (the `private` trust
tier); the disruptive directory migration is roadmapped, not executed.

---

## Phase A — Audit of the current implementation

### What is implemented correctly

| Area | State | Evidence |
|---|---|---|
| RuntimeVariant schema | Complete, disjoint from VoiceVariant | `runtime_types.py::RuntimeVariantDescriptor` (+ `RuntimeCheckpoint`, trust) |
| Registry index | Complete | `runtime_registry.py::list_variants_for_runtime/get_variant/select_variant` |
| Resolution wiring (Phase 1) | Complete, additive | `RuntimeResolution.runtime_variant_id`; implicit-base = `None` |
| Concrete variants on disk | Present | `runtime-registry/*/variants/base.json` (all 3 runtimes) |
| Composed API | Complete, public-safe | `/models/with-runtimes` `variants[]` (no checkpoint internals) |
| Import **validate** | Complete, network-free | `runtime_variant_import.py` + `POST …/variants/validate-import` |
| Trust (verified/community) | Complete | `trust` field + UI badges + forced-community on import |
| Frontend variant workflow | Complete (view/inspect/badges/import-validate) | `VariantsSection.tsx` + capability picker |

### What remains transitional / coupled to the legacy structure

1. **Directory naming still encodes `Runtime ≈ Variant`.** `omnivoice-base/`,
   `f5-tts-base/`, `kokoro-82m/` — the `-base` / `-82m` suffix is a *variant/size*
   label baked into the *runtime* directory. The domain says Runtime + Variants;
   the folder still says "the base runtime."
2. **`metadata.id` carries the same suffix** (`omnivoice-base`, `kokoro-base`
   model id). The runtime *identity* still reads like a single variant.
3. **Only `base` variants exist.** The N-variants-per-runtime capability is real
   in code but unexercised on disk (no `singing.json` / `pt-br.json` shipped).
4. **Import stops at validate.** Download + register + load are not built
   (require the multi-checkpoint runtime service, migration Phase 4).
5. **Weights still bundle/boot-download per image.** The shared
   `/data/runtime-weights/<rt>/<variant>/` cache the schema implies is not yet
   the storage path; base weights still come via `HF_HOME=/data/hf-cache` on
   first inference.

### The load-bearing discovery

**The loader indexes runtimes by `descriptor.metadata.id`, not by directory
name** (`runtime_registry.py:184-204`; variants are matched by
`runtime_id == metadata.id`). Consequences:

- **Renaming a directory `omnivoice-base/ → omnivoice/` is a no-op to identity**
  as long as `metadata.id` is unchanged. The loader never reads the folder name.
- The genuinely breaking change is renaming **`metadata.id`** — it is the install
  key, the container name (`peakvox-runtime-<id>`), the image-label join, and the
  frontend's runtime id. *That* needs an alias window.

This means Registry 2.0's directory layout can be adopted **safely and
additively**; only the id rename is disruptive.

### Verdict

The RuntimeVariant **domain** is implemented and correct. The **physical
registry** is transitional: directory + id naming still reflect the pre-variant
world, and the variant lifecycle (download/register/load) is unbuilt. No drift,
no incorrectness — just an unfinished migration, exactly as Task 27 scoped it.

---

## Phase B — Runtime Registry 2.0 target structure

**Decision: yes, adopt the family-directory layout as the official target.**

```
runtime-registry/
├── omnivoice/                 # directory = runtime FAMILY (provider/engine)
│   ├── descriptor.json        #   the Runtime (image, service, requirements)
│   ├── Dockerfile             #   one image for the whole family
│   ├── server.py              #   one runtime service hosting many checkpoints
│   └── variants/              #   the RuntimeVariants (checkpoints)
│       ├── base.json
│       ├── singing.json
│       └── narrator.json
├── f5-tts/
│   ├── … + variants/{base,pt-br,narrator,expressive}.json
└── kokoro/
    └── … + variants/{base,multilingual}.json
```

| | Pros | Cons |
|---|---|---|
| Family directory | one image/Dockerfile/server per engine; N variants = N small JSON; mirrors the domain; "Add variant" is a file, not a folder | requires renaming dirs + ids (one-time) |
| Status-quo `*-base/` | already shipped; zero migration | misnames runtime as variant; implies one image per variant |

**Migration complexity: Low–Medium, and stageable** because the loader is
directory-name-agnostic:

1. **Stage 1 (safe, additive).** Rename directories `omnivoice-base/ → omnivoice/`
   etc. **keeping `metadata.id` unchanged**. Loader behavior is identical; only
   the on-disk folder reads correctly. Add a `runtime_family` label.
2. **Stage 2 (id alias window).** Introduce new ids (`omnivoice`) while the
   registry **aliases** the old id (`omnivoice-base`) for one release: index the
   runtime under both, so installed containers + frontend keep resolving. Catalog
   model ids (`omnivoice-base`) move to a `base` variant binding.
3. **Stage 3 (cutover).** Drop the alias; old ids gone.

**Backward compatibility:** Stage 1 is invisible to running systems. Stage 2
preserves `/api/v1` and installed containers via aliasing. Stage 3 is the only
breaking step and is gated on a release boundary + deprecation note.

**Future scalability:** adding the 50th community F5-TTS variant is one
`variants/<id>.json` (or a registered row) — never a new directory, image, or
container. This is the whole point.

**This task ships none of the rename** (it touches install/identity paths and
wants validation under a real install). It ships the *roadmap* + the additive
`private` tier. Stage 1 is the recommended next PR.

---

## Phase C — Download + Register architecture

Current: **validate only.** Target flow:

```
Paste HF URL → validate (done) → download → register → available for generation
            (no Docker rebuild, no runtime duplication, no new image)
```

### Storage layout

Reuse the **already-shared `/data` named volume** (the backend and every runtime
container mount it; `docker_runtime_driver.py::_data_volume_mounts`,
`HF_HOME=/data/hf-cache`). Variant checkpoints live at:

```
/data/runtime-variants/<runtime_id>/<variant_id>/
    checkpoint/            # weights (safetensors/…), config, tokenizer
    variant.json           # the RuntimeVariantDescriptor (registered copy)
    .meta.json             # provenance: source_url, digest, size, imported_at, trust
```

(`/data/runtime-variants/` chosen over `/data/runtime-weights/` from earlier
drafts — "variants" matches the domain noun and keeps it distinct from the raw
`/data/hf-cache` HF blob cache.)

### Metadata layout

- The **registered descriptor** is written to
  `runtime-registry/<rt>/variants/<id>.json` (Stage-1 layout) *or*, for
  user/private imports that must not pollute the read-only shipped registry, to
  `/data/runtime-variants/<rt>/<id>/variant.json` and merged by the loader from
  **two roots**: the shipped `runtime-registry/` (read-only, verified) and a
  writable `/data/runtime-variants/` overlay (community/private). This two-root
  load is the key additive change that unlocks user imports without writing into
  the shipped tree.
- `.meta.json` holds non-descriptor provenance (digest, byte size, timestamp,
  importing user) for cleanup/versioning.

### Lifecycle ownership

| Step | Owner | Why |
|---|---|---|
| validate | backend (`runtime_variant_import`) | pure, network-free, no framework |
| download | **runtime container** | has the framework, GPU, HF token, `/data` mount; backend stays framework-free (ADR-0016/0017) |
| register | backend | writes the descriptor to the writable overlay + refreshes the registry index |
| load/switch | runtime service (`server.py`) | multi-checkpoint host (migration Phase 4) |

Progress is surfaced through a new `variant_add` / `variant_remove`
`RuntimeOperation`, mirroring install/start.

### Cleanup strategy

- **Remove variant** → delete `/data/runtime-variants/<rt>/<id>/` + overlay
  descriptor + evict from the runtime service LRU. Never touches the image.
- **Orphan GC**: a variant whose runtime is removed is tombstoned; a periodic
  sweep deletes directories with no descriptor (or no runtime).
- **Cache vs variant**: `/data/hf-cache` (raw HF blobs) may be GC'd freely;
  `/data/runtime-variants/` is authoritative and only deleted on explicit remove.

### Versioning strategy

- Variant identity = `(runtime_id, variant_id)`. Re-importing the same id with a
  new checkpoint writes `checkpoint/` under a content digest and updates
  `.meta.json.digest`; keep the previous digest dir for rollback (bounded, e.g.
  last 2), mirroring `VoiceVariantArtifact` retention (ADR-0009) **without**
  reusing that domain table — a future `RuntimeVariantArtifact` (Cloud) formalizes
  it. CE keeps it filesystem-simple.

---

## Phase D — Trust model evolution: add `private`

**Decision: yes — `verified | community | private` becomes the trust vocabulary.**

| Tier | Meaning | Source | Audited | Visibility |
|---|---|---|---|---|
| `verified` | PeakVox-audited, official, supported | shipped registry | yes | everyone |
| `community` | imported from a public source (HF) | public URL | no | the deploying user |
| `private` | user-owned, local, not public | local/private import | no | owner only |

**Why `private` is needed:** `community` conflates "public but unaudited" with
"my own local checkpoint I never want published." A creator fine-tuning a voice
model locally, or an enterprise with a proprietary checkpoint, needs a tier that
(a) is never a marketplace-publish candidate and (b) signals "do not share."

### Implications

- **UX:** a third badge — neutral/lock styling (vs green ✓ verified, amber ⚠
  community). "Private" reads as ownership, not danger.
- **Registry:** `private` variants live only in the writable `/data` overlay,
  never in the shipped `runtime-registry/` tree, and are excluded from any
  export/publish path.
- **Resolution:** trust is **provenance only — it never changes selection**.
  `select_variant` ignores trust; a private variant resolves exactly like any
  other for *its* owner. (Keeps Constitution II/VIII intact.)
- **Marketplace (Cloud):** `verified`/`community` may be publishable under policy;
  `private` is **never** publishable — it is the explicit opt-out. This makes
  `trust` the single field governing publish eligibility.

This task **implements** the schema + UI + tests for `private` (additive,
default still `verified`). See Phase H.

---

## Phase E — Generic model import (LM Studio / Ollama style)

**Feasibility: yes, per-runtime-family — confirmed and unchanged from Task 27
findings (Phase E there).** Restated for Registry 2.0:

- The Ollama analogy holds *within* a family: `f5-tts` is "the loader," and any
  compatible F5 checkpoint imports onto it. It does **not** hold across families
  (no universal voice loader exists).
- **Flow:** `Runtime (installed) → Import Variant (HF/local) → validate → download
  → register → generate`. PeakVox does **not** pre-register the variant; the user
  imports it onto an existing runtime. This is exactly the Phase C pipeline.
- **Architecture impact:** the two-root loader (shipped read-only + `/data`
  writable overlay) is the enabling change; everything else already exists.
- **Security:** downloads run in the sandboxed runtime container, not the
  backend; validate gates provider/family/capability before any byte is fetched;
  HF token scoping already wired. Untrusted checkpoints are `community`/`private`,
  never `verified`. Recommend an allowlist of sources in Cloud policy.
- **Licensing:** capture the HF card `license:` into `.meta.json`; surface it on
  the variant; block publish of incompatible licenses in the marketplace (Cloud).
- **Capability discovery:** declared-and-checked (ADR-0003); a probe may
  *pre-fill* from `pipeline_tag`/`language` but never *grant* — see Task 27
  findings Phase G.

**Verdict:** Runtime Registry 2.0 + the two-root loader makes the LM-Studio-style
CE workflow reachable additively. No blocker.

---

## Phase F — Shared runtime base image

**Feasibility: high; recommended; not implemented here (no disruptive Docker
migration).** Restated/sharpened from Task 27 findings Phase F.

```
peakvox/runtime-base:cuda12.8-torch2.8   # Python + CUDA + matched torch stack +
                                         # huggingface_hub + shared lifecycle tooling
  ├── FROM → omnivoice/Dockerfile
  ├── FROM → f5-tts/Dockerfile
  └── FROM → (future) xtts/Dockerfile
```

| Dimension | Impact |
|---|---|
| Image size | The multi-GB CUDA+torch layer is **shared on disk** across all runtimes (Docker layer dedupe) — pull/build once. Per-runtime images shrink to their framework + server. |
| Cache efficiency | Base layer cached once; rebuilding a runtime reuses it; CI builds drop dramatically. |
| Build efficiency | Each runtime Dockerfile becomes ~5 lines (FROM base + pip the engine + COPY server.py). |
| Maintenance | The CUDA/torch ABI pin (the exact thing the OmniVoice hotfix fought) lives in **one** place — fix once, inherit everywhere. |
| CE implications | Faster, smaller installs; the base pulls once and every subsequent runtime install is small. Pure win. |

**Recommendation:** build `peakvox/runtime-base` as the **first concrete image
change** of Registry 2.0 Stage 1 (it pairs naturally with the directory rename).
Pin the exact stack the OmniVoice hotfix validated
(`pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime`). Low risk; reversible per
runtime (a runtime can keep its own `FROM` until ported).

---

## Phase G — Frontend evolution

Current: variants render **inside** the runtime card (good). Registry 2.0 should
make the **family + variant tree** the primary mental model:

```
Models
└── F5-TTS                         ← family card (one image, one lifecycle)
    Runtime: ● Active
    Variants
      ✓ Base        Verified ★
      ✓ PT-BR       Community   huggingface.co/firstpixel/F5-TTS-pt-br
      ○ Narrator    Community   (available — not installed)
      🔒 My-Voice   Private
    [ + Add variant ]
```

Recommendations (additive, mostly already in place):

1. **Family grouping** — collapse `*-base` aliases into one family header once
   Stage 2 lands (presentation only).
2. **Installed vs Available** — once download/register ships, variants gain an
   install state: `✓ installed` / `○ available` with Add/Remove per variant
   (the chip already exists; add the state + actions).
3. **Trust visibility** — three badges (verified ✓ / community ⚠ / private 🔒);
   shipped in Phase H for the badge, full tri-state once `private` data flows.
4. **Discoverability** — a variant count + a "Browse compatible models" entry
   (Cloud marketplace / curated HF list) on the family card.
5. **Scalability** — virtualize/scroll the variant list when a family has many
   (community-heavy F5-TTS); keep the default + installed pinned to top.
6. **Capability picker** (shipped) already prevents vocabulary errors on import.

No redesign required — Registry 2.0 is an **additive elaboration** of the current
card, not a new IA.

---

## Migration roadmap (Runtime Registry 2.0)

| Stage | Scope | Risk | Breaking? |
|---|---|---|---|
| **0 (done)** | Schema, resolution, validate, trust(2), variant chips | — | no |
| **0.1 (this task)** | `private` trust tier (schema+UI+tests); review+roadmap | Low | no |
| **1** | `peakvox/runtime-base` image; rename dirs → family (keep `metadata.id`); `runtime_family` label; ship a real 2nd variant (e.g. omnivoice `singing.json`) | Low | no |
| **2** | Two-root loader (shipped read-only + `/data` writable overlay); id-alias window | Medium | no (aliased) |
| **3** | Download + register pipeline (runtime-container download, backend register, `variant_add` op) | Medium | no |
| **4** | Multi-checkpoint runtime service (`/v1/variants/load`, LRU); Kokoro→OmniVoice→F5 | Medium | no |
| **5** | Installed-vs-available UI + per-variant Add/Remove | Low | no |
| **6** | Drop id aliases (cutover) | Low | **yes** (gated) |
| **7 (Cloud)** | Marketplace publish (verified/community), `RuntimeVariantArtifact` versioning, license policy | Cloud | no (CE empty) |

**Dependencies:** 3 needs 2; 4 needs 3; 5 needs 4; 6 needs 2; 7 is Cloud-only.
Stages 1–5 are the high-value CE slice and require **no** image-per-variant.

---

## Summary

- RuntimeVariant **domain**: complete and correct.
- Physical registry: **transitional** (legacy `*-base` naming; validate-only
  import; per-image weights). No drift — an unfinished, well-scoped migration.
- **Runtime Registry 2.0 = family directories + variants/ + two-root loader +
  shared base image + download/register + tri-state trust.**
- Adopt the family layout (loader is dir-name-agnostic → Stage 1 is safe).
- `private` trust tier is justified and shipped this task (additive).
- Shared base image + directory rename = the recommended next PR (Stage 1).
- Everything stays additive; the only breaking step (id cutover) is release-gated.

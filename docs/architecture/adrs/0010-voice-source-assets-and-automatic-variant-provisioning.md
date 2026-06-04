# ADR-0010: Voice Source Assets and Automatic Variant Provisioning

- **Status:** Accepted (architecture only — implementation deferred to a future phase)
- **Date:** 2026-06-04
- **Deciders:** Bruno Silva (product owner), architecture planning
- **Extends:** [ADR-0006](0006-voice-variant-realization-types.md) (realization types),
  [ADR-0008](0008-voice-variant-build-lifecycle.md) (build lifecycle),
  [ADR-0009](0009-artifact-versioning-and-retention.md) (artifact versioning)
- **Refines:** ADR-0008 §Runtime resolution flow — the *build-trigger policy* (when a variant is
  built and what generation does when one is missing). The five-state lifecycle, the build
  mechanism, and the artifact-versioning model are **unchanged**.

> **Scope guard.** This ADR is architecture-only. It does **not** change Runtime behavior,
> add migrations, or ship production code. Current CE code still builds variants lazily at
> generation time (`ensure_variant`); that remains until the provisioning pipeline described
> here is implemented in a later phase.

## Context

Validation of the Universal Voice Runtime ([11-PHASE-1-RETROSPECTIVE](../11-PHASE-1-RETROSPECTIVE.md),
[12-PROVIDER-VALIDATION](../12-PROVIDER-VALIDATION.md)) surfaced a gap that the existing ADRs
left implicit: **the system still treats "a reference audio sample" as if it were "the voice."**

That equivalence was safe when PeakVox primarily supported OmniVoice-style reference-audio
cloning. It is no longer safe. PeakVox is a multi-provider runtime, and each provider needs a
different realization format ([ADR-0006](0006-voice-variant-realization-types.md)):

| Provider | Realization | Built from |
|---|---|---|
| OmniVoice / OmniVoice Singing | `reference_sample` | the original audio |
| Fish Audio | `speaker_embedding` (assumed — see [12](../12-PROVIDER-VALIDATION.md) §3.2) | the original audio |
| Kokoro (future) | `voice_pack` (preset) | model-native presets (no cloning) |
| OpenVoice / Chatterbox / Orpheus / future | `conversion_profile` / `lora` / `checkpoint` / … | the original audio |

Three consequences follow:

1. **A Voice is not a WAV file.** A Voice is a model-independent identity; the WAV is merely one
   *input* from which model-specific realizations are produced.
2. **The original input is the canonical source of truth.** Every variant must be (re)buildable
   from it, never from another variant — otherwise portability and reproducibility degrade as
   formats lossily derive from each other.
3. **Variant existence is a platform responsibility, not a user action.** Users should not have
   to think about which model needs which artifact. They submit source material; PeakVox makes it
   usable across providers.

ADR-0006 named realization *formats*. ADR-0008 named the *build lifecycle*. ADR-0009 named
*artifact versioning*. None of them formalized **the source material as a first-class entity**,
nor **who triggers builds and when**. This ADR is that missing bridge between ADR-0006/0008/0009
and the Voice Clone workflow.

## Options considered

1. **Status quo — source audio lives inside the OmniVoice variant; build lazily at generation
   time.** Today the reference clip is stored as the OmniVoice variant's `artifacts.audio`, and a
   missing variant is built on first `Voice+Model` request (ADR-0008 `ensure_variant`). Simple,
   but: the "source of truth" is entangled with one provider's variant (OmniVoice-centric); other
   variants risk being derived from the OmniVoice variant rather than the original; and
   generation-time builds create hidden latency, silent behavior, and surprise failures. Rejected
   as the long-term model.

2. **Source Asset as a first-class entity + Automatic Variant Provisioning (proactive builds).**
   Elevate the original input to a tracked, model-independent **Voice Source Asset** that is the
   sole rebuild source for every variant. Provision variants **proactively** — when a source
   asset is accepted and when a new compatible model is installed — instead of lazily at
   generation time. **Chosen.**

3. **Per-provider source assets (each model keeps its own copy of the input).** Maximum provider
   isolation, but breaks portability and reproducibility (no single canonical source), duplicates
   storage, and makes "rebuild all variants from the original" impossible. Rejected.

## Decision

PeakVox formally separates **four distinct concepts** and adopts **Automatic Variant
Provisioning** driven by the Runtime.

### 1. The four-layer domain model

```
Voice                  universal identity            voice_8JXQ29K4L3        [ADR-0001/0004]
  └── Voice Source Asset   the original user-provided source material   larissa.wav   [THIS ADR]
        └── VoiceVariant       a model-specific realization of the Voice   (Voice × Model)  [ADR-0001/0006]
              └── Voice Variant Artifact   the concrete build output (a version)   reference_sample / embedding / voice_pack / …  [ADR-0008/0009]
```

| Concept | Definition | Examples | Owned / produced by |
|---|---|---|---|
| **Voice** | The universal, model-independent identity. | `voice_8JXQ29K4L3` | PeakVox / creator |
| **Voice Source Asset** | The **original** user-provided source material — the canonical source of truth. | `larissa.wav`, `speaker_recording.wav`, `reference_audio.flac` | The **user** (the only thing a user creates) |
| **VoiceVariant** | The model-specific representation of a Voice for one Model `(voice_id × model_id)`. | OmniVoice Variant, Fish Variant, Kokoro Variant | **PeakVox** (the Runtime) |
| **Voice Variant Artifact** | The concrete, versioned build output produced from a Variant. | `reference_sample`, `speaker_embedding`, `voice_pack`, `lora`, `checkpoint` | **PeakVox** (the adapter's `build_variant()`, versioned by the Runtime) |

The Source Asset is **new**; the other three are formalizations of ADR-0001/0006/0008/0009.

### 2. The official PeakVox voice lifecycle

```
Voice Source Asset            (user submits original material)
        ↓
Voice                         (identity created; permanent public_voice_id)
        ↓
Automatic Variant Provisioning   (Runtime schedules builds for compatible installed models)
        ↓
Voice Variants                (one per compatible model; lifecycle per ADR-0008)
        ↓
Voice Variant Artifacts       (versioned build outputs per ADR-0009)
        ↓
Generation Runtime            (resolves Voice + Model → active artifact → inference)
```

This supersedes the implicit "reference clip = voice → build on demand at generation" flow as the
**official** lifecycle.

### 3. Voice Source Asset — the canonical source of truth

- The Source Asset is **model-independent**. It is associated with the **Voice**, never with any
  single variant. (Conceptually a `voice_source_assets` association keyed to `voice_id`, supporting
  one-or-more source clips — *schema deferred; no migration in this ADR*.)
- **Every variant must be rebuildable from the Source Asset, never from another variant.**

  ```
  Fish Variant   must rebuild from:  larissa.wav        (the Source Asset)
                 must NOT rebuild from:  OmniVoice Variant
  ```

  This preserves portability (any future provider can be added and built from the original) and
  reproducibility (ADR-0009 artifact versions trace back to a stable input).
- Today's OmniVoice-centric storage (the reference clip living inside the OmniVoice variant's
  `artifacts.audio`) is **migrated conceptually** to the Source Asset layer in the implementation
  phase. Until then, the OmniVoice variant's reference clip is treated *as* the de-facto source.

### 4. Automatic Variant Provisioning

**Definition.** When a Voice Source Asset is submitted and accepted, PeakVox automatically creates
the required VoiceVariants for **all compatible installed models** — without a generation request.

```
Installed Models:  ✓ OmniVoice   ✓ OmniVoice Singing   ✓ Fish Audio

User uploads: larissa.wav
        ↓
Voice created: voice_G4R8NHVJ09
        ↓
Variant Build Queue (Runtime-scheduled):
   • Build OmniVoice Variant
   • Build OmniVoice Singing Variant
   • Build Fish Variant
        ↓
Result:
   voice_G4R8NHVJ09
   ├── OmniVoice Variant         (READY)
   ├── OmniVoice Singing Variant (READY)
   └── Fish Variant              (READY)
```

**Compatibility filter.** A model is *compatible* with a Source Asset when its adapter can build a
variant from that source — i.e. the adapter's `supported_realization_types` ([ADR-0008](0008-voice-variant-build-lifecycle.md))
can be produced from the Source Asset, the model is installed/active, and it is available in the
edition ([ADR-0005](0005-edition-scoped-model-availability.md)). Preset-only providers (Kokoro,
`voice_pack`) **cannot** clone an arbitrary Source Asset and are therefore **not** provisioned
from user uploads (see §8).

**Builds reuse the existing mechanism.** Provisioning does not introduce a new build path — it
*triggers* the ADR-0008 lifecycle (`pending → building → ready|failed`) per model and the ADR-0009
artifact versioning. What is new is the **trigger policy**: provisioning happens proactively at
accept time, not lazily at generation time.

### 5. Model installation triggers provisioning (synchronization)

When a new compatible model is installed, the Runtime detects existing Voices that lack a variant
for it and schedules builds — keeping *installed models* and *supported voices* synchronized.

```
Existing Voices:  Larissa, Theo, Bruno
New model installed:  Kokoro        (if it were clonable)
        ↓
Runtime detects: 3 voices missing the new variant
Runtime schedules: Build × 3 (from each Voice's Source Asset)
```

Invariant: **Installed Models → Supported Voices stay in sync**, in both directions (uploading a
voice provisions across installed models; installing a model backfills across existing voices).

### 6. Community Edition behavior (explicit, hardware-aware)

CE users control local hardware and which models are installed, so CE **exposes** variant state.

- **Voice Library** surfaces per-voice variant status, e.g.:

  ```
  Supported Models
    ✓ OmniVoice
    ✓ OmniVoice Singing
    ⚠ Fish Audio (Building)
    ✗ Kokoro (Not Built)
  ```

- **The Voice Details panel** (the existing selected-voice details panel in the Voice Library) is
  formally **reserved** as the future home for: Source Asset presence, Variant status, Supported
  Models, Build progress, Build failures, and **manual rebuild actions**. Illustrative only:

  ```
  Selected Voice
  ────────────────
  Source Asset   ✓ Present

  Variants
    ✓ OmniVoice
    ✓ OmniVoice Singing
    ⚠ Fish Audio (Building)
    ✗ Kokoro (Missing)

  [Build Variant]   [Rebuild Variant]
  ```

  This visibility is **CE-only**.

- **Generation behavior (CE).** If a variant does not exist for the selected `(Voice, Model)`,
  **generation is blocked** — there are **no generation-time builds and no hidden runtime
  behavior**. The TTS screen shows an explicit message ("This voice is not yet available for the
  selected model.") and directs the user to **Voice Library → Build Variant**. The model selector
  must not silently fail. *(This refines ADR-0008's generation-time "pending → trigger build"
  path: in CE, builds are a deliberate Voice-Library action, not a side effect of generation.)*

### 7. Cloud behavior (abstracted)

Cloud abstracts all of the above. Users **never** see variants, artifacts, or build queues.

```
Upload Voice → Voice Created → Automatic Variant Provisioning → Ready
```

The user sees only **"Processing Voice…"** until provisioning completes, then the voice is usable.
Cloud may still resolve/provision transparently (it does not block the way CE does); the
complexity is hidden, not removed.

### 8. Provider compatibility and preset-only models

Not every model can realize every Voice. Cloning providers (OmniVoice, Fish) build a variant
*from the Source Asset*. **Preset-only providers (Kokoro, `voice_pack`) cannot** — their "voices"
are model-native presets, not realizations of a user's identity. Therefore:

- A user Source Asset is **not** provisioned onto preset-only models.
- A Voice that has *no* compatible installed model simply has zero variants — a valid identity
  with no realizations (consistent with [Domain §5](../02-DOMAIN_ARCHITECTURE.md) invariants).
- Preset voices remain a separate origin (the `Voice.is_preset_voice` hook); their full treatment
  is a **future ADR-0011 ("Preset-backed Voices / non-cloning providers")**, to be written when a
  preset provider is actually integrated — not speculatively here
  ([12 §4.4](../12-PROVIDER-VALIDATION.md)).

### 9. Responsibility split (normative)

| Actor | Responsible for |
|---|---|
| **User** | Creating **Voice Source Assets** (the only thing a user creates). |
| **PeakVox Runtime** | Variant **provisioning**, **synchronization**, **rebuild orchestration**, **build triggering**, **missing-variant detection**, lifecycle state, artifact versioning, and **cross-provider compatibility**. |
| **Adapter** | **Only** `build_variant()` and artifact production. Adapters **never** manage lifecycle state, never schedule, never decide compatibility policy. |

> **Users do not create Variants. Users create Voice Source Assets. PeakVox creates Variants,
> creates Artifacts, and manages compatibility across providers.**

## Consequences

- **Positive:**
  - A Voice is finally, formally, *not* a WAV file — the Source Asset is a distinct canonical
    layer, and the public identity is fully model-independent (upholds [Vision](../00-VISION.md)).
  - Portability + reproducibility are structural: every variant rebuilds from the original source,
    never from a derived variant; ADR-0009 versions trace to a stable input.
  - Variant availability becomes a platform guarantee (proactive provisioning + install-time
    synchronization) rather than a generation-time surprise.
  - CE stays explicit and hardware-honest (visible variant state, deliberate builds, block-on-
    missing); Cloud stays effortless (hidden provisioning). One architecture, two UX policies.
  - Cleanly accommodates non-cloning providers by *excluding* them from cloning-based provisioning
    instead of forcing a broken assumption.
- **Negative / costs:**
  - Introduces a new first-class concept (Source Asset) and, in the implementation phase, a data
    model for it + a migration of the OmniVoice-centric reference storage. (Deferred — not in this
    ADR.)
  - Proactive provisioning consumes compute/storage up front (building variants that may never be
    generated). Mitigation: compatibility filter; CE builds are user-initiated where heavy;
    retention policy (ADR-0009) bounds artifact growth.
  - A background build queue / scheduler becomes a real Runtime responsibility (the async build
    path ADR-0008 deferred). Until built, CE continues lazy generation-time builds.
- **Follow-ups / what this enables:**
  - Implementation phase: a `voice_source_assets` data model; the provisioning scheduler;
    install-time backfill; the CE block-on-missing generation guard; the Voice Details variant
    panel; the Cloud "Processing Voice…" abstraction.
  - **ADR-0011 (future):** preset-backed Voices / non-cloning providers (Kokoro), when integrated.
  - Auto-routing ([Vision §Future](../00-VISION.md), [12 §8](../12-PROVIDER-VALIDATION.md)) gains a
    clean signal: a Voice's set of READY variants is exactly the set of models it can route to.

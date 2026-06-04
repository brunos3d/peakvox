# PeakVox — Strategic Vision

> **Read this first.** This document is the north star. Every architectural decision in this
> suite — and every future one — must remain aligned with it. When a design choice and this
> vision conflict, the vision wins or the choice is wrong.

---

## PeakVox is a Universal Voice Runtime

PeakVox is **not** a voice model platform. PeakVox is a **Universal Voice Runtime**.

The primary product is **not** OmniVoice, Fish Audio, Kokoro, OpenVoice, Chatterbox, Orpheus,
or any future model. The primary product is the **Runtime Layer**.

- **Models are providers.** Interchangeable inference engines.
- **Voices are portable assets.** Persistent, ownable, model-independent.
- **Voice IDs are universal.** One id addresses one identity, everywhere, forever.
- **Voice Variants are model-specific implementations** of a universal voice.

Developers integrate with PeakVox **once**. Voice creators publish **once**. Applications
consume **a single API**. Adding a new model never breaks any of them.

## What the runtime is responsible for

- Model abstraction · Provider abstraction · Voice abstraction
- Voice resolution · Variant resolution · Model routing
- Inference orchestration · GPU management · VRAM management
- Runtime lifecycle · API compatibility · Marketplace compatibility
- Future cloud orchestration

See [10 — Runtime Architecture](10-RUNTIME_ARCHITECTURE.md) for how this is structured.

## The non-negotiable invariant

**PeakVox must never be architected around a specific model.**

Every architectural decision must assume new voice models can be added **without** changing:

- Public APIs
- Voice IDs
- Voice Library concepts
- Marketplace concepts
- Developer integrations

The long-term vision, in one line:

> **OpenRouter for Voice + Ollama for Voice + a Voice Marketplace.**

OpenRouter (model-agnostic routing through one API), Ollama (effortless local runtime + model
lifecycle), and a marketplace (a creator economy of portable voices) — unified, for voice.

---

## Core principle: a voice does not belong to a model

A voice should **not** belong to a model. A voice belongs to **PeakVox**.

- Models are interchangeable engines.
- Voices are persistent assets.
- **The same Voice ID survives across different model providers.**

```
Voice ID:  voice_8JXQ29K4L3

Supported Variants:
  ✓ OmniVoice
  ✓ OmniVoice Singing
  ✓ Fish Audio
  ✓ Kokoro
  ✓ OpenVoice
```

The user changes the engine. The voice remains the same.

This principle is the load-bearing reason for the [Voice / VoiceVariant split](adrs/0001-voice-variant-split.md):
**Voice** is the universal identity; **VoiceVariant** is its per-model realization. The split
is not an implementation convenience — it is the structural expression of this vision.

---

## Developer experience

The contract is `voice_id + model + text`. The same call, the same voice id, the same
integration — only the model changes. (Examples are conceptual; the wire API is
[`POST /v1/speech/generate`](04-API_ARCHITECTURE.md).)

**Example 1 — OmniVoice**

```python
peakvox.tts.generate(
    voice_id="voice_8JXQ29K4L3",
    model="omnivoice",
    text="Hello world."
)
```

**Example 2 — Fish Audio**

```python
peakvox.tts.generate(
    voice_id="voice_8JXQ29K4L3",
    model="fish-audio-s2",
    text="Hello world."
)
```

**Example 3 — OmniVoice Singing**

```python
peakvox.tts.generate(
    voice_id="voice_8JXQ29K4L3",
    model="omnivoice-singing",
    text="Happy birthday to you."
)
```

Notice: same API, same Voice ID, same integration — **different model**. Only the model
changes; everything else is stable.

---

## Future: automatic model routing

PeakVox may eventually route automatically. The application code does not change.

```python
peakvox.tts.generate(
    voice_id="voice_8JXQ29K4L3",
    model="auto",
    text="Hello world."
)
```

With `model="auto"` the Runtime selects the most appropriate engine based on: quality, cost,
latency, singing support, emotion support, language support, and user preferences. This is the
"OpenRouter for Voice" behaviour, made possible by the [capability contract](adrs/0003-model-capability-contract.md)
and [Runtime routing](10-RUNTIME_ARCHITECTURE.md). It is a forward-compatible extension of the
same endpoint — never a new integration.

---

## What PeakVox is — and is not

**PeakVox is NOT:**

- A frontend for OmniVoice
- A wrapper around a single model
- A model-specific application
- A voice-cloning tool tied to one provider

**PeakVox IS:**

- A universal voice runtime
- A model orchestration layer
- A voice infrastructure platform
- A future voice marketplace
- A future cloud inference platform

OmniVoice is simply the **first provider** the runtime supports. It is a starting point, not
the center of gravity.

---

## How this vision binds the architecture

| Vision statement | Where it is enforced |
|---|---|
| A voice belongs to PeakVox, not a model | [ADR-0001](adrs/0001-voice-variant-split.md): Voice / VoiceVariant split |
| Models are interchangeable providers | [ADR-0002](adrs/0002-model-as-first-class-entity.md): Model as a first-class entity |
| Capabilities are stable across providers | [ADR-0003](adrs/0003-model-capability-contract.md): Model Capability Contract |
| The runtime is the product | [10 — Runtime Architecture](10-RUNTIME_ARCHITECTURE.md) |
| One API, stable across model change | [04 — API Architecture](04-API_ARCHITECTURE.md) |
| Voices are economic assets | [05 — Marketplace](05-MARKETPLACE_ARCHITECTURE.md), [07 — Monetization](07-MONETIZATION_ARCHITECTURE.md) |
| Variants are buildable runtime assets | [ADR-0008](adrs/0008-voice-variant-build-lifecycle.md): Voice Variant Build Lifecycle |
| Artifacts are versioned, retained, and auditable | [ADR-0009](adrs/0009-artifact-versioning-and-retention.md): Artifact Versioning and Retention |
| CE = local runtime, Cloud = ecosystem | [01 — Product](01-PRODUCT_ARCHITECTURE.md) |

Start at [00 — Overview](00-OVERVIEW.md) for the document map.

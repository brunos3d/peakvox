# PeakVox — Open-Source Philosophy

PeakVox is a Universal Voice Runtime. This document states *why* it is built the way it is —
the beliefs that shape the architecture, the licensing, and the community.

For *what* PeakVox is, start at the [README](README.md). For *how* decisions get made, see
[GOVERNANCE.md](GOVERNANCE.md). For *who we want to be*, see
[COMMUNITY_VALUES.md](COMMUNITY_VALUES.md).

---

## What we believe

- **Open models matter.** The most important advances in speech are increasingly open. A
  platform that locks itself to one proprietary model inherits that model's limits, pricing,
  and politics. PeakVox is model-agnostic on purpose, so the ecosystem — not a vendor — decides
  which models matter.

- **Open ecosystems matter.** Voices, integrations, and workflows should not be hostage to a
  single provider. The same `public_voice_id` works across every model, forever. You integrate
  once; you are never re-platformed by a model change.

- **Voice technology should remain accessible.** Self-hosting is a first-class path, not a
  downgraded one. Community Edition is genuinely useful on its own hardware — including
  CPU-capable runtimes — so capability does not require a credit card or a cloud account.

- **Infrastructure should not be locked behind proprietary systems.** The runtime, the model
  registry, the voice library, the generation pipeline, and the public API are all in the open.
  The parts reserved for Cloud (marketplace, creators, billing, multi-tenant auth) are clearly
  bounded, schema-ready, and disabled in CE — never a hidden fork.

- **The platform should remain extensible and transparent.** Adding a runtime or a model family
  is a documented, ADR-driven process — never a privileged, closed integration. Capabilities
  are declared, not inferred. Decisions are written down.

- **A voice belongs to its owner, not to a model.** This is both a technical invariant and an
  ethical stance. People should own their voice identity, carry it across engines, and use it
  under clear, consent-based rules (see the [Voice Usage Policy](VOICE_USAGE_POLICY.md)).

---

## How the philosophy shows up in the code

These beliefs are not aspirational — they are enforced by the
[Constitution](docs/.agents/CONSTITUTION.md) and the ADRs:

| Belief | Where it is enforced |
|---|---|
| Never architected around one model | Constitution Art. I–II; [ADR-0002](docs/.agents/DECISIONS/adr-0002-model-as-first-class-entity.md), [ADR-0004](docs/.agents/DECISIONS/adr-0004-voice-variant-model-separation.md) |
| Voices are portable, model-independent assets | [ADR-0001](docs/.agents/DECISIONS/adr-0001-voice-variant-split.md) Voice/Variant split |
| Capabilities declared, not inferred | [ADR-0003](docs/.agents/DECISIONS/adr-0003-model-capability-contract.md) |
| One stable entry point for generation | [Runtime architecture](docs/.agents/ARCHITECTURE/runtime-architecture.md) |
| Models are installable runtimes, not bespoke builds | [ADR-0016](docs/.agents/DECISIONS/adr-0016-models-as-runtime-services.md), [ADR-0018](docs/.agents/DECISIONS/adr-0018-runtime-variants-architecture.md) |
| Open-core boundary is honest and bounded | Constitution Art. V; [Product Architecture](docs/.agents/ARCHITECTURE/product-architecture.md) |
| Code is proof; documentation is intent | Constitution Art. VII |

---

## Open core, stated plainly

PeakVox is **source-available**, not a traditional permissive open-source license. The code is
readable, modifiable, and self-hostable under the [Community License](LICENSE) (based on the
Elastic License 2.0). What it prohibits is narrow and specific: reselling PeakVox as a competing
managed/SaaS offering. Everything a self-hoster, developer, researcher, or business wants to do
internally is permitted, free of charge.

We chose open core — rather than fully permissive — so the project can be sustainable without
fragmenting the ecosystem or paywalling the infrastructure. We chose source-available — rather
than closed — because transparency and self-hosting are non-negotiable to us. The bundled model
runtimes keep their own upstream licenses; PeakVox does not restrict them (see [NOTICE](NOTICE)).

If the boundary ever needs to move, it moves in the open, through a superseding decision —
never silently.

---

## Build in public

Architecture lives in [`docs/.agents/`](docs/.agents/README.md): a vision, a constitution,
ADRs, an architecture suite, a roadmap, and honest validation reports that separate "the
platform can orchestrate this" from "a real model runs this end-to-end." The intent is that a
newcomer can understand the project — and disagree with it — from the documents alone.

---

**Related:** [README.md](README.md) · [GOVERNANCE.md](GOVERNANCE.md) ·
[COMMUNITY_VALUES.md](COMMUNITY_VALUES.md) · [CONTRIBUTING.md](CONTRIBUTING.md) ·
[Vision](docs/.agents/CONTEXT/VISION.md) · [Constitution](docs/.agents/CONSTITUTION.md)

# ADR-0002: Model as a first-class persisted entity

- **Status:** Accepted
- **Date:** 2026-06-03
- **Deciders:** Bruno Silva (product owner), architecture planning

## Context

Multi-model support began as a runtime **registry** (`model_registry`, `model_catalog`,
provider plugins) with a persisted `models` table already on `main`. Future phases require more
than a runtime lookup: **versioning** (multiple versions of a model line coexisting; variants
pinning a version), **lifecycle** (discover/install/activate/deactivate/update/deprecate),
**licensing metadata** (weights license, commercial-use flag — relevant to the marketplace and
Cloud), **provider metadata** (author, source, citation), and **requirements** (VRAM/GPU for
Cloud scheduling). A purely in-memory registry object cannot carry this.

## Options considered

1. **Runtime-only registry (in-memory descriptors).** Simplest, but no durable versioning,
   lifecycle state, licensing, or scheduling metadata; can't support model updates without
   breaking pinned variants; can't participate in marketplace/cloud.

2. **Model as a first-class persisted entity** with versioning, lifecycle, licensing, provider
   metadata, and requirements; the registry/providers remain the runtime layer over it. The
   `models` table already exists and is extended additively.

## Decision

Adopt **Option 2**. `Model` is a first-class persisted domain entity, not merely a runtime
registry object. The registry and provider plugins stay as the runtime/load layer **on top of**
the persisted entity. Model **updates install a new version row** rather than mutating
artifacts a `VoiceVariant` pins, so existing variants keep working and can be regenerated
deliberately.

## Consequences

- **Positive:** durable versioning + lifecycle; licensing/provider/requirements metadata
  available to scheduling, marketplace, and Cloud; safe model updates via versioning; HF-based
  install fits naturally.
- **Negative / costs:** more schema and lifecycle code than a pure registry; version
  management adds surface (mitigated by an additive `version` field now, `model_versions` child
  table only if needed).
- **Follow-ups:** the additive metadata columns and the versioning rule are
  [Roadmap Phase 2](../09-ROADMAP.md) and
  [Migration §5](../08-MIGRATION_ARCHITECTURE.md); variant staleness on `model.updated` ties to
  [ADR-0001](0001-voice-variant-split.md).

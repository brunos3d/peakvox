# ADR-0007: Canonical Model Metadata Registry

- **Status:** Accepted
- **Date:** 2026-06-04
- **Deciders:** Bruno Silva (product owner), architecture planning

## Context

ADR-0002 made `Model` a first-class persisted entity, ADR-0003 made capabilities a declared
contract, ADR-0005 made availability edition-scoped, and ADR-0006 hid provider-specific voice
realizations behind the Runtime. The Models page now exposes registry data directly to users,
which raises the bar: the registry must not ship fictional models or incomplete placeholder
metadata.

## Decision

PeakVox uses a **canonical normalized model metadata registry** for built-in models.

1. Upstream facts are captured from provider-backed sources: Hugging Face model pages, GitHub
   repositories, official documentation, papers, and license pages.
2. Provider-specific upstream metadata is normalized into `ModelDescriptor`.
3. API and UI surfaces read normalized descriptors only. They never fetch provider APIs directly
   and never maintain duplicate model definitions.
4. Lifecycle state is separate from static metadata:
   - static metadata comes from the canonical registry and is refreshed on startup;
   - install/activation state is persisted in the `models.status` column and must not be
     clobbered by metadata refreshes.
5. Built-in models that no longer exist in the canonical registry are removed from the persisted
   built-in table during migration. User/community models (`is_builtin = 0`) are preserved.
6. Unknown upstream facts must be explicit (`null` / `unknown` / notes), not silently hidden as
   if they were merely omitted.

## Consequences

- The Models page becomes a true Model Manager, not a presentation copy of hardcoded UI data.
- Removing a fictional or unverified model is a metadata change, not a UI change.
- The Runtime and Registry remain data-driven: capabilities, edition availability, and lifecycle
  state are read from the normalized descriptor.
- Adding a provider requires a normalized metadata record plus an adapter; provider APIs may be
  used for ingestion, but the product reads from PeakVox's normalized schema.

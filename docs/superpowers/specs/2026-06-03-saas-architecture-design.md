# SaaS Architecture Preparation — Design Spec

**Date:** 2026-06-03
**Status:** Design only (no auth/billing/cloud implementation)
**Sub-project:** F of the OmniVoice Phase 2 platform initiative

---

## Goal

Phase 17: prepare the architecture for Community / Cloud / Enterprise editions so future
authentication, billing, multi-tenancy, and cloud sync attach **without a database
redesign or breaking changes**. No billing, auth, or cloud infrastructure is implemented.

## Deliverables

1. **`docs/SAAS_ARCHITECTURE.md`** — the architecture blueprint: edition matrix,
   what is already SaaS-ready, the extension-point table, tenancy model, API evolution,
   deployment topology, and an explicit out-of-scope list.
2. **Identity seam** — `backend/app/core/identity.py::get_current_owner_id()`, the single
   function future auth overrides. Returns the local owner today. Additive; existing
   endpoints are unchanged.
3. **Edition flag** — `settings.EDITION` (default `"community"`), documented as the
   selector for which optional extensions load. It never changes the core schema.
4. **Rate-limit seam** — already present from sub-project D
   (`api/v1.enforce_rate_limit`), documented as the quota extension point.

## Why this is safe / non-breaking

- The seams are additive (a new module, a new setting). No existing call sites change.
- The data model from sub-project A (`users`, `owner_id`, hashed API keys, stable
  `public_voice_id`, visibility flags) already encodes the multi-tenant shape; Cloud =
  populate users + resolve `owner_id` at the seam.
- The idempotent migration pattern supports later additive tables/columns
  (Organizations, RBAC, metering) the same way.

## Out of scope

Authentication, sessions, JWT, OAuth/SSO, billing, metering backends, multi-tenant query
rewiring, organizations, RBAC, and cloud infrastructure — all deferred to the Cloud/
Enterprise editions. This sub-project is preparation only.

## Success criteria

- A reader can see exactly how each future capability attaches and to which seam.
- The identity seam and edition flag exist, compile, and are documented.
- No behavior change in the Community Edition (39 backend tests still pass).

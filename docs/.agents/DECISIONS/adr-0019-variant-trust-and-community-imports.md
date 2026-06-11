# ADR-0019: Variant Trust Tiers & Community Imports

- **Status:** Accepted
- **Date:** 2026-06-11
- **Deciders:** PeakVox architecture (Task 27). Extends the RuntimeVariant
  architecture once it began wiring into resolution and the UI.
- **Supersedes:** none.
- **Extends:** [ADR-0018](adr-0018-runtime-variants-architecture.md) — adds a
  `trust` provenance dimension to `RuntimeVariant` and specifies the *validate*
  gate of the Hugging Face import flow ADR-0018 reserved for Phase 6.
- **Superseded by:** none.
- **Spec:** [`../SPECS/FEATURES/runtime-variants/`](../SPECS/FEATURES/runtime-variants/)
- **Audit:** [`../VALIDATION/AUDITS/task-27-runtime-variants-audit.md`](../VALIDATION/AUDITS/task-27-runtime-variants-audit.md)
- **Findings:** [`../VALIDATION/RESEARCH/task-27-model-ecosystem-findings.md`](../VALIDATION/RESEARCH/task-27-model-ecosystem-findings.md)

---

## Context

ADR-0018 made a `RuntimeVariant` an infrastructure descriptor that binds a
checkpoint to a runtime, and reserved a Hugging Face import flow for Phase 6.
As PeakVox evolves from a *fixed runtime catalog* into a *model ecosystem* — the
"Ollama / LM Studio for voice" direction — two questions become load-bearing:

1. **Provenance.** A first-party checkpoint PeakVox tested end-to-end and a
   checkpoint a user pasted from a random Hugging Face repo are not equivalent,
   yet ADR-0018's schema could not tell them apart. The UI must make the
   difference visible, and policy (especially Cloud) must be able to act on it.
2. **Import safety.** Letting a user attach an arbitrary checkpoint to a runtime
   risks attaching an *incompatible* one (wrong provider/architecture, claims a
   capability the runtime lacks). Compatibility must be decided *before* any
   download, and **declared-and-checked, never inferred from the repo name**
   (ADR-0003 applied to checkpoints).

This is not a new concept — it is a named, enforced form of the project's
existing **architecture-validated vs provider-validated** distinction
(Constitution VII §23).

## Decision

### 1. A RuntimeVariant has a `trust` tier

Add `trust: "verified" | "community"` to `RuntimeVariantMetadata`, defaulting to
`verified` (so first-party `variants/*.json` are curated-by-default and existing
descriptors stay valid). Optional `source_url` records a human-facing origin
(e.g. the HF repo) — never a model-internal artifact path.

| | **Verified** | **Community** |
|---|---|---|
| Curated by PeakVox | yes | no |
| Provider-validated (ran end-to-end) | yes | no |
| Checkpoint source | pinned / known | user-supplied |
| Compatibility | checked **and** tested | checked only |
| UI | green ✓ badge | amber ⚠ badge |

**Mapping:** Verified ≙ provider-validated; Community ≙ architecture-validated
(compatibility checked) but not provider-validated. An imported variant is
**always** `community` until someone runs it end-to-end.

### 2. Community import is a gated, staged flow; *validate* is decided first

```
Add Variant → paste HF URL → VALIDATE → download → register → use
```

The **validate** stage is pure and network-free and is the architectural gate.
`validate_variant_import(runtime, candidate)` enforces, in order:

1. **Capability vocabulary** — declared capabilities ∈ the closed
   `RUNTIME_CAPABILITY_VOCABULARY` (ADR-0003). Unknown → reject.
2. **Capability ceiling** — declared capabilities ⊆ the runtime's capabilities;
   a variant may not exceed its runtime (ADR-0017 §1.5). Exceeds → reject.
3. **Provider/family match** — if declared, must match the runtime's
   `provider` or `model_family`; mismatch → reject. If **not** declared → a
   *warning* (compatibility unverified), never a silent pass.
4. **Format** — unrecognized container format → warning (the runtime service is
   the final authority on loadability).

Result is `compatible` (go/no-go), `reasons` (hard blockers), `warnings`
(non-blocking), and the `proposed_variant_id` + forced `trust = community`.

### 3. Download + register stay out of the backend

The later stages (resolve files, download to
`/data/runtime-weights/<runtime>/<variant>/`, write `variants/<id>.json`, load
on the runtime) run **inside the runtime container** — which already has the
model framework, the GPU, and the HF cache mount — surfaced through a
`variant_add` RuntimeOperation. The backend never imports a model framework
(ADR-0016/0017; Runtime Activation Audit). These stages are PLANNED (they need
the multi-checkpoint runtime service of migration Phase 4) and are out of scope
for this ADR, which decides the *trust model* and the *validate contract*.

## Consequences

**Positive**
- The Models page can honestly distinguish curated from imported models.
- Incompatible checkpoints are rejected *before* a multi-GB download.
- `trust` is the natural hook for Cloud curation tiers (Verified / Partner /
  Community) and policy (e.g. forbid `community` on shared tenants) — schema-ready
  in CE, inert there (Constitution V §15).
- No new public-API surface; `trust` rides the additive composed-view `variants`
  array; checkpoint internals remain hidden (ADR-0004 §6).

**Negative / trade-offs**
- Compatibility relies on a *declaration*. A user can mis-declare; the result is
  a `community`/unverified variant that may fail at load — acceptable, because
  Verified is reserved for provider-validated models and the failure is
  contained to that variant.
- Auto-discovery of provider/capabilities from HF metadata is deliberately *not*
  trusted to grant compatibility (only to pre-fill a declaration) — see the
  findings doc, Phases E/G.

## Compliance

- **ADR-0003** — capabilities declared, not inferred; enforced at the import gate.
- **ADR-0004 §6** — no checkpoint internals on the public surface.
- **ADR-0016/0017** — backend stays model-framework-free; download belongs to the
  runtime container.
- **Constitution VII §23** — Verified/Community is the provider-validated vs
  architecture-validated line, named for users.
- **Constitution V §15** — Cloud curation/policy is schema-ready, inert in CE.

## Status of implementation (Task 27)

Shipped: `trust` + `source_url` schema fields, the composed-view `variants`
array, `validate_variant_import` + `POST /runtimes/{id}/variants/validate-import`,
and the frontend Variants section with trust badges + import dialog. 29 new
unit tests; full backend suite green. Download + register PLANNED.

---

**Related:** [ADR-0018](adr-0018-runtime-variants-architecture.md) ·
[ADR-0016](adr-0016-models-as-runtime-services.md) ·
[ADR-0003](adr-0003-model-capability-contract.md) ·
[ADR-0004](adr-0004-voice-variant-model-separation.md) ·
[`../CONSTITUTION.md`](../CONSTITUTION.md)

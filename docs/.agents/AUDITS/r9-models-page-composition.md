# R9 — Models Page Composition: Catalog + Registry + State (Refinement)

**Date:** 2026-06-08
**Subject:** Architectural clarification on how the Models page renders runtime-related metadata.
**Status:** ACCEPTED (R9 — refinement of Task 1 source-of-truth audit)
**Result:** The Models page renders a **composed view**: Model Catalog + Runtime Registry + Runtime Operational State. A model exists whether or not a runtime descriptor exists. The runtime-registry AUGMENTS the catalog; it does NOT replace it.

---

## The clarification

The Task 1 source-of-truth audit was correct that there is a mismatch between the Models page and the runtime-registry. The audit's fix was: "make the runtime-registry the source of truth for the Models page." This refinement REJECTS that fix.

**The runtime-registry is NOT the source of truth for the Models page.** The runtime-registry is **infrastructure metadata that augments the model cards**. The Models page renders a composed view from three sources:

| Source | What it provides | Authority |
|---|---|---|
| **Model Catalog** (`BUILTIN_MODELS` → `models` table) | Domain: id, name, capabilities, supported_tags, edition | The model itself. **Always present.** |
| **Runtime Registry** (`runtime-registry/<id>/descriptor.json`) | Infrastructure: image, port, lifecycle, model_binding | Optional. A model may exist without a runtime. |
| **Runtime Operational State** (`RuntimeManager._instance_cache`) | Live: phase, host, port, image_identity, last_request_at | Optional. A model without a runtime has no state. |

A model may exist without a runtime.
A runtime may never exist without a model binding (per the invariant in ADR-0017 §1.5).

## The composed view's data shape

For each catalog model, the composed card carries:

```json
{
  "model": {
    "id": "kokoro-base",
    "name": "Kokoro 82M",
    "capabilities": { ... },
    "supported_tags": [ ... ],
    "edition": ["ce", "cloud"]
  },
  "runtimes": [
    {
      "runtime_id": "kokoro-82m",
      "descriptor": { ... },
      "state": { "phase": "Active", "host": "...", "port": 8000, ... }
    }
  ],
  "default_runtime_id": "kokoro-82m"
}
```

When the model has no runtime descriptor:

```json
{
  "model": {
    "id": "omnivoice-base",
    "name": "OmniVoice Base",
    "capabilities": { ... }
  },
  "runtimes": [],
  "default_runtime_id": null
}
```

The card renders the **Runtime section** as:
- "Not Available — Not Migrated" (when `runtimes` is empty)
- The default runtime's state (when `runtimes` is non-empty)
- Lifecycle action buttons (only when `runtimes` is non-empty)

## The migration path

| Stage | Description | Models page behavior |
|---|---|---|
| **Current** | Catalog only | Renders catalog. Lifecycle buttons are DB-status mock. |
| **Intermediate (now)** | Catalog + Registry + State | Renders composed view. Models without runtimes are visible but flagged "Not Migrated". Models with runtimes show real state. |
| **Future** | All models migrated | Catalog becomes thin. Each model has 1+ runtimes. Lifecycle is the primary control surface. |

The composed view preserves gradual migration. OmniVoice, F5-TTS, XTTS, OpenVoice, Fish Audio can be added to the catalog in Phase 4-6 without breaking the Models page; their "Not Migrated" status is honest and visible.

## UI behavior matrix

| Model state | Catalog visible? | Runtime section | Lifecycle buttons | Real audio? |
|---|---|---|---|---|
| Catalog only, no runtime | ✅ | "Not Available — Not Migrated" | (none) | n/a |
| Catalog + runtime descriptor, no install | ✅ | "Not Installed" | Install | n/a |
| Catalog + runtime, image pulled, container stopped | ✅ | "Installed" | Start, Remove | via runtime when started |
| Catalog + runtime, container running, /ready 200 | ✅ | "Active" (with uptime, host:port, endpoint) | Stop, Remove, Update | ✅ |
| Catalog + runtime, failed | ✅ | "Failed — <reason>" | Start, Remove | n/a |

## The new endpoint

`GET /api/models/with-runtimes` returns the composed view. Available whether or not a `RuntimeManager` is attached:

| Manager attached? | Behavior |
|---|---|
| Yes | `runtimes[]` is populated from `RuntimeRegistry` + `RuntimeManager.get_cached_instance()`; `default_runtime_id` is the runtime with `is_default = true` (or the first, by priority). |
| No (CE default) | `runtimes[]` is `[]` for every model; `default_runtime_id` is `null`. The page renders the catalog with "Not Migrated" badges. |

This is different from the existing endpoints:

- `GET /api/models` returns the catalog (DB-backed). 4 entries.
- `GET /api/runtimes` returns the runtime-registry. 1 entry. Gated on `RUNTIME_SERVICE_ENABLED`.
- `GET /api/models/with-runtimes` is the **composed view**. 4 entries; the Kokoro entry has 1 runtime, the others have 0. NOT gated.

## The frontend rendering

The Models page renders a `ModelWithRuntimesCard` for each catalog entry:

```
┌──────────────────────────────────────────────────────┐
│  Kokoro 82M                          [Default] [CE]  │
│  Lightweight open-weight TTS ...                     │
│  ──────────────────────────────────────────────────  │
│  Runtime                                                │
│  ┌──────────────────────────────────────────────────┐│
│  │ peakvox/kokoro-runtime:0.1.0    [Active]         ││
│  │ http://peakvox-kokoro-runtime:8000                ││
│  │ Idle timeout: 15m   Started: 2 min ago           ││
│  │ [Stop] [Update] [Remove]                          ││
│  └──────────────────────────────────────────────────┘│
│  ──────────────────────────────────────────────────  │
│  Capabilities: TTS, ...                               │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│  OmniVoice Base                       [CE + Cloud]    │
│  The full-quality OmniVoice model ...                 │
│  ──────────────────────────────────────────────────  │
│  Runtime                                                │
│  ┌──────────────────────────────────────────────────┐│
│  │ Not Available                                    ││
│  │ This model has no runtime descriptor yet.        ││
│  │ Migration is scheduled for Phase 6.               ││
│  └──────────────────────────────────────────────────┘│
│  ──────────────────────────────────────────────────  │
│  Capabilities: TTS, Voice Cloning, ...                │
└──────────────────────────────────────────────────────┘
```

The Runtime section is rendered for **every** model. When the runtime exists, the section is rich (state, endpoint, lifecycle buttons). When it doesn't, the section is a clear "Not Available — Not Migrated" badge.

## What changes vs the previous fix

The previous fix (in the source-of-truth audit, before R9) was: "the Models page must render from `/api/runtimes` when `RUNTIME_SERVICE_ENABLED=true`." **This is REJECTED.** The right fix is: "the Models page must render from `/api/models/with-runtimes` always; the runtime-registry is the augmentation, not the replacement."

Specifically:
- The Models page does NOT replace its catalog view with the runtime-registry view.
- The catalog remains the primary entity; the runtime is infrastructure metadata.
- Models without runtimes are visible (and flagged "Not Available").
- Runtime lifecycle actions only appear when a runtime descriptor exists.

## What this means for the runtime-registry contract

The runtime-registry contract (ADR-0017 §1) is unchanged. A RuntimeDescriptor is still a self-contained, buildable, runnable artifact. The contract doesn't change.

What changes is the **UI's relationship to the registry**: the registry is one of three inputs to the composed view, not the sole input.

## Implementation plan

1. **Backend:** New endpoint `GET /api/models/with-runtimes` (TDD). Joins catalog + registry + state. Available without a manager (returns catalog with empty runtimes).
2. **Frontend:** New hook `useModelsWithRuntimes()`. New types `ModelWithRuntimesCard`. The Models page renders the composed view from this hook.
3. **Re-validate with Chrome DevTools** (Task 8): the page shows 4 cards; the Kokoro card has a Runtime section with the live state; the other 3 cards have a "Not Available" Runtime section.

## Update to Task 1 audit

The Task 1 source-of-truth audit is **updated** to reflect R9:

- The original statement "the Models page must render from the runtime-registry" is replaced.
- The new statement: "the Models page must render from the composed view: Model Catalog + Runtime Registry + Runtime Operational State."

The single-source-of-truth table is unchanged (catalog and registry are still authoritative for their respective concerns). What's clarified is the **rendering policy** at the API/UI boundary.

## Conclusion

The composed view is the right design. The runtime-registry is **infrastructure** that **augments** the catalog, not the **source of truth** that **replaces** it. A model may exist without a runtime; a runtime may never exist without a model binding. The Models page becomes the orchestration view: it shows every model, every runtime, and the live state, in one place. The migration of OmniVoice, F5-TTS, XTTS, OpenVoice, Fish Audio to runtime-registry is gradual and visible; the UI never hides valid platform capabilities just because the infrastructure isn't there yet.

---

**See also:**
[`docs/.agents/AUDITS/source-of-truth-audit.md`](source-of-truth-audit.md) (Task 1, updated)
·
[`docs/.agents/AUDITS/models-page-integration-audit.md`](models-page-integration-audit.md) (Task 2)
·
[`docs/.agents/AUDITS/frontend-runtime-convergence-validation.md`](frontend-runtime-convergence-validation.md) (Task 8)
·
[`docs/.agents/SPECS/FEATURES/runtime-services-implementation/SPEC.md`](../SPECS/FEATURES/runtime-services-implementation/SPEC.md) (R1-R8)
·
[`runtime-registry/kokoro-82m/`](../../../runtime-registry/kokoro-82m/) (R8 reference)

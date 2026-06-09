# Task 19 — Voice ↔ Model Compatibility: Runtime-Aware Activation

## Problem

Three UI surfaces show contradictory compatibility data because `activation_status` in the
`/api/models` response is computed from the legacy in-process `ModelDescriptor.status`
field, which is never updated by `RuntimeManager` lifecycle operations.

### Causal chain

```
RuntimeManager.start("kokoro-82m") → container running, ACTIVE in instance cache
  BUT model_registry.set_status() is NEVER called by RuntimeManager
  → descriptor.status remains "available" (default for all models)
  → activation_status computed from descriptor.status
  → ALL models return activation_status: "active" via legacy path
  → frontend modelIds filter includes wrong models

OR (OmniVoice scenario):
  → descriptor.status was previously set to "inactive" by old lifecycle
  → activation_status: "inactive" for the actually-running model
  → OmniVoice disappears from compatibility surfaces
```

### Affected surfaces

| Surface | Symptom |
|---|---|
| Voice Library → Compatible Models | Shows Kokoro (not running) as active; OmniVoice (running) absent |
| TTS → Model Selector | "No compatible models for the selected voice" |
| Voice Library → VoiceCard badge | "Not compatible" even when active model supports the voice |
| Voice Library → VoiceSelector header | Contradicts individual card badges |

## Root Cause

`_descriptor_payload()` in `backend/app/api/models.py` calls `descriptor.model_dump()` which
computes `activation_status` from `descriptor.status` (the legacy field). It never consults
`RuntimeManager.resolve(model_id)` — the authoritative source for Runtime Registry-managed
models.

Secondary bug: `_build_library_map()` in `voice_resource_service.py` uses Python `and`
between two SQLAlchemy column expressions instead of `sqlalchemy.and_()`. Python `and` between
two truthy objects returns the second operand, so the OR clause only filters by `preset_name`
(not by `provider + preset_name` combination). This can incorrectly mark preset voices as
already-in-library when a different provider has the same preset name.

## Required Outcome

`activation_status` MUST reflect `RuntimeManager` state for all Runtime Registry-managed models:

- Model has active container in RuntimeManager cache → `activation_status: "active"`
- Model has runtime registry entries but container not active → `activation_status: "inactive"`
- Model has no runtime registry entries → legacy path (unchanged)

All three surfaces fix automatically when the backend emits correct data.

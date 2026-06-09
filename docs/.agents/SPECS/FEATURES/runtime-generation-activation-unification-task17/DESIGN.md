# DESIGN — Runtime/Generation Activation Unification (Task 17)

## Root Cause
`/generate` calls `runtime.ensure_active(model_id)`. That gate used `ModelDescriptor.activation_status`, derived from legacy model `status` field. Runtime lifecycle actions (install/start) can make runtime active without changing model status to active, causing false 409 conflicts.

## Single Source of Truth
When runtime subsystem is attached and model has runtime descriptors:
- Generation eligibility owner: RuntimeManager
- Predicate: `RuntimeManager.resolve(model_id) != None` (requires ACTIVE runtime instance)

Fallback (legacy/no runtime descriptor):
- `ModelDescriptor.activation_status`

## Ownership Contract
- Runtime active state: RuntimeManager + RuntimeInstance cache
- Runtime lifecycle state transitions: RuntimeManager/driver
- Generation eligibility: PeakVoxRuntime.ensure_active (delegates to RuntimeManager in runtime-enabled path)
- Model lifecycle status field: compatibility/fallback metadata, not authoritative for runtime-enabled generation

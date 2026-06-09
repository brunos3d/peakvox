# Generation Trace — Task 17

## Request Path Traced
Text To Speech UI -> POST /generate -> create_generation_job -> runtime.ensure_active -> PeakVoxRuntime.ensure_active

## Exact 409 Origin (Before Fix)
- File: backend/app/api/generation.py
- Function: create_generation_job
- Condition: runtime.ensure_active(model.id) raises ModelNotActive

Raised from:
- File: backend/app/services/runtime.py
- Function: PeakVoxRuntime.ensure_active
- Condition (legacy): descriptor.activation_status != "active"
- Source of truth used: ModelDescriptor.status/activation_status (legacy model lifecycle)

## Why It Broke
Runtime lifecycle start/install updated RuntimeManager runtime state, but generation eligibility still depended on legacy model descriptor activation state.

## Fix
When runtime manager is attached and runtime descriptors exist for model:
- Generation eligibility source of truth becomes RuntimeManager.resolve(model_id)
- ACTIVE runtime instance allows generation
- Legacy descriptor activation is fallback only when no runtime descriptor exists.

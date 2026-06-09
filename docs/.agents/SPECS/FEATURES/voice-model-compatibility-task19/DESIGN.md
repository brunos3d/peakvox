# Design — Voice ↔ Model Compatibility (Task 19)

## Fix 1: `_descriptor_payload()` — RuntimeManager override (backend/app/api/models.py)

**Location:** `_descriptor_payload()`, after `data.update(model_registry.status(descriptor.id))`

**Logic:**
```python
if runtime._runtime_manager is not None:
    registry_descriptors = runtime._runtime_manager.registry.list_for_model(descriptor.id)
    if registry_descriptors:
        # This model is Runtime-Registry-managed. RuntimeManager.resolve() is authoritative.
        if runtime._runtime_manager.resolve(descriptor.id) is not None:
            data["activation_status"] = "active"
        else:
            data["activation_status"] = "inactive"
    # No runtime registry entries → legacy path unchanged.
```

**Why this is the right location:** `_descriptor_payload()` is called for every model in
`/api/models` and `/api/models/{id}`. Fixing it here ensures all consumers (models list,
model detail, all frontend hooks) see the correct value without any frontend changes.

**Why not touch the descriptor or model_registry:** The descriptor's `status` field is the
legacy in-process state. RuntimeManager's instance cache is the Runtime Registry operational
state. These are two orthogonal sources. We don't overwrite one with the other — we let the
API layer merge them at serialization time.

## Fix 2: `_build_library_map()` Python `and` bug (backend/app/services/voice_resource_service.py)

**Location:** `_build_library_map()`, the list comprehension that builds `clauses`

**Bug:** Python's `and` between two truthy SQLAlchemy `ColumnElement` objects returns the
second operand. The `OR(*clauses)` only filters by `preset_name`, not `provider + preset_name`.

**Fix:** Replace Python `and` with `sqlalchemy.and_()`:
```python
from sqlalchemy import and_
clauses = [
    and_(
        func.json_extract(VoiceProfile.meta, "$.provider") == pid,
        func.json_extract(VoiceProfile.meta, "$.preset_name") == eid,
    )
    for pid, eid in pairs
]
```

## No frontend changes needed

All three UI surfaces use `activation_status` from the models API response. Once the backend
emits correct values:

- `useVoiceModelCompatibility` → `modelIds` filtered by `activation_status === "active"` → correct
- `ModelSelector.activeModels` → same filter → correct
- `VoiceCard.compatState` → `getCompatState(activeModel.id)` → correct
- `VoiceSelector` header/card consistency → both use same source of truth

## Related ADRs

- ADR-0017: RuntimeManager as orchestration-only component; `resolve()` is authoritative
- ADR-0003: Capabilities are declared, not inferred — `activation_status` must come from runtime state, not model name branching
- ADR-0002: Voice-model compatibility is a derived field, not a stored flag

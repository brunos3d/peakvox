# Tasks — Voice ↔ Model Compatibility (Task 19)

## T1 — Backend: fix `_descriptor_payload()` activation_status override
**File:** `backend/app/api/models.py`
**Status:** DONE

After `data.update(model_registry.status(...))`, add RuntimeManager override:
if runtime._runtime_manager is wired and model has registry descriptors,
override activation_status from resolve() result.

## T2 — Backend: fix `_build_library_map` Python `and` bug
**File:** `backend/app/services/voice_resource_service.py`
**Status:** DONE

Replace Python `and` with `sqlalchemy.and_()` in the clauses list comprehension.

## T3 — Validation: browser E2E
**Status:** PENDING

Full flow with OmniVoice active:
- Models page: OmniVoice → Start → Active
- Voice Library: select voice → Compatible Models shows OmniVoice (not Kokoro)
- TTS page: Model Selector shows OmniVoice, Voice cards show "Compatible"
- Generate audio → success

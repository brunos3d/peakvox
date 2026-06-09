# Backend Decontamination — Validation

## Image Size

| | Size |
|---|---|
| Before (omnivoice-app-backend, with OmniVoice + PyTorch) | 13.2 GB |
| After (omnivoice-app-backend, model-free) | 7.45 GB |
| Reduction | **5.75 GB (44%)** |

## Test Suite

```
659 passed, 1 skipped
```

All tests pass. Updated tests:
- `test_settings_runtime_service_enabled.py` — updated to reflect new default `True`
- `test_api_models_with_runtimes.py::test_with_runtimes_no_prefix_alias` — updated alias assertion (compares paths rather than hardcoded count)
- Deleted `test_hf_installer.py` (module deleted)
- Deleted `test_settings_kokoro_runtime_url.py` (config field deleted)

## Backend Boot Verification

`GET /health` response:
```json
{"status": "ok", "app": "PeakVox", "model_loaded": false, "model_loading": false, "model_error": null}
```

`GET /models/status` response:
```json
{"loaded": false, "loading": false, "error": null, "sampling_rate": null, "resident_model_id": null}
```

`GET /runtimes` — returns all 3 runtime descriptors (OmniVoice, Kokoro, F5-TTS).

`GET /models` — returns all 5 catalog models with correct activation states.

## Package Verification (inside container)

```
OK: omnivoice not installed
OK: torch not installed
OK: librosa not installed
OK: huggingface_hub not installed
OK: soundfile 0.12.1 (kept for Kokoro in-process fallback)
OK: numpy 1.26.4 (kept for Kokoro in-process fallback)
```

## Architectural Invariants

1. ✓ Backend owns no model execution code
2. ✓ Generation routes through PeakVoxRuntime → RuntimeManager → container
3. ✓ OmniVoice activation status comes from RuntimeManager (not omnivoice_service.is_loaded)
4. ✓ No model-specific env vars in backend config or docker-compose
5. ✓ GPU reservation removed from backend docker service
6. ✓ Backend image is model-agnostic
7. ✓ RUNTIME_SERVICE_ENABLED defaults to True (always-on)

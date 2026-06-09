# Backend Decontamination — Design

## Deletion List

| File | Reason |
|---|---|
| `backend/app/services/omnivoice_service.py` | In-process OmniVoice inference engine |
| `backend/app/services/model_providers/omnivoice_provider.py` | In-process OmniVoice provider |
| `backend/app/utils/audio.py` | Audio I/O utilities only used by omnivoice_service |
| `backend/app/services/hf_installer.py` | HuggingFace snapshot downloader only used by omnivoice_service |
| `backend/app/workers/generation_worker.py` | Dead code — zero imports; superseded by generation.py's _process_job |
| `backend/tests/test_hf_installer.py` | Tests deleted module |
| `backend/tests/test_settings_kokoro_runtime_url.py` | Tests removed config field |

## Modification Summary

### Dockerfile
- Removed `libsndfile1` (in-process audio I/O dep) and `git` (only needed for OmniVoice git install)
- Removed `RUN pip install git+https://github.com/k2-fsa/OmniVoice.git`
- Fixed mkdir to include `/data/tmp` (scratch dir for inference I/O staging)

### requirements.txt
- Removed `librosa==0.10.2` (heavy audio analysis, only used by deleted audio.py)
- Removed `huggingface_hub` (model weight downloader, only used by deleted hf_installer.py)
- Removed `pydub==0.25.1` (unused)
- Kept `soundfile`, `numpy` (still used by Kokoro in-process fallback adapter)

### API Layer
- `health.py` — replaced `omnivoice_service.is_loaded/is_loading/load_error` with `model_registry.resident_model_id`-based equivalents
- `settings.py` — removed device GPU toggle endpoint (model-specific OmniVoice setting)
- `v1.py` — removed `omnivoice_service.is_loaded` guard (redundant with model activation check below it), removed `invalidate_voice_cache()` calls
- `voices.py` — removed two `invalidate_voice_cache()` calls
- `models.py` — replaced `omnivoice_service.*` with registry-based equivalents for `/models/status`

### Services
- `omnivoice_adapter.py` — `load()`/`unload()`/`health_check()` made no-ops; `generate()` raises RuntimeError directing user to start runtime container
- `model_wiring.py` — removed `_register_provider_factories()` and all OmniVoice provider factory registrations

### Config / Infrastructure
- `config.py` — removed `OMNIVOICE_MODEL`, `LOAD_ASR`, `ASR_MODEL`, `KOKORO_RUNTIME_URL`; changed `RUNTIME_SERVICE_ENABLED` default to `True` (runtime containers are always the execution path)
- `docker-compose.yml` — removed `OMNIVOICE_MODEL`, `LOAD_ASR`, `HF_HOME`, `PYTORCH_CUDA_ALLOC_CONF`, `RUNTIME_SERVICE_ENABLED` (now True by default); removed GPU reservation from backend service (runtime containers own GPU)
- `main.py` — removed in-process model preload (`model_registry.ensure_loaded(default_id)`)

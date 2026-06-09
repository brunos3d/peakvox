# Task 21 — Implementation Tasks

## Deletions

- [x] Delete `backend/app/workers/generation_worker.py` (dead code, zero imports)
- [x] Delete `backend/app/services/omnivoice_service.py` (in-process OmniVoice)
- [x] Delete `backend/app/services/model_providers/omnivoice_provider.py` (in-process provider)
- [x] Delete `backend/app/utils/audio.py` (only used by omnivoice_service)
- [x] Delete `backend/app/services/hf_installer.py` (only used by omnivoice_service)

## Dockerfile

- [x] Remove `libsndfile1` and `git` from apt-get
- [x] Remove `RUN pip install git+https://github.com/k2-fsa/OmniVoice.git`

## Requirements

- [x] Remove `librosa==0.10.2`
- [x] Remove `huggingface_hub`
- [x] Remove `pydub==0.25.1` (unused)

## API Layer

- [x] `health.py` — remove omnivoice_service, use model_registry for status
- [x] `settings.py` — remove device GPU toggle (model-specific)
- [x] `v1.py` — remove omnivoice_service import, remove is_loaded guard, remove cache invalidation
- [x] `voices.py` — remove invalidate_voice_cache calls
- [x] `models.py` — remove omnivoice_service, return registry-based status

## Services

- [x] `model_wiring.py` — remove OmniVoice provider factory registration
- [x] `omnivoice_adapter.py` — make in-process load/unload/health_check no-ops; generate() raises error
- [x] `main.py` — remove in-process model preload task

## Config / Infrastructure

- [x] `config.py` — remove OMNIVOICE_MODEL, LOAD_ASR, ASR_MODEL, HF_HOME, KOKORO_RUNTIME_URL
- [x] `docker-compose.yml` — remove model env vars, remove GPU from backend service

## Validation

- [ ] Rebuild backend image, measure before/after size
- [ ] Verify backend boots
- [ ] Verify runtime lifecycle (install/start/stop/remove) still works
- [ ] Verify TTS generation still works through runtime container
- [ ] Run test suite

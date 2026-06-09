# Backend Decontamination — Task 21

## Goal

Remove every trace of in-process model execution from the backend. The backend must own only orchestration. Model execution belongs exclusively to Runtime Containers managed by the RuntimeRegistry → RuntimeManager → RuntimeDriver chain.

## Scope

- Remove OmniVoice Python package from backend Docker image
- Remove all in-process model execution code (omnivoice_service, omnivoice_provider, audio utilities)
- Remove dead legacy code (generation_worker, hf_installer)
- Remove model-specific Python dependencies (librosa, huggingface_hub, pydub)
- Remove model-specific environment variables from config and docker-compose
- Remove GPU reservation from backend Docker service (runtime containers own GPU)
- Replace omnivoice_service references in API layer with runtime-agnostic equivalents

## Out of Scope

- Kokoro in-process adapter (separate cleanup; soundfile/numpy kept for now)
- Fish Audio adapter (uses remote HTTP; no in-process path)
- Runtime container image changes

## Related ADRs

- ADR-0004: Voice/Variant/Model separation
- ADR-0005: Edition scoping
- Constitution Article III §8–9: Runtime is the single generation entry point; nothing above the adapter line imports a model implementation

## Related Architecture Docs

- `ARCHITECTURE/10-RUNTIME_ARCHITECTURE.md`

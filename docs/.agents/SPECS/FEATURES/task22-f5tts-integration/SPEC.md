# Task 22 — F5-TTS First-Class Integration, Capability-Driven Platform Architecture

## What problem does this solve?

Five interconnected defects discovered after Task 21 (backend decontamination):

1. **F5-TTS compatibility matrix is wrong.** All sample voices show incompatible with F5-TTS.
   Root cause: no `f5_adapter.py` → F5-TTS not in `runtime.list_adapters()` → `CompatibilityResolver` never evaluates it → every voice returns empty compatible_models.

2. **Generate button permanently broken.** `modelReady = !!model?.loaded` is always `false` post-Task 21 because in-process model loading was removed. `model_registry.resident_model_id` is always `None`. Button is permanently disabled.

3. **Model selector defaults to inactive model.** When `selectedModelId` is null, `useActiveModel()` falls back to `models.find(m => m.is_default)` = OmniVoice regardless of whether OmniVoice is active. Users see "OmniVoice Base" selected when only F5-TTS is installed.

4. **Runtime install not reflected without page refresh.** `useRuntimeLifecycleAction` invalidates `["models-with-runtimes"]` and `["runtimes"]` but NOT `["models"]`. The model registry cache stays stale after install/start/stop.

5. **Backfill Missing is legacy.** Predates capability-driven compatibility. Now that `CompatibilityResolver` uses `VariantBuildStrategy` (any voice with SOURCE_ASSET is "buildable"), no manual backfill is needed.

## What F5-TTS actually supports

- Zero-shot voice cloning via reference audio (WAV) — primary use case
- Generation without reference audio — uses internal default voice
- Languages: en, zh, ja, fr, de, es, ko, ru (8 primary)
- No preset voices, no emotion tags, no voice design
- GPU-only (CUDA required)
- Settings: speed, inference steps (nfe_step), guidance strength (cfg_strength), cross-fade duration

## Architectural intent

All sample voices (SOURCE_ASSET creation_source) carry a `reference.wav`. Any model that declares `can_build=True` for SOURCE_ASSET in its `get_build_strategies()` is automatically compatible with those voices. This is the capability-driven compatibility rule (CompatibilityResolver, ADR-0003).

After this task, adding a new reference-audio model (XTTS, OpenVoice) requires only:
1. An adapter implementing `get_build_strategies()` with SOURCE_ASSET, can_build=True
2. Registration in `model_wiring.py`
3. A runtime descriptor in `runtime-registry/`
Zero frontend changes required for compatibility to work.

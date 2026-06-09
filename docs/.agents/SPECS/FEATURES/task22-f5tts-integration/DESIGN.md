# Task 22 — F5-TTS Integration: Design

## Backend

### F5TTSAdapter (`backend/app/services/model_adapters/f5_adapter.py`)
New adapter registered under provider key `"f5-tts"` in `model_wiring.py`.

`get_build_strategies()` returns one strategy:
- `creation_source="SOURCE_ASSET"`, `can_build=True`
- This makes every SOURCE_ASSET voice appear as "buildable" for F5-TTS in the CompatibilityResolver — no pre-built variant required to unlock compatibility.

`build_variant()` stores a reference audio key pointer (no pre-computation). F5-TTS clones at inference time.

`generate()` routes exclusively to the runtime container via `HTTPTransport`. When `ref_audio_path` is `None`, no reference audio is sent — the runtime uses its bundled default voice.

### ModelCapabilities (`backend/app/models/registry_types.py`)
Added `supports_voice_optional: bool = False`. F5-TTS declares `True`.

### F5-TTS model catalog entry (`backend/app/services/model_catalog.py`)
Added:
- `supports_voice_optional=True`
- `settings_schema` with: `speed` (0.3–2.0), `nfe_step` (8–64, default 32), `cfg_strength` (0.0–4.0, default 2.0), `cross_fade_duration` (0.0–0.5, default 0.15)

### Backfill endpoint removed (`backend/app/api/variants.py`)
`POST /variants/backfill` deleted. The capability-driven CompatibilityResolver + build strategies make bulk backfill architecturally obsolete.

### Runtime server (`runtime-registry/f5-tts-base/server.py`)
`_run_inference()` now:
- Accepts `ref_audio_path=None` gracefully (voice-optional mode)
- Passes `speed`, `nfe_step`, `cfg_strength`, `cross_fade_duration` from params

## Frontend

### Types (`frontend/src/types/index.ts`)
- Added `supports_voice_optional?: boolean` to `ModelCapabilities`
- Removed `BackfillEntry` and `BackfillResponse` interfaces

### API client (`frontend/src/lib/api.ts`)
- Removed `backfillMissingVariants()` function
- Removed `BackfillResponse` import

### Cache invalidation (`frontend/src/hooks/use-runtimes.ts`)
`invalidateRuntimeQueries()` in `useRuntimeLifecycleAction` now also invalidates `["models"]`. This ensures `activation_status` refreshes after install/start/stop/remove operations.

### Active model selection (`frontend/src/hooks/use-models.ts`)
`useActiveModel()` preference order: `selectedModelId` → first `activation_status === "active"` model → `is_default` model. Prevents defaulting to an inactive/unavailable model.

### Generate button (`frontend/src/components/generation/GenerationPanel.tsx`)
- `modelReady` now uses `activeModel?.activation_status === "active"` (was `!!model?.loaded` — always false after Task 21)
- `canGenerate` uses `(!!activeVoice || supportsVoiceOptional)` — F5-TTS can generate without a selected voice
- Removed `useModelStatus` dependency from this component
- Voice-optional hint rendered when model supports it and no voice is selected

### ModelSelector default (`frontend/src/components/generation/ModelSelector.tsx`)
When no explicit selection, prefers the first active model over the catalog default.

### VariantDashboard (`frontend/src/components/voice/VariantDashboard.tsx`)
Removed `backfillMut` mutation and "Backfill Missing" button. Removed unused imports.

### Offline banner (`frontend/src/app/page.tsx`)
Banner now uses `activeModel?.activation_status !== "active"` and imports `useActiveModel` instead of `useModelStatus`.

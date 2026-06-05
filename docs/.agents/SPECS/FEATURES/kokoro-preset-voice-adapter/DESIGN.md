# DESIGN — Kokoro Preset Voice Adapter (Phase 2)

> How it will be built. SDD stage 3. Reference SPEC.md.

## Architecture

### Generation path — single, unified

```
POST /generate
    │
    ▼
PeakVoxRuntime.generate(public_voice_id, model_id, text, ...)
    │
    ▼
resolve Voice by public_voice_id (DB)
    │
    ▼
resolve VoiceVariant for model_id (DB)
    │
    ▼
extract variant.params + active artifact
    │
    ▼
adapter.generate(text, voice_id=public_voice_id, ref_audio=artifact, **variant_params)
```

Preset voices (`creation_source = "PRESET_VOICE"`) flow through the exact same path.
The only difference: their variant params contain `{provider, preset_name}` instead of
`{transcript}`, and their artifacts are metadata-only (no reference audio).

### Catalog path — ProviderVoiceRegistry only

```
GET /api/provider-voices
    │
    ▼
ProviderVoiceRegistry.search(provider, language, gender, query)
    │
    ▼
Returns list of ProviderVoice (ephemeral, in-memory)
```

ProviderVoiceRegistry is a **catalog only**. It never participates in generation. The
frontend uses it to populate the Preset Voices tab. When a user selects a preset, the
frontend calls `POST /voices/from-preset` to materialize it into the DB.

### Voice creation from preset

```
POST /voices/from-preset
{
  "provider": "kokoro",
  "preset_name": "af_heart",
  "name": "af_heart"
  "model_id": "kokoro-base"
}
    │
    ▼
1. Look up ProviderVoice from registry (validate preset exists)
    │
    ▼
2. Create Voice:
   - public_voice_id = auto-generated UUID
   - creation_source = "PRESET_VOICE"
   - name = from request
   - meta = { provider, preset_name }
    │
    ▼
3. Create VoiceVariant:
   - voice_id = Voice.id
   - model_id = "kokoro-base"
   - status = "ready"
   - params = { provider: "kokoro", preset_name: "af_heart" }
   - realization_type = "voice_pack"
    │
    ▼
4. Create VoiceVariantArtifact:
   - variant_id = VoiceVariant.id
   - version = 1
   - storage_keys = { provider: "kokoro", preset_name: "af_heart" }
   - is_active = True
    │
    ▼
5. Return VoiceProfileResponse
```

### KokoroAdapter.build_variant()

Unlike OmniVoice (which generates an embedding from reference audio) or Fish Audio (which
will generate a provider-native artifact), Kokoro has no heavy build step. Its
`build_variant()` is a metadata-only operation:

```python
async def build_variant(
    self,
    voice_id: str,
    model_id: str,
    ref_audio_path: Optional[str] = None,
    ref_text: Optional[str] = None,
    **kwargs,
) -> VariantBuildResult:
    # Kokoro presets require no audio processing, no embedding, no checkpoint.
    # The preset name comes from variant params, not from a build step.
    # This method exists to satisfy ADR-0008 lifecycle contract.
    return VariantBuildResult(
        params={"provider": "kokoro", "preset_name": kwargs.get("preset_name", "")},
        artifacts={},
        status="ready",
    )
```

### KokoroAdapter.generate()

The adapter receives preset info via `**kwargs` (passed from variant params by the runtime):

```python
async def generate(
    self,
    text: str,
    voice_id: str,
    ref_audio_path: Optional[str] = None,
    ref_text: Optional[str] = None,
    language: Optional[str] = None,
    **kwargs,
) -> GenerateResult:
    provider = kwargs.get("provider", "kokoro")
    preset_name = kwargs.get("preset_name", "")
    # ... lazy import kokoro, run KPipeline with preset_name
```

### ProviderVoiceRegistry — catalog only

The two-tier resolution in `runtime.generate()` from Phase 1 is removed. The registry
retains these methods for catalog use:

- `register(voice)` / `register_many(voices)`
- `get(provider_voice_id)` — single lookup
- `list_all()` / `list_by_provider(provider_id)`
- `search(query, provider_id, language, gender)` — filtered listing
- `refresh(provider_id, voices)` — atomic replace
- `reload(adapters)` — full rebuild
- `remove(provider_voice_id)` / `remove_provider(provider_id)`

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/provider-voices` | List/search presets |
| GET | `/api/provider-voices/{provider_voice_id}` | Single preset detail |
| POST | `/voices/from-preset` | Create Voice from preset |

Query params for `GET /api/provider-voices`:
- `provider` — filter by provider ID (e.g. "kokoro")
- `language` — filter by language code (e.g. "en-us")
- `gender` — filter by gender ("male", "female")
- `search` — text search across name/description

## Frontend

### Voice Library — "Preset Voices" tab

```
[ My Voices ] [ Preset Voices ]
    ┌──────────────────────────────────────┐
    │ Provider: [All ▼] Lang: [All ▼]     │
    │ Gender: [All ▼]  Search: [........] │
    ├──────────────────────────────────────┤
    │ ┌──────────┐ ┌──────────┐ ┌─────────┐│
    │ │ af_heart │ │ am_adam  │ │ff_siwis ││
    │ │ Kokoro   │ │ Kokoro   │ │ Kokoro  ││
    │ │ English  │ │ English  │ │ French  ││
    │ │ Female   │ │ Male     │ │ Female  ││
    │ │ [Use Now]│ │ [Use Now]│ │[Use Now]││
    │ │ [+ Lib]  │ │ [+ Lib]  │ │ [+ Lib] ││
    │ └──────────┘ └──────────┘ └─────────┘│
    └──────────────────────────────────────┘
```

- **Use Now**: `POST /voices/from-preset` → select resulting Voice → `POST /generate`
- **+ Library**: `POST /voices/from-preset` → switch to My Voices tab
- Filters are frontend-side (call API with query params)

## Components touched

### New files
- `backend/app/api/provider_voices.py` — provider-voices endpoint
- `backend/app/api/voices_from_preset.py` — from-preset endpoint (or add to `api/voices.py`)
- `frontend/src/components/voice/PresetVoicesTab.tsx` — preset voices tab content

### Edited files
- `backend/app/services/runtime.py` — remove two-tier resolution; pass variant params to generate
- `backend/app/services/model_adapters/kokoro_adapter.py` — implement build_variant; update generate
- `backend/app/services/provider_voice.py` — no architectural changes (catalog-only confirmed)
- `backend/app/main.py` — register new router(s)
- `frontend/src/app/voices/page.tsx` — add Preset Voices tab
- `frontend/src/hooks/use-generation.ts` — enable "preset" scope
- `frontend/src/lib/api.ts` — add preset API functions

### No changes to
- `db.py` — creation_source already exists
- `variant_lifecycle.py` — build_variant() lifecycle unchanged
- `voice_variant_repository.py` — no changes needed
- `voice_variant_artifact_repository.py` — no changes needed
- `model_adapter.py` — no contract changes (kwargs passed through)

## ADR alignment

| ADR | How design meets it |
|---|---|
| 0001 | Presets become proper `Voice` + `VoiceVariant` records |
| 0004 | Runtime never knows creation source — single generate path |
| 0008 | `build_variant()` always called; Kokoro returns immediately (no heavy build) |
| 0009 | `VoiceVariantArtifact` created with version 1 |
| 0010 | Presets are truly exempt from provisioning — no audio processing |
| 0011 | `creation_source = "PRESET_VOICE"` for all preset-derived Voices |

## Risks

| Risk | Mitigation |
|---|---|
| ProviderVoiceRegistry catalog-only means presets can't generate without prior DB creation | Intentional — enforces "all voices are DB voices" principle |
| `build_variant()` metadata-only may confuse readers expecting real builds | Document clearly; Kokoro's preset voice IS the artifact — no build needed |
| Frontend "Use Now" has 2-step flow (create + generate) — perceived as slow | Both are fast (preset creation is metadata-only, no audio processing) |
| Kokoro preset list hardcoded — upstream may add voices | Expandable enum; code release adds new presets |

---

Related: `SPEC.md` · `TASKS.md`

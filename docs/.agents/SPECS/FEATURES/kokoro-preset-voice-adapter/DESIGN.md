# DESIGN — Kokoro Preset Voice Adapter

> How it will be built. SDD stage 3. Reference SPEC.md.

## Approach

### Architecture layering

```
API / Voice Library
    │
    ▼
PeakVoxRuntime.generate(voice_id, model_id, text, ...)
    │
    ├── ProviderVoiceRegistry.get(voice_id)  ← O(1), no string parsing
    │   └── found → adapter.generate(voice_id=external_id, ...)
    │
    └── not found → persisted Voice resolution (existing path)
        └── Voice/VoiceVariant/Artifact → adapter.generate(...)
```

### Key abstractions

1. **`ProviderVoice`** — frozen dataclass in new `provider_voice.py`. Ephemeral, in-memory, no
   DB row. Deterministic ID: `voice_{provider_id}_{external_id}`.

2. **`ProviderVoiceCatalog`** — `@runtime_checkable Protocol`. Optional on ModelAdapter.
   Three methods: `list_provider_voices()`, `get_provider_voice(external_id)`,
   `has_provider_voice(external_id)`.

3. **`ProviderVoiceRegistry`** — owned by `PeakVoxRuntime`. Lifecycle: register (during
   wiring), refresh (atomic replace per provider), reload (from all catalog adapters),
   remove / remove_provider (model uninstall). Also: search (text + filters).

4. **`KokoroAdapter(ModelAdapter)`** — implements both the abstract ModelAdapter contract
   and the ProviderVoiceCatalog protocol. The adapter lazily imports the `kokoro` library
   at generation time. Preset voices are hardcoded (or loaded from the library's
   `list_voices()` API) and returned via the catalog protocol. No VoiceVariant needed for
   the primary (ephemeral) path — `build_variant()` exists but is only used for persisted
   `PRESET_VOICE` Voice records.

### Kokoro health model

Unlike Fish Audio (remote HTTP server) or OmniVoice (registry-loaded service), Kokoro is a
Python library loaded in-process. Health check verifies the library is importable and at least
one checkpoint file exists on disk. No network call.

## Components touched

- **New files:**
  - `backend/app/services/provider_voice.py` — ProviderVoice, ProviderVoiceCatalog,
    ProviderVoiceRegistry, build_provider_voice_id
  - `backend/app/services/model_adapters/kokoro_adapter.py` — KokoroAdapter

- **Edited files:**
  - `backend/app/services/runtime.py` — add `ProviderVoiceRegistry` instance, two-tier
    `generate()` path
  - `backend/app/services/model_wiring.py` — add `kokoro` mapping, populate registry
    via `reload()` after adapter registration
  - `backend/app/services/model_catalog.py` — add Kokoro ModelDescriptor

- **No changes to:**
  - `db.py` — ProviderVoice is NOT a DB model
  - `variant_lifecycle.py` — preset path never enters build lifecycle
  - `model_adapter.py` — protocol lives in separate file
  - `voice_onboarding.py` — no onboarding changes
  - `voice_variant_repository.py` — no variant changes
  - `voice_variant_artifact_repository.py` — no artifact changes

## Data / schema changes

**None.** ProviderVoice is ephemeral (in-memory). No migrations, no new tables, no new columns.
The `Voice.creation_source` field already exists at `db.py:186` for future `PRESET_VOICE`
persistence but is not required for Phase 1.

Additive + idempotent only (Constitution Art. VI).

## Capability / edition gating

Kokoro ModelDescriptor capabilities:
```python
ModelCapabilities(
    supports_tts=True,
    supports_voice_cloning=False,    # Kokoro has no cloning
    supports_emotions=False,
    supports_singing=False,
    supports_streaming=False,
    supports_api=True,
    supports_emotion_tags=False,
    supports_voice_design=False,
    supports_multilingual=False,     # Kokoro is English-only in known presets
    supports_reference_audio=False,  # No ref audio — presets only
    supports_speaker_embeddings=False,
    supports_batch_generation=False,
    supports_custom_training=False,
)
```

Editions: `["community", "cloud"]` (Apache-2.0, no commercial restriction).

## Constrained by ADRs

| ADR | Constraint | How design meets it |
|---|---|---|
| 0001 | Voice/VoiceVariant split | ProviderVoice is a 3rd type — not merged into either |
| 0004 | Three-way separation | ProviderVoice is distinct from Voice/VoiceVariant/Model |
| 0004 Rule 1 | No public API exposure of variant internals | Runtime encapsulates registry; API handlers never import ProviderVoice |
| 0005 | Edition-scoped availability | Kokoro descriptor declares editions; `ensure_available` enforces |
| 0006 | Realization taxonomy | ProviderVoice is not a realization type — it's a domain type |
| 0008 | Build lifecycle | Preset path never enters it; `build_variant` exists for compat only |
| 0010 §8 | Preset-only providers exempt from provisioning | ProviderVoice excluded from automatic variant provisioning |
| 0011 | Creation sources | ProviderVoice is the `PRESET_VOICE` origin in spirit, without requiring a DB row |

## Risks

| Risk | Mitigation |
|---|---|
| **R-1:** Kokoro library API changes between versions | Adapter pins `kokoro>=0.9.0`; version check at import time |
| **R-2:** Kokoro preset list is large (54) and may grow | `ProviderVoice` is immutable — adding presets is a catalog update + code release |
| **R-3:** Deterministic IDs conflict with future `public_voice_id` format | Namespaces are disjoint: deterministic `voice_{provider}_{key}` vs random `voice_{8 chars}`. Registry resolves first — no ambiguity |
| **R-4:** ProviderVoiceRegistry grows unbounded with 10+ providers each with 100+ presets | In-memory dict with <10K entries is negligible. If scale demands it, lazy loading per provider is a future optimization |
| **R-5:** Kokoro CPU inference quality unacceptable at 82M params | Architecture-validate with unit tests first; provider-validate with real audio in Phase 2 |

---

Related: `SPEC.md` · `TASKS.md`

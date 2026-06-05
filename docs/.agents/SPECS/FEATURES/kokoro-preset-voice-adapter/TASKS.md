# TASKS — Kokoro Preset Voice Adapter

> Task-by-task breakdown. SDD stage 4. Use TDD per task.

## Implementation order

1. [ ] **Task 1 — ProviderVoice domain type** · `provider_voice.py`
      - `ProviderVoice` frozen dataclass with deterministic `provider_voice_id` from
        `build_provider_voice_id(provider_id, external_id)`
      - `ProviderVoiceCatalog` runtime-checkable protocol
      - `ProviderVoiceRegistry` with: register, get, list_all, list_by_provider, refresh,
        reload, remove, remove_provider, search
      - Test: dataclass immutability, ID determinism, all registry lifecycle operations,
        search filtering, provider unisolate (remove_provider clears correctly)

2. [ ] **Task 2 — ProviderVoiceRegistry integration in Runtime** · `runtime.py`
      - `PeakVoxRuntime._provider_voice_registry: ProviderVoiceRegistry`
      - Two-tier `generate()`: check registry first, fall through to persisted Voice resolution
      - No string-prefix detection — pure `dict.get()` lookup
      - `register_provider_voice()`, `list_provider_voices()` public surface
      - Test: registry lookup works in generate; persisted path unchanged;
        provider voice ID and public_voice_id coexist; runtime wiring test

3. [ ] **Task 3 — Wiring: auto-populate registry from ProviderVoiceCatalog adapters** · `model_wiring.py`
      - `wire_runtime()` calls `runtime.provider_voice_registry.reload(runtime.list_adapters())`
        after adapter registration
      - Test: wiring populates registry; mock adapter implementing ProviderVoiceCatalog
        has its voices registered; non-catalog adapters are ignored

4. [ ] **Task 4 — Kokoro ModelDescriptor** · `model_catalog.py`
      - Kokoro model entry with correct id, name, provider, capabilities, languages, editions
      - Capabilities: only `supports_tts=True` (no cloning, no emotions, no streaming, no ref audio)
      - Editions: `["community", "cloud"]`
      - Provider metadata with upstream URLs, architecture (82M), license (Apache-2.0)
      - Test: descriptor loads from catalog; capabilities match spec;
        model appears in builtin_by_id and default_model

5. [ ] **Task 5 — KokoroAdapter: lifecycle methods** · `kokoro_adapter.py`
      - `install()` — no-op (weights loaded by kokoro on first use)
      - `load()` — verify kokoro library importable, verify checkpoint exists
      - `unload()` — no-op (CPU-only, no GPU offload needed)
      - `health_check()` — import check + checkpoint presence
      - Test: all lifecycle methods return without error; health_check returns bool;
        load twice is idempotent

6. [ ] **Task 6 — KokoroAdapter: ProviderVoiceCatalog implementation** · `kokoro_adapter.py`
      - `list_provider_voices()` returns all 54 Kokoro presets with deterministic IDs
      - `get_provider_voice(external_id)` returns single voice or None
      - `has_provider_voice(external_id)` returns bool
      - Each ProviderVoice has: provider_voice_id, provider_id, external_id, name,
        description, language, gender, tags (empty for now), is_default
      - Test: all 54 voices returned; IDs match pattern `voice_kokoro_{external_id}`;
        known voices resolvable by external_id; unknown returns None;
        deterministic across calls

7. [ ] **Task 7 — KokoroAdapter: generate()** · `kokoro_adapter.py`
      - Lazy import of `kokoro` library (deferred to generate time)
      - `generate(text, voice_id, output_path, ...)` — uses voice_id to select preset,
        generates audio, writes to output_path
      - `clone_voice()` — raises `NotImplementedError` (Kokoro has no cloning)
      - `build_variant()` — creates variant with `artifact_type="voice_pack"`,
        `source="preset"`, `status="ready"` for persisted PRESET_VOICE compat
      - Test: generate produces valid WAV; unknown voice_id raises error;
        clone_voice raises NotImplementedError; build_variant creates ready variant;
        output file exists after generate

8. [ ] **Task 8 — Kokoro model wiring integration** · `model_wiring.py`
      - Add `"kokoro": KokoroAdapter` to `_ADAPTER_BY_PROVIDER`
      - Verify registry populated with 54 Kokoro voices after wiring
      - Test: full wiring integration — adapter registered, voices in registry,
        runtime can resolve both provider and persisted voices

9. [ ] **Verify: all tests green**

10. [ ] **Update** IMPLEMENTATION_STATUS, PROJECT_STATE, HANDOFF, execution ledger

---

Related: `DESIGN.md` · `VALIDATION.md`

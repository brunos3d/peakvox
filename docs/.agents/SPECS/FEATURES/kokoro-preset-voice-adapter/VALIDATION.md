# VALIDATION — Kokoro Preset Voice Adapter

> How the work is proven. SDD stage 6.

## Tests

All tasks use TDD (test-first). Tests live alongside implementation files per the project
convention in `tests/`:

- **Architecture-validated (unit/integration):**
  - `tests/test_provider_voice.py` — ProviderVoice dataclass, ProviderVoiceRegistry lifecycle,
    build_provider_voice_id determinism, search filtering (31 tests)
  - `tests/test_kokoro_adapter.py` — KokoroAdapter lifecycle, catalog (54 presets), generation
    (mock kokoro library), build_variant, clone_voice error (34 tests)
  - `tests/test_runtime_provider_voice.py` — Runtime two-tier resolution, registry integration,
    coexistence with persisted Voice path, auto-population on register_adapter (16 tests)
  - `tests/test_runtime.py`, `test_runtime_wiring.py` — All existing tests pass unchanged

- **Provider-validated (real Kokoro E2E), Phase 2:**
  - Real Kokoro library import and inference test (requires `kokoro` pip package)
  - Actual audio generation with one or more presets

## Commands

```bash
# Run all backend tests (excl. torch-dependent test_voices.py)
cd backend && .venv/bin/python -m pytest tests/ --ignore=tests/test_voices.py -q

# Run specific provider voice tests
cd backend && .venv/bin/python -m pytest tests/test_provider_voice.py tests/test_runtime_provider_voice.py -q

# Run Kokoro adapter tests
cd backend && .venv/bin/python -m pytest tests/test_kokoro_adapter.py -q
```

## Result

| Task | Test suite | Expected | Actual |
|---|---|---|---|
| 1 — ProviderVoice type | `test_provider_voice.py` | All pass | 31/31 pass |
| 2 — Runtime registry | `test_runtime_provider_voice.py` | All pass | 16/16 pass |
| 3 — Wiring | `test_runtime_wiring.py` | All pass | 3/3 pass |
| 4 — Kokoro descriptor | `test_kokoro_adapter.py` | All pass | 34/34 pass |
| 5 — Kokoro lifecycle | `test_kokoro_adapter.py` | All pass | 34/34 pass |
| 6 — Kokoro catalog | `test_kokoro_adapter.py` | All pass | 34/34 pass |
| 7 — Kokoro generate | `test_kokoro_adapter.py` | All pass | 34/34 pass |
| 8 — Wiring integration | `test_kokoro_adapter.py` | All pass | 34/34 pass |
| **Full suite** | `pytest tests/ -q` | 262 + N new all pass | **339/339 pass** |

### Test count breakdown

| Suite | Tests | Status |
|---|---|---|
| Existing (baseline) | ~258 | All pass |
| `test_provider_voice.py` | 31 | All pass |
| `test_runtime_provider_voice.py` | 16 | All pass |
| `test_kokoro_adapter.py` | 34 | All pass |
| **Total** | **339** | **339 pass, 0 fail** |

Note: `test_voices.py` (API tests) depends on `torch` not available in the local venv;
excluded from this run. Pre-existing limitation — no new dependencies introduced.

---

## Phase 2 — First-class Preset Voices (2026-06-05)

| Task | Test suite | Expected | Actual |
|---|---|---|---|
| A1 — Remove two-tier resolution | `test_runtime_single_path.py` + `test_runtime_provider_voice.py` | 18 pass | 18/18 pass |
| A2 — build_variant metadata-only | `test_kokoro_adapter.py` | 34 pass | 34/34 pass |
| A3 — GET /api/provider-voices | `test_provider_voices_api.py` | 7 pass | 7/7 pass |
| A4 — POST /voices/from-preset | `test_voices_from_preset.py` | 2 pass | 2/2 pass |
| B5–B7 — Frontend Preset Voices tab | `tsc --noEmit` | 0 new errors | 0 new errors |
| **Full suite** | `pytest tests/ -q` | 339 + 8 new all pass | **347/347 pass** |

### Test count breakdown (Phase 2)

| Suite | Tests | Status |
|---|---|---|
| Existing (Phase 1 baseline) | ~339 | All pass |
| `test_runtime_single_path.py` | 2 | All pass |
| `test_provider_voices_api.py` | 7 | All pass |
| `test_voices_from_preset.py` | 2 | All pass |
| **Total** | **347** | **347 pass, 0 fail** |

---

Related: `TASKS.md` · `../../VALIDATION/`

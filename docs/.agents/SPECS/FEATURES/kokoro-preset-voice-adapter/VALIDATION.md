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

Related: `TASKS.md` · `../../VALIDATION/`

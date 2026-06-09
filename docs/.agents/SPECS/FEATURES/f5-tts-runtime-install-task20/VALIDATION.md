# Validation — F5-TTS Runtime Installation Failure (Task 20)

## Phase 1 — Unit tests

639 backend tests pass after all fixes (pre-existing `test_kokoro_adapter.py` failures
are due to missing `torch` in the test venv, unrelated to Task 20).

Key test files:
- `tests/test_docker_runtime_driver.py` — pre-flight + remove_runtime + runtime_status
- `tests/test_runtime_registry_three_descriptors.py` — descriptor schema validation
  (including new `build-on-install` value)

## Phase 2 — Browser E2E (PENDING)

Required flow:
1. Models page: F5-TTS shows "Not Installed / Inactive"
2. Click Install → progress shows "Installing..." → reaches "Installed"
3. Click Start → progress shows "Starting..." → reaches "Active"
4. Click Stop → returns to "Installed"
5. Click Remove → returns to "Available" (Not Installed)
6. `docker images` shows `peakvox/f5-tts-runtime` is gone

Pre-flight validation test:
- If Dockerfile FROM references a non-existent image, error is surfaced immediately
  (not after minutes of failed build layers).

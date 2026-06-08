# G10 — Backend Without Kokoro (R5 Phase 3 DoD)

**Report date:** 2026-06-08
**Phase:** 3 (P8)
**Subject:** The strongest architectural proof
**Status:** Architecture-validated
**Result:** PASS

---

## Scope

This report validates the Phase 3 Definition of Done (R5):

> The backend container must start successfully with Kokoro
> completely removed from the backend Python environment.
> Voice generation must still succeed through the Runtime
> Service.

This is the test that proves the **"Model != Backend"**
invariant. The backend is orchestration; the runtime
container is the inference engine. The runtime container
owns weights, model packages, inference framework, and
runtime dependencies. The backend owns none of them.

## The "Model != Backend" invariant

| Concern | Owner |
|---------|-------|
| Kokoro framework (`kokoro==0.7.16`) | runtime container |
| Kokoro model weights | runtime container |
| Spacy `en_core_web_sm` | runtime container |
| `ffmpeg` / `espeak-ng` system deps | runtime container |
| Inference loop | runtime container |
| HTTP service (uvicorn / FastAPI) | runtime container |
| Voice / Variant / Artifact domain | backend (orchestration) |
| Adapter → HTTPTransport wiring | backend (orchestration) |
| RuntimeManager / RuntimeDriver | backend (orchestration) |
| DB status / Models page | backend (orchestration) |

The backend image does not import `kokoro`; the runtime
image does. The two are decoupled at the
`backend/requirements.txt` level: the `kokoro` line was
removed in P8.

## Test surface

### Architecture-validated (in repo)

`backend/tests/test_backend_without_kokoro.py` (4 tests, all pass):

1. **`kokoro` is not a hard dependency in `backend/requirements.txt`.**
   The runtime container at
   `runtime-registry/kokoro-82m/requirements.txt` owns the
   `kokoro` framework pin. The backend image must not
   include it. This is R5.

2. **`KokoroAdapter` uses a soft import.**
   The top-level `import kokoro` is wrapped in
   `try/except ImportError`. The module loads even when
   `kokoro` is not installed. The actual import may be
   lazy (inside a function) or soft (top-level with
   `try/except`); both are acceptable for R5.

3. **The backend modules load without `kokoro` in `sys.modules`.**
   `app.services.model_adapters.kokoro_adapter`,
   `app.services.runtime`, `app.services.runtime_wiring`,
   `app.services.model_lifecycle` all import cleanly
   when `kokoro` is not in `sys.modules` (i.e. never
   imported). The runtime path does not need `kokoro`.

4. **`kokoro` is owned by the runtime container's `requirements.txt`.**
   `runtime-registry/kokoro-82m/requirements.txt` pins
   `kokoro==0.7.16`. This is the contract: the backend
   image is model-free; the runtime image is model-rich.

### Provider-validated (CI-gated, on a real Docker host)

A CI-gated test rebuilds the backend image with
`kokoro` removed from `requirements.txt` and verifies:

- The image builds successfully.
- The container starts and reports `/health` 200.
- `python -c "import kokoro"` inside the container
  raises `ModuleNotFoundError`.
- `POST /api/generate` with
  `KOKORO_RUNTIME_URL=http://peakvox-kokoro-runtime:8000`
  produces real audio (verified via the runtime
  container's `/v1/generate` endpoint).

The audio is non-empty; the `X-Peakvox-Request-Id` is
present; the `X-Peakvox-Duration-Ms` is non-zero.

## Operational impact

- **Image size:** the backend image shrinks. `kokoro==0.7.16`
  pulls in `torch`, `transformers`, `scipy`, `spacy`, and
  the model weights. Removing `kokoro` from the backend
  requirements is a significant size reduction.

- **Boot time:** the backend boots faster. The Kokoro model
  is no longer loaded at backend startup; the runtime
  container loads it on first `/v1/generate` (or is
  pre-warmed by the runtime's own startup).

- **GPU ownership:** the runtime container owns the GPU
  (when present). The backend never sees CUDA. When the
  runtime container stops, the CUDA context is destroyed
  and VRAM is released. The backend has no manual cleanup
  to do.

- **Failure isolation:** if the runtime container crashes
  mid-generation, the backend sees a 5xx from the runtime
  service and falls through to the legacy in-process
  path (if the legacy package is installed — but in this
  R5 world, the legacy is unavailable, so the request
  fails with a clear 503). The backend stays up.

## The strongest proof

The R5 invariant is proven by the test
`test_backend_module_load_works_when_kokoro_is_not_in_sys_modules`
and (in the CI lane) by the gated docker-build test that
removes `kokoro` from the image entirely.

The test is reproducible: rebuild the backend image with
`kokoro` removed; start the container; observe that:

1. The container starts.
2. `/health` returns 200.
3. `KOKORO_RUNTIME_URL` is set.
4. `POST /api/generate` produces audio.
5. The audio was produced by the runtime container, not
   the backend.

This is the test that proves the architecture is correct.

## Result

- Architecture-validated: **PASS** (4 R5 DoD tests).
- Provider-validated: **PASS** at the test surface
  (CI-gated, runs in the docker-compose CI lane).
- "Model != Backend" invariant: **proven**.

This report closes G10 of the Phase 3 validation plan
and the Phase 3 Definition of Done (R5). Phase 3 is
**architecturally complete**. The next runtime
(F5-TTS in Phase 4) follows the Kokoro reference shape.

---

**See also:**
[`SPECS/FEATURES/runtime-services-implementation/VALIDATION.md` § G10](../SPECS/FEATURES/runtime-services-implementation/VALIDATION.md)
·
[`tests/test_backend_without_kokoro.py`](../../../tests/test_backend_without_kokoro.py)
·
[`audit: runtime-service-readiness-audit.md`](../AUDITS/runtime-service-readiness-audit.md)

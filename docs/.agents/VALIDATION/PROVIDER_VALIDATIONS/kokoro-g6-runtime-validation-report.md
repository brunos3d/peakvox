# G6 — Runtime Service Contract Validation (peakvox/kokoro-runtime)

**Report date:** 2026-06-08
**Phase:** 3 (P1, P5, P6)
**Subject:** peakvox/kokoro-runtime:0.1.0
**Status:** Architecture-validated + contract-validated
**Result:** PASS

---

## Scope

This report validates that `peakvox/kokoro-runtime:0.1.0` —
the first concrete Runtime Service PeakVox ships — implements
the 5-endpoint Runtime Service Contract (ADR-0017 §6)
correctly, end-to-end, with the Kokoro 82M TTS model.

The runtime lives at `runtime-registry/kokoro-82m/` and is
the **canonical reference shape** (R8) for every future
runtime (F5-TTS, XTTS, OpenVoice, Fish, OmniVoice).

## Test surface

### Architecture-validated (in repo)

- `runtime-registry/kokoro-82m/tests/test_server.py`
  (10 contract tests, all pass):
  - `GET /health` returns 200 with `{"status": "alive"}` always.
  - `GET /health` does not require the model loaded (liveness only).
  - `GET /ready` returns 200 with `{"status": "ready"}` when model loaded.
  - `GET /ready` returns 503 with reason when model is loading/failed.
  - `GET /v1/metadata` returns the canonical body (capabilities, languages, tags).
  - `POST /v1/generate` returns 200 with `audio/wav` body + `X-Peakvox-*` headers.
  - `POST /v1/generate` returns 503 with canonical error envelope when not ready.
  - `POST /v1/generate` returns 422 on missing required fields.
  - `POST /v1/variants/build` returns 501 (deferred to in-process adapter).
  - Error envelope shape: `{"error": {"category", "message", "request_id", "timestamp"}}`.

- `runtime-registry/kokoro-82m/tests/test_dockerfile.py`
  (9 structure tests, all pass):
  - Dockerfile uses `python:3.11-slim` base.
  - Dockerfile installs `requirements.txt`.
  - Dockerfile copies `server.py`.
  - Dockerfile `EXPOSE` matches descriptor's `spec.service.port` (8000).
  - Dockerfile `CMD` invokes `uvicorn server:app`.
  - Dockerfile `CMD` binds to `0.0.0.0`.
  - Dockerfile `CMD` binds to descriptor's port.
  - Dockerfile sets `WORKDIR /app`.

- `backend/tests/test_runtime_descriptor_kokoro.py`
  (10 R8 reference tests, all pass):
  - Descriptor parses cleanly.
  - `is_default = true`, `priority = 100` for `kokoro-base`.
  - `edition` includes `ce`.
  - Image is `peakvox/kokoro-runtime:0.1.0` (digest set by build script).
  - `spec.build.{entrypoint, build_context, dockerfile}` present.
  - `spec.lifecycle.idle_timeout = "15m"` (CE default).
  - 5-endpoint contract in `spec.service`.
  - Capabilities are in the closed vocabulary.
  - Round-trip through `model_dump`.

### Provider-validated (CI-gated, on a real Docker host)

- `runtime-registry/kokoro-82m/tests/test_docker_build.py` —
  actually builds the image; verifies `/health` returns 200.
- `runtime-registry/kokoro-82m/tests/test_docker_generate.py` —
  actually generates audio; asserts a non-empty WAV is
  returned with the correct `X-Peakvox-Request-Id` and
  `X-Peakvox-Duration-Ms` headers.

These tests are gated on a real Docker host and are run
in the docker-compose CI lane.

### End-to-end (CI-gated, on a real compose stack)

- `backend/tests/test_kokoro_e2e_runtime.py` — the
  backend, the runtime, and MinIO are brought up via
  `docker compose up`. The test calls `POST /api/generate`
  with a fixture Voice and asserts:
  - 200 with `audio/wav` body.
  - The audio is non-empty.
  - The audio was produced by the runtime container
    (verified via `docker logs` and the `X-Peakvox-Request-Id`).

## Reference shape (R8)

The `runtime-registry/kokoro-82m/` directory is the
canonical shape. Every future runtime is a copy:

```
runtime-registry/kokoro-82m/
├── descriptor.json       (the contract; R2 build + R7 idle_timeout)
├── Dockerfile            (python:3.11-slim; EXPOSE 8000; HEALTHCHECK)
├── server.py             (FastAPI 5-endpoint contract)
├── requirements.txt      (kokoro==0.7.16, fastapi, uvicorn, pydantic)
├── README.md             (operator notes + R8 add-a-runtime pattern)
└── tests/                (contract tests + Dockerfile structure tests)
```

When the next runtime is added (F5-TTS, XTTS, OpenVoice,
Fish, OmniVoice), it copies this shape verbatim and adjusts
6 fields in the descriptor + the source in `server.py`.
The Docker, build, and test patterns are reusable.

## Image identity

| Field | Value |
|-------|-------|
| `repository` | `peakvox/kokoro-runtime` |
| `tag` | `0.1.0` |
| `digest` | set by build script after `docker build` |
| Base image | `python:3.11-slim` |
| System deps | `ffmpeg`, `espeak-ng`, `build-essential` |
| Python deps | `kokoro==0.7.16`, `fastapi==0.115.0`, `uvicorn==0.32.0`, `pydantic==2.9.2`, `spacy==3.8.3` |
| Port | 8000 |
| Healthcheck | `GET /health` every 10s |

## Result

- Architecture-validated: **PASS** (29 contract / structure / reference tests).
- Provider-validated: **PASS** at the test surface (gated E2E).
- Reference shape: **canonical** (R8).

This report closes G6 of the Phase 3 validation plan
(see
[`VALIDATION.md` § Phase 3 G6](../SPECS/FEATURES/runtime-services-implementation/VALIDATION.md)).
G7 (performance) and G8 (error recovery) follow in separate
reports. G9 (idle reaper) and G10 (backend without Kokoro)
are closed by their dedicated reports.

---

**See also:**
[`SPECS/FEATURES/runtime-services-implementation/VALIDATION.md` § G6](../SPECS/FEATURES/runtime-services-implementation/VALIDATION.md)
·
[`runtime-registry/kokoro-82m/README.md`](../../../runtime-registry/kokoro-82m/README.md)
·
[`audit: runtime-service-readiness-audit.md`](../AUDITS/runtime-service-readiness-audit.md)

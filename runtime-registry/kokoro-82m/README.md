# peakvox/kokoro-runtime

The first Runtime Service PeakVox ships. This directory is
the **canonical reference shape** (R8) for every future
runtime: F5-TTS, XTTS, OpenVoice, Fish, OmniVoice. To add a
new runtime, copy this directory and adjust the descriptor
plus the framework-specific source.

## What is this

A self-contained Docker image (`peakvox/kokoro-runtime:0.1.0`)
that exposes the 5-endpoint **Runtime Service Contract** over
HTTP/JSON (ADR-0017 §6). The Kokoro 82M TTS model runs inside
the container; the backend talks to it over the wire.

```
Voice → VoiceVariant → Active Artifact → Adapter
      → HTTPTransport → peakvox/kokoro-runtime (THIS) → Audio
```

## Contract

| Method | Path                | Purpose                          | 2xx status |
|--------|---------------------|----------------------------------|------------|
| GET    | `/health`           | Liveness (always 200 if alive)   | 200        |
| GET    | `/ready`            | Readiness (model loaded?)        | 200 / 503  |
| POST   | `/v1/generate`      | Inference (returns `audio/wav`)  | 200        |
| POST   | `/v1/variants/build`| Variant build (501 in Phase 3)   | 501        |
| GET    | `/v1/metadata`      | Capabilities, languages, tags    | 200        |

The contract is the **same for every runtime service**. Model-
specific concerns are routed through `/v1/metadata`. See
[`adr-0017-runtime-services-implementation.md`](../../docs/.agents/DECISIONS/adr-0017-runtime-services-implementation.md)
§ Runtime Service Contract for the canonical wire shapes.

## Operator notes

### Build

```bash
docker build -t peakvox/kokoro-runtime:0.1.0 \
    runtime-registry/kokoro-82m/
```

The build installs the `kokoro==0.7.16` framework plus
`ffmpeg` and `espeack-ng` system deps. The first build takes
3-5 minutes; subsequent builds are cached.

### Run

```bash
docker run --rm -d -p 8000:8000 --name kokoro-runtime \
    peakvox/kokoro-runtime:0.1.0
```

The container exposes port 8000. The driver (`RuntimeManager`)
maps this to a host port in CE; in Cloud, the service is
exposed by the orchestrator.

### Probe the endpoints

```bash
# Liveness — always 200 if the process is alive.
curl http://localhost:8000/health
# → {"status":"alive"}

# Readiness — 200 once the model is loaded, 503 otherwise.
curl -i http://localhost:8000/ready
# → HTTP/1.1 503 Not Ready
# → {"status":"not_ready","reason":"weights_loading"}
# After ~10s, the model is loaded:
# → HTTP/1.1 200 OK
# → {"status":"ready"}

# Metadata — capabilities, supported languages, etc.
curl http://localhost:8000/v1/metadata
# → {"runtime_id":"kokoro-82m","model_id":"kokoro-base",
#    "capabilities":["tts","multilingual"],
#    "supported_languages":["en","es","fr","hi","it","ja","pt","tr","zh"],
#    ...}

# Generate — produces a WAV file.
curl -X POST http://localhost:8000/v1/generate \
    -H "Content-Type: application/json" \
    -d '{
      "voice_id": "af_bella",
      "text": "Hello, world.",
      "language": "en",
      "request_id": "req_demo_001"
    }' \
    --output hello.wav
# → hello.wav contains a 1-second 24kHz mono PCM.
```

### Wire it into PeakVox (CE)

The descriptor is published at
`runtime-registry/kokoro-82m/descriptor.json`. The backend
loads it when `RUNTIME_SERVICE_ENABLED=true` (default false
in CE). The Models page resolves `kokoro-base` → this
runtime, and the `KokoroAdapter` routes requests through it.

To enable:

```bash
# .env
RUNTIME_SERVICE_ENABLED=true
KOKORO_RUNTIME_URL=http://peakvox-kokoro-runtime:8000
```

Then `docker compose up` brings up the backend, the runtime,
and the rest of the stack.

## Architecture

```
┌─────────────────────────────────────────┐
│ peakvox/kokoro-runtime:0.1.0            │
│                                         │
│   uvicorn  ──→  server.py (FastAPI)     │
│                      │                  │
│                      ▼                  │
│              kokoro.KPipeline           │
│              (lazy-loaded; 82M params)  │
│                      │                  │
│                      ▼                  │
│              audio/wav (24kHz mono)     │
│                                         │
│   GET  /health          (always 200)    │
│   GET  /ready           (200 if loaded) │
│   POST /v1/generate     (returns WAV)   │
│   POST /v1/variants/build (501 in P3)   │
│   GET  /v1/metadata     (capabilities)  │
└─────────────────────────────────────────┘
```

The backend is **never** inside this container. The container
owns the model weights, the framework, and the inference loop.
The backend owns orchestration, not inference (R5).

## Resource requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU      | 1 core  | 2+ cores    |
| Memory   | 2 GB    | 4 GB        |
| VRAM     | 0 (CPU) | n/a         |
| Disk     | 1 GB    | 2 GB (model cache) |

The image is CPU-only. GPU support is a future ADR (the
descriptor's `spec.requirements.gpu` is `optional`; a future
`peakvox/kokoro-runtime-cuda` descriptor would target NVIDIA
hardware).

## Files

| File | Purpose |
|------|---------|
| `descriptor.json` | The contract (R8 reference shape). |
| `Dockerfile` | Build instructions. |
| `requirements.txt` | Python deps (`kokoro`, `fastapi`, `uvicorn`). |
| `server.py` | The FastAPI service implementing the 5-endpoint contract. |
| `README.md` | This file. |
| `tests/` | Contract tests + Dockerfile structure tests + gated E2E. |

## Tests

```bash
cd runtime-registry/kokoro-82m
pytest tests/
```

The suite has 19 contract / structure tests that run without
Docker. The CI-gated E2E tests (Docker build + container start
+ real audio generation) are in `tests/test_docker_*.py` and
require Docker on the host.

## Adding a new runtime (the R8 pattern)

1. Copy this directory to `runtime-registry/<new-runtime-id>/`.
2. Update `descriptor.json`:
   - `metadata.id` (DNS-label)
   - `metadata.name`, `metadata.provider`, `metadata.version`
   - `spec.image.{repository,tag}`
   - `spec.service.port`
   - `spec.model_binding.model_id` (the catalog model it serves)
   - `spec.build.{entrypoint, build_context, dockerfile}`
   - `spec.capabilities` (subset of the bound model)
   - `spec.requirements.{gpu, min_vram_gb, cpu_cores, memory_gb}`
   - `spec.lifecycle.idle_timeout`
3. Update `requirements.txt` with the new framework pin.
4. Update `server.py` to call the new framework (the 5-endpoint
   shape is the same; only the inference call changes).
5. Update `Dockerfile` (base image, system deps, EXPOSE, CMD).
6. Add a `README.md` (copy this one and adjust).
7. Add tests in `tests/` (mirror `test_server.py` and
   `test_dockerfile.py`).

The new runtime is a `RuntimeManager.install()` away.

## See also

- [`adr-0017-runtime-services-implementation.md`](../../docs/.agents/DECISIONS/adr-0017-runtime-services-implementation.md) — the architecture.
- [`DESIGN.md` §6](../../docs/.agents/SPECS/FEATURES/runtime-services-implementation/DESIGN.md) — the Runtime Service Contract.
- [`VALIDATION.md` § Phase 3](../../docs/.agents/SPECS/FEATURES/runtime-services-implementation/VALIDATION.md) — the G6-G10 provider-validated reports.
- [`audit: runtime-service-readiness-audit.md`](../../docs/.agents/VALIDATION/AUDITS/runtime-service-readiness-audit.md) — the audit that motivated Phase 3.

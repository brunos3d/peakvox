# peakvox/f5-tts-runtime

The third Runtime Service PeakVox ships. This directory mirrors
the canonical reference shape (R8) established by Kokoro 82M
and applies it to the F5-TTS flow-matching TTS model.

```
runtime-registry/
├── kokoro-82m/        (R8 reference)
├── omnivoice-base/    (R8 mirror — CPU-capable)
└── f5-tts-base/       (this directory — R8 mirror — GPU-only)
```

To add a new runtime, copy `kokoro-82m/` and adjust the
descriptor + framework-specific source.

## What is this

A self-contained Docker image (`peakvox/f5-tts-runtime:0.1.0`)
that exposes the 5-endpoint **Runtime Service Contract** over
HTTP/JSON (ADR-0017 §6). The F5-TTS flow-matching model runs
inside the container; the backend talks to it over the wire.

```
Voice → VoiceVariant → Active Artifact → Adapter
      → HTTPTransport → peakvox/f5-tts-runtime (THIS) → Audio
```

F5-TTS is **GPU-only** (CUDA required for inference). The
container base image is `pytorch/pytorch:2.4.0-cuda12.1-cudnn8-runtime`,
not `python:3.11-slim` (Kokoro's base).

## Contract

| Method | Path                | Purpose                          | 2xx status |
|--------|---------------------|----------------------------------|------------|
| GET    | `/health`           | Liveness (always 200 if alive)   | 200        |
| GET    | `/ready`            | Readiness (model loaded + CUDA)  | 200 / 503  |
| POST   | `/v1/generate`      | Inference (returns `audio/wav`)  | 200        |
| POST   | `/v1/variants/build`| Variant build (501 in Phase 3)   | 501        |
| GET    | `/v1/metadata`      | Capabilities, languages, tags    | 200        |

The contract is the **same for every runtime service**. Model-
specific concerns are routed through `/v1/metadata`.

## Capabilities (declared in descriptor)

| Capability        | Declared | Notes |
|-------------------|----------|-------|
| `tts`             | ✅ | TTS is the core operation |
| `voice_cloning`   | ✅ | Zero-shot voice cloning via reference audio |
| `multilingual`    | ✅ | EN / ZH / JA / FR / DE / ES / KO / RU |
| `reference_audio` | ✅ | Required for voice cloning (flow-matching cond.) |
| `singing`         | ❌ | Not supported by F5-TTS |
| `voice_design`    | ❌ | Not supported by F5-TTS |
| `emotion_tags`    | ❌ | Not supported by F5-TTS |
| `streaming`       | ❌ | Not supported by F5-TTS |

## Operator notes

### Build

```bash
docker build -t peakvox/f5-tts-runtime:0.1.0 \
    runtime-registry/f5-tts-base/
```

The build pulls the CUDA-enabled PyTorch base image
(pytorch/pytorch:2.4.0-cuda12.1-cudnn8-runtime), installs
`f5-tts==1.0.3` + `vocos==0.1.0`, and bakes the entrypoint.
First build is heavy (~10 GB base image); subsequent builds
are cached.

### Run

```bash
docker run --rm -d -p 8000:8000 --gpus=all --name f5-tts-runtime \
    peakvox/f5-tts-runtime:0.1.0
```

The container requires `--gpus=all` (or `--runtime=nvidia` on
older Docker) to claim a CUDA device. Without a GPU, the
container starts but `/ready` returns 503 with
`load_failed: cuda_unavailable`.

### Probe the endpoints

```bash
curl -s http://localhost:8000/health | jq
curl -s http://localhost:8000/ready  | jq
curl -s http://localhost:8000/v1/metadata | jq
```

## Status

| Field | Value |
|---|---|
| Descriptor validated | ✅ |
| Descriptor matches `ModelCapabilities` subset | ✅ (requires `f5-tts-base` in BUILTIN_MODELS) |
| Docker image built | ⚠️ (requires CUDA host + `f5-tts` package on PyPI) |
| E2E audio generation validated | ⚠️ (requires GPU + weights; deferred to a future phase) |

The descriptor is the **canonical contract**. The build,
weights download, and E2E generation are operational concerns
that land in a later phase.

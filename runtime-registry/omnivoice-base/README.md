# peakvox/omnivoice-runtime

The second Runtime Service PeakVox ships. This directory mirrors
the canonical reference shape (R8) established by Kokoro 82M
and applies it to the OmniVoice 0.6B diffusion-language-model
TTS.

```
runtime-registry/
├── kokoro-82m/        (R8 reference)
├── omnivoice-base/    (this directory — R8 mirror)
└── f5-tts-base/       (planned — R8 mirror)
```

To add a new runtime, copy `kokoro-82m/` and adjust the
descriptor + framework-specific source.

## What is this

A self-contained Docker image (`peakvox/omnivoice-runtime:0.1.0`)
that exposes the 5-endpoint **Runtime Service Contract** over
HTTP/JSON (ADR-0017 §6). The OmniVoice 0.6B TTS model runs
inside the container; the backend talks to it over the wire.

```
Voice → VoiceVariant → Active Artifact → Adapter
      → HTTPTransport → peakvox/omnivoice-runtime (THIS) → Audio
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
specific concerns are routed through `/v1/metadata`.

## Capabilities (declared in descriptor)

| Capability        | Declared | Notes |
|-------------------|----------|-------|
| `tts`             | ✅ | TTS is the core operation |
| `voice_cloning`   | ✅ | Reference-audio-based cloning |
| `multilingual`    | ✅ | 646 languages per upstream card |
| `emotion_tags`    | ✅ | Reaction / question / surprise tags |
| `voice_design`    | ✅ | 18 speaker-attribute categories |
| `reference_audio` | ✅ | Required for voice cloning |
| `singing`         | ❌ | Not supported by OmniVoice base |
| `streaming`       | ❌ | Not supported by OmniVoice base |

## Operator notes

### Build

```bash
docker build -t peakvox/omnivoice-runtime:0.1.0 \
    runtime-registry/omnivoice-base/
```

The build installs `omnivoice==0.1.0` plus `ffmpeg`. The
OmniVoice weights (~2.4 GB BF16) are downloaded on first
inference; the entrypoint can be parameterized to pre-bake
the weights for offline deploys.

### Run

```bash
docker run --rm -d -p 8000:8000 --name omnivoice-runtime \
    peakvox/omnivoice-runtime:0.1.0
```

### Probe the endpoints

```bash
curl -s http://localhost:8000/health | jq
curl -s http://localhost:8000/ready  | jq
curl -s http://localhost:8000/v1/metadata | jq
```

## Relationship to the in-process adapter

The PeakVox backend ships an in-process `OmniVoiceAdapter` that
loads the model inside the FastAPI process. This runtime entry
is the **containerized** alternative: the same model, the same
adapter contract, but the model is owned by a separate process
the adapter talks to over `HTTPTransport`.

The in-process adapter is the **fallback** when the runtime
container is not installed. The runtime container is the
**default** in CE. The two paths produce identical audio; the
selection happens at runtime based on the descriptor binding.

## Status

| Field | Value |
|---|---|
| Descriptor validated | ✅ |
| Descriptor matches `ModelCapabilities` subset | ✅ |
| Docker image built | ⚠️ (requires `omnivoice` package on PyPI; not built in this validation pass) |
| E2E audio generation validated | ⚠️ (requires weights + GPU for production; deferred to a future phase) |

The descriptor is the **canonical contract** — the build, weights
download, and E2E generation are operational concerns that
land in a later phase. The structural contract is correct and
the loader accepts the entry today.

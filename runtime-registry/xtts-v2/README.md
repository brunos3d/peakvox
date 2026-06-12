# peakvox/xtts-runtime

The fourth Runtime Service PeakVox ships — Coqui **XTTS v2** multilingual
zero-shot voice cloning, integrated as a first-class PeakVox runtime
(Task 30, ADR-0021). It mirrors the F5-TTS runtime shape (R8) and implements
the 5-endpoint Runtime Service Contract (ADR-0017 §6).

| | |
|---|---|
| Runtime id | `xtts-v2` |
| Bound model | `xtts-v2` (`provider: "xtts"`) |
| Image | `peakvox/xtts-runtime:0.1.0` |
| Engine | `coqui-tts` (`tts_models/multilingual/multi-dataset/xtts_v2`) |
| Substrate | **GPU-optional** — CUDA when available, real CPU fallback |
| Sample rate | 24 kHz mono, 16-bit PCM WAV |
| Capabilities | `tts`, `voice_cloning`, `multilingual`, `reference_audio` |
| Languages | en, es, fr, de, it, pt, pl, tr, ru, nl, cs, ar, zh-cn, hu, ko, ja, hi (17) |
| License | Coqui Public Model License (CPML) — **non-commercial**; CE-disabled by default |

## GPU / CPU behavior (the divergence from F5-TTS)

XTTS v2 is **CPU-capable**, so unlike F5-TTS (CUDA-only, raises on missing GPU)
this runtime never fails for lack of a GPU. `server.py` picks the device at load
time with `torch.cuda.is_available()`. The descriptor declares
`requirements.gpu: "optional"`, so the Docker driver honors the global
**Settings → Use GPU (CUDA)** toggle:

| Use GPU (CUDA) | Host CUDA | Device |
|---|---|---|
| ON | yes | CUDA (fast) |
| ON | no | CPU |
| OFF | yes | CPU (driver hides the GPU; setting is authoritative) |
| OFF | no | CPU |

`/v1/metadata` reports the live `substrate` (`gpu`/`cpu`). No setting is silently
ignored.

## Endpoints (Runtime Service Contract — ADR-0017 §6)

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | liveness |
| GET | `/ready` | readiness (model loaded?) |
| POST | `/v1/generate` | inference → `audio/wav` |
| POST | `/v1/variants/build` | `501` — handled by the in-process XTTS adapter |
| GET | `/v1/metadata` | capabilities + live substrate |

## Voice cloning & voice-optional

- **Cloning:** pass `params.ref_audio_path` (a reference clip, ~6 s). XTTS computes
  conditioning latents and clones the voice. The PeakVox `XTTSAdapter` resolves the
  voice's Source Asset reference to a local temp file — same path as F5/OmniVoice.
- **Voice-optional** (`supports_voice_optional=True`): with no reference clip, the
  server synthesizes with a built-in XTTS studio speaker, so the generate button
  stays usable with no voice selected.

## Runtime Variants

`variants/base.json` formalizes the bundled `coqui/XTTS-v2` checkpoint as the
explicit, default, `verified` base variant. Fine-tuned / community / imported
Hugging Face XTTS checkpoints attach as **additional** RuntimeVariants of this same
runtime (ADR-0018/0019) — no new image. See
`docs/.agents/VALIDATION/RESEARCH/task-30-xtts-discovery.md` §6.

## Local development

```bash
# Build
docker build -t peakvox/xtts-runtime:0.1.0 runtime-registry/xtts-v2/

# Run (GPU)
docker run --rm --gpus all -p 8000:8000 peakvox/xtts-runtime:0.1.0
# Run (CPU)
docker run --rm -e NVIDIA_VISIBLE_DEVICES=void -p 8000:8000 peakvox/xtts-runtime:0.1.0
```

In PeakVox, lifecycle is managed from the **Models** page (Install / Start / Stop /
Restart / Update / Remove) via the RuntimeManager → DockerRuntimeDriver — never by
hand.

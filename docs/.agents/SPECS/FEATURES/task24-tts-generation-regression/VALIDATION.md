# Task 24 — Validation Report

> **Verdict: VALIDATED.** Both real TTS providers generate reliably through the
> Runtime Registry architecture: OmniVoice via its runtime container (CPU), F5-TTS in
> voice-optional and voice-cloning modes including transcript-less sample voices. The
> meta-tensor crash class is eliminated at two layers. Date: 2026-06-10.

## 1. Root causes (full analysis in DESIGN.md)

| Issue | Root cause | Layer |
|---|---|---|
| 1 — "in-process execution not available" while runtime Active | `OmniVoiceAdapter.generate()` unconditionally raised; never consumed `runtime_endpoint` (T21 decontamination left the adapter without the HTTP path) | backend adapter |
| 1b — `HTTP 0` after routing fix | 30 s transport default vs ~3.5 min CPU inference | backend adapter (timeout 600 s) |
| 2 — "Cannot copy out of meta tensor" | `transcript: null` in variant params → `ref_text=""` → f5-tts triggers Whisper ASR → ASR init crashes on torch 2.12 | f5 adapter + f5 runtime server |
| 1c — OmniVoice runtime load failed | `from omnivoice import OmniVoicePipeline` — class doesn't exist (real: `OmniVoice`); handler written for nonexistent `synthesize()` API | omnivoice runtime server |
| 1d — "should be either the number of the text or 1, but got 3" | voice_design tag list passed raw as `instruct`; arity must match text count | omnivoice runtime server |
| 1e — duration 0.0 for valid audio | `(1, N)` batch tensor not squeezed → `len(audio) == 1` | omnivoice runtime server |
| 3 — voice-optional "inconsistency" | **By design**: `supports_voice_optional=True` on F5-TTS only; UI is capability-driven (Constitution Art. III §10) | n/a |
| 4 — sample-voice compatibility | **Already working**: all SOURCE_ASSET voices report `compatible_models: ['f5-tts-base']`; Jarvis/Lucas Montano lack a built variant (Voice Library action) | n/a |

## 2. Live generation evidence (through the backend API, runtime containers Active)

| Scenario | Provider | Voice | Result |
|---|---|---|---|
| Voice cloning, transcript-less SOURCE_ASSET | F5-TTS | Fireship (`transcript: null`) | ✅ 8.10 s audio — the exact voice that crashed with the meta-tensor error |
| Voice cloning, sample voice | F5-TTS | Donald Trump | ✅ 6.87 s audio |
| Voice cloning, with stored transcript | F5-TTS | Bruno PT-BR | ✅ 3.46 s audio |
| Voice-optional (no voice selected) | F5-TTS | — (bundled default) | ✅ 5.75 s audio |
| Voice design via runtime container | OmniVoice | design tags → instruct | ✅ 5.92 s audio, correct duration reported (squeeze fix) |

Consecutive generations succeeded for both providers; the OmniVoice CPU request
(~3.5 min) completes within the 600 s adapter timeout. Runtime activation detection
was never the defect — `PeakVoxRuntime` resolved the ACTIVE instance and passed the
endpoint correctly in every trace.

## 3. Regression-prevention tests (53 new, all passing)

| Suite | Tests | Command |
|---|---|---|
| `backend/tests/test_t24_omnivoice_adapter_routing.py` | 11 | `pytest tests/test_t24_omnivoice_adapter_routing.py` |
| `backend/tests/test_t24_f5_adapter_ref_text.py` | 10 | `pytest tests/test_t24_f5_adapter_ref_text.py` |
| `runtime-registry/omnivoice-base/tests/test_server.py` | 17 | `pytest tests/test_server.py` (from the runtime dir) |
| `runtime-registry/f5-tts-base/tests/test_server.py` | 15 | `pytest tests/test_server.py` (from the runtime dir) |

Key locked-down behaviors: adapter raises **only** when `runtime_endpoint is None`;
600 s OmniVoice transport timeout; effective-ref_text precedence with placeholder on
`null`/`""`/absent transcript; an empty-`ref_text` sweep asserting no parameter
combination ever reaches the model without a transcript; `OmniVoice` class +
`generate()` API + `k2-fsa/OmniVoice` repo; instruct list→string join; batch-dim
squeeze (1000 ms, not 0 ms); f5-tts 1.0.3 `ref_file` kwarg; null-param guards.

## 4. Full test sweep

| Suite | Result |
|---|---|
| `backend/` (full) | ✅ 680 passed, 1 skipped |
| `runtime-registry/kokoro-82m` | ✅ 19 passed |
| `runtime-registry/omnivoice-base` | ✅ 41 passed (with backend on `PYTHONPATH`) |
| `runtime-registry/f5-tts-base` | ✅ 41 passed (with backend on `PYTHONPATH`) |

(The two descriptor tests importing `app.*` require the backend on `PYTHONPATH`; that
is a pre-existing harness property, unrelated to T24.)

## 5. Constitution compliance

- **Art. III §8–9:** all generation routes through `PeakVoxRuntime` → adapter →
  HTTPTransport → runtime container. No in-process inference path exists or was added.
- **Art. III §10:** issue 3 resolved by *reading* capabilities, not by branching on
  model ids; no per-model conditionals added anywhere.
- **Art. VII §21–23:** every "fixed" claim above carries code, test, and live-audio
  evidence; issues 3–4 are explicitly classified by-design rather than silently closed.

## 6. Residual risks / follow-ups

- Running containers carry the server fixes via `docker commit`; the next image rebuild
  from `runtime-registry/` sources supersedes them (sources already contain the fixes).
- The cloning placeholder slightly weakens conditioning vs. a true transcript; storing
  real transcripts at variant build time remains the quality-preferred path and always
  wins the precedence chain.
- Jarvis / Lucas Montano need an F5-TTS variant build through the Voice Library UI to
  appear in the F5-TTS voice picker.

# Task 24 — Design: Root Causes and Fixes

Five independent defects stacked into the two reported failures. Each fix is designed
at the layer that owns the defect; where a crash class is catastrophic (meta tensor),
the guard exists at **two** layers (adapter + runtime server) so a stale container or a
bypassing client cannot reintroduce it.

## 1. OmniVoice adapter never routed to the runtime (issue 1)

**Root cause.** `OmniVoiceAdapter.generate()` *unconditionally* raised
`RuntimeError("OmniVoice in-process execution is not available…")`. The Task 21
decontamination removed in-process torch execution but left the adapter without the
HTTP-transport generation path that Kokoro and F5-TTS received. `PeakVoxRuntime`
resolved the ACTIVE runtime correctly and passed `runtime_endpoint` — the adapter
ignored it. The error message ("start the runtime container") was misleading because
the container *was* running; the dead end was inside the adapter.

**Fix** (`backend/app/services/model_adapters/omnivoice_adapter.py`):
- `generate()` raises only when `runtime_endpoint is None`; otherwise it POSTs the
  canonical `/v1/generate` body (ADR-0017 §6.3) via `HTTPTransport.post_binary()`,
  writes the WAV bytes, and reads duration from `X-Peakvox-Duration-Ms` (falling back
  to WAV introspection).
- `ref_audio_path` / `ref_text` / `instruct` travel inside `params`, same shape as the
  F5-TTS and Kokoro adapters.

**Timeout design.** OmniVoice is a 0.6B LLM running on CPU in CE — ~3.5 min per
request. The transport default (30 s) produced `HTTP 0` network-timeout failures after
the routing fix. The adapter constructs its transport with `timeout_seconds=600.0`.
The value lives in the adapter (the component that knows its model's latency), not in
the shared transport default.

## 2. F5-TTS meta-tensor crash = Whisper ASR triggered by empty ref_text (issue 2)

**Root cause chain.** SOURCE_ASSET voices cloned without a transcript store
`{"transcript": null}` in variant params → generation sent `ref_text=""` →
f5-tts 1.0.3 auto-transcribes the reference clip with Whisper ASR whenever
`ref_text` is empty → Whisper initialization crashes on torch 2.12 with
*"Cannot copy out of meta tensor; no data!"*. The voice (e.g. Fireship) was fine;
the missing transcript silently switched f5-tts into its broken ASR path.

**Fix, layer 1 — adapter** (`backend/app/services/model_adapters/f5_adapter.py`):
resolve an *effective* ref_text with explicit precedence —
`ref_text` arg → variant `transcript` param → upstream `ref_text` param. When
reference audio is present and no transcript exists anywhere, inject the neutral
placeholder `"Voice cloning reference audio sample."` so the model never sees an
empty transcript. Falsy guards (`or None`) treat `null` and `""` as missing.

**Fix, layer 2 — runtime server** (`runtime-registry/f5-tts-base/server.py`):
after the voice-optional fallback, `if ref_file and not ref_text:` applies the same
placeholder. This protects containers reached by older backends or direct API users.

**Why a placeholder instead of real ASR?** ASR is the crashing component; any
transcription dependency reintroduces the failure class. A short neutral English
sentence keeps F5-TTS's cloning conditioning stable (validated by ear and by output
duration on Fireship/Trump clips). Voices that need maximum fidelity should store a
real transcript at variant build time — that remains the preferred path and wins the
precedence chain.

**Voice-optional mode is exempt:** with no reference audio the server substitutes its
bundled `basic_ref_en.wav` *plus its known transcript*, so no placeholder is needed and
the adapter sends neither `ref_audio_path` nor `ref_text`.

## 3. OmniVoice runtime server shipped against a nonexistent API

Three defects inside `runtime-registry/omnivoice-base/server.py`, all hit on the first
real inference (the lazy load hid them from /health and /ready):

1. **Wrong class:** `from omnivoice import OmniVoicePipeline` — the package exports
   `OmniVoice`. Every lazy load failed; `/ready` reported `load_failed`.
2. **Wrong method/shape:** the handler was written for a `synthesize()`-style API.
   The real surface is `OmniVoice.generate(text=…, ref_audio=…, ref_text=…,
   instruct=…)` returning `list[torch.Tensor]`.
3. **Instruct arity:** voice-design tags arrived as a list
   (`["male", "elderly", "moderate pitch"]`); OmniVoice requires
   `len(instruct) == len(texts)` when given a list → *"should be either the number of
   the text or 1, but got 3"*. Lists are now joined into one comma-separated string.

**Duration bug:** OmniVoice tensors carry a batch dimension `(1, N)`.
`torch.cat(...)` kept it, so `len(audio) == 1` and `X-Peakvox-Duration-Ms` reported
`0` for valid audio. `.squeeze()` flattens to `(N,)` before encoding.

## 4. Issues 3 & 4 are capability-contract behavior, not bugs

- **Issue 3 (voice-optional inconsistency):** F5-TTS declares
  `supports_voice_optional=True` (`model_catalog.py:286`); OmniVoice does not. The UI
  requiring a voice for OmniVoice but not for F5-TTS is capability-driven rendering
  (Constitution Art. III §10) working as designed. The perceived inconsistency was the
  *same screen* behaving differently per selected model.
- **Issue 4 (sample-voice compatibility):** `/voices` compatibility already reports
  `compatible_models: ['f5-tts-base']` for every SOURCE_ASSET voice. Fireship, Donald
  Trump and Bruno PT-BR generate (validated live). Jarvis and Lucas Montano simply have
  no F5-TTS variant built yet — a Voice Library build action, not a generation defect.

## 5. Deployment of runtime-server fixes

Running containers were updated via `docker exec -i … 'cat > /app/server.py'` +
`docker commit` + `docker restart` (uvicorn is PID 1; in-place restarts kill the
container). The canonical fix lives in `runtime-registry/*/server.py` and lands in all
future image builds; the commit pattern was a zero-rebuild deployment shortcut only.

## 6. Test strategy

Every fixed layer gets a regression test that fails if the defect returns:

| Layer | File | Locks down |
|---|---|---|
| OmniVoice adapter | `backend/tests/test_t24_omnivoice_adapter_routing.py` | raise-only-when-no-endpoint, `/v1/generate` routing, 600 s timeout, duration header + WAV fallback, param forwarding, transport reuse, error wrapping |
| F5-TTS adapter | `backend/tests/test_t24_f5_adapter_ref_text.py` | effective-ref_text precedence, placeholder on `transcript: null/""/absent`, voice-optional sends neither key, capability declarations |
| OmniVoice server | `runtime-registry/omnivoice-base/tests/test_server.py` | `OmniVoice` class import, `from_pretrained` repo, `generate()` usage, instruct list→string join, batch-dim squeeze (1000 ms ≠ 0 ms), contract endpoints |
| F5-TTS server | `runtime-registry/f5-tts-base/tests/test_server.py` | never-empty ref_text sweep, placeholder fallback, bundled-default voice-optional, `ref_file` kwarg (1.0.3), null-param guards, contract endpoints |

Runtime-server tests load `server.py` under unique module names via `importlib` (no
`import server` collisions across runtime suites) and stub `torch` in `sys.modules`,
so they run in the torch-free backend test venv.

# Task 24 — Execution Tasks

| # | Task | State |
|---|---|---|
| 1 | Review uncommitted files; commit T19–T23 work as semantic commits | ✅ done |
| 2 | Reproduce both failures; confirm runtime containers Active during failure | ✅ done |
| 3 | Root-cause issue 1: OmniVoice adapter `generate()` unconditionally raises | ✅ done |
| 4 | Fix OmniVoice adapter: HTTPTransport routing + 600 s timeout | ✅ done |
| 5 | Root-cause issue 2: empty `ref_text` → Whisper ASR → meta-tensor crash | ✅ done |
| 6 | Fix F5-TTS adapter: effective-ref_text precedence + placeholder injection | ✅ done |
| 7 | Fix F5-TTS server: cloning-mode transcript fallback (defense in depth) | ✅ done |
| 8 | Root-cause + fix OmniVoice server: `OmniVoice` class, `generate()` API, instruct list join, batch-dim squeeze | ✅ done |
| 9 | Deploy server fixes into running containers (`docker commit` + restart) | ✅ done |
| 10 | Verify issues 3–4 against the capability contract (by-design confirmation) | ✅ done |
| 11 | Live validation: OmniVoice + F5-TTS consecutive generations, voice-optional, sample voices | ✅ done |
| 12 | Regression tests: both adapters + both runtime servers (53 new tests) | ✅ done |
| 13 | Full test sweep: backend 680 passed; runtime suites 41/41/19 passed | ✅ done |
| 14 | Spec folder (SPEC/DESIGN/TASKS/VALIDATION/STATUS) + agent state docs | ✅ done |
| 15 | Semantic commits for all T24 changes | ✅ done |

Deferred (out of scope, tracked for later):

- Build F5-TTS variants for Jarvis / Lucas Montano via the Voice Library UI (user action).
- Rebuild `peakvox/omnivoice-runtime` and `peakvox/f5-tts-runtime` images from the
  updated registry sources (current containers carry the fixes via `docker commit`).

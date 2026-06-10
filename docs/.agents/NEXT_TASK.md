# NEXT TASK

> Exactly one highest-priority task — the execution queue head. When this task is done, move
> it to the execution ledger and promote the next item from [`ROADMAP/BACKLOG.md`](ROADMAP/BACKLOG.md).

**As of:** 2026-06-10

> **Context.** T24 (TTS Generation Regression Investigation) is VALIDATED 2026-06-10:
> OmniVoice and F5-TTS both generate reliably through the Runtime Registry
> architecture (see
> [`SPECS/FEATURES/task24-tts-generation-regression/`](SPECS/FEATURES/task24-tts-generation-regression/)).
> The T24 server-side fixes reached the **running** containers via `docker commit`;
> the canonical fixes live in `runtime-registry/omnivoice-base/server.py` and
> `runtime-registry/f5-tts-base/server.py` and land in any image built from sources.

## Task: Rebuild runtime images from registry sources + close the T24 follow-ups

- **Priority:** P1. CE generation works today; this removes the only divergence
  between running containers and the source tree.

1. **Rebuild `peakvox/omnivoice-runtime` and `peakvox/f5-tts-runtime`** from
   `runtime-registry/` sources (Remove + Install through the Models page is
   sufficient — the UI path builds from the platform Dockerfiles).
2. **Re-run the T24 live matrix** after rebuild: OmniVoice voice-design generation;
   F5-TTS voice-optional, Fireship (transcript-less), Donald Trump, Bruno PT-BR.
   Expected results in
   [`SPECS/FEATURES/task24-tts-generation-regression/VALIDATION.md`](SPECS/FEATURES/task24-tts-generation-regression/VALIDATION.md) §2.
3. **Build F5-TTS variants for Jarvis and Lucas Montano** through the Voice Library
   UI so every sample voice is selectable for F5-TTS.

**Done when:** both images rebuilt from sources, live matrix green, all sample voices
selectable for F5-TTS. Then promote the next item from
[`ROADMAP/BACKLOG.md`](ROADMAP/BACKLOG.md) (candidates: Kokoro G7 performance / G8
error-recovery reports; Cloud architecture planning — the provider-validation gate is
open).

---

**Related:** [`ACTIVE_WORK.md`](ACTIVE_WORK.md) · [`CURRENT_CONTEXT.md`](CURRENT_CONTEXT.md) ·
[`HANDOFF.md`](HANDOFF.md) ·
[`SPECS/FEATURES/task24-tts-generation-regression/`](SPECS/FEATURES/task24-tts-generation-regression/)

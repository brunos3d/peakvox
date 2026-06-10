# Task 24 — TTS Generation Regression Investigation (OmniVoice + F5-TTS)

## Intent

Task 23 certified F5-TTS operationally; Task 22/21 finished the runtime-registry
decontamination. Immediately after, **both** real TTS providers regressed in production
use. Task 24 root-causes and eliminates every generation failure so that OmniVoice and
F5-TTS generate audio reliably through the Runtime Registry architecture — no fallback
execution paths, no runtime-activation conflicts, no reference-voice failures.

## Reported issues

| # | Symptom |
|---|---|
| 1 | OmniVoice jobs fail with *"OmniVoice in-process execution is not available. Start the 'omnivoice-base' runtime container via the Models page."* — even while the runtime container **is** Active. |
| 2 | F5-TTS jobs fail with *"inference failed: Cannot copy out of meta tensor; no data! Please use torch.nn.Module.to_empty() instead of torch.nn.Module.to()"* when generating with certain sample voices. |
| 3 | F5-TTS voice-optional behavior appears inconsistent — sometimes generation works with no voice selected, sometimes the UI forces a voice. |
| 4 | Sample voices (Fireship, Donald Trump, …) should be selectable for F5-TTS generation. |

## Scope

1. Root-cause each failure at the responsible layer (adapter, runtime server, transport).
2. Fix the OmniVoice generation path end-to-end through the runtime container.
3. Fix the F5-TTS meta-tensor crash for transcript-less SOURCE_ASSET voices.
4. Verify issues 3 and 4 against the capability contract (bug vs. by-design).
5. Live-validate: consecutive generations for both providers, voice-optional and
   voice-cloning modes, multiple sample voices.
6. Add regression-prevention tests at every fixed layer.
7. Document root causes, fixes, and validation evidence.

## Non-goals

- New generation features or UI changes.
- GPU provisioning for OmniVoice (CPU inference is the CE baseline; timeout is sized for it).
- Variant build pipeline changes (Jarvis / Lucas Montano variants are a Voice Library
  action, not a generation bug).
- Image-rebuild automation (running containers were patched via `docker commit`; the
  registry sources are the canonical fix for future builds).

## Success criteria

- OmniVoice generates through the runtime container (no in-process path exists).
- F5-TTS generates without a voice selected (voice-optional mode).
- F5-TTS generates with sample voices (Fireship, Donald Trump, Bruno PT-BR).
- The meta-tensor error is eliminated.
- Runtime activation detection is validated.
- Multiple consecutive generations succeed for both providers.
- Root causes documented; tests added; documentation updated.

## References

- Predecessors: `../task23-f5tts-production-validation/`, `../task22-f5tts-integration/`,
  `../backend-decontamination-task21/`
- ADR-0017 (Runtime Service Contract), ADR-0003 (Capability Contract)
- `docs/.agents/ARCHITECTURE/10-RUNTIME_ARCHITECTURE.md`
- Constitution Art. III (Runtime joins the three), Art. VII (truth & evidence)

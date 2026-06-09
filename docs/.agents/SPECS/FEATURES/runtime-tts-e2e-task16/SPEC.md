# SPEC — Runtime TTS End-to-End Validation (Task 16)

## Objective
Validate end-to-end TTS generation via browser workflow for kokoro-82m and omnivoice-base before continuing F5 work.

## Scope
- UI workflow: install/start/select model/select voice/generate/playback.
- Trace frontend -> backend -> runtime -> audio output path.
- Produce root-cause evidence for any generation/playback failure.

## Acceptance Criteria
- Kokoro browser generation returns playable audio.
- OmniVoice browser generation returns playable audio.
- Request/response traces and runtime/backend logs are captured.
- Any failures include exact failing stage and reason.

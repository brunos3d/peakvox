# VALIDATION — Runtime Clean Install Lifecycle (Task 14)

## Root Cause Analysis

1. False-positive installs:
- Install success was frequently due to pre-existing local image.
- Validation path drifted into manual local image creation.

2. Remove incompleteness:
- Driver remove flow attempted image removal after container deletion by re-fetching container; this could skip image cleanup.

3. Descriptor transparency gap:
- No image size metadata; UI could not inform users of download/storage expectations.

## Implementation Validation (Code)

Completed:

- Driver install now supports platform-managed build fallback when pull returns image-not-found and descriptor has `spec.build`.
- Driver remove now tracks image references before/while container removal and then removes images best-effort.
- Descriptor/API/UI now support `spec.image.image_size_mb`.
- UI shows optimistic in-progress lifecycle states for all lifecycle actions.

## Environment Validation Evidence (Executed)

### 1) Clean baseline established

Validation command removed runtime-managed containers/images before lifecycle checks.

Observed baseline:

- Runtime containers: none (`docker ps -a` filtered by `peakvox-runtime-*`)
- Runtime images: none (`docker image ls` filtered by `peakvox/*`)

### 2) Lifecycle pass completed end-to-end for `kokoro-82m`

Captured evidence from API lifecycle loop:

- `install`: HTTP 200, phase=`installed`, image=`peakvox/kokoro-runtime:0.1.0`
- `start`: HTTP 200, phase=`active`, host=`peakvox-runtime-kokoro-82m`, port=`8000`
- `stop`: HTTP 200, phase=`stopped`
- `remove`: HTTP 200, phase=`notInstalled`

Docker before/after evidence for `kokoro-82m`:

- Before install: container absent, image absent
- After install: image present (`peakvox/kokoro-runtime:0.1.0`)
- After start: container present (`peakvox-runtime-kokoro-82m`)
- After remove: container absent, image absent

Result: clean install/start/use-path/stop/remove behavior is validated for the CE-shipped runtime path.

### 3) Browser-side communication + UI lifecycle pass (rerun)

Frontend communication hardening was applied and validated:

- `frontend/src/lib/api.ts`
  - Added API base URL normalization and deterministic resolution so browser requests do not degrade into ambiguous relative origins.
- `frontend/src/hooks/use-runtimes.ts`
  - Added `onError`/`onSettled` invalidation to force backend state re-sync after optimistic lifecycle phases.

Browser DevTools evidence after patch:

- Resource timeline showed runtime lifecycle calls targeting backend origin directly (example: `http://localhost:8000/runtimes/kokoro-82m/start`).
- `Loading models...` intermittency still occurred during backend socket resets, but recovered to `Online/Ready` and rendered cards once backend fetch succeeded.

Browser click lifecycle for `kokoro-82m` was completed end-to-end from Models dialog:

- `Install` clicked in UI -> backend state became `installed`
- `Start` clicked in UI -> backend state became `active`
- `Stop` clicked in UI -> backend state became `stopped`
- `Remove` clicked in UI -> backend state became `notInstalled`

Docker evidence paired with UI actions:

- After UI `Start`: `peakvox-runtime-kokoro-82m Up ... (healthy)`
- After UI `Stop`: `peakvox-runtime-kokoro-82m Exited (0)`
- After UI `Remove`: container absent, image absent

### 4) Remaining runtime validations

Post-UI pass runtime checks:

- `omnivoice-base`
	- Install probe returned HTTP 200.
	- Browser UI lifecycle continuation was executed from dialog:
		- `Start` clicked -> runtime reached `active`, container `peakvox-runtime-omnivoice-base` healthy
		- `Stop` clicked -> runtime reached `stopped`, container exited
		- `Remove` clicked -> runtime reached `notInstalled`, container absent, image absent
- `f5-tts-base`
	- Install probe returned HTTP 500.
	- Error payload: `install_failed` due missing manifest for base image `pytorch/pytorch:2.4.0-cuda12.1-cudnn8-runtime`.
	- Runtime state remained `notInstalled`.

## Remaining To Reach VALIDATED

- Resolve `f5-tts-base` runtime image source/manifest mismatch so CE install can complete via UI/API.
- Execute full browser click lifecycle for `f5-tts-base` once install readiness is confirmed.

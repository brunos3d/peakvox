# Spec — F5-TTS Runtime Installation Failure (Task 20)

## Problem

Installing `f5-tts-base` from the Models page fails with:

```
runtime 'f5-tts-base': [docker] manifest for
pytorch/pytorch:2.4.0-cuda12.1-cudnn8-runtime not found: manifest unknown
```

The UI surfaces the error correctly. The installation lifecycle works. The runtime
definition is wrong.

## Root Cause

`runtime-registry/f5-tts-base/Dockerfile` used the base image
`pytorch/pytorch:2.4.0-cuda12.1-cudnn8-runtime` which **never existed** on Docker Hub.

PyTorch 2.4.0 was released with CUDA 12.4 / cuDNN 9. The `cuda12.1-cudnn8` variant
existed only for PyTorch ≤ 2.3.x. The tag was simply wrong from the start.

Additionally, `install_policy` in `descriptor.json` was set to `"pull-on-install"`,
but the driver's install decision is driven by the presence of `spec.build` (not this
field). The semantic mismatch was corrected to `"build-on-install"`.

## Secondary Issues Found

1. **`remove_runtime` Docker SDK ≥7 bug** — `c.image` in `remove_runtime` was still
   using the old string API (same class of bug fixed in Task 19 for `runtime_status` and
   `_descriptor_for_runtime`). Images could be missed during cleanup.

2. **No pre-flight validation** — The driver started the build (potentially downloading
   gigabytes) before discovering the base image doesn't exist. A pre-flight check that
   verifies the FROM image via `client.api.inspect_distribution()` gives a clear error
   immediately.

3. **`install_policy` enum incomplete** — `"build-on-install"` was not a valid value in
   `RuntimeLifecycleConfig` despite being the accurate policy for source-built runtimes.

## Success Criteria

- `f5-tts-base` installs without manual Docker operations
- Install → Installing → Installed via browser UI
- Start → Starting → Active
- Stop → Installed
- Remove → Available; `peakvox/f5-tts-runtime` image gone from Docker
- Pre-flight check raises `ImagePullError` immediately for invalid base images
- 639 backend tests pass

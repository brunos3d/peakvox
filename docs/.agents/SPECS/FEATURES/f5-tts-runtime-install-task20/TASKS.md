# Tasks — F5-TTS Runtime Installation Failure (Task 20)

## Completed

- [x] Audit `runtime-registry/f5-tts-base/` (Dockerfile, descriptor.json, requirements.txt, server.py).
- [x] Identify root cause: `pytorch/pytorch:2.4.0-cuda12.1-cudnn8-runtime` does not exist.
- [x] Fix Dockerfile FROM: `pytorch/pytorch:2.4.0-cuda12.4-cudnn9-runtime`.
- [x] Fix `descriptor.json` install_policy: `"build-on-install"`.
- [x] Add `"build-on-install"` to `RuntimeLifecycleConfig.install_policy` Literal type.
- [x] Add `_parse_dockerfile_from()` static method to `DockerRuntimeDriver`.
- [x] Add `_preflight_base_image()` method to `DockerRuntimeDriver`.
- [x] Wire pre-flight into `_install_image()` before build.
- [x] Fix `remove_runtime` Docker SDK ≥7 bug (`c.image` → `c.attrs["Config"]["Image"]`).
- [x] Update `_MockContainer.attrs` in test suite.
- [x] Add `inspect_distribution` to `_MockApi`.
- [x] Add `manifest_not_found` flag to `_MockDockerClient`.
- [x] 639 backend tests pass.
- [x] Backend rebuilt.

## Pending

- [ ] Browser E2E: Install → Installed → Start → Active → Stop → Remove → Available.
- [ ] Docker cleanup evidence: `peakvox/f5-tts-runtime` absent after Remove.
- [ ] Update VALIDATION.md with browser evidence.
- [ ] Update STATUS.md to VALIDATED.
- [ ] Commit all Task 20 changes.

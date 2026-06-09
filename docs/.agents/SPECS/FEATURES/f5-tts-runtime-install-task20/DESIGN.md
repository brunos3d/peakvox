# Design — F5-TTS Runtime Installation Failure (Task 20)

## Fix 1 — Dockerfile base image (root cause)

**File:** `runtime-registry/f5-tts-base/Dockerfile`

```diff
-FROM pytorch/pytorch:2.4.0-cuda12.1-cudnn8-runtime
+FROM pytorch/pytorch:2.4.0-cuda12.4-cudnn9-runtime
```

**Why `cuda12.4-cudnn9`:**
- RTX 3060 Ti (CUDA compute 8.6) + driver 595.71.05 (supports up to CUDA 13.2) is
  fully compatible with CUDA 12.4 images.
- `pytorch/pytorch:2.4.0-cuda12.4-cudnn9-runtime` is the official PyTorch 2.4.0 tag.
- `pytorch/pytorch:2.4.0-cuda11.8-cudnn8-runtime` also exists but CUDA 11.8 is older.
- F5-TTS 1.0.3 requires `torch>=2.0`, satisfied by 2.4.0.

## Fix 2 — `install_policy` semantic accuracy

**File:** `runtime-registry/f5-tts-base/descriptor.json`

```diff
-"install_policy": "pull-on-install",
+"install_policy": "build-on-install",
```

`peakvox/f5-tts-runtime:0.1.0` is not published on Docker Hub — it is always built
from source. The driver decision is driven by `spec.build` presence (not this field),
but the value should be honest for documentation and future tooling.

**File:** `backend/app/services/runtime_types.py`

```diff
-install_policy: Literal["pull-on-start", "pull-on-install", "lazy"] = "pull-on-start"
+install_policy: Literal["pull-on-start", "pull-on-install", "build-on-install", "lazy"] = "pull-on-start"
```

## Fix 3 — Pre-flight base image validation

**File:** `backend/app/services/drivers/docker_runtime_driver.py`

New methods: `_parse_dockerfile_from()` + `_preflight_base_image()`.

Called at the top of `_install_image()` when `spec.build is not None`, before
`client.images.build()` starts.

Flow:
1. Parse the Dockerfile to extract the first `FROM` image reference.
2. Check if that image is already present locally (`client.images.get()`).
3. If not local, probe the registry via `client.api.inspect_distribution()`.
4. If the manifest is not found → raise `ImagePullError` immediately with a clear message.
5. Any unexpected error in the pre-flight → log warning, proceed (let build surface its own error).

This turns a confusing mid-build failure into an immediate, actionable error:
```
invalid runtime definition: base image 'pytorch/pytorch:2.4.0-cuda12.1-cudnn8-runtime'
does not exist in the registry
```

## Fix 4 — `remove_runtime` Docker SDK ≥7 bug

**File:** `backend/app/services/drivers/docker_runtime_driver.py`

```diff
-if getattr(c, "image", None):
-    image_refs.add(c.image)
+image_str = c.attrs.get("Config", {}).get("Image", "") or ""
+if image_str:
+    image_refs.add(image_str)
```

Same class of bug as fixed in Task 19. `c.image` is an `Image` object in Docker SDK ≥7.
Using `c.attrs["Config"]["Image"]` always returns the string tag.

## Test mock updates

**File:** `backend/tests/test_docker_runtime_driver.py`

- `_MockContainer`: add `self.attrs = {"Config": {"Image": f"{image_repo}:{image_tag}"}}`
  to simulate Docker SDK ≥7 container inspection.
- `_MockApi`: add `inspect_distribution(name)` stub (returns success by default; raises
  when `owner.manifest_not_found = True`).
- `_MockDockerClient`: add `manifest_not_found = False` flag + `set_manifest_not_found()`.

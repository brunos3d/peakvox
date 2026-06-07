# SPEC — Models as Runtime Services

> **Status:** APPROVED (architecture only; implementation deferred)
> **Date:** 2026-06-07
> **ADR:** [`adr-0016-models-as-runtime-services.md`](../../../DECISIONS/adr-0016-models-as-runtime-services.md)
> **Phase:** 1 of 7 (ADR + design only; no code)
> **Method:** Architecture documentation. No code, no migrations, no runtime-registry directory, no Docker wiring, no F5-TTS implementation.

---

## Problem

PeakVox today loads model implementations directly inside the backend Python process.
The backend owns the model lifecycle (install, load, unload, execute), the GPU
memory, and the model's Python dependencies. Each new model is a Python package
in the same process as the API.

This is fine for the current two-model spine (OmniVoice + Kokoro). It does not
scale to the vision of PeakVox as a Universal Voice Runtime hosting many models:

1. The backend image becomes polluted with model-specific dependencies.
2. Each model introduces dependency conflicts.
3. GPU management becomes increasingly difficult.
4. Horizontal scaling becomes expensive.
5. Runtime isolation is weak.
6. Model upgrades become risky (in-process reloads).
7. Backend image gains Docker / orchestration concerns.
8. Cloud deployment couples backend releases to model releases.
9. Large models become tightly coupled to backend lifecycle.
10. F5-TTS, Fish Audio, XTTS, and future providers all face the same friction.

The product is the Runtime Layer — not any model. Models are interchangeable
engines. They must not couple to the backend process.

---

## Goals / Non-goals

### Goals

- Define **Runtime Service** as the new unit of model execution: a model
  realized as an isolated workload (initially a container) reachable over a
  stable contract.
- Introduce the **Runtime Registry** — a versioned, declarative catalog of
  available runtimes (id, image, capabilities, requirements, health).
- Introduce the **Runtime Manager** — the orchestration component inside the
  backend that owns runtime lifecycle (discover, install, update, remove,
  activate, deactivate, health) without executing inference.
- Introduce the **Runtime Driver** — the abstraction that isolates the
  Runtime Manager from any specific execution substrate. The first driver is
  `DockerRuntimeDriver` (CE); the abstraction is forward-compatible with
  Kubernetes, Podman, and a local-process driver.
- Keep the **`ModelAdapter` contract intact** (ADR-0004) and the **Active
  Artifact resolution step intact** (ADR-0009). Adapters evolve into
  protocol translators; they do not lose responsibilities.
- Preserve the existing Voice, VoiceVariant, VoiceVariantArtifact, and Model
  domain boundary. Runtime infrastructure is **not** a domain concept.
- Strengthen — not weaken — Constitution Articles I, III §8, III §9, and V.
- Define a **7-phase migration path** that does not require backend
  architectural changes to add new models.

### Non-goals (this ADR / this phase)

- No `RuntimeManager` code.
- No `RuntimeRegistry` code or `runtime-registry/` directory.
- No Docker integration, no Docker SDK, no `docker compose` files.
- No Kubernetes, Podman, or local-process implementations.
- No adapter migration code. Adapters continue to execute in-process.
- No F5-TTS implementation.
- No F5-TTS runtime image.
- No schema changes (the existing `models` and `models_runtime` is the only
  state surface; ADR-0016 adds *no* new tables in this phase).
- No runtime-instance persistence model. Phase 1 is purely architectural.

---

## Requirements

### Functional

1. **Runtime Registry** — A versioned, declarative description of available
   runtimes exists. The contract is `runtime.yaml`:

   ```yaml
   id: f5-tts
   runtime_type: docker
   image:
     repository: peakvox/f5-runtime
     tag: latest
   api:
     endpoint: http://f5-runtime:8000
   health:
     endpoint: /health
   capabilities:
     - tts
     - voice_cloning
     - multilingual
   requirements:
     gpu: optional
     min_vram_gb: 8
   ```

   This descriptor is the **runtime contract**. It is the only artifact
   required (in addition to the runtime image and the adapter) to add a new
   model — no backend architectural changes.

2. **Runtime Manager** — A single component inside the backend that performs
   **orchestration only**. It does **not** execute inference, allocate GPUs,
   load weights, import model frameworks, or perform substrate-specific
   operations. It depends solely on the `RuntimeDriver` interface.

   The Runtime Manager **owns**:

   - **Discovers** runtimes from the Runtime Registry; reads
     `runtime.yaml` descriptors.
   - **Resolves endpoints** — knows which URL an adapter should call for
     a given runtime.
   - **Delegates** all lifecycle operations to the Runtime Driver
     (install, update, remove, start, stop, restart, status, logs,
     health, metrics).
   - **Reports status** — surfaces the driver's view of each
     `RuntimeInstance` to the rest of the system (API, adapters, ops).

   The Runtime Manager **does NOT**:

   - Execute model inference.
   - Allocate GPUs (or any device).
   - Load model weights.
   - Import model frameworks (torch, transformers, kokoro, f5-tts,
     fish-audio, or any other model code).
   - Perform substrate-specific operations (Docker / Kubernetes /
     Podman / shell calls). Substrate-specific code lives only inside
     concrete driver implementations.

3. **Runtime Driver abstraction** — A formal interface that the Runtime
   Manager depends on. The first implementation is `DockerRuntimeDriver`.
   Other implementations are named as future work to validate the abstraction:
   - `DockerRuntimeDriver` (CE, first)
   - `KubernetesRuntimeDriver` (Cloud, future)
   - `PodmanRuntimeDriver` (alternative, future)
   - `LocalProcessDriver` (development / single-node, future)

   Required operations (naming illustrative, responsibilities normative):
   - `install_runtime(runtime_id, descriptor) -> RuntimeInstance`
   - `update_runtime(runtime_id, descriptor) -> RuntimeInstance`
   - `remove_runtime(runtime_id) -> None`
   - `start_runtime(runtime_id) -> RuntimeInstance`
   - `stop_runtime(runtime_id) -> None`
   - `restart_runtime(runtime_id) -> RuntimeInstance`
   - `runtime_status(runtime_id) -> RuntimeInstance`
   - `runtime_logs(runtime_id, since) -> LogStream`
   - `runtime_health(runtime_id) -> HealthReport`
   - `runtime_metrics(runtime_id) -> Metrics` (optional, future-safe)

   The Runtime Manager must depend **only** on the `RuntimeDriver` interface.
   It must never depend directly on Docker APIs, Kubernetes APIs, Podman, or
   shell.

4. **Critical conceptual distinction** — *PeakVox does not install models.
   PeakVox installs runtimes.* Models are logical catalog entities (rows in
   the `models` table). Runtimes are executable deployment units. A single
   model may have multiple runtimes:

   ```
   Model: F5-TTS
   ├── Runtime: F5 CUDA Runtime     (image: peakvox/f5-runtime-cuda)
   └── Runtime: F5 CPU Runtime      (image: peakvox/f5-runtime-cpu)

   Model: OmniVoice
   ├── Runtime: OmniVoice Local Runtime   (image: peakvox/omnivoice-local)
   └── Runtime: OmniVoice Cloud Runtime   (image: peakvox/omnivoice-cloud)
   ```

5. **Active Artifact resolution is preserved** — The resolution chain remains
   the same as today, with the Runtime Manager inserted **after** the
   adapter is selected:

   ```
   Voice
     → VoiceVariant
       → Active Artifact (ADR-0009)
         → Adapter
           → Runtime Manager
             → Runtime Driver
               → Runtime Service
                 → Inference
   ```

   No architecture introduced by ADR-0016 may bypass the Artifact Resolution
   layer (preserves ADR-0006, ADR-0008, ADR-0009, ADR-0010, ADR-0011,
   ADR-0012).

6. **Domain boundary** — Runtime infrastructure is **not** part of the domain
   model. The domain model contains: Voice, VoiceSourceAsset, VoicePreview,
   VoiceVariant, VoiceVariantArtifact, Model, Provider, Adapter,
   VoiceResource. Runtime infrastructure (RuntimeRegistry, RuntimeManager,
   RuntimeDriver, RuntimeService, RuntimeInstance) is **infrastructure** and
   must never become a domain entity. Forbidden future patterns include
   `RuntimeServiceEntity`, `RuntimeServiceRepository`, `RuntimeVariant`,
   `RuntimeArtifact`.

### Constraints (constitution articles, ADRs that bind this)

- **Constitution Article I, §1** — PeakVox is a Universal Voice Runtime.
- **Constitution Article III, §8** — The Runtime is the single, model-agnostic
  generation entry point.
- **Constitution Article III, §9** — Nothing above the adapter line imports a
  model implementation. ADR-0016 *strengthens* this: the backend process
  itself is now above the line; only the Runtime Service imports the model.
- **Constitution Article V, §14** — CE and Cloud share the architecture. The
  RuntimeDriver abstraction is the seam that lets CE use Docker and Cloud use
  Kubernetes without diverging.
- **ADR-0004** — Voice, VoiceVariant, and Model are three separate concepts.
  Adapters remain the only translation point.
- **ADR-0006, ADR-0008, ADR-0009** — Variant realization + artifact lifecycle
  are not bypassed.
- **ADR-0010, ADR-0011, ADR-0012** — Provisioning policies and Creation
  Sources continue to govern variant builds.

### Future drivers (informational only)

- `DockerRuntimeDriver` — Community Edition initial implementation.
- `KubernetesRuntimeDriver` — Cloud Edition production.
- `PodmanRuntimeDriver` — rootless / alternative environments.
- `LocalProcessDriver` — development / single-process testing.

These are not implemented. They exist in the ADR to validate that the
RuntimeDriver abstraction is future-proof.

---

## Acceptance criteria

For this ADR / Phase 1:

- [ ] ADR-0016 is **Accepted**.
- [ ] The RuntimeRegistry, RuntimeManager, RuntimeDriver, RuntimeService,
      and RuntimeInstance concepts are formally defined.
- [ ] The Domain Boundary section explicitly states that runtime
      infrastructure is not a domain concept.
- [ ] The "PeakVox installs runtimes, not models" distinction is explicit
      and paired with the model-many-runtimes example.
- [ ] The 7-phase migration path is documented and self-contained.
- [ ] Architectural Invariants 1–10 are stated.
- [ ] Cross-links to Constitution Articles I, III §8, III §9, V and to
      ADR-0004, ADR-0006, ADR-0008, ADR-0009, ADR-0010, ADR-0011, ADR-0012
      are present and resolve.
- [ ] `IMPLEMENTATION_STATUS.md` records ADR-0016 as **APPROVED** (not
      IMPLEMENTED). Per Constitution §22, an Accepted ADR is not evidence of
      implementation.
- [ ] No code, no `runtime-registry/` directory, no Docker wiring, no
      F5-TTS implementation, no adapter changes. All deferred to Phase 2+.

For the broader feature (validated across all 7 phases):

- [ ] F5-TTS can be installed as an isolated runtime.
- [ ] Kokoro runs as an isolated runtime.
- [ ] The backend image contains **no** model-specific dependencies
      (torch, transformers, kokoro, f5-tts, fish-audio).
- [ ] Runtime lifecycle (install / activate / deactivate / update / remove)
      is managed independently of backend releases.
- [ ] The architecture is compatible with future Kubernetes deployment
      without backend redesign.
- [ ] Adding a new model requires only: model metadata, runtime descriptor,
      runtime image, adapter.

---

## Open questions (deferred)

These are tracked for the implementation phases. They do not block ADR
acceptance.

- How is the runtime endpoint discovered at runtime? DNS-based service
  name (Docker compose default), explicit URL, or sidecar registry?
- What is the upgrade / rollback story for a runtime? (Container image
  tagging strategy.)
- How is GPU allocation negotiated between the backend and the runtime
  service? (Runtime exposes the GPU; backend never imports CUDA.)
- What is the per-runtime health contract? (Liveness + readiness.)
- Does the backend authenticate to runtime services? (mTLS, token, none.)

These become the design surface for Phase 2.

---

## Architectural Invariants

1. **Models are catalog entities.** A Model is a row in `models` (ADR-0002).
2. **Runtimes are deployment units.** A Runtime is a runtime image +
   descriptor + instance, managed by the Runtime Manager.
3. **PeakVox installs runtimes, not models.** The install surface is the
   Runtime Registry. The model is the logical identity; the runtime is the
   executable form.
4. **The backend never owns model dependencies.** The backend image ships
   only the Runtime Manager + adapters + Driver + protocol. Model code
   (torch, transformers, kokoro, f5-tts) lives in Runtime Service images.
5. **The backend never executes model inference.** Inference is the
   Runtime Service's responsibility. The adapter translates; the driver
   routes; the service runs.
6. **Runtime Manager orchestrates runtimes.** It does not execute them.
7. **Runtime Registry describes runtimes.** The descriptor is the contract.
8. **Adapters communicate with runtime services.** Adapters remain the
   translation point (ADR-0004). Adapters never talk to Docker, Kubernetes,
   or any other infrastructure directly.
9. **Runtime services are replaceable.** A model can have multiple runtimes
   (CUDA, CPU, local, cloud). Replacing one runtime does not require
   backend changes.
10. **CE and Cloud share the architecture.** The RuntimeDriver abstraction
    is the seam: Docker in CE, Kubernetes in Cloud.
11. **Runtime infrastructure is not a domain concept.** Forbidden:
    `RuntimeServiceEntity`, `RuntimeServiceRepository`, `RuntimeVariant`,
    `RuntimeArtifact`.
12. **Active Artifact resolution is preserved.** Voice → VoiceVariant →
    Active Artifact → Adapter → Runtime Manager → Runtime Driver →
    Runtime Service → Inference. No bypass.

---

## Final Statement

> **Voices are assets. Models are engines. Runtimes are infrastructure.
> Adapters are translators. The Runtime is orchestration.**

---

**Related:** [`DESIGN.md`](DESIGN.md) · [`TASKS.md`](TASKS.md) ·
[`VALIDATION.md`](VALIDATION.md) · [`STATUS.md`](STATUS.md) ·
[`adr-0016-models-as-runtime-services.md`](../../../DECISIONS/adr-0016-models-as-runtime-services.md) ·
[`../../CONSTITUTION.md`](../../../CONSTITUTION.md) ·
[`../../ARCHITECTURE/runtime-architecture.md`](../../../ARCHITECTURE/runtime-architecture.md)

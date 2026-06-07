# ADR-0016: Models as Runtime Services

- **Status:** Accepted
- **Date:** 2026-06-07
- **Deciders:** PeakVox architecture (this ADR formalizes the
  Runtime-Service architecture already implied by
  [`runtime-architecture.md`](../ARCHITECTURE/runtime-architecture.md) §9.2
  and strengthens Constitution Articles I, III §8, III §9, V).
- **Supersedes:** none.
- **Superseded by:** none.
- **Spec:** [`../SPECS/FEATURES/models-as-runtime-services/`](../SPECS/FEATURES/models-as-runtime-services/)

---

## Context

PeakVox today loads model implementations directly inside the backend
Python process. The backend owns the model lifecycle (install, load,
unload, execute), the GPU memory, and the model's Python dependencies.
Each new model is a Python package in the same process as the API.

The current two-model spine (OmniVoice + Kokoro) works this way, and
the [`ModelAdapter`](../ARCHITECTURE/runtime-architecture.md) contract
(ADR-0004) cleanly isolates model specifics from the Runtime. But the
coupling that remains — model code inside the backend process — does
not scale to the vision of PeakVox as a Universal Voice Runtime hosting
many models (F5-TTS, Fish Audio, XTTS, OpenVoice, future providers).

The concrete pressures:

1. The backend image becomes polluted with model-specific dependencies.
2. Each model introduces dependency conflicts.
3. GPU management becomes increasingly difficult.
4. Horizontal scaling becomes expensive.
5. Runtime isolation is weak.
6. Model upgrades become risky (in-process reloads).
7. Backend image gains Docker / orchestration concerns.
8. Cloud deployment couples backend releases to model releases.
9. Large models become tightly coupled to backend lifecycle.

The product is the **Runtime Layer**, not any model. Models are
interchangeable engines. They must not couple to the backend process.

The architecture already anticipates a distributed future
([`runtime-architecture.md` §9.2](../ARCHITECTURE/runtime-architecture.md))
where CE in-process and Cloud workers run the same runtime code. The
gap is that the *substrate* (Docker today, Kubernetes in Cloud) is
implicit; this ADR makes the substrate a named, first-class seam
**now** and applies the model-agnostic runtime pattern to **every**
edition.

---

## Options considered

### Option A — Keep models in-process; harden the model registry

Continue treating the model implementation as a Python package in the
backend process. Add dependency isolation tricks (sub-interpreters,
process pools) to mitigate conflicts.

- **Pros:** Minimum change today; no new operational surface.
- **Cons:** Does not solve GPU management, horizontal scaling, or
  release coupling. Adds Python-specific complexity. Cloud
  architecture is still a redesign, not a deployment change.
- **Rejected.**

### Option B — Models as separate worker processes (no container)

Spawn the model as a subprocess and talk to it over a socket. The
backend orchestrates the lifecycle.

- **Pros:** Real isolation; no Docker coupling at first.
- **Cons:** Subprocess management on the host is brittle; no
  environment isolation; no image portability; no GPU-aware
  scheduling; Cloud still requires container semantics later.
- **Rejected** as a final state. Kept as `LocalProcessDriver` for
  development / single-node testing.

### Option C — Models as Runtime Services (chosen)

Models become isolated runtime workloads, described by a
`runtime.yaml` descriptor, managed by a **Runtime Manager** that
delegates to a **Runtime Driver** abstraction. The first driver is
`DockerRuntimeDriver`; Kubernetes, Podman, and local-process drivers
are future implementations. Adapters translate between PeakVox
concepts and the runtime protocol; they no longer import model code.

- **Pros:**
  - **Architectural seam:** the RuntimeDriver interface is the
    substrate-neutral contract. CE = Docker, Cloud = Kubernetes, no
    business-logic divergence.
  - **Operational separation:** backend image becomes model-free;
    model images can ship on their own release cadence.
  - **GPU hygiene:** the runtime service owns the device; the
    backend never holds VRAM.
  - **Edition parity:** Article V §14 is preserved by construction.
  - **Constitution reinforcement:** Articles I, III §8, III §9 are
    strengthened, not weakened.
  - **Domain cleanliness:** runtime infrastructure is *not* a domain
    concept. No new domain entities.
  - **Forward compatibility:** the same architecture supports
    F5-TTS, Fish Audio, XTTS, and any future provider.

- **Cons:**
  - **Migration cost:** 7 phases; in-process path is removed only
    in Phase 7.
  - **Operational surface:** Docker (and later Kubernetes) is now
    a runtime dependency of PeakVox. Mitigation: `LocalProcessDriver`
    for development without Docker.
  - **Latency overhead:** adapter → runtime service adds a network
    hop. Mitigation: in-process IPC drivers for low-latency paths;
    co-located runtime services in CE.

- **Chosen.**

---

## Decision

PeakVox evolves from "Model = Python Package" to **Model = Runtime
Service**, executed through a new orchestration layer that sits
between the adapter and the substrate.

The change is purely architectural in this phase. **No code is
written.** The migration is sequenced across 7 phases (see
[`TASKS.md`](../SPECS/FEATURES/models-as-runtime-services/TASKS.md)).

### Architectural flow (corrected)

```
Voice
  → VoiceVariant
    → Active Artifact (ADR-0009)
      → Adapter
        → Runtime Manager           ← new orchestration layer
          → Runtime Driver          ← new execution abstraction
            → Runtime Service       ← new execution unit (container)
              → Inference
```

The Active Artifact resolution step is **mandatory** and **may not be
bypassed** by anything introduced by this ADR. This preserves
ADR-0006, ADR-0008, ADR-0009, ADR-0010, ADR-0011, ADR-0012.

### Domain boundary (explicit)

Runtime infrastructure is **not** part of the domain model. The
domain model contains: Voice, VoiceSourceAsset, VoicePreview,
VoiceVariant, VoiceVariantArtifact, Model, Provider, Adapter,
VoiceResource.

Runtime infrastructure (RuntimeRegistry, RuntimeManager,
RuntimeDriver, RuntimeService, RuntimeInstance) is **infrastructure
only** and must never become a domain entity.

**Forbidden future patterns:**

- `RuntimeServiceEntity`
- `RuntimeServiceRepository`
- `RuntimeVariant`
- `RuntimeArtifact`
- Any `*Entity` / `*Repository` that names a runtime concept

### The critical conceptual distinction

**PeakVox does not install models. PeakVox installs runtimes.**

- **Models** are logical catalog entities (rows in the `models`
  table; ADR-0002). They are the *what*.
- **Runtimes** are executable deployment units. They are the *how*.

A single model may have many runtimes:

```
Model: F5-TTS
├── Runtime: F5 CUDA Runtime     (image: peakvox/f5-runtime-cuda)
└── Runtime: F5 CPU Runtime      (image: peakvox/f5-runtime-cpu)

Model: OmniVoice
├── Runtime: OmniVoice Local Runtime   (image: peakvox/omnivoice-local)
└── Runtime: OmniVoice Cloud Runtime   (image: peakvox/omnivoice-cloud)
```

The install surface is the **Runtime Registry**. The descriptor
(`runtime.yaml`) is the **runtime contract**.

### Runtime Manager — orchestration only

The Runtime Manager **performs orchestration only**. It is a thin,
adapter-agnostic lifecycle coordinator. It depends solely on the
`RuntimeDriver` interface and never on a specific substrate.

**Owns:**

- **Discovers** runtimes from the Runtime Registry; reads
  `runtime.yaml` descriptors.
- **Resolves endpoints** — knows which URL an adapter should call for
  a given runtime.
- **Delegates** all lifecycle operations to the Runtime Driver
  (install, update, remove, start, stop, restart, status, logs,
  health, metrics).
- **Reports status** — surfaces the driver's view of each
  `RuntimeInstance` to the rest of the system (API, adapters, ops).

**Does NOT own:**

- Execute inference.
- Allocate GPUs (or any device).
- Load model weights.
- Import model frameworks (torch, transformers, kokoro, f5-tts,
  fish-audio, or any other model code).
- Perform substrate-specific operations (Docker / Kubernetes /
  Podman / shell calls). Substrate-specific code lives only inside
  concrete driver implementations.

The boundary is structural: the Runtime Manager has no concept of
Docker, Kubernetes, Podman, containers, images, networks, or
processes. All of those are the driver's concern. Adapters likewise
have no concept of substrate; they ask the Runtime Manager for a
route.

### Runtime Driver — interface contract

The Runtime Manager depends only on `RuntimeDriver`. This is the
load-bearing architectural seam.

Required operations (responsibilities normative, naming illustrative):

| Operation | Responsibility |
|---|---|
| `install_runtime(runtime_id, descriptor) -> RuntimeInstance` | Pull image, register instance. |
| `update_runtime(runtime_id, descriptor) -> RuntimeInstance` | Re-pull, possibly restart. |
| `remove_runtime(runtime_id) -> None` | Stop, delete image, unregister. |
| `start_runtime(runtime_id) -> RuntimeInstance` | Bring up the instance. |
| `stop_runtime(runtime_id) -> None` | Tear down the instance. |
| `restart_runtime(runtime_id) -> RuntimeInstance` | Stop + start. |
| `runtime_status(runtime_id) -> RuntimeInstance` | Current state + endpoint. |
| `runtime_logs(runtime_id, since) -> LogStream` | Stream of logs. |
| `runtime_health(runtime_id) -> HealthReport` | Liveness + readiness. |
| `runtime_metrics(runtime_id) -> Metrics` | Optional / future-safe. |

**The Runtime Manager must never import Docker / Kubernetes / Podman
directly.** Substrate-specific code lives only in concrete driver
implementations.

### First driver and future drivers

- `DockerRuntimeDriver` — **first implementation**, used by
  Community Edition. This is an implementation choice, not an
  architectural dependency.
- `KubernetesRuntimeDriver` — Cloud Edition production (future).
- `PodmanRuntimeDriver` — rootless / alternative environments
  (future).
- `LocalProcessDriver` — development / single-process testing
  (future).

Future drivers are listed to validate that the abstraction is
future-proof. They are not implemented and are not specified in
detail.

### Runtime Registry — future structure (architecture only)

```
peakvox/
├── frontend/
├── backend/
├── docs/
├── scripts/
└── runtime-registry/                  ← future, not created in Phase 1
    ├── omnivoice/
    │   ├── runtime.yaml
    │   ├── docker-compose.yml
    │   ├── env.example
    │   └── README.md
    ├── kokoro/
    │   └── …
    ├── f5-tts/
    │   └── …
    ├── fish-audio/
    │   └── …
    └── xtts/
        └── …
```

This directory is **not** created by this ADR. The structure is
captured here so that implementers in Phase 2+ have a clear target.

### Runtime Descriptor — full schema

The `runtime.yaml` descriptor is the runtime contract:

```yaml
id: f5-tts                            # unique runtime id
runtime_type: docker                  # docker | kubernetes | podman | process
image:
  repository: peakvox/f5-runtime
  tag: latest
api:
  endpoint: http://f5-runtime:8000
  protocol: http                      # http | grpc
  health_endpoint: /health
  generate_endpoint: /v1/generate
health:
  endpoint: /health
  interval_seconds: 10
  timeout_seconds: 3
capabilities:
  - tts
  - voice_cloning
  - multilingual
requirements:
  gpu: optional                       # required | optional | none
  min_vram_gb: 8
  cpu_cores: 2
  memory_gb: 4
edition:
  - ce                                # community edition supported
  - cloud                             # cloud edition supported
```

### Adapter evolution

Adapters remain first-class architecture components (ADR-0004). Their
responsibilities do not disappear. They evolve in transport only:

```
BEFORE:  Adapter  → Python package  → torch / transformers / kokoro / f5-tts
AFTER:   Adapter  → HTTP / gRPC     → Runtime Service
```

- `OmniVoiceAdapter` → HTTP/gRPC → `OmniVoice Runtime Service`
- `F5Adapter` → HTTP/gRPC → `F5 Runtime Service`
- `FishAdapter` → HTTP/gRPC → `Fish Runtime Service`
- `KokoroAdapter` → HTTP/gRPC → `Kokoro Runtime Service`

The adapter remains responsible for capability declaration, variant
build strategies, supported realization types, capability / tag /
language / voice-design validation, and translating PeakVox concepts
to and from the runtime protocol. The contract is unchanged; the
transport becomes remote.

### Generation flow (post-migration)

```
1. authenticate            → principal (CE: local owner)            [Auth seam]
2. resolve voice           → Voice by public_voice_id
3. route model             → Model (explicit | default | auto)
4. validate capabilities   → request vs ModelCapabilities (ADR-0003) → 422 on mismatch
5. ensure variant          → VoiceVariant(Voice, Model)              [ADR-0008]
6. resolve active artifact → Active Artifact (ADR-0009)
7. acquire adapter         → ModelAdapter for the model
8. acquire runtime         → RuntimeManager.route(model) → runtime endpoint
9. translate + send        → adapter.generate(variant, artifact, text, params)
                             → POST /v1/generate to runtime endpoint
10. deliver                → audio stream | URL
11. emit generation.completed → metering + royalties (Cloud)         [emit only]
```

Steps 8 and 9 are new; they replace in-process inference. Steps 1–7
and 10–11 are unchanged.

### Migration phases (7)

1. **Phase 1** — ADR + design docs. **This phase.** No code.
2. **Phase 2** — Runtime Registry + Runtime Manager skeleton +
   `DockerRuntimeDriver`. No model migrated.
3. **Phase 3** — Kokoro migration. First validation target.
4. **Phase 4** — F5-TTS as Runtime Service. **Reference
   implementation.** F5-TTS becomes the canonical "how to add a new
   model" example.
5. **Phase 5** — Fish Audio migration.
6. **Phase 6** — OmniVoice migration.
7. **Phase 7** — Remove direct in-process model execution. Backend
   image becomes model-free.

### Constitutional reinforcement

This ADR *strengthens* (never weakens):

- **Article I, §1** — "Universal Voice Runtime, not a model
  frontend." The runtime is now even more orchestration-only.
- **Article III, §8** — "The Runtime is the single, model-agnostic
  generation entry point." The Runtime (now the Runtime Manager) is
  the only thing the API talks to. Adapters are downstream.
- **Article III, §9** — "Nothing above the adapter line imports a
  model implementation." The line is now drawn around the *backend
  process*: the backend process never imports torch, transformers,
  kokoro, f5-tts, or fish-audio. Only Runtime Service images import
  model code.
- **Article V, §14–17** — "CE and Cloud share the architecture." The
  RuntimeDriver abstraction is the seam: Docker in CE, Kubernetes in
  Cloud, no architectural divergence.

No exception to the constitution is introduced.

### Architectural invariants

1. Models are catalog entities.
2. Runtimes are deployment units.
3. PeakVox installs runtimes, not models. One Model → many Runtimes.
4. The backend never owns model dependencies.
5. The backend never executes model inference.
6. Runtime Manager orchestrates; it does not execute.
7. Runtime Registry describes; the descriptor is the contract.
8. Adapters communicate with runtime services; they never talk to
   Docker / Kubernetes / Podman directly.
9. Runtime services are replaceable.
10. CE and Cloud share the architecture (RuntimeDriver is the seam).
11. Runtime infrastructure is not a domain concept.
12. Active Artifact resolution is preserved.

### Final statement

> **Voices are assets. Models are engines. Runtimes are
> infrastructure. Adapters are translators. The Runtime is
> orchestration.**

---

## Consequences

### Positive

- **Clean domain:** runtime infrastructure stays out of the domain
  model. No new entities, no new repositories, no new domain
  concepts.
- **Edition parity:** CE and Cloud use the same architecture. The
  driver is the seam.
- **Operational separation:** backend image becomes model-free;
  model images ship on their own cadence.
- **GPU hygiene:** the runtime service owns the device. The backend
  never holds VRAM.
- **Multi-runtime per model:** CUDA / CPU / local / cloud variants
  are first-class, not hacks.
- **Provider agility:** F5-TTS, Fish Audio, XTTS, OpenVoice, and
  future providers all integrate through the same surface.
- **Constitution strength:** Articles I, III §8, III §9, V become
  harder to violate, not easier.

### Negative / costs

- **Migration cost:** 7 phases; in-process path is removed only in
  Phase 7. The current CE must continue to work throughout.
- **Operational surface:** Docker (and later Kubernetes) becomes a
  PeakVox runtime dependency. Mitigation: `LocalProcessDriver` for
  development without Docker.
- **Latency overhead:** adapter → runtime service adds a network
  hop. Mitigation: co-located runtime services in CE; in-process IPC
  drivers for low-latency paths (future).
- **Adapter work:** every adapter must be ported to `HTTPTransport`.
  This is sequenced across Phases 3–6.

### Follow-ups / what this enables or forecloses

- **Enables:** Kubernetes deployment, autoscaling on queue depth,
  per-model GPU pools, multi-region, marketplace-grade retention
  without backend redesign. Multi-runtime variants per model
  (CUDA / CPU / cloud).
- **Enables:** Backend image size drops dramatically (no torch,
  no transformers, no kokoro, no f5-tts). Deploy times drop.
- **Forecloses:** Direct in-process model execution as a stable
  API. After Phase 7, "import torch" in the backend image is a
  constitution violation.

---

**Related:** [`../SPECS/FEATURES/models-as-runtime-services/`](../SPECS/FEATURES/models-as-runtime-services/) ·
[`../ARCHITECTURE/runtime-architecture.md`](../ARCHITECTURE/runtime-architecture.md) ·
[`../CONSTITUTION.md`](../CONSTITUTION.md) ·
[`../DECISIONS/ADR_INDEX.md`](ADR_INDEX.md)

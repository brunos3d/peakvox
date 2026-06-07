# DESIGN — Models as Runtime Services

> **How it will be built.** SDD stage 3. References the [SPEC](./SPEC.md) and
> [ADR-0016](../../../DECISIONS/adr-0016-models-as-runtime-services.md).
> **Phase 1 of 7 — architecture only. No code.**

---

## Approach

The architectural change is a **seam insertion** rather than a rewrite. The
existing resolution chain in [`runtime-architecture.md`](../../../ARCHITECTURE/runtime-architecture.md)
is preserved end-to-end. A new orchestration layer — the **Runtime Manager**
— is inserted *after* the adapter is selected, sitting between the adapter
and the (formerly in-process) model implementation. The model implementation
migrates from "Python package inside the backend" to "container reachable
over a stable contract" — i.e. a **Runtime Service**.

The key conceptual move:

- **Models stay as catalog entities** (rows in `models`, ADR-0002).
- **Runtimes become deployment units** (image + descriptor + instance,
  managed by the Runtime Manager).
- **One Model can have many Runtimes** (CUDA / CPU / local / cloud).
- **The adapter is unchanged in contract**; its transport evolves from
  in-process Python to HTTP/gRPC.
- **The Active Artifact resolution step is preserved** (ADR-0009).

The change is purely architectural in Phase 1. The implementation is a
7-phase migration (see [TASKS.md](./TASKS.md)).

---

## Architectural Flow (corrected)

```
Voice
  → VoiceVariant
    → Active Artifact (ADR-0009)
      → Adapter
        → Runtime Manager           ← NEW orchestration layer
          → Runtime Driver          ← NEW execution abstraction
            → Runtime Service       ← NEW execution unit (container)
              → Inference
```

**Why the Active Artifact step is mandatory in this flow:**

PeakVox's existing voice artifact system (ADR-0006, ADR-0008, ADR-0009,
ADR-0010) deliberately separates *identity* (Voice) from *realization*
(VoiceVariant) from *materialized artifact* (VoiceVariantArtifact) from
*active version* (Active Artifact). The adapter receives the active
artifact, not the abstract variant, so the runtime can:

- Run inference against the exact realized artifact version
- Pin to a specific artifact version for reproducibility (ADR-0009 §5)
- Trigger rebuilds from a source asset (ADR-0010) without disturbing the
  artifact layer

No architecture introduced by ADR-0016 may bypass the Artifact Resolution
layer.

---

## Components touched

### Backend (new components in Phase 2+)

| Component | Phase | Role |
|---|---|---|
| `RuntimeManager` | 2 | Orchestrates runtime lifecycle. Never executes inference. |
| `RuntimeDriver` (interface) | 2 | Abstract execution substrate. |
| `DockerRuntimeDriver` | 2 | First concrete driver. CE initial implementation. |
| `RuntimeRegistryLoader` | 2 | Reads `runtime.yaml` descriptors. |
| `RuntimeEndpointResolver` | 3 | Maps runtime_id → reachable URL. |
| Adapter `HTTPTransport` | 3+ | Generic HTTP/gRPC adapter transport. |
| `KokoroRuntimeAdapter` | 3 | Kokoro as a remote runtime. |
| `F5RuntimeAdapter` | 4 | F5-TTS as a remote runtime (reference). |
| `FishRuntimeAdapter` | 5 | Fish Audio as a remote runtime. |
| `OmniVoiceRuntimeAdapter` | 6 | OmniVoice as a remote runtime. |

### Backend (no changes in Phase 1)

- `PeakVoxRuntime` (`backend/app/services/runtime.py`) — unchanged contract.
- `ModelAdapter` (`backend/app/services/model_adapter.py`) — unchanged
  contract.
- All existing adapters (`omnivoice_adapter`, `kokoro_adapter`,
  `fish_adapter`) — continue to execute in-process; migration is additive.
- All domain repositories, services, and APIs — unchanged.

### Frontend (no changes in Phase 1, possibly later)

- A future Models page may surface runtime install/activate/deactivate, but
  that is a UX decision deferred to the relevant migration phase. The
  `voices/page.tsx` UI is not touched in Phase 1.

### Runtime / adapter impact (Phase 3+)

- Adapters gain a new transport: HTTP/gRPC to a remote runtime service.
- The adapter's **contract** (`generate`, `build_variant`, `health_check`,
  capabilities, supported realization types, build strategies) does not
  change. The contract remains the **stable interface** between the
  model-agnostic Runtime and the model-specific provider.
- The first adapters migrated are: Kokoro (Phase 3, validation),
  F5-TTS (Phase 4, reference), Fish (Phase 5), OmniVoice (Phase 6).
- Phase 7 removes direct in-process model execution; the in-process code
  path is deleted once each model has at least one runtime service
  available.

---

## Data / schema changes

**Phase 1 (this ADR): no changes.**

The existing `models` table (ADR-0002) is the catalog. The runtime layer
operates on the existing `models` rows; it does not introduce new tables.
Per Constitution §18 ("Migrations are additive and idempotent"), any
future persistence for runtime instances will follow the SQLite-safe
runner in `app/core/migrations.py`.

**Future (Phase 2+, deferred):**

A possible `runtime_instances` table would be **infrastructure state**,
not domain state. It would track:

```
runtime_instances:
  id, runtime_id, model_id, status, endpoint, image_tag,
  started_at, last_health_at, health_state, ...
```

This is explicitly *not* a `RuntimeServiceEntity` and is not part of the
domain. It is the Runtime Manager's bookkeeping, and would be
implementation detail of the chosen driver.

Per Constitution Article II, no runtime concept may become a domain
entity. Forbidden:

- `RuntimeServiceEntity`
- `RuntimeServiceRepository`
- `RuntimeVariant`
- `RuntimeArtifact`

---

## Capability / edition gating

- **ADR-0003** — Capabilities remain declared on `ModelDescriptor`; the
  Runtime Descriptor carries a *subset* of capabilities as documentation of
  what the runtime image actually implements. The runtime cannot exceed
  the model's declared contract.
- **ADR-0005** — Model editions (CE / Cloud) remain declared on the model.
  A Cloud-only model may have runtimes that are CE-incompatible; the
  descriptor carries `requirements` and the Runtime Manager rejects
  activation when the host cannot satisfy them.
- **ADR-0012** — Voice resources and creation sources are unaffected.
  Voice-resource browsing remains a domain concern; runtime browsing is
  infrastructure concern.

---

## Runtime Manager — orchestration only

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

- Execute model inference.
- Allocate GPUs (or any device).
- Load model weights.
- Import model frameworks (torch, transformers, kokoro, f5-tts,
  fish-audio, or any other model code).
- Perform substrate-specific operations (Docker / Kubernetes /
  Podman / shell calls). Substrate-specific code lives only inside
  concrete driver implementations.
- Own Voice / Variant / Artifact state (the domain owns that).

---

## Runtime Driver — interface contract

**The Runtime Manager depends only on `RuntimeDriver`.** This is the
load-bearing architectural seam. The first implementation is
`DockerRuntimeDriver`; other drivers are listed as future work to validate
the abstraction.

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

**Forbidden — direct substrate calls from the Runtime Manager:**

- `docker.Client(...)` / `docker.from_env()` (in the Runtime Manager).
- `kubernetes.client.AppsV1Api()` (in the Runtime Manager).
- `subprocess.run(["docker", ...])` (in the Runtime Manager).
- Any shell-out to `kubectl`, `podman`, `nerdctl`.

These are allowed *only* inside concrete driver implementations
(`DockerRuntimeDriver`, `KubernetesRuntimeDriver`, etc.). The Runtime
Manager and any business logic must depend only on the `RuntimeDriver`
protocol.

---

## Future drivers (informational only — not implemented in Phase 1)

- `DockerRuntimeDriver` — Community Edition initial driver. Image-based
  runtimes; Docker compose for multi-container scenarios.
- `KubernetesRuntimeDriver` — Cloud Edition production driver. Deployments,
  Services, GPU resource claims, Horizontal Pod Autoscaler.
- `PodmanRuntimeDriver` — Rootless alternative. Same operational shape as
  Docker.
- `LocalProcessDriver` — Development / testing. Runs the runtime image as
  a subprocess on the same host as the backend; no container isolation.

These are listed to validate that the abstraction is future-proof. They
are not implemented, and ADR-0016 does not specify their semantics beyond
the shared `RuntimeDriver` interface.

---

## Runtime Registry — future structure (architecture only)

The future directory structure for the runtime registry is:

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
    │   ├── runtime.yaml
    │   ├── docker-compose.yml
    │   ├── env.example
    │   └── README.md
    ├── f5-tts/
    │   ├── runtime.yaml
    │   ├── docker-compose.yml
    │   ├── env.example
    │   └── README.md
    ├── fish-audio/
    │   ├── runtime.yaml
    │   ├── docker-compose.yml
    │   ├── env.example
    │   └── README.md
    └── xtts/
        ├── runtime.yaml
        ├── docker-compose.yml
        ├── env.example
        └── README.md
```

**Phase 1 does not create this directory.** It is described in the ADR so
that implementers in Phase 2+ have a clear target.

---

## Runtime Descriptor — full schema

The `runtime.yaml` descriptor is the runtime contract. It is the only
artifact required (in addition to the runtime image and the adapter) to
add a new model.

```yaml
id: f5-tts                            # unique runtime id

runtime_type: docker                  # docker | kubernetes | podman | process

image:
  repository: peakvox/f5-runtime
  tag: latest

api:
  endpoint: http://f5-runtime:8000    # initial endpoint (overridable at runtime)
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

Fields are advisory for Phase 1; the schema is finalized in Phase 2.

---

## Adapter evolution

Adapters remain **first-class architecture components** (ADR-0004). Their
responsibilities do not disappear. They evolve in transport only:

```
BEFORE:  Adapter  → Python package  → torch / transformers / kokoro / f5-tts
AFTER:   Adapter  → HTTP / gRPC     → Runtime Service
```

Examples (post-migration):

- `OmniVoiceAdapter` → HTTP/gRPC → `OmniVoice Runtime Service`
- `F5Adapter` → HTTP/gRPC → `F5 Runtime Service`
- `FishAdapter` → HTTP/gRPC → `Fish Runtime Service`
- `KokoroAdapter` → HTTP/gRPC → `Kokoro Runtime Service`

The adapter remains responsible for:

- Capability declaration (ADR-0003).
- Variant build strategies (ADR-0008, ADR-0012).
- Supported realization types (ADR-0008).
- Realization type taxonomy (ADR-0006).
- Capability / tag / language / voice-design validation.
- Translating PeakVox concepts to and from the runtime protocol.

The adapter does **not** become a "thin RPC client". It remains the
semantic translator. The only change is that the engine it talks to is
remote and reachable over a stable contract, instead of being a Python
package in the same process.

---

## Generation flow (post-migration)

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

The new steps (8, 9) replace the in-process inference. Steps 1–7 and 10–11
are unchanged.

---

## Installation flow (post-migration)

```
Install:
  User clicks Install (Future: Models page)
    ↓
  Backend API
    ↓
  Runtime Manager
    ↓
  Read runtime-registry/<runtime_id>/runtime.yaml
    ↓
  RuntimeDriver.install_runtime(runtime_id, descriptor)
    ↓
  Image pulled
    ↓
  Runtime registered
    ↓
  Installed

Activate:
  User clicks Activate
    ↓
  Runtime Manager
    ↓
  RuntimeDriver.start_runtime(runtime_id)
    ↓
  Health check
    ↓
  Active

Deactivate:
  User clicks Deactivate
    ↓
  Runtime Manager
    ↓
  RuntimeDriver.stop_runtime(runtime_id)
    ↓
  Inactive
```

These flows are **future** (Phase 2+). The `POST /api/v1/models/{id}/install`,
`activate`, `deactivate` endpoints (ADR-0002 lifecycle) are unchanged in
Phase 1 — they continue to operate on the in-process model implementation.
The endpoint contracts are *not* modified in Phase 1.

---

## Constrained by ADRs

- **ADR-0002** (Model as first-class entity) — Models remain in the
  catalog. ADR-0016 adds a runtime layer *alongside* the model, not in
  place of it.
- **ADR-0004** (Voice / Variant / Model separation) — Adapters remain the
  translation point. Their contract is unchanged.
- **ADR-0006** (Realization types) — Variant realization types are
  declared by the adapter. Unchanged.
- **ADR-0008** (Variant build lifecycle) — Build pipelines may be
  in-runtime (the runtime service exposes its own build endpoint) or
  in-adapter. The lifecycle states are unchanged.
- **ADR-0009** (Artifact versioning) — The active artifact remains the
  unit of reproducibility. Runtimes pin to artifact versions.
- **ADR-0010** (Source assets + auto-provisioning) — Provisioning still
  triggered by Source Asset changes. The build target may be a runtime
  service instead of the adapter.
- **ADR-0011** (Creation sources) — Unchanged. The variant build strategy
  per creation source is declared on the adapter, regardless of whether
  the runtime is in-process or remote.
- **ADR-0012** (Voice identity vs catalog resources) — Voice resources
  are domain; runtime registry is infrastructure. The boundary is
  reinforced.
- **ADR-0003, ADR-0005** — Capability contract and edition gating
  unchanged. The runtime descriptor carries a capability subset for
  documentation; the model is the source of truth.
- **ADR-0001, ADR-0007** — Voice identity, canonical metadata, etc. —
  unchanged.

**No ADR is superseded.** ADR-0016 is additive.

---

## Constitution alignment

ADR-0016 *strengthens* (never weakens) the following constitutional
articles:

- **Article I, §1** — "Universal Voice Runtime, not a model frontend." The
  runtime is now even more orchestration-only; the model implementation
  has been fully extracted.
- **Article III, §8** — "The Runtime is the single, model-agnostic
  generation entry point." The Runtime (now the Runtime Manager) is the
  only thing the API talks to. Adapters are downstream.
- **Article III, §9** — "Nothing above the adapter line imports a model
  implementation." The line is now drawn around the *backend process*:
  the backend process never imports torch, transformers, kokoro, f5-tts,
  or fish-audio. Only Runtime Service images import model code.
- **Article V, §14** — "CE and Cloud share the architecture." The
  RuntimeDriver abstraction is the seam: Docker in CE, Kubernetes in
  Cloud, no architectural divergence.
- **Article V, §17** — "Model availability is edition-scoped and
  licensing-governed." The runtime descriptor's `edition` field
  expresses this; the Runtime Manager rejects mismatched activation.

No exception to the constitution is introduced.

---

## Risks

| Risk | Mitigation |
|---|---|
| Scope creep — turning Phase 1 into a code change. | Strict "no code, no migrations" rule for Phase 1. ADR acceptance is the deliverable. |
| Driver abstraction leaks Docker specifics. | ADR pins the interface; concrete drivers are confined to those details. Lint rule (Phase 2) can ban `import docker` outside `DockerRuntimeDriver`. |
| F5-TTS availability assumptions baked into the design. | F5-TTS is named only as a reference migration target. The design is provider-agnostic. |
| Adapter migration breaks existing CE generation. | Migration is additive: each phase adds a remote runtime option while keeping the in-process path. Phase 7 removes the in-process path only when every model has a runtime service. |
| Runtime infrastructure creeps into the domain model. | Constitution-aligned Domain Boundary section; explicit forbidden patterns. |
| GPU allocation double-booked between backend and runtime. | Backend no longer holds GPU. Runtime Service owns the device. VRAM contract is the runtime's concern, not the backend's. |
| 7-phase migration is too long. | Each phase is independently shippable. CE may stop at any phase; Cloud continues from there. |

---

**Related:** [`SPEC.md`](./SPEC.md) · [`TASKS.md`](./TASKS.md) ·
[`VALIDATION.md`](./VALIDATION.md) · [`STATUS.md`](./STATUS.md) ·
[`adr-0016-models-as-runtime-services.md`](../../../DECISIONS/adr-0016-models-as-runtime-services.md) ·
[`../../ARCHITECTURE/runtime-architecture.md`](../../../ARCHITECTURE/runtime-architecture.md)

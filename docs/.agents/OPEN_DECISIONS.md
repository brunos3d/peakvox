# OPEN DECISIONS

> Unresolved architectural decisions. When one is resolved, write an ADR (or amend the
> relevant one), then move the entry to [`DECISIONS/ADR_INDEX.md`](DECISIONS/ADR_INDEX.md).
> These mirror the "Candidate future ADRs" in `../architecture/adrs/README.md` plus active
> open questions.

**Last update:** 2026-06-05

---

## Decision 1 — How to achieve first non-OmniVoice provider validation

- **Status:** ✅ **RESOLVED** (2026-06-05).
- **Decision:** Option 3 — **Kokoro validated as the first non-OmniVoice provider.**
  The `kokoro` pip package was installed (82M, Apache-2.0, CPU-capable), and real audio
  was generated end-to-end through the PeakVox Runtime. All 347 backend tests pass.
- **Context:** The Universal Voice Runtime thesis was architecture-validated but
  provider-validated only for OmniVoice. Fish Audio real inference was blocked (codec/VRAM).
- **Result:** The Cloud readiness gate is now open. The multi-provider thesis is no longer
  architecture-only — Kokoro proves the runtime works with a real non-OmniVoice provider.
- **Related ADRs:** ADR-0008, ADR-0010, ADR-0011; reserved ADR-0012 (provisioning policies),
  ADR-0013 (model categories).
- **See:** `VALIDATION/PROVIDER_VALIDATIONS/kokoro-validation-report.md`

## Decision 2 — Variant provisioning policies per Creation Source (reserved ADR-0012)

- **Status:** OPEN.
- **Context:** ADR-0010's "rebuild every variant from the Source Asset" applies only to
  `SOURCE_ASSET` voices. Other origins (`PRESET_VOICE`, etc.) need their own strategy.
- **Impact:** Provisioning pipeline correctness across origin types.
- **Related ADRs:** ADR-0010, ADR-0011.

## Decision 3 — Model categories (reserved ADR-0013)

- **Status:** OPEN.
- **Context:** Classifying providers — cloning vs preset vs training — to drive provisioning
  and capability expectations.
- **Related ADRs:** ADR-0011.

## Decision 4 — Auth vendor seam (Clerk)

- **Status:** OPEN (Phase 4, Cloud).
- **Context:** First `AuthProvider` adapter choice and principal-resolution wiring.
- **Impact:** Cloud multi-tenancy.

## Decision 5 — Payments/payouts vendor seam (Stripe + Connect)

- **Status:** OPEN (Phases 5–6, Cloud).
- **Context:** First `BillingProvider`/`PaymentProvider`/`PayoutProvider` adapters.

## Decision 6 — SQLite→Postgres cut-over and Alembic adoption

- **Status:** OPEN (Phase 8, Cloud).
- **Context:** Alembic is adopted only at the Cloud Postgres cut-over; CE stays on the
  idempotent SQLite runner.
- **Related:** `../architecture/08-MIGRATION_ARCHITECTURE.md`.

## Decision 7 — pgvector reconsideration

- **Status:** OPEN, current verdict NO.
- **Context:** Only if semantic voice-similarity becomes a product feature; would need its own
  ADR. Today search runs on derived `characteristics`.
- **Related:** `../architecture/03-DATA_ARCHITECTURE.md` §6.

## Decision 8 — Marketplace search backend

- **Status:** OPEN (Phase 7, Cloud).
- **Context:** Postgres FTS vs external index for marketplace discovery at scale.

## Decision 9 — Runtime-Service architecture adopted (ADR-0016)

- **Status:** ✅ **RESOLVED** (2026-06-07).
- **Decision:** PeakVox adopts the Runtime-Service architecture as defined by
  [ADR-0016](DECISIONS/adr-0016-models-as-runtime-services.md). PeakVox installs
  *runtimes*, not models. One Model → many Runtimes (CUDA / CPU / local / cloud).
  Migration is sequenced across 7 phases; Phase 1 (ADR + design) is complete with
  no code. Existing in-process model execution continues unchanged.
- **Context:** The Universal Voice Runtime thesis implied a distributed future (see
  `ARCHITECTURE/runtime-architecture.md` §9.2) but never made the substrate a
  first-class seam. ADR-0016 closes that gap and applies the model-agnostic
  runtime pattern to every edition (Article V §14).
- **Result:** The next workstream is **Phase 2** of the Runtime-Service migration
  (Runtime Manager skeleton + `DockerRuntimeDriver`). This preempts Cloud
  architecture planning; the same target is shared by CE and Cloud, so investing
  in Phase 2 unblocks both.
- **Related:** ADR-0016; [`SPECS/FEATURES/models-as-runtime-services/`](SPECS/FEATURES/models-as-runtime-services/);
  Architecture §9.2 (distributed execution, now formalized).
- **See:** `VALIDATION/PROVIDER_VALIDATIONS/` (Phase 3 will add
  `kokoro-runtime-validation-report.md`).

## Decision 10 — Runtime-Service Phase 2 implementation ADR

- **Status:** OPEN. Phase 2 implementation **may not begin** until the Phase 2
  implementation ADR is accepted (see also [`NEXT_TASK.md`](NEXT_TASK.md) and
  [`ROADMAP/CURRENT_PHASE.md`](ROADMAP/CURRENT_PHASE.md) for the explicit guardrail).
- **Context:** ADR-0016 defers five open questions that the Phase 2 implementation
  must answer before code is written. They are tracked here for the next ADR.
- **Sub-questions:**
  1. **Runtime endpoint discovery** — DNS-based service name vs explicit URL vs
     sidecar registry.
  2. **Runtime upgrade / rollback** — image tagging strategy; in-place upgrade
     vs versioned runtimes.
  3. **GPU allocation protocol** — how the runtime service claims the device;
     how the backend queries it (or stays out of it entirely).
  4. **Runtime health contract** — liveness + readiness endpoints; cadence;
     what counts as healthy.
  5. **Backend-to-runtime authentication** — mTLS, token, none. What is the
     default in CE; what changes in Cloud.
- **Impact:** Phase 2 implementation cannot start until the next ADR lands.
- **Related:** ADR-0016 (Open questions section); Phase 2 tasks in
  `SPECS/FEATURES/models-as-runtime-services/TASKS.md` §2.

### Implementation direction (non-binding)

> **The notes below are implementation direction, not accepted architecture.**
> They are recorded here to seed the Phase 2 ADR. They become binding only when
> the Phase 2 ADR is **Accepted** by the architecture process. They MUST NOT be
> treated as decisions and MUST NOT be used to justify Phase 2 code before the
> ADR is accepted.

#### 1. Runtime endpoint discovery

- **RuntimeManager owns endpoint resolution.** Adapters never discover
  endpoints directly.
- **Adapters never read** Docker, Kubernetes, DNS, environment variables, or
  runtime metadata directly. They ask the RuntimeManager for a route.
- **RuntimeDriver remains responsible for substrate-specific discovery** (e.g.
  resolving a service name into a reachable URL inside a Docker network, K8s
  cluster, etc.). The RuntimeManager does not import or call substrate APIs.

Desired flow:

```
Adapter
  → RuntimeManager
      → RuntimeDriver
          → endpoint
```

#### 2. Runtime upgrade / rollback

- **Prefer versioned runtime images** (e.g. `peakvox/f5-runtime:1.4.2`) over
  mutable tags like `latest` for production paths.
- **Avoid in-place mutable upgrades.** A new version = a new image + (when
  activated) a new instance; do not patch the running image.
- **`RuntimeInstance` always exposes image identity** (repository + immutable
  tag + digest) so the backend can pin, roll back, and audit.
- **Rollback** is a return to a prior image version, not a hot-swap.

#### 3. GPU allocation ownership

- **The Runtime Service owns the device.** It is the only thing that imports
  CUDA / cuDNN / driver libraries.
- **The backend never owns CUDA resources.** The backend process does not
  import `torch.cuda`, `cupy`, or any GPU driver surface.
- **The RuntimeManager only observes** declared capability and reports
  health. It does not allocate, schedule, or release GPUs.
- **VRAM contract** is enforced by the runtime service and reported via
  `runtime_health` / `runtime_metrics`. The RuntimeManager surfaces the
  report; it does not negotiate.

#### 4. Runtime health contract

Separate two concepts:

- **Liveness** — the runtime process is up and responding (HTTP 200 on
  a liveness probe). Used to decide whether to restart the instance.
- **Readiness** — the runtime can actually serve inference right now
  (model loaded, weights resident, GPU claimed, no transient error).
  Used to decide whether to route traffic to the instance.

**Readiness must indicate the runtime can actually serve inference** —
not merely that the process is alive. The RuntimeManager must refuse to
route to an instance whose readiness is `false`. The health endpoint and
cadence are part of the `runtime.yaml` descriptor.

#### 5. Backend-to-runtime authentication

- **Community Edition (default):** `none`. The backend and the runtime
  service are co-located on the same host / Docker network; network-level
  isolation is sufficient.
- **Cloud Edition (deferred):** `token` or `mTLS`. The final choice
  (token-based, mTLS, sidecar mesh) is left to the Cloud ADR.

> These notes do not decide the Cloud authentication mechanism. The
> Phase 2 implementation ADR (or a follow-up Cloud ADR) makes that call.

## Decision 11 — Future runtime drivers (Kubernetes, Podman, LocalProcess)

- **Status:** OPEN (no ADR written).
- **Context:** ADR-0016 names `DockerRuntimeDriver` (CE, first), and lists
  `KubernetesRuntimeDriver` (Cloud), `PodmanRuntimeDriver`, and
  `LocalProcessDriver` as future implementations. None is implemented. They
  exist in the ADR to validate the abstraction.
- **Impact:** Each driver becomes its own ADR when its edition begins
  (Cloud → `KubernetesRuntimeDriver`; alternative deployments → Podman;
  dev/single-process testing → LocalProcess). The shared interface is locked
  by ADR-0016; per-driver ADRs cover substrate-specific semantics only.
- **Related:** ADR-0016 §"Future drivers".

---

**Related:** [`DECISIONS/ADR_INDEX.md`](DECISIONS/ADR_INDEX.md) · [`ROADMAP/ROADMAP.md`](ROADMAP/ROADMAP.md)

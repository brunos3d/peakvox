# VALIDATION — Models as Runtime Services

> **How the work is proven.** SDD stage 6. **Phase 1 (this phase) is
> documentation only; no runtime validation is required.** Per
> Constitution §22, an Accepted ADR is not evidence of implementation.
> ADR-0016 status is **APPROVED, not IMPLEMENTED**.

The validation surface for the broader feature is structured per the
project's standing rule (Constitution §23): **architecture-validated ≠
provider-validated**. Each phase below is tagged with the validation
type it produces.

---

## Tests (per phase)

### Phase 1 — ADR + design (current)

- **Architecture-validated:** Yes. ADR is accepted; spec files exist;
  cross-links resolve; no code is written.
- **Provider-validated:** Not applicable (no implementation).
- **Tests:** N/A (documentation phase). Validation = the artifacts
  themselves (SPEC, DESIGN, TASKS, VALIDATION, STATUS, ADR).

### Phase 2 — Runtime Registry + Runtime Manager skeleton

- **Architecture-validated:**
  - `tests/test_runtime_descriptor.py` — schema validation.
  - `tests/test_runtime_registry.py` — discovery + parsing.
  - `tests/test_runtime_driver_protocol.py` — structural conformance.
  - `tests/test_docker_runtime_driver.py` — install/start/stop/
    health against a mocked Docker client.
  - `tests/test_runtime_manager.py` — delegates to the driver.
  - `tests/test_runtimes_api.py` — `GET /api/v1/runtimes` discovery.
  - `scripts/lint_no_docker_outside_driver.py` — AST lint that
    bans `import docker` outside the driver package.
- **Provider-validated:** Not applicable (no model migrated yet).
- **No regression:** existing 374+ backend tests stay green.

### Phase 3 — Kokoro migration

- **Architecture-validated:**
  - `tests/test_http_transport.py` — generic adapter transport.
  - `tests/test_kokoro_runtime_adapter.py` — adapter talks to
    runtime; falls back to in-process when env unset.
  - `tests/test_runtime_binding_migration.py` — additive + idempotent.
  - `tests/test_runtime_routing.py` — RuntimeManager.route(model_id).
- **Provider-validated:**
  - `docs/.agents/VALIDATION/PROVIDER_VALIDATIONS/kokoro-runtime-validation-report.md`
    — real audio generated E2E through the runtime service.

### Phase 4 — F5-TTS (reference implementation)

- **Architecture-validated:**
  - `tests/test_model_catalog_f5.py` — F5-TTS in the catalog.
  - `tests/test_f5_runtime_adapter.py` — adapter talks to F5 runtime.
  - `tests/test_f5_build_strategies.py` — F5 build strategies
    declared (SOURCE_ASSET only).
- **Provider-validated:**
  - `docs/.agents/VALIDATION/PROVIDER_VALIDATIONS/f5-validation-report.md`
    — real audio generated E2E.

### Phase 5 — Fish Audio migration

- **Architecture-validated:**
  - `tests/test_fish_runtime_adapter.py` — adapter talks to
    Fish runtime.
- **Provider-validated:** Blocked or partial — see existing
  `docs/.agents/VALIDATION/PROVIDER_VALIDATIONS/fish-*-report.md`.
  Architecture-validated at minimum; provider-validated when
  hardware permits.

### Phase 6 — OmniVoice migration

- **Architecture-validated:**
  - `tests/test_omnivoice_runtime_adapter.py` — adapter talks to
    OmniVoice runtime.
- **Provider-validated:**
  - `docs/.agents/VALIDATION/PROVIDER_VALIDATIONS/omnivoice-runtime-validation-report.md`
    — real audio generated E2E.

### Phase 7 — Remove direct in-process execution

- **Architecture-validated:**
  - `tests/test_backend_image_isolation.py` — `pip list` on the
    backend image no longer contains model-specific packages
    (torch, transformers, kokoro, f5-tts, fish-audio).
  - `scripts/lint_architecture_invariants.py` — constitution
    invariants (article-by-article) all hold.
- **Provider-validated:** cumulative — all four models remain
  provider-validated (real audio generation works through their
  runtime services).

---

## Commands

```bash
# Full backend test suite (per phase)
docker compose run --rm backend bash -c "python -m pytest tests/ -q"

# Frontend (where applicable)
cd frontend && pnpm lint && pnpm typecheck && pnpm test

# Architecture compliance
python scripts/lint_no_docker_outside_driver.py
python scripts/lint_architecture_invariants.py

# Cross-link resolution (visual check)
rg -n "\.md\)" docs/.agents/

# Phase 1 specifically — no code may be added
git status --short
rg -n "runtime-registry" backend frontend 2>/dev/null || echo "OK"
```

---

## Result (this phase — Phase 1)

**Pass criteria (Phase 1):**

- ADR-0016 is **Accepted** (status visible in `ADR_INDEX.md`).
- All 5 spec files exist in the feature folder.
- Cross-links to Constitution and ADRs resolve.
- No code in `backend/` or `frontend/`; no `runtime-registry/`
  directory.
- `IMPLEMENTATION_STATUS.md` records ADR-0016 as **APPROVED**
  (per Constitution §22, not IMPLEMENTED).

**Result (this phase — Phase 1):** APPROVED. ADR-0016 is Accepted. All 5
spec files exist; cross-links resolve; no code is added.

**Result (Phases 2–7):** not yet measured. Each phase lands its own
result in its own validation report per
[`../../VALIDATION/`](../../VALIDATION/).

---

## Architecture vs provider validation (the standing distinction)

Per Constitution §23, the project tracks two distinct axes for
anything touching a model:

| Axis | Question | Evidence |
|---|---|---|
| Architecture | Can the platform represent and orchestrate the concept? | Contract / unit / integration tests; ADR accepted. |
| Provider | Does a real model run end-to-end and generate audio? | Provider validation reports with real audio output. |

ADR-0016 (Phase 1) is **architecture-validated** by definition (no
implementation). Each subsequent phase is both architecture- and
provider-validated; the provider axis is gated by the
`VALIDATION/PROVIDER_VALIDATIONS/` reports.

**The two are never conflated.** "Architecture-validated" never implies
"a real model runs end-to-end"; "provider-validated" is the only
statement that a real model ran.

---

**Related:** [`TASKS.md`](./TASKS.md) · [`SPEC.md`](./SPEC.md) ·
[`DESIGN.md`](./DESIGN.md) · [`STATUS.md`](./STATUS.md) ·
[`../../VALIDATION/`](../../VALIDATION/)

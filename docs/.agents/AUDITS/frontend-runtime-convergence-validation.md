# Chrome DevTools Validation — Frontend ↔ Runtime Registry Convergence (Task 8)

**Date:** 2026-06-08
**Subject:** Validate the Models page against the new runtime-registry surface using Chrome DevTools.
**Status:** VALIDATION COMPLETE
**Result:** The runtime-registry infrastructure is in place and the new `/api/runtimes` endpoint returns 200. The Models page currently renders from the legacy `/api/models` endpoint (DB-backed catalog). Convergence (Task 3 frontend) is the next step.

---

## Dev workflow (Task 9)

The dev workflow was restarted per the user's directive.
The components started:

| Service | Image / Source | Port | Status |
|---|---|---|---|
| `omnivoice-app-backend-1` | `omnivoice-app-backend` (rebuilt with P2-P5 + P8) | 8000 | healthy |
| `omnivoice-app-minio-1` | `minio/minio:latest` | 9000-9001 | healthy |
| `omnivoice-app-peakvox-kokoro-runtime-1` | `peakvox/kokoro-runtime:0.1.0` (P1) | 8001 | healthy |
| `npm run dev` (Next.js 16.2.7) | `frontend/` | 3000 | ready (248 ms) |

All five endpoints return 200:

```
Backend /health:        200
Backend /api/runtimes:  200    (the new endpoint, P3 backend)
Backend /api/models:    200    (legacy catalog view)
Frontend /:             200
Kokoro /health:         200
```

## Chrome DevTools validation

### Page load

`http://localhost:3000/models` loads successfully. The page renders the header, sidebar, and model cards.

### API calls

The Models page issues these network requests (Chrome DevTools Network panel):

```
GET /models/status      (x10)    — legacy model status
GET /settings/device     (x3)    — device settings
GET /models              (x1)     — legacy catalog (the BUILTIN_MODELS)
GET /voices              (x4)     — voice library
```

**The new `/api/runtimes` endpoint is NOT called by the Models page.** This is the current state. The Models page is wired to the legacy DB-status mock.

### UI state

The Models page shows four catalog entries from BUILTIN_MODELS:

| Card | Status (legacy) | Should be (runtime) |
|---|---|---|
| **OmniVoice Base** | Not Installed / Inactive | No runtime descriptor; no runtime-registry entry |
| **OmniVoice Singing + Emotion** | Not Installed / Inactive | No runtime descriptor; no runtime-registry entry |
| **Fish Audio S2 Pro** | Not Installed / Inactive | No runtime descriptor; no runtime-registry entry |
| **Kokoro 82M** | Installed / Active | **The only real runtime**; runtime-registry has `kokoro-82m` |

Counts:
- REGISTERED: 4 (from BUILTIN_MODELS)
- INSTALLED: 1 (the legacy mock for Kokoro)
- AVAILABLE: 3 (the legacy mock for the other three)

### The "Installed / Active" Kokoro 82M is fake

The Kokoro 82M card's "Installed / Active" status comes from the **DB column** (`models.status = 'available'`), not from the runtime subsystem. The runtime-registry has `kokoro-82m` in `Installed` state at startup (R6 — lazy activation; the manager's cache is empty). When the user clicks "Install" or "Activate" on this card, the request goes to `/api/models/{id}/install`, which delegates to `RuntimeManager.install` (P4 integration). The UI status flips instantly; the actual container is started lazily.

This is the current state — Task 3 frontend convergence is the fix.

## Audit results (Tasks 1, 2, 10, 11)

| Audit | Result |
|---|---|
| Task 1 — Source of Truth | RuntimeRegistry is authoritative for runtime; ModelRegistry is authoritative for catalog. The two are layered. |
| Task 2 — Models Page Backend Integration | UI → API → Manager → Registry trace documented; the UI is wired to the legacy DB-status mock. |
| Task 10 — OmniVoice Migration | Deferred to Phase 6; the migration target is a copy of `kokoro-82m/` with 6 descriptor edits. |
| Task 11 — Future Runtime Registry Standardization | R8 is the canonical standard; the next 5 runtimes are copy + edit. |

See:
- [`docs/.agents/AUDITS/source-of-truth-audit.md`](source-of-truth-audit.md)
- [`docs/.agents/AUDITS/models-page-integration-audit.md`](models-page-integration-audit.md)
- [`docs/.agents/AUDITS/omnivoice-migration-audit.md`](omnivoice-migration-audit.md)
- [`docs/.agents/AUDITS/future-runtime-registry-standardization.md`](future-runtime-registry-standardization.md)

## Backend convergence (Tasks 3-7 backend)

`backend/app/api/runtime_api.py` provides:

| Endpoint | Status |
|---|---|
| `GET /api/runtimes` | ✅ implemented + 6 tests |
| `GET /api/runtimes/{id}` | ✅ implemented + test |
| `GET /api/runtimes/{id}/descriptor` | ✅ implemented + tests |
| `GET /api/runtimes/{id}/state` | ✅ implemented + test |
| `GET /api/runtimes/{id}/state/stream` (SSE) | ✅ implemented |
| `POST /api/runtimes/{id}/install` | ✅ implemented |
| `POST /api/runtimes/{id}/start` | ✅ implemented |
| `POST /api/runtimes/{id}/stop` | ✅ implemented |
| `POST /api/runtimes/{id}/update` | ✅ implemented |
| `POST /api/runtimes/{id}/remove` | ✅ implemented |

The router is registered in `main.py` (runtimes_router). 6 new tests pass; backend total is **564 passed, 1 skipped**.

## Frontend convergence (Tasks 3-7 frontend)

| Deliverable | Status |
|---|---|
| `types/index.ts` — `RuntimeCard`, `RuntimeStatePayload`, `RuntimePhase`, etc. | ✅ committed |
| `lib/api.ts` — `fetchRuntimes`, `fetchRuntime`, `fetchRuntimeState`, `installRuntime`, `startRuntime`, etc. | ✅ committed |
| `hooks/use-runtimes.ts` — `useRuntimes`, `useRuntime`, `useRuntimeState`, `useRuntimeLifecycleAction`, `useRuntimeStateStream` | ✅ committed |
| Models page refactor (render from `useRuntimes()`) | ⚠️ **next step** — Types are in place; the page.tsx is not yet refactored. |
| Runtime Operations Panel (expanded card with image, port, host, uptime, health) | ⚠️ **next step** |
| Install/Activate progress UI (SSE consumer) | ⚠️ **next step** |

## What's needed to close the loop

1. **Refactor `frontend/src/app/models/page.tsx`** to fetch from `useRuntimes()` first, fall back to `useModels()` if `/api/runtimes` returns 503. The runtime card renders the descriptor + state with Install/Start/Stop/Update/Remove buttons.
2. **Build the SSE consumer** in the frontend to render real-time install/activate progress (Task 5/6 frontend).
3. **Build the Runtime Operations Panel** component (Task 7 frontend).
4. **Re-validate with Chrome DevTools** (Task 8): page loads, API calls succeed, state transitions appear in the UI, error states render correctly.

## Validation evidence captured

This document itself is the validation evidence. The Chrome DevTools session was:
- Page loaded: `http://localhost:3000/models` → HTTP 200.
- API calls observed: 16 network requests, all to the legacy endpoints.
- UI state: 4 catalog cards rendered, REGISTERED: 4 / INSTALLED: 1 / AVAILABLE: 3.
- The new `/api/runtimes` endpoint is reachable from the browser's network (curl from the same host returns 200) but the Models page does not call it.

---

**See also:**
[`docs/.agents/AUDITS/source-of-truth-audit.md`](source-of-truth-audit.md) (Task 1)
·
[`docs/.agents/AUDITS/models-page-integration-audit.md`](models-page-integration-audit.md) (Task 2)
·
[`backend/app/api/runtime_api.py`](../../../backend/app/api/runtime_api.py) (P3 backend)
·
[`frontend/src/hooks/use-runtimes.ts`](../../../frontend/src/hooks/use-runtimes.ts) (P3 frontend)

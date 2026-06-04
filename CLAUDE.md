@frontend/AGENTS.md

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project direction — PeakVox (READ FIRST)

This project is evolving from a single-model OmniVoice frontend into **PeakVox**, a
model-agnostic **Universal Voice Runtime** + voice marketplace (think "OpenRouter for Voice +
Ollama for Voice"). The full architecture lives in **`docs/architecture/`** — **read
[`00-VISION.md`](docs/architecture/00-VISION.md) first**, then the
[`09-ROADMAP.md`](docs/architecture/09-ROADMAP.md) and the ADRs.

> **Implementation status (branch `feat/peakvox-phase-1`):** Phases 1–3 and 3.5–3.10 are
> **built and tested** — edition feature flags + schema-ready commercial tables + vendor seams
> (P1); first-class Model registry/metadata/lifecycle + HF installer (P2); the
> **Voice/VoiceVariant split** with backfill + dual-write (P3); the **Model Capability
> Contract** (`ModelCapabilities` superset + `app/services/capabilities.py`, P3.6); the
> **`ModelAdapter` contract + `PeakVoxRuntime`** single entry point (`app/services/model_adapter.py`,
> `app/services/runtime.py`, P3.5); **OmniVoice + OmniVoiceSinging adapters** (P3.7);
> **runtime exclusivity** — all generation routes through `PeakVoxRuntime` (P3.7.5);
> **edition-scoped model availability** ([ADR-0005](docs/architecture/adrs/0005-edition-scoped-model-availability.md));
> the **FishAudioAdapter** — first non-OmniVoice provider, CE-only (`app/services/model_adapters/fish_adapter.py`, P3.8);
> capability-driven UI gating (P3.9); and cross-provider **universal Voice asset validation**
> (one Voice ID → OmniVoice/Singing/Fish variants via one Runtime, P3.10).
>
> **Still planned (not built):** Auth, Billing, Creators, Marketplace, Cloud infra — their
> schema/seams exist (P1) but no implementation. The commercial tables are empty in CE. Don't
> assume a *commercial* PeakVox concept exists in code unless you've verified it.

### Binding architectural rules (do not violate)

These are normative; new code and designs must uphold them (see the ADRs):

1. **PeakVox is model-agnostic.** OmniVoice is just the **first model provider**. Never
   architect around a specific model. Adding a model must not change public APIs, Voice IDs,
   the Voice Library, marketplace, or developer integrations.
2. **Voice ≠ VoiceVariant ≠ Model** — three separate concepts ([ADR-0004](docs/architecture/adrs/0004-voice-variant-model-separation.md)).
   A **Voice** is a portable PeakVox asset (its `public_voice_id` is a **permanent** public
   contract). A **VoiceVariant** is a model-specific realization (embeddings/checkpoints/refs) —
   replaceable, **never exposed on the public API**. A **Model** is an interchangeable engine.
3. **The Runtime joins them** — `Voice + Model → VoiceVariant → inference`
   ([10-RUNTIME_ARCHITECTURE](docs/architecture/10-RUNTIME_ARCHITECTURE.md)). Models integrate
   via the `ModelAdapter` contract; nothing above that line imports a model implementation.
4. **Capabilities are declared, not inferred** ([ADR-0003](docs/architecture/adrs/0003-model-capability-contract.md)).
   Read `ModelCapabilities`; never branch on model id or model name to detect a feature.
5. **CE = infrastructure layer, Cloud = ecosystem layer.** Marketplace, creators, royalties,
   credits, payouts, and multi-tenant auth are **Cloud-only** but **schema-ready in CE** behind
   feature flags + deployment boundaries — never a forked schema. Auth/billing are swappable
   interfaces (Clerk/Stripe are the first adapters), like the existing identity seam.
6. **Migrations are additive + idempotent** (`app/core/migrations.py`, the SQLite-safe runner —
   **not** Alembic in CE). Add nullable columns + backfill; never destructive changes. Alembic
   arrives only at the Cloud Postgres cut-over.
7. **No pgvector** unless a real semantic voice-similarity feature justifies it (own ADR).
   Voice search/filter runs on the derived structured `characteristics`.

## Commands

### Docker (primary workflow)

```bash
docker compose up --build        # Start all services (first run downloads ~2.5 GB model)
docker compose up                # Start without rebuilding
docker compose down
```

### Backend (without Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
mkdir -p /tmp/omnivoice-data/{voices,uploads,generated,models}
DATA_DIR=/tmp/omnivoice-data uvicorn app.main:app --reload
```

### Frontend (without Docker)

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
npm run build
npm run lint
```

## Architecture

Two services: a **FastAPI backend** (`backend/`) and a **Next.js 15 frontend** (`frontend/`), communicating over HTTP. Persistent data (SQLite DB, voice audio files, generated audio, HuggingFace model cache) lives in a Docker volume mounted at `/data`.

### Backend (`backend/app/`)

| Module                          | Purpose                                                                                                                                                       |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `main.py`                       | App entrypoint — registers middleware, mounts `/audio` static files, fires model load as background task on startup                                           |
| `core/config.py`                | Pydantic settings (env-driven); all paths derive from `DATA_DIR`                                                                                              |
| `core/database.py`              | Async SQLAlchemy + SQLite via `aiosqlite`; `init_db()` creates tables on startup                                                                              |
| `models/db.py`                  | ORM models: `User`, `ApiKey`, `VoiceProfile`, `Model`, `GenerationJob` (PeakVox Phase 3 splits `VoiceProfile` → `Voice` + `VoiceVariant`)                      |
| `models/registry_types.py`      | Torch-free `ModelDescriptor` / `ModelCapabilities` (the model registry contract)                                                                              |
| `services/model_registry.py` + `model_catalog.py` + `model_providers/` | Persisted, multi-model registry: catalog seeding, runtime load/offload, provider plugins. `Model` is a first-class entity ([ADR-0002](docs/architecture/adrs/0002-model-as-first-class-entity.md)) |
| `services/runtime.py` | **`PeakVoxRuntime`** — the single, model-agnostic generation entry point: `Voice + Model → VoiceVariant` resolution, capability/tag validation, generation orchestration ([10-RUNTIME](docs/architecture/10-RUNTIME_ARCHITECTURE.md)) |
| `services/model_adapter.py` + `model_adapters/` | The **`ModelAdapter`** contract + OmniVoice/OmniVoiceSinging adapters. The Runtime talks only to adapters; never a model implementation ([ADR-0004](docs/architecture/adrs/0004-voice-variant-model-separation.md)) |
| `services/capabilities.py` | Centralized **Model Capability Contract** registry + validation ([ADR-0003](docs/architecture/adrs/0003-model-capability-contract.md)); capability-driven, no model-name branching |
| `services/voice_onboarding.py` + `voice_variant_repository.py` + `variant_resolution.py` | Voice/VoiceVariant split: `split_profile_row` mapping, dual-write/backfill, identity + variant lookups, generation-input resolution |
| `core/migrations.py`            | Idempotent, SQLite-safe startup migration runner (additive only; **not** Alembic)                                                                            |
| `schemas/`                      | Pydantic request/response schemas                                                                                                                             |
| `api/generation.py`             | `POST /generate` creates a `GenerationJob` row and fires `_process_job()` as an `asyncio.create_task`; job status is polled via `GET /jobs/{id}`              |
| `api/voices.py`                 | CRUD for voice profiles; audio stored at `/data/voices/{id}/voice.wav`                                                                                        |
| `services/omnivoice_service.py` | Singleton wrapping the OmniVoice model — loads once at startup, offloads to CPU after each generation to free VRAM, caches voice clone prompts per profile ID |
| `utils/audio.py`                | WAV save/load helpers                                                                                                                                         |

Generation is fire-and-forget: the HTTP response returns a `job_id` immediately and the frontend polls `GET /jobs/{id}` until `status` is `"completed"` or `"failed"`. MP3 conversion (via `ffmpeg`) is done on-demand at `GET /jobs/{id}/audio/mp3`.

### Frontend (`frontend/src/`)

| Path                          | Purpose                                                                                                             |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `lib/api.ts`                  | All HTTP calls to the backend; `NEXT_PUBLIC_API_URL` controls the base URL                                          |
| `store/use-store.ts`          | Zustand global store — holds selected voice profile, uploaded/recorded audio, active job state, generation settings |
| `hooks/use-generation.ts`     | React Query mutation that submits a job and polls until completion                                                  |
| `hooks/use-media-recorder.ts` | Browser MediaRecorder wrapper for in-browser voice recording                                                        |
| `types/index.ts`              | Shared TypeScript types (`VoiceProfile`, `JobStatus`, `GenerationRequest`, etc.)                                    |
| `app/page.tsx`                | Single-page layout composing all feature components                                                                 |

The frontend is a single page. Voice reference audio comes from one of three mutually exclusive sources tracked in Zustand: a saved `VoiceProfile`, an uploaded file, or a browser recording. Selecting one clears the other two.

### Key data flow

1. User picks/uploads/records reference audio → Zustand store
2. `GenerationForm` submits `POST /generate` with text + voice ref + generation params
3. `use-generation` hook polls `GET /jobs/{id}` every ~1s
4. On completion, `AudioPlayer` streams from `/audio/{filename}` (static mount) or `/jobs/{id}/audio/mp3`

### Generation parameters (defaults in Zustand store)

- `num_step`: 32 (diffusion steps)
- `guidance_scale`: 2.0
- `t_shift`: 0.1
- `denoise`: true
- `speed` / `duration`: null (auto)

## Removed files

| File | Reason |
|------|--------|
| `frontend/src/hooks/use-tts-generation.ts` | Extracted `useTtsGeneration` — unused, never imported. Generation logic lives inline in `GenerationPanel` + `useSubmitGeneration` in `use-generation.ts`. Removed 2026-06-03. |

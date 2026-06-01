# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

| Module | Purpose |
|--------|---------|
| `main.py` | App entrypoint — registers middleware, mounts `/audio` static files, fires model load as background task on startup |
| `core/config.py` | Pydantic settings (env-driven); all paths derive from `DATA_DIR` |
| `core/database.py` | Async SQLAlchemy + SQLite via `aiosqlite`; `init_db()` creates tables on startup |
| `models/db.py` | ORM models: `VoiceProfile`, `GenerationJob` |
| `schemas/` | Pydantic request/response schemas |
| `api/generation.py` | `POST /generate` creates a `GenerationJob` row and fires `_process_job()` as an `asyncio.create_task`; job status is polled via `GET /jobs/{id}` |
| `api/voices.py` | CRUD for voice profiles; audio stored at `/data/voices/{id}/voice.wav` |
| `services/omnivoice_service.py` | Singleton wrapping the OmniVoice model — loads once at startup, offloads to CPU after each generation to free VRAM, caches voice clone prompts per profile ID |
| `utils/audio.py` | WAV save/load helpers |

Generation is fire-and-forget: the HTTP response returns a `job_id` immediately and the frontend polls `GET /jobs/{id}` until `status` is `"completed"` or `"failed"`. MP3 conversion (via `ffmpeg`) is done on-demand at `GET /jobs/{id}/audio/mp3`.

### Frontend (`frontend/src/`)

| Path | Purpose |
|------|---------|
| `lib/api.ts` | All HTTP calls to the backend; `NEXT_PUBLIC_API_URL` controls the base URL |
| `store/use-store.ts` | Zustand global store — holds selected voice profile, uploaded/recorded audio, active job state, generation settings |
| `hooks/use-generation.ts` | React Query mutation that submits a job and polls until completion |
| `hooks/use-media-recorder.ts` | Browser MediaRecorder wrapper for in-browser voice recording |
| `types/index.ts` | Shared TypeScript types (`VoiceProfile`, `JobStatus`, `GenerationRequest`, etc.) |
| `app/page.tsx` | Single-page layout composing all feature components |

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

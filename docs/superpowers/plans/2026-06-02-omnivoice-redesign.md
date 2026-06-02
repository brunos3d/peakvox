# OmniVoice SaaS Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the OmniVoice prototype into a premium ElevenLabs-class SaaS interface (App Router shell + 5 pages + reusable design system) backed by MinIO object storage, preserving all existing functionality and generation behavior.

**Architecture:** Backend keeps SQLite for metadata and the OmniVoice inference path verbatim, but persists all audio in MinIO (download-to-temp for inference, upload result, proxy-stream for serving — preserving the `/audio/...` URL contract). Frontend becomes a Next.js App Router app with a shared shell (sidebar + context panel + persistent bottom player), driven by a retuned dark design system.

**Tech Stack:** FastAPI, SQLAlchemy(async)+aiosqlite, MinIO Python client, Next.js 15 App Router, Tailwind, shadcn/ui, Zustand, React Query.

**Spec:** `docs/superpowers/specs/2026-06-02-omnivoice-redesign-design.md`

---

## Phase 0 — Backend MinIO migration

### Task 0.1: Add MinIO service + config
**Files:** Modify `docker-compose.yml`, `backend/requirements.txt`, `backend/app/core/config.py`

- [ ] Add `minio` service to docker-compose (image `minio/minio:latest`, command `server /data --console-address ":9001"`, ports 9000/9001, env `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD`, named volume `minio_data`, healthcheck). Add `MINIO_*` env to `backend` service + `depends_on: [minio]`.
- [ ] Add `minio==7.2.*` to requirements.txt.
- [ ] Add to `Settings`: `MINIO_ENDPOINT="minio:9000"`, `MINIO_ACCESS_KEY="minioadmin"`, `MINIO_SECRET_KEY="minioadmin"`, `MINIO_BUCKET="omnivoice"`, `MINIO_SECURE=False`, `TMP_DIR=Path("/data/tmp")`. Add `TMP_DIR` to `create_dirs()`.
- [ ] Commit.

### Task 0.2: Storage service
**Files:** Create `backend/app/services/storage.py`

Interface (sync MinIO client wrapped via `asyncio.to_thread`):
```python
class StorageService:
    def ensure_bucket(self) -> None
    async def put_file(self, key: str, local_path: Path, content_type: str) -> None
    async def put_bytes(self, key: str, data: bytes, content_type: str) -> None
    async def download_to_temp(self, key: str, suffix: str = "") -> Path
    async def open_stream(self, key: str) -> tuple[Iterator[bytes], int, str]  # (chunks, size, content_type)
    async def exists(self, key: str) -> bool
    async def delete(self, key: str) -> None
    async def delete_prefix(self, prefix: str) -> None
storage = StorageService()
```
- [ ] Implement using `Minio(endpoint, access_key, secret_key, secure)`. `ensure_bucket` creates bucket if missing. `open_stream` uses `client.get_object` + `stat_object` for size/content-type; yields chunks; caller closes.
- [ ] Commit.

### Task 0.3: Wire storage into startup
**Files:** Modify `backend/app/main.py`
- [ ] In lifespan after `create_dirs()`: `storage.ensure_bucket()`, then run migration (Task 0.7) before model load.
- [ ] Replace `/audio` static mount with a streaming route (Task 0.6 provides it) — remove `app.mount("/audio", StaticFiles(...))`.
- [ ] Commit.

### Task 0.4: Voice CRUD → MinIO
**Files:** Modify `backend/app/api/voices.py`
- [ ] `create_voice`/`update_voice`: keep `process_audio` writing to a temp dir under `settings.TMP_DIR`, then `storage.put_file("voices/{id}/reference.wav", ...)` and `storage.put_bytes("voices/{id}/metadata.json", ...)`. Remove permanent `VOICES_DIR` writes.
- [ ] `get_voice_audio`: stream `voices/{id}/reference.wav` via `StreamingResponse`.
- [ ] `delete_voice`: `storage.delete_prefix("voices/{id}/")` instead of `shutil.rmtree`.
- [ ] `_resolve_audio_path` replaced by object-key existence checks (`reference.wav` then legacy `voice.wav`).
- [ ] Commit.

### Task 0.5: Generation path → MinIO
**Files:** Modify `backend/app/api/generation.py`
- [ ] `create_generation_job`: set `output_path` to object key `generated/{hex}.wav` (not fs path). For voice ref, store the voice id; resolution happens in `_process_job`.
- [ ] `_process_job`: download ref object (if voice) to temp via `storage.download_to_temp`; pass temp path to `generate_async` writing to a temp WAV; on success `storage.put_file(job.output_path, temp_wav, "audio/wav")`.
- [ ] `get_job_audio`/`get_job_audio_mp3`: stream from MinIO. MP3: if `generated/{stem}.mp3` not `exists`, download wav→temp, ffmpeg→temp mp3, upload, then stream.
- [ ] Commit.

### Task 0.6: Audio serving route
**Files:** Modify `backend/app/api/generation.py` (or new `app/api/media.py`)
- [ ] Add `GET /audio/{filename}` → stream `generated/{filename}` with range-request support (`Accept-Ranges: bytes`, honor `Range` header) so the player can seek. Keeps `audio_url="/audio/{filename}"` contract.
- [ ] Commit.

### Task 0.7: Startup migration
**Files:** Create `backend/app/services/migration.py`; call from `main.py`
- [ ] Idempotent: for each existing `VOICES_DIR/*/` and `GENERATED_DIR/*` file, upload to matching key if not `exists`; rewrite DB `GenerationJob.output_path`/`ref_audio_path` and any `/data/...` values to object keys. Safe no-op when dirs empty.
- [ ] Commit.

### Task 0.8: History endpoints (additive)
**Files:** Modify `backend/app/api/generation.py`, `backend/app/schemas/job.py`
- [ ] `GET /jobs?limit=50&offset=0&status=` → ordered `created_at desc`, returns list of `JobResponse` (audio_url for completed).
- [ ] `DELETE /jobs/{id}` → delete row + `storage.delete("generated/{stem}.wav")` + `.mp3`.
- [ ] Verify: `docker compose up --build`, create voice, generate, GET /jobs, play, DELETE. Commit.

---

## Phase 1 — Design tokens
### Task 1.1: Retune globals.css
**Files:** Modify `frontend/src/app/globals.css`
- [ ] Replace `.dark` neutrals with near-neutral near-black; add `--surface`, `--surface-2`, `--success/--warning/--error/--info` (+ foregrounds); `--radius: 0.75rem`. Keep purple `--primary` as accent.
- [ ] Add type-scale utility classes (`.text-page-title`, `.text-section-title`, `.text-card-title`, `.text-caption`).
- [ ] Map new tokens in `tailwind.config` (surface, status colors).
- [ ] Commit.

---

## Phase 2 — App shell
### Task 2.1: Global player + nav state in store
**Files:** Modify `frontend/src/store/use-store.ts`
- [ ] Add `currentAudio: {url, duration, jobId, text, voiceName} | null`, `setCurrentAudio`. Move active-job desync guards here.
- [ ] Commit.

### Task 2.2: Shell components
**Files:** Create `frontend/src/components/shell/AppSidebar.tsx`, `PageLayout.tsx`, `PageHeader.tsx`, `BottomPlayer.tsx`, `StatusRow.tsx`. Add shadcn `sheet`, `tooltip`.
- [ ] AppSidebar: logo + nav (TTS/Library/Clone/History/Settings, active state via `usePathname`) + footer StatusRows (System/Model/GPU). Mobile = Sheet.
- [ ] PageLayout: grid (content + optional `contextPanel`). PageHeader: title/description/actions. BottomPlayer: store-driven AudioPlayer.
- [ ] Commit.

### Task 2.3: Root layout + routes
**Files:** Modify `frontend/src/app/layout.tsx`; create `frontend/src/app/{(tts page stays at) page.tsx, voices/page.tsx, clone/page.tsx, history/page.tsx, settings/page.tsx}`
- [ ] layout.tsx renders Providers + shell frame (Sidebar + children + BottomPlayer + ModelLoadingScreen gate moved into a client wrapper).
- [ ] Stub each route page rendering PageHeader. Commit.

---

## Phase 3 — Reusable primitives
### Task 3.1: AudioPlayer upgrade
**Files:** Modify `frontend/src/components/AudioPlayer.tsx`
- [ ] Make a reusable `<AudioPlayer src duration title onRegenerate? downloadUrl? compact? />` wrapping WaveformDisplay with play/pause/seek/duration/download. Commit.

### Task 3.2: Voice components
**Files:** Create `frontend/src/components/voice/VoiceCard.tsx`, `VoiceGrid.tsx`, `VoiceSelector.tsx`, `VoiceDetailsDrawer.tsx`
- [ ] VoiceCard (name/language/duration/preview/edit/delete, badges). Grid responsive. Selector card. Drawer = Sheet with preview/transcript/metadata/defaults. Commit.

### Task 3.3: Generation + misc primitives
**Files:** Create `frontend/src/components/generation/GenerationPanel.tsx`, `ModelSelector.tsx`, `QuickPrompts.tsx`; `frontend/src/components/common/{EmptyState,FilterBar}.tsx`
- [ ] GenerationPanel groups existing GenerationSettings controls + GPU. Commit.

---

## Phase 4 — Text to Speech page
### Task 4.1
**Files:** Modify `frontend/src/app/page.tsx`; reuse GenerationForm logic
- [ ] Center canvas textarea + QuickPrompts; contextPanel = VoiceSelector + ModelSelector + GenerationPanel + Output Format. Submit via existing hooks; on completion set `currentAudio` (BottomPlayer shows it). Preserve language + instruct controls. Commit + verify generate flow.

---

## Phase 5 — Voice Library page
### Task 5.1
**Files:** Modify `frontend/src/app/voices/page.tsx`
- [ ] PageHeader (search + FilterBar + Create Voice→/clone). VoiceGrid; single-click select, double-click → VoiceDetailsDrawer. contextPanel = selected voice metadata/preview/actions. Commit.

---

## Phase 6 — Voice Clone wizard
### Task 6.1
**Files:** Create `frontend/src/components/wizard/VoiceWizard.tsx` + steps; modify `frontend/src/app/clone/page.tsx`
- [ ] 6 steps (Source/Validation/Crop/Info/Defaults/Review) reusing VoiceProfileAudioInput, AudioCropEditor, GenerationSettingsFields, audio-duration. Finish → createVoice → /voices. Commit + verify clone.

---

## Phase 7 — History page
### Task 7.1
**Files:** Add `fetchJobs`/`deleteJob` to `frontend/src/lib/api.ts`; create `frontend/src/components/history/{HistoryList,HistoryItem}.tsx`; modify `frontend/src/app/history/page.tsx`; add types
- [ ] List from GET /jobs; HistoryItem (text/voice/timestamp/duration + play/download/regenerate/delete). Regenerate prefills TTS. contextPanel = filters. Commit + verify.

---

## Phase 8 — Settings + responsive polish
### Task 8.1
**Files:** Modify `frontend/src/app/settings/page.tsx`; create `frontend/src/components/settings/SettingsPanel.tsx`
- [ ] Device/GPU toggle (existing API), default output format (client pref via store/localStorage), about. Commit.

### Task 8.2: Responsive + QA
- [ ] Sidebar collapse (tablet) / Sheet (mobile); context panels become drawers/bottom-sheets; condensed BottomPlayer. `npm run build` + `npm run lint` clean. Full Docker E2E: clone → generate → play/seek → history → delete. Commit.

---

## Self-review notes
- Spec coverage: §2 routing→P2/P3; §3 tokens→P1; §4 shell→P2; §5 pages→P4–P8; §6 components→P3; §7 MinIO→P0; §8 responsive→P8.2; §9 preserved behavior→P0 keeps inference path + 409 guard + voice defaults.
- API contract: `JobResponse` field names unchanged; `audio_url` shape unchanged; only `GET /jobs` + `DELETE /jobs/{id}` added.
- Risk: serving range support (Task 0.6) required for seek through proxy.

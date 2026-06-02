# OmniVoice — Production-Grade SaaS Redesign

**Date:** 2026-06-02
**Status:** Approved (design); pending implementation plan
**Scope:** Full UX + visual redesign of the frontend, plus a backend migration to MinIO object storage and two additive job endpoints.

---

## 1. Goals & Principles

Evolve the working prototype into a premium AI SaaS interface in the spirit of ElevenLabs / Linear / Vercel / Notion / Perplexity: clean, spacious, scalable, strong hierarchy, minimal visual noise, fast navigation.

**Hard constraints**

- Do **not** remove existing functionality.
- Do **not** change generation behavior or generation quality (the ML inference path is preserved verbatim).
- Preserve existing **public API response shapes and audio URL contracts**. The only API changes are additive (two new job endpoints) and a storage-backing swap that is invisible to clients.
- Keep Next.js, Tailwind, shadcn/ui. Dark theme only.

**Decisions locked during brainstorming**

- Routing: real Next.js App Router URL routes (not in-memory view switching).
- History data: backed by the server via a full **MinIO object-storage migration** + new list/delete job endpoints.
- Delivery: full redesign as one phased plan.
- `Voice Design` / `Voice Remix`: **omitted** from the sidebar for now.
- Audio serving: backend **proxy-streams** from MinIO, preserving the existing `/audio/...` URL contract (chosen over presigned URLs to avoid Docker hostname/CORS issues in local deployment).

---

## 2. Architecture & Routing

Replace the single client page with App Router routes under one shared shell:

| Route | Page |
|-------|------|
| `/` | Text to Speech |
| `/voices` | Voice Library |
| `/clone` | Voice Clone (6-step wizard) |
| `/history` | Generation History |
| `/settings` | Settings |

A root layout renders: **AppSidebar (left) + page content (center) + per-page context panel (right) + persistent bottom player**.

**Global state move:** active-job state and the "current output audio" (URL + duration + source job id) move from `page.tsx` local `useState` into the Zustand store, so the bottom player persists across route changes and continues polling regardless of which page is shown. The existing job-desync guards (matching `jobData.id === activeJobId`, the 3s clear timer keyed on `completedJobId`) are preserved in their new home.

---

## 3. Visual System (`globals.css`, dark-only)

The app already forces `class="dark"` on `<html>`; keep that.

- **Neutral palette.** Replace blue-tinted dark neutrals (`222 84% 4.9%`) with near-neutral near-black. Introduce a layered surface scale:
  - `--background` — app canvas (darkest)
  - `--surface` — cards
  - `--surface-2` — popovers / elevated / drawers
  - `--border` — hairline borders
- **Purple = accent only.** `--primary` stays purple, used for active nav, focus rings, primary buttons, waveform played-portion. Never a fill background.
- **Status tokens** defined once and reused everywhere: `--success`, `--warning`, `--error`, `--info` (each with a foreground/subtle variant as needed). Drives validation messages, job status, GPU/model dots.
- `--radius` → `0.75rem`; cards use `rounded-xl`. Shadows very subtle.
- **Type scale** standardized (utility classes or a small `Text`/heading convention): Page Title, Section Title, Card Title, Body, Caption — consistent sizes/weights/line-heights.
- **Spacing** generous: `gap-6/8/10`, roomy page padding.

CSS custom properties remain space-separated HSL components (e.g. `262.1 83.3% 57.8%`) consumed via `hsl(var(--x))`, consistent with current usage. Note for canvas (waveform): values must be wrapped with `hsl()` when read via `getComputedStyle` (this fix already exists in `WaveformDisplay.tsx`).

---

## 4. App Shell Components

- **`AppSidebar`** — logo; nav (Text to Speech, Voice Library, Voice Clone, History, Settings) with active-route styling; footer with **System / Model / GPU** status rows. Reuses `useModelStatus` and a device-settings query. Collapsible icon-rail on tablet; shadcn `sheet` drawer on mobile.
- **`PageLayout`** — grid wrapper providing the center content column and an optional right context-panel slot; pages pass `contextPanel={...}`.
- **`PageHeader`** — page title + optional description + action slot (e.g. Create Voice button).
- **`BottomPlayer`** — persistent player wired to global store state; visible across all routes when there is current/active output.
- **`StatusRow`** — sidebar footer status line (label + colored dot + value), status-token driven.

New shadcn primitives to add: `sheet` (drawer / mobile nav), `tooltip`. (Existing: accordion, badge, button, card, dialog, dropdown-menu, input, label, progress, scroll-area, select, separator, skeleton, slider, switch, tabs, textarea.)

---

## 5. Pages

### 5.1 Text to Speech (`/`)
- **Center:** large writing canvas — a tall textarea occupying most of the screen, placeholder `"Type or paste text to generate speech..."`. Below it, **QuickPrompts** chips: Narrate a story, Explain a concept, Podcast introduction, Advertisement, News report, YouTube narration (clicking inserts starter text).
- **Right context panel:** `VoiceSelector` (current voice card + change), `ModelSelector`, `GenerationPanel` (grouped controls: Voice / Model / Speed / Guidance / Steps / Denoise / GPU), Output Format selector.
- **Bottom player:** play/pause/seek/duration/download/regenerate.
- **Behavior preserved:** submission via `useSubmitGeneration`, polling via `useJobStatus` (1s while pending/processing). Generation requires text + a selected voice source, identical to today. Language and Style Prompt (`instruct`) controls retained.

### 5.2 Voice Library (`/voices`)
- **`PageHeader`**: title "Voice Library", search box, filter chips (Language, Duration, Presets, Custom, Recently Used), **Create Voice** button → `/clone`.
- **`VoiceGrid`** of **`VoiceCard`**: name, language, duration, preview/edit/delete actions; optional tags, preset badge, last-used.
- **Interaction:** single-click selects the voice (sets `store.selectedProfile`); double-click opens **`VoiceDetailsDrawer`** (slide-over: audio preview, transcript, metadata, generation defaults, usage stats).
- Filtering/search is client-side over the already-loaded `voices` list.

### 5.3 Voice Clone (`/clone`) — `VoiceWizard`
Six steps:
1. **Source** — large dropzone (Upload) or Record; accepts WAV/MP3/OGG/M4A/FLAC/OPUS/MP4 (reuses `VoiceProfileAudioInput` / `VoiceRecorder`).
2. **Validation** — duration, waveform, quality indicators; warnings (too noisy / too short / too long) using existing `audio-duration` util and backend limits (`MAX_REFERENCE_DURATION` = 15s).
3. **Crop** — interactive waveform editor when audio exceeds limits (reuses `AudioCropEditor`).
4. **Info** — name, language, transcript, tags, description.
5. **Generation Defaults** — collapsible; configures Inference Steps, Guidance Scale, Speed, Duration, Time Shift, Denoise, GPU (reuses `GenerationSettingsFields`).
6. **Review** — summary + Create Voice → `createVoice` (multipart, unchanged contract) → navigate to `/voices`.

Wizard state is local to the route; on completion it calls the existing `POST /voices` form payload (including `crop_start`/`crop_end` and `generation_defaults` JSON) exactly as the current modal does.

### 5.4 History (`/history`)
- **`HistoryList` / `HistoryItem`** from new `GET /jobs`: generated text (truncated), voice used, timestamp, duration.
- **Actions:** Play (bottom player), Download (existing `/jobs/{id}/audio[/mp3]`), Regenerate (prefill TTS: set store text + settings + voice, navigate to `/`), Delete (new `DELETE /jobs/{id}`).
- **Right panel:** filters (status, voice) + playback.
- List uses pagination params from `GET /jobs`.

### 5.5 Settings (`/settings`)
- GPU/device toggle (existing `GET/PATCH /settings/device`), default output format preference (client-side), about/system info. Reuses a `SettingsPanel`.

---

## 6. Reusable Components

`AppSidebar`, `PageLayout`, `PageHeader`, `AudioPlayer` (upgraded; wraps existing `WaveformDisplay` for waveform + play/pause/seek/duration/download), `BottomPlayer`, `VoiceCard`, `VoiceGrid`, `VoiceSelector`, `GenerationPanel`, `ModelSelector`, `VoiceWizard` (+ per-step components), `VoiceDetailsDrawer`, `HistoryList`, `HistoryItem`, `SettingsPanel`, `QuickPrompts`, `FilterBar`, `EmptyState`, `StatusRow`.

Principle: build reusable primitives, not page-specific one-offs. `AudioPlayer` is the single audio surface used by TTS output, bottom player, voice previews, drawer, and history.

---

## 7. Backend — MinIO Object Storage Migration

### 7.1 Infrastructure
- Add a **`minio`** service to `docker-compose.yml`: image `minio/minio`, API + console ports, a named volume, root credentials via env. Backend gains `MINIO_*` env vars and `depends_on: [minio]`.
- Add the **`minio`** Python client to `backend/requirements.txt`.

### 7.2 Storage service (`app/services/storage.py`)
A thin abstraction over the MinIO client (sync client invoked via `run_in_executor` to stay async-friendly), exposing: `put_object`, `get_object_stream`, `download_to_temp`, `delete_object`, `object_exists`. Bucket auto-created on startup (`ensure_bucket`).

**Key layout** (single bucket):
- `voices/{id}/reference.wav`
- `voices/{id}/metadata.json`
- `uploads/{name}`
- `generated/{name}.wav`
- `generated/{name}.mp3`

### 7.3 Config
`app/core/config.py` gains: `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`, `MINIO_SECURE`. A local scratch/temp dir for inference I/O (e.g. `/data/tmp`, kept on the existing volume).

### 7.4 Generation path (ML code untouched)
`omnivoice_service.py` keeps its local-path signature — **no change to inference**. `_process_job` orchestrates storage around it:
1. Resolve reference audio: if the voice's `reference.wav` object exists, `download_to_temp` → local path; ad-hoc uploads likewise.
2. Run `generate_async` writing to a local temp WAV (unchanged).
3. `put_object` the result to `generated/{name}.wav`; set `job.output_path` to the **object key**.
4. MP3 conversion endpoint: download WAV temp → ffmpeg → upload `generated/{name}.mp3` → stream (cache by checking `object_exists` first).

The voice-prompt cache (keyed by `voice_id`) is unaffected — temp paths vary but cache hits are by id.

### 7.5 Voice creation/update path
`process_audio` writes `reference.wav` + `metadata.json` to a temp dir, then `put_object` uploads both under `voices/{id}/`. Delete removes all `voices/{id}/*` objects.

### 7.6 Serving (contract preserved)
Replace the `/audio` static mount and `FileResponse` usages with `StreamingResponse` sourced from MinIO, keeping identical routes/URLs:
- `GET /audio/{filename}` (replaces static mount) → stream `generated/{filename}`.
- `GET /voices/{id}/audio` → stream `voices/{id}/reference.wav`.
- `GET /jobs/{id}/audio` and `GET /jobs/{id}/audio/mp3` → stream from MinIO.

`JobResponse.audio_url` keeps returning `/audio/{filename}`; the frontend needs no change to audio URL handling.

### 7.7 New endpoints (additive only)
- `GET /jobs?limit=&offset=&status=` → list of jobs (newest first) for History. Returns existing `JobResponse` shape (or a lighter list schema with the same field names) + `audio_url` for completed jobs.
- `DELETE /jobs/{id}` → delete the DB row and its `generated/*` objects (wav + mp3 if present).

### 7.8 Data migration (startup, one-time, idempotent)
On startup, scan existing `/data/voices` and `/data/generated`; upload any present files to MinIO under the key layout, and rewrite stored paths in DB rows (`VoiceProfile.audio_filename` semantics + `GenerationJob.output_path` / `ref_audio_path`) from `/data/...` filesystem paths to object keys. Legacy `/data/...` values are handled for back-compat if encountered. SQLite remains the metadata store.

---

## 8. Responsive

- **Desktop ≥1280px:** sidebar + content + context panel + bottom player.
- **Tablet 768–1279px:** collapsible icon-rail sidebar; context panel becomes a toggleable drawer.
- **Mobile <768px:** `sheet` drawer nav; context panel as a bottom sheet; condensed bottom player. Everything remains usable.

---

## 9. Non-goals / Explicitly Preserved

**Preserved:** all generation parameters and the polling flow; the voice generation-defaults feature; client-side audio-duration detection; MP3 on-demand conversion; GPU offload-after-generation behavior; the single-busy-GPU 409 guard.

**Non-goals:** Voice Design / Voice Remix features, authentication / multi-user, billing, light theme.

---

## 10. Implementation Order (one phased plan)

0. **Backend MinIO** — storage service, config, generation/voice path rewiring, streaming serving, 2 new endpoints, startup migration.
1. **Design tokens** — `globals.css` palette/surfaces/status/type/radius retune.
2. **App shell** — `AppSidebar`, `PageLayout`, context-panel slot, `BottomPlayer`, route scaffold, global player state in store.
3. **Reusable primitives** — upgraded `AudioPlayer`, `VoiceCard`/`VoiceGrid`, `GenerationPanel`, `VoiceSelector`, `ModelSelector`, `StatusRow`, `EmptyState`, `FilterBar`, shadcn `sheet`/`tooltip`.
4. **Text to Speech page**.
5. **Voice Library page** + `VoiceDetailsDrawer`.
6. **Voice Clone wizard**.
7. **History page** — wire to new endpoints.
8. **Settings page** + responsive polish + QA (Docker up, generate, clone, history, delete).

---

## 11. Risks / Watch-items

- **MinIO migration is the riskiest piece** — generation, voice CRUD, and serving all depend on it. Build and verify Phase 0 end-to-end (create voice → generate → play → history → delete) before frontend work relies on it.
- Existing volume data: migration must be idempotent and safe to run when the bucket is already populated.
- Streaming responses must set correct `Content-Type` and support range requests if the player needs seeking (verify audio seek works through the proxy; add `Accept-Ranges`/range handling if required).
- Keep `JobResponse` field names stable so the frontend `types/index.ts` contracts hold.

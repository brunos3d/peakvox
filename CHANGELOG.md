# Changelog

All notable changes to **PeakVox** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **XTTS v2 — fourth first-class runtime** (Task 30, [ADR-0021](docs/.agents/DECISIONS/adr-0021-xtts-v2-integration.md)):
  - Integrated **Coqui XTTS v2** (`coqui/XTTS-v2`) — multilingual (17 languages) zero-shot voice
    cloning — as a native runtime with full parity to OmniVoice, Kokoro, and F5-TTS, **through the
    existing contracts with no model-specific exception**.
  - **Runtime Registry entry** `runtime-registry/xtts-v2/`: descriptor, `peakvox/xtts-runtime`
    FastAPI service (5-endpoint Runtime Service Contract), Dockerfile, requirements, README, and
    `variants/base.json` (the bundled checkpoint as the explicit, default, `verified` base variant).
    Auto-discovered by the file-based registry — no central registration.
  - **`XTTSAdapter`** (`backend/app/services/model_adapters/xtts_adapter.py`): `reference_sample`
    realization, generation routed exclusively via `HTTPTransport` (no in-process inference),
    `SOURCE_ASSET` build strategy — a sibling of `F5TTSAdapter`. Wired in `model_wiring.py`
    (`provider="xtts"`).
  - **Catalog model** `xtts-v2` (`model_catalog.py`): capabilities declared (ADR-0003) —
    `tts`, `voice_cloning`, `multilingual`, `reference_audio`, `voice_optional` — identical to F5,
    so the capability-driven Models page and Public API surface it with **zero frontend changes**.
  - **The one deliberate divergence from F5-TTS:** XTTS is **CPU-capable**. The descriptor declares
    `gpu: "optional"` and `server.py` falls back to CPU instead of raising, so **Settings → Use GPU
    (CUDA)** is an authoritative GPU↔CPU switch via the existing Docker driver. `/v1/metadata`
    reports the live `substrate`. No setting is silently ignored.
  - **Licensing:** XTTS weights are under the Coqui Public Model License (CPML, non-commercial) —
    CE-disabled by default, enabled per deployment after license review (same posture as F5-TTS).
  - **Runtime Variants:** XTTS is the strongest validation target for the checkpoint ecosystem
    (ADR-0018/0019) — fine-tuned / community / imported Hugging Face checkpoints attach as siblings
    of `base` with no new image and no new model id.
  - **Tests:** `backend/tests/test_xtts_adapter.py` (11) + `runtime-registry/xtts-v2/tests/` (48:
    server contract, CPU fallback, voice-optional, concurrency, descriptor, base variant). Full
    backend suite green (765 passed). Discovery + provider-validation reports under
    `docs/.agents/VALIDATION/`.

### Changed

- **Public documentation, positioning & community governance overhaul** (Task 28):
  - Repositioned all public-facing docs from "OmniVoice App" (a single-model frontend) to
    **PeakVox**, a **Universal Voice Runtime** — voice-first, model-agnostic, Community-Edition
    first. OmniVoice is now documented as the first *provider*, alongside F5-TTS and Kokoro.
  - **`README.md`** rewritten as the canonical entry point: what PeakVox is and why, the
    Voice/Variant/Model separation, Runtime Registry and Runtime Variants, the architecture
    diagram, Community-Edition-first positioning, factual Cloud vision, and a FAQ. Fixed broken
    links that pointed at removed `docs/ARCHITECTURE.md` / `ROADMAP.md` / `FAQ.md` /
    `COMMERCIAL_MODEL.md` (now under `docs/.agents/`).
  - **`CONTRIBUTING.md`** rewritten: ADR-driven decision process, how the Runtime Registry and
    Runtime Variants evolve, how to propose a new runtime / model family, and model-agnostic
    coding standards.
  - **`SECURITY.md`** updated for the runtime threat surface: Docker-socket exposure, runtime/
    weight downloads (Hugging Face), and community runtime-variant imports + trust tiers.
  - **`VOICE_USAGE_POLICY.md`**, **`CODE_OF_CONDUCT.md`**, **`LICENSE`**, **`NOTICE`** rebranded
    to PeakVox; legal meaning preserved, upstream-runtime carve-out generalized beyond OmniVoice.
  - Added **`PHILOSOPHY.md`** (open-source philosophy), **`GOVERNANCE.md`** (ADR-driven, build-in
    -public governance), and **`COMMUNITY_VALUES.md`** (community values + exploration-only
    contributor-recognition section, no financial promises).
  - Fixed a dead `docs/superpowers/specs/` reference (specs now live under `docs/.agents/SPECS/`).

### Added

- **Kokoro preset voice adapter + ProviderVoice domain** (Phase 1):
  - `ProviderVoice` frozen dataclass — ephemeral, in-memory preset voice identity (no DB, no assets, no variants).
  - `ProviderVoiceCatalog` runtime-checkable protocol — optional interface on `ModelAdapter` for providers with built-in presets.
  - `ProviderVoiceRegistry` — O(1) dict-based lifecycle (register, refresh, reload, remove, remove_provider, search).
  - `KokoroAdapter` — implements `ModelAdapter` + `ProviderVoiceCatalog` with 54 presets across 9 languages, EPHEMERAL `voice_pack` realization, lazy `kokoro` import, WAV generation at 24kHz.
  - Runtime two-tier `generate()` — registry-first (O(1) dict) → persisted Voice DB fallback; no string prefix detection.
  - Auto-population of `ProviderVoiceRegistry` at adapter registration time for `ProviderVoiceCatalog` adapters.
  - Deterministic voice IDs: `voice_{provider}_{external_id}` (e.g. `voice_kokoro_af_heart`).
- **Phase 2 — Voice Platform** (SaaS-ready foundation):
  - **Stable Voice IDs** (`public_voice_id`, e.g. `voice_8JXQ29K4L3`) — permanent external identifier for every voice; minimal local-owner `users` model; `owner_id` across resources; derived voice `characteristics` and richer metadata; idempotent startup migrations.
  - **646-language registry** generated from OmniVoice's language list, with a searchable combobox; language stored as OmniVoice id + display name.
  - **Voice Library redesign** — My/Community/Preset/Recently-Used tabs, server-side pagination, instant search, advanced filters (language/gender/age/accent), favorites, Copy-Voice-ID, and an expanded details panel.
  - **API platform** — hashed API keys (`ov_live_…`, sha256, shown once), versioned public REST API `/api/v1` (list/get/create/delete voices + text-to-speech with stream or download-URL), in-app API dashboard (Overview / API Keys / Voice API / Usage), and Use-in-API code examples (cURL/JS/Python).
  - **TTS auto-configuration** — selecting a voice applies its language, preset, and voice design, consistent with the API.
  - **SaaS architecture preparation** — identity and rate-limit seams, `EDITION` flag; no authentication/billing implemented.
  - **Docs**: `API`, `VOICE_MODEL`, `DATA_MODEL`, `LANGUAGES`, `SAAS_ARCHITECTURE`, `DEVELOPER`, and design specs (now under `docs/.agents/SPECS/`).
- Project governance and documentation suite: `README`, `LICENSE` (PeakVox Community License, based on Elastic License 2.0), `NOTICE`, `CONTRIBUTING`, `CODE_OF_CONDUCT`, `SECURITY`, `VOICE_USAGE_POLICY`, and `docs/` (`ARCHITECTURE`, `ROADMAP`, `FAQ`, `COMMERCIAL_MODEL`).

## [0.1.0] - 2026-06-02

Initial public preview of PeakVox — a self-hosted Voice Cloning, Text-to-Speech, and Voice Design platform built on [OmniVoice](https://github.com/k2-fsa/OmniVoice).

### Added

- **Text-to-Speech** workspace with fine-grained generation controls (`num_step`, `guidance_scale`, `t_shift`, `denoise`, `speed`/`duration`).
- **Voice Cloning** from uploaded files or in-browser recording, with per-profile clone-prompt caching.
- **Voice Design Builder** — controlled-vocabulary attribute editor (Gender, Age, Pitch, Style, English Accent, Chinese Dialect) with searchable picker and one-attribute-per-category enforcement.
- **Voice Library** — create, edit, search, and delete saved voice profiles, each with optional default generation settings.
- **Generation History** — list, replay, and delete past generation jobs.
- **Settings** page with persisted output-format preference (`localStorage`).
- **Language-aware Quick Prompts** with smooth visibility transitions and undo-preserving insertion.
- **Waveform player** (wavesurfer.js) with interactive timeline.
- **Multi-page SaaS-style UI** (Next.js 15 App Router, React 19, Tailwind, shadcn/ui) across TTS, Clone, Library, History, and Settings routes.
- **Async generation API** (FastAPI) — fire-and-forget jobs polled via `GET /jobs/{id}`; on-demand MP3 transcoding via `ffmpeg`.
- **MinIO** S3-compatible object storage for reference and generated audio.
- **Docker Compose** deployment with GPU reservation, MinIO healthcheck dependency, and persistent volumes.
- **600+ language** support via OmniVoice (auto-detect or manual selection).

### Notes

- Persistence defaults to **SQLite**; the data layer is **PostgreSQL-ready** for future multi-user deployments (see [ROADMAP](docs/.agents/ROADMAP/ROADMAP.md)).
- The Community Edition ships without built-in user authentication — see [SECURITY.md](SECURITY.md) before any internet-facing deployment.

[Unreleased]: https://github.com/brunos3d/omnivoice-app/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/brunos3d/omnivoice-app/releases/tag/v0.1.0

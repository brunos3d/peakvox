# Changelog

All notable changes to **OmniVoice App** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Project governance and documentation suite: `README`, `LICENSE` (OmniVoice App Community License, based on Elastic License 2.0), `NOTICE`, `CONTRIBUTING`, `CODE_OF_CONDUCT`, `SECURITY`, `VOICE_USAGE_POLICY`, and `docs/` (`ARCHITECTURE`, `ROADMAP`, `FAQ`, `COMMERCIAL_MODEL`).

## [0.1.0] - 2026-06-02

Initial public preview of OmniVoice App — a self-hosted Voice Cloning, Text-to-Speech, and Voice Design platform built on [OmniVoice](https://github.com/k2-fsa/OmniVoice).

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
- Persistence defaults to **SQLite**; the data layer is **PostgreSQL-ready** for future multi-user deployments (see [ROADMAP](docs/ROADMAP.md)).
- The Community Edition ships without built-in user authentication — see [SECURITY.md](SECURITY.md) before any internet-facing deployment.

[Unreleased]: https://github.com/brunos3d/omnivoice-app/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/brunos3d/omnivoice-app/releases/tag/v0.1.0

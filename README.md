# OmniVoice Platform

A self-hosted Voice Cloning and Text-to-Speech (TTS) web application powered by [OmniVoice](https://github.com/k2-fsa/OmniVoice).

## Features

- **Text-to-Speech** — Generate natural speech from text using OmniVoice
- **Voice Cloning** — Clone any voice from a reference audio recording
- **Voice Library** — Save, manage, and reuse voice profiles
- **Browser Recording** — Record voice samples directly from your browser
- **Voice Design** — Use style prompts (e.g., "calm and professional", "energetic")
- **600+ Languages** — Support for auto-detection or manual language selection
- **Dark Modern UI** — Inspired by ElevenLabs and modern AI audio tools
- **Fully Dockerized** — Run with a single `docker compose up --build`
- **Self-Hosted** — Your data stays on your infrastructure

## Tech Stack

| Layer     | Technology                                      |
| --------- | ----------------------------------------------- |
| Frontend  | Next.js 15, TypeScript, Tailwind CSS, shadcn/ui |
| State     | React Query (TanStack), Zustand                 |
| Backend   | FastAPI, Python 3.11+, SQLAlchemy, Pydantic     |
| AI Engine | OmniVoice (k2-fsa/OmniVoice)                    |
| Storage   | SQLite (default), PostgreSQL-ready              |
| Infra     | Docker, Docker Compose                          |

## Quick Start

### Prerequisites

- Docker & Docker Compose v2
- NVIDIA GPU with CUDA (recommended, falls back to CPU)

### Run

```bash
git clone git@github.com:brunos3d/omnivoice-app.git
cd omnivoice-app

cp .env.example .env

# Start all services
docker compose up --build
```

The first startup downloads the OmniVoice model (~2.5 GB). This happens automatically.

Open **http://localhost:3000** in your browser.

### Environment Variables

See `.env.example` for all configuration options.

| Variable          | Default                  | Description                             |
| ----------------- | ------------------------ | --------------------------------------- |
| `DATABASE_URL`    | `sqlite+aiosqlite://...` | Database connection URL                 |
| `OMNIVOICE_MODEL` | `k2-fsa/OmniVoice`       | HuggingFace model repo or local path    |
| `LOAD_ASR`        | `false`                  | Load Whisper ASR for auto-transcription |
| `ASR_MODEL`       | `openai/whisper-...`     | ASR model for reference transcription   |
| `HF_HOME`         | `/data/models`           | HuggingFace cache directory             |
| `CORS_ORIGINS`    | `["http://localhost:...` | Allowed CORS origins                    |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Browser                           │
│  ┌─────────────────────────────────────────────────┐│
│  │  Next.js 15 App (port 3000)                     ││
│  │  - Text Input / Voice Recorder / Upload          ││
│  │  - Audio Player / Waveform / Status Panel        ││
│  │  - Voice Library (CRUD)                          ││
│  └──────────────┬──────────────────────────────────┘│
└─────────────────┼───────────────────────────────────┘
                  │ HTTP / JSON
┌─────────────────┼───────────────────────────────────┐
│  FastAPI Backend (port 8000)                         │
│  ┌──────────────┴──────────────────────────────────┐│
│  │  REST API                                        ││
│  │  ├── /voices        — Voice profile CRUD         ││
│  │  ├── /generate      — Submit generation job      ││
│  │  ├── /jobs/{id}     — Poll job status            ││
│  │  └── /health        — Health check               ││
│  └──────────────────────────────────────────────────┘│
│  ┌──────────────────────────────────────────────────┐│
│  │  OmniVoice Service                                ││
│  │  - Model lifecycle (load once per startup)        ││
│  │  - Voice clone prompt extraction + caching        ││
│  │  - Async inference with background workers        ││
│  └──────────────────────────────────────────────────┘│
│  ┌──────────────────────────────────────────────────┐│
│  │  Persistence                                      ││
│  │  - SQLite (voice profiles, generation jobs)       ││
│  │  - /data/voices/{id}/voice.wav                    ││
│  │  - /data/generated/{hash}.wav                     ││
│  │  - /data/models/ (HuggingFace cache)              ││
│  └──────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
```

## API Endpoints

| Method | Path                 | Description                      |
| ------ | -------------------- | -------------------------------- |
| GET    | `/health`            | Health check + model status      |
| GET    | `/models/status`     | Detailed model loading status    |
| GET    | `/voices`            | List all voice profiles          |
| POST   | `/voices`            | Create voice profile (multipart) |
| GET    | `/voices/{id}`       | Get voice profile details        |
| PUT    | `/voices/{id}`       | Update voice profile             |
| DELETE | `/voices/{id}`       | Delete voice profile             |
| GET    | `/voices/{id}/audio` | Download reference audio         |
| POST   | `/generate`          | Submit a TTS generation job      |
| GET    | `/jobs/{id}`         | Poll job status                  |
| GET    | `/jobs/{id}/audio`   | Download generated audio         |

## Development

### Without Docker

**Backend:**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
mkdir -p /tmp/omnivoice-data/{voices,uploads,generated,models}
DATA_DIR=/tmp/omnivoice-data uvicorn app.main:app --reload
```

**Frontend:**

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

## License

This project is for educational and research purposes. OmniVoice is licensed under Apache 2.0.

# Developer Onboarding

A fast path to running, testing, and extending OmniVoice.

> See also: [Architecture](ARCHITECTURE.md) · [Data Model](DATA_MODEL.md) · [API](API.md) · [Voice Model](VOICE_MODEL.md) · [Languages](LANGUAGES.md) · [Contributing](../CONTRIBUTING.md)

---

## Run the app

```bash
docker compose up --build      # first run downloads the model (~2.5 GB)
```

Frontend: http://localhost:3000 · Backend: http://localhost:8000 · API docs (FastAPI):
http://localhost:8000/docs

### Without Docker

Backend:
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
mkdir -p /tmp/omnivoice-data/{voices,uploads,generated,models}
DATA_DIR=/tmp/omnivoice-data uvicorn app.main:app --reload
```

Frontend:
```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

---

## Project layout

```
backend/app/
  api/            FastAPI routers (voices, generation, v1 public API, api_keys, …)
  core/           config, database, migrations (startup runner), identity seam
  models/db.py    ORM models (User, VoiceProfile, ApiKey, GenerationJob)
  schemas/        Pydantic request/response models
  services/       omnivoice model wrapper, storage, voice_repository, voice_metadata,
                  api_keys
frontend/src/
  app/            routes (TTS, voices, clone, history, settings, api/*)
  components/     shell, voice, generation, api, ui (shadcn), common
  lib/            api client, languages registry, api-examples
  store/          Zustand global store
  hooks/          React Query hooks
docs/             architecture, API, voice model, data model, languages, roadmap, specs
```

---

## Testing & verification

**Backend** (tests avoid the heavy model/storage deps). The pinned dependencies need
Python 3.12 (newer Python lacks some wheels):

```bash
cd backend
uv venv --python 3.12 .venv-test            # or: python3.12 -m venv .venv-test
.venv-test/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv-test/bin/python -m pytest             # run from backend/
```

`.venv-test` is gitignored. Tests cover ids, voice metadata, migrations, repository,
schemas, voice listing/favorites, and API keys.

**Frontend:**

```bash
cd frontend
npx tsc --noEmit        # type check
npx next lint           # lint
npx next build          # production build
node --test scripts/    # language parser tests
```

---

## Common tasks

- **Add a DB column** — see [Data Model → Adding a column](DATA_MODEL.md#adding-a-column-pattern).
- **Refresh the language list** — see [Languages → Regenerating](LANGUAGES.md#regenerating).
- **Add a voice attribute** — edit `frontend/src/config/voice-design.ts`; the builder,
  validation, and `instruct` string follow automatically. Mirror category membership in
  `backend/app/services/voice_metadata.py` if it should feed `characteristics`.
- **Add a public API endpoint** — add to `backend/app/api/v1.py` behind the
  `require_api_key` dependency; document it in [API.md](API.md).

---

## Conventions

- TypeScript strict mode; reuse shadcn/ui + existing components; preserve the dark theme.
- Backend: async SQLAlchemy; keep migrations idempotent and additive.
- TDD for backend logic (write the failing test first).
- New multi-tenant-aware code should depend on `core/identity.get_current_owner_id()`
  rather than referencing the owner constant directly — see [SaaS Architecture](SAAS_ARCHITECTURE.md).
- Address voices externally by `public_voice_id`, never the internal UUID.

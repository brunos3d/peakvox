# PeakVox Phase 3 — Voice / VoiceVariant Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Prerequisite:** Phases 1–2 merged. This is the **core domain change** (ADR-0001) and gates Phases 4–10.

**Goal:** Split the fused `VoiceProfile` into a model-agnostic `Voice` identity plus per-model `VoiceVariant` realizations, backfilling existing voices to one OmniVoice variant (carrying `public_voice_id` unchanged), and resolve `Voice + Model → VoiceVariant` in the generation path — without breaking the existing `/voices` API, generation, or any external `public_voice_id`.

**Architecture:** Additive + backfill. New `voices` and `voice_variants` tables are created by the idempotent runner and backfilled from `voice_profiles` (one `Voice` + one `omnivoice-base` `VoiceVariant` each). `voice_profiles` is **kept as a read-only fallback** during this phase — voice CRUD continues to write it AND mirror into `voices`/`voice_variants` (dual-write), so a regression can fall back. Generation resolves the variant from the new tables, reading the reference audio + transcript from the variant's `artifacts`/`params`. Full retirement of `voice_profiles` is a later, separate step once all consumers read the new tables.

**Tech Stack:** Python 3.12, async SQLAlchemy + aiosqlite, FastAPI. Tests: pytest (`asyncio_mode=auto`), SQLite on `tmp_path`, `run_migrations(conn)` + PRAGMA introspection (per `tests/test_migrations.py`).

**Reference docs:** [ADR-0001](../../architecture/adrs/0001-voice-variant-split.md), [Domain §1,4,5,7](../../architecture/02-DOMAIN_ARCHITECTURE.md), [Data §3.2,3.3](../../architecture/03-DATA_ARCHITECTURE.md), [Migration §2](../../architecture/08-MIGRATION_ARCHITECTURE.md).

---

## File Structure

**Modify:**
- `backend/app/models/db.py` — add `Voice` + `VoiceVariant` ORM models.
- `backend/app/core/migrations.py` — backfill `voice_profiles → voices + voice_variants`; add `generation_jobs.voice_id`/`voice_variant_id` columns.
- `backend/app/api/voices.py` — dual-write `voices`/`voice_variants` on create/update/delete.
- `backend/app/services/omnivoice_service.py` or the generation worker — resolve variant artifacts (located in-task).

**Create:**
- `backend/app/services/voice_variant_repository.py` — identity + variant lookups, `resolve_variant`.
- `backend/app/services/voice_onboarding.py` — `split_profile_into_voice_and_variant` (used by both backfill and dual-write).
- `backend/tests/test_voice_variant_models.py`
- `backend/tests/test_voice_split_migration.py`
- `backend/tests/test_voice_variant_repository.py`
- `backend/tests/test_variant_resolution.py`
- `backend/tests/test_generation_jobs_voice_columns.py`

---

## Task 1: `Voice` + `VoiceVariant` ORM models

**Files:**
- Modify: `backend/app/models/db.py`
- Create: `backend/tests/test_voice_variant_models.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_voice_variant_models.py`:

```python
from app.core.database import Base
import app.models.db  # noqa: F401


def test_voice_and_variant_tables_registered():
    tables = set(Base.metadata.tables.keys())
    assert {"voices", "voice_variants"} <= tables


def test_voice_has_identity_columns():
    cols = {c.name for c in Base.metadata.tables["voices"].columns}
    assert {
        "id", "public_voice_id", "creator_id", "owner_id", "name", "language",
        "preview_audio", "characteristics", "royalty_config", "is_public", "status",
    } <= cols


def test_variant_has_realization_columns_and_unique_pair():
    table = Base.metadata.tables["voice_variants"]
    cols = {c.name for c in table.columns}
    assert {"id", "voice_id", "model_id", "model_version", "artifact_type",
            "artifacts", "params", "source", "status"} <= cols
    # UNIQUE(voice_id, model_id)
    uniques = [
        tuple(c.name for c in con.columns)
        for con in table.constraints
        if con.__class__.__name__ == "UniqueConstraint"
    ]
    assert ("voice_id", "model_id") in uniques
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_voice_variant_models.py -v`
Expected: FAIL (tables not registered).

- [ ] **Step 3: Write minimal implementation**

In `backend/app/models/db.py`, add `UniqueConstraint` to the SQLAlchemy import line:

```python
from sqlalchemy import String, Text, DateTime, Float, JSON, Boolean, Integer, UniqueConstraint
```

Add the models (after `VoiceProfile`):

```python
class Voice(Base):
    """Model-agnostic voice identity — the stable, ownable economic asset (ADR-0001).

    Split out of the legacy VoiceProfile: identity + metadata live here; per-model artifacts
    live in VoiceVariant. ``public_voice_id`` is carried over from the profile unchanged.
    """

    __tablename__ = "voices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    public_voice_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=generate_public_voice_id
    )
    creator_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    owner_id: Mapped[str] = mapped_column(
        String(36), index=True, default=lambda: settings.LOCAL_OWNER_ID
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(64), nullable=True)
    language_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    preview_audio: Mapped[str | None] = mapped_column(String(512), nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    characteristics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    royalty_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # Cloud-only semantics
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_community_voice: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_preset_voice: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ready")
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class VoiceVariant(Base):
    """A Voice realized for one Model — the artifacts that engine needs to render the identity.

    Unique per (voice_id, model_id). Derivable: if its model updates, mark ``stale`` and
    rebuild from the Voice's canonical sources without changing public_voice_id.
    """

    __tablename__ = "voice_variants"
    __table_args__ = (UniqueConstraint("voice_id", "model_id", name="uq_variant_voice_model"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    voice_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    model_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # reference_sample | embedding | checkpoint | adapter | finetune | metadata
    artifact_type: Mapped[str] = mapped_column(String(32), nullable=False, default="reference_sample")
    artifacts: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # storage keys
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True)     # model-specific config
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="cloned")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ready")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_voice_variant_models.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/db.py backend/tests/test_voice_variant_models.py
git commit -m "feat(models): Voice (identity) + VoiceVariant (realization) entities"
```

---

## Task 2: The split helper (pure function, reused by backfill + dual-write)

A single pure function maps a `voice_profiles` row dict into a `Voice` dict + an `omnivoice-base` `VoiceVariant` dict. Defining it once keeps backfill and runtime dual-write consistent (DRY).

**Files:**
- Create: `backend/app/services/voice_onboarding.py`
- Create: `backend/tests/test_voice_onboarding.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_voice_onboarding.py`:

```python
from app.services.voice_onboarding import split_profile_row

PROFILE = {
    "id": "uuid-1",
    "public_voice_id": "voice_ABC123",
    "owner_id": "owner-1",
    "name": "Bruno",
    "description": "test",
    "language": "Portuguese",
    "language_code": "pt",
    "transcript": "olá mundo",
    "audio_filename": "voices/uuid-1/reference.wav",
    "characteristics": {"gender": "male"},
    "generation_defaults": {"voice_design": {"gender": "male"}, "num_step": 32},
    "is_public": False,
    "is_favorite": True,
    "status": "ready",
    "usage_count": 5,
}


def test_split_preserves_public_voice_id_on_voice():
    voice, variant = split_profile_row(PROFILE)
    assert voice["public_voice_id"] == "voice_ABC123"
    assert voice["id"] == "uuid-1"  # reuse the profile UUID as the Voice id (stable storage prefix)
    assert voice["name"] == "Bruno"
    assert voice["is_favorite"] is True


def test_split_builds_omnivoice_variant_with_artifacts_and_params():
    voice, variant = split_profile_row(PROFILE)
    assert variant["voice_id"] == "uuid-1"
    assert variant["model_id"] == "omnivoice-base"
    assert variant["artifacts"]["audio"] == "voices/uuid-1/reference.wav"
    assert variant["params"]["transcript"] == "olá mundo"
    assert variant["params"]["generation_defaults"]["num_step"] == 32
    assert variant["source"] == "cloned"
    assert variant["status"] == "ready"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_voice_onboarding.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.voice_onboarding'`.

- [ ] **Step 3: Write minimal implementation**

`backend/app/services/voice_onboarding.py`:

```python
"""Voice onboarding: turn a legacy VoiceProfile into a Voice + OmniVoice VoiceVariant.

``split_profile_row`` is a pure mapping reused by the backfill migration and by runtime
dual-write on voice create/update, so both paths stay identical (ADR-0001 / Migration §2).
"""

from typing import Any

DEFAULT_MODEL_ID = "omnivoice-base"


def split_profile_row(profile: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return ``(voice_dict, variant_dict)`` derived from a voice_profiles row.

    The Voice reuses the profile's UUID as its ``id`` (so existing storage prefixes
    ``/data/voices/{id}/`` keep working) and carries ``public_voice_id`` unchanged.
    """
    voice = {
        "id": profile["id"],
        "public_voice_id": profile["public_voice_id"],
        "owner_id": profile.get("owner_id"),
        "creator_id": None,
        "name": profile["name"],
        "description": profile.get("description"),
        "language": profile.get("language"),
        "language_code": profile.get("language_code"),
        "preview_audio": profile.get("audio_filename"),  # the reference doubles as preview initially
        "meta": profile.get("meta"),
        "characteristics": profile.get("characteristics"),
        "royalty_config": None,
        "is_public": bool(profile.get("is_public", False)),
        "is_community_voice": bool(profile.get("is_community_voice", False)),
        "is_preset_voice": bool(profile.get("is_preset_voice", False)),
        "is_favorite": bool(profile.get("is_favorite", False)),
        "status": profile.get("status", "ready"),
        "usage_count": int(profile.get("usage_count", 0) or 0),
    }
    defaults = profile.get("generation_defaults") or {}
    variant = {
        "voice_id": profile["id"],
        "model_id": DEFAULT_MODEL_ID,
        "model_version": None,
        "artifact_type": "reference_sample",
        "artifacts": {"audio": profile.get("audio_filename")},
        "params": {
            "transcript": profile.get("transcript"),
            "voice_design": defaults.get("voice_design"),
            "generation_defaults": defaults,
        },
        "source": "cloned",
        "status": "ready",
    }
    return voice, variant
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_voice_onboarding.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/voice_onboarding.py backend/tests/test_voice_onboarding.py
git commit -m "feat(voices): pure split_profile_row mapping (Voice + OmniVoice variant)"
```

---

## Task 3: Backfill migration (`voice_profiles → voices + voice_variants`)

The central migration. Idempotent: a profile is split only if no `voices` row already carries its `public_voice_id`.

**Files:**
- Modify: `backend/app/core/migrations.py`
- Create: `backend/tests/test_voice_split_migration.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_voice_split_migration.py`:

```python
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.migrations import run_migrations


@pytest.fixture
async def engine(tmp_path):
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/split.db", future=True)
    yield eng
    await eng.dispose()


async def _seed_profile(engine):
    # Run migrations first so voice_profiles + new columns exist, then insert a legacy voice.
    async with engine.begin() as conn:
        await run_migrations(conn)
        await conn.execute(text(
            "INSERT INTO voice_profiles "
            "(id, public_voice_id, owner_id, name, audio_filename, transcript, "
            " generation_defaults, status, usage_count, created_at, updated_at) "
            "VALUES ('uuid-1', 'voice_ABC123', 'owner-1', 'Bruno', "
            " 'voices/uuid-1/reference.wav', 'olá', '{\"num_step\": 32}', 'ready', 3, "
            " '2026-01-01T00:00:00', '2026-01-01T00:00:00')"
        ))


async def test_backfill_creates_voice_and_variant(engine):
    await _seed_profile(engine)
    async with engine.begin() as conn:
        await run_migrations(conn)  # second run performs the split

    async with engine.begin() as conn:
        v = (await conn.execute(text(
            "SELECT id, public_voice_id, name FROM voices WHERE public_voice_id='voice_ABC123'"
        ))).first()
        assert v is not None
        assert v[0] == "uuid-1" and v[2] == "Bruno"

        var = (await conn.execute(text(
            "SELECT model_id, artifacts, params FROM voice_variants WHERE voice_id='uuid-1'"
        ))).first()
        assert var is not None
        assert var[0] == "omnivoice-base"
        assert "voices/uuid-1/reference.wav" in var[1]


async def test_backfill_is_idempotent(engine):
    await _seed_profile(engine)
    async with engine.begin() as conn:
        await run_migrations(conn)
    async with engine.begin() as conn:
        await run_migrations(conn)  # must not duplicate
    async with engine.begin() as conn:
        count = (await conn.execute(text(
            "SELECT COUNT(*) FROM voices WHERE public_voice_id='voice_ABC123'"
        ))).scalar()
        assert count == 1
        vcount = (await conn.execute(text(
            "SELECT COUNT(*) FROM voice_variants WHERE voice_id='uuid-1'"
        ))).scalar()
        assert vcount == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_voice_split_migration.py -v`
Expected: FAIL (no backfill yet; `voices` empty).

- [ ] **Step 3: Write the backfill step**

In `backend/app/core/migrations.py`, add the import near the top:

```python
from app.services.voice_onboarding import split_profile_row
```

Add this function (after `_backfill_voice_profiles`):

```python
async def _backfill_voice_split(conn: AsyncConnection) -> None:
    """Split each voice_profiles row into a voices row + an omnivoice-base voice_variants row.

    Idempotent: skips any profile whose public_voice_id already exists in voices.
    """
    existing = await conn.execute(text("SELECT public_voice_id FROM voices"))
    already = {r[0] for r in existing.fetchall()}

    profiles = await conn.execute(text("SELECT * FROM voice_profiles"))
    rows = profiles.mappings().all()
    now = datetime.now(timezone.utc).isoformat()

    for row in rows:
        if row["public_voice_id"] in already:
            continue
        voice, variant = split_profile_row(dict(row))
        await conn.execute(
            text(
                "INSERT INTO voices (id, public_voice_id, creator_id, owner_id, name, "
                "description, language, language_code, preview_audio, meta, characteristics, "
                "royalty_config, is_public, is_community_voice, is_preset_voice, is_favorite, "
                "status, usage_count, created_at, updated_at) VALUES "
                "(:id, :public_voice_id, :creator_id, :owner_id, :name, :description, :language, "
                ":language_code, :preview_audio, :meta, :characteristics, :royalty_config, "
                ":is_public, :is_community_voice, :is_preset_voice, :is_favorite, :status, "
                ":usage_count, :now, :now)"
            ),
            {
                **voice,
                "meta": json.dumps(voice["meta"]) if voice["meta"] is not None else None,
                "characteristics": json.dumps(voice["characteristics"]) if voice["characteristics"] is not None else None,
                "royalty_config": None,
                "now": now,
            },
        )
        await conn.execute(
            text(
                "INSERT INTO voice_variants (id, voice_id, model_id, model_version, "
                "artifact_type, artifacts, params, source, status, created_at, updated_at) "
                "VALUES (:id, :voice_id, :model_id, :model_version, :artifact_type, "
                ":artifacts, :params, :source, :status, :now, :now)"
            ),
            {
                "id": _new_variant_id(),
                "voice_id": variant["voice_id"],
                "model_id": variant["model_id"],
                "model_version": variant["model_version"],
                "artifact_type": variant["artifact_type"],
                "artifacts": json.dumps(variant["artifacts"]),
                "params": json.dumps(variant["params"]),
                "source": variant["source"],
                "status": variant["status"],
                "now": now,
            },
        )
```

Add a UUID helper near the top of the file (the runner has no `uuid` import yet):

```python
import uuid


def _new_variant_id() -> str:
    return str(uuid.uuid4())
```

Call the backfill in `run_migrations`, **after** `_seed_builtin_models(conn)` (voices need the models seeded first) and after the public-id index step:

```python
    # 7. Split legacy voice_profiles into voices + voice_variants (idempotent backfill).
    await _backfill_voice_split(conn)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_voice_split_migration.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/migrations.py backend/tests/test_voice_split_migration.py
git commit -m "feat(migrations): backfill voice_profiles -> voices + omnivoice voice_variants (idempotent)"
```

---

## Task 4: `generation_jobs.voice_id` + `voice_variant_id` columns

**Files:**
- Modify: `backend/app/models/db.py` (add columns to `GenerationJob`)
- Modify: `backend/app/core/migrations.py` (`_NEW_JOB_COLUMNS`)
- Create: `backend/tests/test_generation_jobs_voice_columns.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_generation_jobs_voice_columns.py`:

```python
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.migrations import run_migrations


@pytest.fixture
async def engine(tmp_path):
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/jobs.db", future=True)
    yield eng
    await eng.dispose()


async def test_generation_jobs_has_voice_columns(engine):
    async with engine.begin() as conn:
        await run_migrations(conn)
        res = await conn.execute(text("PRAGMA table_info(generation_jobs)"))
        cols = {row[1] for row in res.fetchall()}
    assert {"voice_id", "voice_variant_id"} <= cols
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_generation_jobs_voice_columns.py -v`
Expected: FAIL (columns absent).

- [ ] **Step 3: Write minimal implementation**

In `backend/app/models/db.py`, add to `GenerationJob` (after `voice_profile_id`):

```python
    voice_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    voice_variant_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
```

In `backend/app/core/migrations.py`, extend `_NEW_JOB_COLUMNS`:

```python
_NEW_JOB_COLUMNS: list[tuple[str, str]] = [
    ("model_id", "ALTER TABLE generation_jobs ADD COLUMN model_id VARCHAR(64)"),
    ("voice_id", "ALTER TABLE generation_jobs ADD COLUMN voice_id VARCHAR(36)"),
    ("voice_variant_id", "ALTER TABLE generation_jobs ADD COLUMN voice_variant_id VARCHAR(36)"),
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_generation_jobs_voice_columns.py tests/test_model_migration.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/db.py backend/app/core/migrations.py backend/tests/test_generation_jobs_voice_columns.py
git commit -m "feat(jobs): generation_jobs.voice_id + voice_variant_id columns"
```

---

## Task 5: Variant repository + resolution

`resolve_variant(db, voice_id, model_id)` returns the variant or None; `get_voice_identity_by_public_id` reads the new `voices` table.

**Files:**
- Create: `backend/app/services/voice_variant_repository.py`
- Create: `backend/tests/test_voice_variant_repository.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_voice_variant_repository.py`:

```python
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)

from app.core.migrations import run_migrations
from app.services.voice_variant_repository import (
    get_voice_identity_by_public_id, resolve_variant,
)


@pytest.fixture
async def session(tmp_path):
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/vr.db", future=True)
    async with eng.begin() as conn:
        await run_migrations(conn)
        await conn.execute(text(
            "INSERT INTO voice_profiles (id, public_voice_id, owner_id, name, audio_filename, "
            "transcript, generation_defaults, status, usage_count, created_at, updated_at) "
            "VALUES ('uuid-1','voice_ABC123','owner-1','Bruno','voices/uuid-1/reference.wav',"
            "'olá','{}','ready',0,'2026-01-01','2026-01-01')"
        ))
        await run_migrations(conn)  # backfill the split
    maker = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await eng.dispose()


async def test_get_identity_by_public_id(session):
    voice = await get_voice_identity_by_public_id(session, "voice_ABC123")
    assert voice is not None
    assert voice.id == "uuid-1"
    assert voice.public_voice_id == "voice_ABC123"


async def test_resolve_existing_omnivoice_variant(session):
    variant = await resolve_variant(session, voice_id="uuid-1", model_id="omnivoice-base")
    assert variant is not None
    assert variant.artifacts["audio"] == "voices/uuid-1/reference.wav"


async def test_resolve_missing_variant_returns_none(session):
    variant = await resolve_variant(session, voice_id="uuid-1", model_id="kokoro")
    assert variant is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_voice_variant_repository.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

`backend/app/services/voice_variant_repository.py`:

```python
"""Lookups for the split voice model: identity (voices) + realization (voice_variants)."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import Voice, VoiceVariant


async def get_voice_identity_by_public_id(db: AsyncSession, public_voice_id: str) -> Optional[Voice]:
    res = await db.execute(select(Voice).where(Voice.public_voice_id == public_voice_id))
    return res.scalar_one_or_none()


async def resolve_variant(db: AsyncSession, *, voice_id: str, model_id: str) -> Optional[VoiceVariant]:
    """Return the (voice_id, model_id) variant, or None if it does not exist yet.

    A None result means the variant must be built by the onboarding pipeline before generation
    (lazy build / stale rebuild — wired in a later phase). For omnivoice-base on a backfilled
    voice, the variant always exists.
    """
    res = await db.execute(
        select(VoiceVariant).where(
            VoiceVariant.voice_id == voice_id, VoiceVariant.model_id == model_id
        )
    )
    return res.scalar_one_or_none()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_voice_variant_repository.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/voice_variant_repository.py backend/tests/test_voice_variant_repository.py
git commit -m "feat(voices): variant repository — identity lookup + resolve_variant"
```

---

## Task 6: Resolve variant artifacts in the generation path

Generation currently reads reference audio + transcript from the voice profile. Add a resolver that, given a `public_voice_id` + `model_id`, returns the generation inputs (`ref_audio_key`, `ref_text`, `generation_defaults`) from the **variant**, falling back to the profile only if the split hasn't happened (defensive).

**Files:**
- Create: `backend/app/services/variant_resolution.py`
- Create: `backend/tests/test_variant_resolution.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_variant_resolution.py`:

```python
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)

from app.core.migrations import run_migrations
from app.services.variant_resolution import resolve_generation_inputs, VariantUnavailableError


@pytest.fixture
async def session(tmp_path):
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/gr.db", future=True)
    async with eng.begin() as conn:
        await run_migrations(conn)
        await conn.execute(text(
            "INSERT INTO voice_profiles (id, public_voice_id, owner_id, name, audio_filename, "
            "transcript, generation_defaults, status, usage_count, created_at, updated_at) "
            "VALUES ('uuid-1','voice_ABC123','owner-1','Bruno','voices/uuid-1/reference.wav',"
            "'olá','{\"num_step\":32}','ready',0,'2026-01-01','2026-01-01')"
        ))
        await run_migrations(conn)
    maker = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await eng.dispose()


async def test_resolves_inputs_for_omnivoice(session):
    inputs = await resolve_generation_inputs(
        session, public_voice_id="voice_ABC123", model_id="omnivoice-base"
    )
    assert inputs.voice_id == "uuid-1"
    assert inputs.ref_audio_key == "voices/uuid-1/reference.wav"
    assert inputs.ref_text == "olá"
    assert inputs.generation_defaults["num_step"] == 32


async def test_unknown_voice_raises(session):
    with pytest.raises(VariantUnavailableError):
        await resolve_generation_inputs(session, public_voice_id="voice_NOPE", model_id="omnivoice-base")


async def test_missing_variant_raises(session):
    with pytest.raises(VariantUnavailableError):
        await resolve_generation_inputs(session, public_voice_id="voice_ABC123", model_id="kokoro")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_variant_resolution.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

`backend/app/services/variant_resolution.py`:

```python
"""Resolve generation inputs from a Voice + Model, via its VoiceVariant.

This is the wire-level realization of the ``Voice + Model -> VoiceVariant`` contract: callers
pass a stable public_voice_id + model id; this returns the concrete inputs the provider needs.
Lazy/auto build of a missing variant is wired in a later phase; for now a missing variant is an
explicit error the caller maps to 409 (API §3).
"""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.voice_variant_repository import (
    get_voice_identity_by_public_id, resolve_variant,
)


class VariantUnavailableError(Exception):
    pass


@dataclass(frozen=True)
class GenerationInputs:
    voice_id: str
    variant_id: str
    ref_audio_key: str | None
    ref_text: str | None
    generation_defaults: dict


async def resolve_generation_inputs(
    db: AsyncSession, *, public_voice_id: str, model_id: str
) -> GenerationInputs:
    voice = await get_voice_identity_by_public_id(db, public_voice_id)
    if voice is None:
        raise VariantUnavailableError(f"Unknown voice '{public_voice_id}'")

    variant = await resolve_variant(db, voice_id=voice.id, model_id=model_id)
    if variant is None:
        raise VariantUnavailableError(
            f"No variant for voice '{public_voice_id}' on model '{model_id}' (build required)"
        )

    artifacts = variant.artifacts or {}
    params = variant.params or {}
    return GenerationInputs(
        voice_id=voice.id,
        variant_id=variant.id,
        ref_audio_key=artifacts.get("audio"),
        ref_text=params.get("transcript"),
        generation_defaults=params.get("generation_defaults") or {},
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_variant_resolution.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/variant_resolution.py backend/tests/test_variant_resolution.py
git commit -m "feat(generation): Voice+Model->VoiceVariant input resolution"
```

---

## Task 7: Wire resolution into the generation endpoint (dual-path, safe)

Make the generation endpoint resolve inputs through the variant when a `voice` (public id) + `model` are supplied, recording `voice_id`/`voice_variant_id` on the job, while preserving the existing ad-hoc (uploaded/recorded ref) path unchanged.

**Files:**
- Locate first: `grep -n "voice_profile_id\|ref_audio_path\|create_task\|_process_job\|public_voice_id" backend/app/api/generation.py`
- Modify: `backend/app/api/generation.py`
- Create: `backend/tests/test_generation_uses_variant.py`

- [ ] **Step 1: Read the current generation flow**

Run: `sed -n '1,160p' backend/app/api/generation.py` and identify where a saved voice profile is currently turned into `ref_audio_path` + `ref_text` for the job.

- [ ] **Step 2: Write the failing test**

`backend/tests/test_generation_uses_variant.py` — an integration-style test that posts a generation referencing the backfilled `voice_ABC123` and asserts the created job row carries `voice_id='uuid-1'` and a non-null `voice_variant_id`. Use the app's existing test client pattern (match any existing API test, e.g. `tests/test_api_keys.py`, for client + DB setup). If no HTTP client fixture exists yet, test the resolver integration at the service boundary instead: call the job-creation helper directly with `public_voice_id='voice_ABC123'`, `model_id='omnivoice-base'` and assert the persisted job's `voice_id`/`voice_variant_id`.

```python
# Assert the generation path stamps the job with the resolved variant.
assert job.voice_id == "uuid-1"
assert job.voice_variant_id is not None
assert job.ref_audio_path == "voices/uuid-1/reference.wav"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_generation_uses_variant.py -v`
Expected: FAIL (job not stamped with variant fields).

- [ ] **Step 4: Implement**

In the generation endpoint, when the request carries a saved voice (`public_voice_id`) and a `model_id`, call `resolve_generation_inputs(db, public_voice_id=..., model_id=...)`; populate the `GenerationJob` with `voice_id`, `voice_variant_id`, `ref_audio_path=inputs.ref_audio_key`, `ref_text=inputs.ref_text`, and merge `inputs.generation_defaults` under the request's explicit params (explicit request params win). Catch `VariantUnavailableError` and return `HTTP 409` with its message (per [API §3](../../architecture/04-API_ARCHITECTURE.md)). Leave the uploaded/recorded-reference path untouched.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_generation_uses_variant.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/generation.py backend/tests/test_generation_uses_variant.py
git commit -m "feat(generation): resolve saved-voice generation via VoiceVariant; stamp job"
```

---

## Task 8: Dual-write `voices`/`voice_variants` on voice create/update/delete

Keep `voice_profiles` as the primary write target (fallback), and mirror into the split tables using `split_profile_row`, so new/edited voices are immediately resolvable by generation.

**Files:**
- Modify: `backend/app/api/voices.py` (create/update/delete handlers — lines located via the earlier grep: create `:200`, update `:262`, delete `:372`)
- Create: `backend/tests/test_voice_dual_write.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_voice_dual_write.py` — create a voice through the create handler (or its service helper) and assert a matching `voices` row + `omnivoice-base` `voice_variants` row exist with the same `public_voice_id`; update it and assert the variant's `params`/`artifacts` reflect the change; delete it and assert both the `voices` row and its variants are removed.

- [ ] **Step 2: Run test to verify it fails.** Expected: FAIL (no mirror rows yet).

- [ ] **Step 3: Implement the mirror**

Add a helper `mirror_profile_to_split(db, profile)` in `backend/app/services/voice_onboarding.py` that upserts the `Voice` + `omnivoice-base` `VoiceVariant` from a `VoiceProfile` ORM object using `split_profile_row(profile_as_dict)`. Call it at the end of the create and update handlers (after the profile is committed). In the delete handler, delete the `voices` row (cascade variants by `voice_id`) alongside the profile. Reuse `split_profile_row` — do not duplicate the mapping.

- [ ] **Step 4: Run tests to verify they pass.** Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/voices.py backend/app/services/voice_onboarding.py backend/tests/test_voice_dual_write.py
git commit -m "feat(voices): dual-write Voice + variant on create/update/delete"
```

---

## Task 9: Full backend suite (regression gate)

- [ ] **Step 1:** Run `cd backend && python -m pytest -q`. Expected: all PASS — especially `test_migrations.py`, `test_voice_repository.py`, `test_voice_listing.py` (the legacy profile path must keep working as the fallback).
- [ ] **Step 2:** Debug failures with superpowers:systematic-debugging; commit fixes.

---

## Task 10: Frontend — reference Voice identity; no behavior change

> **REQUIRED per `frontend/AGENTS.md`:** read the relevant Next.js doc before editing.

The split is backend-internal this phase (dual-write keeps the existing `/voices` responses identical). Frontend work is limited to:

- [ ] **Step 1:** Confirm the voice library + generation still function unchanged (the `/voices` payloads are unchanged because the profile path is preserved). Run the app (`run` skill) and verify create → generate with a saved voice works end-to-end.
- [ ] **Step 2:** No code change required unless a payload field moved; if so, update `frontend/src/types/index.ts` + `frontend/src/lib/api.ts` accordingly and `npm run lint && npm run build`.
- [ ] **Step 3:** Commit only if changes were needed.

---

## Done criteria

- [ ] `voices` + `voice_variants` exist; legacy voices backfilled to one `omnivoice-base` variant; `public_voice_id` preserved.
- [ ] Backfill is idempotent (re-running creates no duplicates).
- [ ] `generation_jobs` carries `voice_id` + `voice_variant_id`.
- [ ] `resolve_generation_inputs` returns variant-derived inputs; missing variant → explicit error → `409`.
- [ ] Generation stamps jobs with the resolved variant; ad-hoc reference path unchanged.
- [ ] Voice create/update/delete dual-writes the split tables; `/voices` responses unchanged.
- [ ] `cd backend && python -m pytest -q` fully green; `voice_profiles` still works as fallback.

## Self-review notes (author)

- **Spec coverage** vs Roadmap Phase 3 / ADR-0001 / Migration §2: tables ✓ (T1), backfill preserving `public_voice_id` ✓ (T2–T3), `generation_jobs` columns ✓ (T4), repositories ✓ (T5), `Voice+Model→Variant` resolution ✓ (T6), generation wiring ✓ (T7), dual-write so consumers stay consistent ✓ (T8), fallback retained ✓ (T9). Storage-path moves are deliberately deferred: the variant points at the existing `audio_filename` key, so no bytes move this phase (de-risks; matches Migration §2's "keep old paths in artifacts initially").
- **Type consistency:** `split_profile_row` (T2) is the single mapping reused by backfill (T3) and dual-write (T8). `GenerationInputs` fields (T6) are consumed in T7. `resolve_variant`/`get_voice_identity_by_public_id` (T5) are used by T6. `VoiceVariant` unique `(voice_id, model_id)` (T1) underpins `resolve_variant`'s single-row assumption.
- **No placeholders:** core tasks (T1–T6) carry complete code; T7/T8 give exact integration points + assertions and reuse already-defined functions, with the one "read the current flow" step explicit because those handlers vary by request-shape. Retiring `voice_profiles` entirely is a separate later step (out of scope here, by design — the fallback is intentional).

## Critical path complete

Phases 1→2→3 plans are now written. After Phase 3 lands green, the spine is in place and the **Cloud ecosystem phases (4 Auth → 5 Billing → 6 Creators → 7 Marketplace)** and the **runtime phases (8 Cloud Infra → 9 Public API → 10 Scaling)** each get their own plan via writing-plans, per [Roadmap §cross-phase order](../../architecture/09-ROADMAP.md).

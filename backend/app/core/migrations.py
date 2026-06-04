"""Idempotent, SQLite-safe startup migration runner for the Community Edition.

This is the deliberate, lightweight alternative to Alembic for the self-hosted SQLite
deployment. ``run_migrations`` may be executed any number of times with no changes to
already-migrated records and no data loss. It evolves the legacy single-user schema into
the SaaS-ready voice entity model without recreating any voice.
"""

import json
import uuid
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.config import settings
from app.core.database import Base
from app.services.model_catalog import BUILTIN_MODELS
from app.services.voice_onboarding import split_profile_row
from app.utils.ids import generate_unique_public_voice_id


def _new_variant_id() -> str:
    return str(uuid.uuid4())


def _maybe_json(value):
    """Decode a JSON string column read via raw SQL into a Python object; pass through otherwise."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return value
    return value

# Importing the models registers every table on Base.metadata for create_all.
import app.models.db  # noqa: F401

# New voice_profiles columns and their SQLite-safe DDL. NOT NULL columns carry a DEFAULT
# so existing rows are populated immediately; nullable ones are backfilled below.
_NEW_VOICE_COLUMNS: list[tuple[str, str]] = [
    # Predates Phase 2 — kept so very old databases still converge.
    ("generation_defaults", "ALTER TABLE voice_profiles ADD COLUMN generation_defaults JSON"),
    ("public_voice_id", "ALTER TABLE voice_profiles ADD COLUMN public_voice_id VARCHAR(32)"),
    ("owner_id", "ALTER TABLE voice_profiles ADD COLUMN owner_id VARCHAR(36)"),
    ("language_code", "ALTER TABLE voice_profiles ADD COLUMN language_code VARCHAR(16)"),
    ("preset_tags", "ALTER TABLE voice_profiles ADD COLUMN preset_tags JSON"),
    ("characteristics", "ALTER TABLE voice_profiles ADD COLUMN characteristics JSON"),
    ("is_public", "ALTER TABLE voice_profiles ADD COLUMN is_public BOOLEAN NOT NULL DEFAULT 0"),
    ("is_community_voice", "ALTER TABLE voice_profiles ADD COLUMN is_community_voice BOOLEAN NOT NULL DEFAULT 0"),
    ("is_preset_voice", "ALTER TABLE voice_profiles ADD COLUMN is_preset_voice BOOLEAN NOT NULL DEFAULT 0"),
    ("is_favorite", "ALTER TABLE voice_profiles ADD COLUMN is_favorite BOOLEAN NOT NULL DEFAULT 0"),
    ("status", "ALTER TABLE voice_profiles ADD COLUMN status VARCHAR(32) NOT NULL DEFAULT 'ready'"),
    ("usage_count", "ALTER TABLE voice_profiles ADD COLUMN usage_count INTEGER NOT NULL DEFAULT 0"),
    ("updated_at", "ALTER TABLE voice_profiles ADD COLUMN updated_at DATETIME"),
]

# Matches SQLAlchemy's auto-generated name (ix_<table>_<column>) so fresh installs — where
# create_all already built the unique index — converge with the IF NOT EXISTS path here.
_PUBLIC_ID_INDEX = (
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_voice_profiles_public_voice_id "
    "ON voice_profiles (public_voice_id)"
)


async def run_migrations(conn: AsyncConnection) -> None:
    """Bring the database up to the current schema. Idempotent and safe to re-run."""
    # 1. Create any missing tables (users, generation_jobs, voice_profiles, models).
    await conn.run_sync(Base.metadata.create_all)

    # 2. Additively add new voice_profiles columns to pre-existing databases.
    await _add_missing_columns(conn)

    # 2b. Additively add new generation_jobs columns (multi-model support).
    await _add_missing_job_columns(conn)

    # 2c. Additively add new models columns (first-class model metadata).
    await _add_missing_model_columns(conn)

    # 3. Seed the single implicit local owner.
    await _seed_local_owner(conn)

    # 4. Backfill legacy rows that predate the new columns.
    await _backfill_voice_profiles(conn)

    # 5. Enforce public_voice_id uniqueness (after backfill — order matters).
    await conn.execute(text(_PUBLIC_ID_INDEX))

    # 6. Upsert the built-in model catalog (never clobbers user/community models).
    await _seed_builtin_models(conn)

    # 7. Split legacy voice_profiles into voices + voice_variants (idempotent backfill).
    await _backfill_voice_split(conn)


async def _existing_voice_columns(conn: AsyncConnection) -> set[str]:
    res = await conn.execute(text("PRAGMA table_info(voice_profiles)"))
    return {row[1] for row in res.fetchall()}


async def _add_missing_columns(conn: AsyncConnection) -> None:
    existing = await _existing_voice_columns(conn)
    for column, ddl in _NEW_VOICE_COLUMNS:
        if column in existing:
            continue
        try:
            await conn.execute(text(ddl))
        except Exception:  # pragma: no cover - duplicate column on a racing run
            logger.debug("Column {} already present, skipping", column)


# New generation_jobs columns (multi-model). Additive, NULL-default = back-compat.
_NEW_JOB_COLUMNS: list[tuple[str, str]] = [
    ("model_id", "ALTER TABLE generation_jobs ADD COLUMN model_id VARCHAR(64)"),
    ("voice_id", "ALTER TABLE generation_jobs ADD COLUMN voice_id VARCHAR(36)"),
    ("voice_variant_id", "ALTER TABLE generation_jobs ADD COLUMN voice_variant_id VARCHAR(36)"),
]


async def _add_missing_job_columns(conn: AsyncConnection) -> None:
    res = await conn.execute(text("PRAGMA table_info(generation_jobs)"))
    existing = {row[1] for row in res.fetchall()}
    for column, ddl in _NEW_JOB_COLUMNS:
        if column in existing:
            continue
        try:
            await conn.execute(text(ddl))
        except Exception:  # pragma: no cover - duplicate column on a racing run
            logger.debug("Job column {} already present, skipping", column)


# New models columns (Phase 2 — first-class model metadata). Additive, NULL-default.
_NEW_MODEL_COLUMNS: list[tuple[str, str]] = [
    ("requirements", "ALTER TABLE models ADD COLUMN requirements JSON"),
    ("license", "ALTER TABLE models ADD COLUMN license JSON"),
    ("provider_metadata", "ALTER TABLE models ADD COLUMN provider_metadata JSON"),
    ("deprecated_at", "ALTER TABLE models ADD COLUMN deprecated_at DATETIME"),
]


async def _add_missing_model_columns(conn: AsyncConnection) -> None:
    res = await conn.execute(text("PRAGMA table_info(models)"))
    existing = {row[1] for row in res.fetchall()}
    for column, ddl in _NEW_MODEL_COLUMNS:
        if column in existing:
            continue
        try:
            await conn.execute(text(ddl))
        except Exception:  # pragma: no cover - duplicate column on a racing run
            logger.debug("Model column {} already present, skipping", column)


async def _seed_builtin_models(conn: AsyncConnection) -> None:
    """Idempotently upsert built-in model rows. Built-in fields are refreshed on every run so
    catalog edits (new tags, status changes) propagate; user/community rows (is_builtin=0) are
    never touched."""
    now = datetime.now(timezone.utc).isoformat()
    for m in BUILTIN_MODELS:
        await conn.execute(
            text(
                """
                INSERT INTO models (
                    id, name, description, version, provider, repo_id, model_path,
                    supported_languages, supported_tags, supported_voice_design,
                    capabilities, status, is_default, is_builtin, editions,
                    requirements, license, provider_metadata,
                    owner_id, created_at, updated_at
                ) VALUES (
                    :id, :name, :description, :version, :provider, :repo_id, :model_path,
                    :supported_languages, :supported_tags, :supported_voice_design,
                    :capabilities, :status, :is_default, 1, :editions,
                    :requirements, :license, :provider_metadata,
                    NULL, :now, :now
                )
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    description=excluded.description,
                    version=excluded.version,
                    provider=excluded.provider,
                    repo_id=excluded.repo_id,
                    model_path=excluded.model_path,
                    supported_languages=excluded.supported_languages,
                    supported_tags=excluded.supported_tags,
                    supported_voice_design=excluded.supported_voice_design,
                    capabilities=excluded.capabilities,
                    status=excluded.status,
                    is_default=excluded.is_default,
                    editions=excluded.editions,
                    requirements=excluded.requirements,
                    license=excluded.license,
                    provider_metadata=excluded.provider_metadata,
                    updated_at=excluded.updated_at
                WHERE models.is_builtin = 1
                """
            ),
            {
                "id": m.id,
                "name": m.name,
                "description": m.description,
                "version": m.version,
                "provider": m.provider,
                "repo_id": m.repo_id,
                "model_path": m.model_path,
                "supported_languages": json.dumps(m.supported_languages),
                "supported_tags": json.dumps(m.supported_tags),
                "supported_voice_design": json.dumps(m.supported_voice_design),
                "capabilities": json.dumps(m.capabilities.model_dump()),
                "status": m.status,
                "is_default": 1 if m.is_default else 0,
                "editions": json.dumps(m.editions),
                "requirements": json.dumps(m.requirements.model_dump()),
                "license": json.dumps(m.license.model_dump()) if m.license else None,
                "provider_metadata": json.dumps(m.provider_metadata),
                "now": now,
            },
        )


async def _backfill_voice_split(conn: AsyncConnection) -> None:
    """Split each voice_profiles row into a voices row + an omnivoice-base voice_variants row.

    Idempotent: skips any profile whose public_voice_id already exists in voices. The Voice
    reuses the profile UUID and carries public_voice_id over unchanged (ADR-0001).
    """
    existing = await conn.execute(text("SELECT public_voice_id FROM voices"))
    already = {r[0] for r in existing.fetchall()}

    profiles = await conn.execute(text("SELECT * FROM voice_profiles"))
    rows = profiles.mappings().all()
    now = datetime.now(timezone.utc).isoformat()

    for row in rows:
        if row["public_voice_id"] in already:
            continue
        # Raw SELECT returns JSON columns as strings (no ORM type decoding) — decode them so
        # split_profile_row receives the same dict shape the ORM dual-write path provides.
        row_dict = dict(row)
        for json_col in ("generation_defaults", "meta", "characteristics"):
            row_dict[json_col] = _maybe_json(row_dict.get(json_col))
        voice, variant = split_profile_row(row_dict)
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
                "characteristics": (
                    json.dumps(voice["characteristics"])
                    if voice["characteristics"] is not None
                    else None
                ),
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


async def _seed_local_owner(conn: AsyncConnection) -> None:
    res = await conn.execute(
        text("SELECT id FROM users WHERE id = :id"), {"id": settings.LOCAL_OWNER_ID}
    )
    if res.first() is not None:
        return
    await conn.execute(
        text(
            "INSERT INTO users (id, handle, display_name, email, is_system, created_at) "
            "VALUES (:id, :handle, :display_name, NULL, 1, :created_at)"
        ),
        {
            "id": settings.LOCAL_OWNER_ID,
            "handle": settings.LOCAL_OWNER_HANDLE,
            "display_name": settings.LOCAL_OWNER_DISPLAY_NAME,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )


async def _backfill_voice_profiles(conn: AsyncConnection) -> None:
    # Scalar backfills only touch rows still holding NULLs — already-migrated rows untouched.
    await conn.execute(
        text("UPDATE voice_profiles SET owner_id = :owner WHERE owner_id IS NULL"),
        {"owner": settings.LOCAL_OWNER_ID},
    )
    await conn.execute(text("UPDATE voice_profiles SET status = 'ready' WHERE status IS NULL"))
    await conn.execute(text("UPDATE voice_profiles SET usage_count = 0 WHERE usage_count IS NULL"))
    await conn.execute(
        text("UPDATE voice_profiles SET updated_at = created_at WHERE updated_at IS NULL")
    )

    # Per-row stable public_voice_id for legacy voices, guaranteed unique within the table.
    taken_res = await conn.execute(
        text("SELECT public_voice_id FROM voice_profiles WHERE public_voice_id IS NOT NULL")
    )
    taken = {row[0] for row in taken_res.fetchall()}

    missing_res = await conn.execute(
        text("SELECT id FROM voice_profiles WHERE public_voice_id IS NULL")
    )
    for (voice_id,) in missing_res.fetchall():
        new_id = generate_unique_public_voice_id(exists=lambda v: v in taken)
        taken.add(new_id)
        await conn.execute(
            text("UPDATE voice_profiles SET public_voice_id = :pid WHERE id = :id"),
            {"pid": new_id, "id": voice_id},
        )

#!/usr/bin/env python3
"""Backfill missing VoiceVariants for all voices x all installed models.

Usage:
    # Run inside the Docker container or with backend venv activated:
    python scripts/backfill_variants.py
    python scripts/backfill_variants.py --dry-run
    python scripts/backfill_variants.py --model fish-audio
    python scripts/backfill_variants.py --dry-run --model fish-audio

Algorithm:
    For each Voice:
        locate VoiceSourceAsset
        for each installed model (optionally filtered by --model):
            if variant exists (status in ready|pending|building|failed|deprecated): skip
            else: build variant via runtime.ensure_variant

Environment:
    Requires DATABASE_URL (default: sqlite+aiosqlite:////data/omnivoice.db)
    and DATA_DIR (default: /data) matching the Docker setup.
"""

import argparse
import asyncio
import os
import sys

_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_script_dir)
# Inside Docker: app/ package is at <project_root>/app/
# Locally: app/ package is at <project_root>/backend/app/
for _candidate in (_project_root, os.path.join(_project_root, "backend")):
    if os.path.isdir(os.path.join(_candidate, "app")):
        sys.path.insert(0, _candidate)
        break
else:
    sys.exit("FATAL: cannot find app/ package — run from project root or inside Docker container")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.models.db import Voice, Model, VoiceVariant
from app.services.runtime import runtime, ModelNotRegistered
from app.services.voice_variant_repository import get_voice_identity_by_public_id
from app.services.model_wiring import wire_registry, wire_runtime


async def backfill(
    dry_run: bool = False,
    model_filter: str | None = None,
):
    from app.core.database import init_db

    database_url = os.environ.get("DATABASE_URL", settings.DATABASE_URL)
    engine = create_async_engine(database_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: None)

    async with AsyncSession(engine) as db:
        await init_db()

        voices = (await db.execute(select(Voice))).scalars().all()
        print(f"Found {len(voices)} voices")

        if not voices:
            print("No voices found. Nothing to do.")
            return

        models = (await db.execute(select(Model))).scalars().all()
        if model_filter:
            models = [m for m in models if model_filter.lower() in m.id.lower() or model_filter.lower() in m.name.lower()]
        print(f"Found {len(models)} target models" + (f" (filter: {model_filter})" if model_filter else ""))

        if not models:
            print("No target models found. Nothing to do.")
            return

        all_variants = (await db.execute(select(VoiceVariant))).scalars().all()
        variant_lookup: dict[tuple[str, str], VoiceVariant] = {}
        for v in all_variants:
            variant_lookup[(v.voice_id, v.model_id)] = v

        wire_registry()
        wire_runtime()

        total_built = 0
        total_skipped = 0
        total_errors = 0

        for voice in voices:
            for model in models:
                key = (voice.id, model.id)
                existing = variant_lookup.get(key)

                if existing is not None:
                    print(f"  SKIP  voice={voice.name} ({voice.id}) model={model.name} ({model.id}) — variant exists ({existing.status})")
                    total_skipped += 1
                    continue

                if dry_run:
                    print(f"  WOULD_BUILD  voice={voice.name} ({voice.id}) model={model.name} ({model.id})")
                    total_built += 1
                    continue

                print(f"  BUILD voice={voice.name} ({voice.id}) model={model.name} ({model.id}) ...", end=" ", flush=True)
                try:
                    resolved_voice = await get_voice_identity_by_public_id(db, voice.public_voice_id)
                    if resolved_voice is None:
                        print("FAIL (voice not found by public ID)")
                        total_errors += 1
                        continue

                    variant = await runtime.ensure_variant(db, voice=resolved_voice, model_id=model.id)
                    print(f"OK (status={variant.status})")
                    total_built += 1
                except ModelNotRegistered as e:
                    print(f"FAIL (model not registered: {e})")
                    total_errors += 1
                except Exception as e:
                    print(f"FAIL ({e})")
                    total_errors += 1

        await db.commit()

    await engine.dispose()

    print(f"\nSummary: {total_built} built, {total_skipped} skipped, {total_errors} errors")
    if dry_run:
        print("(dry run — no changes made)")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill missing VoiceVariants for all voices",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only display actions without making changes",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Only process models whose id or name contains this string",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    asyncio.run(backfill(dry_run=args.dry_run, model_filter=args.model))


if __name__ == "__main__":
    main()

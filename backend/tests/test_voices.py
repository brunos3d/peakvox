from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import get_db
from app.core.migrations import run_migrations
from app.models.db import VoiceProfile, VoiceSourceAsset
from app.api import voices as voices_api


@pytest.fixture
async def client(tmp_path):
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/voices.db", future=True)
    async with eng.begin() as conn:
        await run_migrations(conn)
    maker = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)

    async with maker() as session:
        now = datetime.now(timezone.utc)
        session.add(VoiceProfile(
            id="v-src",
            name="Has Source Asset",
            audio_filename="reference.wav",
            audio_duration=3.5,
            owner_id=settings.LOCAL_OWNER_ID,
            created_at=now,
        ))
        session.add(VoiceSourceAsset(
            voice_id="v-src",
            asset_type="reference_audio",
            storage_key="voices/v-src/reference.wav",
            original_filename="my-recording.wav",
            content_type="audio/wav",
            file_size=65536,
            audio_duration=3.5,
            created_at=now,
        ))
        session.add(VoiceProfile(
            id="v-no-src",
            name="No Source Asset",
            audio_filename="reference.wav",
            audio_duration=2.0,
            owner_id=settings.LOCAL_OWNER_ID,
            created_at=now,
        ))
        await session.commit()

    async def _override_get_db():
        async with maker() as s:
            yield s

    app = FastAPI()
    app.include_router(voices_api.router, prefix="/voices")
    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app)
    await eng.dispose()


def test_voice_detail_includes_source_asset(client):
    resp = client.get("/voices/v-src")
    assert resp.status_code == 200
    data = resp.json()
    assert data["source_asset"] is not None
    assert data["source_asset"]["original_filename"] == "my-recording.wav"
    assert data["source_asset"]["asset_type"] == "reference_audio"
    assert data["source_asset"]["audio_duration"] == 3.5
    assert data["source_asset"]["content_type"] == "audio/wav"
    assert data["source_asset"]["file_size"] == 65536
    assert data["source_asset"]["id"] is not None
    assert data["source_asset"]["created_at"] is not None


def test_voice_detail_missing_source_asset_is_none(client):
    resp = client.get("/voices/v-no-src")
    assert resp.status_code == 200
    data = resp.json()
    assert data["source_asset"] is None


def test_list_response_includes_source_asset(client):
    resp = client.get("/voices")
    assert resp.status_code == 200
    data = resp.json()
    by_id = {v["id"]: v for v in data}
    assert by_id["v-src"]["source_asset"] is not None
    assert by_id["v-no-src"]["source_asset"] is None


def test_page_response_includes_source_asset(client):
    resp = client.get("/voices/page")
    assert resp.status_code == 200
    data = resp.json()
    by_id = {v["id"]: v for v in data["items"]}
    assert by_id["v-src"]["source_asset"] is not None
    assert by_id["v-no-src"]["source_asset"] is None

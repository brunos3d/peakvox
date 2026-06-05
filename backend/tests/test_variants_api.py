import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api import variants as variants_api
from app.core.database import get_db
from app.core.migrations import run_migrations
from app.services.model_wiring import wire_registry, wire_runtime
from app.services.runtime import runtime

_SEED = (
    "INSERT INTO voice_profiles (id, public_voice_id, owner_id, name, audio_filename, "
    "transcript, generation_defaults, is_public, is_community_voice, is_preset_voice, "
    "is_favorite, status, usage_count, created_at, updated_at) "
    "VALUES ('uuid-1','voice_ABC123','owner-1','Bruno','voices/uuid-1/reference.wav',"
    "'olá','{}',0,0,0,0,'ready',0,'2026-01-01','2026-01-01')"
)


@pytest.fixture
async def client(tmp_path):
    wire_registry()
    wire_runtime()
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/api.db", future=True)
    async with eng.begin() as conn:
        await run_migrations(conn)
        await conn.execute(text(_SEED))
        await run_migrations(conn)
    maker = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_db():
        async with maker() as s:
            yield s

    app = FastAPI()
    app.include_router(variants_api.router, prefix="/voices")
    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app)
    await eng.dispose()
    runtime._adapters.clear()


def test_list_variants_after_backfill(client):
    resp = client.get("/voices/voice_ABC123/variants")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    omnivoice = [v for v in data if v["model_id"] == "omnivoice-base"]
    assert len(omnivoice) == 1
    assert omnivoice[0]["status"] == "ready"


def test_list_variants_voice_not_found(client):
    resp = client.get("/voices/nonexistent/variants")
    assert resp.status_code == 404


def test_get_variant_status_ready_after_backfill(client):
    resp = client.get("/voices/voice_ABC123/variants/omnivoice-base")
    assert resp.status_code == 200
    data = resp.json()
    assert data["model_id"] == "omnivoice-base"
    assert data["status"] == "ready"
    assert data["active_artifact_version"] == 1


def test_get_variant_status_model_not_found(client):
    resp = client.get("/voices/voice_ABC123/variants/nonexistent-model")
    assert resp.status_code == 404


def test_build_variant_creates_variant(client):
    resp = client.post("/voices/voice_ABC123/variants?model_id=omnivoice-base")
    assert resp.status_code == 201
    data = resp.json()
    assert data["model_id"] == "omnivoice-base"
    assert data["status"] == "ready"


def test_build_variant_is_idempotent(client):
    client.post("/voices/voice_ABC123/variants?model_id=omnivoice-base")
    resp = client.post("/voices/voice_ABC123/variants?model_id=omnivoice-base")
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "ready"


def test_build_variant_then_rollback_creates_artifacts(client):
    resp1 = client.post("/voices/voice_ABC123/variants?model_id=omnivoice-base")
    assert resp1.status_code == 201

    resp2 = client.post("/voices/voice_ABC123/variants/omnivoice-base/rebuild")
    assert resp2.status_code == 200
    assert resp2.json()["active_artifact_version"] == 2

    artifacts = client.get("/voices/voice_ABC123/variants/omnivoice-base/artifacts")
    assert artifacts.status_code == 200
    versions = artifacts.json()
    assert len(versions) == 2
    assert versions[0]["version"] == 1
    assert versions[-1]["version"] == 2
    assert versions[-1]["is_active"] is True

    resp3 = client.post("/voices/voice_ABC123/variants/omnivoice-base/rollback/1")
    assert resp3.status_code == 200
    assert resp3.json()["active_artifact_version"] == 1


def test_rebuild_singing_uses_canonical_from_backfill(client):
    resp = client.post("/voices/voice_ABC123/variants/omnivoice-singing/rebuild")
    assert resp.status_code == 200
    data = resp.json()
    assert data["model_id"] == "omnivoice-singing"
    assert data["status"] == "ready"


def test_rebuild_nonexistent_voice_returns_404(client):
    resp = client.post("/voices/nonexistent/variants/omnivoice-base/rebuild")
    assert resp.status_code == 404


def test_rollback_nonexistent_version(client):
    client.post("/voices/voice_ABC123/variants?model_id=omnivoice-base")
    resp = client.post("/voices/voice_ABC123/variants/omnivoice-base/rollback/99")
    assert resp.status_code == 404


def test_list_artifact_versions_backfill_creates_v1(client):
    resp = client.get("/voices/voice_ABC123/variants/omnivoice-base/artifacts")
    assert resp.status_code == 200
    versions = resp.json()
    assert len(versions) >= 1
    assert versions[0]["version"] == 1
    assert versions[0]["is_active"] is True


def test_build_without_model_id_uses_default(client):
    resp = client.post("/voices/voice_ABC123/variants")
    assert resp.status_code == 201
    data = resp.json()
    assert data["model_id"] is not None


def test_voice_not_found_on_build(client):
    resp = client.post("/voices/nonexistent/variants?model_id=omnivoice-base")
    assert resp.status_code == 404

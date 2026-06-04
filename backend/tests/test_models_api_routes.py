import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api import models as models_api
from app.core.database import get_db
from app.core.migrations import run_migrations
from app.services.model_wiring import wire_registry


@pytest.fixture
async def client(tmp_path):
    wire_registry()
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/routes.db", future=True)
    async with eng.begin() as conn:
        await run_migrations(conn)
    maker = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_db():
        async with maker() as s:
            yield s

    app = FastAPI()
    app.include_router(models_api.router)
    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app)
    await eng.dispose()


def test_models_payload_includes_availability_and_capabilities(client):
    body = client.get("/models").json()
    fish = next(m for m in body["models"] if m["id"] == "fish-audio-s2")
    assert fish["available_in_ce"] is True
    assert fish["available_in_cloud"] is False
    assert fish["repository_url"] == "https://github.com/fishaudio/fish-speech"
    assert fish["license_name"] == "Fish Audio Research License"
    assert fish["install_status"] == "not_installed"
    assert fish["capabilities"]["supports_voice_cloning"] is True


def test_api_models_alias_uses_same_payload(client):
    assert client.get("/api/models").json() == client.get("/models").json()


def test_install_then_remove_builtin_via_routes(client):
    # CE: writes enabled. Install fish (disabled -> inactive), activate, then remove (-> disabled).
    r = client.post("/models/fish-audio-s2/install")
    assert r.status_code == 200 and r.json()["status"] == "inactive"
    fish = next(m for m in client.get("/models").json()["models"] if m["id"] == "fish-audio-s2")
    assert fish["install_status"] == "installed"
    assert fish["activation_status"] == "inactive"

    r = client.post("/models/fish-audio-s2/activate")
    assert r.status_code == 200 and r.json()["status"] == "available"
    fish = next(m for m in client.get("/models").json()["models"] if m["id"] == "fish-audio-s2")
    assert fish["activation_status"] == "active"

    r = client.post("/models/fish-audio-s2/deactivate")
    assert r.status_code == 200 and r.json()["status"] == "inactive"
    fish = next(m for m in client.get("/models").json()["models"] if m["id"] == "fish-audio-s2")
    assert fish["activation_status"] == "inactive"

    r = client.post("/models/fish-audio-s2/remove")
    assert r.status_code == 200 and r.json()["removed"] is True
    fish = next(m for m in client.get("/models").json()["models"] if m["id"] == "fish-audio-s2")
    assert fish["status"] == "disabled"
    assert fish["install_status"] == "not_installed"


def test_install_unknown_model_404(client):
    assert client.post("/models/ghost/install").status_code == 404


def test_writes_blocked_in_cloud_edition(client, monkeypatch):
    from app.core import config as config_module
    monkeypatch.setattr(config_module.settings, "EDITION", "cloud")
    assert client.post("/models/fish-audio-s2/install").status_code == 403

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from app.api.provider_voices import router as provider_voices_router
from app.services.provider_voice import ProviderVoice, build_provider_voice_id


@pytest.fixture
def app():
    _app = FastAPI()
    _app.include_router(provider_voices_router)
    return _app


@pytest.fixture
def preset_voices():
    """Register known presets for testing."""
    from app.services.runtime import runtime
    voices = [
        ProviderVoice(
            provider_voice_id=build_provider_voice_id("kokoro", "af_heart"),
            provider_id="kokoro", external_id="af_heart", name="Heart",
            language="en-us", gender="female",
        ),
        ProviderVoice(
            provider_voice_id=build_provider_voice_id("kokoro", "am_adam"),
            provider_id="kokoro", external_id="am_adam", name="Adam",
            language="en-us", gender="male",
        ),
        ProviderVoice(
            provider_voice_id=build_provider_voice_id("kokoro", "ff_siwis"),
            provider_id="kokoro", external_id="ff_siwis", name="Siwis",
            language="fr", gender="female",
        ),
    ]
    runtime._provider_voice_registry.register_many(voices)
    yield
    runtime._provider_voice_registry.remove_provider("kokoro")


@pytest.mark.asyncio
async def test_list_provider_voices_returns_all(app, preset_voices):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/provider-voices")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 3


@pytest.mark.asyncio
async def test_list_provider_voices_filters_by_provider(app, preset_voices):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/provider-voices?provider=kokoro")
    assert resp.status_code == 200
    data = resp.json()
    assert all(v["provider_id"] == "kokoro" for v in data)


@pytest.mark.asyncio
async def test_list_provider_voices_filters_by_language(app, preset_voices):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/provider-voices?language=fr")
    assert resp.status_code == 200
    data = resp.json()
    assert all(v["language"] == "fr" for v in data)


@pytest.mark.asyncio
async def test_list_provider_voices_filters_by_gender(app, preset_voices):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/provider-voices?gender=male")
    assert resp.status_code == 200
    data = resp.json()
    assert all(v["gender"] == "male" for v in data)


@pytest.mark.asyncio
async def test_list_provider_voices_search(app, preset_voices):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/provider-voices?search=heart")
    assert resp.status_code == 200
    data = resp.json()
    assert any("Heart" in v["name"] for v in data)


@pytest.mark.asyncio
async def test_get_provider_voice_by_id(app, preset_voices):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/provider-voices/{build_provider_voice_id('kokoro', 'af_heart')}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Heart"
    assert data["provider_id"] == "kokoro"


@pytest.mark.asyncio
async def test_get_provider_voice_not_found(app, preset_voices):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/provider-voices/nonexistent")
    assert resp.status_code == 404

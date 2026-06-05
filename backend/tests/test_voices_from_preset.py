import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.migrations import run_migrations
from app.api.voices import router as voices_router
from app.services.provider_voice import ProviderVoice, build_provider_voice_id
from app.models.registry_types import ModelCapabilities, ModelDescriptor
from app.services.model_adapter import ModelAdapter


class FakeCatalogAdapter(ModelAdapter):
    def __init__(self, descriptor):
        super().__init__(descriptor)
    async def install(self): ...
    async def load(self): ...
    def unload(self): ...
    async def health_check(self) -> bool: return True
    async def generate(self, *, text, output_path, **kwargs):
        return (2.0, [])
    async def clone_voice(self, *, db, voice, reference_audio_key):
        raise NotImplementedError
    async def build_variant(self, *, db, voice):
        raise NotImplementedError
    def list_provider_voices(self):
        return [ProviderVoice(
            provider_voice_id=build_provider_voice_id("kokoro", "af_heart"),
            provider_id="kokoro", external_id="af_heart", name="Heart",
            language="en-us", gender="female",
        )]
    def get_provider_voice(self, external_id):
        return self.list_provider_voices()[0] if external_id == "af_heart" else None
    def has_provider_voice(self, external_id):
        return external_id == "af_heart"


@pytest.fixture(autouse=True)
def setup_runtime():
    """Ensure the runtime has a catalog adapter registered."""
    from app.services.runtime import runtime
    desc = ModelDescriptor(
        id="kokoro-base", name="Kokoro", description="d", provider="kokoro",
        capabilities=ModelCapabilities(supports_tts=True),
    )
    runtime.register_adapter(FakeCatalogAdapter(desc))
    yield
    runtime._adapters.pop("kokoro-base", None)
    runtime._provider_voice_registry.remove_provider("kokoro")


@pytest.fixture
async def client(tmp_path):
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/preset.db", future=True)
    async with eng.begin() as conn:
        await run_migrations(conn)
    maker = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_db():
        async with maker() as s:
            yield s

    app = FastAPI()
    app.include_router(voices_router, prefix="/voices")
    app.dependency_overrides[get_db] = _override_get_db

    from httpx import AsyncClient, ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    await eng.dispose()


@pytest.mark.asyncio
async def test_create_voice_from_preset_returns_profile(client):
    resp = await client.post("/voices/from-preset", json={
        "provider": "kokoro",
        "preset_name": "af_heart",
        "name": "My Heart",
        "model_id": "kokoro-base",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Heart"
    assert data["creation_source"] == "PRESET_VOICE"
    assert data["is_preset_voice"] is True
    assert "public_voice_id" in data


@pytest.mark.asyncio
async def test_create_voice_from_unknown_preset_returns_404(client):
    resp = await client.post("/voices/from-preset", json={
        "provider": "kokoro",
        "preset_name": "nonexistent",
        "name": "Nope",
        "model_id": "kokoro-base",
    })
    assert resp.status_code == 404

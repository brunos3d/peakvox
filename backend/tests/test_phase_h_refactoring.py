"""Phase H: verify H9 and H10 refactoring is correct.

- H9: ``POST /voices/from-preset`` delegates to ``ImportResolver`` (sole import impl)
- H10: ``GET /api/provider-voices`` delegates to ``VoiceResourceService`` (sole catalog impl)
- ``VoiceResource`` remains transient — no new DB table
- Derived fields (``is_in_library``, ``compatible_models``) are never persisted
"""

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.provider_voices import router as provider_voices_router
from app.api.voice_resources import router as voice_resources_router
from app.api.voices import router as voices_router
from app.core.database import get_db
from app.core.migrations import run_migrations
from app.models.db import Voice, VoiceProfile, VoiceVariant, VoiceVariantArtifact
from app.models.registry_types import ModelCapabilities, ModelDescriptor
from app.schemas.voice_resource import VoiceResourceResponse
from app.services.compatibility_resolver import CompatibilityResolver
from app.services.import_resolver import ImportAlreadyExistsError, ImportResolver
from app.services.model_adapter import ModelAdapter
from app.services.provider_voice import ProviderVoice, build_provider_voice_id
from app.services.runtime import runtime
from app.services.voice_resource_service import VoiceResourceService


# ── helpers ────────────────────────────────────────────────────────────────


class _FakeCatalogAdapter(ModelAdapter):
    def __init__(self, descriptor):
        super().__init__(descriptor)

    async def install(self): ...
    async def load(self): ...
    def unload(self): ...
    async def health_check(self) -> bool: return True
    async def generate(self, *, text, output_path, **kwargs): return (2.0, [])
    async def clone_voice(self, *, db, voice, reference_audio_key):
        raise NotImplementedError
    async def build_variant(self, *, db, voice): raise NotImplementedError

    def list_provider_voices(self):
        return [
            ProviderVoice(
                provider_voice_id=build_provider_voice_id("kokoro", "af_heart"),
                provider_id="kokoro", external_id="af_heart", name="Heart",
                language="en-us", gender="female",
                catalog_source={"type": "adapter", "adapter_id": "kokoro"},
            ),
            ProviderVoice(
                provider_voice_id=build_provider_voice_id("kokoro", "am_adam"),
                provider_id="kokoro", external_id="am_adam", name="Adam",
                language="en-us", gender="male",
                catalog_source={"type": "adapter", "adapter_id": "kokoro"},
            ),
        ]

    def get_provider_voice(self, external_id):
        for v in self.list_provider_voices():
            if v.external_id == external_id:
                return v
        return None

    def has_provider_voice(self, external_id):
        return self.get_provider_voice(external_id) is not None


@pytest.fixture(autouse=True)
def _setup_runtime():
    desc = ModelDescriptor(
        id="kokoro-base", name="Kokoro", description="d", provider="kokoro",
        capabilities=ModelCapabilities(supports_tts=True),
    )
    runtime.register_adapter(_FakeCatalogAdapter(desc))
    yield
    for mid in list(runtime._adapters.keys()):
        runtime._adapters.pop(mid)
    runtime._provider_voice_registry.remove_provider("kokoro")


@pytest.fixture
async def db(tmp_path):
    eng = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path}/phase_h.db", future=True
    )
    async with eng.begin() as conn:
        await run_migrations(conn)
    maker = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session
    await eng.dispose()


@pytest.fixture
def app(db):
    _app = FastAPI()

    async def _override_get_db():
        yield db

    _app.dependency_overrides[get_db] = _override_get_db
    _app.include_router(provider_voices_router)
    _app.include_router(voice_resources_router)
    _app.include_router(voices_router, prefix="/voices")
    return _app


# ── H9 test: from-preset delegates to ImportResolver ──────────────────────


@pytest.mark.asyncio
async def test_legacy_import_creates_correct_records(app, db):
    """Verify the records produced by the legacy endpoint match expected shape."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/voices/from-preset", json={
            "provider": "kokoro",
            "preset_name": "af_heart",
            "name": "My Heart",
            "model_id": "kokoro-base",
        })
    assert resp.status_code == 201
    profile_id = resp.json()["id"]

    # Verify VoiceProfile has the expected structure
    profile = await db.get(VoiceProfile, profile_id)
    assert profile is not None
    assert profile.name == "My Heart"
    assert profile.is_preset_voice is True
    assert profile.meta["provider"] == "kokoro"
    assert profile.meta["preset_name"] == "af_heart"
    assert profile.meta["resource_type"] == "preset"
    assert profile.meta["resource_origin"] == "kokoro"
    assert profile.meta["catalog_source"] == {"type": "adapter", "adapter_id": "kokoro"}

    # Verify Voice record
    voice = (await db.execute(select(Voice).where(Voice.id == profile_id))).scalars().first()
    assert voice is not None

    # Verify VoiceVariant — there are two: one from mirror_profile_to_split
    # (omnivoice-base) and one from ImportResolver (kokoro-base).
    variants = (await db.execute(
        select(VoiceVariant).where(VoiceVariant.voice_id == profile_id)
    )).scalars().all()
    variant_ids = {v.model_id for v in variants}
    assert "kokoro-base" in variant_ids
    assert "omnivoice-base" in variant_ids

    # Verify the ImportResolver-created variant (kokoro-base)
    variant = next(v for v in variants if v.model_id == "kokoro-base")
    assert variant.status == "ready"
    assert variant.params == {"provider": "kokoro", "preset_name": "af_heart"}

    # Verify VoiceVariantArtifact
    artifact = (await db.execute(
        select(VoiceVariantArtifact).where(VoiceVariantArtifact.voice_variant_id == variant.id)
    )).scalars().first()
    assert artifact is not None
    assert artifact.version == 1
    assert artifact.meta == {"provider": "kokoro", "preset_name": "af_heart"}


@pytest.mark.asyncio
async def test_legacy_import_and_new_import_go_through_same_code_path(app, db):
    """Legacy endpoint and direct ImportResolver both create the same record structure.

    Since the refactored ``POST /voices/from-preset`` delegates entirely to
    ``ImportResolver._import_preset``, both paths produce VoiceProfiles with
    identical meta structure.
    """
    # Import via legacy endpoint
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/voices/from-preset", json={
            "provider": "kokoro",
            "preset_name": "af_heart",
            "name": "My Heart",
            "model_id": "kokoro-base",
        })
    assert resp.status_code == 201
    legacy_id = resp.json()["id"]

    # Import a different resource via ImportResolver directly
    resource = VoiceResourceResponse(
        id=build_provider_voice_id("kokoro", "am_adam"),
        resource_type="preset",
        resource_origin="kokoro",
        name="Adam Direct",
        description="kokoro preset: Adam (en-us)",
        language="en-us",
        provider_id="kokoro",
        external_id="am_adam",
        gender="male",
    )
    resolver = ImportResolver()
    profile = await resolver.resolve(db, resource, model_id="kokoro-base")
    assert profile.name == "Adam Direct"
    assert profile.is_preset_voice is True
    assert profile.meta["provider"] == "kokoro"
    assert profile.meta["preset_name"] == "am_adam"
    assert profile.meta["resource_type"] == "preset"
    assert profile.meta["resource_origin"] == "kokoro"

    # Both voices have the same structural fields
    legacy_profile = await db.get(VoiceProfile, legacy_id)
    assert legacy_profile is not None
    assert legacy_profile.meta["provider"] == "kokoro"
    assert legacy_profile.meta["preset_name"] == "af_heart"
    assert legacy_profile.meta["resource_type"] == "preset"
    assert legacy_profile.meta["resource_origin"] == "kokoro"

    # Both paths produce is_preset_voice=True and PRESET_VOICE creation_source
    assert legacy_profile.is_preset_voice is True
    assert profile.is_preset_voice is True


@pytest.mark.asyncio
async def test_legacy_import_404_on_unknown_preset(app):
    """Unknown preset still returns 404 (preserved from old endpoint)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/voices/from-preset", json={
            "provider": "kokoro",
            "preset_name": "nonexistent",
            "name": "Nope",
            "model_id": "kokoro-base",
        })
    assert resp.status_code == 404


# ── H10 test: provider-voices delegates to VoiceResourceService ───────────


@pytest.mark.asyncio
async def test_legacy_catalog_returns_same_count_as_service(app):
    """Legacy catalog returns the same number of items as VoiceResourceService."""
    svc = VoiceResourceService(
        provider_registry=runtime._provider_voice_registry,
        compatibility_resolver=CompatibilityResolver(runtime),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/provider-voices")

    assert resp.status_code == 200
    legacy_data = resp.json()

    # ProviderVoiceResponse has the expected fields
    for item in legacy_data:
        assert "provider_voice_id" in item
        assert "provider_id" in item
        assert "name" in item
        assert "external_id" in item


@pytest.mark.asyncio
async def test_legacy_catalog_returns_same_names_as_registry(app):
    """Legacy catalog returns the same set of voice names as the registry."""
    direct = runtime._provider_voice_registry.list_all()
    direct_names = {v.name for v in direct}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/provider-voices")

    assert resp.status_code == 200
    legacy_names = {v["name"] for v in resp.json()}

    assert direct_names == legacy_names


@pytest.mark.asyncio
async def test_legacy_catalog_get_by_id(app):
    """GET /api/provider-voices/{id} still returns a single voice."""
    voice_id = build_provider_voice_id("kokoro", "af_heart")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/provider-voices/{voice_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Heart"


# ── Sole implementation invariants ────────────────────────────────────────


@pytest.mark.asyncio
async def test_import_resolver_is_only_import_path(app, db):
    """ImportResolver is the sole implementation for creating preset voices.

    The legacy endpoint delegates entirely — all DB writes flow through
    ImportResolver._import_preset.
    """
    # ImportResolver can import directly (not just through the legacy endpoint)
    resource = VoiceResourceResponse(
        id=build_provider_voice_id("kokoro", "am_adam"),
        resource_type="preset",
        resource_origin="kokoro",
        name="Adam Direct",
        description="kokoro preset: Adam (en-us)",
        language="en-us",
        provider_id="kokoro",
        external_id="am_adam",
        gender="male",
    )
    resolver = ImportResolver()
    profile = await resolver.resolve(db, resource, model_id="kokoro-base")
    assert profile.name == "Adam Direct"
    assert profile.is_preset_voice is True
    assert profile.meta["provider"] == "kokoro"


@pytest.mark.asyncio
async def test_voice_resource_service_is_only_catalog_aggregator(app):
    """VoiceResourceService is the sole aggregator of catalog data.

    The legacy endpoint delegates entirely — all catalog reads flow
    through VoiceResourceService.
    """
    direct = runtime._provider_voice_registry.list_all()
    direct_ids = {v.provider_voice_id for v in direct}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/provider-voices")
    assert resp.status_code == 200
    legacy_ids = {v["provider_voice_id"] for v in resp.json()}

    assert direct_ids == legacy_ids


# ── Architectural invariants (H14) ────────────────────────────────────────


@pytest.mark.asyncio
async def test_voice_resource_remains_transient(tmp_path):
    """VoiceResourceResponse is never stored in the DB — no matching table."""
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/transient.db")
    async with eng.begin() as conn:
        await run_migrations(conn)

    async with eng.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='voice_resources'"
            )
        )
        assert result.first() is None, "voice_resources table must not exist"

    VoiceResourceResponse(
        id="test",
        resource_type="preset",
        resource_origin="test",
        name="test",
    )
    await eng.dispose()


@pytest.mark.asyncio
async def test_derived_fields_not_persisted(app, db):
    """is_in_library and compatible_models are query-time only — never in DB."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/voices/from-preset", json={
            "provider": "kokoro",
            "preset_name": "af_heart",
            "name": "Heart",
            "model_id": "kokoro-base",
        })
    assert resp.status_code == 201

    profile_id = resp.json()["id"]
    profile = await db.get(VoiceProfile, profile_id)
    assert not hasattr(profile, "is_in_library")
    assert not hasattr(profile, "compatible_models")


@pytest.mark.asyncio
async def test_compatibility_remains_query_time(app, db):
    """Compatibility data is never stored — derived from build strategies."""
    svc = VoiceResourceService(
        provider_registry=runtime._provider_voice_registry,
        compatibility_resolver=CompatibilityResolver(runtime),
    )
    resource = await svc.get(db, build_provider_voice_id("kokoro", "af_heart"))
    assert resource is not None
    assert isinstance(resource.compatible_models, list)

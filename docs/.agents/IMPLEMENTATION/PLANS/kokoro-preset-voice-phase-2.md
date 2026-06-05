# Kokoro Preset Voice Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make preset voices first-class Voice entities that participate in the full Voice → VoiceVariant → VoiceVariantArtifact → Generation lifecycle.

**Architecture:** ProviderVoiceRegistry becomes catalog-only (no generation resolution). `runtime.generate()` has a single DB-based resolution path. `KokoroAdapter.build_variant()` creates metadata-only variants. `POST /voices/from-preset` materializes presets into the DB. `GET /api/provider-voices` exposes the catalog to the frontend.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, React/Next.js, Radix UI Tabs

---

## File Structure

### New files
- `backend/app/api/provider_voices.py` — GET /api/provider-voices and /{provider_voice_id}
- `backend/app/schemas/provider_voice.py` — request/response schemas for provider-voices API
- `backend/tests/test_provider_voices_api.py` — tests for provider-voices API
- `backend/tests/test_voices_from_preset.py` — tests for from-preset endpoint
- `backend/tests/test_runtime_single_path.py` — tests for single-path generation
- `frontend/src/components/voice/PresetVoicesTab.tsx` — preset voices tab content
- `frontend/src/components/voice/PresetVoiceCard.tsx` — preset voice card component

### Modified files
- `backend/app/services/runtime.py` — remove two-tier resolution; pass variant params as kwargs
- `backend/app/services/model_adapters/kokoro_adapter.py` — build_variant returns metadata variant
- `backend/app/api/voices.py` — add POST /voices/from-preset
- `backend/app/main.py` — register provider_voices router
- `backend/app/services/provider_voice.py` — no changes (catalog-only confirmed)
- `backend/tests/test_runtime_provider_voice.py` — update/remove registry-path tests
- `backend/tests/test_kokoro_adapter.py` — update build_variant test
- `frontend/src/app/voices/page.tsx` — add Preset Voices tab
- `frontend/src/hooks/use-generation.ts` — enable preset scope
- `frontend/src/lib/api.ts` — add preset API functions
- `frontend/src/types/index.ts` — add ProviderVoiceResponse type

---

### Task A1: Remove two-tier resolution from runtime.generate()

**Files:**
- Modify: `backend/app/services/runtime.py:412-447`
- Test: `backend/tests/test_runtime_provider_voice.py`
- Test: `backend/tests/test_runtime_single_path.py`

- [ ] **Step 1: Write the failing test — single path always resolves through DB**

Create `backend/tests/test_runtime_single_path.py`:

```python
from pathlib import Path
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)
from app.core.migrations import run_migrations
from app.models.registry_types import ModelCapabilities, ModelDescriptor
from app.services.model_adapter import ModelAdapter
from app.services.provider_voice import (
    ProviderVoice, ProviderVoiceCatalog, build_provider_voice_id,
)
from app.services.runtime import PeakVoxRuntime, ModelNotRegistered, VoiceNotFound

class TrackingAdapter(ModelAdapter):
    def __init__(self, descriptor):
        super().__init__(descriptor)
        self.captured_kwargs: dict = {}
    async def install(self): ...
    async def load(self): ...
    def unload(self): ...
    async def health_check(self) -> bool: return True
    async def generate(self, *, text, output_path, **kwargs):
        self.captured_kwargs = kwargs
        return (2.0, [f"{self.model_id}:{text}"])
    async def clone_voice(self, *, db, voice, reference_audio_key):
        raise NotImplementedError
    async def build_variant(self, *, db, voice):
        raise NotImplementedError

def _desc(model_id, *, default=False, caps=None):
    return ModelDescriptor(
        id=model_id, name=model_id, description="d", provider="fake",
        supported_tags=[], is_default=default,
        capabilities=caps or ModelCapabilities(),
    )

_SEED = (
    "INSERT INTO voice_profiles (id, public_voice_id, owner_id, name, audio_filename, "
    "transcript, generation_defaults, is_public, is_community_voice, is_preset_voice, "
    "is_favorite, status, usage_count, created_at, updated_at) "
    "VALUES ('uuid-1','voice_ABC123','owner-1','Test','','{}',0,0,0,0,'ready',0,"
    "'2026-01-01','2026-01-01')"
)

@pytest.fixture
async def session(tmp_path):
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/single_path.db", future=True)
    async with eng.begin() as conn:
        await run_migrations(conn)
        await conn.execute(text(_SEED))
        await run_migrations(conn)
    maker = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await eng.dispose()

def test_provider_voice_id_no_longer_resolves_without_db_record():
    """ProviderVoiceRegistry does NOT participate in generation resolution."""
    rt = PeakVoxRuntime()
    # Register an adapter that also provides presets.
    voices = [ProviderVoice(
        provider_voice_id=build_provider_voice_id("test", "v1"),
        provider_id="test", external_id="v1", name="V1",
    )]
    adapter = TrackingAdapter(_desc("test-model", default=True, caps=ModelCapabilities(supports_tts=True)))
    adapter.list_provider_voices = lambda: voices
    adapter.get_provider_voice = lambda eid: voices[0] if eid == "v1" else None
    # Manually register in catalog (simulating what register_adapter does)
    rt.register_adapter(adapter)
    # Registry has the voice, but generate() should NOT use it — goes to DB
    with pytest.raises(VoiceNotFound):
        import anyio
        anyio.run(
            rt.generate, None, text="hi", model_id="test-model",
            voice_id=build_provider_voice_id("test", "v1"),
            output_path=Path("/tmp/x.wav"),
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/bruno/Desktop/omnivoice-app/backend && .venv/bin/python -m pytest tests/test_runtime_single_path.py -v 2>&1 | tail -10`

Expected: The test might pass depending on current behavior — if so, it means the current two-tier resolution catches it. Wait, actually the current code DOES resolve via registry first, so passing `voice_id=voice_kokoro_af_heart` would succeed. The test EXPECTS VoiceNotFound. So this test SHOULD fail with the current code.

- [ ] **Step 3: Write the passing test — variant params flow through to adapter**

Add to `test_runtime_single_path.py`:

```python
async def test_variant_params_flow_through_to_adapter(session):
    """Variant params are passed as kwargs to adapter.generate()."""
    from app.services.runtime import runtime as global_runtime
    # We need a Voice + VoiceVariant in the DB. Use the seed.
    # First ensure the DB has a variant with params.
    from app.models.db import Voice, VoiceVariant
    voice = await session.get(Voice, "uuid-1")
    if voice is None:
        # Create Voice for seed profile
        voice = Voice(
            id="uuid-1", public_voice_id="voice_ABC123",
            owner_id="owner-1", name="Test",
            creation_source="SOURCE_ASSET", status="ready",
        )
        session.add(voice)
        await session.commit()
    
    # Ensure a variant with params exists
    from app.models.db import VoiceVariant as VV
    variant = VV(
        voice_id="uuid-1", model_id="test-model",
        params={"provider": "kokoro", "preset_name": "af_heart"},
        artifacts={}, status="ready", source="preset",
    )
    session.add(variant)
    await session.commit()
    
    rt = PeakVoxRuntime()
    adapter = TrackingAdapter(_desc("test-model", default=True, caps=ModelCapabilities(supports_tts=True)))
    rt.register_adapter(adapter)
    
    await rt.generate(
        db=session, text="hello", model_id="test-model",
        public_voice_id="voice_ABC123", output_path=Path("/tmp/x.wav"),
    )
    # Variant params should be in kwargs
    assert adapter.captured_kwargs.get("provider") == "kokoro"
    assert adapter.captured_kwargs.get("preset_name") == "af_heart"
```

- [ ] **Step 4: Implement the single-path resolution**

Edit `backend/app/services/runtime.py:412-447`. Replace the two-tier block:

```python
        # Single voice resolution path: always resolve through DB.
        if public_voice_id is not None:
            resolution = await self.resolve(
                db, public_voice_id=public_voice_id, model_id=descriptor.id
            )
            artifacts = resolution.variant.artifacts or {}
            variant_params = resolution.variant.params or {}
            ref_audio_path = ref_audio_path or artifacts.get("audio")
            ref_text = ref_text if ref_text is not None else variant_params.get("transcript")
            voice_id = voice_id or resolution.voice.id
            voice_profile_id = voice_profile_id or resolution.voice.id
            resolved_voice_id = voice_id or voice_profile_id
        else:
            resolved_voice_id = voice_id or voice_profile_id
        
        # Merge variant params into generate kwargs so adapters can read
        # provider/preset_name for preset voices.
        gen_kwargs = dict(params or {})
        if variant_params:
            gen_kwargs.update(variant_params)
        if params:
            gen_kwargs.update(params)

        return await adapter.generate(
            text=text,
            output_path=output_path,
            voice_profile_id=resolved_voice_id,
            ref_audio_path=ref_audio_path,
            ref_text=ref_text,
            language=language,
            instruct=instruct,
            params=params,
            job_id=job_id,
            **gen_kwargs,
        )
```

Need to add `variant_params` initialization above the if block:
```python
        variant_params: dict = {}
```

- [ ] **Step 5: Run all tests to verify**

Run: `cd /home/bruno/Desktop/omnivoice-app/backend && .venv/bin/python -m pytest tests/test_runtime_single_path.py tests/test_runtime.py tests/test_runtime_provider_voice.py -v 2>&1 | tail -20`

Expected: New tests pass. Some old tests in test_runtime_provider_voice.py may fail because they relied on the two-tier resolution (e.g., `test_generate_with_provider_voice_resolves_via_registry`).

- [ ] **Step 6: Update existing tests that relied on registry resolution**

In `test_runtime_provider_voice.py`:
- Remove or update `test_generate_with_provider_voice_resolves_via_registry` (no longer valid)
- Remove `test_provider_voice_takes_priority_over_persisted_voice` (no longer valid)
- Remove `test_generate_provider_voice_does_not_touch_db` (no longer valid — now needs DB)
- Keep: `test_runtime_has_provider_voice_registry`, `test_register_provider_voice_delegates_to_registry`, 
  `test_list_provider_voices_*`, `test_register_adapter_auto_populates_*`
- Keep: `test_generate_with_public_voice_id_still_uses_db_path`

- [ ] **Step 7: Commit**

```bash
cd /home/bruno/Desktop/omnivoice-app && git add backend/app/services/runtime.py backend/tests/test_runtime_single_path.py backend/tests/test_runtime_provider_voice.py && git commit -m "refactor(runtime): remove two-tier resolution, single DB path for all voices

- ProviderVoiceRegistry is now catalog-only (no generation resolution)
- runtime.generate() always resolves through Voice → VoiceVariant → Artifact
- Variant params (provider/preset_name) flow as kwargs to adapter.generate()
- Catalog listing/list_provider_voices methods unchanged"
```

---

### Task A2: Implement KokoroAdapter.build_variant()

**Files:**
- Modify: `backend/app/services/model_adapters/kokoro_adapter.py:242-243`
- Test: `backend/tests/test_kokoro_adapter.py`

- [ ] **Step 1: Write the failing test**

In `test_kokoro_adapter.py`, replace the `test_build_variant_raises_not_implemented` test:

```python
async def test_build_variant_creates_metadata_variant(db_session):
    adapter = _adapter()
    voice = Voice(
        id="preset-voice-1", public_voice_id="voice_preset_1",
        owner_id="owner", name="Heart",
        meta={"provider": "kokoro", "preset_name": "af_heart"},
        creation_source="PRESET_VOICE", status="ready",
    )
    db_session.add(voice)
    await db_session.commit()
    
    variant = await adapter.build_variant(db=db_session, voice=voice)
    
    assert variant is not None
    assert variant.status == "ready"
    assert variant.params == {"provider": "kokoro", "preset_name": "af_heart"}
    assert variant.artifacts == {}
    assert variant.source == "preset"
    assert variant.artifact_type == "voice_pack"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/bruno/Desktop/omnivoice-app/backend && .venv/bin/python -m pytest tests/test_kokoro_adapter.py::test_build_variant_creates_metadata_variant -v 2>&1 | tail -5`

- [ ] **Step 3: Implement KokoroAdapter.build_variant()**

Replace the `build_variant` method in `kokoro_adapter.py`:

```python
from app.models.db import Voice, VoiceVariant
from sqlalchemy import select

async def build_variant(self, *, db, voice):
    """Create a metadata-only VoiceVariant for the Kokoro preset.
    
    Kokoro presets require no audio processing, no embedding generation,
    no checkpoint creation. The variant exists to satisfy ADR-0008 lifecycle
    contract — all providers participate in Voice → Variant → Artifact → Generation.
    
    The preset name is read from voice.meta (set by POST /voices/from-preset).
    """
    from app.models.db import VoiceVariant as VV
    from sqlalchemy import select as _select
    
    existing = (
        await db.execute(
            _select(VV).where(
                VV.voice_id == voice.id,
                VV.model_id == self.model_id,
            )
        )
    ).scalars().first()
    
    if existing is not None:
        return existing
    
    meta = voice.meta or {}
    import uuid
    
    variant = VV(
        id=str(uuid.uuid4()),
        voice_id=voice.id,
        model_id=self.model_id,
        artifact_type="voice_pack",
        params={"provider": meta.get("provider", "kokoro"),
                "preset_name": meta.get("preset_name", "")},
        artifacts={},
        source="preset",
        status="pending",
    )
    db.add(variant)
    await db.commit()
    await db.refresh(variant)
    return variant
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/bruno/Desktop/omnivoice-app/backend && .venv/bin/python -m pytest tests/test_kokoro_adapter.py::test_build_variant_creates_metadata_variant -v 2>&1 | tail -5`

- [ ] **Step 5: Add import for uuid at top of file**

Add `import uuid` to the imports in `kokoro_adapter.py`.

- [ ] **Step 6: Commit**

```bash
cd /home/bruno/Desktop/omnivoice-app && git add backend/app/services/model_adapters/kokoro_adapter.py backend/tests/test_kokoro_adapter.py && git commit -m "feat(kokoro): implement build_variant as metadata-only variant creation

- KokoroAdapter.build_variant() creates VoiceVariant with params={provider, preset_name}
- No audio processing, no embedding, no checkpoint
- status=pending (runtime marks ready after artifact versioning)
- All providers now participate identically in ADR-0008 lifecycle"
```

---

### Task A3: GET /api/provider-voices endpoint + schema

**Files:**
- Create: `backend/app/schemas/provider_voice.py`
- Create: `backend/app/api/provider_voices.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_provider_voices_api.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_provider_voices_api.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.provider_voice import ProviderVoice, build_provider_voice_id

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
    # Cleanup
    runtime._provider_voice_registry.remove_provider("kokoro")

@pytest.mark.asyncio
async def test_list_provider_voices_returns_all(preset_voices):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/provider-voices")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 3

@pytest.mark.asyncio
async def test_list_provider_voices_filters_by_provider(preset_voices):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/provider-voices?provider=kokoro")
    assert resp.status_code == 200
    data = resp.json()
    assert all(v["provider_id"] == "kokoro" for v in data)

@pytest.mark.asyncio
async def test_list_provider_voices_filters_by_language(preset_voices):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/provider-voices?language=fr")
    assert resp.status_code == 200
    data = resp.json()
    assert all(v["language"] == "fr" for v in data)

@pytest.mark.asyncio
async def test_list_provider_voices_filters_by_gender(preset_voices):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/provider-voices?gender=male")
    assert resp.status_code == 200
    data = resp.json()
    assert all(v["gender"] == "male" for v in data)

@pytest.mark.asyncio
async def test_list_provider_voices_search(preset_voices):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/provider-voices?search=heart")
    assert resp.status_code == 200
    data = resp.json()
    assert any("Heart" in v["name"] for v in data)
```

- [ ] **Step 2: Run tests to verify they fail (404 router not registered)**

- [ ] **Step 3: Create the response schema**

`backend/app/schemas/provider_voice.py`:

```python
from typing import Optional
from pydantic import BaseModel


class ProviderVoiceResponse(BaseModel):
    provider_voice_id: str
    provider_id: str
    external_id: str
    name: str
    description: str = ""
    language: Optional[str] = None
    gender: Optional[str] = None
    is_default: bool = False
```

- [ ] **Step 4: Create the endpoint**

`backend/app/api/provider_voices.py`:

```python
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException

from app.schemas.provider_voice import ProviderVoiceResponse
from app.services.runtime import runtime

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/provider-voices", response_model=list[ProviderVoiceResponse])
async def list_provider_voices(
    provider: Optional[str] = None,
    language: Optional[str] = None,
    gender: Optional[str] = None,
    search: Optional[str] = None,
):
    voices = runtime._provider_voice_registry.search(
        query=search or "",
        provider_id=provider,
        language=language,
        gender=gender,
    )
    return [
        ProviderVoiceResponse(
            provider_voice_id=v.provider_voice_id,
            provider_id=v.provider_id,
            external_id=v.external_id,
            name=v.name,
            description=v.description,
            language=v.language,
            gender=v.gender,
            is_default=v.is_default,
        )
        for v in voices
    ]


@router.get("/api/provider-voices/{provider_voice_id}", response_model=ProviderVoiceResponse)
async def get_provider_voice(provider_voice_id: str):
    voice = runtime._provider_voice_registry.get(provider_voice_id)
    if voice is None:
        raise HTTPException(status_code=404, detail="Provider voice not found")
    return ProviderVoiceResponse(
        provider_voice_id=voice.provider_voice_id,
        provider_id=voice.provider_id,
        external_id=voice.external_id,
        name=voice.name,
        description=voice.description,
        language=voice.language,
        gender=voice.gender,
        is_default=voice.is_default,
    )
```

- [ ] **Step 5: Register the router in main.py**

Add to `backend/app/main.py` near the other router registrations:

```python
from app.api.provider_voices import router as provider_voices_router
# ...
app.include_router(provider_voices_router, tags=["Provider Voices"])
```

- [ ] **Step 6: Run tests**

Run: `cd /home/bruno/Desktop/omnivoice-app/backend && .venv/bin/python -m pytest tests/test_provider_voices_api.py -v 2>&1 | tail -15`

- [ ] **Step 7: Commit**

```bash
cd /home/bruno/Desktop/omnivoice-app && git add backend/app/schemas/provider_voice.py backend/app/api/provider_voices.py backend/app/main.py backend/tests/test_provider_voices_api.py && git commit -m "feat(api): add /api/provider-voices catalog endpoint

- GET /api/provider-voices lists/search/filters presets from ProviderVoiceRegistry
- GET /api/provider-voices/{id} returns single preset detail
- ProviderVoiceResponse schema (snake_case, internal API)
- Router registered in main.py"
```

---

### Task A4: POST /voices/from-preset endpoint

**Files:**
- Modify: `backend/app/api/voices.py`
- Create: `backend/tests/test_voices_from_preset.py`

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_voices_from_preset.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)
from app.core.migrations import run_migrations
from app.main import app
from app.services.runtime import runtime
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
    desc = ModelDescriptor(
        id="kokoro-base", name="Kokoro", description="d", provider="kokoro",
        capabilities=ModelCapabilities(supports_tts=True),
    )
    runtime.register_adapter(FakeCatalogAdapter(desc))
    yield
    # Cleanup
    runtime._adapters.pop("kokoro-base", None)
    runtime._provider_voice_registry.remove_provider("kokoro")

@pytest.fixture
async def db_session(tmp_path):
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/preset.db", future=True)
    async with eng.begin() as conn:
        await run_migrations(conn)
    maker = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await eng.dispose()

@pytest.mark.asyncio
async def test_create_voice_from_preset_returns_profile(db_session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
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
async def test_create_voice_from_preset_creates_variant(db_session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/voices/from-preset", json={
            "provider": "kokoro",
            "preset_name": "af_heart",
            "name": "Heart",
            "model_id": "kokoro-base",
        })
    assert resp.status_code == 201
    voice_id = resp.json()["id"]
    
    # Verify Voice + VoiceVariant + VoiceVariantArtifact exist
    from app.models.db import Voice, VoiceVariant, VoiceVariantArtifact
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        voice = await db.get(Voice, voice_id)
        assert voice is not None
        assert voice.creation_source == "PRESET_VOICE"
        assert voice.meta == {"provider": "kokoro", "preset_name": "af_heart"}
        
        from sqlalchemy import select
        variant = (await db.execute(
            select(VoiceVariant).where(VoiceVariant.voice_id == voice_id)
        )).scalars().first()
        assert variant is not None
        assert variant.params == {"provider": "kokoro", "preset_name": "af_heart"}
        assert variant.status == "ready"
        
        artifact = (await db.execute(
            select(VoiceVariantArtifact).where(
                VoiceVariantArtifact.voice_variant_id == variant.id
            )
        )).scalars().first()
        assert artifact is not None
        assert artifact.version == 1

@pytest.mark.asyncio
async def test_create_voice_from_unknown_preset_returns_404(db_session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/voices/from-preset", json={
            "provider": "kokoro",
            "preset_name": "nonexistent",
            "name": "Nope",
            "model_id": "kokoro-base",
        })
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Create the request schema and endpoint**

Add to `backend/app/schemas/provider_voice.py`:

```python
class CreateFromPresetRequest(BaseModel):
    provider: str
    preset_name: str
    name: str
    model_id: str
```

Add the endpoint to `backend/app/api/voices.py`:

```python
import uuid
from datetime import datetime, timezone

from app.schemas.provider_voice import CreateFromPresetRequest
from app.models.db import Voice, VoiceVariant, VoiceVariantArtifact
from app.services.runtime import runtime
from app.services.provider_voice import build_provider_voice_id


@router.post("/from-preset", response_model=VoiceProfileResponse, status_code=201)
async def create_voice_from_preset(
    body: CreateFromPresetRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a first-class Voice from a provider preset.
    
    Materializes a provider preset into the full Voice → VoiceVariant → 
    VoiceVariantArtifact lifecycle so it appears in My Voices and can be
    generated through the standard path.
    """
    # Validate preset exists in catalog
    provider_voice_id = build_provider_voice_id(body.provider, body.preset_name)
    provider_voice = runtime._provider_voice_registry.get(provider_voice_id)
    if provider_voice is None:
        raise HTTPException(
            status_code=404,
            detail=f"Preset '{body.preset_name}' not found for provider '{body.provider}'",
        )
    
    now = datetime.now(timezone.utc)
    profile_id = str(uuid.uuid4())
    public_id = f"voice_{uuid.uuid4().hex[:10].upper()}"
    
    # 1. Create VoiceProfile (frontend API compatibility)
    profile = VoiceProfile(
        id=profile_id,
        public_voice_id=public_id,
        name=body.name,
        description=f"{body.provider} preset: {provider_voice.name} ({provider_voice.language or ''})",
        language=provider_voice.language,
        language_code=provider_voice.language,
        transcript="",
        audio_filename="",
        audio_duration=0.0,
        is_preset_voice=True,
        owner_id=settings.LOCAL_OWNER_ID,
        meta={"provider": body.provider, "preset_name": body.preset_name},
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    
    # 2. Mirror to split Voice table with PRESET_VOICE creation_source
    await mirror_profile_to_split(db, profile)
    
    # 3. Create VoiceVariant (ready status)
    from sqlalchemy import select
    voice = (await db.execute(
        select(Voice).where(Voice.id == profile_id)
    )).scalars().first()
    
    variant = VoiceVariant(
        id=str(uuid.uuid4()),
        voice_id=voice.id,
        model_id=body.model_id,
        artifact_type="voice_pack",
        params={"provider": body.provider, "preset_name": body.preset_name},
        artifacts={},
        source="preset",
        status="ready",
    )
    db.add(variant)
    await db.commit()
    await db.refresh(variant)
    
    # 4. Create VoiceVariantArtifact (version 1, metadata-only)
    artifact = VoiceVariantArtifact(
        id=str(uuid.uuid4()),
        voice_variant_id=variant.id,
        version=1,
        storage_keys={},
        meta={"provider": body.provider, "preset_name": body.preset_name},
    )
    db.add(artifact)
    await db.commit()
    
    logger.info("Created preset voice %s (%s/%s)", profile_id, body.provider, body.preset_name)
    return profile
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/bruno/Desktop/omnivoice-app/backend && .venv/bin/python -m pytest tests/test_voices_from_preset.py -v 2>&1 | tail -15`

- [ ] **Step 5: Commit**

```bash
cd /home/bruno/Desktop/omnivoice-app && git add backend/app/api/voices.py backend/app/schemas/provider_voice.py backend/tests/test_voices_from_preset.py && git commit -m "feat(api): add POST /voices/from-preset endpoint

- Materializes a provider preset into Voice + VoiceVariant + VoiceVariantArtifact
- creation_source='PRESET_VOICE' on Voice record
- Validates preset exists in ProviderVoiceRegistry first
- Returns VoiceProfileResponse for frontend compatibility"
```

---

### Task B5–B7: Frontend

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/src/components/voice/PresetVoicesTab.tsx`
- Modify: `frontend/src/app/voices/page.tsx`
- Modify: `frontend/src/hooks/use-generation.ts`

- [ ] **Step 1: Add frontend types**

In `frontend/src/types/index.ts`:

```typescript
export interface ProviderVoiceResponse {
  provider_voice_id: string
  provider_id: string
  external_id: string
  name: string
  description: string
  language: string | null
  gender: string | null
  is_default: boolean
}

export interface CreateFromPresetRequest {
  provider: string
  preset_name: string
  name: string
  model_id: string
}
```

- [ ] **Step 2: Add API functions**

In `frontend/src/lib/api.ts`:

```typescript
export async function fetchProviderVoices(params?: {
  provider?: string
  language?: string
  gender?: string
  search?: string
}): Promise<ProviderVoiceResponse[]> {
  const qs = new URLSearchParams()
  if (params?.provider) qs.set("provider", params.provider)
  if (params?.language) qs.set("language", params.language)
  if (params?.gender) qs.set("gender", params.gender)
  if (params?.search) qs.set("search", params.search)
  const query = qs.toString()
  return request<ProviderVoiceResponse[]>(`/api/provider-voices${query ? `?${query}` : ""}`)
}

export async function fetchProviderVoice(id: string): Promise<ProviderVoiceResponse> {
  return request<ProviderVoiceResponse>(`/api/provider-voices/${id}`)
}

export async function createVoiceFromPreset(data: CreateFromPresetRequest): Promise<VoiceProfile> {
  return request<VoiceProfile>("/voices/from-preset", {
    method: "POST",
    body: JSON.stringify(data),
  })
}
```

- [ ] **Step 3: Create PresetVoicesTab component**

`frontend/src/components/voice/PresetVoicesTab.tsx`:

```typescript
"use client"

import { useState, useEffect, useMemo } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { fetchProviderVoices, createVoiceFromPreset } from "@/lib/api"
import type { ProviderVoiceResponse, CreateFromPresetRequest } from "@/types"
import { useStore } from "@/store/use-store"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { Loader2, Plus, Play } from "lucide-react"
import { useRouter } from "next/navigation"

interface PresetVoicesTabProps {
  onScopeChange?: (scope: string) => void
}

export function PresetVoicesTab({ onScopeChange }: PresetVoicesTabProps) {
  const [provider, setProvider] = useState<string>("")
  const [language, setLanguage] = useState<string>("")
  const [gender, setGender] = useState<string>("")
  const [search, setSearch] = useState<string>("")

  const { data: voices, isLoading } = useQuery({
    queryKey: ["provider-voices", provider, language, gender, search],
    queryFn: () => fetchProviderVoices({ provider, language, gender, search }),
  })

  // Extract unique providers, languages, genders for filter dropdowns
  const providers = useMemo(() => {
    if (!voices) return []
    return [...new Set(voices.map((v) => v.provider_id))].sort()
  }, [voices])

  const languages = useMemo(() => {
    if (!voices) return []
    return [...new Set(voices.map((v) => v.language).filter(Boolean))].sort()
  }, [voices])

  const genders = useMemo(() => {
    if (!voices) return []
    return [...new Set(voices.map((v) => v.gender).filter(Boolean))].sort()
  }, [voices])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div>
      <div className="flex gap-2 mb-4 flex-wrap">
        <Select value={provider} onValueChange={setProvider}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="All Providers" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All Providers</SelectItem>
            {providers.map((p) => (
              <SelectItem key={p} value={p}>{p}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={language} onValueChange={setLanguage}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="All Languages" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All Languages</SelectItem>
            {languages.map((l) => (
              <SelectItem key={l} value={l}>{l}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={gender} onValueChange={setGender}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="All Genders" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All Genders</SelectItem>
            {genders.map((g) => (
              <SelectItem key={g} value={g}>{g}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Input
          placeholder="Search presets..."
          className="w-48"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {(!voices || voices.length === 0) ? (
        <div className="text-center py-16 text-muted-foreground">
          No preset voices found
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {voices.map((voice) => (
            <PresetVoiceCard key={voice.provider_voice_id} voice={voice} onScopeChange={onScopeChange} />
          ))}
        </div>
      )}
    </div>
  )
}

function PresetVoiceCard({ voice, onScopeChange }: { voice: ProviderVoiceResponse; onScopeChange?: (scope: string) => void }) {
  const queryClient = useQueryClient()
  const router = useRouter()
  const { setSelectedProfile } = useStore()
  const [isAdding, setIsAdding] = useState(false)

  const addToLibrary = async (useNow: boolean) => {
    setIsAdding(true)
    try {
      const profile = await createVoiceFromPreset({
        provider: voice.provider_id,
        preset_name: voice.external_id,
        name: `${voice.name} (${voice.provider_id})`,
        model_id: `${voice.provider_id}-base`,
      })
      // Invalidate My Voices query
      queryClient.invalidateQueries({ queryKey: ["voices-page"] })
      
      if (useNow) {
        setSelectedProfile(profile)
        router.push("/")  // Navigate to TTS page
      } else if (onScopeChange) {
        onScopeChange("mine")  // Switch to My Voices tab
      }
    } finally {
      setIsAdding(false)
    }
  }

  return (
    <div className="border border-border rounded-lg p-4 hover:border-primary/50 transition-colors">
      <div className="font-semibold text-sm truncate">{voice.name}</div>
      <div className="text-xs text-muted-foreground mt-1 space-y-0.5">
        <div>{voice.provider_id} · {voice.language ?? "unknown"} · {voice.gender ?? "unknown"}</div>
        {voice.description && <div className="truncate">{voice.description}</div>}
      </div>
      <div className="flex gap-2 mt-3">
        <Button
          size="sm"
          variant="default"
          className="flex-1 gap-1"
          onClick={() => addToLibrary(true)}
          disabled={isAdding}
        >
          {isAdding ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
          Use Now
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="flex-1 gap-1"
          onClick={() => addToLibrary(false)}
          disabled={isAdding}
        >
          {isAdding ? <Loader2 className="h-3 w-3 animate-spin" /> : <Plus className="h-3 w-3" />}
          Library
        </Button>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Update the Voice Library page**

In `frontend/src/app/voices/page.tsx`:

Replace the `TABS` array:
```typescript
const TABS: { value: VoiceScope; label: string }[] = [
  { value: "mine", label: "My Voices" },
  { value: "preset", label: "Preset Voices" },
]
```

Add import and render logic for the PresetVoicesTab when `scope === "preset"`.

- [ ] **Step 5: Enable preset scope in useVoicesPage hook**

In `frontend/src/hooks/use-generation.ts`, change the `enabled` condition:
```typescript
enabled: scope === "mine" || scope === "recent" || scope === "preset",
```

- [ ] **Step 6: Commit**

```bash
cd /home/bruno/Desktop/omnivoice-app && git add frontend/src/types/index.ts frontend/src/lib/api.ts frontend/src/components/voice/PresetVoicesTab.tsx frontend/src/app/voices/page.tsx frontend/src/hooks/use-generation.ts && git commit -m "feat(ui): add Preset Voices tab to Voice Library

- PresetVoicesTab with provider/language/gender/search filters
- PresetVoiceCard with "Use Now" and "+ Library" actions
- "Use Now" creates Voice from preset, selects it, routes to TTS
- "+ Library" creates Voice and switches to My Voices tab
- New API functions: fetchProviderVoices, createVoiceFromPreset"
```

---

### Task C8: Run full suite + update state files + final commit

- [ ] **Step 1: Run full test suite**

Run: `cd /home/bruno/Desktop/omnivoice-app/backend && .venv/bin/python -m pytest tests/ --ignore=tests/test_voices.py -v 2>&1 | tail -20`

Expected: All tests green.

- [ ] **Step 2: Update VALIDATION.md**

`docs/.agents/SPECS/FEATURES/kokoro-preset-voice-adapter/VALIDATION.md` — add Phase 2 results.

- [ ] **Step 3: Update STATUS.md**

Set `IMPLEMENTED` for Phase 2.

- [ ] **Step 4: Update IMPLEMENTATION_STATUS.md** — add Phase 2 rows

- [ ] **Step 5: Update EXECUTION_LEDGER.md** — append Phase 2 entry

- [ ] **Step 6: Update HANDOFF.md** — current session

- [ ] **Step 7: Final commit**

```bash
cd /home/bruno/Desktop/omnivoice-app && git add docs/.agents/SPECS/FEATURES/kokoro-preset-voice-adapter/ docs/.agents/IMPLEMENTATION_STATUS.md docs/.agents/IMPLEMENTATION/EXECUTION_HISTORY/EXECUTION_LEDGER.md docs/.agents/HANDOFF.md && git commit -m "docs: update state files for Kokoro Phase 2 completion"
```

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.core.editions import mount_cloud_routers
from app.api import voices, generation, health, media, models, platform
from app.api.settings import router as settings_router
from app.api.api_keys import router as api_keys_router
from app.api.v1 import router as v1_router
from app.services.model_registry import model_registry
from app.services.model_wiring import wire_registry
from app.services.storage import storage
from app.services.migration import run_migration

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s", settings.APP_NAME)
    settings.create_dirs()
    await init_db()
    storage.ensure_bucket()
    await run_migration()
    # Wire the model registry (descriptors + provider factories) and warm the default model.
    wire_registry()
    default_id = model_registry.resolve_default().id
    asyncio.create_task(model_registry.ensure_loaded(default_id))
    yield
    logger.info("Shutting down")


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["System"])
app.include_router(platform.router, tags=["Platform"])
app.include_router(models.router, tags=["Models"])
app.include_router(media.router, tags=["Media"])
app.include_router(voices.router, prefix="/voices", tags=["Voices"])
app.include_router(generation.router, prefix="", tags=["Generation"])
app.include_router(settings_router, prefix="", tags=["Settings"])
app.include_router(api_keys_router, prefix="/api-keys", tags=["API Keys"])
app.include_router(v1_router, prefix="/api/v1", tags=["Public API v1"])

# Cloud-only routers mount only under cloud features; a no-op in Community Edition.
mount_cloud_routers(app, features=settings.features)

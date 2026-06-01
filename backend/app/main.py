import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import init_db
from app.api import voices, generation, health
from app.api.settings import router as settings_router
from app.services.omnivoice_service import omnivoice_service

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s", settings.APP_NAME)
    settings.create_dirs()
    await init_db()
    asyncio.create_task(omnivoice_service.load_model())
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

app.mount(
    "/audio",
    StaticFiles(directory=str(settings.GENERATED_DIR)),
    name="generated_audio",
)

app.include_router(health.router, tags=["System"])
app.include_router(voices.router, prefix="/voices", tags=["Voices"])
app.include_router(generation.router, prefix="", tags=["Generation"])
app.include_router(settings_router, prefix="", tags=["Settings"])

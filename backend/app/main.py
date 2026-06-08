import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.database import AsyncSessionLocal, init_db
from app.core.editions import mount_cloud_routers
from app.api import voices, generation, health, media, models, platform, variants
from app.api.variants_summary import router as variants_summary_router
from app.api.provider_voices import router as provider_voices_router
from app.api.voice_resources import router as voice_resources_router
from app.api.settings import router as settings_router
from app.api.api_keys import router as api_keys_router
from app.api.v1 import router as v1_router
from app.services.model_registry import model_registry
from app.services.model_wiring import wire_registry_from_database, wire_runtime
from app.services.runtime_wiring import start_idle_reaper, stop_idle_reaper, wire_runtime_services
from app.services.storage import storage
from app.services.migration import run_migration

logger = logging.getLogger(__name__)


def _categorize(status: int, hint: str) -> str:
    """Server-side category hint for the frontend error dialog. Mirrors the
    client-side `categorizeError` in lib/api-error.ts so the two stay in sync.
    """
    lower = hint.lower()
    if status == 404:
        if "voice" in lower:
            return "voice_not_found"
        if "model" in lower:
            return "model_loading"
        return "not_found"
    if status == 409:
        if "variant" in lower:
            return "model_loading"
        if "loading" in lower:
            return "model_loading"
        if "cuda" in lower or "oom" in lower or "out of memory" in lower:
            return "cuda_out_of_memory"
        if "gpu" in lower:
            return "gpu_unavailable"
        return "conflict"
    if status == 422:
        return "validation"
    if status == 429:
        return "rate_limited"
    if status == 503:
        if "loading" in lower:
            return "model_loading"
        return "backend_unavailable"
    if status == 504:
        return "generation_timeout"
    if status >= 500:
        if "cuda" in lower or "oom" in lower or "out of memory" in lower:
            return "cuda_out_of_memory"
        if "model" in lower:
            return "model_loading"
        if "voice" in lower:
            return "voice_not_found"
        return "internal_server"
    return "unknown"


def _enrich(status: int, message: str, extra: dict | None = None) -> dict:
    """Build the structured ``detail`` payload the frontend parses."""
    request_id = uuid.uuid4().hex[:12]
    detail: dict = {
        "message": message,
        "category": _categorize(status, message),
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        detail.update(extra)
    return detail


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s", settings.APP_NAME)
    settings.create_dirs()
    await init_db()
    storage.ensure_bucket()
    await run_migration()
    # Wire the model registry (persisted descriptors + provider factories), the PeakVox Runtime
    # (model adapters), and warm the default model.
    async with AsyncSessionLocal() as session:
        await wire_registry_from_database(session)
    wire_runtime()
    default_id = model_registry.resolve_default().id
    asyncio.create_task(model_registry.ensure_loaded(default_id))

    # Phase 3: wire the runtime subsystem (R3, R6, R7).
    #
    # Gated on Settings.RUNTIME_SERVICE_ENABLED. When the flag is
    # False (CE default), the runtime subsystem is not constructed
    # and the in-process adapter path is the only path. When the
    # flag is True, the registry is loaded, the driver is built,
    # the manager is attached to PeakVoxRuntime, and the idle
    # reaper background task is started. NO runtime container is
    # started at boot (R6 — lazy activation).
    runtime_manager = wire_runtime_services(settings)
    idle_reaper_task = await start_idle_reaper(runtime_manager)

    try:
        yield
    finally:
        await stop_idle_reaper(idle_reaper_task)
        logger.info("Shutting down")


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Structured error responses ------------------------------------------------
# Every error path goes through one of these handlers so the frontend can
# parse a stable ``detail`` shape: ``{ message, category, request_id, timestamp }``
# (plus endpoint-specific extras). The frontend categorises any error that
# arrives without a ``category`` field using the same heuristic defined below.

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    request_id = uuid.uuid4().hex[:12]
    # Preserve a dict detail (existing 422s ship a richer payload) but rewrap
    # the message + add the new metadata.
    if isinstance(exc.detail, dict) and "message" in exc.detail:
        message = str(exc.detail.get("message", ""))
        extra = {k: v for k, v in exc.detail.items() if k != "message"}
        detail = _enrich(exc.status_code, message, extra)
    else:
        message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        detail = _enrich(exc.status_code, message)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": detail},
        headers={"x-request-id": request_id},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = uuid.uuid4().hex[:12]
    message = "Request validation failed"
    detail = _enrich(
        422,
        message,
        {"errors": exc.errors()},
    )
    return JSONResponse(
        status_code=422,
        content={"detail": detail},
        headers={"x-request-id": request_id},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = uuid.uuid4().hex[:12]
    # Log with full traceback so the dev-mode panel can show the same source.
    logger.exception("Unhandled exception in %s %s", request.method, request.url.path)
    detail = _enrich(
        500,
        f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__,
        {"error_class": type(exc).__name__},
    )
    return JSONResponse(
        status_code=500,
        content={"detail": detail},
        headers={"x-request-id": request_id},
    )

app.include_router(health.router, tags=["System"])
app.include_router(platform.router, tags=["Platform"])
app.include_router(models.router, tags=["Models"])
app.include_router(media.router, tags=["Media"])
app.include_router(voices.router, prefix="/voices", tags=["Voices"])
app.include_router(variants.router, prefix="/voices", tags=["Variants"])
app.include_router(variants_summary_router, tags=["Variants"])
app.include_router(generation.router, prefix="", tags=["Generation"])
app.include_router(settings_router, prefix="", tags=["Settings"])
app.include_router(api_keys_router, prefix="/api-keys", tags=["API Keys"])
app.include_router(v1_router, prefix="/api/v1", tags=["Public API v1"])
app.include_router(provider_voices_router, tags=["Provider Voices"])
app.include_router(voice_resources_router, tags=["Voice Resources"])

# Cloud-only routers mount only under cloud features; a no-op in Community Edition.
mount_cloud_routers(app, features=settings.features)

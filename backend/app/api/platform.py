"""Platform metadata for the frontend — edition + active feature flags.

Torch-free and dependency-light so the UI can discover, at runtime, which surfaces to render.
Community Edition reports every commercial flag as false; the frontend hides marketplace /
creator / billing nav accordingly (docs/architecture/01-PRODUCT_ARCHITECTURE.md §4).
"""

from dataclasses import asdict

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/platform/features")
async def get_platform_features():
    return {
        "name": settings.APP_NAME,
        "edition": settings.EDITION,
        "features": asdict(settings.features),
    }

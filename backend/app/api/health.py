import logging

from fastapi import APIRouter

from app.core.config import settings
from app.services.model_registry import model_registry

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "model_loaded": model_registry.resident_model_id is not None,
        "model_loading": False,
        "model_error": None,
    }

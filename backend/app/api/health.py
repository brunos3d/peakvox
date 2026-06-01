import logging

from fastapi import APIRouter

from app.core.config import settings
from app.services.omnivoice_service import omnivoice_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "model_loaded": omnivoice_service.is_loaded,
        "model_loading": omnivoice_service.is_loading,
        "model_error": omnivoice_service.load_error,
    }


@router.get("/models/status")
async def model_status():
    return {
        "loaded": omnivoice_service.is_loaded,
        "loading": omnivoice_service.is_loading,
        "error": omnivoice_service.load_error,
        "sampling_rate": omnivoice_service.sampling_rate,
    }

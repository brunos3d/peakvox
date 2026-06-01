import logging

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.omnivoice_service import omnivoice_service

logger = logging.getLogger(__name__)
router = APIRouter()


class DeviceSettings(BaseModel):
    use_gpu: bool


@router.get("/settings/device")
async def get_device_settings():
    return {
        "use_gpu": omnivoice_service.use_gpu,
        "cuda_available": __import__("torch").cuda.is_available(),
    }


@router.patch("/settings/device")
async def set_device_settings(body: DeviceSettings):
    omnivoice_service.use_gpu = body.use_gpu
    logger.info("Device preference set to: %s", "GPU" if body.use_gpu else "CPU")
    return {
        "use_gpu": omnivoice_service.use_gpu,
        "cuda_available": __import__("torch").cuda.is_available(),
    }

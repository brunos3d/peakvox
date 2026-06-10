import subprocess
import logging
from fastapi import APIRouter, HTTPException
from app.schemas.settings import DeviceSettings
from app.services.settings_service import get_device_settings, save_device_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settings")

def check_cuda_available() -> bool:
    """Check if NVIDIA GPU and drivers are available on the host."""
    try:
        # Check for nvidia-smi
        subprocess.run(["nvidia-smi"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

@router.get("/device", response_model=DeviceSettings)
async def get_device():
    saved = get_device_settings()
    cuda = check_cuda_available()
    use_gpu = saved.get("use_gpu", True)
    
    return DeviceSettings(
        use_gpu=use_gpu,
        cuda_available=cuda,
        gpu_available=cuda,
        device="cuda" if cuda and use_gpu else "cpu"
    )

@router.patch("/device", response_model=DeviceSettings)
async def update_device(update: dict):
    if "use_gpu" not in update:
        raise HTTPException(status_code=400, detail="Missing use_gpu field")
    
    save_device_settings({"use_gpu": update["use_gpu"]})
    return await get_device()

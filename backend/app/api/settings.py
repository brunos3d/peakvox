import subprocess
import logging
from fastapi import APIRouter, HTTPException
from app.schemas.settings import (
    DeviceSettings,
    HuggingFaceStatus,
    HuggingFaceTokenUpdate,
)
from app.services.settings_service import (
    get_device_settings,
    save_device_settings,
    huggingface_configured,
    save_huggingface_token,
    delete_huggingface_token,
)

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


@router.get("/huggingface", response_model=HuggingFaceStatus)
async def get_huggingface():
    """Return whether a Hugging Face token is configured (never the token)."""
    return HuggingFaceStatus(configured=huggingface_configured())


@router.put("/huggingface", response_model=HuggingFaceStatus)
async def put_huggingface(update: HuggingFaceTokenUpdate):
    """Save / update the Hugging Face token. The token is never echoed back."""
    if not update.token or not update.token.strip():
        raise HTTPException(status_code=400, detail="Token must not be empty")
    save_huggingface_token(update.token)
    return HuggingFaceStatus(configured=True)


@router.delete("/huggingface", response_model=HuggingFaceStatus)
async def remove_huggingface():
    """Remove the stored Hugging Face token."""
    delete_huggingface_token()
    return HuggingFaceStatus(configured=False)

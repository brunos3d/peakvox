from pydantic import BaseModel

class DeviceSettings(BaseModel):
    use_gpu: bool = True
    cuda_available: bool = False
    device: str = "cpu"
    gpu_available: bool = False


class HuggingFaceStatus(BaseModel):
    """Presence-only view of the Hugging Face token. Never carries the token."""
    configured: bool = False


class HuggingFaceTokenUpdate(BaseModel):
    """Request body for saving/updating the Hugging Face token."""
    token: str

from pydantic import BaseModel

class DeviceSettings(BaseModel):
    use_gpu: bool = True
    cuda_available: bool = False
    device: str = "cpu"
    gpu_available: bool = False

"""Provider adapter for OmniVoice-family models (Base, Distilled).

Delegates to the existing :data:`omnivoice_service` singleton so the proven inference path is
preserved verbatim (plan Risk R-6). torch/omnivoice are imported lazily by the service, so
this module stays import-safe without a GPU stack — but it is only instantiated by the
registry at load time, never at import.
"""

import logging
from pathlib import Path
from typing import Optional

from app.models.registry_types import ModelDescriptor
from app.services.model_providers.base import ModelProvider
from app.services.omnivoice_service import omnivoice_service

logger = logging.getLogger(__name__)


class OmniVoiceProvider(ModelProvider):
    def __init__(self) -> None:
        self._loaded_model_id: Optional[str] = None

    async def load(self, descriptor: ModelDescriptor) -> None:
        await omnivoice_service.load_model(repo_id=descriptor.repo_id)
        if omnivoice_service.load_error:
            self._loaded_model_id = None
            raise RuntimeError(omnivoice_service.load_error)
        self._loaded_model_id = descriptor.id

    def offload(self) -> None:
        omnivoice_service.offload()

    @property
    def is_loaded(self) -> bool:
        return omnivoice_service.is_loaded and self._loaded_model_id is not None

    @property
    def loaded_model_id(self) -> Optional[str]:
        return self._loaded_model_id

    async def generate(
        self,
        *,
        descriptor: ModelDescriptor,
        text: str,
        output_path: Path,
        voice_profile_id: Optional[str] = None,
        ref_audio_path: Optional[str] = None,
        ref_text: Optional[str] = None,
        language: Optional[str] = None,
        instruct: Optional[str] = None,
        params: Optional[dict] = None,
        job_id: Optional[str] = None,
    ) -> tuple[float, list[str]]:
        p = params or {}
        return await omnivoice_service.generate_async(
            text=text,
            output_path=output_path,
            voice_profile_id=voice_profile_id,
            ref_audio_path=ref_audio_path,
            ref_text=ref_text,
            language=language,
            instruct=instruct,
            num_step=p.get("num_step", 32),
            guidance_scale=p.get("guidance_scale", 2.0),
            speed=p.get("speed"),
            duration=p.get("duration"),
            t_shift=p.get("t_shift", 0.1),
            denoise=p.get("denoise", True),
            job_id=job_id,
        )

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

import numpy as np
import torch

from app.core.config import settings
from app.utils.audio import save_numpy_as_wav

logger = logging.getLogger(__name__)


class OmniVoiceService:
    """Singleton that wraps the OmniVoice model, offloading to CPU when idle."""

    _instance: Optional["OmniVoiceService"] = None

    def __init__(self) -> None:
        self._model = None
        self._device: str = "cpu"
        self._use_gpu: bool = True
        self._loading: bool = False
        self._loaded: bool = False
        self._load_error: Optional[str] = None
        self._voice_prompt_cache: dict = {}

    @classmethod
    def get_instance(cls) -> "OmniVoiceService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Device preference
    # ------------------------------------------------------------------

    @property
    def use_gpu(self) -> bool:
        return self._use_gpu

    @use_gpu.setter
    def use_gpu(self, value: bool) -> None:
        self._use_gpu = value
        if not value and torch.cuda.is_available():
            self._offload_to_cpu()

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def _do_load(self) -> None:
        os.environ["HF_HOME"] = str(settings.HF_HOME)
        os.makedirs(settings.HF_HOME, exist_ok=True)

        from omnivoice import OmniVoice
        from omnivoice.utils.common import get_best_device

        self._device = get_best_device()
        dtype = torch.float16 if self._device in ("cuda", "xpu") else torch.float32

        logger.info(f"Loading OmniVoice model '{settings.OMNIVOICE_MODEL}' ({dtype})")
        self._model = OmniVoice.from_pretrained(
            settings.OMNIVOICE_MODEL,
            device_map=self._device,
            dtype=dtype,
            load_asr=settings.LOAD_ASR,
            asr_model_name=settings.ASR_MODEL,
        )

        if torch.cuda.is_available():
            self._model.to("cpu")
            torch.cuda.empty_cache()
            logger.info("Offloaded model to CPU — GPU is free until generation")

        logger.info("OmniVoice model loaded successfully")

    async def load_model(self) -> None:
        if self._loaded or self._loading:
            return
        self._loading = True
        try:
            await asyncio.to_thread(self._do_load)
            self._loaded = True
        except Exception as exc:
            self._load_error = str(exc)
            logger.error(f"OmniVoice model load failed: {exc}")
        finally:
            self._loading = False

    # ------------------------------------------------------------------
    # GPU management
    # ------------------------------------------------------------------

    def _ensure_on_gpu(self) -> None:
        if not self._use_gpu or self._device != "cuda" or self._model is None:
            return
        try:
            p = next(self._model.parameters())
            if p.device.type != "cuda":
                logger.debug("Moving model to GPU")
                self._model.to("cuda")
                torch.cuda.empty_cache()
        except StopIteration:
            pass

    def _offload_to_cpu(self) -> None:
        if self._model is None:
            return
        try:
            p = next(self._model.parameters())
            if p.device.type == "cuda":
                logger.debug("Offloading model to CPU")
                self._model.to("cpu")
                torch.cuda.empty_cache()
        except StopIteration:
            pass

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def is_loading(self) -> bool:
        return self._loading

    @property
    def load_error(self) -> Optional[str]:
        return self._load_error

    @property
    def sampling_rate(self) -> int:
        if self._model is not None:
            return self._model.sampling_rate
        return 24000

    # ------------------------------------------------------------------
    # Voice clone prompt caching
    # ------------------------------------------------------------------

    def get_or_create_voice_prompt(
        self,
        voice_id: str,
        ref_audio_path: str,
        ref_text: Optional[str] = None,
    ):
        if voice_id in self._voice_prompt_cache:
            return self._voice_prompt_cache[voice_id]

        self._ensure_on_gpu()
        prompt = self._model.create_voice_clone_prompt(
            ref_audio=ref_audio_path,
            ref_text=ref_text or None,
        )
        self._voice_prompt_cache[voice_id] = prompt
        return prompt

    def invalidate_voice_cache(self, voice_id: str) -> None:
        self._voice_prompt_cache.pop(voice_id, None)

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def _do_generate(
        self,
        text: str,
        voice_profile_id: Optional[str],
        ref_audio_path: Optional[str],
        ref_text: Optional[str],
        language: Optional[str],
        instruct: Optional[str],
        num_step: int,
        guidance_scale: float,
        speed: Optional[float],
        duration: Optional[float],
        t_shift: float,
        denoise: bool,
        output_path: Path,
    ) -> tuple[float, list[str]]:
        from omnivoice import OmniVoiceGenerationConfig

        logs: list[str] = []

        self._ensure_on_gpu()
        if self._use_gpu and self._device == "cuda":
            logs.append("Using GPU for generation")
        else:
            logs.append("Using CPU for generation")

        gen_config = OmniVoiceGenerationConfig(
            num_step=num_step,
            guidance_scale=guidance_scale,
            t_shift=t_shift,
            denoise=denoise,
        )

        voice_clone_prompt = None

        if voice_profile_id and ref_audio_path:
            logs.append(f"Extracting voice clone prompt for profile {voice_profile_id}")
            voice_clone_prompt = self.get_or_create_voice_prompt(
                voice_id=voice_profile_id,
                ref_audio_path=ref_audio_path,
                ref_text=ref_text,
            )
        elif ref_audio_path and not voice_profile_id:
            logs.append("Extracting voice clone prompt from uploaded audio")
            self._ensure_on_gpu()
            voice_clone_prompt = self._model.create_voice_clone_prompt(
                ref_audio=ref_audio_path,
                ref_text=ref_text or None,
            )

        logs.append(f"Generating speech ({num_step} steps, guidance={guidance_scale})")

        audios: list[np.ndarray] = self._model.generate(
            text=text,
            language=language or None,
            voice_clone_prompt=voice_clone_prompt,
            instruct=instruct or None,
            duration=duration,
            speed=speed,
            generation_config=gen_config,
        )

        audio = audios[0]
        audio_duration = save_numpy_as_wav(audio, output_path, self._model.sampling_rate)
        logs.append(f"Generated {audio_duration:.2f}s of audio -> {output_path.name}")

        self._offload_to_cpu()
        if self._use_gpu and self._device == "cuda" and torch.cuda.is_available():
            logs.append("Offloaded model to CPU -> GPU memory freed")

        return audio_duration, logs

    async def generate_async(
        self,
        text: str,
        output_path: Path,
        voice_profile_id: Optional[str] = None,
        ref_audio_path: Optional[str] = None,
        ref_text: Optional[str] = None,
        language: Optional[str] = None,
        instruct: Optional[str] = None,
        num_step: int = 32,
        guidance_scale: float = 2.0,
        speed: Optional[float] = None,
        duration: Optional[float] = None,
        t_shift: float = 0.1,
        denoise: bool = True,
    ) -> tuple[float, list[str]]:
        if not self._loaded:
            raise RuntimeError("OmniVoice model is not loaded yet")

        return await asyncio.to_thread(
            self._do_generate,
            text,
            voice_profile_id,
            ref_audio_path,
            ref_text,
            language,
            instruct,
            num_step,
            guidance_scale,
            speed,
            duration,
            t_shift,
            denoise,
            output_path,
        )


omnivoice_service = OmniVoiceService.get_instance()

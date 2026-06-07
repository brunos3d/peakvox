import asyncio
import gc
import logging
import os
from pathlib import Path
from typing import Optional

import numpy as np
import torch

from app.core.config import settings
from app.utils.audio import save_numpy_as_wav

logger = logging.getLogger(__name__)


def _vram_snapshot() -> str:
    """Return a compact VRAM usage string, or empty string if CUDA unavailable."""
    try:
        if not torch.cuda.is_available():
            return ""
        alloc = torch.cuda.memory_allocated() / 1024 ** 3
        reserved = torch.cuda.memory_reserved() / 1024 ** 3
        return f"alloc={alloc:.2f}GB reserved={reserved:.2f}GB"
    except Exception:
        return ""


class OmniVoiceService:
    """
    Singleton wrapping the OmniVoice model.

    GPU safety contract
    -------------------
    • Only one inference runs at a time, enforced by ``_generation_lock``.
    • ``_do_generate`` always calls ``_offload_to_cpu`` + ``torch.cuda.empty_cache``
      in its ``finally`` block, so VRAM is released on both success and failure.
    • ``is_generating`` is checked by the HTTP endpoint to return 409 instead of
      queuing a second job when the GPU is already busy.
    """

    _instance: Optional["OmniVoiceService"] = None

    def __init__(self) -> None:
        self._model = None
        self._device: str = "cpu"
        self._use_gpu: bool = True
        self._loading: bool = False
        self._loaded: bool = False
        self._load_error: Optional[str] = None
        # The HF repo / model id currently loaded (defaults to settings.OMNIVOICE_MODEL).
        self._loaded_repo_id: Optional[str] = None
        self._voice_prompt_cache: dict = {}
        # Initialised lazily inside generate_async (must run inside a live event loop).
        self._generation_lock: Optional[asyncio.Lock] = None

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

    def _do_load(self, repo_id: Optional[str] = None) -> None:
        os.environ["HF_HOME"] = str(settings.HF_HOME)
        os.makedirs(settings.HF_HOME, exist_ok=True)

        from omnivoice import OmniVoice
        from omnivoice.utils.common import get_best_device

        repo = repo_id or settings.OMNIVOICE_MODEL
        self._device = get_best_device()
        dtype = torch.float16 if self._device in ("cuda", "xpu") else torch.float32

        logger.info("Loading OmniVoice model '%s' on %s (%s)", repo, self._device, dtype)
        self._model = OmniVoice.from_pretrained(
            repo,
            device_map=self._device,
            dtype=dtype,
            load_asr=settings.LOAD_ASR,
            asr_model_name=settings.ASR_MODEL,
        )
        self._loaded_repo_id = repo

        if torch.cuda.is_available():
            self._model.to("cpu")
            torch.cuda.empty_cache()
            logger.info("Model offloaded to CPU after load — VRAM is free until first generation")

        logger.info("OmniVoice model loaded successfully")

    async def load_model(self, repo_id: Optional[str] = None) -> None:
        target = repo_id or settings.OMNIVOICE_MODEL
        # Already serving the requested repo — nothing to do.
        if self._loaded and self._loaded_repo_id == target:
            return
        if self._loading:
            return
        self._loading = True
        try:
            await asyncio.to_thread(self._do_load, target)
            self._loaded = True
            self._load_error = None
        except Exception as exc:
            self._load_error = str(exc)
            logger.error("OmniVoice model load failed: %s", exc)
        finally:
            self._loading = False

    @property
    def loaded_repo_id(self) -> Optional[str]:
        return self._loaded_repo_id

    def offload(self) -> None:
        """Public hook for the registry: release GPU memory without unloading weights."""
        self._offload_to_cpu()

    # ------------------------------------------------------------------
    # GPU management
    # ------------------------------------------------------------------

    def _ensure_on_gpu(self) -> None:
        if not self._use_gpu or self._device != "cuda" or self._model is None:
            return
        try:
            p = next(self._model.parameters())
            if p.device.type != "cuda":
                logger.debug("Moving model to GPU | before: %s", _vram_snapshot())
                self._model.to("cuda")
        except StopIteration:
            pass

    def _offload_to_cpu(self) -> None:
        """Move model to CPU and free the VRAM allocator cache."""
        if self._model is None:
            return
        try:
            p = next(self._model.parameters())
            if p.device.type == "cuda":
                self._model.to("cpu")
        except StopIteration:
            pass
        # Offload cached voice prompts before emptying cache so their
        # GPU memory is reclaimed by empty_cache.
        self._move_voice_prompts_to("cpu")
        # Always run empty_cache regardless of where the model was.
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def _move_voice_prompts_to(self, device: str) -> None:
        """Move cached voice prompts to *device* (best-effort).

        Voice prompts are created on the GPU while the model is resident there.
        Without moving them to CPU before ``torch.cuda.empty_cache()`` they
        pin VRAM indefinitely, causing a silent memory leak.
        """
        for voice_id, prompt in list(self._voice_prompt_cache.items()):
            self._move_prompt_to(prompt, device)
            if hasattr(prompt, "to"):
                self._voice_prompt_cache[voice_id] = prompt

    def _move_prompt_to(self, prompt, device: str) -> None:
        """Move a single cached voice prompt to *device* (best-effort)."""
        try:
            if hasattr(prompt, "to"):
                prompt.to(device)
        except Exception as exc:
            logger.warning("Failed to move voice prompt to %s: %s", device, exc)

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
    def is_generating(self) -> bool:
        """True while a generation is holding the lock."""
        return self._generation_lock is not None and self._generation_lock.locked()

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
            logger.debug("Voice prompt cache hit | voice_id=%s", voice_id)
            prompt = self._voice_prompt_cache[voice_id]
            # Move only THIS prompt to GPU — other cached prompts stay on CPU so
            # the generation peak holds at most one prompt in VRAM regardless of
            # how many voices are in the library.
            self._move_prompt_to(prompt, "cuda")
            self._voice_prompt_cache[voice_id] = prompt
            return prompt

        logger.debug("Extracting voice clone prompt | voice_id=%s ref=%s", voice_id, ref_audio_path)
        self._ensure_on_gpu()
        prompt = self._model.create_voice_clone_prompt(
            ref_audio=ref_audio_path,
            ref_text=ref_text or None,
        )
        self._voice_prompt_cache[voice_id] = prompt
        logger.debug("Voice prompt cached | voice_id=%s cache_size=%d", voice_id, len(self._voice_prompt_cache))
        return prompt

    def invalidate_voice_cache(self, voice_id: str) -> None:
        if self._voice_prompt_cache.pop(voice_id, None) is not None:
            logger.debug("Voice prompt cache invalidated | voice_id=%s", voice_id)

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
        try:
            device_label = "GPU" if (self._use_gpu and self._device == "cuda") else "CPU"
            logs.append(f"Using {device_label} for generation | {_vram_snapshot()}")
            logger.debug("Inference start | device=%s vram=%s", device_label, _vram_snapshot())

            gen_config = OmniVoiceGenerationConfig(
                num_step=num_step,
                guidance_scale=guidance_scale,
                t_shift=t_shift,
                denoise=denoise,
            )

            voice_clone_prompt = None

            if voice_profile_id and ref_audio_path:
                logs.append(f"Loading voice clone prompt | voice_id={voice_profile_id}")
                logger.debug("Fetching voice prompt | voice_id=%s", voice_profile_id)
                voice_clone_prompt = self.get_or_create_voice_prompt(
                    voice_id=voice_profile_id,
                    ref_audio_path=ref_audio_path,
                    ref_text=ref_text,
                )
            elif ref_audio_path:
                logs.append("Extracting voice clone prompt from ad-hoc reference audio")
                logger.debug("Extracting ad-hoc voice prompt | ref=%s", ref_audio_path)
                self._ensure_on_gpu()
                voice_clone_prompt = self._model.create_voice_clone_prompt(
                    ref_audio=ref_audio_path,
                    ref_text=ref_text or None,
                )

            logs.append(
                f"Generating speech | steps={num_step} guidance={guidance_scale} "
                f"speed={speed or 'auto'} duration={duration or 'auto'}"
            )
            logger.debug("Calling model.generate | text_len=%d", len(text))

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
            logs.append(f"Audio saved | duration={audio_duration:.2f}s path={output_path.name}")
            logger.debug("Inference done | output_duration=%.2fs output=%s", audio_duration, output_path.name)

            # Release the numpy arrays before the VRAM offload
            del audios, audio, voice_clone_prompt

            return audio_duration, logs

        finally:
            # Always release GPU memory, on both success and any exception.
            # Python executes finally AFTER storing the return value, so any
            # appends here ARE included in the returned `logs` list.
            logger.debug("Cleanup start | vram_before=%s", _vram_snapshot())
            self._offload_to_cpu()
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            snapshot = _vram_snapshot()
            logger.debug("Cleanup done | vram_after=%s", snapshot)
            if snapshot:
                logs.append(f"GPU memory released | {snapshot}")

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
        job_id: Optional[str] = None,
    ) -> tuple[float, list[str]]:
        if not self._loaded:
            raise RuntimeError("OmniVoice model is not loaded yet")

        # Lazy-initialise inside the running event loop.
        if self._generation_lock is None:
            self._generation_lock = asyncio.Lock()

        if self._generation_lock.locked():
            raise RuntimeError(
                "A generation is already in progress. Please wait for it to complete."
            )

        async with self._generation_lock:
            logger.info(
                "Generation start | job=%s voice=%s lang=%s steps=%d guidance=%.2f vram=%s",
                job_id or "adhoc",
                voice_profile_id or "none",
                language or "auto",
                num_step,
                guidance_scale,
                _vram_snapshot(),
            )

            result = await asyncio.to_thread(
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

            logger.info(
                "Generation end | job=%s output_duration=%.2fs vram=%s",
                job_id or "adhoc",
                result[0],
                _vram_snapshot(),
            )
            return result


omnivoice_service = OmniVoiceService.get_instance()

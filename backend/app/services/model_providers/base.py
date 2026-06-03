"""The provider adapter contract.

A :class:`ModelProvider` knows how to load, run, and offload one family of models. It is the
plugin seam: built-in providers wrap OmniVoice; future custom/community models register their
own. This module is torch-free; concrete providers import the heavy runtime lazily inside
their methods so the registry can be imported without a GPU/ML stack present.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from app.models.registry_types import ModelDescriptor


class ModelProvider(ABC):
    """Loads/offloads/generates for the models it backs. Implementations must keep the
    VRAM contract: only generate while loaded, and release GPU memory on offload."""

    @abstractmethod
    async def load(self, descriptor: ModelDescriptor) -> None:
        """Load (or swap to) the given model's weights, making the provider ready to generate."""

    @abstractmethod
    def offload(self) -> None:
        """Release GPU memory (move to CPU / empty cache). Safe to call when not loaded."""

    @property
    @abstractmethod
    def is_loaded(self) -> bool:
        ...

    @property
    @abstractmethod
    def loaded_model_id(self) -> Optional[str]:
        """The id of the descriptor currently loaded, or None."""

    @abstractmethod
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
        """Run inference, write audio to ``output_path``, return ``(duration_seconds, logs)``."""

"""The model registry — the runtime authority over which models exist and which one is
resident on the GPU.

Design (see plan AD-5 / AD-8):

* **Torch-free import.** Providers are registered as lazy factories; the heavy ML runtime is
  only touched when a model is actually loaded. This keeps the registry importable in tests
  and in environments without a GPU stack.
* **One resident model.** A typical self-hosted GPU cannot hold multiple voice models. The
  registry keeps at most one model loaded; switching offloads the outgoing provider before
  loading the incoming one.
* **One generation at a time.** A single ``asyncio`` lock preserves the existing 409-on-busy
  contract across all models.
"""

import asyncio
import logging
from pathlib import Path
from typing import Callable, Optional

from app.models.registry_types import ModelDescriptor
from app.services.model_providers.base import ModelProvider

logger = logging.getLogger(__name__)

ProviderFactory = Callable[[], ModelProvider]


class ModelRegistry:
    def __init__(self) -> None:
        self._descriptors: dict[str, ModelDescriptor] = {}
        self._provider_factories: dict[str, ProviderFactory] = {}
        self._providers: dict[str, ModelProvider] = {}
        self._resident_model_id: Optional[str] = None
        self._load_lock = asyncio.Lock()
        self._generation_lock: Optional[asyncio.Lock] = None

    # ── Catalog ───────────────────────────────────────────────────────────────
    def set_descriptors(self, descriptors: list[ModelDescriptor]) -> None:
        # Store independent copies so runtime lifecycle changes (status, etc.) never mutate the
        # static BUILTIN_MODELS catalog (avoids global leakage between requests/tests).
        self._descriptors = {d.id: d.model_copy(deep=True) for d in descriptors}

    def upsert_descriptor(self, descriptor: ModelDescriptor) -> None:
        self._descriptors[descriptor.id] = descriptor

    def set_status(self, model_id: str, status: str) -> None:
        """Sync an in-memory descriptor's status after a persisted lifecycle change.

        Adapters share the registry's descriptor object (see wire_runtime), so this keeps the
        runtime + /models view consistent with the DB without a reload.
        """
        descriptor = self._descriptors.get(model_id)
        if descriptor is not None:
            descriptor.status = status

    def remove(self, model_id: str) -> None:
        """Drop a descriptor from the in-memory catalog (e.g. a removed community model)."""
        self._descriptors.pop(model_id, None)

    def list_models(self, edition: Optional[str] = None) -> list[ModelDescriptor]:
        models = list(self._descriptors.values())
        if edition is not None:
            models = [m for m in models if edition in m.editions]
        return models

    def get(self, model_id: str) -> Optional[ModelDescriptor]:
        return self._descriptors.get(model_id)

    def resolve_default(self) -> ModelDescriptor:
        for d in self._descriptors.values():
            if d.is_default:
                return d
        raise RuntimeError("No default model registered")

    def get_or_default(self, model_id: Optional[str]) -> ModelDescriptor:
        """Resolve an optional model id, falling back to the default when None/empty.

        Raises KeyError for a non-empty id that does not exist.
        """
        if not model_id:
            return self.resolve_default()
        d = self._descriptors.get(model_id)
        if d is None:
            raise KeyError(model_id)
        return d

    # ── Providers ───────────────────────────────────────────────────────────────
    def register_provider(self, name: str, factory: ProviderFactory) -> None:
        self._provider_factories[name] = factory

    def _provider_for(self, descriptor: ModelDescriptor) -> ModelProvider:
        name = descriptor.provider
        if name not in self._providers:
            factory = self._provider_factories.get(name)
            if factory is None:
                raise RuntimeError(f"No provider registered for '{name}'")
            self._providers[name] = factory()
        return self._providers[name]

    # ── Loading / residency ───────────────────────────────────────────────────
    @property
    def resident_model_id(self) -> Optional[str]:
        return self._resident_model_id

    async def ensure_loaded(self, model_id: str) -> ModelDescriptor:
        descriptor = self.get_or_default(model_id)
        async with self._load_lock:
            if self._resident_model_id == descriptor.id:
                provider = self._providers.get(descriptor.provider)
                if provider is not None and provider.is_loaded:
                    return descriptor

            # Offload whatever is currently resident (possibly a different provider).
            if self._resident_model_id is not None:
                prev = self.get(self._resident_model_id)
                if prev is not None:
                    prev_provider = self._providers.get(prev.provider)
                    if prev_provider is not None and prev_provider.is_loaded:
                        logger.info("Offloading resident model %s before loading %s",
                                    prev.id, descriptor.id)
                        prev_provider.offload()

            provider = self._provider_for(descriptor)
            logger.info("Loading model %s via provider %s", descriptor.id, descriptor.provider)
            await provider.load(descriptor)
            self._resident_model_id = descriptor.id
            return descriptor

    # ── Generation ──────────────────────────────────────────────────────────────
    @property
    def is_generating(self) -> bool:
        return self._generation_lock is not None and self._generation_lock.locked()

    async def generate(
        self,
        model_id: Optional[str],
        *,
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
        descriptor = self.get_or_default(model_id)

        if self._generation_lock is None:
            self._generation_lock = asyncio.Lock()
        if self._generation_lock.locked():
            raise RuntimeError("A generation is already in progress. Please wait for it to complete.")

        async with self._generation_lock:
            await self.ensure_loaded(descriptor.id)
            provider = self._provider_for(descriptor)
            return await provider.generate(
                descriptor=descriptor,
                text=text,
                output_path=output_path,
                voice_profile_id=voice_profile_id,
                ref_audio_path=ref_audio_path,
                ref_text=ref_text,
                language=language,
                instruct=instruct,
                params=params or {},
                job_id=job_id,
            )

    # ── Status ──────────────────────────────────────────────────────────────────
    def status(self, model_id: str) -> dict:
        descriptor = self.get(model_id)
        if descriptor is None:
            return {"id": model_id, "status": "unknown", "loaded": False}
        provider = self._providers.get(descriptor.provider)
        loaded = bool(provider and provider.is_loaded and provider.loaded_model_id == model_id)
        return {
            "id": model_id,
            "status": "loaded" if loaded else descriptor.status,
            "loaded": loaded,
            "resident": self._resident_model_id == model_id,
        }


# Process-wide singleton.
model_registry = ModelRegistry()

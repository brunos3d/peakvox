"""Wires the in-memory model registry: loads built-in descriptors and registers provider
factories. Called once at startup (after migrations). Kept separate from ``model_registry``
so the registry module stays provider-agnostic and torch-free at import time.

Provider factories are lazy — instantiating ``OmniVoiceProvider`` is cheap and does not touch
torch; the heavy load happens only when the registry calls ``provider.load(...)``.
"""

import logging

from app.services.model_catalog import BUILTIN_MODELS
from app.services.model_registry import model_registry

logger = logging.getLogger(__name__)


def wire_registry() -> None:
    model_registry.set_descriptors(list(BUILTIN_MODELS))

    def _omnivoice():
        from app.services.model_providers.omnivoice_provider import OmniVoiceProvider

        return OmniVoiceProvider()

    # Base + Distilled share the OmniVoice runtime.
    model_registry.register_provider("omnivoice", _omnivoice)

    # Singing provider is registered in Phase 8; until then the singing model is disabled
    # in the catalog and generation requests for it are rejected before reaching a provider.
    logger.info("Model registry wired with %d models", len(BUILTIN_MODELS))

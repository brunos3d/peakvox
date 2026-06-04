"""Wires the in-memory model registry: loads built-in descriptors and registers provider
factories. Called once at startup (after migrations). Kept separate from ``model_registry``
so the registry module stays provider-agnostic and torch-free at import time.

Provider factories are lazy — instantiating ``OmniVoiceProvider`` is cheap and does not touch
torch; the heavy load happens only when the registry calls ``provider.load(...)``.
"""

import logging

from app.services.model_adapters.omnivoice_adapter import (
    OmniVoiceAdapter,
    OmniVoiceSingingAdapter,
)
from app.services.model_catalog import BUILTIN_MODELS
from app.services.model_registry import model_registry
from app.services.runtime import runtime

logger = logging.getLogger(__name__)

# Provider name → ModelAdapter class. This is registration wiring (not capability behavior):
# capabilities/tags/languages are read from each model's declared descriptor, never branched on.
_ADAPTER_BY_PROVIDER = {
    "omnivoice": OmniVoiceAdapter,
    "omnivoice-singing": OmniVoiceSingingAdapter,
}


def wire_registry() -> None:
    model_registry.set_descriptors(list(BUILTIN_MODELS))

    def _omnivoice():
        from app.services.model_providers.omnivoice_provider import OmniVoiceProvider

        return OmniVoiceProvider()

    # Base + Distilled + Singing all run on the OmniVoice runtime; the descriptor's repo_id
    # selects the weights. The singing model stays catalog-`disabled` for *generation* until its
    # upstream weights are verified (Risk R-7), but registering the provider + adapter lets the
    # Runtime resolve and validate it now (multi-model architecture validation).
    model_registry.register_provider("omnivoice", _omnivoice)
    model_registry.register_provider("omnivoice-singing", _omnivoice)

    logger.info("Model registry wired with %d models", len(BUILTIN_MODELS))


def wire_runtime() -> None:
    """Register a ModelAdapter with the PeakVox Runtime for each built-in model."""
    for descriptor in BUILTIN_MODELS:
        adapter_cls = _ADAPTER_BY_PROVIDER.get(descriptor.provider)
        if adapter_cls is not None:
            runtime.register_adapter(adapter_cls(descriptor))
    logger.info("PeakVox Runtime wired with %d adapters", len(runtime.list_adapters()))

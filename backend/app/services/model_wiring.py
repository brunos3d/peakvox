"""Wires the in-memory model registry: loads built-in descriptors and registers provider
factories. Called once at startup (after migrations). Kept separate from ``model_registry``
so the registry module stays provider-agnostic and torch-free at import time.

Provider factories are lazy — instantiating ``OmniVoiceProvider`` is cheap and does not touch
torch; the heavy load happens only when the registry calls ``provider.load(...)``.
"""

import logging
import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.model_adapters.fish_adapter import FishAudioAdapter
from app.services.model_adapters.omnivoice_adapter import (
    OmniVoiceAdapter,
    OmniVoiceSingingAdapter,
)
from app.services.model_catalog import BUILTIN_MODELS
from app.models.registry_types import (
    ModelCapabilities,
    ModelDescriptor,
    ModelLicense,
    ModelRequirements,
)
from app.services.model_registry import model_registry
from app.services.runtime import runtime

logger = logging.getLogger(__name__)

# Provider name → ModelAdapter class. This is registration wiring (not capability behavior):
# capabilities/tags/languages are read from each model's declared descriptor, never branched on.
_ADAPTER_BY_PROVIDER = {
    "omnivoice": OmniVoiceAdapter,
    "omnivoice-singing": OmniVoiceSingingAdapter,
    "fish-audio": FishAudioAdapter,
}


def wire_registry() -> None:
    model_registry.set_descriptors(list(BUILTIN_MODELS))
    _register_provider_factories()
    logger.info("Model registry wired with %d models", len(BUILTIN_MODELS))


def _register_provider_factories() -> None:
    def _omnivoice():
        from app.services.model_providers.omnivoice_provider import OmniVoiceProvider

        return OmniVoiceProvider()

    # Base + Singing run on the OmniVoice runtime; the descriptor's repo_id
    # selects the weights. The singing model stays catalog-`disabled` for *generation* until its
    # upstream weights are verified (Risk R-7), but registering the provider + adapter lets the
    # Runtime resolve and validate it now (multi-model architecture validation).
    model_registry.register_provider("omnivoice", _omnivoice)
    model_registry.register_provider("omnivoice-singing", _omnivoice)


def _decode_json(value, fallback):
    if value is None:
        return fallback
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return fallback
    return value


def _descriptor_from_row(row) -> ModelDescriptor:
    return ModelDescriptor(
        id=row["id"],
        name=row["name"],
        description=row["description"] or "",
        version=row["version"],
        provider=row["provider"],
        repo_id=row["repo_id"],
        model_path=row["model_path"],
        supported_languages=_decode_json(row["supported_languages"], []),
        supported_tags=_decode_json(row["supported_tags"], []),
        supported_voice_design=_decode_json(row["supported_voice_design"], []),
        capabilities=ModelCapabilities(**_decode_json(row["capabilities"], {})),
        requirements=ModelRequirements(**_decode_json(row["requirements"], {})),
        license=(
            ModelLicense(**_decode_json(row["license"], {}))
            if _decode_json(row["license"], None) is not None
            else None
        ),
        provider_metadata=_decode_json(row["provider_metadata"], {}),
        status=row["status"],
        is_default=bool(row["is_default"]),
        is_builtin=bool(row["is_builtin"]),
        editions=_decode_json(row["editions"], ["community"]),
    )


async def wire_registry_from_database(session: AsyncSession) -> None:
    """Hydrate the in-memory registry from persisted Model rows after migrations.

    Static metadata is refreshed by migrations from the canonical catalog, while lifecycle status
    is persisted in the DB. This makes the DB the restart-safe source of truth for registry state.
    """
    res = await session.execute(
        text(
            "SELECT id, name, description, version, provider, repo_id, model_path, "
            "supported_languages, supported_tags, supported_voice_design, capabilities, "
            "status, is_default, is_builtin, editions, requirements, license, provider_metadata "
            "FROM models"
        )
    )
    descriptors = [_descriptor_from_row(row) for row in res.mappings().all()]
    model_registry.set_descriptors(descriptors)
    _register_provider_factories()
    logger.info("Model registry hydrated from database with %d models", len(descriptors))


def wire_runtime() -> None:
    """Register a ModelAdapter with the PeakVox Runtime for each built-in model.

    Adapters are built on the *registry's* descriptor object (falling back to the catalog if the
    registry hasn't been wired) so that persisted lifecycle status changes synced into the
    registry are immediately visible to the runtime/adapters.
    """
    for descriptor in BUILTIN_MODELS:
        adapter_cls = _ADAPTER_BY_PROVIDER.get(descriptor.provider)
        if adapter_cls is not None:
            shared = model_registry.get(descriptor.id) or descriptor
            runtime.register_adapter(adapter_cls(shared))
    logger.info("PeakVox Runtime wired with %d adapters", len(runtime.list_adapters()))

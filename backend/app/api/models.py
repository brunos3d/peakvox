"""Internal model-registry API consumed by the app frontend.

Exposes the available models, their capabilities, per-model load status, and each model's
inline-tag catalog (with UI metadata) so the editor can build its slash menu, toolbar, and
live validation from a single backend source of truth (plan AD-3).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import settings
from app.core.database import get_db
from app.services.model_lifecycle import (
    ModelNotFoundError,
    activate_model,
    deactivate_model,
    deprecate_model,
    install_model,
    remove_model,
    update_model,
)
from app.services.model_registry import model_registry
from app.services.tag_catalog import tags_for

logger = logging.getLogger(__name__)
router = APIRouter()


def _descriptor_payload(descriptor) -> dict:
    # model_dump() already serialises requirements/license/provider_metadata (nested models to dicts).
    data = descriptor.model_dump()
    data.update(model_registry.status(descriptor.id))

    from app.models.registry_types import derive_voice_features
    from app.services.runtime import runtime

    # For Runtime-Registry-managed models, RuntimeManager.resolve() is the authoritative
    # source of "active" state (ADR-0017 §3.4). The legacy descriptor.status / activation_status
    # computed field is never updated by RuntimeManager lifecycle operations, so we override it
    # here at serialization time. Models with no runtime registry entries use the legacy path.
    if runtime._runtime_manager is not None:
        registry_descriptors = runtime._runtime_manager.registry.list_for_model(descriptor.id)
        if registry_descriptors:
            is_active = runtime._runtime_manager.resolve(descriptor.id) is not None
            data["activation_status"] = "active" if is_active else "inactive"

    try:
        adapter = runtime.get_adapter(descriptor.id)
        build_strategies = [
            (s.creation_source, s.can_build) for s in adapter.get_build_strategies()
        ]
        features = derive_voice_features(descriptor.capabilities, build_strategies)
        data["voice_features"] = features.model_dump()
    except Exception:
        data["voice_features"] = {"voice_types": []}

    return data


def _writes_enabled() -> bool:
    # Community Edition: the local owner manages their own instance ("Ollama for Voice") -
    # install/activate/remove models locally. Cloud: model management is operator-only
    # (admin roles arrive with Phase 4 auth), so user-facing writes are disabled there for now.
    return settings.EDITION == "community"


def _require_writes() -> None:
    if not _writes_enabled():
        raise HTTPException(
            status_code=403,
            detail="Model management is operator-only in this edition",
        )


@router.get("/models")
async def list_models():
    """All models available in the current edition."""
    models = model_registry.list_models(edition=settings.EDITION)
    return {"models": [_descriptor_payload(m) for m in models]}


@router.get("/api/models")
async def list_api_models():
    """Alias for clients that expect the internal registry under /api/models."""
    return await list_models()


@router.get("/models/status")
async def models_status_aggregate():
    """Back-compat aggregate: the default model's load state.

    Preserves the original ``/models/status`` contract used by the sidebar status row.
    """
    from app.services.omnivoice_service import omnivoice_service

    return {
        "loaded": omnivoice_service.is_loaded,
        "loading": omnivoice_service.is_loading,
        "error": omnivoice_service.load_error,
        "sampling_rate": omnivoice_service.sampling_rate,
        "resident_model_id": model_registry.resident_model_id,
    }


@router.get("/models/{model_id}")
async def get_model(model_id: str):
    descriptor = model_registry.get(model_id)
    if descriptor is None:
        raise HTTPException(status_code=404, detail="Model not found")
    return _descriptor_payload(descriptor)


@router.get("/api/models/{model_id}")
async def get_api_model(model_id: str):
    return await get_model(model_id)


@router.get("/models/{model_id}/tags")
async def get_model_tags(model_id: str):
    descriptor = model_registry.get(model_id)
    if descriptor is None:
        raise HTTPException(status_code=404, detail="Model not found")
    return {
        "model_id": model_id,
        "tags": [
            {
                "id": t.id,
                "label": t.label,
                "emoji": t.emoji,
                "category": t.category,
                "description": t.description,
                "syntax": t.syntax,
            }
            for t in tags_for(descriptor.supported_tags)
        ],
    }


@router.get("/models/{model_id}/status")
async def get_model_status(model_id: str):
    if model_registry.get(model_id) is None:
        raise HTTPException(status_code=404, detail="Model not found")
    return model_registry.status(model_id)


# --- Model lifecycle ---------------------------------------------------------------


@router.post("/models/{model_id}/activate")
async def activate(model_id: str, session=Depends(get_db)):
    _require_writes()
    try:
        status = await activate_model(session, model_id)
    except ModelNotFoundError:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"id": model_id, "status": status}


@router.post("/models/{model_id}/deactivate")
async def deactivate(model_id: str, session=Depends(get_db)):
    _require_writes()
    try:
        status = await deactivate_model(session, model_id)
    except ModelNotFoundError:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"id": model_id, "status": status}


@router.post("/models/{model_id}/deprecate")
async def deprecate(model_id: str, session=Depends(get_db)):
    _require_writes()
    try:
        status = await deprecate_model(session, model_id)
    except ModelNotFoundError:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"id": model_id, "status": status}


@router.post("/models/{model_id}/install")
async def install(model_id: str, session=Depends(get_db)):
    """Install a model locally (CE 'Ollama for Voice'). Download is mocked; the rest is real."""
    _require_writes()
    try:
        status = await install_model(session, model_id)
    except ModelNotFoundError:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"id": model_id, "status": status}


@router.post("/models/{model_id}/update")
async def update(model_id: str, session=Depends(get_db)):
    _require_writes()
    try:
        status = await update_model(session, model_id)
    except ModelNotFoundError:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"id": model_id, "status": status}


@router.post("/models/{model_id}/remove")
async def remove(model_id: str, session=Depends(get_db)):
    _require_writes()
    try:
        status = await remove_model(session, model_id)
    except ModelNotFoundError:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"id": model_id, "status": status, "removed": True}

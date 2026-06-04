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
)
from app.services.model_registry import model_registry
from app.services.tag_catalog import tags_for

logger = logging.getLogger(__name__)
router = APIRouter()


def _descriptor_payload(descriptor) -> dict:
    # model_dump() already serialises requirements/license/provider_metadata (nested models → dicts).
    data = descriptor.model_dump()
    data.update(model_registry.status(descriptor.id))
    return data


def _writes_enabled() -> bool:
    # Admin model management is a Cloud capability; CE is read-only for the registry.
    return settings.features.auth


def _require_writes() -> None:
    if not _writes_enabled():
        raise HTTPException(status_code=403, detail="Model management is a Cloud-only capability")


@router.get("/models")
async def list_models():
    """All models available in the current edition."""
    models = model_registry.list_models(edition=settings.EDITION)
    return {"models": [_descriptor_payload(m) for m in models]}


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


# --- Admin lifecycle (Cloud-only writes; 403 in Community Edition) -----------------


@router.post("/models/{model_id}/activate")
async def activate(model_id: str, session=Depends(get_db)):
    _require_writes()
    try:
        await activate_model(session, model_id)
    except ModelNotFoundError:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"id": model_id, "status": "available"}


@router.post("/models/{model_id}/deactivate")
async def deactivate(model_id: str, session=Depends(get_db)):
    _require_writes()
    try:
        await deactivate_model(session, model_id)
    except ModelNotFoundError:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"id": model_id, "status": "disabled"}


@router.post("/models/{model_id}/deprecate")
async def deprecate(model_id: str, session=Depends(get_db)):
    _require_writes()
    try:
        await deprecate_model(session, model_id)
    except ModelNotFoundError:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"id": model_id, "status": "deprecated"}

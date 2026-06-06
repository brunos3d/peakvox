"""VoiceResourceService — catalog aggregation layer.

Aggregates all catalog sources (``ProviderVoiceRegistry``, future marketplace + external
catalogs) into a unified ``GET /voice-resources`` view.  Enriches each item at query time
with ``is_in_library`` / ``library_voice_id`` (cross-referenced against the DB) and
``compatible_models`` / ``recommended_model_id`` (from ``CompatibilityResolver``).
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import VoiceProfile
from app.schemas.voice_resource import VoiceResourceResponse
from app.services.compatibility_resolver import CompatibilityResolver
from app.services.provider_voice import ProviderVoice, ProviderVoiceRegistry


class VoiceResourceService:
    """Orchestrates catalog sources into a single ``VoiceResourceResponse`` view."""

    def __init__(
        self,
        provider_registry: ProviderVoiceRegistry,
        compatibility_resolver: CompatibilityResolver,
    ) -> None:
        self._provider_registry = provider_registry
        self._compat = compatibility_resolver

    async def list(
        self,
        db: AsyncSession,
        *,
        resource_type: Optional[str] = None,
        resource_origin: Optional[str] = None,
        search: Optional[str] = None,
        language: Optional[str] = None,
        gender: Optional[str] = None,
    ) -> list[VoiceResourceResponse]:
        voices = self._get_candidates(resource_type, resource_origin, search, language, gender)
        if not voices:
            return []
        return await self._enrich(db, voices)

    async def get(
        self, db: AsyncSession, voice_id: str
    ) -> Optional[VoiceResourceResponse]:
        voice = self._provider_registry.get(voice_id)
        if voice is None:
            return None
        results = await self._enrich(db, [voice])
        return results[0] if results else None

    # ── internal ──────────────────────────────────────────────────────────

    def _get_candidates(
        self,
        resource_type: Optional[str],
        resource_origin: Optional[str],
        search: Optional[str],
        language: Optional[str],
        gender: Optional[str],
    ) -> list[ProviderVoice]:
        if resource_type and resource_type != "preset":
            return []
        candidates = self._provider_registry.list_all()

        if resource_origin:
            candidates = [v for v in candidates if v.resource_origin == resource_origin]
        if search:
            q = search.lower()
            candidates = [
                v
                for v in candidates
                if q in v.name.lower() or q in v.description.lower()
            ]
        if language:
            candidates = [v for v in candidates if v.language == language]
        if gender:
            candidates = [v for v in candidates if v.gender == gender]
        return candidates

    async def _enrich(
        self, db: AsyncSession, voices: list[ProviderVoice]
    ) -> list[VoiceResourceResponse]:
        if not voices:
            return []

        library_map = await self._build_library_map(db, voices)

        results: list[VoiceResourceResponse] = []
        for v in voices:
            lib = library_map.get(v.provider_voice_id)
            is_in_library = lib is not None
            library_voice_id = lib["id"] if lib else None

            compatible_models = (
                self._compat.get_models_for_creation_source(
                    creation_source="PRESET_VOICE",
                )
                if not is_in_library
                else []
            )
            # If already in library, compatibility is already on the Voice record.
            recommended = compatible_models[0] if compatible_models else None

            results.append(
                VoiceResourceResponse(
                    id=v.provider_voice_id,
                    resource_type="preset",
                    resource_origin=v.resource_origin,
                    name=v.name,
                    description=v.description,
                    language=v.language,
                    preview_audio_url=None,
                    catalog_source=v.catalog_source,
                    provider_id=v.provider_id,
                    external_id=v.external_id,
                    gender=v.gender,
                    is_default=v.is_default,
                    is_in_library=is_in_library,
                    library_voice_id=library_voice_id,
                    compatible_models=compatible_models,
                    recommended_model_id=recommended,
                )
            )
        return results

    async def _build_library_map(
        self, db: AsyncSession, voices: list[ProviderVoice]
    ) -> dict[str, dict]:
        """Cross-reference provider presets against the voice_profiles table.

        Matches on ``meta->>'provider'`` and ``meta->>'preset_name'`` — the same
        fields that ``POST /voices/from-preset`` stores at import time.
        """
        if not voices:
            return {}

        pairs = [(v.provider_id, v.external_id) for v in voices if v.provider_id and v.external_id]
        if not pairs:
            return {}

        clauses = [
            func.json_extract(VoiceProfile.meta, "$.provider") == pid
            and func.json_extract(VoiceProfile.meta, "$.preset_name") == eid
            for pid, eid in pairs
        ]

        result = await db.execute(
            select(
                VoiceProfile.id,
                func.json_extract(VoiceProfile.meta, "$.provider").label("provider"),
                func.json_extract(VoiceProfile.meta, "$.preset_name").label("preset_name"),
            ).where(or_(*clauses))
        )
        rows = result.all()

        lookup: dict[str, dict] = {}
        pair_to_vid: dict[tuple[str, str], str] = {}
        for pid, eid in pairs:
            for row in rows:
                if row.provider == pid and row.preset_name == eid:
                    pair_to_vid[(pid, eid)] = row.id

        for v in voices:
            key = (v.provider_id, v.external_id)
            if key in pair_to_vid:
                lookup[v.provider_voice_id] = {"id": pair_to_vid[key]}
        return lookup

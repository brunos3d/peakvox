"""ImportResolver — handles importing a VoiceResource into the user's voice library.

Resource-type agnostic: branches on ``VoiceResourceResponse.resource_type``,
delegating to the appropriate import strategy (preset → POST /voices/from-preset
equivalent, etc.).
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.db import Voice, VoiceProfile, VoiceVariant, VoiceVariantArtifact
from app.schemas.voice_resource import VoiceResourceResponse
from app.services.voice_onboarding import mirror_profile_to_split


class ImportAlreadyExistsError(ValueError):
    """Raised when the resource is already in the library."""


class ImportResolver:
    """Resolves a catalog resource into the user's voice library.

    If the resource is already in the library (``is_in_library=True``), raises
    ``ImportAlreadyExistsError``.  Otherwise delegates to the appropriate import
    strategy.
    """

    async def resolve(
        self,
        db: AsyncSession,
        resource: VoiceResourceResponse,
        *,
        model_id: Optional[str] = None,
    ) -> VoiceProfile:
        if resource.is_in_library and resource.library_voice_id:
            raise ImportAlreadyExistsError(
                f"Resource {resource.id} already imported as voice {resource.library_voice_id}"
            )

        if resource.resource_type == "preset":
            return await self._import_preset(db, resource, model_id=model_id)

        raise ValueError(f"Unsupported resource_type: {resource.resource_type}")

    @staticmethod
    async def _import_preset(
        db: AsyncSession,
        resource: VoiceResourceResponse,
        *,
        model_id: Optional[str] = None,
    ) -> VoiceProfile:
        profile_id = str(uuid.uuid4())
        public_id = f"voice_{uuid.uuid4().hex[:10].upper()}"
        resolved_model_id = model_id or resource.recommended_model_id or ""

        profile = VoiceProfile(
            id=profile_id,
            public_voice_id=public_id,
            name=resource.name,
            description=resource.description or (
                f"{resource.provider_id} preset: {resource.name} ({resource.language or ''})"
            ),
            language=resource.language,
            language_code=resource.language,
            transcript="",
            audio_filename="",
            audio_duration=0.0,
            is_preset_voice=True,
            owner_id=settings.LOCAL_OWNER_ID,
            meta={
                "provider": resource.provider_id,
                "preset_name": resource.external_id,
                "resource_type": resource.resource_type,
                "resource_origin": resource.resource_origin,
                "catalog_source": resource.catalog_source,
            },
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

        await mirror_profile_to_split(db, profile)

        voice = (
            await db.execute(select(Voice).where(Voice.id == profile_id))
        ).scalars().first()

        variant = VoiceVariant(
            id=str(uuid.uuid4()),
            voice_id=voice.id,
            model_id=resolved_model_id,
            artifact_type="voice_pack",
            params={"provider": resource.provider_id, "preset_name": resource.external_id},
            artifacts={},
            source="preset",
            status="ready",
        )
        db.add(variant)
        await db.commit()
        await db.refresh(variant)

        artifact = VoiceVariantArtifact(
            id=str(uuid.uuid4()),
            voice_variant_id=variant.id,
            version=1,
            storage_keys={},
            meta={"provider": resource.provider_id, "preset_name": resource.external_id},
        )
        db.add(artifact)
        variant.active_artifact_id = artifact.id
        await db.commit()

        return profile

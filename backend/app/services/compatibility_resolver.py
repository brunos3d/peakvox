"""CompatibilityResolver — single source of truth for voice-model compatibility.

Determines which models can generate for a given voice, and which voices can be
used with a given model. Used by API endpoints to expose ``compatible_models``
as a derived field (no new endpoints, no DB column).

Compatibility rule (ADR-0002 §3.4 / SPEC §3.4):
  A voice V is compatible with model M IF:
    (a) a ready ``VoiceVariant`` exists for ``(V, M)``, OR
    (b) M's adapter declares a ``VariantBuildStrategy`` for
        ``V.creation_source`` with ``can_build=True``.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import VoiceVariant
from app.services.model_adapter import ModelAdapter
from app.services.runtime import PeakVoxRuntime


class CompatibilityResolver:
    """Stateless resolver — instantiate once per request or use as a singleton."""

    def __init__(self, runtime: PeakVoxRuntime) -> None:
        self.runtime = runtime

    async def get_compatible_models(
        self,
        db: AsyncSession,
        voice_id: str,
        creation_source: str,
        *,
        _adapters: Optional[list[ModelAdapter]] = None,
    ) -> list[str]:
        """Return model IDs compatible with the given voice.

        Args:
            db: Database session.
            voice_id: The voice's ``id`` (matches ``VoiceProfile.id``).
            creation_source: The voice's ``creation_source`` (e.g. ``SOURCE_ASSET``,
                ``PRESET_VOICE``).
            _adapters: Override for testing. If omitted, reads from runtime.

        Returns:
            Sorted list of compatible ``model_id`` strings.
        """
        adapters = _adapters if _adapters is not None else self.runtime.list_adapters()
        if not adapters:
            return []

        # Single query for all variants of this voice
        result = await db.execute(
            select(VoiceVariant).where(VoiceVariant.voice_id == voice_id)
        )
        variants: list[VoiceVariant] = list(result.scalars().all())
        ready_models: set[str] = {v.model_id for v in variants if v.status == "ready"}

        # Pre-compute which adapters can build for this creation_source. A model is only
        # *actually* compatible if it can build (or already has a built variant) for
        # this voice's creation_source. Rule (a) without this check is too permissive:
        # a stray ready VoiceVariant row in the DB can mark a model compatible even when
        # the model has no build strategy for this voice type (e.g. a kokoro variant on
        # a SOURCE_ASSET voice).
        can_build_for_source: dict[str, bool] = {}
        for adapter in adapters:
            can_build_for_source[adapter.model_id] = any(
                s.creation_source == creation_source and s.can_build
                for s in adapter.get_build_strategies()
            )

        compatible: list[str] = []
        for adapter in adapters:
            mid = adapter.model_id

            # Rule (a): ready variant exists AND the model can build for this source
            if mid in ready_models and can_build_for_source.get(mid, False):
                compatible.append(mid)
                continue

            # Rule (b): adapter declares build strategy for this creation_source
            if can_build_for_source.get(mid, False):
                compatible.append(mid)

        return compatible

    async def get_compatible_voices(
        self,
        db: AsyncSession,
        model_id: str,
        *,
        _adapters: Optional[list[ModelAdapter]] = None,
    ) -> list[str]:
        """Return voice IDs compatible with the given model.

        Note: This is a best-effort inverse. For server-side filtering in large
        voice libraries, prefer a dedicated query path rather than iterating all
        voices + all adapters per voice.
        """
        return []  # Reserved for future use — Phase E may implement this.

    def get_models_for_creation_source(
        self, creation_source: str, *, _adapters: Optional[list[ModelAdapter]] = None
    ) -> list[str]:
        """Return model IDs that can build a variant for the given creation source.

        Unlike ``get_compatible_models``, this does NOT check for existing ready
        variants — it only checks adapter build strategies.  Useful for catalog
        resources (``VoiceResource``) that don't have a persisted Voice yet.
        """
        adapters = _adapters if _adapters is not None else self.runtime.list_adapters()
        if not adapters:
            return []
        compatible: list[str] = []
        for adapter in adapters:
            for strategy in adapter.get_build_strategies():
                if strategy.creation_source == creation_source and strategy.can_build:
                    compatible.append(adapter.model_id)
                    break
        return compatible

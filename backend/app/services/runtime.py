"""The PeakVox Runtime — the single, model-agnostic entry point for generation.

Layering (ADR-0004, Runtime §2):

    User / API  →  PeakVoxRuntime  →  ModelAdapter  →  Model Provider  →  Inference

The runtime owns: adapter resolution, model resolution, ``Voice + Model → VoiceVariant``
resolution, and capability/tag validation. It interacts *only* with :class:`ModelAdapter`
instances — never a model implementation — and never branches on a model id/name; behavior is
driven by declared capabilities (ADR-0003). The OmniVoice adapters delegate actual inference to
the proven registry/provider path, so the runtime adds orchestration without reimplementing the
VRAM/load discipline.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.db import Voice, VoiceVariant
from app.models.registry_types import ModelDescriptor
from app.services.capabilities import missing_capabilities as _missing_caps
from app.services.model_adapter import ModelAdapter
from app.services.provider_voice import ProviderVoice, ProviderVoiceCatalog, ProviderVoiceRegistry
from app.services.tag_validation import find_unsupported_tags
from app.services.variant_lifecycle import VariantStatus
from app.services.voice_variant_artifact_repository import (
    append_artifact,
    get_active_artifact,
    get_version,
    list_versions,
    prune_artifacts,
    set_active,
)
from app.services.voice_variant_repository import (
    get_voice_identity_by_public_id,
    resolve_variant,
)


class ModelNotRegistered(Exception):
    pass


class VoiceNotFound(Exception):
    pass


class VariantUnavailable(Exception):
    pass


class ModelNotAvailableInEdition(Exception):
    """A model is installed/registered but not licensed/available in the active edition (ADR-0005)."""

    def __init__(self, model_id: str, edition: str) -> None:
        self.model_id = model_id
        self.edition = edition
        super().__init__(f"Model '{model_id}' is not available in the '{edition}' edition")


class ModelNotActive(Exception):
    """A model exists but is not installed/active for generation."""

    def __init__(self, model_id: str, status: str) -> None:
        self.model_id = model_id
        self.status = status
        super().__init__(f"Model '{model_id}' is not active (status: {status})")


class VariantBuilding(Exception):
    """A variant build is already in progress (ADR-0008). Poll for completion."""

    def __init__(self, voice_id: str, model_id: str) -> None:
        self.voice_id = voice_id
        self.model_id = model_id
        super().__init__(f"Variant build in progress for voice '{voice_id}' on '{model_id}'")


class VariantBuildFailed(Exception):
    """A variant build failed (ADR-0008). Retry transitions failed → building."""

    def __init__(self, voice_id: str, model_id: str, error: Optional[str] = None) -> None:
        self.voice_id = voice_id
        self.model_id = model_id
        self.error = error
        super().__init__(
            f"Variant build failed for voice '{voice_id}' on '{model_id}'"
            + (f": {error}" if error else "")
        )


class VariantDeprecated(Exception):
    """A variant's artifact is deprecated (ADR-0008). Rebuild required before use."""

    def __init__(self, voice_id: str, model_id: str) -> None:
        self.voice_id = voice_id
        self.model_id = model_id
        super().__init__(
            f"Variant for voice '{voice_id}' on '{model_id}' is deprecated; rebuild required"
        )


class ArtifactVersionNotFound(Exception):
    """A requested artifact version does not exist for the variant (ADR-0009)."""

    def __init__(self, voice_id: str, model_id: str, version: int) -> None:
        super().__init__(
            f"No artifact version {version} for voice '{voice_id}' on '{model_id}'"
        )


class UnsupportedTags(Exception):
    def __init__(self, tags: list[str]) -> None:
        self.tags = tags
        super().__init__(f"Unsupported tags: {tags}")


class UnsupportedCapability(Exception):
    def __init__(self, missing: set[str]) -> None:
        self.missing = missing
        super().__init__(f"Missing capabilities: {sorted(missing)}")


@dataclass(frozen=True)
class Resolution:
    voice: Voice
    model: ModelDescriptor
    variant: VoiceVariant
    adapter: ModelAdapter


class PeakVoxRuntime:
    """Resolves and orchestrates generation across registered model adapters."""

    def __init__(self) -> None:
        self._adapters: dict[str, ModelAdapter] = {}
        self._provider_voice_registry: ProviderVoiceRegistry = ProviderVoiceRegistry()

    # --- Adapter registry ---------------------------------------------------------

    def register_adapter(self, adapter: ModelAdapter) -> None:
        self._adapters[adapter.model_id] = adapter
        if isinstance(adapter, ProviderVoiceCatalog):
            self._provider_voice_registry.register_many(adapter.list_provider_voices())

    def get_adapter(self, model_id: str) -> ModelAdapter:
        try:
            return self._adapters[model_id]
        except KeyError:
            raise ModelNotRegistered(model_id)

    def list_adapters(self) -> list[ModelAdapter]:
        return list(self._adapters.values())

    # --- Provider voice registry delegations ------------------------------------

    def register_provider_voice(self, voice: ProviderVoice) -> None:
        self._provider_voice_registry.register(voice)

    def register_provider_voices(self, voices: list[ProviderVoice]) -> None:
        self._provider_voice_registry.register_many(voices)

    def list_provider_voices(
        self, provider_id: Optional[str] = None
    ) -> list[ProviderVoice]:
        if provider_id is not None:
            return self._provider_voice_registry.list_by_provider(provider_id)
        return self._provider_voice_registry.list_all()

    # --- Readiness / concurrency (so endpoints never poke providers directly) ------

    @property
    def is_generating(self) -> bool:
        """True while a generation holds the single-flight lock (delegated to the registry)."""
        from app.services.model_registry import model_registry

        return model_registry.is_generating

    async def is_ready(self) -> bool:
        """True when the runtime can serve — the default model adapter reports healthy."""
        if not self._adapters:
            return False
        try:
            default = self.resolve_model(None)
        except ModelNotRegistered:
            return False
        return await self.get_adapter(default.id).health_check()

    def resolve_model(self, model_id: Optional[str]) -> ModelDescriptor:
        """Resolve a model id to its descriptor; ``None`` → the default adapter's model."""
        if model_id is not None:
            return self.get_adapter(model_id).descriptor
        for adapter in self._adapters.values():
            if adapter.descriptor.is_default:
                return adapter.descriptor
        if self._adapters:
            return next(iter(self._adapters.values())).descriptor
        raise ModelNotRegistered("no adapters registered")

    # --- Edition-scoped availability (ADR-0005; never name-driven) ----------------

    def is_available(self, model_id: str, edition: Optional[str] = None) -> bool:
        """True if the model is available in ``edition`` (defaults to the active edition)."""
        edition = edition or settings.EDITION
        descriptor = self.get_adapter(model_id).descriptor
        return edition in (descriptor.editions or [])

    def ensure_available(self, model_id: str, edition: Optional[str] = None) -> None:
        edition = edition or settings.EDITION
        if not self.is_available(model_id, edition):
            raise ModelNotAvailableInEdition(model_id, edition)

    def ensure_active(self, model_id: str) -> None:
        descriptor = self.get_adapter(model_id).descriptor
        if descriptor.activation_status != "active":
            raise ModelNotActive(model_id, descriptor.status)

    # --- Capability / tag validation (capability-driven, never name-driven) -------

    def validate_tags(self, model_id: str, text: str) -> list[str]:
        adapter = self.get_adapter(model_id)
        return find_unsupported_tags(text, adapter.get_supported_tags())

    def missing_capabilities(self, model_id: str, required: set[str]) -> set[str]:
        adapter = self.get_adapter(model_id)
        return _missing_caps(adapter.get_capabilities(), set(required))

    # --- Resolution ---------------------------------------------------------------

    async def resolve(
        self, db: AsyncSession, *, public_voice_id: str, model_id: Optional[str]
    ) -> Resolution:
        """Resolve ``Voice + Model → VoiceVariant`` for a stable public voice id."""
        descriptor = self.resolve_model(model_id)
        self.ensure_available(descriptor.id)
        adapter = self.get_adapter(descriptor.id)
        voice = await get_voice_identity_by_public_id(db, public_voice_id)
        if voice is None:
            raise VoiceNotFound(public_voice_id)
        variant = await resolve_variant(db, voice_id=voice.id, model_id=descriptor.id)
        if variant is None:
            raise VariantUnavailable(
                f"No variant for voice '{public_voice_id}' on model '{descriptor.id}'"
            )
        return Resolution(voice=voice, model=descriptor, variant=variant, adapter=adapter)

    # --- Variant build lifecycle (ADR-0008) + artifact versioning (ADR-0009) ------
    #
    # The Runtime owns variant existence: it dispatches builds to adapters, records the
    # resulting artifact as a versioned row, flips the active pointer, and enforces retention.
    # Adapters only *produce* artifacts; they never decide lifecycle state. Builds are
    # synchronous here (the CE-appropriate path); an async build queue is deferred to platform
    # scale (ADR-0008 Option 3 / Phase 10+).

    async def _run_build(
        self, db: AsyncSession, *, voice: Voice, model_id: str
    ) -> VoiceVariant:
        """Dispatch a build to the adapter, version the artifact, and activate it.

        On adapter failure the variant is left in ``failed`` with an error message and a
        :class:`VariantBuildFailed` is raised (the failure is a tracked, recoverable state).
        """
        self.ensure_available(model_id)
        adapter = self.get_adapter(model_id)
        try:
            variant = await adapter.build_variant(db=db, voice=voice)
        except Exception as exc:  # adapter build error — record and surface
            existing = await resolve_variant(db, voice_id=voice.id, model_id=model_id)
            if existing is not None:
                existing.status = VariantStatus.FAILED
                existing.error_message = str(exc)
                await db.commit()
            raise VariantBuildFailed(voice.id, model_id, str(exc)) from exc

        # Version the artifact the adapter just produced and make it active (ADR-0009 §3).
        artifact = await append_artifact(
            db,
            variant_id=variant.id,
            storage_keys=variant.artifacts,
            model_version=variant.model_version,
        )
        await set_active(db, variant, artifact)
        variant.status = VariantStatus.READY
        variant.error_message = None
        await db.commit()
        await db.refresh(variant)

        # CE retention: keep the active version plus the last N (ADR-0009 §6).
        await prune_artifacts(db, variant)
        return variant

    async def build_variant(
        self, db: AsyncSession, *, voice: Voice, model_id: str
    ) -> VoiceVariant:
        """Build (or first-build) this model's variant for ``voice``; returns it ``ready``."""
        return await self._run_build(db, voice=voice, model_id=model_id)

    async def rebuild_variant(
        self, db: AsyncSession, *, voice: Voice, model_id: str
    ) -> VoiceVariant:
        """Rebuild an existing variant — appends a new artifact version, preserving the old
        one for rollback (ADR-0009 §3). The new version becomes active on success."""
        return await self._run_build(db, voice=voice, model_id=model_id)

    async def get_variant_status(
        self, db: AsyncSession, *, voice: Voice, model_id: str
    ) -> Optional[str]:
        """The variant's lifecycle status, or ``None`` if no variant exists yet."""
        variant = await resolve_variant(db, voice_id=voice.id, model_id=model_id)
        return variant.status if variant is not None else None

    async def ensure_variant(
        self, db: AsyncSession, *, voice: Voice, model_id: str
    ) -> VoiceVariant:
        """Return a ``ready`` variant or take the correct lifecycle action (ADR-0008).

        ready → return · missing/pending → build · building → in-progress · failed/deprecated →
        actionable error. This is the resolution guard the generation path can call before
        running inference.
        """
        variant = await resolve_variant(db, voice_id=voice.id, model_id=model_id)
        if variant is None or variant.status == VariantStatus.PENDING:
            return await self._run_build(db, voice=voice, model_id=model_id)
        if variant.status == VariantStatus.READY:
            return variant
        if variant.status == VariantStatus.BUILDING:
            raise VariantBuilding(voice.id, model_id)
        if variant.status == VariantStatus.FAILED:
            raise VariantBuildFailed(voice.id, model_id, variant.error_message)
        if variant.status == VariantStatus.DEPRECATED:
            raise VariantDeprecated(voice.id, model_id)
        # Unknown/forward-compatible status — treat as unavailable rather than guessing.
        raise VariantUnavailable(
            f"Variant for voice '{voice.id}' on '{model_id}' has status '{variant.status}'"
        )

    async def get_active_artifact(self, db: AsyncSession, *, voice: Voice, model_id: str):
        """The variant's active artifact version metadata, or ``None``."""
        variant = await resolve_variant(db, voice_id=voice.id, model_id=model_id)
        if variant is None:
            return None
        return await get_active_artifact(db, variant)

    async def list_artifact_versions(self, db: AsyncSession, *, voice: Voice, model_id: str):
        """Ordered artifact version history for the variant (empty if none)."""
        variant = await resolve_variant(db, voice_id=voice.id, model_id=model_id)
        if variant is None:
            return []
        return await list_versions(db, variant.id)

    async def rollback_artifact(
        self, db: AsyncSession, *, voice: Voice, model_id: str, version: int
    ) -> VoiceVariant:
        """Set the active artifact to a prior ``version`` without rebuilding (ADR-0009 §4)."""
        variant = await resolve_variant(db, voice_id=voice.id, model_id=model_id)
        if variant is None:
            raise VariantUnavailable(f"No variant for voice '{voice.id}' on '{model_id}'")
        target = await get_version(db, variant.id, version)
        if target is None:
            raise ArtifactVersionNotFound(voice.id, model_id, version)
        await set_active(db, variant, target)
        return variant

    async def prune_artifacts(
        self, db: AsyncSession, *, voice: Voice, model_id: str, keep_count: Optional[int] = None
    ) -> list[str]:
        """Enforce artifact retention for the variant; returns pruned artifact ids."""
        variant = await resolve_variant(db, voice_id=voice.id, model_id=model_id)
        if variant is None:
            return []
        return await prune_artifacts(db, variant, keep_count)

    # --- Generation (single entry point) ------------------------------------------

    async def generate(
        self,
        db: AsyncSession,
        *,
        text: str,
        output_path: Path,
        model_id: Optional[str] = None,
        public_voice_id: Optional[str] = None,
        voice_profile_id: Optional[str] = None,
        voice_id: Optional[str] = None,
        ref_audio_path: Optional[str] = None,
        ref_text: Optional[str] = None,
        language: Optional[str] = None,
        instruct: Optional[str] = None,
        params: Optional[dict] = None,
        job_id: Optional[str] = None,
        required_capabilities: Optional[set[str]] = None,
    ) -> tuple[float, list[str]]:
        descriptor = self.resolve_model(model_id)
        self.ensure_available(descriptor.id)
        self.ensure_active(descriptor.id)
        adapter = self.get_adapter(descriptor.id)

        # Capability-driven validation — no model-name branching.
        bad_tags = find_unsupported_tags(text, adapter.get_supported_tags())
        if bad_tags:
            raise UnsupportedTags(bad_tags)
        if required_capabilities:
            missing = _missing_caps(adapter.get_capabilities(), set(required_capabilities))
            if missing:
                raise UnsupportedCapability(missing)

        # Single voice resolution path: always resolve through DB.
        variant_params: dict = {}
        if public_voice_id is not None:
            resolution = await self.resolve(
                db, public_voice_id=public_voice_id, model_id=descriptor.id
            )
            artifacts = resolution.variant.artifacts or {}
            variant_params = resolution.variant.params or {}
            ref_audio_path = ref_audio_path or artifacts.get("audio")
            ref_text = ref_text if ref_text is not None else variant_params.get("transcript")
            voice_id = voice_id or resolution.voice.id
            voice_profile_id = voice_profile_id or resolution.voice.id
            resolved_voice_id = voice_id or voice_profile_id
        else:
            resolved_voice_id = voice_id or voice_profile_id

        # Merge variant params into the params dict (not as top-level kwargs)
        # so adapters can read provider/preset_name for preset voices without
        # receiving generation settings (num_step, guidance_scale, etc.) as
        # unexpected keyword arguments that crash strict-sig adapters.
        merged_params = params or {}
        if variant_params:
            merged_params = {**variant_params, **(params or {})}

        return await adapter.generate(
            text=text,
            output_path=output_path,
            voice_profile_id=resolved_voice_id,
            ref_audio_path=ref_audio_path,
            ref_text=ref_text,
            language=language,
            instruct=instruct,
            params=merged_params,
            job_id=job_id,
        )


# Process-wide runtime singleton (adapters registered at wiring time).
runtime = PeakVoxRuntime()

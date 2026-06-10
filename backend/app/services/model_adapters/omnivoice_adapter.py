"""OmniVoice-family ModelAdapters.

``OmniVoiceAdapter`` (Base) and ``OmniVoiceSingingAdapter`` (Singing + Emotion) share
one variant shape (reference-audio cloning) but advertise different capabilities
and tags via their descriptors. Both implement the same :class:`ModelAdapter` contract.

Lifecycle is managed exclusively by the RuntimeManager → DockerRuntimeDriver → OmniVoice
runtime container. There is no in-process execution path. Data/variant methods are torch-free.
"""

from __future__ import annotations

import logging
import uuid
import wave as _wave
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import Voice, VoiceVariant
from app.services.adapter_transport.http_transport import HTTPTransport, HTTPTransportError
from app.services.model_adapter import ModelAdapter, VariantBuildStrategy

logger = logging.getLogger(__name__)


class OmniVoiceFamilyAdapter(ModelAdapter):
    """Shared behavior for OmniVoice-family models."""

    # --- Lifecycle (owned by RuntimeManager → runtime container) -----------------

    async def install(self) -> None:
        return None

    async def load(self) -> None:
        return None

    def unload(self) -> None:
        return None

    async def health_check(self) -> bool:
        return False

    @staticmethod
    def get_build_strategies() -> list[VariantBuildStrategy]:
        return [
            VariantBuildStrategy(
                creation_source="SOURCE_ASSET",
                can_build=True,
                requires=["source_asset"],
                description="OmniVoice clones a voice from reference audio.",
            ),
        ]

    # --- Runtime-service generation ──────────────────────────────────────────

    def _get_transport(self, base_url: str) -> HTTPTransport:
        existing = getattr(self, "_transport", None)
        if existing is not None and existing.base_url == base_url:
            return existing
        # 600s: OmniVoice is a 0.6B LLM that runs on CPU in CE — inference can take
        # minutes per request. The default 30s transport timeout is far too short.
        transport = HTTPTransport(base_url=base_url, bearer_token="", timeout_seconds=600.0)
        self._transport = transport  # type: ignore[attr-defined]
        return transport

    async def generate(
        self,
        *,
        text: str,
        output_path: Path,
        voice_profile_id: Optional[str] = None,
        voice_id: Optional[str] = None,
        ref_audio_path: Optional[str] = None,
        ref_text: Optional[str] = None,
        language: Optional[str] = None,
        instruct: Optional[str] = None,
        params: Optional[dict] = None,
        job_id: Optional[str] = None,
        runtime_endpoint: Optional[str] = None,
    ) -> tuple[float, list[str]]:
        if runtime_endpoint is None:
            raise RuntimeError(
                f"OmniVoice in-process execution is not available. "
                f"Start the '{self.model_id}' runtime container via the Models page."
            )

        transport = self._get_transport(runtime_endpoint)
        merged_params: dict[str, Any] = dict(params or {})
        if ref_audio_path is not None:
            merged_params["ref_audio_path"] = ref_audio_path
        if ref_text is not None:
            merged_params["ref_text"] = ref_text
        if instruct is not None:
            merged_params["instruct"] = instruct

        request_body: dict[str, Any] = {
            "text": text,
            "voice_id": voice_id or voice_profile_id or "default",
            "language": language or "auto",
            "params": merged_params,
            "request_id": job_id or str(uuid.uuid4()),
        }

        try:
            wav_bytes, headers = await transport.post_binary("/v1/generate", request_body)
        except HTTPTransportError as exc:
            raise RuntimeError(f"OmniVoice runtime error: {exc}") from exc

        output_path.write_bytes(wav_bytes)

        duration_ms_str = headers.get("x-peakvox-duration-ms")
        if duration_ms_str is not None:
            duration = float(duration_ms_str) / 1000.0
        else:
            try:
                with _wave.open(str(output_path)) as wf:
                    duration = wf.getnframes() / wf.getframerate()
            except Exception:
                duration = 0.0

        logs = [
            f"OmniVoice: routed via runtime {runtime_endpoint} → {output_path.name} "
            f"({'cloning' if ref_audio_path else 'voice design' if instruct else 'default'})"
        ]
        return duration, logs

    # --- Voice realization (torch-free: reference-audio reuse) ---------------------

    async def _upsert_variant(
        self, db: AsyncSession, *, voice: Voice, audio_key: Optional[str],
        transcript: Optional[str], source: str, status: Optional[str] = None,
    ) -> VoiceVariant:
        existing = (
            await db.execute(
                select(VoiceVariant).where(
                    VoiceVariant.voice_id == voice.id,
                    VoiceVariant.model_id == self.model_id,
                )
            )
        ).scalar_one_or_none()
        artifacts = {"audio": audio_key}
        params = {"transcript": transcript, "generation_defaults": {}}
        if existing is None:
            existing = VoiceVariant(
                voice_id=voice.id,
                model_id=self.model_id,
                artifact_type="reference_sample",
                artifacts=artifacts,
                params=params,
                source=source,
            )
            if status:
                existing.status = status
            db.add(existing)
        else:
            existing.artifacts = artifacts
            existing.params = params
            existing.source = source
            if status:
                existing.status = status
        await db.commit()
        await db.refresh(existing)
        return existing

    async def clone_voice(
        self, *, db: AsyncSession, voice: Voice, reference_audio_key: str
    ) -> VoiceVariant:
        """Create this model's variant from an explicit reference clip."""
        return await self._upsert_variant(
            db, voice=voice, audio_key=reference_audio_key, transcript=None, source="cloned", status="ready"
        )

    async def build_variant(self, *, db: AsyncSession, voice: Voice) -> VoiceVariant:
        """(Re)build this model's variant from the voice's canonical sources.

        OmniVoice-family models clone from reference audio, so a variant reuses the voice's
        existing reference (and transcript) — no new artifacts, no new ``public_voice_id``.
        """
        canonical = (
            await db.execute(select(VoiceVariant).where(VoiceVariant.voice_id == voice.id))
        ).scalars().first()
        audio_key = (canonical.artifacts or {}).get("audio") if canonical else voice.preview_audio
        transcript = (canonical.params or {}).get("transcript") if canonical else None
        return await self._upsert_variant(
            db, voice=voice, audio_key=audio_key, transcript=transcript, source="regenerated"
        )


class OmniVoiceAdapter(OmniVoiceFamilyAdapter):
    """OmniVoice Base — TTS, cloning, emotion tags, voice design."""


class OmniVoiceSingingAdapter(OmniVoiceFamilyAdapter):
    """OmniVoice Singing + Emotion — adds sung delivery + the rich emotion tag set."""

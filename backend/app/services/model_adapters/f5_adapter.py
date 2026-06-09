"""F5TTSAdapter — reference-audio voice cloning via the F5-TTS runtime container.

F5-TTS (SWivid/F5-TTS) is a flow-matching TTS model. Every generation routes
through the F5-TTS runtime container via HTTPTransport — no in-process inference.

Voice cloning mechanism:
  F5-TTS accepts a reference audio clip (WAV) at inference time. The VoiceVariant
  stores the reference audio key from the voice's Source Asset. At generation
  time, the key is resolved to a local temp file and passed to the runtime via
  the params dict — same pattern as OmniVoice.

Voice-optional generation:
  When no reference audio is provided (voice_optional mode), the request is sent
  without ref_audio_path. The F5-TTS runtime uses its bundled default voice.
  Declared via supports_voice_optional=True in ModelCapabilities.
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


class F5TTSAdapter(ModelAdapter):
    """Adapter for F5-TTS (flow-matching TTS). Routes exclusively via runtime container.

    Lifecycle is owned by RuntimeManager → DockerRuntimeDriver → F5-TTS container.
    This adapter owns only: build strategy declaration, variant building (reference
    audio storage pointer), and generation routing (HTTPTransport to the container).
    """

    # ── Realization type ─────────────────────────────────────────────────────

    @property
    def supported_realization_types(self) -> list[str]:
        return ["reference_sample"]

    @staticmethod
    def get_build_strategies() -> list[VariantBuildStrategy]:
        return [
            VariantBuildStrategy(
                creation_source="SOURCE_ASSET",
                can_build=True,
                requires=["source_asset"],
                description="F5-TTS clones a voice from reference audio at inference time.",
            ),
        ]

    # ── Lifecycle (owned by RuntimeManager → runtime container) ──────────────

    async def install(self) -> None:
        return None

    async def load(self) -> None:
        return None

    def unload(self) -> None:
        return None

    async def health_check(self) -> bool:
        return False

    # ── Runtime-service generation ────────────────────────────────────────────

    def _get_transport(self, base_url: str) -> HTTPTransport:
        existing = getattr(self, "_transport", None)
        if existing is not None and existing.base_url == base_url:
            return existing
        transport = HTTPTransport(base_url=base_url, bearer_token="")
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
                f"F5-TTS in-process execution is not available. "
                f"Start the '{self.model_id}' runtime container via the Models page."
            )

        transport = self._get_transport(runtime_endpoint)
        merged_params: dict[str, Any] = dict(params or {})
        if ref_audio_path is not None:
            merged_params["ref_audio_path"] = ref_audio_path
        if ref_text is not None:
            merged_params["ref_text"] = ref_text

        request_body: dict[str, Any] = {
            "text": text,
            "voice_id": voice_id or voice_profile_id or "default",
            "language": language or "en",
            "params": merged_params,
            "request_id": job_id or str(uuid.uuid4()),
        }

        try:
            wav_bytes, headers = await transport.post_binary("/v1/generate", request_body)
        except HTTPTransportError as exc:
            raise RuntimeError(f"F5-TTS runtime error: {exc}") from exc

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
            f"F5-TTS: routed via runtime {runtime_endpoint} -> {output_path.name} "
            f"({'cloning from ref' if ref_audio_path else 'default voice'})"
        ]
        return duration, logs

    # ── Voice realization ─────────────────────────────────────────────────────

    async def _upsert_variant(
        self,
        db: AsyncSession,
        *,
        voice: Voice,
        audio_key: Optional[str],
        transcript: Optional[str],
        source: str,
        status: Optional[str] = None,
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
        params = {"transcript": transcript}
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
        return await self._upsert_variant(
            db,
            voice=voice,
            audio_key=reference_audio_key,
            transcript=None,
            source="cloned",
            status="ready",
        )

    async def build_variant(self, *, db: AsyncSession, voice: Voice) -> VoiceVariant:
        """Build the F5-TTS variant by registering the voice's reference audio.

        F5-TTS clones at inference time; no pre-computation required. The variant
        records the reference audio key so generation can resolve it.
        """
        canonical = (
            await db.execute(
                select(VoiceVariant).where(VoiceVariant.voice_id == voice.id)
            )
        ).scalars().first()
        audio_key = (
            (canonical.artifacts or {}).get("audio")
            if canonical
            else getattr(voice, "preview_audio", None)
        )
        transcript = (canonical.params or {}).get("transcript") if canonical else None
        return await self._upsert_variant(
            db,
            voice=voice,
            audio_key=audio_key,
            transcript=transcript,
            source="regenerated",
        )

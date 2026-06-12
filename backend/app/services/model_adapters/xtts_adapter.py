"""XTTSAdapter — reference-audio voice cloning via the XTTS v2 runtime container.

Coqui XTTS v2 (``coqui/XTTS-v2``) is a multilingual zero-shot voice-cloning TTS.
Every generation routes through the XTTS runtime container via HTTPTransport —
no in-process inference (Constitution Art. III §9). This adapter is a sibling of
:class:`F5TTSAdapter`: same ``reference_sample`` realization, same runtime-routed
generation, same build strategy.

Voice cloning mechanism:
  XTTS accepts a reference audio clip (WAV, ~6 s) at inference time. The
  VoiceVariant stores the reference audio key from the voice's Source Asset. At
  generation time the key is resolved to a local temp file and passed to the
  runtime via the params dict (``ref_audio_path``) — the same pattern as
  OmniVoice and F5-TTS.

Voice-optional generation:
  When no reference audio is provided (voice_optional mode), the request is sent
  without ``ref_audio_path`` and the XTTS runtime falls back to a built-in studio
  speaker. Declared via ``supports_voice_optional=True`` in ModelCapabilities.

GPU / CPU:
  XTTS is CPU-capable; the runtime container selects CUDA or CPU based on the
  global "Use GPU (CUDA)" setting (honored by the Docker driver). The adapter is
  device-agnostic — it just routes to the runtime endpoint.
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


class XTTSAdapter(ModelAdapter):
    """Adapter for Coqui XTTS v2. Routes exclusively via the runtime container.

    Lifecycle is owned by RuntimeManager → DockerRuntimeDriver → XTTS container.
    This adapter owns only: build strategy declaration, variant building
    (reference audio storage pointer), and generation routing (HTTPTransport to
    the container).
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
                description="XTTS v2 clones a voice from reference audio at inference time.",
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
        # 600s: XTTS on CPU (Use GPU OFF) is markedly slower than on GPU, and
        # long texts split into many chunks, so a generation can far exceed the
        # 30s default. Match the F5-TTS posture so a slow CPU run is not killed
        # mid-inference (which would also leave the serialized engine busy).
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
                f"XTTS in-process execution is not available. "
                f"Start the '{self.model_id}' runtime container via the Models page."
            )

        transport = self._get_transport(runtime_endpoint)
        merged_params: dict[str, Any] = dict(params or {})
        if ref_audio_path is not None:
            merged_params["ref_audio_path"] = ref_audio_path

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
            raise RuntimeError(f"XTTS runtime error: {exc}") from exc

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
            f"XTTS: routed via runtime {runtime_endpoint} -> {output_path.name} "
            f"({'cloning from ref' if ref_audio_path else 'built-in speaker'})"
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
        """Build the XTTS variant by registering the voice's reference audio.

        XTTS clones at inference time; no pre-computation required. The variant
        records the reference audio key so generation can resolve it. (Precomputing
        XTTS speaker latents as a variant artifact is a documented future
        optimization — see ADR-0021 / task-30 discovery §6.)
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

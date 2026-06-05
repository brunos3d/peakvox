"""FishAudioAdapter — first non-OmniVoice provider validated via the ModelAdapter contract.

Fish Audio S2 Pro connects to a remote HTTP server (api_server.py or SGLang Omni) for
inference — no heavyweight runtime is imported into the PeakVox backend process.

Voice conditioning mechanism (corrected per P0 provider validation):
  Fish Audio uses **reference audio**, not pre-computed speaker embeddings. The VQ encoding
  (DAC codec) that produces speaker features is a model-internal step performed at inference
  time by the server. The variant stores the reference audio path — same pattern as OmniVoice.
  See ``docs/architecture/12-PROVIDER-VALIDATION.md`` §3.2 for the audit trail.

Architecture rule (ADR-0004): Fish-specific details live entirely inside this adapter and the
variant; never exposed on the public API.
"""

from __future__ import annotations

import base64
import json
import logging
import wave
from pathlib import Path
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.db import Voice, VoiceVariant
from app.services.model_adapter import ModelAdapter

logger = logging.getLogger(__name__)


class FishAudioAdapter(ModelAdapter):
    """Adapter for Fish Audio S2 Pro (CE-only). Connects to a remote HTTP server for inference.

    The server runs independently (api_server.py or SGLang Omni); this adapter speaks
    the standard Fish Audio ``/v1/tts`` JSON API. No torch or fish-speech deps are imported.
    """

    def __init__(self, descriptor):
        super().__init__(descriptor)
        self._server_healthy: bool = False
        self._http_client: httpx.AsyncClient | None = None

    @property
    def supported_realization_types(self) -> list[str]:
        return ["reference_sample"]

    @property
    def _server_url(self) -> str:
        return settings.FISH_AUDIO_SERVER_URL

    def _client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=120.0)
        return self._http_client

    # --- Lifecycle ----------------------------------------------------------------

    async def install(self) -> None:
        return None

    async def load(self) -> None:
        logger.info("FishAudioAdapter: verifying server at %s", self._server_url)
        try:
            async with httpx.AsyncClient(timeout=10.0) as c:
                resp = await c.get(f"{self._server_url}/v1/health")
            self._server_healthy = resp.status_code == 200 and resp.json().get("status") == "ok"
            if self._server_healthy:
                logger.info("FishAudioAdapter: server is healthy")
            else:
                logger.warning("FishAudioAdapter: server returned unhealthy status")
        except Exception as exc:
            self._server_healthy = False
            logger.warning("FishAudioAdapter: server unreachable (%s)", exc)

    def unload(self) -> None:
        self._server_healthy = False

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as c:
                resp = await c.get(f"{self._server_url}/v1/health")
            return resp.status_code == 200
        except Exception:
            return False

    # --- Inference ---------------------------------------------------------------

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
    ) -> tuple[float, list[str]]:
        logs: list[str] = []

        if not self._server_healthy:
            raise RuntimeError(
                "Fish Audio server is not healthy. Start the server or check "
                "FISH_AUDIO_SERVER_URL."
            )

        if not ref_audio_path:
            raise ValueError("Fish Audio requires reference audio for voice cloning")

        ref_path = Path(ref_audio_path)
        if not ref_path.exists():
            raise FileNotFoundError(f"Reference audio not found: {ref_audio_path}")

        ref_audio_bytes = ref_path.read_bytes()
        ref_text_content = ref_text or ""
        p = params or {}

        # Build the request body matching the Fish Audio /v1/tts JSON schema.
        # Audio is base64-encoded (the server's ServeReferenceAudio model_validator
        # decodes base64 strings automatically). No ormsgpack dependency needed.
        body = {
            "text": text,
            "references": [
                {
                    "audio": base64.b64encode(ref_audio_bytes).decode("ascii"),
                    "text": ref_text_content,
                }
            ],
            "format": "wav",
            "streaming": False,
            "max_new_tokens": p.get("max_new_tokens", 1024),
            "top_p": p.get("top_p", 0.8),
            "repetition_penalty": p.get("repetition_penalty", 1.1),
            "temperature": p.get("temperature", 0.8),
            "seed": p.get("seed"),
            "chunk_length": p.get("chunk_length", 200),
        }
        body = {k: v for k, v in body.items() if v is not None}

        logs.append(f"Fish Audio: requesting {self._server_url}/v1/tts")

        try:
            client = self._client()
            response = await client.post(
                f"{self._server_url}/v1/tts",
                content=json.dumps(body),
                headers={"content-type": "application/json"},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logs.append(f"Fish Audio server returned {exc.response.status_code}")
            raise RuntimeError(
                f"Fish Audio server error: {exc.response.status_code} "
                f"{exc.response.text[:500]}"
            ) from exc
        except httpx.RequestError as exc:
            logs.append(f"Fish Audio server unreachable: {exc}")
            raise RuntimeError(f"Fish Audio server request failed: {exc}") from exc

        output_path.write_bytes(response.content)

        try:
            with wave.open(str(output_path), "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                duration = frames / rate if rate > 0 else 0.0
        except Exception:
            duration = 0.0

        logs.append(f"Audio generated: {duration:.2f}s -> {output_path.name}")
        return duration, logs

    # --- Voice realization -------------------------------------------------------

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
        vparams = {"transcript": transcript, "generation_defaults": {}}
        if existing is None:
            existing = VoiceVariant(
                voice_id=voice.id,
                model_id=self.model_id,
                artifact_type="reference_sample",
                artifacts=artifacts,
                params=vparams,
                source=source,
            )
            if status:
                existing.status = status
            db.add(existing)
        else:
            existing.artifact_type = "reference_sample"
            existing.artifacts = artifacts
            existing.params = vparams
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
            db, voice=voice, audio_key=reference_audio_key, transcript=None,
            source="cloned", status="ready",
        )

    async def build_variant(self, *, db: AsyncSession, voice: Voice) -> VoiceVariant:
        canonical = (
            await db.execute(select(VoiceVariant).where(VoiceVariant.voice_id == voice.id))
        ).scalars().first()
        audio_key = (canonical.artifacts or {}).get("audio") if canonical else voice.preview_audio
        transcript = (canonical.params or {}).get("transcript") if canonical else None
        return await self._upsert_variant(
            db, voice=voice, audio_key=audio_key, transcript=transcript, source="regenerated",
        )

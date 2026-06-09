from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any, Optional

from app.services.adapter_transport.http_transport import (
    HTTPTransport,
    HTTPTransportError,
)
from app.services.model_adapter import ModelAdapter, VariantBuildStrategy
from app.services.provider_voice import (
    ProviderVoice,
    ProviderVoiceCatalog,
    build_provider_voice_id,
)

logger = logging.getLogger(__name__)

# Lazy import — kokoro may not be installed at import time.
try:
    import kokoro as _kokoro_mod  # type: ignore[no-redef]
except ImportError:
    _kokoro_mod = None  # type: ignore[assignment]


# ── 54 preset voice definitions ──────────────────────────────────────────
# Source: https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md
# Language prefix → language code
_LANG_MAP: dict[str, str] = {
    "a": "en-us",
    "b": "en-gb",
    "e": "es",
    "f": "fr",
    "h": "hi",
    "i": "it",
    "j": "ja",
    "k": "ko",
    "p": "pt",
    "z": "zh",
}

_GENDER_MAP: dict[str, str] = {
    "f": "female",
    "m": "male",
}

_KOKORO_VOICES: list[tuple[str, str, str]] = [
    # American English — female
    ("af_alloy", "Alloy", "en-us"),
    ("af_aoede", "Aoede", "en-us"),
    ("af_bella", "Bella", "en-us"),
    ("af_heart", "Heart", "en-us"),
    ("af_jessica", "Jessica", "en-us"),
    ("af_kore", "Kore", "en-us"),
    ("af_nicole", "Nicole", "en-us"),
    ("af_nova", "Nova", "en-us"),
    ("af_river", "River", "en-us"),
    ("af_sarah", "Sarah", "en-us"),
    ("af_sky", "Sky", "en-us"),
    # American English — male
    ("am_adam", "Adam", "en-us"),
    ("am_echo", "Echo", "en-us"),
    ("am_eric", "Eric", "en-us"),
    ("am_fenrir", "Fenrir", "en-us"),
    ("am_liam", "Liam", "en-us"),
    ("am_michael", "Michael", "en-us"),
    ("am_onyx", "Onyx", "en-us"),
    ("am_puck", "Puck", "en-us"),
    ("am_santa", "Santa", "en-us"),
    # British English — female
    ("bf_alice", "Alice", "en-gb"),
    ("bf_emma", "Emma", "en-gb"),
    ("bf_isabella", "Isabella", "en-gb"),
    ("bf_lily", "Lily", "en-gb"),
    # British English — male
    ("bm_daniel", "Daniel", "en-gb"),
    ("bm_fable", "Fable", "en-gb"),
    ("bm_george", "George", "en-gb"),
    ("bm_lewis", "Lewis", "en-gb"),
    # Spanish
    ("ef_dora", "Dora", "es"),
    ("em_alex", "Alex", "es"),
    ("em_santa", "Santa", "es"),
    # French
    ("ff_siwis", "Siwis", "fr"),
    # Hindi
    ("hf_alpha", "Alpha", "hi"),
    ("hf_beta", "Beta", "hi"),
    ("hm_omega", "Omega", "hi"),
    ("hm_psi", "Psi", "hi"),
    # Italian
    ("if_sara", "Sara", "it"),
    ("im_nicola", "Nicola", "it"),
    # Japanese
    ("jf_alpha", "Alpha", "ja"),
    ("jf_gongitsune", "Gongitsune", "ja"),
    ("jf_nezumi", "Nezumi", "ja"),
    ("jf_tebukuro", "Tebukuro", "ja"),
    ("jm_kumo", "Kumo", "ja"),
    # Brazilian Portuguese
    ("pf_dora", "Dora", "pt"),
    ("pm_alex", "Alex", "pt"),
    ("pm_santa", "Santa", "pt"),
    # Mandarin Chinese
    ("zf_xiaobei", "Xiaobei", "zh"),
    ("zf_xiaoni", "Xiaoni", "zh"),
    ("zf_xiaoxiao", "Xiaoxiao", "zh"),
    ("zf_xiaoyi", "Xiaoyi", "zh"),
    ("zm_yunjian", "Yunjian", "zh"),
    ("zm_yunxi", "Yunxi", "zh"),
    ("zm_yunxia", "Yunxia", "zh"),
    ("zm_yunyang", "Yunyang", "zh"),
]


def _gender(external_id: str) -> str | None:
    lang_prefix = external_id[1] if len(external_id) > 1 else ""
    return _GENDER_MAP.get(lang_prefix)


def _lang_code(external_id: str) -> str:
    prefix = external_id[0]
    return _LANG_MAP.get(prefix, "en-us")


def _build_voices() -> list[ProviderVoice]:
    return [
        ProviderVoice(
            provider_voice_id=build_provider_voice_id("kokoro", external_id),
            provider_id="kokoro",
            external_id=external_id,
            name=name,
            description=f"Kokoro preset: {name} ({language})",
            language=language,
            gender=_gender(external_id),
        )
        for external_id, name, language in _KOKORO_VOICES
    ]


class KokoroAdapter(ModelAdapter, ProviderVoiceCatalog):
    """Adapter for Kokoro-82M — open-weight TTS with 54 preset voices.

    No voice cloning, no reference audio, no embeddings. Ephemeral presets only.
    ``voice_pack`` realization: the generator receives the preset id as
    ``voice_profile_id`` (e.g. ``"af_heart"``).
    """

    def __init__(self, descriptor):
        super().__init__(descriptor)
        self._voices: list[ProviderVoice] = _build_voices()
        self._voices_by_ext: dict[str, ProviderVoice] = {
            v.external_id: v for v in self._voices
        }
        self._kokoro = None

    # --- Realization type -------------------------------------------------------

    @property
    def supported_realization_types(self) -> list[str]:
        return ["voice_pack"]

    @staticmethod
    def get_build_strategies() -> list[VariantBuildStrategy]:
        return [
            VariantBuildStrategy(
                creation_source="PRESET_VOICE",
                can_build=True,
                requires=["preset_name", "provider"],
                description="Kokoro presets are realized by selecting the preset voice pack.",
            ),
        ]

    # --- Lifecycle --------------------------------------------------------------

    def install(self) -> None:
        return None

    def load(self) -> None:
        return None

    def unload(self) -> None:
        self._kokoro = None

    def health_check(self) -> bool:
        return True

    # --- ProviderVoiceCatalog ---------------------------------------------------

    def list_provider_voices(self) -> list[ProviderVoice]:
        return list(self._voices)

    def get_provider_voice(self, external_id: str) -> ProviderVoice | None:
        return self._voices_by_ext.get(external_id)

    def has_provider_voice(self, external_id: str) -> bool:
        return external_id in self._voices_by_ext

    # --- Inference --------------------------------------------------------------

    def _get_kokoro_pipeline(self, voice_id: str):
        """Lazy-import and cache the kokoro KPipeline for the voice's language."""
        import app.services.model_adapters.kokoro_adapter as _self
        if _self._kokoro_mod is None:
            raise RuntimeError("kokoro package is not installed; run: pip install kokoro")
        if self._kokoro is None:
            self._kokoro = _self._kokoro_mod
        lang_prefix = voice_id[0] if voice_id else "a"
        if lang_prefix not in _LANG_MAP:
            lang_prefix = "a"
        return self._kokoro.KPipeline(lang_code=lang_prefix)

    # --- Runtime-service path -------------------------------------------
    #
    # When PeakVoxRuntime resolves an ACTIVE RuntimeInstance for this
    # adapter's model, it passes the endpoint URL via the
    # ``runtime_endpoint`` kwarg. The adapter routes the request to
    # that endpoint via HTTPTransport. The endpoint is NEVER read from
    # an environment variable — it is injected by the orchestration
    # layer (PeakVoxRuntime → RuntimeManager → RuntimeDriver), which
    # is the only component that owns runtime operational state.
    #
    # The runtime-service path does NOT import Docker, does NOT
    # reference RuntimeDescriptor / RuntimeInstance / RuntimeRegistry /
    # RuntimeManager, and does NOT add any new contract surface
    # beyond what the ModelAdapter base defines. It is a single
    # allowed seam: HTTPTransport. Per the Transport Boundary Audit,
    # this is the ONLY allowed seam; any other runtime-related import
    # in this file is a violation.

    def _get_runtime_transport(self, base_url: str) -> HTTPTransport:
        """Return a cached HTTPTransport for the given runtime URL."""
        existing = getattr(self, "_runtime_transport", None)
        if existing is not None and existing.base_url == base_url:
            return existing
        transport = HTTPTransport(base_url=base_url, bearer_token="")
        self._runtime_transport = transport  # type: ignore[attr-defined]
        return transport

    async def _generate_via_runtime(
        self,
        *,
        runtime_endpoint: str,
        text: str,
        output_path: Path,
        voice_profile_id: Optional[str],
        voice_id: Optional[str],
        ref_audio_path: Optional[str],
        ref_text: Optional[str],
        language: Optional[str],
        instruct: Optional[str],
        params: Optional[dict],
        job_id: Optional[str],
    ) -> tuple[float, list[str]]:
        """Route a generation request to the runtime service.

        Translates kwargs to the Runtime Service Contract (ADR-0017
        §6.3). The runtime returns ``audio/wav`` binary bytes; the
        audio is written to ``output_path`` and the duration is read
        from the ``X-Peakvox-Duration-Ms`` response header.
        """
        transport = self._get_runtime_transport(runtime_endpoint)
        preset_name = (params or {}).get("preset_name")
        request_body: dict[str, Any] = {
            "text": text,
            "voice_id": preset_name or voice_id or voice_profile_id,
            "language": language,
            "params": params or {},
            "request_id": job_id or str(uuid.uuid4()),
        }
        # Strip None entries for a cleaner request body.
        request_body = {k: v for k, v in request_body.items() if v is not None}
        # The runtime returns audio/wav binary (ADR-0017 §6.3); use
        # post_binary() to receive raw bytes and response headers.
        wav_bytes, headers = await transport.post_binary("/v1/generate", request_body)
        output_path.write_bytes(wav_bytes)
        # Duration comes from the X-Peakvox-Duration-Ms header (ms →
        # seconds). Fall back to parsing the WAV if the header is absent.
        duration_ms_str = headers.get("x-peakvox-duration-ms")
        if duration_ms_str is not None:
            duration = float(duration_ms_str) / 1000.0
        else:
            import wave as _wave
            try:
                with _wave.open(str(output_path)) as wf:
                    duration = wf.getnframes() / wf.getframerate()
            except Exception:
                duration = 0.0
        logs: list[str] = [
            f"Kokoro: routed via runtime service {runtime_endpoint} -> {output_path.name}",
        ]
        return duration, logs

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
        # Dispatch: when PeakVoxRuntime injects a runtime_endpoint
        # (the RuntimeManager found an ACTIVE instance), route to
        # the runtime service via HTTPTransport. Otherwise, use the
        # in-process kokoro package (for local dev / testing).
        if runtime_endpoint is not None:
            return await self._generate_via_runtime(
                runtime_endpoint=runtime_endpoint,
                text=text,
                output_path=output_path,
                voice_profile_id=voice_profile_id,
                voice_id=voice_id,
                ref_audio_path=ref_audio_path,
                ref_text=ref_text,
                language=language,
                instruct=instruct,
                params=params,
                job_id=job_id,
            )

        # In-process path: lazy-import soundfile + numpy so the
        # test venv (no soundfile) can still import the module.
        import soundfile as sf
        import numpy as np

        preset = (params or {}).get("preset_name") or voice_profile_id or voice_id or "af_heart"
        pipeline = self._get_kokoro_pipeline(preset)
        generator = pipeline(text, voice=preset)

        all_audio: list[np.ndarray] = []
        sample_rate = 24000
        for gs, ps, audio_tensor in generator:
            all_audio.append(audio_tensor.numpy())

        if not all_audio:
            raise RuntimeError("Kokoro generated no audio output")

        combined = np.concatenate(all_audio)
        sf.write(str(output_path), combined, sample_rate)
        duration = len(combined) / sample_rate

        logs: list[str] = [
            f"Kokoro: generated {duration:.2f}s with voice '{preset}' -> {output_path.name}",
        ]
        return duration, logs

    # --- Voice realization ------------------------------------------------------

    async def clone_voice(
        self, *, db, voice, reference_audio_key: str
    ):
        raise NotImplementedError("Kokoro does not support voice cloning")

    async def build_variant(self, *, db, voice):
        """Create a metadata-only VoiceVariant for the Kokoro preset.

        Kokoro presets require no audio processing, no embedding generation,
        no checkpoint creation. The variant exists to satisfy ADR-0008 lifecycle
        contract — all providers participate in Voice → Variant → Artifact → Generation.

        The preset name is read from voice.meta (set by POST /voices/from-preset).
        """
        from app.models.db import VoiceVariant as VV
        from sqlalchemy import select

        existing = (
            await db.execute(
                select(VV).where(
                    VV.voice_id == voice.id,
                    VV.model_id == self.model_id,
                )
            )
        ).scalars().first()

        if existing is not None:
            return existing

        meta = voice.meta or {}

        variant = VV(
            id=str(uuid.uuid4()),
            voice_id=voice.id,
            model_id=self.model_id,
            artifact_type="voice_pack",
            params={
                "provider": meta.get("provider", "kokoro"),
                "preset_name": meta.get("preset_name", ""),
            },
            artifacts={},
            source="preset",
            status="pending",
        )
        db.add(variant)
        await db.commit()
        await db.refresh(variant)
        return variant

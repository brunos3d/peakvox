"""ProviderVoice — ephemeral, in-memory preset voice identity from provider-native catalogs.

A ProviderVoice is NOT a persisted Voice record. It has no source assets, no VoiceVariants,
no artifacts, no provisioning lifecycle. It is a lightweight reference to a model-native
preset (e.g. Kokoro's af_heart, Piper's voice_1). The Runtime resolves it via the
ProviderVoiceRegistry before falling through to persisted Voice resolution.

Domain boundaries (ADR-0011):
  - ProviderVoice = model-native preset (ephemeral, no DB)
  - Voice          = persisted identity (SQL, owns assets/variants/artifacts)
  - VoiceVariant   = per-model realization of a Voice (SQL, build lifecycle)

Identity: ``voice_{provider_id}_{external_id}`` — deterministic, stable across restarts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable


# ── Identifier helper ──────────────────────────────────────────────────────


def build_provider_voice_id(provider_id: str, external_id: str) -> str:
    """Deterministic provider voice identifier — stable across restarts.

    Example: ``build_provider_voice_id("kokoro", "af_heart")`` → ``voice_kokoro_af_heart``
    """
    return f"voice_{provider_id}_{external_id}"


# ── Domain type ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ProviderVoice:
    """A model-native preset voice — ephemeral, in-memory, no DB row.

    Implements the ``VoiceResource`` catalog contract for ``resource_type="preset"``.
    ``resource_origin`` identifies the provider (e.g. ``"kokoro"``, ``"piper"``).
    ``catalog_source`` carries provenance metadata (adapter version, sync info, etc.).

    Frozen (immutable) by design: presets are fixed at compile time.
    No owner_id, no creator_id — presets are model-native, not user-owned.
    """

    provider_voice_id: str      # deterministic: build_provider_voice_id(...)
    provider_id: str            # e.g. "kokoro", "piper"
    external_id: str            # provider's native key, e.g. "af_heart"
    name: str                   # human-readable name, e.g. "Heart"
    description: str = ""
    language: Optional[str] = None
    gender: Optional[str] = None
    tags: tuple[str, ...] = ()
    is_default: bool = False
    resource_origin: str = ""   # catalog contract field; defaults to provider_id
    catalog_source: Optional[dict[str, Any]] = None  # provenance metadata

    def __post_init__(self) -> None:
        if not self.resource_origin:
            object.__setattr__(self, "resource_origin", self.provider_id)


# ── Optional adapter protocol ──────────────────────────────────────────────


@runtime_checkable
class ProviderVoiceCatalog(Protocol):
    """Optional protocol on ModelAdapter for providers with built-in preset voices.

    Use ``isinstance(adapter, ProviderVoiceCatalog)`` at wiring time to discover
    adapters that expose a preset voice catalog.
    """

    def list_provider_voices(self) -> list[ProviderVoice]:
        """All preset voices this provider offers."""
        ...

    def get_provider_voice(self, external_id: str) -> Optional[ProviderVoice]:
        """Single voice by its provider-native external_id, or None."""
        ...

    def has_provider_voice(self, external_id: str) -> bool:
        """True if a preset with the given external_id exists."""
        ...


# ── Registry ────────────────────────────────────────────────────────────────


class ProviderVoiceRegistry:
    """O(1) lookup for provider-native preset voices, keyed by ``provider_voice_id``.

    Lifecycle:
        register / register_many  – add voices at wiring time
        refresh(provider_id, …)   – atomic replace of one provider's entire set
        reload(adapters)          – full rebuild from ProviderVoiceCatalog adapters
        remove(voice_id)          – single voice
        remove_provider(id)       – all voices for a provider (model uninstall)
    """

    def __init__(self) -> None:
        self._voices: dict[str, ProviderVoice] = {}
        self._by_provider: dict[str, list[str]] = {}

    # ── Registration ──────────────────────────────────────────────────────

    def register(self, voice: ProviderVoice) -> None:
        self._voices[voice.provider_voice_id] = voice
        self._by_provider.setdefault(voice.provider_id, []).append(voice.provider_voice_id)

    def register_many(self, voices: list[ProviderVoice]) -> None:
        for v in voices:
            self.register(v)

    # ── Lookup ────────────────────────────────────────────────────────────

    def get(self, voice_id: str) -> Optional[ProviderVoice]:
        return self._voices.get(voice_id)

    def list_all(self) -> list[ProviderVoice]:
        return list(self._voices.values())

    def list_by_provider(self, provider_id: str) -> list[ProviderVoice]:
        return [self._voices[vid] for vid in self._by_provider.get(provider_id, [])]

    # ── Refresh — atomic provider-level replace ───────────────────────────

    def refresh(self, provider_id: str, voices: list[ProviderVoice]) -> None:
        old_ids = self._by_provider.pop(provider_id, [])
        for vid in old_ids:
            self._voices.pop(vid, None)
        for v in voices:
            if v.provider_id != provider_id:
                raise ValueError(
                    f"Voice provider_id mismatch: got {v.provider_id!r}, "
                    f"expected {provider_id!r}"
                )
            self._voices[v.provider_voice_id] = v
        self._by_provider[provider_id] = [v.provider_voice_id for v in voices]

    # ── Reload — full rebuild from ProviderVoiceCatalog adapters ──────────

    def reload(self, adapters: list) -> None:
        self._voices.clear()
        self._by_provider.clear()
        for adapter in adapters:
            if isinstance(adapter, ProviderVoiceCatalog):
                self.register_many(adapter.list_provider_voices())

    # ── Remove ────────────────────────────────────────────────────────────

    def remove(self, voice_id: str) -> None:
        voice = self._voices.pop(voice_id, None)
        if voice is not None and voice.provider_id in self._by_provider:
            ids = self._by_provider[voice.provider_id]
            if voice_id in ids:
                ids.remove(voice_id)

    def remove_provider(self, provider_id: str) -> None:
        for voice_id in self._by_provider.pop(provider_id, []):
            self._voices.pop(voice_id, None)

    # ── Search (text + filters) ───────────────────────────────────────────

    def search(
        self,
        query: str = "",
        *,
        provider_id: Optional[str] = None,
        language: Optional[str] = None,
        gender: Optional[str] = None,
    ) -> list[ProviderVoice]:
        candidates = self.list_by_provider(provider_id) if provider_id else self.list_all()
        q = query.lower()
        if q:
            candidates = [
                v for v in candidates
                if q in v.name.lower()
                or q in v.description.lower()
                or any(q in t.lower() for t in v.tags)
            ]
        if language:
            candidates = [v for v in candidates if v.language == language]
        if gender:
            candidates = [v for v in candidates if v.gender == gender]
        return candidates

from typing import Any, Optional
from pydantic import BaseModel


class VoiceResourceResponse(BaseModel):
    """API-facing catalog descriptor.

    Domain type (``ProviderVoice``, future ``MarketplaceVoice``, etc.) is enriched at
    query time with derived library and compatibility state.  Never stored in the DB.
    """

    id: str
    resource_type: str = "preset"
    resource_origin: str
    name: str
    description: str = ""
    language: Optional[str] = None
    preview_audio_url: Optional[str] = None
    catalog_source: Optional[dict[str, Any]] = None

    # ProviderVoice-specific (non-null when resource_type == "preset")
    provider_id: Optional[str] = None
    external_id: Optional[str] = None
    gender: Optional[str] = None
    is_default: bool = False

    # Derived query-time state (never stored)
    is_in_library: bool = False
    library_voice_id: Optional[str] = None
    compatible_models: list[str] = []
    recommended_model_id: Optional[str] = None

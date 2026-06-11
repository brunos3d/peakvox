import json
from typing import Optional
from app.core.config import settings

SETTINGS_FILE = settings.DATA_DIR / "settings.json"

# Persistence key for the user's Hugging Face access token. Stored in the
# single local settings.json alongside device settings — one config file,
# one merge. The token is never returned by any API and never logged.
_HF_TOKEN_KEY = "hf_token"


def _load() -> dict:
    """Read the whole settings document, or an empty dict if absent/corrupt."""
    if not SETTINGS_FILE.exists():
        return {}
    try:
        with open(SETTINGS_FILE) as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save(data: dict) -> dict:
    """Merge ``data`` into the settings document and persist it."""
    current = _load()
    current.update(data)
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(current, f)
    return current


def get_device_settings() -> dict:
    data = _load()
    if "use_gpu" not in data:
        return {"use_gpu": True}
    return data


def save_device_settings(data: dict) -> dict:
    return _save(data)


# ---- Hugging Face token (CE canonical HF auth source) -------------------------

def get_huggingface_token() -> Optional[str]:
    """Return the stored Hugging Face token, or ``None`` if not configured.

    Empty / whitespace-only values are treated as not configured.
    """
    token = _load().get(_HF_TOKEN_KEY)
    if not isinstance(token, str):
        return None
    token = token.strip()
    return token or None


def save_huggingface_token(token: str) -> None:
    """Persist the Hugging Face token (trimmed) in the local settings file."""
    _save({_HF_TOKEN_KEY: token.strip()})


def delete_huggingface_token() -> None:
    """Remove the Hugging Face token from the local settings file."""
    current = _load()
    if _HF_TOKEN_KEY in current:
        del current[_HF_TOKEN_KEY]
        settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(current, f)


def huggingface_configured() -> bool:
    return get_huggingface_token() is not None

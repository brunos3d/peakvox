import json
from pathlib import Path
from app.core.config import settings

SETTINGS_FILE = settings.DATA_DIR / "settings.json"

def get_device_settings() -> dict:
    if not SETTINGS_FILE.exists():
        return {"use_gpu": True}
    try:
        with open(SETTINGS_FILE) as f:
            return json.load(f)
    except Exception:
        return {"use_gpu": True}

def save_device_settings(data: dict) -> dict:
    current = get_device_settings()
    current.update(data)
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(current, f)
    return current

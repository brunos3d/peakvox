"""Hugging Face token management — persistence, API, and runtime env injection.

Verifies the hotfix end-to-end at the unit level:
  - settings_service round-trip (save → configured → delete) reusing the single
    local settings.json,
  - the /settings/huggingface API (GET/PUT/DELETE) returns presence only and
    never the token; blank token → 400,
  - DockerRuntimeDriver._environment injects HF_TOKEN (+ legacy
    HUGGING_FACE_HUB_TOKEN) when a token is configured, and omits it when not.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.services.settings_service as ss
from app.api.settings import router as settings_router
from app.services.drivers.docker_runtime_driver import DockerRuntimeDriver

TOKEN = "hf_exampletoken_THIS_MUST_NEVER_LEAK_1234567890"


@pytest.fixture
def settings_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect the settings store to a temp file (no /data dependency)."""
    target = tmp_path / "settings.json"
    monkeypatch.setattr(ss, "SETTINGS_FILE", target)
    monkeypatch.setattr(ss.settings, "DATA_DIR", tmp_path)
    return target


# ---- settings_service ---------------------------------------------------------

def test_token_roundtrip(settings_file: Path) -> None:
    assert ss.get_huggingface_token() is None
    assert ss.huggingface_configured() is False

    ss.save_huggingface_token(TOKEN)
    assert ss.get_huggingface_token() == TOKEN
    assert ss.huggingface_configured() is True

    ss.delete_huggingface_token()
    assert ss.get_huggingface_token() is None
    assert ss.huggingface_configured() is False


def test_token_is_trimmed_and_blank_is_none(settings_file: Path) -> None:
    ss.save_huggingface_token("   ")
    assert ss.get_huggingface_token() is None
    assert ss.huggingface_configured() is False

    ss.save_huggingface_token("  hf_padded  ")
    assert ss.get_huggingface_token() == "hf_padded"


def test_device_settings_coexist_with_token(settings_file: Path) -> None:
    ss.save_device_settings({"use_gpu": False})
    ss.save_huggingface_token(TOKEN)
    # Both keys live in the same file; neither clobbers the other.
    assert ss.get_device_settings()["use_gpu"] is False
    assert ss.get_huggingface_token() == TOKEN
    ss.delete_huggingface_token()
    assert ss.get_device_settings()["use_gpu"] is False


# ---- API ----------------------------------------------------------------------

@pytest.fixture
def client(settings_file: Path) -> TestClient:
    app = FastAPI()
    app.include_router(settings_router)
    return TestClient(app)


def test_api_get_reports_presence_only(client: TestClient) -> None:
    r = client.get("/settings/huggingface")
    assert r.status_code == 200
    assert r.json() == {"configured": False}


def test_api_put_then_get_then_delete(client: TestClient) -> None:
    r = client.put("/settings/huggingface", json={"token": TOKEN})
    assert r.status_code == 200
    assert r.json() == {"configured": True}
    assert TOKEN not in r.text  # never echoed

    r = client.get("/settings/huggingface")
    assert r.json() == {"configured": True}
    assert TOKEN not in r.text

    r = client.delete("/settings/huggingface")
    assert r.status_code == 200
    assert r.json() == {"configured": False}

    assert client.get("/settings/huggingface").json() == {"configured": False}


def test_api_put_blank_is_rejected(client: TestClient) -> None:
    r = client.put("/settings/huggingface", json={"token": "   "})
    assert r.status_code == 400
    assert client.get("/settings/huggingface").json() == {"configured": False}


def test_api_never_returns_token_anywhere(client: TestClient) -> None:
    client.put("/settings/huggingface", json={"token": TOKEN})
    for resp in (
        client.get("/settings/huggingface"),
        client.put("/settings/huggingface", json={"token": TOKEN}),
        client.delete("/settings/huggingface"),
    ):
        assert TOKEN not in resp.text


# ---- driver env injection -----------------------------------------------------

def _descriptor():
    from tests.test_docker_runtime_driver import _good_descriptor
    return _good_descriptor()


def test_environment_includes_hf_token_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ss, "get_huggingface_token", lambda: TOKEN)
    driver = DockerRuntimeDriver(client=object())  # type: ignore[arg-type]
    env = driver._environment(_descriptor())
    assert env["HF_TOKEN"] == TOKEN
    assert env["HUGGING_FACE_HUB_TOKEN"] == TOKEN
    # base keys still present
    assert env["PEAKVOX_RUNTIME_ID"]


def test_environment_omits_hf_token_when_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ss, "get_huggingface_token", lambda: None)
    driver = DockerRuntimeDriver(client=object())  # type: ignore[arg-type]
    env = driver._environment(_descriptor())
    assert "HF_TOKEN" not in env
    assert "HUGGING_FACE_HUB_TOKEN" not in env

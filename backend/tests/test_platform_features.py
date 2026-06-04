from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.platform import router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_features_endpoint_reports_community_all_false():
    resp = _client().get("/platform/features")
    assert resp.status_code == 200
    body = resp.json()
    assert body["edition"] == "community"
    assert body["name"] == "PeakVox"
    feats = body["features"]
    assert feats["marketplace"] is False
    assert feats["creators"] is False
    assert feats["billing"] is False
    assert feats["auth"] is False

from fastapi import FastAPI

from app.core.editions import mount_cloud_routers
from app.core.features import Features


def _paths(app: FastAPI) -> set[str]:
    return {r.path for r in app.routes}


def test_community_mounts_no_cloud_routers():
    app = FastAPI()
    before = _paths(app)
    mount_cloud_routers(app, features=Features.for_edition("community"))
    assert _paths(app) == before  # nothing added in CE


def test_cloud_features_allow_mounting_hook():
    # With cloud features, the hook runs without error (concrete routers arrive in later phases).
    app = FastAPI()
    mount_cloud_routers(app, features=Features.for_edition("cloud"))
    assert isinstance(_paths(app), set)

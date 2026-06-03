"""Identity seam — the single place where ownership is resolved.

This is the deliberate extension point for future authentication. Today (Community
Edition) every request is attributed to the implicit local owner. Cloud/Enterprise
editions replace the resolver with one that reads the authenticated session / JWT /
API-key principal — **without any database change**, because every resource already
carries ``owner_id``.

Usage (future):

    @router.get("/voices")
    async def list_voices(owner_id: str = Depends(get_current_owner_id)):
        ...

Endpoints are not yet wired to this dependency (Community Edition has no auth), but new
multi-tenant-aware code should depend on it so the Cloud/Enterprise swap is a one-line
change here.
"""

from app.core.config import settings


async def get_current_owner_id() -> str:
    """Return the owner id for the current request.

    Community Edition: always the seeded local owner. Cloud/Enterprise editions override
    this to resolve the authenticated principal.
    """
    return settings.LOCAL_OWNER_ID

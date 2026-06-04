"""Install community models from Hugging Face.

The download is isolated in ``_download_snapshot`` so it can be mocked in tests and swapped for
a resumable/progress-aware implementation later. Installing inserts a non-builtin ``models`` row
(``is_builtin=0``) — never touching built-in catalog rows. Provider must already be registered.
"""

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.registry_types import ModelDescriptor
from app.services.model_registry import model_registry

# Providers known to the platform. Installing a model for an unknown provider is rejected.
_KNOWN_PROVIDERS = {"omnivoice", "omnivoice-singing"}


class HfInstallError(Exception):
    pass


def _download_snapshot(repo_id: str) -> str:
    """Download the repo snapshot into HF_HOME and return the local path.

    Isolated for mocking. Real implementation uses huggingface_hub.snapshot_download(
    repo_id, cache_dir=settings.HF_HOME). Kept import-local to stay torch/HF-free at module load.
    """
    from huggingface_hub import snapshot_download

    from app.core.config import settings

    return snapshot_download(repo_id=repo_id, cache_dir=settings.HF_HOME)


async def install_from_hf(
    session: AsyncSession, *, repo_id: str, provider: str, name: str,
) -> ModelDescriptor:
    if provider not in _KNOWN_PROVIDERS:
        raise HfInstallError(f"Unknown provider '{provider}'. Known: {sorted(_KNOWN_PROVIDERS)}")

    model_path = _download_snapshot(repo_id)
    model_id = repo_id.replace("/", "--")
    now = datetime.now(timezone.utc).isoformat()

    await session.execute(
        text(
            """
            INSERT INTO models (
                id, name, description, version, provider, repo_id, model_path,
                status, is_default, is_builtin, editions, owner_id, created_at, updated_at
            ) VALUES (
                :id, :name, :desc, '1.0.0', :provider, :repo_id, :model_path,
                'available', 0, 0, :editions, NULL, :now, :now
            )
            ON CONFLICT(id) DO UPDATE SET
                model_path=excluded.model_path, status='available', updated_at=excluded.updated_at
            """
        ),
        {
            "id": model_id, "name": name, "desc": f"Installed from {repo_id}",
            "provider": provider, "repo_id": repo_id, "model_path": model_path,
            "editions": '["community"]', "now": now,
        },
    )
    await session.commit()

    descriptor = ModelDescriptor(
        id=model_id, name=name, description=f"Installed from {repo_id}",
        provider=provider, repo_id=repo_id, model_path=model_path,
        is_builtin=False,
    )
    model_registry.upsert_descriptor(descriptor)
    return descriptor

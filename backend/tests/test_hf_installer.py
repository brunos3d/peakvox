import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)

from app.core.migrations import run_migrations
from app.services.hf_installer import install_from_hf, HfInstallError


@pytest.fixture
async def session(tmp_path):
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/hf.db", future=True)
    async with eng.begin() as conn:
        await run_migrations(conn)
    maker = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await eng.dispose()


async def test_install_inserts_non_builtin_model(session, monkeypatch):
    def fake_download(repo_id: str) -> str:
        return f"/data/models/{repo_id}"

    monkeypatch.setattr("app.services.hf_installer._download_snapshot", fake_download)

    descriptor = await install_from_hf(
        session,
        repo_id="someorg/cool-tts",
        provider="omnivoice",
        name="Cool TTS",
    )
    assert descriptor.is_builtin is False
    row = (await session.execute(
        text("SELECT is_builtin, model_path, provider FROM models WHERE id=:id"),
        {"id": descriptor.id},
    )).first()
    assert row[0] == 0
    assert row[1] == "/data/models/someorg/cool-tts"
    assert row[2] == "omnivoice"


async def test_install_rejects_unknown_provider(session):
    with pytest.raises(HfInstallError):
        await install_from_hf(session, repo_id="x/y", provider="nonexistent-provider", name="X")

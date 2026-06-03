import hashlib

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import settings
from app.core.migrations import run_migrations
from app.services.api_keys import (
    KEY_PREFIX,
    create_api_key,
    extract_api_token,
    generate_api_key,
    hash_key,
    list_api_keys,
    revoke_api_key,
    verify_api_key,
)


def test_extract_api_token_from_headers():
    assert extract_api_token("Bearer ov_live_abc", None) == "ov_live_abc"
    assert extract_api_token("bearer ov_live_abc", None) == "ov_live_abc"
    assert extract_api_token(None, "ov_live_xyz") == "ov_live_xyz"
    # X-API-Key takes precedence when both present.
    assert extract_api_token("Bearer a", "ov_live_xyz") == "ov_live_xyz"
    assert extract_api_token(None, None) is None
    assert extract_api_token("Basic foo", None) is None


@pytest.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/test.db")
    async with engine.begin() as conn:
        await run_migrations(conn)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


def test_generate_api_key_format():
    full, prefix, secret_hash = generate_api_key()
    assert full.startswith(KEY_PREFIX)
    assert prefix.startswith(KEY_PREFIX)
    assert full.startswith(prefix)  # prefix is a leading slice of the full key
    assert secret_hash == hashlib.sha256(full.encode()).hexdigest()
    assert full != secret_hash


def test_generate_api_keys_are_unique():
    keys = {generate_api_key()[0] for _ in range(50)}
    assert len(keys) == 50


async def test_create_returns_raw_once_and_stores_hash(session_factory):
    async with session_factory() as s:
        key, raw = await create_api_key(s, name="CI")
    assert raw.startswith(KEY_PREFIX)
    assert key.name == "CI"
    assert key.owner_id == settings.LOCAL_OWNER_ID
    assert key.status == "active"
    # The raw key is never persisted — only its hash.
    assert key.secret_hash == hash_key(raw)
    assert raw not in key.secret_hash


async def test_verify_valid_key_updates_last_used(session_factory):
    async with session_factory() as s:
        _, raw = await create_api_key(s, name="CI")
    async with session_factory() as s:
        verified = await verify_api_key(s, raw)
    assert verified is not None
    assert verified.last_used_at is not None


async def test_verify_rejects_unknown_and_revoked(session_factory):
    async with session_factory() as s:
        key, raw = await create_api_key(s, name="CI")
    async with session_factory() as s:
        assert await verify_api_key(s, "ov_live_bogus") is None
        await revoke_api_key(s, key.id)
    async with session_factory() as s:
        assert await verify_api_key(s, raw) is None  # revoked


async def test_list_returns_owner_keys(session_factory):
    async with session_factory() as s:
        await create_api_key(s, name="A")
        await create_api_key(s, name="B")
    async with session_factory() as s:
        keys = await list_api_keys(s)
    assert {k.name for k in keys} == {"A", "B"}


async def test_revoke_missing_returns_none(session_factory):
    async with session_factory() as s:
        assert await revoke_api_key(s, "nope") is None

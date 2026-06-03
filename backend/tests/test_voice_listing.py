from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.migrations import run_migrations
from app.models.db import VoiceProfile
from app.services.voice_repository import list_voices_page, set_favorite


@pytest.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/test.db")
    async with engine.begin() as conn:
        await run_migrations(conn)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


_BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


async def _seed(session_factory, voices: list[dict]):
    async with session_factory() as session:
        for i, v in enumerate(voices):
            session.add(
                VoiceProfile(
                    name=v["name"],
                    audio_filename="reference.wav",
                    created_at=v.get("created_at", _BASE + timedelta(minutes=i)),
                    language_code=v.get("language_code"),
                    characteristics=v.get("characteristics"),
                    is_favorite=v.get("is_favorite", False),
                    last_used_at=v.get("last_used_at"),
                )
            )
        await session.commit()


async def test_pagination_walks_all_pages(session_factory):
    await _seed(session_factory, [{"name": f"V{i}"} for i in range(5)])
    async with session_factory() as s:
        page1, cur1 = await list_voices_page(s, limit=2)
        assert len(page1) == 2
        assert cur1 is not None
        page2, cur2 = await list_voices_page(s, limit=2, cursor=cur1)
        assert len(page2) == 2
        page3, cur3 = await list_voices_page(s, limit=2, cursor=cur2)
        assert len(page3) == 1
        assert cur3 is None
    # No overlap across pages.
    names = [v.name for v in page1 + page2 + page3]
    assert len(set(names)) == 5


async def test_filter_by_favorite(session_factory):
    await _seed(session_factory, [
        {"name": "Fav", "is_favorite": True},
        {"name": "Plain", "is_favorite": False},
    ])
    async with session_factory() as s:
        items, _ = await list_voices_page(s, favorite=True)
    assert [v.name for v in items] == ["Fav"]


async def test_filter_by_characteristic_gender(session_factory):
    await _seed(session_factory, [
        {"name": "Male", "characteristics": {"gender": "male", "style_tags": []}},
        {"name": "Female", "characteristics": {"gender": "female", "style_tags": []}},
    ])
    async with session_factory() as s:
        items, _ = await list_voices_page(s, gender="male")
    assert [v.name for v in items] == ["Male"]


async def test_filter_by_language_code(session_factory):
    await _seed(session_factory, [
        {"name": "Eng", "language_code": "en"},
        {"name": "Por", "language_code": "pt"},
    ])
    async with session_factory() as s:
        items, _ = await list_voices_page(s, language_code="pt")
    assert [v.name for v in items] == ["Por"]


async def test_scope_recent_only_used_ordered_desc(session_factory):
    await _seed(session_factory, [
        {"name": "Old", "last_used_at": _BASE},
        {"name": "Never"},
        {"name": "New", "last_used_at": _BASE + timedelta(days=1)},
    ])
    async with session_factory() as s:
        items, _ = await list_voices_page(s, scope="recent")
    assert [v.name for v in items] == ["New", "Old"]


async def test_search_by_name_and_accent(session_factory):
    await _seed(session_factory, [
        {"name": "Narrator", "characteristics": {"accent": "british", "style_tags": []}},
        {"name": "Host", "characteristics": {"accent": "american", "style_tags": []}},
    ])
    async with session_factory() as s:
        by_name, _ = await list_voices_page(s, search="narr")
        by_accent, _ = await list_voices_page(s, search="british")
    assert [v.name for v in by_name] == ["Narrator"]
    assert [v.name for v in by_accent] == ["Narrator"]


async def test_set_favorite_toggles(session_factory):
    await _seed(session_factory, [{"name": "V"}])
    async with session_factory() as s:
        items, _ = await list_voices_page(s)
        vid = items[0].id
        updated = await set_favorite(s, vid, True)
        assert updated.is_favorite is True
        again = await set_favorite(s, vid, False)
        assert again.is_favorite is False


async def test_set_favorite_missing_returns_none(session_factory):
    async with session_factory() as s:
        assert await set_favorite(s, "nope", True) is None

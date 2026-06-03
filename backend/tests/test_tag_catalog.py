from app.services.tag_catalog import TAG_CATALOG, get_tag, tags_for


def test_every_known_tag_has_metadata():
    expected = {
        # base
        "laughter", "sigh", "confirmation-en", "question-en", "question-ah",
        "question-oh", "question-ei", "question-yi", "surprise-ah", "surprise-oh",
        "surprise-wa", "surprise-yo", "dissatisfaction-hnn",
        # singing + emotion
        "singing", "happy", "sad", "angry", "nervous", "whisper", "calm", "excited",
    }
    assert expected <= set(TAG_CATALOG)


def test_tag_metadata_shape():
    happy = get_tag("happy")
    assert happy is not None
    assert happy.id == "happy"
    assert happy.label
    assert happy.emoji
    assert happy.category
    assert happy.syntax == "[happy]"


def test_get_unknown_tag_returns_none():
    assert get_tag("does-not-exist") is None


def test_tags_for_filters_and_preserves_order_and_skips_unknown():
    result = tags_for(["happy", "nope", "singing"])
    assert [t.id for t in result] == ["happy", "singing"]

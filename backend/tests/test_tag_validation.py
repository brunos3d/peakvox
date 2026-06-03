from app.services.tag_validation import extract_tags, find_unsupported_tags


def test_extract_tags_finds_bracket_tokens():
    assert extract_tags("Hi [happy] there [singing]") == ["happy", "singing"]


def test_extract_tags_handles_empty_and_none():
    assert extract_tags("") == []
    assert extract_tags(None) == []


def test_extract_ignores_malformed_brackets():
    # Empty brackets and uppercase are not valid tag tokens.
    assert extract_tags("a [] b [Happy] c [ok-1]") == ["ok-1"]


def test_find_unsupported_returns_offenders_in_order_deduped():
    supported = ["laughter", "sigh"]
    assert find_unsupported_tags("[laughter] no [singing] [singing] [bad]", supported) == [
        "singing",
        "bad",
    ]


def test_no_unsupported_when_all_allowed():
    assert find_unsupported_tags("plain [happy] text", ["happy"]) == []

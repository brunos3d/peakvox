"""Authoritative inline-tag validation for generation requests.

The editor validates tags live in the browser, but the backend re-validates against the
selected model's ``supported_tags`` so the public API and the UI behave identically and a
malicious/old client cannot smuggle unsupported tags past the model (plan AD-3 / AD-6).

Pure and dependency-light; the tag grammar matches the frontend serializer's grammar
(``[a-z0-9][a-z0-9-]*``).
"""

import re

_TAG_RE = re.compile(r"\[([a-z0-9][a-z0-9-]*)\]")


def extract_tags(text: str | None) -> list[str]:
    """All inline tag ids in ``text``, in order (duplicates kept)."""
    if not text:
        return []
    return _TAG_RE.findall(text)


def find_unsupported_tags(text: str | None, supported: list[str]) -> list[str]:
    """Tag ids present in ``text`` but not in ``supported`` — in first-seen order, deduped."""
    allowed = set(supported)
    seen: set[str] = set()
    bad: list[str] = []
    for tag in extract_tags(text):
        if tag not in allowed and tag not in seen:
            seen.add(tag)
            bad.append(tag)
    return bad

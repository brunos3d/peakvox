"""Authoritative catalog of OmniVoice inline performance tags and their UI metadata.

This is the single source of truth for "what does ``[happy]`` mean and how should it be
shown". Models advertise *which* tag ids they support (see ``model_catalog``); this module
describes *each* tag once. The frontend mirrors this (fetched via the API) to render the
slash menu, toolbar, chips, and tooltips.

Dependency-light by design (no torch / no DB) so it can be imported anywhere.
"""

from pydantic import BaseModel

TagCategory = str  # "emotion" | "reaction" | "question" | "surprise" | "delivery" | "vocal"


class TagMetadata(BaseModel):
    id: str
    label: str
    emoji: str
    category: TagCategory
    description: str

    @property
    def syntax(self) -> str:
        """The literal OmniVoice token, e.g. ``[happy]``."""
        return f"[{self.id}]"


def _t(id: str, label: str, emoji: str, category: str, description: str) -> TagMetadata:
    return TagMetadata(id=id, label=label, emoji=emoji, category=category, description=description)


# Order within a category is the display order in menus/toolbars.
_ALL: list[TagMetadata] = [
    # ── Emotions (OmniVoice Singing + Emotion) ──────────────────────────────
    _t("happy", "happy", "😊", "emotion", "Warm, upbeat delivery."),
    _t("sad", "sad", "😢", "emotion", "Downcast, sorrowful delivery."),
    _t("angry", "angry", "😡", "emotion", "Harsh, intense delivery."),
    _t("nervous", "nervous", "😰", "emotion", "Anxious, hesitant delivery."),
    _t("calm", "calm", "😌", "emotion", "Relaxed, even-toned delivery."),
    _t("excited", "excited", "🤩", "emotion", "High-energy, enthusiastic delivery."),
    # ── Delivery ────────────────────────────────────────────────────────────
    _t("whisper", "whisper", "🤫", "delivery", "Soft, breathy whispered delivery."),
    # ── Vocal ─────────────────────────────────────────────────────────────────
    _t("singing", "singing", "🎵", "vocal", "Sung rather than spoken."),
    # ── Reactions (OmniVoice Base) ──────────────────────────────────────────
    _t("laughter", "laughter", "😂", "reaction", "Inserts natural laughter."),
    _t("sigh", "sigh", "😮‍💨", "reaction", "Inserts an audible sigh."),
    _t("dissatisfaction-hnn", "dissatisfaction", "😒", "reaction", "A discontented 'hnn'."),
    _t("confirmation-en", "confirmation", "👍", "reaction", "An affirming 'en' sound."),
    # ── Questions (OmniVoice Base) ──────────────────────────────────────────
    _t("question-en", "question (en)", "❓", "question", "Rising questioning 'en'."),
    _t("question-ah", "question (ah)", "❓", "question", "Rising questioning 'ah'."),
    _t("question-oh", "question (oh)", "❓", "question", "Rising questioning 'oh'."),
    _t("question-ei", "question (ei)", "❓", "question", "Rising questioning 'ei'."),
    _t("question-yi", "question (yi)", "❓", "question", "Rising questioning 'yi'."),
    # ── Surprise (OmniVoice Base) ───────────────────────────────────────────
    _t("surprise-ah", "surprise (ah)", "😲", "surprise", "Surprised 'ah' exclamation."),
    _t("surprise-oh", "surprise (oh)", "😲", "surprise", "Surprised 'oh' exclamation."),
    _t("surprise-wa", "surprise (wa)", "😲", "surprise", "Surprised 'wa' exclamation."),
    _t("surprise-yo", "surprise (yo)", "😲", "surprise", "Surprised 'yo' exclamation."),
]

TAG_CATALOG: dict[str, TagMetadata] = {t.id: t for t in _ALL}


def get_tag(tag_id: str) -> TagMetadata | None:
    return TAG_CATALOG.get(tag_id)


def tags_for(tag_ids: list[str]) -> list[TagMetadata]:
    """Resolve a model's supported tag ids to metadata, preserving order, skipping unknowns."""
    out: list[TagMetadata] = []
    for tid in tag_ids:
        meta = TAG_CATALOG.get(tid)
        if meta is not None:
            out.append(meta)
    return out

# Voice Model

The Voice is the central entity in OmniVoice. This document describes its identity,
metadata, characteristics, and lifecycle.

> See also: [Data Model](DATA_MODEL.md) · [API](API.md) · [Languages](LANGUAGES.md)

---

## Identifiers

Each voice has **two** identifiers, by design:

| Field | Example | Purpose |
|---|---|---|
| `id` (internal UUID) | `f47ac10b-58cc-…` | Primary key; storage paths (`/data/voices/{id}/`); internal references |
| `public_voice_id` | `voice_8JXQ29K4L3` | The **external contract** — APIs, SDKs, Copy-Voice-ID, community voices, import/export, cloud sync |

`public_voice_id` is generated once (Crockford base32, no ambiguous letters) and **never
changes**, even if the voice is renamed or its audio is replaced. Always store this id in
external systems — never the internal UUID.

---

## Fields

| Field | Type | Notes |
|---|---|---|
| `name` | string | Display name |
| `description` | string? | Optional |
| `language` | string? | Display language (e.g. `Portuguese`) |
| `language_code` | string? | OmniVoice language id (e.g. `pt`) — sent to the model. See [Languages](LANGUAGES.md) |
| `transcript` | string? | Reference-audio transcript; improves cloning |
| `audio_filename` | string | Reference audio (`reference.wav`) |
| `audio_duration` | float? | Seconds |
| `generation_defaults` | json? | Saved inference settings + `voice_design` (the preset) |
| `preset_tags` | json? | Free-form tags |
| `characteristics` | json? | **Derived, read-only** snapshot (see below) |
| `is_public` / `is_community_voice` / `is_preset_voice` / `is_favorite` | bool | Flags (community/preset disabled in Community Edition) |
| `status` | string | `ready` / `archived` / `processing` / `failed` |
| `usage_count` | int | Incremented on each generation |
| `owner_id` | string | The local owner (SaaS-ready) |
| `created_at` / `updated_at` / `last_used_at` | datetime | Timestamps |

---

## Voice design & characteristics

Two related concepts:

- **`voice_design`** (source of truth) — structured attributes chosen in the Voice Design
  Builder (gender, age, pitch, accent, style…), from a controlled vocabulary
  (`frontend/src/config/voice-design.ts`). These are joined into the flat `instruct`
  string the model accepts.
- **`characteristics`** (derived snapshot) — generated from `voice_design` + preset tags
  by `backend/app/services/voice_metadata.py::derive_characteristics`. Read-only; never
  hand-edited. **Filtering, search, and recommendations read `characteristics`** so they
  never recompute and never drift.

Whenever `voice_design` changes (create / update / save-defaults), the snapshot is
regenerated automatically.

Snapshot shape:

```json
{
  "gender": "male",
  "age_group": "young",
  "accent": "british",
  "pitch": "low",
  "style_tags": ["whisper"],
  "speaking_speed": null,
  "emotional_range": null
}
```

---

## Lifecycle

```
create (upload/record reference)        ──► status: ready, public_voice_id assigned
   │                                         characteristics derived from voice_design
   ▼
use in TTS / API  ──► usage_count++, last_used_at updated
   │
   ├─ edit (name/lang/transcript/defaults) ──► updated_at, characteristics re-derived
   ├─ favorite toggle                       ──► is_favorite
   └─ delete                                ──► row + storage prefix removed
```

### TTS auto-configuration

Selecting a voice applies its metadata to the Text-to-Speech screen — language,
generation defaults, and voice design — matching what the API applies at generation
time. See the [TTS auto-config spec](superpowers/specs/2026-06-03-tts-auto-config-design.md).

---

## Backend touch points

| Concern | Location |
|---|---|
| ORM model | `backend/app/models/db.py::VoiceProfile` |
| Public id generation | `backend/app/utils/ids.py` |
| Characteristics derivation | `backend/app/services/voice_metadata.py` |
| Lookups / listing / favorite | `backend/app/services/voice_repository.py` |
| CRUD endpoints | `backend/app/api/voices.py` |
| Public API representation | `backend/app/api/v1.py` |

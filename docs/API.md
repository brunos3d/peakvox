# OmniVoice API Reference

The public REST API lets you manage voices and generate speech programmatically. Voices
are addressed by their stable **public Voice ID** (e.g. `voice_8JXQ29K4L3`).

> See also: [Voice Model](VOICE_MODEL.md) · [Languages](LANGUAGES.md) · [Architecture](ARCHITECTURE.md) · [SaaS Architecture](SAAS_ARCHITECTURE.md)

---

## Base URL

```
{API_URL}/api/v1
```

`{API_URL}` is your backend origin (default `http://localhost:8000` for a local install).

## Authentication

Every `/api/v1` request requires an API key. Create one in the app under **API → API
Keys**; the full key (`ov_live_…`) is shown **once** at creation and stored only as a hash.

Send it either way:

```
Authorization: Bearer ov_live_xxxxxxxxxxxxxxxxx
# or
X-API-Key: ov_live_xxxxxxxxxxxxxxxxx
```

Missing/invalid/revoked keys return `401`.

> **Community Edition** runs locally and unauthenticated for the in-app UI; the API-key
> check still applies to `/api/v1` so integrations behave like Cloud. See
> [SaaS Architecture](SAAS_ARCHITECTURE.md).

---

## Voices

### List voices

```
GET /api/v1/voices?limit=50&cursor=<opaque>
```

```json
{
  "voices": [
    { "voiceId": "voice_8JXQ29K4L3", "name": "Narrator", "language": "English" }
  ],
  "nextCursor": "MjQ="
}
```

`nextCursor` is `null` on the last page; pass it back as `cursor` to page forward.

### Get a voice

```
GET /api/v1/voices/{voiceId}
```

```json
{
  "voiceId": "voice_8JXQ29K4L3",
  "name": "Narrator",
  "language": "English",
  "languageCode": "en",
  "description": null,
  "usageCount": 12,
  "characteristics": { "gender": "male", "accent": "british", "style_tags": [] },
  "createdAt": "2026-06-03T00:00:00Z"
}
```

### Create a voice

```
POST /api/v1/voices        (multipart/form-data)
```

| Field | Type | Notes |
|---|---|---|
| `name` | string | required |
| `file` | file | required; reference audio (**≤ 10 s**, validated server-side) |
| `transcript` | string | optional; improves cloning accuracy |
| `language` | string | optional; display name |
| `language_code` | string | optional; OmniVoice language id (e.g. `en`) |

Returns the created voice (same shape as **Get a voice**), `201`.

### Delete a voice

```
DELETE /api/v1/voices/{voiceId}
```

```json
{ "deleted": "voice_8JXQ29K4L3" }
```

---

## Text to Speech

```
POST /api/v1/text-to-speech?response=stream|url
```

```json
{
  "voiceId": "voice_8JXQ29K4L3",
  "text": "Hello from OmniVoice!",
  "language": "en",
  "format": "wav"
}
```

| Field | Type | Notes |
|---|---|---|
| `voiceId` | string | required; a public Voice ID |
| `text` | string | required |
| `language` | string | optional; OmniVoice id. Defaults to the voice's `languageCode` |
| `format` | `wav` \| `mp3` | default `wav` |

The voice's saved generation defaults and voice design are applied automatically, so API
output matches the in-app result.

**Response modes** (query param `response`, default `stream`):

- `stream` — the audio bytes (`audio/wav` or `audio/mpeg`).
- `url` — JSON with a download URL:

  ```json
  { "jobId": "…", "audioUrl": "/audio/abc.wav", "format": "wav", "durationSeconds": 3.4 }
  ```

The architecture supports both so a future signed-URL / CDN delivery path drops in behind
the same endpoint.

---

## API keys (management)

Used by the dashboard; local in Community Edition.

| Method | Path | Description |
|---|---|---|
| `GET` | `/api-keys` | List keys (masked: `prefix` + status) |
| `POST` | `/api-keys` | Create a key — **returns the raw key once** |
| `DELETE` | `/api-keys/{id}` | Revoke a key |

Raw keys are never retrievable after creation; only a sha256 hash is stored.

---

## Errors

| Status | Meaning |
|---|---|
| `401` | Missing / invalid / revoked API key |
| `404` | Voice not found |
| `422` | Validation error (e.g. reference audio too long) |
| `503` | Model still loading |
| `500` | Generation failed |

Errors use FastAPI's shape: `{ "detail": "…" }`.

---

## Examples

### cURL

```bash
curl -X POST "$API_URL/api/v1/text-to-speech" \
  -H "Authorization: Bearer $OMNIVOICE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"voiceId":"voice_8JXQ29K4L3","text":"Hello!","format":"mp3"}' \
  --output speech.mp3
```

### JavaScript

```js
const res = await fetch(`${API_URL}/api/v1/text-to-speech`, {
  method: "POST",
  headers: {
    Authorization: `Bearer ${process.env.OMNIVOICE_API_KEY}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({ voiceId: "voice_8JXQ29K4L3", text: "Hello!", format: "mp3" }),
});
const audio = await res.arrayBuffer();
```

### Python

```python
import os, requests

res = requests.post(
    f"{API_URL}/api/v1/text-to-speech",
    headers={"Authorization": f"Bearer {os.environ['OMNIVOICE_API_KEY']}"},
    json={"voiceId": "voice_8JXQ29K4L3", "text": "Hello!", "format": "mp3"},
)
open("speech.mp3", "wb").write(res.content)
```

---

## Versioning & stability

- The API is versioned (`/api/v1`); breaking changes will ship under a new version.
- `voiceId` (`public_voice_id`) is **stable forever** — safe to persist in your systems.
- Field names are camelCase and SDK-friendly.

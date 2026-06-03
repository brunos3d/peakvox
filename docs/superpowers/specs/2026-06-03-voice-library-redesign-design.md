# Voice Library Redesign — Design Spec

**Date:** 2026-06-03
**Status:** Approved (decisions confirmed)
**Sub-project:** C of the OmniVoice Phase 2 platform initiative
**Depends on:** A (voice entity + characteristics + flags + public_voice_id), B (language registry)

---

## Context

Covers Phase 2 brief phases 4–9: library tabs, global search, advanced filters,
pagination, community publishing surface (disabled), and an expanded voice details panel.

Current library ([voices/page.tsx](../../../frontend/src/app/voices/page.tsx)) loads ALL
voices into the global Zustand store via `useVoices()` and filters client-side. That same
store (`store.voices`) is read app-wide for id→name lookups:
[VoiceSelector](../../../frontend/src/components/voice/VoiceSelector.tsx),
[BottomPlayer](../../../frontend/src/components/shell/BottomPlayer.tsx),
[history/page.tsx](../../../frontend/src/app/history/page.tsx).

## Confirmed decisions

1. **Pagination:** server-side paginated/filtered/searchable list drives the library; the
   existing full-list store stays for lightweight cross-app lookups (single-user reality).
2. **Empty tabs:** render all four tabs; Community + Preset show a "coming soon" disabled
   state (Community disabled and presets unseeded per sub-project A).
3. **Favorites:** add a functional `is_favorite` toggle (endpoint + UI) so the Favorites
   filter is real.

---

## Backend

### Query layer (in `services/voice_repository.py`, unit-tested)

```python
async def list_voices_page(
    db, *, scope="mine", search=None, filters=VoiceFilters(),
    limit=24, cursor=None,
) -> tuple[list[VoiceProfile], str | None]
```

- **scope:**
  - `mine` — all voices owned by the local owner, ordered by `created_at desc, id desc`.
  - `recent` — only voices with `last_used_at` set, ordered by `last_used_at desc, id desc`.
  - `community` — `is_public AND is_community_voice` (empty for now).
  - `preset` — `is_preset_voice` (empty for now).
- **search** (case-insensitive): `name`, `language`, `language_code`, plus
  `characteristics.accent` (via `json_extract`) and a raw-JSON LIKE over `characteristics`
  / `preset_tags` for tags/style. Pragmatic for SQLite; refine later if needed.
- **filters:** `language_code`, `gender`, `age_group`, `accent` (the last three via
  `json_extract(characteristics, '$.X')`), `favorite` (bool).
- **cursor:** opaque base64 token. Implemented as an offset token now (the brief allows
  "cursor *or* server-side pagination"); the client contract (`next_cursor`) is
  keyset-ready so the internals can change without touching callers. `next_cursor` is
  null when no more rows.
- **limit:** clamped 1..100, default 24.

```python
async def set_favorite(db, voice_id, value: bool) -> VoiceProfile | None
```

### Schemas

```python
class VoiceFilters(BaseModel):  # query model
    language_code: str | None = None
    gender: str | None = None
    age_group: str | None = None
    accent: str | None = None
    favorite: bool | None = None

class VoiceListPage(BaseModel):
    items: list[VoiceProfileResponse]
    next_cursor: str | None = None
```

### Endpoints (in `api/voices.py`)

- `GET /voices/page` — query params: `scope, search, language_code, gender, age_group,
  accent, favorite, limit, cursor` → `VoiceListPage`.
- `PATCH /voices/{id}/favorite` — body `{ "is_favorite": bool }` → `VoiceProfileResponse`.
- `GET /voices` — **unchanged** (keeps the global lookup store working).

---

## Frontend

### Data layer

- `api.ts`: `fetchVoicesPage(params): Promise<VoiceListPage>`, `setFavorite(id, value)`.
- `types`: `VoiceListPage`, `VoiceScope`, `VoiceFilters`.
- Hook `useVoicesPage(scope, search, filters)` → React Query `useInfiniteQuery`
  (getNextPageParam = `next_cursor`). Library reads this, **not** `store.voices`.
- `useToggleFavorite()` mutation — optimistic, invalidates `["voices-page"]` and `["voices"]`.
- `useVoices()` (global store) stays as-is for lookups.

### Library page rewrite ([voices/page.tsx](../../../frontend/src/app/voices/page.tsx))

- **Tabs** (reuse [ui/tabs.tsx](../../../frontend/src/components/ui/tabs.tsx)): My Voices,
  Community Voices, Preset Voices, Recently Used. Community + Preset render a disabled
  "coming soon" `EmptyState`.
- **Instant search** input (debounced ~200ms) in the existing `FilterBar`.
- **Advanced Filters** (collapsible panel): Language (`LanguageCombobox`), Gender, Age,
  Accent (selects driven by characteristic value sets), Favorites toggle (`Chip`). A
  "Clear filters" affordance.
- **Pagination:** "Load more" button driven by `fetchNextPage` / `hasNextPage`.
- Selected-voice context panel and edit/delete dialogs are preserved.

### VoiceCard ([voice/VoiceCard.tsx](../../../frontend/src/components/voice/VoiceCard.tsx))

Add: favorite **star toggle**, **Copy Voice ID** (copies `public_voice_id` with a copied
state), characteristic **chips** (gender / accent when present), and **usage count**.

### Voice details panel (Phase 9 — [voice/VoiceDetailsDrawer.tsx](../../../frontend/src/components/voice/VoiceDetailsDrawer.tsx))

Expand to show: **Voice ID** with a Copy button, Language (display + code), Reference
Audio player, Creation Date, Usage Count, Preset Tags, and Voice Characteristics
(gender, age, accent, pitch, style tags, speaking speed, emotional range).

---

## Out of scope (other sub-projects)

- "Use in API" dialog / cURL/JS/Python examples → **D**.
- Community publishing action / Shared-with-me / Team voices → later (schema exists).
- TTS auto-config from selected voice metadata → **E**.

---

## Risks & mitigations

- **Two list code paths** (`/voices` full + `/voices/page`): intentional; keeps lookups
  working while the library scales. Documented; future work can migrate lookups to
  by-id fetches.
- **SQLite JSON search** is pragmatic (json_extract + LIKE), not a full-text index.
  Adequate at current scale; revisit if community search needs it.
- **Offset-cursor drift** under concurrent inserts: acceptable for a single-user app;
  the keyset-ready contract allows upgrading later.
- **Optimistic favorite** could desync on error → invalidate queries on settle.

## Success criteria

- Library shows the four tabs; My Voices + Recently Used populated, Community + Preset
  show coming-soon states.
- Search and each filter work server-side and compose; results paginate via "Load more".
- Favorite toggling persists and the Favorites filter returns favorited voices.
- Voice cards expose Copy Voice ID + characteristics; details panel shows the full
  Phase-9 field set.
- Other screens (TTS picker, bottom player, history) keep working unchanged.
- Backend query/favorite tests pass; `tsc`, lint, and build are clean.

## Execution order

1. Backend `list_voices_page` + `set_favorite` + schemas (TDD).
2. Backend endpoints `GET /voices/page`, `PATCH /voices/{id}/favorite`.
3. Frontend api client + types + hooks.
4. VoiceCard enhancements.
5. Library page rewrite (tabs, search, filters, load more).
6. Expand VoiceDetailsDrawer.
7. Verify: backend tests, tsc, lint, build.

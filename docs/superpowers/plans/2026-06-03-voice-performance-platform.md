# Voice Performance Platform — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. This is a **master program plan**: each Phase below should be expanded into its own bite-sized, TDD task plan via `superpowers:writing-plans` immediately before that phase is executed. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evolve OmniVoice App from a single-model, plain-textarea TTS tool into a multi-model "voice performance" platform with a rich, model-aware scripting editor — preserving the OmniVoice ecosystem, the self-hosted simplicity, and the SaaS-ready architecture already in place.

**Architecture:** A backend **model registry** (catalog + DB + provider adapters) replaces the hardcoded single model. A **tag catalog** keyed per-model becomes the single source of truth for emotion/effect tags. The frontend center column becomes a **TipTap** rich editor that renders human-friendly emotion blocks, validates against the active model's tags, and serializes back to OmniVoice's `[tag]` plain-text syntax. The right sidebar becomes the control surface (Voice, Model, Settings, Output, Language, Voice Design, Emotion, Model Info, Generate). Generation, jobs, storage, and the public API are extended additively with a `model_id`.

**Tech Stack:** FastAPI + async SQLAlchemy + aiosqlite + MinIO (backend); Next.js 16 / React 19, App Router, Zustand, React Query, Tailwind, shadcn/ui, **TipTap v2 (ProseMirror)** (frontend). No new infra services.

---

## 0. How to read this document

This plan is intentionally a **program-level specification + execution roadmap**, not a single flat task list. The initiative spans five independent subsystems (model registry, editor, tag system, validation, API). Per the `writing-plans` scope check, each **Phase** is a self-contained, independently shippable unit and gets its own detailed bite-sized TDD plan generated at execution time.

Sections:

1. Current-state analysis (what exists today)
2. Architectural decisions (with rationale) — the "why"
3. Backend design (registry, DB, API, providers)
4. Frontend design (editor, layout, dynamic UI)
5. Serialization & validation architecture
6. API compatibility layer
7. UX proposals (wireframes, interaction flows, "directing" concept)
8. Epic → Phase → Milestone → Task breakdown
9. Dependency graph
10. Risk analysis
11. Migration strategy
12. Testing strategy
13. Rollout strategy
14. Acceptance criteria
15. Exemplar bite-sized tasks (the three highest-risk cores, fully specified)

---

## 1. Current-State Analysis

Findings from a full read of the repository (2026-06-03, branch `feat/voice-performance-platform`).

### 1.1 Backend

| Area | Current reality | Implication for this initiative |
|------|-----------------|---------------------------------|
| Model loading | `backend/app/services/omnivoice_service.py` — a single `OmniVoiceService` singleton hardcoded to `settings.OMNIVOICE_MODEL` (`"k2-fsa/OmniVoice"`). Loads once at startup (`main.py` lifespan → `asyncio.create_task(omnivoice_service.load_model())`), offloads to CPU after each generation, single `_generation_lock`. | Needs a registry + provider abstraction. The offload-after-generation + single-resident-model VRAM discipline MUST be preserved. |
| Generation | `backend/app/api/generation.py` — `POST /generate` creates a `GenerationJob` row, fires `_process_job()` as `asyncio.create_task`; polled via `GET /jobs/{id}`. `is_generating` → 409 if busy. MP3/OGG transcode on demand via ffmpeg. | `model_id` must thread through request → job row → `_process_job` → service. |
| Job model | `backend/app/models/db.py` `GenerationJob` has **no** `model_id` column. `generation_params` is a JSON blob. | Add `model_id` column (additive migration). |
| Voice model | `VoiceProfile` is rich and SaaS-ready: `public_voice_id`, `owner_id`, `generation_defaults` (JSON), `characteristics`, visibility flags. | A voice may later carry a `default_model_id` / per-model defaults. Not required for MVP. |
| Schema migration | `backend/app/core/migrations.py` — idempotent, SQLite-safe, additive `ALTER TABLE ADD COLUMN` runner. The established pattern (not Alembic). | All new columns/tables follow this exact pattern. |
| Public API | `backend/app/api/v1.py` — `/api/v1/voices`, `/api/v1/text-to-speech` (synchronous), API-key auth, camelCase schemas in `schemas/api.py`. `TextToSpeechRequest` has `voiceId, text, language, format` — **no `modelId`**. | Add optional `modelId` (additive, defaults to base model). |
| Model status | `backend/app/api/health.py` — `GET /models/status` returns a single model's load state. | Becomes per-model; keep a back-compat aggregate. |
| Config | `backend/app/core/config.py` — pydantic settings, `EDITION` flag (`community`/`cloud`/`enterprise`), `LOCAL_OWNER_ID`. | Registry default model + per-edition model availability hook here. |

### 1.2 Frontend

| Area | Current reality | Implication |
|------|-----------------|-------------|
| TTS page | `frontend/src/app/page.tsx` — `"use client"`, a plain shadcn `<Textarea>`, with **Language** and **Voice Design** rendered *below* the editor; `PageLayout` provides the docked right context panel. | Center becomes the rich editor; Language + Voice Design move into the right sidebar. |
| Right panel | `frontend/src/components/generation/GenerationPanel.tsx` already renders `VoiceSelector`, `ModelSelector`, `GenerationSettings`, `OutputFormatSelector`. | The sidebar already exists — we extend it, not invent it. |
| Model selector | `frontend/src/components/generation/ModelSelector.tsx` — a **stub** `<Select>` with a single hardcoded `omnivoice` option, explicitly commented "feature-ready for additional models". | Wire it to the live registry. |
| Voice Design | `frontend/src/config/voice-design.ts` — controlled vocabulary, one-attribute-per-category rule, `buildInstruct()` → flat comma string. This is the model for how to do a tag catalog cleanly. | Reuse this pattern's shape for the tag catalog; keep voice_design distinct from emotion tags (different concept: speaker attributes vs inline performance directions). |
| State | `frontend/src/store/use-store.ts` (Zustand) — holds `ttsText`, `selectedProfile`, `generationSettings`, `voiceDesign`, `ttsLanguage`, `activeJobId`, etc. `setSelectedProfile` auto-applies a voice's language. | Add `selectedModelId`, and the editor document/serialized text. Selecting a voice may set its default model. |
| Generation hook | `frontend/src/hooks/use-generation.ts` — React Query mutation + polling, `useModelStatus()`. | Add `useModels()`, `useModelTags(modelId)`, `useActiveModel()`. |
| Types | `frontend/src/types/index.ts` — `GenerationRequest`, `JobResponse`, `VoiceProfile`, `ModelStatus`. | Add `Model`, `ModelTag`, `ModelCapabilities`; add `model_id` to `GenerationRequest`. |
| Shell | App Router server-frame + client-island pattern (recently refactored). `PageLayout` = scrollable center + docked `xl:` right panel + mobile slide-over sheet. Persistent `BottomPlayer`. | Editor is a client island inside the (server) page frame. |
| UI kit | shadcn present incl. `command.tsx`, `popover.tsx`, `dropdown-menu.tsx`, `tabs.tsx`, `accordion.tsx`, `badge.tsx`. | `command` + `popover` are exactly what the slash/`[` menu needs. `accordion` drives the collapsible sidebar sections. No new primitives required. |

### 1.3 What this means

- **~40% of the scaffolding already exists** (right panel, model-selector stub, voice-design controlled-vocabulary pattern, SaaS-ready schema, idempotent migrations, additive public API). The work is mostly *filling in* and *replacing the textarea*, not greenfield.
- The single biggest new dependency is the **rich editor** (TipTap) and its **serialization/validation** core — these are the highest-risk items and get exemplar TDD detail in §15.
- VRAM management is the biggest backend risk: multiple models cannot be resident at once on a typical self-hosted GPU.

---

## 2. Architectural Decisions

### AD-1 — Editor library: **TipTap v2 (ProseMirror)** ✅ recommended over Lexical

| Criterion | TipTap v2 | Lexical | Verdict |
|-----------|-----------|---------|---------|
| Custom inline atoms (emotion tags as non-editable chips) | First-class `Node` with `atom: true` + React `NodeViewRenderer` | Custom `DecoratorNode` | Both capable; TipTap more ergonomic |
| Slash / `[` trigger menus | `@tiptap/suggestion` (the exact utility powering `@tiptap/extension-mention`) — battle-tested | Hand-rolled via `TextNode` transforms + command listener | **TipTap** — purpose-built |
| Serialization control (doc ⇄ OmniVoice `[tag]` text) | Deterministic `getText()` override / custom serializer per node; full ProseMirror schema control | `$generateNodesFromDOM` / manual node walk | **TipTap** — cleaner node→text mapping |
| React integration | `@tiptap/react` (`useEditor`, `NodeViewWrapper`) | `@lexical/react` | Even |
| Ecosystem / examples for "mention/tag" UX | Very large; mention tutorial is canonical | Smaller | **TipTap** |
| Bundle size | Larger (~ProseMirror core) | Smaller | Lexical |
| Learning curve / boilerplate | Lower | Higher | **TipTap** |
| Headless + shadcn/Tailwind styling | Yes (headless) | Yes (headless) | Even |

**Decision:** TipTap v2. The dominant requirements here — non-editable tag atoms, a `/` and `[` suggestion menu, and **strict, testable serialization to a specific text grammar** — are exactly TipTap's wheelhouse (`@tiptap/suggestion` + custom `Node`). Lexical's smaller bundle does not outweigh the boilerplate cost for this tag-centric use case. We will keep the editor **headless** and style it with the existing Tailwind tokens so it matches the design system.

Packages: `@tiptap/react`, `@tiptap/core`, `@tiptap/pm`, `@tiptap/starter-kit` (we will trim it heavily — see AD-2), `@tiptap/suggestion`.

### AD-2 — The editor is a **constrained plain-text surface**, not a Notion clone

OmniVoice consumes **plain text with inline `[tag]` tokens**. Rich formatting (bold, headings, lists) has **no meaning** to the model and would silently degrade output. Therefore:

- The document schema allows exactly: `doc → paragraph+`, `paragraph → (text | emotionTag)*`, plus hard breaks. **No** marks (bold/italic), **no** headings/lists/tables.
- This keeps serialization total and lossless, keeps the API-safe text trivial to produce, and avoids users pasting rich content that the model can't honor.
- The "Notion/modern AI writing tool feel" comes from **interaction polish** (slash menu, chips, placeholder, focus mode), not from rich-text features.

This is a deliberate scope reduction from the brief's "rich text editing" — documented here as an autonomous architectural decision for correctness. (If real rich formatting is later wanted for *display only*, it can be layered without touching the serializer.)

### AD-3 — Tags are model-scoped data, owned by the **backend**

The backend is the single source of truth for "which tags exist and which model supports them." The frontend fetches the catalog (React Query, cached) and derives the slash menu, toolbar, highlighting, and live validation from it. Rationale: the public API must validate identically to the UI; duplicating the tag list in TS would drift. A generated TS fallback (mirroring the `languages.generated.ts` pattern already in the repo) provides instant first paint and offline dev.

### AD-4 — Two distinct concepts kept separate: **Voice Design** vs **Emotion Tags**

- **Voice Design** (existing `config/voice-design.ts`, `instruct` string) = *global speaker attributes* (gender, age, accent…) applied once per generation.
- **Emotion Tags** (new) = *inline performance directions* (`[happy]`, `[whisper]`, `[singing]`) interleaved with text at specific positions.

These are not merged. Voice Design stays a sidebar control; Emotion Tags live inside the editor text. Both are model-aware (a model advertises `supported_tags` and `supported_voice_design`).

### AD-5 — Model loading: **single resident model + LRU offload**, lazy load-on-use

A self-hosted GPU typically cannot hold multiple voice models in VRAM. The registry keeps **at most one model on GPU at a time**. Switching models offloads the previous (reusing the existing `_offload_to_cpu` discipline) and loads the next on first generation. The current "load at startup" becomes "load the **default** model at startup; others lazily." A per-model async lock plus a registry-level resident-model pointer enforce safety.

### AD-6 — Serializer/validator is a **framework-free pure module**

`serializeToOmniVoice(doc)`, `parseOmniVoiceText(text, model)`, and `validateTags(text|doc, model)` are pure functions with zero React/TipTap imports (they operate on a plain doc-JSON shape and on strings). This makes them unit-testable in isolation and reusable by: the editor, the "use in API" code preview, and (ported/mirrored) the backend validator. **This is the API compatibility layer.**

### AD-7 — Additive, backward-compatible everywhere

No existing endpoint, response shape, audio URL, or DB row is broken. `model_id` is **optional** and defaults to the base model both in `/generate` and `/api/v1/text-to-speech`. Old jobs (no `model_id`) render as base model. This mirrors the repo's established "additive only" migration ethos.

### AD-8 — Plugin/extension architecture via **provider adapters**

Each model family is backed by a `ModelProvider` implementing a small interface (`load`, `generate`, `offload`, `capabilities`). Built-in providers: `OmniVoiceProvider` (wraps today's service for Base & Distilled, which share the OmniVoice runtime), `OmniVoiceSingingProvider` (Phase 8). Future custom/community models register a provider + a catalog entry. This is the seam for the "future plugin architecture" without over-building it now.

---

## 3. Backend Design

### 3.1 Model descriptor (the contract every model exposes)

A `ModelDescriptor` (pydantic) with exactly the fields the brief requires, plus operational metadata:

```python
# backend/app/models/registry_types.py  (new)
class ModelCapabilities(BaseModel):
    supports_tts: bool = True
    supports_voice_cloning: bool = False
    supports_emotions: bool = False
    supports_singing: bool = False
    supports_streaming: bool = False
    supports_api: bool = True

class ModelDescriptor(BaseModel):
    id: str                       # stable slug, e.g. "omnivoice-base"
    name: str                     # "OmniVoice Base"
    description: str
    version: str                  # "1.0.0"
    provider: str                 # "omnivoice" | "omnivoice-singing" | ...
    repo_id: str | None           # HF repo or None for local
    model_path: str | None        # resolved local path / HF id used at load
    supported_languages: list[str]  # OmniVoice language ids; [] = all/auto
    supported_tags: list[str]     # tag ids, e.g. ["laughter","sigh",...]
    supported_voice_design: list[str]  # voice-design attr values, [] = none
    capabilities: ModelCapabilities
    status: Literal["available","loading","loaded","error","disabled"]
    is_default: bool = False
    editions: list[str] = ["community"]  # which editions expose it
```

### 3.2 Built-in catalog (static seed)

```python
# backend/app/services/model_catalog.py  (new)
# The authoritative built-in list. Seeds the DB on startup (idempotent upsert).
BUILTIN_MODELS = [
  ModelDescriptor(
    id="omnivoice-base", name="OmniVoice Base", version="1.0.0",
    provider="omnivoice", repo_id="k2-fsa/OmniVoice", is_default=True,
    supported_tags=["laughter","sigh","confirmation-en","question-en",
      "question-ah","question-oh","question-ei","question-yi",
      "surprise-ah","surprise-oh","surprise-wa","surprise-yo",
      "dissatisfaction-hnn"],
    capabilities=ModelCapabilities(supports_tts=True, supports_voice_cloning=True,
      supports_emotions=True, supports_singing=False, supports_api=True),
    ... ),
  ModelDescriptor(
    id="omnivoice-distilled", name="OmniVoice Distilled", version="1.0.0",
    provider="omnivoice", repo_id="k2-fsa/OmniVoice-distilled",
    # Distilled shares Base's tag set; faster, fewer steps.
    supported_tags=[... same as base ...], ... ),
  ModelDescriptor(
    id="omnivoice-singing", name="OmniVoice Singing + Emotion", version="1.0.0",
    provider="omnivoice-singing", repo_id="k2-fsa/OmniVoice-singing",
    supported_tags=["singing","happy","sad","angry","nervous","whisper","calm","excited"],
    capabilities=ModelCapabilities(..., supports_emotions=True, supports_singing=True),
    ... ),
]
```

> **Note:** exact `repo_id`s for Distilled/Singing must be confirmed against upstream OmniVoice releases at execution time (Risk R-7). The catalog is the only place that changes.

### 3.3 Database

New table `models` (mirrors `ModelDescriptor`, JSON for list/dict fields), so custom/community models can be added at runtime and so `status` is queryable:

```sql
CREATE TABLE models (
  id VARCHAR(64) PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  version VARCHAR(32) NOT NULL DEFAULT '1.0.0',
  provider VARCHAR(64) NOT NULL,
  repo_id VARCHAR(255),
  model_path VARCHAR(512),
  supported_languages JSON,
  supported_tags JSON,
  supported_voice_design JSON,
  capabilities JSON,            -- the ModelCapabilities dict
  status VARCHAR(32) NOT NULL DEFAULT 'available',
  is_default BOOLEAN NOT NULL DEFAULT 0,
  is_builtin BOOLEAN NOT NULL DEFAULT 1,
  editions JSON,
  owner_id VARCHAR(36),         -- NULL for built-ins; set for user/community models (SaaS-ready)
  created_at DATETIME,
  updated_at DATETIME
);
```

Additive column on `generation_jobs`:

```sql
ALTER TABLE generation_jobs ADD COLUMN model_id VARCHAR(64);  -- NULL = base (back-compat)
```

Optional (Phase 8+), additive on `voice_profiles`:

```sql
ALTER TABLE voice_profiles ADD COLUMN default_model_id VARCHAR(64);  -- NULL = platform default
```

All via the existing `core/migrations.py` pattern: add to `_NEW_*_COLUMNS`, add a `models` create + idempotent **catalog upsert** step (`INSERT … ON CONFLICT(id) DO UPDATE` for built-ins, never clobbering user-owned rows).

### 3.4 Services

```
backend/app/services/
  model_registry.py        # NEW — async singleton: catalog cache, resident-model pointer,
                           #       per-model lock, load/offload/evict, capabilities lookup
  model_providers/
    base.py                # NEW — ModelProvider ABC: load(), generate(), offload(), descriptor
    omnivoice_provider.py  # NEW — wraps the EXISTING OmniVoiceService for base/distilled
    omnivoice_singing_provider.py  # Phase 8
  omnivoice_service.py     # KEPT — refactored so the singleton is parameterised by repo_id
                           #        (currently reads settings.OMNIVOICE_MODEL directly)
  tag_catalog.py           # NEW — supported_tags + metadata (label, emoji, category, syntax)
```

`ModelRegistry` responsibilities:
- `list_models() -> list[ModelDescriptor]` (filtered by `EDITION`)
- `get(model_id) -> ModelDescriptor`
- `resolve_default() -> ModelDescriptor`
- `ensure_loaded(model_id)` — lazy load; offload current resident if different (LRU=1)
- `generate(model_id, **params)` — delegates to provider under the model's lock
- `status(model_id)` / `status_all()`

VRAM contract preserved: provider's `generate` keeps the existing offload-to-CPU + `empty_cache` in `finally`. Registry guarantees **one resident GPU model**; a model switch triggers `offload()` on the outgoing model before `load()` on the incoming.

### 3.5 API surface (all additive)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/models` | List available models (descriptors, edition-filtered) |
| GET | `/models/{id}` | One descriptor |
| GET | `/models/{id}/tags` | Tag catalog with metadata (label/emoji/category) for this model |
| GET | `/models/{id}/status` | Per-model load state |
| GET | `/models/status` | **KEPT** — aggregate/default model state (back-compat) |
| POST | `/generate` | **EXTENDED** — accepts optional `model_id` (defaults to base) |
| GET | `/api/v1/models` | Public list (capabilities + tags), API-key auth |
| POST | `/api/v1/text-to-speech` | **EXTENDED** — optional `modelId` |

`POST /generate` validates: model exists & enabled; tags in `text` ⊆ model's `supported_tags` (422 with the offending tags otherwise — the authoritative safety net behind the UI). Threads `model_id` into the `GenerationJob` row and `_process_job` → `registry.generate(model_id, …)`.

---

## 4. Frontend Design

### 4.1 New module map

```
frontend/src/
  editor/                              # NEW — framework-isolated editor core + React glue
    serialize.ts                       # serializeToOmniVoice(docJSON) -> string   (pure)
    parse.ts                           # parseOmniVoiceText(text, model) -> docJSON (pure)
    validate.ts                        # validateTags(text|docJSON, model) -> Issue[] (pure)
    tags.ts                            # ModelTag type + helpers; fetch-or-fallback
    extensions/
      EmotionTag.ts                    # TipTap atom Node (attrs: tagId, modelId)
      EmotionTagView.tsx               # React NodeView — renders "😊 happy" chip
      SlashMenu.ts                     # @tiptap/suggestion config for "/"
      BracketMenu.ts                   # @tiptap/suggestion config for "["
      TagHighlight.ts                  # decoration plugin: invalid-tag underline
    PerformanceEditor.tsx              # the client-island editor component
    EmotionToolbar.tsx                 # lightweight ElevenLabs-style toolbar
    useTagMenuItems.ts                 # builds menu items from active model's tags
  hooks/
    use-models.ts                      # useModels(), useModelTags(id), useActiveModel()
  components/generation/
    ModelSelector.tsx                  # REPLACE stub -> live registry, capability badges
    ModelInfoCard.tsx                  # NEW — model description + capability chips + tag list
    EmotionSettings.tsx                # NEW — sidebar emotion controls (intensity presets etc.)
  app/page.tsx                         # REWORK — center = <PerformanceEditor/>, sidebar grows
```

### 4.2 Editor document model & rendering

- **Internal doc** (TipTap/ProseMirror JSON): paragraphs of `text` nodes and `emotionTag` atom nodes `{ type:"emotionTag", attrs:{ tagId:"happy", modelId:"omnivoice-singing" } }`.
- **On screen**: each `emotionTag` renders as a non-editable rounded chip "😊 happy" (emoji + label from the tag catalog), themed with status tokens; invalid tags render red with a tooltip.
- **Serialized out** (to backend / API preview): `serializeToOmniVoice` walks the doc; `text` nodes emit verbatim, `emotionTag` nodes emit `[tagId]`, paragraph breaks emit `\n`. Result is exactly today's OmniVoice syntax.
- **Pasted/loaded in**: `parseOmniVoiceText` regex-tokenises `\[([a-z0-9-]+)\]`; known-for-model tags → tag nodes, unknown → either literal text or an `invalid` tag node (policy flag), everything else → text. Enables History "Regenerate" round-trips and editing existing scripts.

### 4.3 Insertion UX (three mechanisms, one menu)

- **`/` slash menu** and **`[` bracket menu** both open the same shadcn `command`-styled list, fed by `useTagMenuItems(activeModel)` → emoji + label + category groups (Emotions, Effects, Singing…). Selecting inserts an `emotionTag` node and removes the trigger char. Keyboard: ↑/↓ navigate, Enter/Tab insert, Esc close. Typing filters fuzzily.
- **Toolbar** (`EmotionToolbar.tsx`): a clean row of the most common tags for the active model as one-click chips + an "Insert emotion ▾" dropdown for the full set. Inserts at the caret.
- Users never type raw `[tag]` syntax; if they do, it still parses and highlights correctly.

### 4.4 Dynamic, model-aware UI

A `useActiveModel()` hook (reads `selectedModelId` from Zustand, joins with `useModels()`/`useModelTags()`) drives, reactively, on model change:
- Toolbar chip set, slash/bracket menu items, live validation set, `ModelInfoCard`, capability-gated controls (e.g. hide singing affordances unless `supports_singing`), and re-validation of existing editor content (tags now-unsupported flip to invalid).

### 4.5 Right sidebar (the control surface)

Accordion (shadcn `accordion`) sections, top→bottom, with the **Generate** button pinned at the bottom of the panel:

1. **Voice** (`VoiceSelector` — existing)
2. **Model** (`ModelSelector` — live)
3. **Generation Settings** (`GenerationSettings` — existing)
4. **Output Format** (`OutputFormatSelector` — existing)
5. **Language** (`LanguageCombobox` — moved from below editor)
6. **Voice Design** (`VoiceDesignBuilder` — moved from below editor)
7. **Emotion Settings** (`EmotionSettings` — new)
8. **Model Information** (`ModelInfoCard` — new)
9. **Generate Speech** (pinned button)

---

## 5. Serialization & Validation Architecture

### 5.1 Grammar

```
script   := line ( "\n" line )*
line     := token*
token    := TEXT | TAG
TAG      := "[" tag-id "]"
tag-id   := [a-z0-9] [a-z0-9-]*
```

### 5.2 Functions (pure, in `frontend/src/editor/`)

- `serializeToOmniVoice(docJSON): string` — total function, never throws; tag nodes → `[tagId]`.
- `parseOmniVoiceText(text, model): DocJSON` — tokenise; classify each tag against `model.supported_tags`.
- `validateTags(input, model): Issue[]` — `Issue = { tagId, from, to, reason: "unsupported"|"unknown" }`. Used live in the editor (decorations) and by the "can I generate?" gate.

### 5.3 Three validation layers

1. **Live (editor)** — `TagHighlight` decoration marks unsupported/unknown tags; a small validation summary lists them. Non-blocking.
2. **Pre-submit (gate)** — Generate is **disabled** (or warns) if `validateTags` returns issues, with a "Fix tags / switch model" affordance. Configurable: strict (block) vs lenient (strip unsupported on serialize).
3. **Backend (authoritative)** — `/generate` re-validates against the model's `supported_tags`; returns 422 listing offending tags. Protects API clients and guarantees UI/API parity (AD-3, AD-6).

Example required behavior: with `omnivoice-base` selected, `[singing]` → live red highlight + pre-submit block + (if forced via API) 422. With `omnivoice-singing` selected, `[singing]` → valid chip, generates.

---

## 6. API Compatibility Layer

- The **same** `serializeToOmniVoice` that feeds the editor's hidden value feeds the **"Use in API"** code preview (`components/api/UseInApiDialog.tsx`), so the JSON body's `text` is exactly what the model will receive.
- Public API contract (additive):

```jsonc
POST /api/v1/text-to-speech
{
  "voiceId": "voice_8JXQ29K4L3",
  "modelId": "omnivoice-singing",   // NEW, optional; defaults to base
  "text": "Hello [happy] it's great to see you [laughter]",
  "language": "en",
  "format": "wav"
}
```

- `GET /api/v1/models` lets SDK users discover models + capabilities + tags programmatically.
- Old clients omitting `modelId` keep working unchanged (defaults to base).

---

## 7. UX Proposals

### 7.1 Wireframe — desktop (`xl` and up)

```
┌───────────┬────────────────────────────────────────────┬───────────────────────────┐
│           │  Text to Speech                              │  ┌ Voice ─────────────┐    │
│  Sidebar  │  Direct a voice performance.                 │  │ ● Aria (EN)      ▾ │    │
│  (nav)    │                                              │  └────────────────────┘    │
│           │  ┌────────────────────────────────────────┐ │  ┌ Model ─────────────┐    │
│  TTS ◀    │  │ Toolbar: 😊 😢 😡 🤫 🎵  [Insert ▾]     │ │  │ OmniVoice Singing ▾│    │
│  Voices   │  ├────────────────────────────────────────┤ │  └ caps: 🎵 clone 😊 ─┘    │
│  Clone    │  │                                          │ │  ▸ Generation Settings     │
│  History  │  │  Welcome back 😊 happy  — I missed       │ │  ▸ Output Format           │
│  Settings │  │  you 🤫 whisper  it's a secret.          │ │  ▸ Language                │
│           │  │                                          │ │  ▸ Voice Design            │
│           │  │  (type "/" or "[" for emotions)          │ │  ▸ Emotion Settings        │
│           │  │                                          │ │  ▸ Model Information        │
│           │  └────────────────────────────────────────┘ │  ┌──────────────────────┐  │
│           │  ⚠ 0 issues · 142 chars · ~9s est.           │  │  ⚡ Generate Speech   │  │
│           │                                              │  └──────────────────────┘  │
├───────────┴────────────────────────────────────────────┴───────────────────────────┤
│  ▶  Aria — "Welcome back…"      ──────●────────  0:03 / 0:09        ⤓ wav   ↻         │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Wireframe — tablet / mobile (`< xl`)

Editor is full-width; the sidebar collapses behind the existing floating **Panel** trigger → right slide-over `Sheet` (reusing `PageLayout`'s mechanism). Generate also available as a sticky bottom bar above the player. Toolbar collapses to "😊 Insert emotion ▾".

### 7.3 Interaction flow — inserting an emotion

```
caret in editor ──type "/"──▶ command menu opens (grouped by category)
   │                               │ ↑/↓ filter, Enter/Tab select
   │                               ▼
   └────────────── inserts non-editable "😊 happy" chip at caret, removes "/"
caret in editor ──type "["──▶ same menu (bracket mode), Enter inserts chip
toolbar ──click 😊 chip──▶ inserts at caret
toolbar ──"Insert ▾"──▶ full categorized list
```

### 7.4 Interaction flow — switching model with incompatible tags

```
script has [singing] + model = OmniVoice Base
user opens Model ▾ ──selects OmniVoice Base──▶ useActiveModel re-validates
   ▼
[singing] chip turns red · summary: "1 unsupported tag: singing"
Generate disabled · CTA: "Remove tag" | "Switch to OmniVoice Singing"
```

### 7.5 "Directing a voice performance" — reinforcing the concept

- Page subtitle: **"Direct a voice performance."** (not "Generate audio").
- Toolbar grouped as **performance directions**: *Emotion*, *Delivery* (whisper/calm/excited), *Vocal* (singing), *Reactions* (laughter/sigh/surprise).
- Generate button reads **"⚡ Generate Speech"**; while running, a "Directing…" micro-copy.
- Chips use warm, human emoji; hover shows a one-line "what this does to the voice" description from the tag catalog.
- Empty-state placeholder coaches: *"Write your script. Type `/` to add emotion, whisper, or singing."*
- Model Info card frames capabilities as *what this performer can do* (🎵 can sing, 😊 emotional range, 🗣️ clones voices).

---

## 8. Epic → Phase → Milestone → Task Breakdown

> Each Phase = one shippable increment behind a flag where risky. Tasks are at "half-day or less" granularity; the executing agent expands each into TDD steps via `writing-plans`.

### EPIC A — Multi-Model Backend Foundation  → **Phase 1**

**Goal:** Replace the hardcoded single model with a registry + provider abstraction, additively, with no behavior change for the default model.

- **M1.1 Descriptors & catalog**
  - T1.1.1 `registry_types.py`: `ModelCapabilities`, `ModelDescriptor` (+ schema tests).
  - T1.1.2 `model_catalog.py`: `BUILTIN_MODELS` (base default; distilled; singing entries).
  - T1.1.3 `tag_catalog.py`: tag id → `{label, emoji, category, description, syntax}` for all Base + Singing tags.
- **M1.2 Persistence**
  - T1.2.1 `models` table in `models/db.py`.
  - T1.2.2 `generation_jobs.model_id` column.
  - T1.2.3 Migration: create `models`, add column, idempotent built-in **upsert** (extend `core/migrations.py`).
- **M1.3 Provider + registry**
  - T1.3.1 `ModelProvider` ABC (`model_providers/base.py`).
  - T1.3.2 Refactor `OmniVoiceService` to be parameterised by `repo_id` (remove direct `settings.OMNIVOICE_MODEL` read; default still resolves to it).
  - T1.3.3 `OmniVoiceProvider` wrapping the service (base + distilled).
  - T1.3.4 `ModelRegistry` singleton: catalog cache, resident-model pointer, per-model lock, `ensure_loaded`/`offload`/`generate`/`status`. Preserve VRAM offload contract.
  - T1.3.5 `main.py` lifespan: load **default** model on startup via registry (others lazy).
- **M1.4 API**
  - T1.4.1 `api/models.py`: `GET /models`, `/models/{id}`, `/models/{id}/tags`, `/models/{id}/status`; keep `/models/status` aggregate.
  - T1.4.2 `POST /generate`: accept optional `model_id`, validate existence + tags, persist to job, route through registry.
  - T1.4.3 `_process_job`: read `model_id`, call `registry.generate`.
- **Acceptance:** see §14 Phase 1.

### EPIC B — Experience Shell Redesign  → **Phase 2**

**Goal:** Move Language + Voice Design into the right sidebar; restructure the panel into the 9-section accordion with a pinned Generate; center column reserved for the editor (still the textarea until Phase 3). No functional regressions.

- **M2.1** Sidebar accordion scaffold (`GenerationPanel` → accordion sections in the §4.5 order).
- **M2.2** Move `LanguageCombobox` + `VoiceDesignBuilder` from `page.tsx` into sidebar sections; wire to store (already in store).
- **M2.3** Pin Generate button to panel bottom; keep `canGenerate` logic.
- **M2.4** Responsive: verify slide-over `Sheet` carries all sections; sticky mobile Generate.
- **Acceptance:** §14 Phase 2.

### EPIC C — Rich Editor  → **Phases 3–6**

#### Phase 3 — Rich editor foundation
- **M3.1** Add TipTap deps; `PerformanceEditor.tsx` headless + Tailwind-styled; constrained schema (AD-2).
- **M3.2** Bind editor ⇄ store: editor holds doc JSON; `serializeToOmniVoice` produces `ttsText`; Generate uses serialized text.
- **M3.3** Replace `<Textarea>` in `page.tsx` with `<PerformanceEditor>`; preserve quick-prompts behavior (insert into editor) and Regenerate prefill (parse text → doc).
- **M3.4** Empty-state placeholder + char/est-duration footer.

#### Phase 4 — Tag system (serialization core)
- **M4.1** `serialize.ts`, `parse.ts`, `tags.ts` pure modules (**fully TDD — see §15.1/§15.2**).
- **M4.2** `EmotionTag` atom Node + `EmotionTagView` chip renderer.
- **M4.3** `TagHighlight` decoration for invalid tags.
- **M4.4** `useModelTags` + generated TS fallback (mirror `languages.generated.ts`).

#### Phase 5 — Slash & bracket commands
- **M5.1** `SlashMenu.ts` via `@tiptap/suggestion` (`/` trigger) + shadcn `command` popup.
- **M5.2** `BracketMenu.ts` (`[` trigger) reusing the same item source/renderer.
- **M5.3** Keyboard shortcuts (↑/↓/Enter/Tab/Esc), fuzzy filter, category grouping.

#### Phase 6 — Emotion toolbar
- **M6.1** `EmotionToolbar.tsx`: common-tag chips + "Insert ▾" full list, caret insertion.
- **M6.2** `EmotionSettings.tsx` sidebar section.
- **M6.3** Accessibility pass (roles, labels, focus, contrast) on menus/toolbar/chips.

### EPIC D — Validation & Model-Aware UI  → **Phase 7**

- **M7.1** `validate.ts` pure module (**TDD — see §15.3**).
- **M7.2** `useActiveModel()`; reactive re-validation on model switch.
- **M7.3** Pre-submit gate (strict/lenient) + "switch model / remove tag" CTAs.
- **M7.4** `ModelSelector` live (capability badges) + `ModelInfoCard`.
- **M7.5** Backend authoritative tag validation on `/generate` (422 contract) + tests.

### EPIC E — OmniVoice Singing Integration  → **Phase 8**

- **M8.1** `OmniVoiceSingingProvider`; confirm upstream repo id + load path.
- **M8.2** Verify Singing tags end-to-end (`[singing]`, `[happy]`…); capability gating in UI.
- **M8.3** Model-switch VRAM eviction test under real load.
- **M8.4** Distilled model validated (fewer steps default surfaced in settings).

### EPIC F — API Compatibility & Documentation  → **Phases 9–10**

#### Phase 9 — API compatibility
- **M9.1** `/api/v1/models` endpoint + camelCase schema.
- **M9.2** `modelId` on `/api/v1/text-to-speech` (default base) + validation parity.
- **M9.3** "Use in API" dialog uses shared serializer; examples include `modelId`.

#### Phase 10 — Documentation
- **M10.1** Update `docs/VOICE_MODEL.md`, `docs/API.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `frontend/AGENTS.md`/`CLAUDE.md` model+editor sections.
- **M10.2** In-app Model Information content + tag glossary.
- **M10.3** `CHANGELOG.md` entry; migration notes for self-hosters.

---

## 9. Dependency Graph

```
Phase 1 (registry backend) ──┬─▶ Phase 7 (validation needs model tag sets from API)
                              ├─▶ Phase 8 (providers + registry)
                              └─▶ Phase 9 (public model API)

Phase 2 (sidebar redesign) ──▶ Phase 6 (toolbar/EmotionSettings live in sidebar)
                              └─▶ (Model/ModelInfo sidebar sections in Phase 7)

Phase 3 (editor foundation) ─▶ Phase 4 (tag nodes/serialization) ─▶ Phase 5 (menus)
                                                                  └▶ Phase 6 (toolbar)
Phase 4 (serializer) ────────▶ Phase 7 (validation) ─▶ Phase 9 (API shares serializer)
Phase 7 ─▶ Phase 8 (singing exercises validation + model switch)
Everything ─▶ Phase 10 (docs)

Critical path:  P1 → P3 → P4 → P7 → P8 → P9 → P10
Parallelisable: P2 alongside P1; P5 & P6 after P4 (can run concurrently).
```

**Hard prerequisites:** P4 requires P3; P5/P6 require P4; P7 requires P1 + P4; P8 requires P1 + P7; P9 requires P1 + P4.

---

## 10. Risk Analysis

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| R-1 | **VRAM**: multiple models can't co-reside; switching thrashes load/offload (slow) | High | High | LRU=1 resident (AD-5); lazy load; surface "loading model…" state; keep base resident by default; document GPU expectations |
| R-2 | **Serializer round-trip bugs** corrupt user text or drop tags | Med | High | Pure functions + exhaustive property/round-trip TDD (§15); serializer never throws; backend is authoritative validator |
| R-3 | **TipTap learning curve / schema escapes** (users paste rich content) | Med | Med | Constrained schema (AD-2) strips marks on paste; spike in P3 before committing UX |
| R-4 | **UI/API tag-validation drift** | Med | Med | Single backend source of truth (AD-3); backend re-validates (AD-6); contract tests assert parity |
| R-5 | **Model load time** blocks first generation, looks broken | Med | Med | Per-model status endpoint + UI "loading" affordance; preload default at startup (existing behavior) |
| R-6 | **Regression** in the preserved ML inference path during refactor | Low | High | OmniVoiceService refactor keeps identical call signature; golden-output test on base model before/after |
| R-7 | **Unknown upstream repo ids / capabilities** for Distilled & Singing | Med | Med | Catalog is the only change point; confirm at P8 start; gate Distilled/Singing behind `status="available"` once verified |
| R-8 | **Mobile editor ergonomics** (slash menu on touch keyboards) | Med | Low | Toolbar is the primary mobile path; `/`+`[` are progressive enhancement |
| R-9 | **Scope creep** toward full rich text | Med | Med | AD-2 documented; reject marks/lists in schema |
| R-10 | **Migration on large existing DBs** | Low | Med | Additive `ADD COLUMN` only; built-in upsert idempotent; tested on a copy |

---

## 11. Migration Strategy

- **Schema:** only additive `ALTER TABLE ADD COLUMN` + a new `models` table, via the existing `core/migrations.py` runner (idempotent, SQLite-safe, re-runnable). Built-in models upserted by `id` on every startup so catalog edits propagate without clobbering user/community rows.
- **Data:** existing `generation_jobs` rows have `model_id = NULL` → treated as `omnivoice-base`. No backfill required (NULL-as-default), but an optional backfill step can set `model_id='omnivoice-base'` for completeness.
- **Behavior parity:** the default model path is byte-for-byte the current path (R-6 golden test).
- **Frontend:** `ttsText` in the store remains the serialized OmniVoice string, so History/Regenerate keep working; editor parses it back via `parseOmniVoiceText`.
- **Rollback:** new columns/table are inert if the new code is reverted; old code ignores `model_id`. Safe to roll back per phase.

---

## 12. Testing Strategy

| Layer | Tooling | Coverage |
|-------|---------|----------|
| Backend unit | pytest (existing `backend/tests/`) | descriptors/catalog validation; registry load/offload/evict (mocked provider); migration idempotency (re-run twice → no-op); tag validation 422 |
| Backend contract | pytest + httpx | `/models*` shapes; `/generate` with/without `model_id`; `/api/v1/models`; UI/API validation parity |
| Backend golden | pytest | base-model generation output stable across the service refactor (R-6) |
| Editor pure-core | Vitest (mirror `scripts/generate-languages.test.mjs` ethos) | `serialize`/`parse` **round-trip** (`parse(serialize(doc)) ≅ doc`, `serialize(parse(text)) === text`); `validate` per model; never-throws property tests |
| Frontend component | Vitest + Testing Library | EmotionTag chip render; slash/bracket menu insert; toolbar insert; model-switch re-validation; pre-submit gate |
| E2E (smoke) | Playwright (or manual checklist, repo has chrome-devtools MCP) | type script → insert emotion via `/`, `[`, toolbar → switch model invalidates `[singing]` → generate → audio plays in BottomPlayer |
| Accessibility | a11y MCP / manual | menu roles, focus trap, chip labels, contrast (Phase 6 gate) |

TDD is mandatory for the three pure cores (§15). Every task lands with its tests; frequent commits.

---

## 13. Rollout Strategy

- **Per-phase merges** to `feat/voice-performance-platform`, each phase independently green (build + lint + tests) and demoable.
- **Feature flag** `NEXT_PUBLIC_RICH_EDITOR` (default off until Phase 4 complete) lets the textarea remain the fallback; flip on once serializer round-trips are proven. Backend `model_id` is always safe (defaults to base).
- **Edition gating:** Distilled/Singing exposed via catalog `editions` + `status`; Community sees what's verified.
- **Order of value delivery:** P1 (invisible plumbing) → P2 (layout) → P3 (editor behind flag) → P4 (tags) → P5/P6 (insertion UX) → P7 (validation, flip flag on) → P8 (new model) → P9 (API) → P10 (docs).
- **Canary:** dogfood on local self-hosted instance through P7 before announcing multi-model in the public API (P9).
- Final integration PR from `feat/voice-performance-platform` → `main` after Phase 10, with the migration notes from M10.3.

---

## 14. Acceptance Criteria (per phase)

**Phase 1 — Multi-model backend**
- `GET /models` returns ≥1 model; base is `is_default`, `status` reflects load state.
- `POST /generate` works with no `model_id` (base) **and** with an explicit valid `model_id`; invalid id → 404, unsupported tag → 422.
- Default model still loads at startup; only one model resident on GPU at a time (verified via logs/metrics).
- Migration re-runs cleanly twice; existing jobs unaffected. Golden base-model output unchanged.

**Phase 2 — Layout**
- Language + Voice Design now live in the right sidebar accordion (9 sections, §4.5 order); Generate pinned at panel bottom.
- No functional regression: selecting voice, settings, output format, generate all behave as before; mobile slide-over shows all sections.

**Phase 3 — Editor foundation**
- Center column is the TipTap editor; typing plain text generates identically to the old textarea (serialized text == typed text when no tags).
- Quick-prompts insert into the editor; History "Regenerate" prefills the editor via parse.

**Phase 4 — Tag system**
- Emotion tags render as "😊 happy" chips; `serialize`/`parse` round-trip tests pass; invalid tags visibly highlighted.

**Phase 5 — Slash/bracket commands**
- `/` and `[` both open the same categorized menu; keyboard nav + fuzzy filter work; selection inserts a chip and removes the trigger char.

**Phase 6 — Toolbar**
- Toolbar chips + "Insert ▾" insert tags at the caret; a11y checks pass.

**Phase 7 — Validation & model-aware UI**
- With Base selected, `[singing]` is flagged (live + pre-submit) and backend returns 422 if forced; with Singing selected it's valid and generates.
- Switching models live re-validates existing content; `ModelSelector` shows capabilities; `ModelInfoCard` accurate.

**Phase 8 — Singing**
- OmniVoice Singing loads, generates with `[singing]`/emotion tags; model switch evicts the previous model without OOM; Distilled validated.

**Phase 9 — API compatibility**
- `GET /api/v1/models` lists models+capabilities+tags; `POST /api/v1/text-to-speech` honors optional `modelId` (defaults base) with the same tag validation as the UI; "Use in API" preview matches generated audio input.

**Phase 10 — Documentation**
- Docs updated (VOICE_MODEL, API, ARCHITECTURE, ROADMAP, CHANGELOG); in-app model info + tag glossary present; self-hoster migration notes published.

---

## 15. Exemplar Bite-Sized Tasks (the three highest-risk cores, fully specified)

These are written to the full `writing-plans` TDD granularity as the template the executing agent follows for every other task. Vitest assumed for frontend pure modules.

### 15.1 `serializeToOmniVoice` (Phase 4)

**Files:**
- Create: `frontend/src/editor/serialize.ts`
- Test: `frontend/src/editor/serialize.test.ts`

- [ ] **Step 1 — Write the failing test**
```ts
import { describe, it, expect } from "vitest";
import { serializeToOmniVoice } from "./serialize";

const doc = {
  type: "doc",
  content: [
    { type: "paragraph", content: [
      { type: "text", text: "Hello " },
      { type: "emotionTag", attrs: { tagId: "happy", modelId: "omnivoice-singing" } },
      { type: "text", text: " world" },
    ]},
  ],
};

describe("serializeToOmniVoice", () => {
  it("renders tag nodes as [tagId] inline with text", () => {
    expect(serializeToOmniVoice(doc)).toBe("Hello [happy] world");
  });
  it("joins multiple paragraphs with newlines", () => {
    const d = { type: "doc", content: [
      { type: "paragraph", content: [{ type: "text", text: "a" }] },
      { type: "paragraph", content: [{ type: "text", text: "b" }] },
    ]};
    expect(serializeToOmniVoice(d)).toBe("a\nb");
  });
  it("returns '' for an empty doc and never throws on missing content", () => {
    expect(serializeToOmniVoice({ type: "doc" })).toBe("");
  });
});
```

- [ ] **Step 2 — Run, expect FAIL**
Run: `cd frontend && npx vitest run src/editor/serialize.test.ts`
Expected: FAIL — "serializeToOmniVoice is not a function".

- [ ] **Step 3 — Minimal implementation**
```ts
type DocNode = { type: string; text?: string; attrs?: Record<string, unknown>; content?: DocNode[] };

export function serializeToOmniVoice(doc: DocNode): string {
  const paragraphs = (doc.content ?? []).map(serializeBlock);
  return paragraphs.join("\n");
}

function serializeBlock(node: DocNode): string {
  return (node.content ?? []).map(serializeInline).join("");
}

function serializeInline(node: DocNode): string {
  if (node.type === "text") return node.text ?? "";
  if (node.type === "emotionTag") return `[${String(node.attrs?.tagId ?? "")}]`;
  if (node.type === "hardBreak") return "\n";
  return "";
}
```

- [ ] **Step 4 — Run, expect PASS**
Run: `cd frontend && npx vitest run src/editor/serialize.test.ts` → PASS.

- [ ] **Step 5 — Commit**
```bash
git add frontend/src/editor/serialize.ts frontend/src/editor/serialize.test.ts
git commit -m "feat(editor): add serializeToOmniVoice doc→text serializer"
```

### 15.2 `parseOmniVoiceText` + round-trip (Phase 4)

**Files:**
- Create: `frontend/src/editor/parse.ts`
- Test: `frontend/src/editor/parse.test.ts`

- [ ] **Step 1 — Failing test (incl. round-trip with the serializer)**
```ts
import { describe, it, expect } from "vitest";
import { parseOmniVoiceText } from "./parse";
import { serializeToOmniVoice } from "./serialize";

const model = { id: "omnivoice-singing", supported_tags: ["happy", "singing", "whisper"] };

describe("parseOmniVoiceText", () => {
  it("converts known [tag] tokens to emotionTag nodes, text to text nodes", () => {
    const doc = parseOmniVoiceText("Hi [happy] there", model);
    const inline = doc.content[0].content;
    expect(inline[0]).toMatchObject({ type: "text", text: "Hi " });
    expect(inline[1]).toMatchObject({ type: "emotionTag", attrs: { tagId: "happy", modelId: "omnivoice-singing" } });
    expect(inline[2]).toMatchObject({ type: "text", text: " there" });
  });
  it("marks unknown/unsupported tags as invalid", () => {
    const doc = parseOmniVoiceText("a [singing] b [bogus]", model);
    const tags = doc.content[0].content.filter((n: any) => n.type === "emotionTag");
    expect(tags[0].attrs.invalid).toBe(false);
    expect(tags[1].attrs.invalid).toBe(true);
  });
  it("round-trips: serialize(parse(text)) === text", () => {
    const text = "Hello [happy] world\n[whisper] secret";
    expect(serializeToOmniVoice(parseOmniVoiceText(text, model))).toBe(text);
  });
  it("never throws on empty/edge input", () => {
    expect(() => parseOmniVoiceText("", model)).not.toThrow();
    expect(() => parseOmniVoiceText("[]", model)).not.toThrow();
  });
});
```

- [ ] **Step 2 — Run, expect FAIL** (`npx vitest run src/editor/parse.test.ts`).

- [ ] **Step 3 — Minimal implementation**
```ts
const TAG_RE = /\[([a-z0-9][a-z0-9-]*)\]/g;
type Model = { id: string; supported_tags: string[] };

export function parseOmniVoiceText(text: string, model: Model) {
  const lines = text.split("\n");
  return {
    type: "doc",
    content: lines.map((line) => ({ type: "paragraph", content: parseInline(line, model) })),
  };
}

function parseInline(line: string, model: Model) {
  const out: any[] = [];
  let last = 0; let m: RegExpExecArray | null;
  TAG_RE.lastIndex = 0;
  while ((m = TAG_RE.exec(line)) !== null) {
    if (m.index > last) out.push({ type: "text", text: line.slice(last, m.index) });
    const tagId = m[1];
    out.push({ type: "emotionTag", attrs: {
      tagId, modelId: model.id, invalid: !model.supported_tags.includes(tagId),
    }});
    last = m.index + m[0].length;
  }
  if (last < line.length) out.push({ type: "text", text: line.slice(last) });
  return out;
}
```

- [ ] **Step 4 — Run, expect PASS.**
- [ ] **Step 5 — Commit** `feat(editor): add parseOmniVoiceText with round-trip guarantees`.

### 15.3 Backend authoritative tag validation (Phase 7)

**Files:**
- Create: `backend/app/services/tag_validation.py`
- Modify: `backend/app/api/generation.py` (call before job creation)
- Test: `backend/tests/test_tag_validation.py`

- [ ] **Step 1 — Failing test**
```python
import pytest
from app.services.tag_validation import extract_tags, find_unsupported_tags

def test_extract_tags_finds_bracket_tokens():
    assert extract_tags("Hi [happy] there [singing]") == ["happy", "singing"]

def test_find_unsupported_returns_offenders():
    supported = ["laughter", "sigh"]
    assert find_unsupported_tags("ok [laughter] no [singing]", supported) == ["singing"]

def test_no_tags_is_empty():
    assert find_unsupported_tags("plain text", ["happy"]) == []
```

- [ ] **Step 2 — Run, expect FAIL** (`cd backend && python -m pytest tests/test_tag_validation.py -v`).

- [ ] **Step 3 — Implementation**
```python
import re
_TAG_RE = re.compile(r"\[([a-z0-9][a-z0-9-]*)\]")

def extract_tags(text: str) -> list[str]:
    return _TAG_RE.findall(text or "")

def find_unsupported_tags(text: str, supported: list[str]) -> list[str]:
    allowed = set(supported)
    seen, bad = set(), []
    for tag in extract_tags(text):
        if tag not in allowed and tag not in seen:
            seen.add(tag); bad.append(tag)
    return bad
```

- [ ] **Step 4 — Run, expect PASS.**

- [ ] **Step 5 — Wire into `/generate` (write the endpoint test first, then the call)**
Endpoint test asserts: posting `text="[singing]"` with `model_id="omnivoice-base"` → HTTP 422, body lists `"singing"`.
Then in `create_generation_job`, after resolving the model descriptor:
```python
from app.services.tag_validation import find_unsupported_tags
bad = find_unsupported_tags(request.text, model.supported_tags)
if bad:
    raise HTTPException(status_code=422, detail={"unsupported_tags": bad, "model_id": model.id})
```

- [ ] **Step 6 — Commit** `feat(api): reject unsupported emotion tags per model with 422`.

---

## 16. Self-Review (against the spec)

- **Goal #1 Multi-model** → Epic A / Phase 1; descriptor exposes every required field (§3.1); registry, loading/switching/compatibility, provider plugin seam (AD-8). ✅
- **Goal #2 Rich editor** → Phases 3–6; TipTap recommended with rationale (AD-1); rich/emotion/model tags, autocomplete, slash, shortcuts, highlighting, validation, a11y. ✅
- **Goal #3 Emotion insertion (`/`, `[`, toolbar)** → Phases 5–6 (§4.3, §7.3). ✅
- **Goal #4 Visual tags / serialization** → §4.2, §5, exemplar §15.1–15.2; backend gets `[tag]` syntax. ✅
- **Goal #5 Layout redesign** → Phase 2 (§4.5, wireframes §7.1–7.2). ✅
- **Goal #6 Model-specific UI** → Phase 7 (`useActiveModel`, §4.4, flow §7.4). ✅
- **Goal #7 API compatibility** → §6, Phase 9; shared serializer = API-safe text (AD-6). ✅
- **Goal #8 Voice performance UX** → §7.5. ✅
- **Goal #9 Implementation plan** → §8–§14 (epics, phases, tasks, deps, migration, testing, rollout, acceptance), all 10 named phases present. ✅
- Placeholder scan: exemplar tasks contain real code/commands; remaining tasks explicitly deferred to per-phase `writing-plans` expansion (stated in §0). 
- Type consistency: `model_id` (snake, backend/store) vs `modelId` (camel, public API) is intentional and matches the repo's existing convention (`schemas/api.py`). `emotionTag` node + `tagId`/`modelId`/`invalid` attrs used consistently across §4.2, §15.1, §15.2.

---

## 17. Open Questions for the User (non-blocking; sensible defaults chosen)

1. **Distilled & Singing repo ids/capabilities** — assumed `k2-fsa/OmniVoice-distilled` / `-singing`; confirm at Phase 8 (Risk R-7).
2. **Strict vs lenient tag policy default** — plan defaults to **strict** (block + 422). Flip to lenient (strip on serialize) if you prefer.
3. **Rich formatting** — deliberately excluded (AD-2). Confirm you don't need bold/headings in scripts.
4. **TipTap license/bundle** — TipTap v2 core is MIT/open-source; no Pro extensions required by this plan.

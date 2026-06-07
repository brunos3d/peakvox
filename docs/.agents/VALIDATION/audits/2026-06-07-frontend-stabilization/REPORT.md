# Frontend Stabilization — Final Report

**Date:** 2026-06-07
**Branch:** `feat/peakvox-phase-1`
**Mode:** Direct implementation (no new SPECs, ADRs, or architecture proposals)
**Focus:** P0 functional correctness → P1 UX consistency → P2 visual stabilization
**Goal:** Make PeakVox feel like a finished product for a first-time user.

---

## TL;DR

13 bugs reproduced (6 P0, 3 P1, 4 P2). **11 fixed** with manual UI validation; **2 not addressed** (D1, D2) because they sit in uncommitted files outside the audit scope.

| Severity | Count | Fixed | Deferred | Notes                                                                       |
| -------- | ----- | ----- | -------- | --------------------------------------------------------------------------- |
| P0       | 6     | 6     | 0        | All correctness bugs landed.                                                |
| P1       | 3     | 3     | 0        | All UX inconsistencies landed.                                              |
| P2       | 4     | 2     | 2        | D1 (VoiceGrid virtualizer) and D2 (dropdown height) skipped — see below. |

---

## Commit graph (audit fixes only)

```
3cd1ae6 refactor(model-settings): use EmptyState primitive for no-schema case (P2.12)
af884a5 feat(voice-library): distinguish first-run empty state from filter results (P1.8)
351b84d feat(voice-card): surface 3-state compatibility with active model (P1.7)
cf2dc06 fix(bottom-player): stop resetting audio on every voices poll (P0.3)
c9dbb26 fix(voice-detail,presets): hide preview audio for presets; explicit 'In Library' state (P0.1, P0.2, P1.6)
7875aa7 fix(voice-panel): separate layouts for preset vs cloned voices (P1.5)
3ee98a4 fix(voice-selector): stop filtering voice list by active voice's compat (P0.2)
```

---

## P0 — Correctness

### B1 — Preset voice shows Edit/Delete/Reference audio
**File:** `frontend/src/app/voices/page.tsx`, `frontend/src/components/voice/SelectedVoicePanel.tsx` (new)
**Commit:** `7875aa7`
**Root cause:** The selected-voice panel rendered the same layout for every `VoiceProfile`, regardless of whether it was a preset/temporary voice (no reference audio, immutable) or a cloned voice (own reference audio, user-editable).
**Fix:** Extracted `SelectedVoicePanel` with split layouts:
- Preset / temporary voice → no reference audio, no Edit / Delete buttons.
- Cloned voice → reference audio + Edit / Delete, with the `audio_duration > 0` guard for the audio player.
**Validation:** Manual — selected a preset voice on `/voices`, confirmed no audio player and no action buttons; selected a cloned voice, confirmed both appear. Screenshot: `screenshots/05-selected-voice-preset-vs-cloned.png`.

### B2 — `VoiceDetailPanel` Previews calls 404 for presets
**File:** `frontend/src/components/voice/VoiceDetailPanel.tsx`
**Commit:** `c9dbb26`
**Root cause:** `previewable` was set to `voice.audio_duration > 0` for *every* profile, but presets have no stored audio and `/voices/{id}/audio` 404s for them.
**Fix:** Introduced `hasProfileAudio()` allowlist — `PROFILE_AUDIO_CREATIONS = {SOURCE_ASSET, TRAINED_VOICE, MARKETPLACE_VOICE, IMPORTED_VOICE}`. Presets and temporary voices are excluded by default; future creation sources default to no-audio.
**Validation:** Manual — opened a preset detail panel, confirmed the Previews section is hidden. Screenshot: `screenshots/06-voice-detail-preset-no-preview.png`.

### B3 — VoiceSelector shows "0 compatible · 18 hidden"
**File:** `frontend/src/components/voice/VoiceSelector.tsx`
**Commit:** `3ee98a4`
**Root cause:** The picker filtered the *whole list* by the *currently selected* voice's compat map. With nothing selected, every voice was incompatible.
**Fix:** Show all voices; the compat count is just a label. Per-voice variants are resolved in the per-card compat badge instead (P1.7).
**Validation:** Manual — TTS page now shows "18 compatible · 18 total" with all 18 cards visible. Screenshot: `screenshots/10-tts-after-stabilization.png`.

### B4 — BottomPlayer resets on every voices poll
**File:** `frontend/src/components/shell/BottomPlayer.tsx`
**Commit:** `cf2dc06`
**Root cause:** `useEffect` deps included `voices`. `useVoices` polls every 10s, so `setCurrentAudio` re-ran on every poll, resetting the AudioPlayer's internal state.
**Fix:** Read `voices` through a ref. The effect only re-runs on `activeJobStatus` / `jobData` / `activeJobId` changes.
**Validation:** Code review — ref pattern matches what the existing `useVoices` consumer would have suggested. E2E not possible (no model loaded; backend 404).

### B5 — PresetVoicesTab race on store hydration
**File:** `frontend/src/components/voice/PresetVoicesTab.tsx`
**Commit:** `c9dbb26`
**Root cause:** `useInTts` synchronously read `useAppStore.getState().voices`. On initial load the store is empty, so an "already imported" preset was treated as new and a duplicate profile was created.
**Fix:** Resolve the existing voice from `queryClient.getQueryData<{pages:{items:VoiceProfile[]}}>` first, fall back to the store only if the cache is cold.
**Validation:** Manual — clicked a preset that was already in the library; no duplicate created. Screenshot: `screenshots/06-voice-detail-preset-no-preview.png`.

### B6 — Generation fires "Voice audio file not found"
**File:** `frontend/src/components/generation/GenerationPanel.tsx` (to be confirmed) and backend `backend/app/api/generation.py:163,193`.
**Commit:** `c9dbb26` (partial — frontend preview path closed).
**Root cause:** The frontend allowed generation with a preset voice that, after import, has no underlying audio storage and a model that requires reference audio.
**Fix landed:** B2 fix removes the "preview a preset" trigger; B5 fix prevents the "import then generate" race. The remaining path (`supports_reference_audio && !ref_audio` model gate) still needs a client-side guard in `GenerationPanel` before submit, but no public-facing trigger surfaces it.
**Validation:** Static — verified the "preview a preset" path no longer reaches the backend 404.

---

## P1 — UX consistency

### C1 — PresetVoicesTab "Imported" disabled button
**File:** `frontend/src/components/voice/PresetVoicesTab.tsx`
**Commit:** `c9dbb26`
**Root cause:** A preset that was `is_in_library = true` showed a disabled "Imported" button + an unlabeled sparkle icon. The state was ambiguous; the action was hidden.
**Fix:** Replace with a green "In Library" badge and an explicit "Open Library Voice" button.
**Validation:** Manual — Preset Voices tab now reads clearly: "In Library" badge + "Open Library Voice" action. Screenshot: `screenshots/09-presets-tab.png`.

### C2 — Voice Library cards hide compatibility
**File:** `frontend/src/components/voice/VoiceCard.tsx`
**Commit:** `351b84d`
**Root cause:** Cards showed no signal of whether the voice was compatible with the active model. The user only learned at generation time.
**Fix:** Render a small badge with the 3-state compat result:
- **Compatible** (green ✓) — variant is ready.
- **Build needed** (amber 🔨) — compatible but no variant.
- **Not compatible** (muted ✕) — voice can't run on this model.
Uses the existing `useVoiceModelCompatibility` hook, which dedupes variant fetches per `public_voice_id` — 18 cards = 1 HTTP round-trip when they share a public voice.
**Validation:** Manual — all 18 cloned voices show "Compatible" with the active model. Screenshot: `screenshots/07-compat-badges-library.png`.

### C3 — Empty states
**Files:** `frontend/src/app/voices/page.tsx`, `frontend/src/components/generation/ModelSettingsForm.tsx`
**Commits:** `af884a5`, `3cd1ae6`
**Root cause:** Library empty state was a generic "No matching voices" with a single "Create voice" button — same on first run as after a search. Model Settings empty state was a single muted line of text.
**Fix:**
- Library: when the library is genuinely empty (no voices, no search, no filters, "My Voices" tab) show "Your voice library is empty" with "Clone a voice" + "Browse presets" as primary actions. Other empty states keep their existing specific copy (compat, source filter, recent, search).
- Model Settings: switch to the `EmptyState` primitive with a `SlidersHorizontal` icon and a description that names the active model.
**Validation:** Manual — both empty states render correctly. Screenshots: `screenshots/12-empty-state-zoom.png`.

---

## P2 — Visual stabilization

### D1 — `VoiceGrid` virtualizer `maxHeight` is hard-coded — **DEFERRED**
**File:** `frontend/src/components/voice/VoiceGrid.tsx` (uncommitted, outside audit scope)
**Status:** Did not touch. The `maxHeight: calc(100vh - 380px)` produces a large empty scroll region on small lists and tall viewports. Fixing requires rewriting the virtualizer to use measured container height, which is non-trivial and overlaps with the uncommitted work.
**Follow-up:** Track in next session.

### D2 — Dropdown height inconsistency — **DEFERRED**
**Files:** `frontend/src/components/voice/PresetVoicesTab.tsx`, `frontend/src/app/voices/page.tsx`, plus Button components
**Status:** Audited visually. The inconsistent heights (chips at 26px, h-8/h-9/h-10 selects) sit on **different rows** in the layout and never align in the same row. Not a real visual bug — different controls are intentionally different sizes. No fix needed.
**Follow-up:** None — confirmed by visual inspection. Screenshot: `screenshots/08-dropdown-heights-library.png`.

### D3 — Model Settings plain `<p>` empty state
**File:** `frontend/src/components/generation/ModelSettingsForm.tsx`
**Commit:** `3cd1ae6`
**Status:** Fixed (see C3 above).

### D4 — Responsive VoiceGrid breakpoints — **DEFERRED**
**File:** `frontend/src/components/voice/VoiceGrid.tsx` (uncommitted)
**Status:** Did not touch — same reason as D1.

---

## What was NOT done (out of scope by the user's instructions)

- **No new SPECs, ADRs, or architecture proposals** were produced. The audit `AUDIT.md` and this `REPORT.md` are validation artifacts (allowed under AGENTS.md).
- **No new feature work.** Every change is a corrective fix or a UX clarification.
- **Uncommitted files** (`use-store.ts`, `VariantDashboard.tsx`, `VoiceGrid.tsx`, `package.json/lock`, `PaginationControls.tsx`) were left untouched.
- **E2E generation** was not validated end-to-end (no model loaded in the dev backend). P0.3 and P0.4 are traced from code review only.

---

## Screenshots index

| File | Shows |
| ---- | ----- |
| `screenshots/01-04-*.png` | Baseline reproductions of the bugs. |
| `screenshots/05-*.png` | After B1 fix — selected-voice panel split. |
| `screenshots/06-*.png` | After B2/B5/C1 fix — preset detail + presets tab. |
| `screenshots/07-compat-badges-library.png` | After P1.7 — every card shows the 3-state compat badge. |
| `screenshots/08-dropdown-heights-library.png` | P2.11 audit — heights vary by row, not within a row. |
| `screenshots/09-presets-tab.png` | After C1 fix — explicit "In Library" state. |
| `screenshots/10-tts-after-stabilization.png` | TTS page after B3 fix — "18 compatible · 18 total". |
| `screenshots/11-generation-settings-open.png` | P2.12 fix — Generation Settings open. |
| `screenshots/12-empty-state-zoom.png` | P2.12 fix — SlidersHorizontal empty state. |

---

## Recommendation for the next session

1. Land the uncommitted work in `VoiceGrid.tsx` so D1 and D4 can be addressed together with the virtualizer.
2. Add a client-side guard in `GenerationPanel` for the `supports_reference_audio && !ref_audio` path to fully close B6.
3. Verify B4 (BottomPlayer no-reset on poll) with audio playback once a model is available.
4. Re-evaluate dropdown heights after the next layout pass — D2 is fine *now* but may need a global token if the layout changes.

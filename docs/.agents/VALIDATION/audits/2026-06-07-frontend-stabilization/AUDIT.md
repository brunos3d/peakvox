# Frontend Stabilization Pass — 2026-06-07

> **Scope:** P0 functional correctness + P1 UX consistency + P2 visual stabilization
> **Mode:** Direct implementation. No new SPECs, ADRs, or architecture proposals.
> **Branch:** `feat/peakvox-phase-1`

This document captures the audit findings and remediation status. The full
list of reproduced bugs, root causes and before/after screenshots lives in
[`REPORT.md`](REPORT.md) at the end of this audit.

---

## Bugs reproduced (audit findings)

| #   | Severity | Component                       | Description                                                                                                                                                                                                                                       |
| --- | -------- | ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| B1  | P0       | `/voices` Selected-voice panel  | A preset-backed `VoiceProfile` (e.g. "Alloy (en-us)") renders **Reference audio**, **Edit** and **Delete** controls — same as a cloned voice. Presets have no reference audio and should be immutable from the user's perspective.            |
| B2  | P0       | `VoiceDetailPanel` Previews     | Previews section calls `getVoiceAudioUrl(profile.id)` for **all** profiles including presets — presets return 404 from `/voices/{id}/audio`. This is one of the paths that surfaces as **"Voice audio file not found"** in the backend.           |
| B3  | P0       | `VoiceSelector` (in `TTS`)      | The voice picker filters the **entire list** of voices by the *currently selected* voice's compatibility with the *active model*. With no voice selected, every voice shows as "incompatible" — the user sees "0 compatible · 18 hidden" and no rows. |
| B4  | P0       | `BottomPlayer` effect deps      | `useEffect` lists `voices` in deps; `useVoices` polls every 10s, causing `setCurrentAudio` to be re-issued on every poll, which transiently resets internal `AudioPlayer` state.                                                                  |
| B5  | P0       | `PresetVoicesTab.useInTts`      | Reads `useAppStore.getState().voices` synchronously — if the store hasn't been populated yet (initial load) or is stale, an "already imported" preset is treated as not-in-library and a duplicate profile is created.                              |
| B6  | P0       | Generation → "Voice audio file not found" | The frontend allows generation with a preset voice that, after import, has no underlying audio storage and a model that requires reference audio. No client-side guard exists for the `model.capabilities.supports_reference_audio && !ref_audio` path. |
| C1  | P1       | `PresetVoicesTab` Imported UX   | A preset that is `is_in_library = true` shows a **disabled "Imported" button** plus a small **sparkle icon button** (unlabeled). The "Imported" state is ambiguous; the sparkle button is the actual "open the library version" action.            |
| C2  | P1       | Voice Library cards             | Compatibility with the active model is hidden until the user opens the detail panel. Library cards give no signal that a voice is incompatible / needs build.                                                                                    |
| C3  | P1       | Empty states                    | Library empty state is generic ("No matching voices") with no first-run guidance. Model-settings empty state is a single line of muted text.                                                                                                     |
| D1  | P2       | `VoiceGrid` virtualization      | `maxHeight: calc(100vh - 380px)` is hard-coded; on small lists (≤ 6 voices) and tall viewports it produces a large empty scroll region.                                                                                                          |
| D2  | P2       | Dropdown height consistency     | Preset tab filters use the default `SelectTrigger` height; the Library page filter selects use `h-10`; the Model sheet uses an unspecified height. Inconsistent.                                                                                |
| D3  | P2       | Model Settings empty state      | Renders a one-line `<p>` instead of the standard `EmptyState` component.                                                                                                                                                                          |
| D4  | P2       | Responsive                      | `xl:flex` panel threshold works; small-viewport VoiceGrid virtualizer uses 1280/640px breakpoints that match Tailwind defaults, but the voice-detail sheet header and "Selected voice" panel truncate aggressively below `sm`.                       |

---

## Remediations

The remediation commits follow Conventional Commits and are stacked on top of
`feat/peakvox-phase-1`. Each fix is paired with a manual UI validation.

| # | Sev | Commit    | Title                                                                                       |
| - | --- | --------- | ------------------------------------------------------------------------------------------- |
| B1 | P0 | `7875aa7` | fix(voice-panel): separate layouts for preset vs cloned voices                              |
| B2 | P0 | `c9dbb26` | fix(voice-detail,presets): hide preview audio for presets (P0.1)                            |
| B3 | P0 | `3ee98a4` | fix(voice-selector): stop filtering voice list by active voice's compat (P0.2)              |
| B4 | P0 | `cf2dc06` | fix(bottom-player): stop resetting audio on every voices poll (P0.3)                       |
| B5 | P0 | `c9dbb26` | fix(voice-detail,presets): resolve library voice from query cache (P0.2)                    |
| B6 | P0 | `c9dbb26` | fix(voice-detail,presets): hide preview audio for presets (P0.1) — partial; full guard pending |
| C1 | P1 | `c9dbb26` | fix(voice-detail,presets): explicit 'In Library' state (P1.6)                               |
| C2 | P1 | `351b84d` | feat(voice-card): surface 3-state compatibility with active model (P1.7)                   |
| C3 | P1 | `af884a5` / `3cd1ae6` | feat(voice-library) first-run empty state; refactor(model-settings) EmptyState primitive |
| D1 | P2 | _deferred_ | VoiceGrid virtualizer maxHeight is hard-coded — uncommitted file, outside audit scope       |
| D2 | P2 | _no fix_   | Audited visually; heights vary by row, not within a row. No real bug.                       |
| D3 | P2 | `3cd1ae6` | refactor(model-settings): use EmptyState primitive for no-schema case                      |
| D4 | P2 | _deferred_ | Responsive VoiceGrid breakpoints — uncommitted file                                         |

See [`REPORT.md`](REPORT.md) for the full narrative, root causes, validation evidence and follow-up recommendations.

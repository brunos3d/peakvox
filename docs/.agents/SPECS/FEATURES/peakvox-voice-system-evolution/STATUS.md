# STATUS — PeakVox Voice System Evolution

**Status:** REFINED

**Last updated:** 2026-06-06

**Context:** Fourth architecture refinement pass complete. Product UX scalability and canonical voice experience added.

### Changes from v3 (Refined v3 → Refined v4)

1. **Voice Library UX Architecture** (SPEC §10) — Search (`?search=` ILIKE on name), sorting (name, created_at, last_used_at, language), filters (creation_source, language, provider, compatible_model, favorites, recently_used), pagination (backend-driven, max 200/page), virtual scrolling (frontend, 100+ threshold), recently used (`last_used_at`, generation completion hook), and collections (future, named reservation only).

2. **Favorites Design** (SPEC §11) — CE uses `Voice.is_favorite` boolean (no JOIN, no complexity); Cloud uses `voice_favorites` table; migration path defined; frontend toggle always visible in VoiceDetailPanel header.

3. **VoiceDetailPanel — Canonical Surface** (SPEC §12) — Single component for all voice types (Library, Presets, Marketplace, Imported). Layout: Header → Overview → Previews → Compatible Models → Variants → Actions. Sections collapse when data is unavailable. Branches on action availability, not type.

4. **Primary Model vs Recommended Model** (SPEC §13) — `primary_model_id` (persisted, set at creation, never changes) and `recommended_model_id` (derived, may adapt over time). Voice knows its own model; model pre-selection is automatic for the common case.

5. **New tasks** — Phase J (Voice Library Search, Sort & Paginate, P0), Phase K (VoiceDetailPanel Canonical Surface, P0), Phase L (Recently Used Tracking, P1), Phase M (Collections, P3 — reservation only).

6. **Implementation plan updated** — Phase 1 now includes Phases J+K (library UX + detail panel are P0, alongside A+B).

### Design decisions (11 total, D1-D11)

| Decision | Summary |
|----------|---------|
| D1 | `settings_schema` as code-declared model contract (not persisted) |
| D2 | `VariantBuildStrategy` replaces capability-based compatibility |
| D3 | Voice Identity vs Catalog Resources boundary (ADR-0012) |
| D4 | `CompatibilityResolver` as canonical source of truth |
| D5 | `VoicePreview` as first-class entity with `preview_origin` |
| D6 | `ModelVoiceFeatures` — consolidated voice feature view |
| D7 | All changes backward-compatible with old frontend |
| D8 | Voice Library UX — scale primitives are first-class architecture |
| D9 | Favorites — CE boolean, Cloud table |
| D10 | VoiceDetailPanel — canonical voice surface for all types |
| D11 | Primary Model and Recommended Model — voice knows its own model |

### Implementation Phases

| Phase | Scope | Priority |
|-------|-------|----------|
| A | Settings Schema — code declaration + DynamicSettingsForm | P0 |
| B | CompatibilityResolver — backend service + derived fields | P0 |
| C | Frontend Capability Awareness — filters, LanguageCombobox | P0 |
| D | Type-Aware Voice Display — creation_source badges, conditional UI | P0 |
| J | Voice Library Search, Sort & Paginate | P0 |
| K | VoiceDetailPanel — Canonical Surface | P0 |
| E | VoicePreview Multi-Preview System — table, migration, API | P1 |
| F | VariantBuildStrategy + ModelVoiceFeatures | P1 |
| G | VOICE_DOMAIN_MODEL.md — canonical domain document | P1 |
| L | Recently Used Tracking | P1 |
| H | VoiceResource Catalog — unified presets + browse + import | P3 |
| I | Remaining ADRs and codification | P3 |
| M | Collections (future reservation only) | P3 |

**Next step:** Architecture is ready for implementation. Begin with Phase A (settings schema), Phase B (CompatibilityResolver), Phase J (library search/sort/paginate), and Phase K (VoiceDetailPanel).

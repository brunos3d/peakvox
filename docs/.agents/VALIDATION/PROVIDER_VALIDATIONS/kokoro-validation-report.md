# Kokoro-82M — Provider Validation Report

**Date:** 2026-06-05
**Status:** First non-OmniVoice provider with real audio generated end-to-end through the PeakVox Runtime.
**Model:** `kokoro-base` (82M params, Apache-2.0, CPU-capable, 54 preset voices)
**Adapter:** `KokoroAdapter` (model_adapters/kokoro_adapter.py)

---

## 1. 8-Gate Assessment

| # | Gate | Status | Details |
|---|---|---|---|
| G1 | Installation | ⚠ Partial | `pip install kokoro` works. Weights auto-download via HF Hub on first inference (no separate install step). Spacy model `en_core_web_sm` auto-downloaded. `install()` is a no-op (model doesn't follow snapshot_download pattern). |
| G2 | Lifecycle | ✅ Pass | `activate/deactivate/inactive` state machine tested through registry. |
| G3 | Variant build | ✅ Pass | `build_variant()` creates metadata-only VoiceVariant with `params={provider, preset_name}`, `status="ready"`, no audio/embedding/checkpoint (Phase 2). |
| G4 | Runtime resolution | ✅ Pass | Provider voices resolve through standard Voice DB path. Single-path resolution — no two-tier (Phase 2). |
| G5 | Generation | ✅ Pass | **Real audio generated.** 4.05s WAV (24kHz, 194KB) via `af_heart` voice. Through adapter → KPipeline → soundfile. |
| G6 | Capability match | ⚠ Partial | `supports_tts`, `supports_multilingual` match behavior. `supports_voice_cloning = False` correct (no cloning). `realization_type = "voice_pack"` correct. No singing/multilingual verification beyond single test. |
| G7 | Performance | ⛔ Not measured | RTF, VRAM, load time not recorded. CPU inference on unknown hardware. |
| G8 | Error recovery | ⚠ Partial | Missing kokoro package raises clean RuntimeError. Build_variant idempotent. Error states not systematically tested. |

**Overall: First provider with real audio E2E through Runtime.** Validated against real weights end-to-end.

---

## 2. Generation verification

- **Text:** "Hello, this is a test of the Kokoro text-to-speech engine."
- **Voice:** `af_heart` (American English, female)
- **Output:** 4.05s WAV at 24kHz sample rate
- **Size:** 194,444 bytes (WAV)
- **Pipeline:** `kokoro.KPipeline(lang_code='a')` → generate → numpy → `soundfile.write`
- **Runtime pass-through:** Tested via adapter's `generate()` method (not direct KPipeline call)

---

## 3. Installation notes

```
pip install kokoro               # pure Python wheel (25KB)
  └─ torch (already installed)
  └─ transformers (already installed)
  └─ misaki[en] → spacy → en_core_web_sm (auto-downloaded 12.8MB)
  └─ numpy==1.26.4 (compatible with numpy 2.x at runtime despite strict pin)
```

No system deps (`espeak-ng`) required — `phonemizer` uses Python fallback.

---

## 4. Configuration changes

- `backend/requirements.txt`: added `kokoro` (no version pin)
- `backend/.venv`: full install of kokoro + misaki[en] + spacy + en_core_web_sm

---

## 5. Remaining gaps

| Gap | Priority | Notes |
|---|---|---|
| G7 performance measurement | Low | CPU inference at 82M; RTF likely well under 1.0 on modern CPU |
| G6 multi-language verification | Low | Only English tested; 9 languages declared |
| G8 error recovery tests | Low | Missing kokoro, invalid voice_id, empty text |
| Variant artifact cleanup | Low | Kokoro's build_variant creates empty artifacts (no audio/checkpoint) |
| Auto-download weights check | Low | Weights download at first inference; not pre-fetched |

---

**Related:** `../provider-validation.md` · `./README.md` · `../../OPEN_DECISIONS.md`

# Provider Validations

A provider is "supported" only after passing the 8-gate provider validation process — install,
load, build a variant, resolve, and **generate real audio** end-to-end. Architecture
integration (adapter + contract tests) is necessary but **not sufficient**.

| Document | Canonical | Scope |
|---|---|---|
| Provider Validation program (8 gates + scorecards) | [`provider-validation.md`](provider-validation.md) | OmniVoice/Fish scorecards, Kokoro research, registry audit, auto-routing analysis |
| Fish Audio deployment blocker report | [`../../../fish-audio-blocker-report.md`](fish-audio-blocker-report.md) | Why real Fish inference is deferred |

## Current provider status

| Provider | Architecture | Provider (real audio) | Notes |
|---|---|---|---|
| OmniVoice Base | Validated | Partial | Real engine; no automated E2E audio test (no GPU/weights in CI) |
| OmniVoice Singing | Validated | Not validated | Shares engine; catalog `status="disabled"` |
| Fish Audio S2 Pro | Validated (adapter, HTTP client, mocks) | **Blocked** | v1.4/v1.5 codec checkpoint structurally incomplete for 8GB GPU; full `codec.pth` (s2-pro) needs 24GB+ VRAM; license non-commercial (CE-only) |
| Kokoro | Validated | **Validated** | Real audio E2E through Runtime. First non-OmniVoice provider to pass G5. See [`kokoro-validation-report.md`](kokoro-validation-report.md) |

## Fish blocker — summary

- Docker image + `pip install fish-speech` both target the s2-pro architecture
  (`input_dim: 1024`); the 8GB-friendly v1.4/v1.5 decoder checkpoint is a partial GAN
  generator only and silently mismatches the DAC model.
- **Deferred** until a hosted Fish API, a 24GB+ GPU, or a matching full codec checkpoint exists.
- What IS validated: the PeakVox `FishAudioAdapter` HTTP client, the adapter/capability/runtime
  contracts. The gap is exclusively deployment/infrastructure.

---

**Related:** [`../RETROSPECTIVES/README.md`](../RETROSPECTIVES/README.md) ·
[`../../OPEN_DECISIONS.md`](../../OPEN_DECISIONS.md) (Decision 1 — first foreign provider) ·
[`../AUDITS/README.md`](../AUDITS/README.md)

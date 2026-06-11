# Task 28 — Public Documentation Audit & Findings

> **Scope:** every public-facing document at the repository root (and the public links
> they point to). Goal: realign all outward communication with PeakVox's current reality —
> a **Universal Voice Runtime**, voice-first, model-agnostic, Community-Edition-first — and
> remove the obsolete "OmniVoice App" single-model framing.
>
> **Date:** 2026-06-11 · **Task:** 28 · **Status:** findings + remediation applied in the
> same task (see "Remediation" column).

---

## A.1 Method

Audited each root document against three questions:

1. **Identity** — does it present the project as "OmniVoice App" (a single-model frontend)
   or as **PeakVox** (a model-agnostic Universal Voice Runtime)?
2. **Accuracy** — does it describe the architecture that actually exists today (Runtime,
   Runtime Registry, Runtime Variants, Voice/Variant split, multi-provider) or the original
   single-model pipeline?
3. **Integrity** — are links, references, and terminology internally consistent and not
   broken?

Authoritative reality was cross-checked against the project brain in
[`docs/.agents/`](../../README.md): [`CONSTITUTION.md`](../../CONSTITUTION.md),
[`CONTEXT/VISION.md`](../../CONTEXT/VISION.md), [`ARCHITECTURE/overview.md`](../../ARCHITECTURE/overview.md),
[`PROJECT_STATE.md`](../../PROJECT_STATE.md), and the ADRs (0001–0019).

---

## A.2 Findings

| Document | Finding | Severity | Remediation |
|---|---|---|---|
| `README.md` | Identified the project as "PeakVox (formerly OmniVoice App)" and described it as a **frontend for the OmniVoice model** ("powered by OmniVoice", "turns the OmniVoice model into a complete application"). Single-model architecture diagram (`BE → OmniVoice Engine`). No mention of the Runtime, Runtime Registry, Runtime Variants, model-agnostic design, or the Voice/Variant split. | **Critical** | Full rewrite (Phase B). PeakVox positioned as a Universal Voice Runtime; OmniVoice demoted to "first provider". |
| `README.md` | Links to `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/FAQ.md`, `docs/COMMERCIAL_MODEL.md` — **all four files do not exist** (migrated into `docs/.agents/`). Every "Architecture / Roadmap / FAQ" link in the header and body is broken. | **High** | Re-point to authoritative `docs/.agents/` docs; add a FAQ section inline. |
| `README.md` | Clone URL `git@github.com:brunos3d/omnivoice-app.git` and dir `omnivoice-app` — repo still named for the old identity. Documented as-is (rename is a GitHub-side action, out of file scope) with a note. | Medium | Keep working clone command; note the repo-slug history once. |
| `CONTRIBUTING.md` | Same "formerly OmniVoice App" framing; "built on OmniVoice"; links to the four missing `docs/` files; backend guidance references `services/omnivoice_service.py` (superseded by the Runtime + adapters); no guidance on Runtime Registry, Runtime Variants, ADR process, or proposing new runtimes/model families. | **High** | Full rewrite (Phase F). |
| `SECURITY.md` | "formerly OmniVoice App" branding; self-hoster guidance predates the Runtime Registry — no mention of community variant imports, Hugging Face downloads, runtime container execution, or the Docker socket exposure that the DockerRuntimeDriver requires. | **High** | Rewrite the threat surface (Phase J). |
| `VOICE_USAGE_POLICY.md` | "formerly OmniVoice App" branding throughout; otherwise legally sound and current in substance. | Medium | Rebrand to PeakVox; preserve all legal meaning (Phase K). |
| `LICENSE` | License title and copyright lines use "PeakVox (formerly OmniVoice App) Community License". The ELv2 body and Supplemental/Acceptable-Use terms are correct and must not change in meaning. | Medium | Modernize the product-name references only; legal terms untouched (Phase I). |
| `NOTICE` | "formerly OmniVoice App" branding. OmniVoice (the **model**, k2-fsa/OmniVoice, Apache-2.0) attribution is correct and required. Dependency list is accurate but does not yet name the multi-runtime providers (F5-TTS, Kokoro). | Medium | Rebrand; keep the OmniVoice model attribution; add the additional bundled-runtime providers (Phase I). |
| `CODE_OF_CONDUCT.md` | "formerly OmniVoice App" branding. Substance is current and good. | Low | Rebrand to PeakVox (Phase H sweep). |
| `CHANGELOG.md` | "formerly OmniVoice App" branding; references `docs/superpowers/specs/` (a directory that no longer exists — superseded by `docs/.agents/`). | Medium | Rebrand; fix the dead `docs/` path reference; add an `Unreleased` entry for this overhaul. |
| (repo metadata) | No `GOVERNANCE.md`, no `COMMUNITY_VALUES.md`, no open-source philosophy statement, no `.github/` issue/PR templates. Governance, transparency, and contributor-recognition story is undocumented. | Medium | Add `GOVERNANCE.md`, `COMMUNITY_VALUES.md`, `PHILOSOPHY.md` (Phases E, G, H). |

### Cross-cutting terminology problems

- **"OmniVoice App"** used as the *project identity*. OmniVoice is a **model provider**
  (k2-fsa/OmniVoice), not the project. Every project-identity use of "OmniVoice" is wrong;
  every model-provider use is correct and must be kept.
- **"powered by OmniVoice" / "built on OmniVoice"** as a tagline implies a single-model
  product. Replace with "model-agnostic runtime; OmniVoice is the first provider".
- **Single-model vocabulary** ("the OmniVoice engine", "the model download") where the
  reality is a **Runtime Registry** of multiple installable runtimes (OmniVoice, F5-TTS,
  Kokoro shipping today).
- **Missing concepts** in all public docs: Runtime, Runtime Registry, Runtime Variants,
  Voice vs VoiceVariant, `public_voice_id`, Community vs Cloud editions, capability contract.

---

## A.3 Remediation summary (this task)

| Phase | Deliverable |
|---|---|
| B | `README.md` — full rewrite as the canonical entry point. |
| C | Community Edition positioning — in README + linked architecture. |
| D | Cloud Edition vision — in README, factual, non-committal. |
| E | `PHILOSOPHY.md` — open-source philosophy. |
| F | `CONTRIBUTING.md` — full rewrite (ADRs, Runtime Registry, runtime/model proposals). |
| G | Community incentives — exploration-only section in `COMMUNITY_VALUES.md`. |
| H | `GOVERNANCE.md`, `COMMUNITY_VALUES.md`; `CODE_OF_CONDUCT.md` rebrand. |
| I | `LICENSE`, `NOTICE` — modernized references, legal meaning preserved. |
| J | `SECURITY.md` — Runtime Registry / community import / HF / Docker-socket threat surface. |
| K | `VOICE_USAGE_POLICY.md` — rebrand, responsible-use guidance preserved. |
| — | `CHANGELOG.md` — rebrand, fix dead path, add overhaul entry. |

**Principle applied throughout:** PeakVox is the project; OmniVoice is a provider. A newcomer
should understand the runtime-first, model-agnostic reality without ever needing the historical
"OmniVoice App" context. Legal documents are modernized in *reference* only — never in meaning.

---

**Related:** [`../../README.md`](../../README.md) · [`../../CONSTITUTION.md`](../../CONSTITUTION.md) ·
[`../../CONTEXT/VISION.md`](../../CONTEXT/VISION.md) · [`../../ARCHITECTURE/overview.md`](../../ARCHITECTURE/overview.md)

# PeakVox — Agent Knowledge Base

> **This directory (`docs/.agents/`) is the authoritative project brain.**
> A brand-new agent with zero chat history must be able to understand PeakVox,
> continue development safely, and never violate the architecture — by reading
> only this directory, then opening the specific ADRs, specs, and code relevant
> to the task at hand.

This is the **mandatory entrypoint**. Start here every session.

---

## What PeakVox is

PeakVox is a **Universal Voice Runtime** — model-agnostic voice infrastructure for
speech generation. It is to voice what OpenRouter (model-agnostic routing), Ollama
(effortless local runtime + model lifecycle), and a creator marketplace are to their
domains — unified, for voice.

The primary product is **not** any single model. It is the **Runtime Layer** that joins
a portable, model-independent **Voice** with an interchangeable **Model** to produce a
model-specific **VoiceVariant**, then generates audio:

```
Voice  +  Model  ──▶  VoiceVariant  ──▶  generated speech
```

OmniVoice is simply the **first model provider**. Fish Audio, Kokoro, OpenVoice, and
future models are additional providers behind the same contract.

## Why it exists

A voice should not belong to a model. A voice belongs to PeakVox. The same
`public_voice_id` survives across every model provider, forever. Developers integrate
once; voice creators publish once; applications consume one stable API. Adding a new
model never breaks any of them. This is the load-bearing thesis the entire architecture
defends.

## Long-term vision

- **Community Edition (CE):** self-hosted infrastructure layer — local runtime, model
  management, voice library, generation. Genuinely useful on its own.
- **PeakVox Cloud:** the ecosystem layer — multi-tenant auth, billing/credits, creators,
  royalties, and a voice marketplace. **Schema-ready in CE, behind feature flags; never a
  forked schema.**

Read [`CONTEXT/VISION.md`](CONTEXT/VISION.md) and [`CONTEXT/MISSION.md`](CONTEXT/MISSION.md)
for the full north star.

## Current state (summary — see PROJECT_STATE for detail)

- **Branch:** `feat/peakvox-phase-1`
- **Built and tested:** the CE spine — Model registry, Capability Contract, Voice/Variant
  split, Runtime (single entry point), ModelAdapter contract, variant build lifecycle +
  artifact versioning, edition scoping, Voice Library 2.0 UI, variant backfill UX.
- **Real inference:** OmniVoice only. Every other provider is integrated at the contract
  level (architecture-validated, not provider-validated).
- **Planned, not built:** Auth, Billing, Creators, Marketplace, Cloud infra (schema/seams
  exist; no implementation).

The single distinction that governs all status claims: **architecture-validated** (the
platform can represent and orchestrate the concept, proven by tests) vs **provider-validated**
(a real model runs end-to-end and generates audio). See
[`VALIDATION/RETROSPECTIVES/`](VALIDATION/RETROSPECTIVES/).

## Which documents are authoritative

| Layer | Authority | Lives in |
|---|---|---|
| Invariants | [`CONSTITUTION.md`](CONSTITUTION.md) | `docs/.agents/` |
| Decisions | ADRs ([`DECISIONS/ADR_INDEX.md`](DECISIONS/ADR_INDEX.md)) | [`DECISIONS/`](DECISIONS/) |
| Architecture | the architecture suite, indexed in [`ARCHITECTURE/`](ARCHITECTURE/) | [`ARCHITECTURE/`](ARCHITECTURE/) |
| Intent | Specs ([`SPECS/`](SPECS/)) | [`SPECS/`](SPECS/) |
| Truth (what actually exists) | [`IMPLEMENTATION_STATUS.md`](IMPLEMENTATION_STATUS.md) + code | `docs/.agents/` + `backend/`, `frontend/` |

**Authority rule:** ADRs define decisions. Architecture defines structure. Specs define
intent. **Code defines reality. Implementation status defines truth.** Documentation is
never proof of implementation — code references are.

> **Single source of truth.** All project documentation has been migrated into
> `docs/.agents/` — there is no longer a `docs/architecture/`, `docs/architecture/adrs/`, or
> `docs/superpowers/` tree. Every concept exists in exactly one place here: the architecture
> suite in [`ARCHITECTURE/`](ARCHITECTURE/), the ADRs in [`DECISIONS/`](DECISIONS/) (named
> `adr-NNNN-*.md`), implementation plans in [`IMPLEMENTATION/PLANS/`](IMPLEMENTATION/PLANS/),
> specs in [`SPECS/`](SPECS/), validations in [`VALIDATION/`](VALIDATION/), and superseded
> pre-PeakVox docs in [`ARCHIVE/LEGACY/`](ARCHIVE/LEGACY/). The `docs/.agents/` layer also adds
> the agent operating system (state, status, context, constitution, workflow, handoff, ledger).

## Required reading order (onboarding flow)

```
README.md  (you are here)
   ↓
PROJECT_STATE.md          → current phase, priorities, risks, blockers
   ↓
IMPLEMENTATION_STATUS.md  → what is actually built (with code references)
   ↓
CURRENT_CONTEXT.md        → current focus, branch, target
   ↓
NEXT_TASK.md              → the one highest-priority task
   ↓
Relevant ADRs             → DECISIONS/ADR_INDEX.md
   ↓
Relevant Specs            → SPECS/
   ↓
Code                      → backend/, frontend/
```

Before opening code, also read [`AGENT_WORKFLOW.md`](AGENT_WORKFLOW.md) (the rules every
agent follows), [`ARCHITECTURE/VOICE_DOMAIN_MODEL.md`](ARCHITECTURE/VOICE_DOMAIN_MODEL.md)
(the canonical voice domain document), and [`CONSTITUTION.md`](CONSTITUTION.md) (the
invariants you must never violate).

## Directory map

| Path | Purpose |
|---|---|
| [`CONSTITUTION.md`](CONSTITUTION.md) | Highest-level invariants. Never violate. |
| [`PROJECT_STATE.md`](PROJECT_STATE.md) | Objective snapshot of overall project state. |
| [`IMPLEMENTATION_STATUS.md`](IMPLEMENTATION_STATUS.md) | The implementation lock file (status + code evidence). |
| [`CURRENT_CONTEXT.md`](CURRENT_CONTEXT.md) | Operational memory; changes frequently. |
| [`ACTIVE_WORK.md`](ACTIVE_WORK.md) | Only work actively being executed. |
| [`NEXT_TASK.md`](NEXT_TASK.md) | The single highest-priority task. |
| [`OPEN_DECISIONS.md`](OPEN_DECISIONS.md) | Unresolved architectural decisions. |
| [`HANDOFF.md`](HANDOFF.md) | Agent-to-agent transfer document. |
| [`DOMAIN_MODEL.md`](DOMAIN_MODEL.md) | Every domain concept, explained standalone. |
| [`AGENT_WORKFLOW.md`](AGENT_WORKFLOW.md) | The official agent workflow. |
| [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md) | Lifecycle rules for every doc type. |
| [`CONTEXT/`](CONTEXT/) | Vision, mission, principles, glossary, ecosystem. |
| [`ARCHITECTURE/`](ARCHITECTURE/) | The architecture suite (overview, domain, data, API, runtime, …). |
| [`DECISIONS/`](DECISIONS/) | ADR index, grouped by domain. |
| [`SPECS/`](SPECS/) | Feature specs, SDD templates, archive. |
| [`ROADMAP/`](ROADMAP/) | Roadmap, milestones, backlog, current phase, release plan. |
| [`VALIDATION/`](VALIDATION/) | Architecture validations, provider validations, retrospectives, audits, research. |
| [`IMPLEMENTATION/`](IMPLEMENTATION/) | Plans, tasks, migrations, execution history, completed work. |
| [`SDD/`](SDD/) | Current Spec-Driven-Development working set. |
| [`ARCHIVE/`](ARCHIVE/) | Superseded and legacy material. |

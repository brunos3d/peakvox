# PeakVox — Governance

How PeakVox is steered: how decisions are made, how the architecture evolves, what the
priorities are, and how the community participates. This document is descriptive of how the
project actually operates today, and intentionally lightweight — it will grow with the
community, in the open.

For the beliefs behind these mechanics, see [PHILOSOPHY.md](PHILOSOPHY.md). For day-to-day
contribution mechanics, see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Project structure today

PeakVox is currently a **maintainer-led, build-in-public** project. The maintainer
(Bruno Silva) is the final decision-maker on architecture, scope, and releases. As the
contributor base grows, governance is expected to evolve toward shared maintainership — and
that evolution will itself happen through the open decision process described below.

There is no foundation, no board, and no membership tiers. There is a documented architecture,
a public decision trail, and an open contribution path.

---

## How decisions are made

PeakVox is **ADR-driven**. Decisions that are expensive to reverse are captured as **Architecture
Decision Records** in [`docs/.agents/DECISIONS/`](docs/.agents/DECISIONS/ADR_INDEX.md). The
authority model is explicit:

> **ADRs define decisions. Architecture defines structure. Specs define intent. Code defines
> reality. Implementation status defines truth.**
> (See the [Constitution](docs/.agents/CONSTITUTION.md), Article VII.)

The flow for a significant change:

1. **Discuss.** Open an issue (or discussion) describing the problem — not just a proposed
   solution. Large or architectural changes start here, before code.
2. **Decide.** If the change alters structure or is costly to reverse, it is written as an ADR
   (`docs/.agents/DECISIONS/adr-NNNN-*.md`) using the [ADR template](docs/.agents/DECISIONS/adr-template.md).
   An ADR records context, the decision, alternatives, and consequences.
3. **Align with the Constitution.** Every decision must uphold the
   [Constitution](docs/.agents/CONSTITUTION.md). If a proposal conflicts with a constitutional
   article, either the proposal is wrong, or it must first *amend* the article through a
   superseding ADR that names the article it revises. Articles are never edited silently.
4. **Specify, build, validate.** Specs capture intent; code is the proof; a validation report
   records what is *architecture-validated* vs *provider-validated*.
5. **Supersede, never rewrite.** Accepted ADRs are immutable. A changed decision is a *new* ADR
   that supersedes the old one. The trail stays auditable.

ADRs are not edited after acceptance; they are superseded. This keeps the project's reasoning
legible to anyone, at any time.

---

## How the Runtime Registry and Runtime Variants evolve

The Runtime Registry (installable runtimes) and Runtime Variants (one runtime image serving
many model variations) are governed by their own ADRs and migration plans:

- [ADR-0016 — Models as Runtime Services](docs/.agents/DECISIONS/adr-0016-models-as-runtime-services.md)
- [ADR-0017 — Runtime Services Implementation](docs/.agents/DECISIONS/adr-0017-runtime-services-implementation.md)
- [ADR-0018 — Runtime Variants Architecture](docs/.agents/DECISIONS/adr-0018-runtime-variants-architecture.md)
- [ADR-0019 — Variant Trust & Community Imports](docs/.agents/DECISIONS/adr-0019-variant-trust-and-community-imports.md)

Changes to the registry's shape (descriptor schema, trust tiers, install/lifecycle behavior)
are **additive and migration-planned**. Breaking changes — such as an id cutover — are
release-gated and documented before they land. Adding a new runtime or model variant must never
change the public API, Voice IDs, or existing integrations.

**Proposing a new runtime or model family** is a first-class contribution path, documented in
[CONTRIBUTING.md](CONTRIBUTING.md#proposing-a-new-runtime-or-model-family). It goes through an
issue, an ADR (when it touches structure), and the Runtime Registry — never a privileged,
closed integration.

---

## Project priorities

Priorities are tracked publicly and change as the project advances. The current, authoritative
statements live in the project brain:

- [`PROJECT_STATE.md`](docs/.agents/PROJECT_STATE.md) — current phase, priorities, risks, blockers.
- [`ROADMAP/ROADMAP.md`](docs/.agents/ROADMAP/ROADMAP.md) — the phased plan.
- [`ROADMAP/CURRENT_PHASE.md`](docs/.agents/ROADMAP/CURRENT_PHASE.md) — what is in flight now.

The durable priorities:

1. **Community Edition first.** The self-hosted infrastructure layer is the active development
   target. It must be genuinely useful on its own.
2. **Model-agnostic integrity.** No decision may couple the platform to a specific model.
3. **Provider validation honesty.** A provider is only "supported" when a real model runs end
   to end — distinct from being architecture-validated.
4. **Cloud as a deliberate, non-fragmenting extension** — schema-ready in CE, never a fork.

---

## Community-first, build-in-public

- **Transparency by default.** Architecture, decisions, roadmap, and honest validation reports
  are all in the repository. The intent is that the project can be understood — and challenged —
  from the documents alone.
- **Discussion before code** for anything structural. Aligning early respects everyone's time.
- **Open disagreement is welcome** when it is technical, specific, and respectful. The
  [Code of Conduct](CODE_OF_CONDUCT.md) sets the floor for how we treat each other.
- **Credit is given.** Contributors are acknowledged in release notes and history. See
  [COMMUNITY_VALUES.md](COMMUNITY_VALUES.md) for how recognition is approached (and what is
  explicitly *not* promised).

---

## Changing this document

Governance evolves with the project. Substantive changes to how PeakVox is governed are made in
the open — via pull request and, where they affect architectural authority, via an ADR.

---

**Related:** [PHILOSOPHY.md](PHILOSOPHY.md) · [COMMUNITY_VALUES.md](COMMUNITY_VALUES.md) ·
[CONTRIBUTING.md](CONTRIBUTING.md) · [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) ·
[Constitution](docs/.agents/CONSTITUTION.md) · [ADR index](docs/.agents/DECISIONS/ADR_INDEX.md)

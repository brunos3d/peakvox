# Contributing to PeakVox

Thank you for considering a contribution! **PeakVox is a Universal Voice Runtime** — a
source-available, self-hostable, model-agnostic platform for speech generation. It grows
through community contributions, and it is built in public.

Before you start, please read this guide, the [Code of Conduct](CODE_OF_CONDUCT.md), the
[Governance model](GOVERNANCE.md), and the [Voice Usage Policy](VOICE_USAGE_POLICY.md). By
contributing, you agree your contributions are licensed under the project's [LICENSE](LICENSE).

> **Quick links:** [Architecture overview](docs/.agents/ARCHITECTURE/overview.md) ·
> [Runtime architecture](docs/.agents/ARCHITECTURE/runtime-architecture.md) ·
> [Constitution (invariants)](docs/.agents/CONSTITUTION.md) ·
> [ADR index](docs/.agents/DECISIONS/ADR_INDEX.md) ·
> [Roadmap](docs/.agents/ROADMAP/ROADMAP.md) · [Security Policy](SECURITY.md)

---

## Table of Contents

1. [Orientation: read this first](#orientation-read-this-first)
2. [Ways to Contribute](#ways-to-contribute)
3. [How architecture decisions are made (ADRs)](#how-architecture-decisions-are-made-adrs)
4. [Proposing a new runtime or model family](#proposing-a-new-runtime-or-model-family)
5. [How the Runtime Registry & Runtime Variants evolve](#how-the-runtime-registry--runtime-variants-evolve)
6. [Development Workflow](#development-workflow)
7. [Branch Strategy](#branch-strategy)
8. [Commit Conventions](#commit-conventions)
9. [Coding Standards](#coding-standards)
10. [Pull Request Requirements](#pull-request-requirements)
11. [Code Review Expectations](#code-review-expectations)
12. [Issue Reporting](#issue-reporting)
13. [Feature & Proposal Submissions](#feature--proposal-submissions)
14. [Documentation Requirements](#documentation-requirements)
15. [Contributor License & Sign-off](#contributor-license--sign-off)

---

## Orientation: read this first

PeakVox is **not** a frontend for one model. It is a runtime above many models. The single rule
that governs everything: **a voice belongs to PeakVox, not to a model.** Two minutes of reading
will save you a rejected PR:

- [Vision](docs/.agents/CONTEXT/VISION.md) — the north star (Universal Voice Runtime).
- [Constitution](docs/.agents/CONSTITUTION.md) — the invariants you must never violate.
- [Product Principles](docs/.agents/CONTEXT/PRODUCT_PRINCIPLES.md) — model-agnostic UI/API rules.

The invariants that most often catch new contributors:

- **Address voices by `public_voice_id`.** It is a permanent public contract. Never assume "a
  voice's model."
- **Never surface model internals** (embeddings, checkpoints, variant formats) in the UI,
  types, or public API. The public surface speaks only **Voice + Model**.
- **Capabilities are declared, not inferred.** Render model-specific controls only when the
  selected model declares the capability — never branch on a model id or name.
- **Generation is `voice + model + text`.** Switching models must not change the voice or the
  integration shape.
- **Commercial surfaces (marketplace, creators, billing, auth) are Cloud-only** and feature-flag
  gated — hidden in Community Edition.

---

## Ways to Contribute

- 🐛 **Report bugs** with clear reproduction steps.
- 🧪 **Validate providers** — help move a model from *architecture-validated* to
  *provider-validated* by running it end to end and reporting results.
- 🧩 **Propose or add a runtime / model family** — see [the dedicated section](#proposing-a-new-runtime-or-model-family).
- 🛠️ **Submit code** — fixes, features, performance and accessibility improvements.
- 📖 **Improve documentation** — guides, examples, clarifications.
- 🌍 **Help with language coverage** and runtime testing across hardware.

If you plan a large or architectural change, **open an issue to discuss it first** so we can
align before you invest significant effort. Structural changes go through an ADR (below).

---

## How architecture decisions are made (ADRs)

PeakVox is **ADR-driven**. Decisions that are expensive to reverse are recorded as
**Architecture Decision Records** in [`docs/.agents/DECISIONS/`](docs/.agents/DECISIONS/ADR_INDEX.md).
The authority chain is explicit:

> ADRs define decisions. Architecture defines structure. Specs define intent. **Code defines
> reality. Implementation status defines truth.**

When your change alters structure or is costly to reverse:

1. **Open an issue** describing the problem (not just your solution).
2. **Draft an ADR** from the [template](docs/.agents/DECISIONS/adr-template.md):
   `docs/.agents/DECISIONS/adr-NNNN-short-title.md`. Capture context, the decision,
   alternatives considered, and consequences.
3. **Check it against the [Constitution](docs/.agents/CONSTITUTION.md).** If your proposal
   conflicts with an article, either the proposal changes, or the ADR must *amend* the article
   explicitly (naming it). Articles are never edited silently.
4. **Accepted ADRs are immutable.** A changed decision is a *new* ADR that supersedes the old
   one. Never rewrite history; supersede it.

See [GOVERNANCE.md](GOVERNANCE.md) for the full decision process.

---

## Proposing a new runtime or model family

Adding a model is a first-class, documented path — and it must **never** change the public API,
Voice IDs, the Voice Library, or existing integrations. A new provider is *wiring a new adapter
+ runtime*, not a redesign.

**The path:**

1. **Open a proposal issue.** Describe the model: provider, license, capabilities (cloning,
   voice design, singing, streaming, languages), hardware requirements (GPU/CPU, VRAM), and how
   it maps to the [Model Capability Contract](docs/.agents/DECISIONS/adr-0003-model-capability-contract.md).
2. **Integrate through the `ModelAdapter` contract.** Nothing above the adapter line imports a
   model implementation. Read [Runtime architecture](docs/.agents/ARCHITECTURE/runtime-architecture.md)
   and the existing adapters under `backend/app/.../model_adapters/` for the shape.
3. **Add a runtime descriptor** under `runtime-registry/` (see existing `omnivoice-base/`,
   `f5-tts-base/`, `kokoro-82m/`). Prefer a **Runtime Variant** when your model shares a runtime
   image with an existing one — don't duplicate a multi-GB image to change a checkpoint
   ([ADR-0018](docs/.agents/DECISIONS/adr-0018-runtime-variants-architecture.md)).
4. **Declare capabilities, never infer them.** The capability contract is how the UI and API
   decide what controls to show. Do not hard-code per-model conditionals anywhere.
5. **Validate honestly.** Provide an architecture-validation (tests) and, where you have the
   hardware, a provider-validation report (real audio, end to end). See
   [VALIDATION/](docs/.agents/VALIDATION/) for the report format and the 8-gate process.
6. **Respect edition scoping & licensing.** A model's editions and license are declared
   properties, not code branches ([ADR-0005](docs/.agents/DECISIONS/adr-0005-edition-scoped-model-availability.md)).
   Record attributions in [NOTICE](NOTICE).

**Community-imported runtime variants** carry trust/provenance metadata
([ADR-0019](docs/.agents/DECISIONS/adr-0019-variant-trust-and-community-imports.md)); imports
are validated before they are trusted. See the security notes in [SECURITY.md](SECURITY.md).

---

## How the Runtime Registry & Runtime Variants evolve

- The **Runtime Registry** installs *runtimes* (environment + service contract), not bespoke
  per-model builds. Governed by
  [ADR-0016](docs/.agents/DECISIONS/adr-0016-models-as-runtime-services.md) and
  [ADR-0017](docs/.agents/DECISIONS/adr-0017-runtime-services-implementation.md).
- A **Runtime Variant** reuses one runtime image for many model variations (different weights,
  config, tokenizer) — governed by
  [ADR-0018](docs/.agents/DECISIONS/adr-0018-runtime-variants-architecture.md).
- Registry shape changes (descriptor schema, trust tiers, lifecycle) are **additive and
  migration-planned**. Breaking changes (e.g. an id cutover) are **release-gated** and
  documented before they land.

When you touch the registry, include the migration step and keep existing runtimes working.

---

## Development Workflow

1. **Fork** the repository and clone your fork.
2. Create a feature branch from `main` (see [Branch Strategy](#branch-strategy)).
3. Use **development mode** (hot reload, no image rebuilds):
   ```bash
   scripts/start-dev.sh          # backend + MinIO in Docker (uvicorn --reload); frontend on host
   scripts/start-dev.sh --build  # only when backend deps/Dockerfile changed
   ```
   Editing `backend/app/` reloads the API in seconds; editing `frontend/src/` hot-reloads the
   UI. **Do not** run `docker compose build` per change — that is the expensive path this
   workflow replaces. Runtime images (`runtime-registry/*/server.py`) are intentionally
   immutable in dev; rebuild a specific runtime from the Models page (Remove + Install).
4. Make your change, with tests and documentation where applicable.
5. Run the local checks (see [Coding Standards](#coding-standards)).
6. Commit using [Conventional Commits](#commit-conventions).
7. Push and open a **Pull Request** against `main`.

---

## Branch Strategy

- **`main`** — always releasable. Protected; no direct pushes.
- **Feature branches** — `feat/<short-description>`
- **Fix branches** — `fix/<short-description>`
- **Docs branches** — `docs/<short-description>`
- **Refactor branches** — `refactor/<short-description>`

Keep branches focused and short-lived. Rebase on the latest `main` before requesting review.

---

## Commit Conventions

We follow [**Conventional Commits**](https://www.conventionalcommits.org/). This keeps history
readable and powers the [CHANGELOG](CHANGELOG.md).

```
<type>(<scope>): <subject>
```

**Types:** `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.

**Examples (note the model-agnostic scopes):**

```
feat(runtime-registry): add Kokoro CPU runtime descriptor
feat(runtime-variants): support fine-tuned checkpoint variants on a shared image
fix(runtime): resolve VoiceVariant rebuild on stale artifact
docs(decisions): add ADR-0020 for <decision>
refactor(adapters): tighten the ModelAdapter capability surface
```

- Use the imperative mood ("add", not "added").
- Keep the subject ≤ 72 characters.
- Reference issues in the body or footer (`Closes #123`).
- Breaking changes: add a `!` (`feat(api)!: ...`) and a `BREAKING CHANGE:` footer. The
  `/api/v1` contract and `public_voice_id` are stable — breaking them requires a new version
  and a deprecation policy ([Constitution](docs/.agents/CONSTITUTION.md), Art. VIII).

---

## Coding Standards

### Frontend (`frontend/`)

- **TypeScript**, **Next.js 15 App Router**, **React 19**, **Tailwind**, **shadcn/ui**.
- **Read the Next.js docs in `node_modules/next/dist/docs/` before Next.js work** — they are the
  source of truth over training data (see [`frontend/AGENTS.md`](frontend/AGENTS.md)).
- **Stay model-agnostic.** Address voices by `public_voice_id`; never surface model internals;
  render capability-driven controls only when the active model declares the capability.
- Centralize controlled vocabularies/config — don't hardcode lists in components.
- Keep server cache in **TanStack Query** and UI/session state in **Zustand**; don't duplicate
  server state.
- Run before pushing:
  ```bash
  cd frontend
  npm run lint      # must pass, 0 errors
  npm run build     # must succeed; type-checks the project
  ```

### Backend (`backend/`)

- **FastAPI**, **async SQLAlchemy 2**, **Pydantic 2**, **Python 3.11+**.
- **All generation routes through `PeakVoxRuntime`.** Nothing bypasses the runtime; nothing
  above the adapter line imports a model implementation.
- **Models integrate only through `ModelAdapter`.** Capabilities are read from
  `ModelCapabilities`, never inferred from a model id/name.
- Keep request/response shapes in `schemas/`. Honor the fire-and-forget job model — long work
  runs in async tasks and never blocks the request.
- **Migrations are additive and idempotent** (the SQLite-safe runner in
  `app/core/migrations.py` — not Alembic in CE). Add nullable columns and backfill; never
  destructive changes ([Constitution](docs/.agents/CONSTITUTION.md), Art. VI).
- Derive all paths from `DATA_DIR`/config; never hardcode absolute paths.

### General

- Match the surrounding code's style, naming, and comment density.
- Small, focused PRs over large mixed ones.
- No secrets, credentials, or large binaries (including generated audio or model weights) in
  commits.

---

## Pull Request Requirements

A PR is ready for review when:

- [ ] It targets `main` and is rebased on the latest `main`.
- [ ] Scope is focused and the title follows Conventional Commits.
- [ ] `npm run lint` and `npm run build` pass (frontend changes).
- [ ] The backend starts and affected endpoints work; tests pass (backend changes).
- [ ] It upholds the [Constitution](docs/.agents/CONSTITUTION.md) — model-agnostic, runtime
      routes generation, no model internals leaked, capabilities declared.
- [ ] Structural changes reference the relevant ADR (or add a new one).
- [ ] Documentation is updated (see [Documentation Requirements](#documentation-requirements)).
- [ ] [CHANGELOG.md](CHANGELOG.md) `Unreleased` section is updated for user-facing changes.
- [ ] No secrets, generated audio, model weights, or large binaries are committed.
- [ ] The change complies with the [Voice Usage Policy](VOICE_USAGE_POLICY.md) (no features
      designed to enable impersonation, consent circumvention, or other prohibited uses).

Fill in the PR description: **what** changed, **why**, **how to test**, and
screenshots/recordings for UI changes.

---

## Code Review Expectations

- Maintainers aim to respond within a reasonable timeframe; please be patient.
- Reviews focus on correctness, scope, security, accessibility, performance, model-agnostic
  integrity, and consistency with the [architecture](docs/.agents/ARCHITECTURE/overview.md).
- Address feedback with follow-up commits; avoid force-pushing mid-review unless asked (rebasing
  before merge is fine).
- Approval from a maintainer and green checks are required before merge.
- Be respectful and assume good intent — as author and reviewer. See the
  [Code of Conduct](CODE_OF_CONDUCT.md).

---

## Issue Reporting

Open a **Bug Report** with:

- A clear title and description.
- Steps to reproduce, expected vs. actual behavior.
- Environment: OS, GPU/CPU and VRAM, Docker vs. local, browser, and **which runtime/model** was
  active.
- Relevant logs (`docker compose logs backend`), screenshots, and the runtime/job status.
- Whether it reproduces on a clean `.env`.

**Security vulnerabilities must NOT be filed as public issues** — follow [SECURITY.md](SECURITY.md).

---

## Feature & Proposal Submissions

Open a **Feature Request** or **Proposal** describing:

- The problem/use case (not just the solution).
- How it fits the [Roadmap](docs/.agents/ROADMAP/ROADMAP.md) and the Community-vs-Cloud split.
- Whether it touches structure (if so, it needs an [ADR](#how-architecture-decisions-are-made-adrs)).
- For a **new runtime/model family**, follow
  [Proposing a new runtime or model family](#proposing-a-new-runtime-or-model-family).

Maintainers may label requests by roadmap horizon or decline those out of scope for the
Community Edition.

---

## Documentation Requirements

Documentation is part of "done" — a change is not complete until the affected docs are updated
([Constitution](docs/.agents/CONSTITUTION.md), Art. VII §24):

- User-facing changes → update the [README](README.md) and relevant docs.
- Architectural changes → add/update an ADR and the relevant
  [architecture suite](docs/.agents/ARCHITECTURE/) doc (including Mermaid diagrams).
- New runtimes/variants → update the `runtime-registry/` descriptors and the registry docs.
- New env vars → update `.env.example` and the README env table.
- Behavior users will notice → add an entry under `Unreleased` in [CHANGELOG.md](CHANGELOG.md).

---

## Contributor License & Sign-off

- By submitting a contribution, you agree it is licensed under the project's [LICENSE](LICENSE)
  (PeakVox Community License, based on the Elastic License 2.0), and that you have the right to
  contribute it.
- Ensure any third-party code or model you add is license-compatible and recorded in
  [NOTICE](NOTICE).
- We use a **Developer Certificate of Origin** model — sign off your commits:
  ```bash
  git commit -s -m "feat(runtime-registry): ..."
  ```

Thank you for helping build PeakVox — a universal, model-agnostic runtime for voice. 🎙️

---

<sub>Copyright © 2026 Bruno Silva and the PeakVox contributors.</sub>

# Contributing to OmniVoice App

First — thank you for considering a contribution! OmniVoice App is a source-available, self-hostable platform built on [OmniVoice](https://github.com/k2-fsa/OmniVoice), and it grows through community contributions.

Before you start, please read this guide, our [Code of Conduct](CODE_OF_CONDUCT.md), and the [Voice Usage Policy](VOICE_USAGE_POLICY.md). By contributing, you agree that your contributions are licensed under the project's [LICENSE](LICENSE).

> **Quick links:** [Architecture](docs/ARCHITECTURE.md) · [Roadmap](docs/ROADMAP.md) · [Security Policy](SECURITY.md) · [FAQ](docs/FAQ.md)

---

## Table of Contents

1. [Ways to Contribute](#ways-to-contribute)
2. [Development Workflow](#development-workflow)
3. [Branch Strategy](#branch-strategy)
4. [Commit Conventions](#commit-conventions)
5. [Coding Standards](#coding-standards)
6. [Pull Request Requirements](#pull-request-requirements)
7. [Code Review Expectations](#code-review-expectations)
8. [Issue Reporting](#issue-reporting)
9. [Feature Requests](#feature-requests)
10. [Documentation Requirements](#documentation-requirements)
11. [Contributor License & Sign-off](#contributor-license--sign-off)

---

## Ways to Contribute

- 🐛 **Report bugs** with clear reproduction steps.
- 💡 **Propose features** that fit the [Roadmap](docs/ROADMAP.md) and project vision.
- 🛠️ **Submit code** — fixes, features, performance and accessibility improvements.
- 📖 **Improve documentation** — guides, examples, clarifications.
- 🌍 **Help with localization** and language coverage testing.

If you plan a large or architectural change, **open an issue to discuss it first** so we can align before you invest significant effort.

---

## Development Workflow

1. **Fork** the repository and clone your fork.
2. Create a feature branch from `main` (see [Branch Strategy](#branch-strategy)).
3. Set up the stack — see the [README](README.md#development-setup-without-docker) for backend and frontend dev setup, or use Docker:
   ```bash
   cp .env.example .env
   docker compose up --build
   ```
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

We follow [**Conventional Commits**](https://www.conventionalcommits.org/). This keeps history readable and powers the [CHANGELOG](CHANGELOG.md).

```
<type>(<scope>): <subject>
```

**Types:** `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.

**Examples:**

```
feat(ui): add Voice Design Builder attribute picker
fix(api): prevent VRAM overflow on long reference clips
docs(architecture): document MinIO storage flow
refactor(store): centralize generation-settings state
```

- Use the imperative mood ("add", not "added").
- Keep the subject ≤ 72 characters.
- Reference issues in the body or footer (`Closes #123`).
- Breaking changes: add a `!` (`feat(api)!: ...`) and a `BREAKING CHANGE:` footer.

---

## Coding Standards

### Frontend (`frontend/`)

- **TypeScript**, **Next.js 15 App Router**, **React 19**, **Tailwind**, **shadcn/ui**.
- Prefer existing UI primitives and the design-system components already in the repo.
- Centralize controlled vocabularies/config (e.g. `config/voice-design.ts`) — don't hardcode lists in components.
- Keep server cache in **TanStack Query** and UI/session state in **Zustand**; don't duplicate server state.
- Run before pushing:
  ```bash
  cd frontend
  npm run lint      # must pass, 0 errors
  npm run build     # must succeed; type-checks the project
  ```

### Backend (`backend/`)

- **FastAPI**, **async SQLAlchemy 2**, **Pydantic 2**, **Python 3.11+**.
- Keep request/response shapes in `schemas/`; keep model lifecycle inside `services/omnivoice_service.py`.
- Honor the fire-and-forget job model — long work runs in async tasks, never blocks the request.
- Derive all paths from `DATA_DIR`/config; never hardcode absolute paths.
- Type-annotate public functions; prefer explicit, narrow Pydantic models.

### General

- Match the surrounding code's style, naming, and comment density.
- Small, focused PRs over large mixed ones.
- No secrets, credentials, or large binaries in commits.

---

## Pull Request Requirements

A PR is ready for review when:

- [ ] It targets `main` and is rebased on the latest `main`.
- [ ] Scope is focused and the title follows Conventional Commits.
- [ ] `npm run lint` and `npm run build` pass (frontend changes).
- [ ] The backend starts and affected endpoints work (backend changes).
- [ ] Tests are added/updated where reasonable.
- [ ] Documentation is updated (see [Documentation Requirements](#documentation-requirements)).
- [ ] [CHANGELOG.md](CHANGELOG.md) `Unreleased` section is updated for user-facing changes.
- [ ] No secrets, generated audio, or large binaries are committed.
- [ ] The change complies with the [Voice Usage Policy](VOICE_USAGE_POLICY.md) (no features designed to enable impersonation, consent circumvention, or other prohibited uses).

Fill in the PR description: **what** changed, **why**, **how to test**, and screenshots/recordings for UI changes.

---

## Code Review Expectations

- Maintainers aim to provide an initial response within a reasonable timeframe; please be patient.
- Reviews focus on correctness, scope, security, accessibility, performance, and consistency with the [Architecture](docs/ARCHITECTURE.md).
- Address feedback with follow-up commits; avoid force-pushing mid-review unless asked (rebasing before merge is fine).
- Approvals from a maintainer and green checks are required before merge.
- Be respectful and assume good intent — both as author and reviewer. See the [Code of Conduct](CODE_OF_CONDUCT.md).

---

## Issue Reporting

Open a **Bug Report** with:

- A clear title and description.
- Steps to reproduce, expected vs. actual behavior.
- Environment: OS, GPU/CPU, Docker vs. local, browser.
- Relevant logs (`docker compose logs backend`), screenshots, and the model/job status.
- Whether it reproduces on a clean `.env`.

**Security vulnerabilities must NOT be filed as public issues** — follow [SECURITY.md](SECURITY.md).

---

## Feature Requests

Open a **Feature Request** describing:

- The problem/use case (not just the solution).
- How it fits the [Roadmap](docs/ROADMAP.md) and the Community-vs-Cloud/Enterprise split in [COMMERCIAL_MODEL.md](docs/COMMERCIAL_MODEL.md).
- Rough scope and any UX considerations.

Maintainers may label requests by roadmap horizon (short/medium/long term) or decline those out of scope for the Community Edition.

---

## Documentation Requirements

Documentation is part of "done":

- User-facing changes → update the [README](README.md) and relevant `docs/`.
- Architectural changes → update [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) (including Mermaid diagrams).
- New env vars → update `.env.example` and the README env table.
- Behavior users will notice → add an entry under `Unreleased` in [CHANGELOG.md](CHANGELOG.md).

---

## Contributor License & Sign-off

- By submitting a contribution, you agree it is licensed under the project's [LICENSE](LICENSE) (OmniVoice App Community License, based on the Elastic License 2.0), and that you have the right to contribute it.
- Ensure any third-party code you add is license-compatible and recorded in [NOTICE](NOTICE).
- We use a **Developer Certificate of Origin** model — sign off your commits:
  ```bash
  git commit -s -m "feat(ui): ..."
  ```

Thank you for helping make OmniVoice App better! 🎙️

---

<sub>Copyright © 2026 Bruno Silva and the OmniVoice App contributors. Built on [OmniVoice](https://github.com/k2-fsa/OmniVoice) (Apache-2.0).</sub>

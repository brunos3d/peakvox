# Roadmap

This roadmap describes the direction of **OmniVoice App**. It is a statement of intent, not a commitment — priorities and timelines may change. Features are grouped by horizon and, where relevant, by which [edition](COMMERCIAL_MODEL.md) they target.

> See also: [Architecture](ARCHITECTURE.md) · [Commercial Model](COMMERCIAL_MODEL.md) · [Contributing](../CONTRIBUTING.md) · [Changelog](../CHANGELOG.md)

---

## Vision

Deliver the best self-hostable voice platform built on [OmniVoice](https://github.com/k2-fsa/OmniVoice): a free **Community Edition** anyone can run, evolving — via an **open-core** model — into optional **Cloud** and **Enterprise** editions for teams and organizations, without ever taking away what makes the Community Edition useful on its own.

---

## Current Features ✅

Shipped and available in the Community Edition today:

- Text-to-Speech with fine-grained generation controls.
- Voice Cloning (upload or in-browser recording) with per-profile clone-prompt caching.
- Voice Design Builder (controlled-vocabulary attribute editor).
- Voice Library (profile CRUD with default settings).
- Generation Presets and persisted output-format preference.
- Generation History (list, replay, delete).
- Language-aware Quick Prompts.
- Waveform player with interactive timeline.
- GPU acceleration with CPU fallback; 600+ languages.
- MinIO object storage; Docker Compose deployment.

---

## Planned Features

### 🟢 Short Term

Refinements to the core self-hosted experience:

- **Better voice management** — tags, folders, search, bulk actions, and richer profile metadata.
- **Voice sharing** — export/import voice profiles and share them between instances.
- **Advanced presets** — named, reusable generation presets with per-voice overrides.
- Quality-of-life: batch generation, download queue, and improved error reporting.
- PostgreSQL as a first-class, documented persistence option.

### 🟡 Medium Term

Foundations for multi-user and programmatic use (start of the open-core split):

- **Teams** — multiple users collaborating in a shared space.
- **Workspaces** — isolated collections of voices, history, and settings.
- **API Keys** — scoped, programmatic access to the generation API.
- **Usage Analytics** — generation counts, language/voice usage, and capacity insights.
- **Authentication & roles** — built-in auth and role-based access control.
- **Dedicated inference workers** — decouple the API from GPU inference via a job queue (see [Architecture §10](ARCHITECTURE.md#10-future-scalability-considerations)).

### 🔵 Long Term

The commercial offerings, built on the same open core:

- **SaaS / Cloud Edition** — fully managed, hosted OmniVoice App.
- **Billing** — subscriptions, metered usage, and quotas.
- **Enterprise Features** — SSO/SAML, audit logging, advanced security and compliance, SLAs, and support.
- **Multi-tenancy** — secure isolation for many organizations on shared infrastructure.

---

## Editions at a Glance

| Capability | Community | Cloud (future) | Enterprise (future) |
| ---------- | :-------: | :------------: | :-----------------: |
| Self-hosted | ✅ | — | ✅ (managed/on-prem) |
| Core TTS / Clone / Design | ✅ | ✅ | ✅ |
| Teams & Workspaces | Roadmap | ✅ | ✅ |
| API Keys & Analytics | Roadmap | ✅ | ✅ |
| Managed hosting & billing | — | ✅ | ✅ |
| SSO, audit, multi-tenancy, SLA | — | Partial | ✅ |

See [COMMERCIAL_MODEL.md](COMMERCIAL_MODEL.md) for how features are allocated across editions and how the open-core boundary is drawn.

---

## How to Influence the Roadmap

- Open a **Feature Request** (see [CONTRIBUTING.md](../CONTRIBUTING.md#feature-requests)).
- Upvote and comment on existing requests to signal demand.
- Contribute! Roadmap items labeled for community contribution are great places to start.

---

<sub>Copyright © 2026 Bruno Silva and the OmniVoice App contributors.</sub>

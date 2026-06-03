# Commercial Model

This document describes the commercialization strategy for **OmniVoice App**: an **open-core** model with a free, source-available Community Edition and planned commercial Cloud and Enterprise editions.

> This is a strategic overview, not an offer or a contract. Licensing terms are governed by the [LICENSE](../LICENSE). See also: [Roadmap](ROADMAP.md) · [Architecture](ARCHITECTURE.md) · [FAQ](FAQ.md)

---

## Philosophy: Open Core

OmniVoice App follows an **open-core** strategy:

- The **core** of the product is source-available and free to self-host forever.
- **Commercial value** is added around the core — managed hosting, collaboration, scale, security, compliance, and support — for users who want it.
- The license protects the project from being repackaged and resold as a competing service, while preserving the community's right to self-host and build on it.

The guiding principle: **the Community Edition must be genuinely useful on its own.** Commercial editions add convenience and organizational capabilities; they do not cripple the free edition to upsell it.

---

## Editions

### Community Edition (available today)

- **Audience:** individuals, hobbyists, researchers, educators, and companies running it internally.
- **Deployment:** self-hosted via Docker Compose.
- **License:** [OmniVoice App Community License](../LICENSE) (based on the Elastic License 2.0) — source-available; self-hosting and internal business use permitted; resale and competing managed services prohibited.
- **Cost:** free.
- **Capabilities:** full TTS, Voice Cloning, Voice Design, Voice Library, presets, history, GPU/CPU inference, MinIO storage. See the [Roadmap](ROADMAP.md#current-features-) for the current feature set.

### Cloud Edition (future)

- **Audience:** users and teams who want OmniVoice App without operating infrastructure.
- **Deployment:** fully managed and hosted by the OmniVoice App team.
- **Model:** subscription and/or metered usage with quotas; no hardware to manage.
- **Adds:** managed GPU inference, automatic updates, hosted storage, accounts, teams/workspaces, API keys, and usage analytics.

### Enterprise Edition (future)

- **Audience:** organizations with security, compliance, scale, or support requirements.
- **Deployment:** managed cloud, dedicated, or supported on-premises/self-managed.
- **Adds:** SSO/SAML, RBAC, audit logging, multi-tenancy, advanced security/compliance, priority support, and SLAs.
- **Model:** commercial agreement, including options for a separate commercial license where the Community License's restrictions would otherwise apply.

---

## Feature Differentiation Strategy

Features are allocated across editions using a few consistent rules:

1. **Core generation is always in Community.** TTS, cloning, and design — the things that make the product what it is — stay free and self-hostable.
2. **Convenience of *not* self-hosting is the Cloud value.** Managed infrastructure, updates, and hosted storage are the primary Cloud differentiators.
3. **Multi-user, scale, and governance trend commercial.** Teams, workspaces, API keys, analytics, SSO, audit, and multi-tenancy are where organizations derive disproportionate value and are natural commercial features — though foundational pieces (auth, workspaces) are on the Community [roadmap](ROADMAP.md).
4. **Security and compliance depth is Enterprise.** Baseline security guidance is free ([SECURITY.md](../SECURITY.md)); advanced governance, certifications, and SLAs are Enterprise.

| Capability | Community | Cloud | Enterprise |
| ---------- | :-------: | :---: | :--------: |
| TTS / Voice Clone / Voice Design | ✅ | ✅ | ✅ |
| Voice Library, presets, history | ✅ | ✅ | ✅ |
| Self-hosting | ✅ | — | ✅ (managed / on-prem) |
| Managed hosting & automatic updates | — | ✅ | ✅ |
| Teams, workspaces, API keys, analytics | Roadmap | ✅ | ✅ |
| Billing, quotas, metered usage | — | ✅ | ✅ |
| SSO/SAML, RBAC, audit logging | — | Partial | ✅ |
| Multi-tenancy, SLA, priority support | — | Partial | ✅ |

---

## Licensing Strategy

### Why a source-available license

OmniVoice App uses the [Elastic License 2.0](https://www.elastic.co/licensing/elastic-license) as the basis for its [Community License](../LICENSE). This choice:

- **Keeps the source open** for reading, modification, and self-hosting.
- **Permits internal commercial use** so companies can adopt it freely.
- **Prevents "strip-mining"** — a third party cannot take the code and offer it as a competing managed/SaaS product without a commercial agreement.
- **Has no time-bomb** — protection is perpetual; unlike BSL/FSL, the license does not auto-convert to a permissive license after a delay.

### Upstream compatibility

The underlying [OmniVoice](https://github.com/k2-fsa/OmniVoice) engine is **Apache-2.0**, a permissive license. This is what makes the open-core model viable: Apache-2.0 allows OmniVoice App's *own* original code to be distributed under more restrictive source-available terms, provided upstream attribution and `NOTICE` requirements are preserved. The Community License explicitly does **not** restrict OmniVoice itself — see [LICENSE Part B.3](../LICENSE) and [NOTICE](../NOTICE).

### Commercial licensing

Uses outside the Community grant — reselling, managed-service hosting, white-labeling, or running a competing SaaS — require a **separate commercial license**. The Cloud and Enterprise editions are delivered under such commercial terms. Contact **bruno3dcontato@gmail.com** to discuss.

### Future licensing options

The project may, at its discretion, offer additional licensing arrangements over time, such as:

- **Dual licensing** — the Community License for open use, plus negotiated commercial licenses for restricted use.
- **OEM / embedding licenses** for integrating OmniVoice App into other products.
- **Relicensing of older versions** under more permissive terms if and when appropriate ([LICENSE Part B / §2.5](../LICENSE)).

Any such options will be announced and applied prospectively; they will not retroactively reduce the rights already granted for a released version.

---

## Commitments to the Community

- The Community Edition will remain **source-available and free to self-host**.
- Core generation features will **not** be removed from Community to force upgrades.
- Changes to licensing will be **transparent** and apply to future versions, not retroactively to rights already granted.
- Upstream **attribution to OmniVoice** will always be preserved.

---

<sub>Copyright © 2026 Bruno Silva and the OmniVoice App contributors. Built on [OmniVoice](https://github.com/k2-fsa/OmniVoice) (Apache-2.0). This document is informational and not legal advice.</sub>

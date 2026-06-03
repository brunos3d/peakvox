# Security Policy

The OmniVoice App team takes the security of the project and its users seriously. This document explains how to report vulnerabilities and what to expect in return.

## Supported Versions

OmniVoice App is in active development toward a stable 1.0. Security fixes are provided for the latest released version on the `main` branch.

| Version | Supported |
| ------- | --------- |
| Latest release (`main`) | ✅ |
| Pre-release / older tags | ⚠️ Best effort |

We recommend always running the latest version. Self-hosters are responsible for keeping their deployment, dependencies, and host environment up to date.

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues, discussions, or pull requests.**

Instead, report privately using one of the following:

1. **GitHub Security Advisories** — open a private advisory via the repository's **Security → Report a vulnerability** tab (preferred).
2. **Email** — **bruno3dcontato@gmail.com** with the subject line `SECURITY: OmniVoice App`.

Please include, where possible:

- A description of the vulnerability and its potential impact.
- Steps to reproduce or a proof of concept.
- Affected version/commit and deployment mode (Docker vs. local, GPU vs. CPU).
- Any suggested remediation.

If you wish to encrypt your report, mention this in an initial email and we will arrange a secure channel.

## Responsible Disclosure Policy

We follow a coordinated disclosure model:

- **Acknowledgement:** we aim to acknowledge your report within **5 business days**.
- **Assessment:** we will investigate, validate, and determine severity and scope.
- **Resolution:** we will work on a fix and keep you informed of progress.
- **Disclosure:** we will coordinate public disclosure with you, typically after a fix is released. We aim to resolve high-severity issues promptly and will agree on a reasonable embargo period.
- **Credit:** with your permission, we will credit you in the release notes / advisory. We do not currently operate a paid bug-bounty program.

We ask that you:

- Give us reasonable time to remediate before any public disclosure.
- Avoid privacy violations, data destruction, and service disruption while researching.
- Only test against your own self-hosted instance — never against other users' deployments.

## Security Expectations for Self-Hosters

OmniVoice App ships with developer-friendly defaults that are **not** production-secure. Before exposing a deployment beyond localhost, you should:

- **Change all default credentials**, especially `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` (default `minioadmin`/`minioadmin`).
- **Do not expose** the backend (`:8000`), MinIO API (`:9000`), or MinIO console (`:9001`) directly to the public internet. Place the app behind a reverse proxy with TLS.
- **Scope `CORS_ORIGINS`** to the exact origins you serve from.
- **Enable TLS** for MinIO (`MINIO_SECURE=true`) and your reverse proxy.
- **Add authentication.** The Community Edition does not include user authentication; add an auth layer (reverse-proxy auth, VPN, or network isolation) before multi-user or internet-facing use.
- **Restrict and back up** the `omnivoice_data` and `minio_data` volumes — they contain voice profiles, reference audio, and generated content.
- **Keep dependencies patched** and rebuild images regularly.

## Scope

This policy covers the OmniVoice App code in this repository. Vulnerabilities in the upstream [OmniVoice](https://github.com/k2-fsa/OmniVoice) engine or other third-party dependencies (see [NOTICE](NOTICE)) should be reported to their respective maintainers; we are happy to help coordinate.

## Abuse and Misuse

Security issues are distinct from **misuse** of the software (e.g. using it to clone a voice without consent). Misuse is addressed by the [Voice Usage Policy](VOICE_USAGE_POLICY.md) and the [LICENSE](LICENSE), not this policy. To report abuse of an OmniVoice App deployment you do not control, contact that deployment's operator.

---

<sub>Copyright © 2026 Bruno Silva and the OmniVoice App contributors.</sub>

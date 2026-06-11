# Security Policy

The PeakVox team takes the security of the project and its users seriously. This document
explains how to report vulnerabilities and what to expect in return, and sets out the security
considerations specific to a model-agnostic, self-hosted voice runtime.

## Supported Versions

PeakVox is in active development toward a stable 1.0. Security fixes are provided for the latest
version on the `main` branch.

| Version | Supported |
| --- | --- |
| Latest release (`main`) | ✅ |
| Pre-release / older tags | ⚠️ Best effort |

We recommend always running the latest version. Self-hosters are responsible for keeping their
deployment, its installed **runtimes**, dependencies, and host environment up to date.

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues, discussions, or
pull requests.**

Instead, report privately using one of the following:

1. **GitHub Security Advisories** — open a private advisory via the repository's
   **Security → Report a vulnerability** tab (preferred).
2. **Email** — **bruno3dcontato@gmail.com** with the subject line `SECURITY: PeakVox`.

Please include, where possible:

- A description of the vulnerability and its potential impact.
- Steps to reproduce or a proof of concept.
- Affected version/commit, deployment mode (Docker vs. local), and the **runtime(s)/model(s)**
  involved.
- Any suggested remediation.

If you wish to encrypt your report, mention this in an initial email and we will arrange a
secure channel.

## Responsible Disclosure Policy

We follow a coordinated disclosure model:

- **Acknowledgement:** we aim to acknowledge your report within **5 business days**.
- **Assessment:** we will investigate, validate, and determine severity and scope.
- **Resolution:** we will work on a fix and keep you informed of progress.
- **Disclosure:** we will coordinate public disclosure with you, typically after a fix is
  released, and agree on a reasonable embargo for high-severity issues.
- **Credit:** with your permission, we will credit you in the release notes / advisory. We do
  not currently operate a paid bug-bounty program.

We ask that you:

- Give us reasonable time to remediate before any public disclosure.
- Avoid privacy violations, data destruction, and service disruption while researching.
- Only test against your own self-hosted instance — never against other users' deployments.

## The PeakVox threat surface (what self-hosters must understand)

PeakVox is a **Universal Voice Runtime**: it installs and runs multiple model **runtimes**,
can **import community runtime variants**, and downloads model assets from third-party sources.
This is powerful, and it changes the threat model compared to a single static application.

### 1. Runtime execution & the Docker socket

The Runtime Registry runs models as **containers** managed by the `DockerRuntimeDriver`. In a
default Docker deployment, the backend is granted access to the host **Docker socket**
(`/var/run/docker.sock`) so it can start, stop, and manage runtime containers.

- **Treat Docker-socket access as root-equivalent on the host.** Anyone who can reach the
  backend API can, by extension, influence container lifecycle. Do **not** expose the backend
  to untrusted networks.
- Run PeakVox on a host you control; isolate it from sensitive workloads.
- Prefer least-privilege deployment topologies as they become available; restrict who can reach
  the management API.

### 2. Installing runtimes & downloading weights (Hugging Face and others)

Activating a runtime downloads images and model weights/checkpoints from third-party sources
(e.g. Hugging Face) into the model cache (`HF_HOME`, default `/data/models`).

- **Only install runtimes and weights you trust.** Model artifacts are executable code paths and
  large binaries; a malicious or tampered artifact is a supply-chain risk.
- Pin runtimes to specific, verified image versions/digests where the descriptor supports it.
- Keep the model cache on storage you control; restrict and back it up.

### 3. Community runtime variant imports

PeakVox supports importing **community runtime variants** (e.g. fine-tuned checkpoints that
reuse a trusted runtime image). These carry **trust/provenance metadata** and are **validated
before they are trusted**
([ADR-0019](docs/.agents/DECISIONS/adr-0019-variant-trust-and-community-imports.md)).

- **Imported variants are untrusted by default.** Verify the source URL and provenance before
  promoting a variant's trust tier.
- A variant from an unknown source should be treated like any other untrusted third-party
  artifact: review it, sandbox it, and do not run it on a host with sensitive data until you
  trust it.
- Do not disable or work around the import validation gates.

### 4. Voice data & generated content

Voice profiles, reference audio, and generated audio are sensitive — they can identify and
impersonate real people.

- Restrict and back up the data volumes (database and object storage) — they contain voice
  identities, reference audio, and generated content.
- Apply the [Voice Usage Policy](VOICE_USAGE_POLICY.md): consent is required to clone a real
  person's voice; the policy is incorporated into the [LICENSE](LICENSE).

### 5. Default credentials & exposure

PeakVox ships with developer-friendly defaults that are **not** production-secure. Before
exposing a deployment beyond localhost:

- **Change all default credentials**, especially `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY`
  (default `minioadmin`/`minioadmin`).
- **Do not expose** the backend (`:8000`), MinIO API (`:9000`), or MinIO console (`:9001`)
  directly to the public internet. Place the app behind a reverse proxy with TLS.
- **Scope `CORS_ORIGINS`** to the exact origins you serve from.
- **Enable TLS** for MinIO (`MINIO_SECURE=true`) and your reverse proxy.
- **Add authentication.** Community Edition does not include user authentication; add an auth
  layer (reverse-proxy auth, VPN, or network isolation) before multi-user or internet-facing
  use. Multi-tenant auth is a Cloud-only concern.
- **Keep dependencies and installed runtimes patched**, and update images regularly.

## Scope

This policy covers the PeakVox code in this repository. Vulnerabilities in **upstream model
runtimes** (e.g. [OmniVoice](https://github.com/k2-fsa/OmniVoice), F5-TTS, Kokoro, and other
integrated providers) or other third-party dependencies (see [NOTICE](NOTICE)) should be
reported to their respective maintainers; we are happy to help coordinate.

## Abuse and Misuse

Security issues are distinct from **misuse** of the software (e.g. cloning a voice without
consent). Misuse is addressed by the [Voice Usage Policy](VOICE_USAGE_POLICY.md) and the
[LICENSE](LICENSE), not this policy. To report abuse of a PeakVox deployment you do not control,
contact that deployment's operator.

---

<sub>Copyright © 2026 Bruno Silva and the PeakVox contributors.</sub>

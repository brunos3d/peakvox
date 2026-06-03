# Frequently Asked Questions

> See also: [README](../README.md) · [Architecture](ARCHITECTURE.md) · [Roadmap](ROADMAP.md) · [Commercial Model](COMMERCIAL_MODEL.md) · [Voice Usage Policy](../VOICE_USAGE_POLICY.md)

---

### What is OmniVoice App?

OmniVoice App is a self-hosted platform for **Voice Cloning**, **Text-to-Speech**, and **Voice Design**, built on top of the open-source [OmniVoice](https://github.com/k2-fsa/OmniVoice) model. It wraps OmniVoice in a polished multi-page web app, an async generation API, voice profile management, generation presets, and object storage — all deployable with a single `docker compose up`. It is a **source-available Community Edition** today, designed to grow into optional Cloud and Enterprise editions (see [COMMERCIAL_MODEL.md](COMMERCIAL_MODEL.md)).

### How is it different from ElevenLabs and other hosted services?

- **Self-hosted & private.** Your text, reference audio, voice profiles, and generated audio stay on infrastructure you control. Nothing is sent to a third-party voice API.
- **Source-available.** You can read, modify, and run the code under the [Community License](../LICENSE).
- **No per-character metering.** Generation is bounded by your own hardware, not a billing plan.
- **Built on open models.** It uses OmniVoice (Apache-2.0), a massively multilingual zero-shot model supporting 600+ languages.

The trade-off: you run and maintain it yourself, and quality/throughput depend on your hardware. A future managed **Cloud Edition** is on the [roadmap](ROADMAP.md) for those who prefer not to self-host.

### Does it require a GPU?

No, but one is **strongly recommended**. OmniVoice is fast on a capable NVIDIA GPU (real-time factor as low as ~0.025, i.e. ~40× faster than real time). It also runs on CPU, but generation is substantially slower. To run on CPU, remove the GPU reservation block from [`docker-compose.yml`](../docker-compose.yml) — see the [CPU deployment](../README.md#cpu-deployment) section.

### Can it run locally?

Yes — that's the primary use case. The full stack (frontend, backend, MinIO) runs on a single machine via Docker Compose, or you can run the frontend and backend directly for development (see the [README](../README.md#development-setup-without-docker)). The first run downloads the OmniVoice model (~2.5 GB) automatically.

### Can I use it commercially?

It depends on **how**:

- ✅ **Allowed:** self-hosting, personal use, educational/research use, and **internal business use** within your own company.
- ❌ **Not allowed without a separate commercial license:** reselling it, offering it to third parties as a hosted/managed service, running a competing SaaS, or white-labeling it.

This is governed by the [OmniVoice App Community License](../LICENSE) (based on the Elastic License 2.0). For commercial/managed-service rights, contact **bruno3dcontato@gmail.com**. Note also that the underlying OmniVoice model is Apache-2.0 and unaffected by this license. *(This is a summary, not legal advice — read the [LICENSE](../LICENSE).)*

### How does voice cloning work?

You provide a short reference clip (upload a file or record in the browser) of a voice **you are authorized to use**. The backend passes it to OmniVoice, which extracts a speaker representation ("clone prompt") and uses it to condition speech generation so the output resembles the reference voice. To keep repeat generations fast, the clone prompt is cached per voice profile. See the [cloning pipeline](ARCHITECTURE.md#7-voice-cloning-pipeline) for details.

**Important:** cloning a real person's voice requires their informed consent. See the [Voice Usage Policy](../VOICE_USAGE_POLICY.md).

### What's the difference between Voice Cloning and Voice Design?

- **Voice Cloning** reproduces a *specific existing* voice from a reference recording.
- **Voice Design** builds a *new* voice from a controlled set of attributes (gender, age, pitch, style, accent) — no reference audio required.

### How are files stored?

Audio is stored as **objects in MinIO** (S3-compatible), not in the database. Reference clips live at `voices/{id}/voice.wav` and generated audio at `generated/{hash}.wav`; the database stores only metadata and keys. MP3 versions are transcoded on demand. Because MinIO is S3-compatible, you can repoint it at AWS S3 or any compatible store in production. See the [storage architecture](ARCHITECTURE.md#5-storage-architecture).

### What database does it use?

The Community Edition defaults to **SQLite** (zero-config, single file). The data layer is written against async SQLAlchemy 2 and is **PostgreSQL-ready** — switching is a `DATABASE_URL` change, intended for multi-user/Cloud deployments. PostgreSQL as a first-class option is on the [roadmap](ROADMAP.md).

### Is it safe to expose to the internet?

Not with the default settings. The Community Edition ships **without built-in authentication** and with developer-friendly defaults (e.g. `minioadmin`/`minioadmin`). Before any internet-facing deployment, follow the hardening steps in [SECURITY.md](../SECURITY.md): change credentials, add an auth layer, enable TLS, and keep ports private behind a reverse proxy.

### How do I report a security issue or misuse?

- **Security vulnerabilities:** privately, per [SECURITY.md](../SECURITY.md) — never as a public issue.
- **Misuse of the software:** see the [Voice Usage Policy](../VOICE_USAGE_POLICY.md#7-reporting-misuse).

### How can I contribute?

Read [CONTRIBUTING.md](../CONTRIBUTING.md) for the workflow, branch strategy, commit conventions, and PR requirements, and the [Code of Conduct](../CODE_OF_CONDUCT.md) before participating.

---

<sub>Copyright © 2026 Bruno Silva and the OmniVoice App contributors. Built on [OmniVoice](https://github.com/k2-fsa/OmniVoice) (Apache-2.0).</sub>

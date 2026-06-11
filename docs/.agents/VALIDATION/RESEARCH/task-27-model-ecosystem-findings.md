# Task 27 — Model Ecosystem Findings (Phases E, F, G + D/H rationale)

> **Date:** 2026-06-11 · **Author:** Task 27 · **Status:** Findings (investigation)
> **Companion to:** [Task 26 audit](../AUDITS/task-27-runtime-variants-audit.md),
> [ADR-0018](../../DECISIONS/adr-0018-runtime-variants-architecture.md),
> [migration plan](../../IMPLEMENTATION/PLANS/2026-06-11-runtime-variants-migration.md)

This document records the feasibility investigations Task 27 was asked to
perform but **not** blindly implement: the generic import path (E), shared
runtime images (F), and capability discovery (G). It also states the rationale
behind the foundations that *were* shipped this task: community imports (D) and
the Verified/Community distinction (H).

---

## Phase D — Community Model Imports (foundation SHIPPED)

**What shipped:** `runtime_variant_import.validate_variant_import()` +
`POST /runtimes/{id}/variants/validate-import` + the frontend import dialog.
This is the **validate** stage of `Add → paste URL → validate → download →
register → use`, and only the network-free part of it.

**Why stop at validate:** download + register touch the filesystem (the shared
weights cache) and the running runtime service (load the new checkpoint). Both
are Phase 4/6 of the migration and require a runtime service that can host
multiple checkpoints (not yet built). Shipping validate-only is safe, additive,
reversible, and immediately useful (it tells the user *before* any download
whether the checkpoint can work).

**The remaining import pipeline (designed, not built):**

```
validate (done) → resolve files (HfApi.list_repo_files) → download to
/data/runtime-weights/<runtime>/<variant>/ (huggingface_hub.snapshot_download,
in the runtime container, not the backend) → write variants/<id>.json with
trust=community + source_url → POST /v1/variants/load on the runtime → available
```

The download belongs **inside the runtime container** (it already has the model
framework + GPU + the HF cache mount), surfaced through a new
`variant_add` RuntimeOperation for progress — never in the backend, which must
stay model-framework-free (Runtime Activation Audit; ADR-0016/0017).

---

## Phase E — Generic Model Import Path (Ollama / LM Studio style)

**Question:** can a user paste *any* model URL and have PeakVox figure out the
rest, like `ollama pull` or LM Studio's catalog?

**Finding: partially, and only within a runtime family.** The Ollama/LM Studio
analogy breaks in one important place: those tools have **one runtime**
(llama.cpp / a GGUF loader) that loads *any* compatible GGUF. Voice models do
**not** share a single loader — F5-TTS, OmniVoice, XTTS, Kokoro each need their
own inference code. So PeakVox can be "Ollama for voice" **per runtime family**:
a checkpoint imports onto *its* runtime, not onto a universal one.

### What can be discovered automatically (from the HF Hub API, no download)

`huggingface_hub.HfApi` exposes, without downloading weights:

| Signal | Source | Reliability |
|---|---|---|
| Repo exists / is public / gated | `model_info()` | High |
| File list (`*.safetensors`, `config.json`, `tokenizer.*`, `vocab.txt`) | `list_repo_files()` | High |
| Library / framework | `model_info().library_name` (`transformers`, `f5_tts`, …) | Medium |
| Pipeline tag | `model_info().pipeline_tag` (`text-to-speech`, …) | Medium |
| Declared language(s) | card metadata `language:` | Medium (often missing) |
| Architecture / base model | `config.json` `architectures`, `model_type` | Medium |
| License | card metadata `license:` | Medium |
| Checkpoint format | file extensions | High |

### What must be declared (cannot be safely inferred)

- **Provider/runtime compatibility.** A repo named `F5-TTS-pt-br` is *not*
  proof it runs on the F5-TTS runtime — naming is not a contract (ADR-0003).
  The architecture string in `config.json` is the strongest *automatic* signal,
  but the safe default is: the user (or a curated catalog) declares the target
  runtime, and we **check** the declaration against the runtime's
  `provider`/`model_family` labels. This is exactly what `validate_variant_import`
  does today.
- **Capabilities.** TTS-vs-voice-cloning-vs-singing is rarely machine-readable.
  Declared-and-checked (Phase G).

### What must be manually verified

- That the checkpoint **actually loads and generates** on the runtime. No static
  signal proves this — it is the boundary between *architecture-validated* and
  *provider-validated* (Constitution VII §23). An imported variant is therefore
  `community` (untested) until someone runs it end-to-end.

**Recommendation:** build a thin `HfModelProbe` service (Cloud-first; CE
optional, behind a network-access flag) that fills the *discoverable* columns to
pre-populate the import dialog, lowering the manual-declaration burden — but the
compatibility decision stays declared-and-checked. Do **not** attempt a fully
automatic "paste any URL, we'll figure out the runtime" flow: it would
inevitably guess wrong and violate ADR-0003.

---

## Phase F — Shared Runtime Images

**Concern:** every runtime image currently bundles Python + CUDA + PyTorch +
libraries → multi-GB images (OmniVoice 9.4 GB, F5-TTS similar). F5-TTS,
OmniVoice, XTTS, OpenVoice share most of that infrastructure.

### Feasibility of each option

1. **Shared base image (layer sharing) — FEASIBLE NOW, low risk.**
   All three runtimes can `FROM` one PeakVox base
   (`peakvox/runtime-base:cuda12.8-torch2.8`) that owns Python + the matched
   torch/torchaudio/torchvision stack (exactly the stack the OmniVoice hotfix
   just pinned). Docker layer caching then **shares those gigabytes on disk
   across every runtime image** — pull/build once, reuse everywhere. This is the
   single highest-leverage, lowest-risk image change and is a natural Phase 2
   companion. It needs no architecture change, only a shared Dockerfile base.

2. **Runtime *family* images (one image, many checkpoints) — FEASIBLE, this is
   the RuntimeVariant thesis.** `f5-tts` ships one image; PT-BR/Narrator/base are
   checkpoint-only `variants/*.json` downloaded into the shared cache. This is
   precisely migration Phases 2+4 and the reason RuntimeVariant exists. No image
   per variant.

3. **Variant-only downloads — FEASIBLE, depends on (2) + the weights cache.**
   The schema already models `RuntimeCheckpoint{source_type, source_ref}`; the
   driver already mounts `/data`. Downloading a checkpoint to
   `/data/runtime-weights/<rt>/<variant>/` is additive.

4. **Dynamic checkpoint loading (switch without restart) — FEASIBLE but
   per-runtime work (migration Phase 4).** Requires each `server.py` to host an
   LRU-bounded keyed variant registry and a `/v1/variants/load` endpoint.
   **F5-TTS is the hard case** (Task 24's serialized-inference + non-thread-safe
   DiT text-embed cache): variant switching must take the module-level lock and
   clear the cache on change. Port order: Kokoro → OmniVoice → F5.

5. **One universal mega-image (all models in one container) — REJECTED.**
   Couples release cycles, multiplies the attack surface, breaks edition/license
   scoping per model, and bloats the image with every framework even when the
   user wants one model. Contradicts the runtime-as-isolation-unit design
   (ADR-0016).

### CE vs Cloud implications

- **CE:** shared base image is a pure win (less disk, faster installs). Family
  images + variant downloads keep CE simple — one card per family, "Add variant"
  instead of "install another multi-GB runtime."
- **Cloud:** shared base + prebuilt family images in a registry; variant
  checkpoints become marketplace artifacts (migration Phase 5). The autoscaler
  benefits from fewer distinct images to warm.

**Recommendation:** implement option (1) — the shared base image — as the first
concrete image change (low risk, immediate disk savings), bundled with migration
Phase 2. Options (2)–(4) follow the existing phased plan. This task does **not**
rebuild images (out of scope for a no-GPU session); it records the path.

---

## Phase G — Model Capability Discovery

**Goal:** imported variants advertise capabilities (`supports_tts`,
`supports_voice_cloning`, `supports_singing`, …) automatically.

**Finding: capabilities must be declared, not inferred — but discovery can
*propose* a declaration.**

| Capability | Auto-inferable? | How |
|---|---|---|
| `tts` | Weakly | `pipeline_tag: text-to-speech` |
| `multilingual` | Weakly | card `language:` lists >1 |
| `voice_cloning` / `reference_audio` | No | not in HF metadata; runtime-family property |
| `voice_conversion` | No | architecture-specific |
| `singing` / `emotions` / `voice_design` | No | almost never declared |
| `streaming` | No | a runtime *service* property, not a checkpoint property |

The honest model, consistent with ADR-0003 (*capabilities are declared, never
inferred*): a variant **inherits its runtime's capability set as the ceiling**,
and may declare a **subset** (a PT-BR checkpoint might do `tts` + `voice_cloning`
but not the runtime's `voice_design`). `validate_variant_import` already enforces
"declared ⊆ runtime capabilities". Discovery's role is to **pre-fill** the
declaration from `pipeline_tag`/`language`, which the user then confirms — never
to silently grant a capability. A capability is only trustworthy once
**provider-validated** (someone ran it), which is why imported variants stay
`community`.

**Recommendation:** keep the closed `RUNTIME_CAPABILITY_VOCABULARY` as the
contract; add an optional `propose_capabilities(probe) → list[str]` helper later
that suggests a subset from discoverable signals. Do not auto-apply.

---

## Phase H — Verified vs Community Models (foundation SHIPPED)

**What shipped:** `RuntimeVariantMetadata.trust: "verified" | "community"`
(defaults `verified`), surfaced in the composed API and as a UI badge; imported
variants are forced to `community` by `validate_variant_import`.

**Semantics (the load-bearing distinction):**

| | Verified | Community |
|---|---|---|
| Curated by PeakVox | ✓ | ✗ |
| Provider-validated (ran end-to-end) | ✓ | ✗ |
| Checkpoint source | pinned/known | user-supplied |
| Compatibility | checked **and** tested | checked only |
| UI badge | green ✓ | amber ⚠ |

This maps cleanly onto the existing *architecture-validated vs provider-validated*
axis (Constitution VII §23): **Verified = provider-validated; Community =
architecture-validated (compatibility checked) but not provider-validated.** No
new concept — a UI-facing name for a distinction the project already enforces.

**Cloud extension (future):** `trust` is the natural hook for marketplace
curation tiers (Verified / Partner / Community) and for policy (Cloud may forbid
`community` variants on shared tenants). Schema-ready, inert in CE.

---

## Summary of recommendations

| Phase | Verdict | Action |
|---|---|---|
| D Community imports | Foundation shipped | Build download+register on top of validate (Phase 6). |
| E Generic import | Feasible per runtime family | Add an `HfModelProbe` to pre-fill declarations; keep compatibility declared-and-checked. |
| F Shared images | Feasible; start with shared base image | Implement `peakvox/runtime-base` in migration Phase 2; family images + variant downloads follow. |
| G Capability discovery | Declared, with proposal | Variant caps ⊆ runtime caps (enforced); add a non-binding `propose_capabilities` later. |
| H Verified/Community | Foundation shipped | `trust` field + badge; extend to Cloud curation tiers + policy. |

None of these require abandoning the Runtime Registry, the Runtime Manager, the
drivers, or the Voice-first architecture. Every step is additive and reversible.

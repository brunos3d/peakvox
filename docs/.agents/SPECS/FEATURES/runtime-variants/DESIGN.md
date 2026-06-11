# DESIGN — Runtime Variants

> **Spec:** [SPEC.md](./SPEC.md) · **ADR:** [ADR-0018](../../../DECISIONS/adr-0018-runtime-variants-architecture.md)
> The ADR carries the full rationale, diagrams, storage/CE/Cloud/HF/UX
> analysis, and the ADR-0016 amendment. This document is the **engineering
> design** for the descriptor primitive (Phase 0) and the resolution shape
> (Phase 1), which the migration plan rolls out.

## 1. Descriptor schema (Phase 0 — shipped)

A new closed Pydantic model in `backend/app/services/runtime_types.py`,
parallel to `RuntimeDescriptor`:

```
RuntimeVariantDescriptor
  api_version: "peakvox.io/v1"
  kind:        "RuntimeVariant"
  metadata:
    id:          DNS-label            # variant id, e.g. "pt-br"
    name:        str
    runtime_id:  str                  # the Runtime this variant belongs to
    description: str = ""
    labels:      dict[str,str] = {}
  spec:
    model_binding: RuntimeModelBinding # reuses the existing type (model_id, is_default, priority)
    checkpoint:    RuntimeCheckpoint   # NEW: source + format + optional digest/size
    is_default:    bool = False
    capabilities:  list[str] = []      # optional; subset of the runtime's, validated like RuntimeDescriptor
    edition:       list[str] = []      # optional; inert in CE (schema-ready, ADR-0005 extension)
```

```
RuntimeCheckpoint
  source_type: "hf" | "url" | "local" | "bundled"
  source_ref:  str                     # HF repo id, URL, or path under the weights cache
  format:      str                     # e.g. "safetensors", "pt"
  digest:      Optional[str]           # sha256, when known
  size_mb:     Optional[float]
```

Design choices:
- **Reuse `RuntimeModelBinding`** — variants bind to a catalog model exactly
  as runtimes do today (audit §1.1, §3.1). No new binding type.
- **Closed schema** (no `extra`) — matches `RuntimeDescriptorSpec` discipline
  (audit §1.5).
- **`checkpoint` never names weights formats on the public API** — it is
  infrastructure-internal (ADR-0004 §6).

## 2. Loader (Phase 0 — shipped)

`RuntimeRegistryLoader` optionally walks `<root>/<id>/variants/*.json`:

- For each runtime directory, after loading `descriptor.json`, glob
  `variants/*.json`, validate each as `RuntimeVariantDescriptor`, and attach
  to the registry's variant index keyed by `runtime_id`.
- Bad variant files are **skipped-and-logged**, never fatal (mirrors
  `_load_one` for descriptors, `runtime_registry.py:117-125`).
- A runtime with no `variants/` folder yields **zero** explicit variants; the
  resolver synthesizes an implicit `base` variant in Phase 1 (R7).

`RuntimeRegistry` gains:
- `_by_runtime_variant: dict[runtime_id -> list[RuntimeVariantDescriptor]]`
- `list_variants_for_runtime(runtime_id) -> list[RuntimeVariantDescriptor]`
- `get_variant(runtime_id, variant_id) -> Optional[...]`

**Phase 0 guarantee:** nothing reads the variant index yet — resolution and
lifecycle are unchanged. The primitive exists to be wired in Phase 1.

## 3. Resolution shape (Phase 1 — planned)

`RuntimeManager.resolve(model_id)` (today `runtime_manager.py:213-271`) gains a
variant step **after** the runtime is chosen:

```
descriptor = choose_runtime(model_id)                  # unchanged: default/priority/hint
variant    = choose_variant(descriptor, model_id)      # NEW:
               # the variant whose model_binding.model_id == model_id,
               # else the runtime's default variant,
               # else synthetic "base"
return RuntimeResolution(descriptor, instance, endpoint,
                         runtime_variant_id=variant.id) # NEW optional field
```

The adapter forwards `runtime_variant` to `/v1/generate` when present. Omission
is valid (service uses its default). **No Voice/VoiceVariant reference enters
the manager** (audit §3.5).

## 4. Runtime Service (Phase 4 — planned, designed here)

Generalize the single-model singleton (`server.py:53-169`) to a keyed registry:

```
_variants: OrderedDict[variant_id -> LoadedCheckpoint]  # LRU, VRAM/RAM-budgeted
_default_variant_id: str                                 # eager-loaded on /ready

load_variant(vid):   idempotent; resolve checkpoint from cache; evict LRU; load under _load_lock
generate(req):       vid = req.runtime_variant or _default; load_variant(vid); infer
```

- `/ready` ⇒ default variant loaded.
- `GET /v1/variants`, `POST /v1/variants/load` added; `GenerateRequest.runtime_variant`
  added **alongside** `variant_id`.
- **F5 constraint (audit §5.5):** switching respects the module-level inference
  lock + clears the DiT cache on variant change; the LRU never holds two
  variants live during one inference.

## 5. Storage & driver (no driver change for CE)

- Weights cache: `/data/runtime-weights/<runtime_id>/<variant_id>/`.
- `DockerRuntimeDriver` already mounts the backend's named `/data` volume into
  every runtime container (`docker_runtime_driver.py:237-255,609-625`) — the
  cache needs **no new driver mechanism** (audit §4.2). Variant download is the
  job of a variant-provisioning service / the runtime service, **not** the
  driver (ADR-0016 invariant 8).

## 6. Naming guards (enforced in review)

| Concept | Field / type | Never |
|---|---|---|
| VoiceVariant | `variant_id` (`/v1/generate`), `VariantListItem`/`VariantSummaryItem` (FE), `/v1/variants/build` | reused for checkpoints |
| RuntimeVariant | `runtime_variant` (`/v1/generate`), `RuntimeVariantDescriptor`, `/v1/variants/load` | a domain entity / repository / public API field |

## 7. Test plan (Phase 0)

- `RuntimeVariantDescriptor` validates a good `variants/*.json`; rejects bad
  `kind`, missing `runtime_id`, unknown capabilities.
- Loader: registry with `variants/` exposes them via
  `list_variants_for_runtime`; registry **without** `variants/` is identical to
  today (existing descriptor tests unchanged).
- Bad variant file is skipped-and-logged, does not block the runtime.

---

## 8. Model Ecosystem UX (Task 27 Phase I)

The Models page evolves from *runtime-oriented* to *model-ecosystem* while
staying understandable to non-technical users. The change is **additive
presentation**, not a new information architecture.

### Before → After (the runtime card)

```
BEFORE (runtime catalog)                AFTER (model ecosystem)
┌─────────────────────────────┐         ┌─────────────────────────────┐
│ F5-TTS                       │         │ F5-TTS                       │
│ image: peakvox/f5-tts:0.1    │         │ image: peakvox/f5-tts:0.1    │
│ [Install] [Start] [Stop]     │         │ [Install] [Start] [Stop]     │
│ Service / Requirements / Caps│         │ ── Variants (2) ──── [+ HF]  │
└─────────────────────────────┘         │  ◆ Base        ✓ Verified ★  │
                                         │    tts, voice_cloning        │
                                         │  ◆ PT-BR       ⚠ Community    │
                                         │    tts · huggingface.co/...  │
                                         │ Service / Requirements / Caps│
                                         └─────────────────────────────┘
```

### Principles

1. **One card per runtime; variants are *inside* it.** Importing a checkpoint
   does **not** create a new card/runtime entry — it adds a chip. This is the
   visible payoff of the Runtime/RuntimeVariant split.
2. **Trust is always visible.** Every variant shows a Verified (green ✓) or
   Community (amber ⚠) badge. The default variant shows a ★.
3. **Capability-driven, never model-internal.** Chips show *declared
   capabilities* (ADR-0003); the UI never shows checkpoint paths/formats/digests
   (ADR-0004 §6). `source_type` shows as a friendly label ("Bundled with
   runtime", "Hugging Face"), `source_url` as a link.
4. **Import is guided and honest.** "Add variant from Hugging Face" opens a
   dialog that *validates compatibility first* and reports reasons/warnings;
   it is explicit that download+register is a follow-up. No fake buttons.
5. **Simplicity preserved.** A single-`base` runtime shows a one-line "no
   additional variants — import one to add a specialization" instead of an empty
   grid. Nothing new to learn until the user wants a variant.

### Future UX (PLANNED, not this task)

- **Family grouping**: collapse `f5-tts-base` / future `f5-tts` aliases into one
  "F5-TTS" family header (migration Phase 2 directory consolidation).
- **Installed vs Available**: once download+register lands, variants gain an
  install state (chip Add/Remove) and an "Available" catalog distinct from
  "Installed" (migration Phase 4/6).
- **Compatibility indicators** on community variants (probe-derived; findings
  Phase E/G), shown as a non-binding hint, never as a trust upgrade.

See [`../../../VALIDATION/RESEARCH/task-27-model-ecosystem-findings.md`](../../../VALIDATION/RESEARCH/task-27-model-ecosystem-findings.md)
for the feasibility analysis behind the future items.

export interface VoiceGenerationDefaults {
  num_step: number
  guidance_scale: number
  speed: number | null
  duration: number | null
  t_shift: number
  denoise: boolean
  use_gpu: boolean
  // Structured Voice Design attributes (one per category). The flat OmniVoice
  // `instruct` string is derived from this at generation time.
  voice_design: string[]
}

export type VoiceStatus = "ready" | "archived" | "processing" | "failed"

/**
 * Derived, read-only snapshot of a voice's traits, generated server-side from
 * `voice_design` (source of truth) + preset tags. Filtering/search read this — never
 * edited by hand.
 */
export interface PreviewSummary {
  origin: "reference" | "provider" | "generated" | "user" | "marketplace" | "none"
  count: number
  languages: string[]
}

export interface VoiceCharacteristics {
  gender: string | null
  age_group: string | null
  accent: string | null
  pitch: string | null
  style_tags: string[]
  speaking_speed: string | null
  emotional_range: string | null
}

export type CreationSource = "SOURCE_ASSET" | "PRESET_VOICE" | "MARKETPLACE_VOICE" | "TRAINED_VOICE" | "IMPORTED_VOICE" | "SYSTEM_VOICE"

export interface VoiceSourceAsset {
  id: string
  asset_type: string
  original_filename: string | null
  content_type: string | null
  file_size: number | null
  audio_duration: number | null
  created_at: string
}

export interface VoiceProfile {
  id: string
  /** Stable, never-changing public identifier (e.g. "voice_8JXQ29K4L3"). */
  public_voice_id: string
  owner_id: string
  name: string
  description: string | null
  language: string | null
  language_code: string | null
  transcript: string | null
  audio_filename: string
  audio_duration: number | null
  meta: Record<string, unknown> | null
  generation_defaults: VoiceGenerationDefaults | null
  preset_tags: string[] | null
  characteristics: VoiceCharacteristics | null
  is_public: boolean
  is_community_voice: boolean
  is_preset_voice: boolean
  is_favorite: boolean
  creation_source: CreationSource
  primary_model_id: string | null
  recommended_model_id: string | null
  compatible_models: string[]
  preview_summary: PreviewSummary
  source_asset: VoiceSourceAsset | null
  status: VoiceStatus
  usage_count: number
  created_at: string
  updated_at: string | null
  last_used_at: string | null
}

export interface ApiKey {
  id: string
  name: string
  prefix: string
  status: string
  created_at: string
  last_used_at: string | null
}

/** Returned only at creation — carries the raw key exactly once. */
export interface ApiKeyCreateResponse extends ApiKey {
  key: string
}

export type VoiceScope = "mine" | "community" | "preset" | "recent"

export interface VoiceQueryFilters {
  language_code?: string | null
  gender?: string | null
  age_group?: string | null
  accent?: string | null
  favorite?: boolean
}

export interface VoicePreview {
  id: string
  voice_id: string
  preview_origin: string
  language: string | null
  source_model_id: string | null
  storage_key: string
  duration: number | null
  created_at: string
}

export interface VoicePreviewList {
  items: VoicePreview[]
}

export type SortField = "name" | "created_at" | "last_used_at" | "language" | "usage_count"

export interface VoiceListPage {
  items: VoiceProfile[]
  next_cursor: string | null
}

export interface TemporaryVoice {
  id: string
  source_resource_id: string
  name: string
  language: string | null
  language_code: string | null
  compatible_models: string[]
  preview_summary: PreviewSummary
  creation_source: CreationSource
  primary_model_id: null
  recommended_model_id: string | null
  meta: Record<string, unknown> | null
  isTemporary: true
  transcript: null
  audio_duration: null
  generation_defaults: null
  preview_audio_url: string | null
  provider_id: string | null
  gender: string | null
  description: string | null
  status: "ready"
  is_favorite: false
  is_public: false
  is_preset_voice: true
  usage_count: 0
}

export type AnyVoice = VoiceProfile | TemporaryVoice

export function isTemporaryVoice(voice: VoiceProfile | TemporaryVoice | null): voice is TemporaryVoice {
  return voice !== null && "isTemporary" in voice && voice.isTemporary === true
}

export function isVoiceProfile(voice: VoiceProfile | TemporaryVoice | null): voice is VoiceProfile {
  return voice !== null && !("isTemporary" in voice)
}

export type RealizationState = "ready" | "buildable" | "incompatible"

/** Canonical three-state compatibility for a voice+model pair.
 *  Computed by merging compatible_models (declarative) with variant status (runtime).
 *  Single source of truth — all components consume this, never raw compatible_models. */
export interface VoiceModelCompatibility {
  modelId: string
  state: RealizationState
  variantStatus?: string
}

export interface GenerationRequest {
  text: string
  /** Optional model selector. null/undefined falls back to the platform default. */
  model_id?: string | null
  voice_profile_id?: string | null
  ref_text?: string | null
  language?: string | null
  instruct?: string | null
  /** Model-specific parameters. Use this instead of the individual fields below. */
  params?: Record<string, unknown>
  /** @deprecated Use params instead. */
  num_step?: number
  /** @deprecated Use params instead. */
  guidance_scale?: number
  /** @deprecated Use params instead. */
  speed?: number | null
  /** @deprecated Use params instead. */
  duration?: number | null
  /** @deprecated Use params instead. */
  t_shift?: number
  /** @deprecated Use params instead. */
  denoise?: boolean
}

export interface JobResponse {
  id: string
  status: "pending" | "processing" | "completed" | "failed"
  text: string
  voice_profile_id: string | null
  language: string | null
  instruct: string | null
  generation_params: Record<string, unknown> | null
  audio_url: string | null
  audio_duration: number | null
  error_message: string | null
  logs: string[] | null
  created_at: string
  started_at: string | null
  completed_at: string | null
}

export type JobStatus = JobResponse["status"]

export interface ModelCapabilities {
  // Contract version (ADR-0003). New capabilities are additive; unknown ones are ignored.
  capability_version?: number
  supports_tts: boolean
  supports_voice_cloning: boolean
  supports_emotions: boolean
  supports_singing: boolean
  supports_streaming: boolean
  supports_api: boolean
  // ADR-0003 superset (optional for forward/back compatibility).
  supports_voice_conversion?: boolean
  supports_emotion_tags?: boolean
  supports_voice_design?: boolean
  supports_multilingual?: boolean
  supports_reference_audio?: boolean
  supports_batch_generation?: boolean
  supports_voice_optional?: boolean
}

export interface SelectOption {
  label: string
  value: string
}

export interface ParameterSchema {
  type: "number" | "boolean" | "string" | "select"
  label: string
  default: number | boolean | string | null
  minimum?: number
  maximum?: number
  step?: number
  options?: SelectOption[]
  description?: string
  /**
   * If true, the parameter accepts `null` to mean "use the model's default".
   * Nullable numbers render as a slider (centered on `auto_value`) or a numeric
   * input depending on `ui_widget`. Nullable booleans/selects ignore this flag
   * unless explicitly extended.
   */
  nullable?: boolean
  /**
   * For nullable numbers: which UI control to render. "slider" centers on
   * `auto_value`; "input" treats empty field as null.
   */
  ui_widget?: "slider" | "input" | null
  /**
   * The slider position that maps to `null` (the "Auto" position). Defaults
   * to the geometric center of `minimum`/`maximum`, or to `default` if it
   * lies within the range.
   */
  auto_value?: number | null
}

export interface SettingsSchema {
  type: string
  properties: Record<string, ParameterSchema>
  required?: string[]
}

export interface ModelRequirements {
  min_vram_gb: number | null
  gpu_required: boolean
  runtime: string | null
}

export interface ModelLicense {
  name: string | null
  code: string | null
  weights_license: string | null
  commercial_use: boolean | null
  url: string | null
}

export interface ModelVoiceFeatures {
  voice_types: string[]
}

export interface Model {
  id: string
  name: string
  description: string
  version: string
  provider: string
  repo_id: string | null
  model_path: string | null
  supported_languages: string[]
  supported_tags: string[]
  supported_voice_design: string[]
  capabilities: ModelCapabilities
  requirements?: ModelRequirements
  license?: ModelLicense | null
  settings_schema?: SettingsSchema | null
  provider_metadata?: Record<string, string | string[]>
  voice_features?: ModelVoiceFeatures
  status: "available" | "loading" | "loaded" | "error" | "disabled" | "inactive" | "deprecated"
  is_default: boolean
  is_builtin: boolean
  editions: string[]
  available_in_ce: boolean
  available_in_cloud: boolean
  homepage_url: string | null
  repository_url: string | null
  provider_url: string | null
  license_name: string | null
  license_url: string | null
  gpu_requirements: { required: boolean; source: string }
  memory_requirements: { min_vram_gb: number | null; source: string }
  runtime_requirements: { runtime: string | null; source: string }
  edition_availability: { community: boolean; cloud: boolean; basis: string }
  install_status: "installed" | "not_installed" | "downloading" | "failed"
  activation_status: "active" | "inactive"
}

export interface ModelTagMetadata {
  id: string
  label: string
  emoji: string
  category: string
  description: string
  syntax: string
}

export interface ModelStatus {
  loaded: boolean
  loading: boolean
  error: string | null
  sampling_rate: number
  resident_model_id?: string | null
}

/**
 * Edition feature flags from the backend. Commercial surfaces (marketplace, creators,
 * billing) are gated on these — hidden in Community Edition where they are all false.
 * See docs/architecture/01-PRODUCT_ARCHITECTURE.md §4.
 */
export interface PlatformFeatures {
  auth: boolean
  tenancy: boolean
  billing: boolean
  marketplace: boolean
  creators: boolean
  payouts: boolean
}

export interface PlatformInfo {
  name: string
  edition: string
  features: PlatformFeatures
}

// ── Variant lifecycle (ADR-0008 / ADR-0009) ──────────────────────────────────

export interface VariantBuildResponse {
  voice_id: string
  model_id: string
  status: string
  active_artifact_version: number | null
}

export interface VariantStatusResponse {
  model_id: string
  model_name: string
  status: string
  active_artifact_version: number | null
  artifact_count: number
  error_message: string | null
}

export interface VariantListItem {
  model_id: string
  model_name: string
  status: string
  realization_type: string | null
  active_artifact_version: number | null
  error_message: string | null
}

export interface VariantSummaryItem {
  voice_id: string
  voice_name: string
  models: Array<{
    model_id: string
    model_name: string
    status: string
    active_artifact_version: number | null
    error_message: string | null
  }>
}

export interface ArtifactVersionResponse {
  version: number
  created_at: string
  is_active: boolean
  model_version: string | null
  size_bytes: number | null
  storage_keys: Record<string, unknown> | null
}

export interface ProviderVoiceResponse {
  provider_voice_id: string
  provider_id: string
  external_id: string
  name: string
  description: string
  language: string | null
  gender: string | null
  is_default: boolean
}

export interface CreateFromPresetRequest {
  provider: string
  preset_name: string
  name: string
  model_id: string
}

export interface VoiceResourceResponse {
  id: string
  resource_type: string
  resource_origin: string
  name: string
  description: string
  language: string | null
  preview_audio_url: string | null
  catalog_source: Record<string, unknown> | null
  provider_id: string | null
  external_id: string | null
  gender: string | null
  is_default: boolean
  is_in_library: boolean
  library_voice_id: string | null
  compatible_models: string[]
  recommended_model_id: string | null
}

// ---------------------------------------------------------------------------
// Runtime types (Phase 3 — runtime-registry surface)
//
// The Runtime Registry is the authoritative source of runtime metadata
// (image, port, lifecycle, etc.). The Models page renders from
// GET /api/runtimes when RUNTIME_SERVICE_ENABLED=true; the legacy
// /api/models (BUILTIN_MODELS) is the fallback.
//
// A Runtime is NOT a Voice and is NOT a Model in the domain sense. It is
// infrastructure that the Model layer routes to. Per ADR-0016/0017, the
// runtime's `model_binding.model_id` joins a runtime to the catalog
// model it serves.
// ---------------------------------------------------------------------------

// RuntimePhase matches the lowercase enum returned by the
// runtime-state API (ADR-0017 §RuntimeState). The UI normalizes
// to Title Case for display only; maps keyed on this type
// therefore use lowercase keys.
export type RuntimePhase =
  | "notInstalled"
  | "installing"
  | "pulling"
  | "installed"
  | "starting"
  | "active"
  | "stopping"
  | "stopped"
  | "failed"
  | "updating"
  | "removing";

export type RuntimeOperationType = "install" | "update" | "start" | "stop" | "remove" | "build"
export type RuntimeOperationStatus = "pending" | "running" | "completed" | "failed" | "cancelled"

export interface RuntimeOperation {
  id: string;
  runtime_id: string;
  type: RuntimeOperationType;
  status: RuntimeOperationStatus;
  progress: number;
  message: string;
  started_at: string;
  updated_at: string;
  cancellable: boolean;
  error: string | null;
}

export interface RuntimeImage {
  repository: string;
  tag: string;
  digest: string | null;
  image_size_mb?: number | null;
}

export interface RuntimeBuild {
  entrypoint: string;
  build_context: string;
  dockerfile: string;
}

export interface RuntimeServiceContract {
  protocol: "http" | "grpc";
  port: number;
  endpoints: {
    health: string;
    ready: string;
    generate: string;
    build: string;
    metadata: string;
  };
}

export interface RuntimeRequirements {
  gpu: "required" | "optional" | "none";
  min_vram_gb: number | null;
  cpu_cores: number | null;
  memory_gb: number | null;
  edition: string[];
}

export interface RuntimeModelBinding {
  model_id: string;
  is_default: boolean;
  priority: number;
}

export interface RuntimeLifecycle {
  install_policy: string;
  health_interval_seconds: number;
  health_timeout_seconds: number;
  start_timeout_seconds: number;
  restart_policy: string;
  idle_timeout: string;
}

export interface RuntimeStatePayload {
  runtime_id: string;
  phase: RuntimePhase;
  host: string | null;
  port: number | null;
  image_identity: RuntimeImage | null;
  started_at: string | null;
  last_health_at: string | null;
  last_request_at: string | null;
  health_state: "ready" | "not_ready" | "unknown" | null;
  endpoint: string | null;
  operation: RuntimeOperation | null;
}

export interface RuntimeCard {
  runtime_id: string;
  name: string;
  description: string;
  provider: string;
  version: string;
  edition: string[];
  image: RuntimeImage;
  build: RuntimeBuild | null;
  service: RuntimeServiceContract;
  capabilities: string[];
  requirements: RuntimeRequirements;
  model_binding: RuntimeModelBinding;
  lifecycle: RuntimeLifecycle;
  state: RuntimeStatePayload;
}

export interface RuntimesResponse {
  runtimes: RuntimeCard[];
}

export interface RuntimeOperationResponse {
  operation: RuntimeOperation | null;
}

export interface RuntimeOperationsResponse {
  operations: RuntimeOperation[];
}

// ---------------------------------------------------------------------------
// Composed view (R9) — Catalog + Runtime Registry + Runtime State
//
// The Models page renders a composed view: the Model Catalog is
// the primary entity; the runtime-registry and runtime state are
// the infrastructure augmentation. A model may exist without a
// runtime; a model with a runtime shows the runtime's state,
// endpoint, and lifecycle buttons.
// ---------------------------------------------------------------------------

export interface ModelWithRuntimesCard {
  model: Record<string, unknown>;  // ModelDescriptor (catalog entity)
  runtimes: ComposedRuntimeEntry[];
  default_runtime_id: string | null;
}

export interface ModelsWithRuntimesResponse {
  models: ModelWithRuntimesCard[];
}

// ---------------------------------------------------------------------------
// Composed-view runtime entry
//
// The /api/models/with-runtimes endpoint returns the raw on-disk
// descriptor (not the lifted RuntimeCard shape used by
// /api/runtimes). This entry pairs that raw descriptor with the
// live state. The Models page renders entirely from this shape.
// ---------------------------------------------------------------------------

export interface ComposedRuntimeImage {
  repository: string;
  tag: string;
  digest: string | null;
  image_size_mb?: number | null;
}

export interface ComposedRuntimeBuild {
  entrypoint: string;
  build_context: string;
  dockerfile: string;
}

export interface ComposedRuntimeService {
  protocol: "http" | "grpc";
  port: number;
  health_path: string;
  readiness_path: string;
  generate_path: string;
  build_path: string;
  metadata_path: string;
}

export interface ComposedRuntimeRequirements {
  gpu: "required" | "optional" | "none";
  min_vram_gb: number | null;
  cpu_cores: number | null;
  memory_gb: number | null;
  edition: string[];
}

export interface ComposedRuntimeLifecycle {
  install_policy: string;
  health_interval_seconds: number;
  health_timeout_seconds: number;
  start_timeout_seconds: number;
  restart_policy: string;
  idle_timeout: string;
}

export interface ComposedRuntimeSpec {
  runtime_type: string;
  image: ComposedRuntimeImage;
  build: ComposedRuntimeBuild | null;
  service: ComposedRuntimeService;
  capabilities: string[];
  requirements: ComposedRuntimeRequirements;
  model_binding: {
    model_id: string;
    is_default: boolean;
    priority: number;
  };
  lifecycle: ComposedRuntimeLifecycle;
}

export interface ComposedRuntimeMetadata {
  id: string;
  name: string;
  description: string;
  provider: string;
  version: string;
  edition: string[];
  labels: Record<string, string>;
}

export interface ComposedRuntimeDescriptor {
  api_version: string;
  kind: string;
  metadata: ComposedRuntimeMetadata;
  spec: ComposedRuntimeSpec;
}

// ---------------------------------------------------------------------------
// RuntimeVariant (ADR-0018) — a checkpoint/specialization attached to a
// runtime. Public-safe: the API never exposes checkpoint internals
// (source_ref/format/digest) per ADR-0004 §6. NEVER the domain VoiceVariant.
// ---------------------------------------------------------------------------

export type RuntimeVariantTrust = "verified" | "community";

export interface ComposedRuntimeVariant {
  id: string;
  name: string;
  description: string;
  trust: RuntimeVariantTrust;
  source_url: string | null;
  source_type: "hf" | "url" | "local" | "bundled";
  model_id: string;
  is_default: boolean;
  capabilities: string[];
}

export interface ComposedRuntimeEntry {
  runtime_id: string;
  descriptor: ComposedRuntimeDescriptor | null;
  state: RuntimeStatePayload;
  variants?: ComposedRuntimeVariant[];
}

// Result of POST /runtimes/{id}/variants/validate-import (validate-only).
export interface VariantImportValidation {
  runtime_id: string;
  repo_id: string;
  source_url: string;
  compatible: boolean;
  proposed_variant_id: string;
  trust: RuntimeVariantTrust;
  reasons: string[];
  warnings: string[];
}

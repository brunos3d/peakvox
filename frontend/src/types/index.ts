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
export interface VoiceCharacteristics {
  gender: string | null
  age_group: string | null
  accent: string | null
  pitch: string | null
  style_tags: string[]
  speaking_speed: string | null
  emotional_range: string | null
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

export interface VoiceListPage {
  items: VoiceProfile[]
  next_cursor: string | null
}

export interface GenerationRequest {
  text: string
  /** Optional model selector. null/undefined falls back to the platform default. */
  model_id?: string | null
  voice_profile_id?: string | null
  ref_text?: string | null
  language?: string | null
  instruct?: string | null
  num_step?: number
  guidance_scale?: number
  speed?: number | null
  duration?: number | null
  t_shift?: number
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

export interface GenerationSettings {
  num_step: number
  guidance_scale: number
  speed: number | null
  duration: number | null
  t_shift: number
  denoise: boolean
}

export interface ModelCapabilities {
  supports_tts: boolean
  supports_voice_cloning: boolean
  supports_emotions: boolean
  supports_singing: boolean
  supports_streaming: boolean
  supports_api: boolean
}

export interface ModelRequirements {
  min_vram_gb: number | null
  gpu_required: boolean
  runtime: string | null
}

export interface ModelLicense {
  code: string | null
  weights_license: string | null
  commercial_use: boolean | null
  url: string | null
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
  provider_metadata?: Record<string, string>
  status: "available" | "loading" | "loaded" | "error" | "disabled"
  is_default: boolean
  is_builtin: boolean
  editions: string[]
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

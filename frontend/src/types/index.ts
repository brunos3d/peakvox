export interface VoiceProfile {
  id: string
  name: string
  description: string | null
  language: string | null
  transcript: string | null
  audio_filename: string
  audio_duration: number | null
  meta: Record<string, unknown> | null
  created_at: string
  last_used_at: string | null
}

export interface GenerationRequest {
  text: string
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

export interface ModelStatus {
  loaded: boolean
  loading: boolean
  error: string | null
  sampling_rate: number
}

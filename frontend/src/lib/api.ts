import type {
  VoiceProfile,
  VoiceGenerationDefaults,
  VoiceListPage,
  VoiceScope,
  VoiceQueryFilters,
  ApiKey,
  ApiKeyCreateResponse,
  GenerationRequest,
  JobResponse,
  Model,
  ModelTagMetadata,
  ModelStatus,
  PlatformInfo,
  VariantListItem,
  VariantStatusResponse,
  VariantBuildResponse,
  VariantSummaryItem,
  ArtifactVersionResponse,
  BackfillResponse,
} from "@/types"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

/** Base URL of the OmniVoice backend — used to render API examples. */
export function getApiBaseUrl(): string {
  return API_URL
}

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = "ApiError"
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_URL}${path}`
  const res = await fetch(url, {
    ...options,
    headers: {
      ...(options?.headers || {}),
    },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    const message =
      typeof body.detail === "object" && body.detail !== null
        ? body.detail.message ?? JSON.stringify(body.detail)
        : body.detail ?? "Request failed"
    throw new ApiError(res.status, message)
  }
  return res.json()
}

export async function fetchVoices(): Promise<VoiceProfile[]> {
  return request<VoiceProfile[]>("/voices")
}

export async function fetchVoice(id: string): Promise<VoiceProfile> {
  return request<VoiceProfile>(`/voices/${id}`)
}

export async function fetchVoicesPage(params: {
  scope?: VoiceScope
  search?: string
  filters?: VoiceQueryFilters
  limit?: number
  cursor?: string | null
}): Promise<VoiceListPage> {
  const qs = new URLSearchParams()
  if (params.scope) qs.set("scope", params.scope)
  if (params.search) qs.set("search", params.search)
  if (params.limit != null) qs.set("limit", String(params.limit))
  if (params.cursor) qs.set("cursor", params.cursor)
  const f = params.filters ?? {}
  if (f.language_code) qs.set("language_code", f.language_code)
  if (f.gender) qs.set("gender", f.gender)
  if (f.age_group) qs.set("age_group", f.age_group)
  if (f.accent) qs.set("accent", f.accent)
  if (f.favorite) qs.set("favorite", "true")
  const suffix = qs.toString() ? `?${qs.toString()}` : ""
  return request<VoiceListPage>(`/voices/page${suffix}`)
}

export async function setVoiceFavorite(id: string, isFavorite: boolean): Promise<VoiceProfile> {
  return request<VoiceProfile>(`/voices/${id}/favorite`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ is_favorite: isFavorite }),
  })
}

export async function createVoice(formData: FormData): Promise<VoiceProfile> {
  return request<VoiceProfile>("/voices", {
    method: "POST",
    body: formData,
  })
}

export async function updateVoice(id: string, formData: FormData): Promise<VoiceProfile> {
  return request<VoiceProfile>(`/voices/${id}`, {
    method: "PUT",
    body: formData,
  })
}

export async function deleteVoice(id: string): Promise<void> {
  await request<void>(`/voices/${id}`, { method: "DELETE" })
}

export async function saveVoiceGenerationDefaults(
  id: string,
  defaults: VoiceGenerationDefaults,
): Promise<VoiceProfile> {
  return request<VoiceProfile>(`/voices/${id}/defaults`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(defaults),
  })
}

export function getVoiceAudioUrl(id: string): string {
  return `${API_URL}/voices/${id}/audio`
}

// ── Variant lifecycle (ADR-0008 / ADR-0009) ──────────────────────────────────

export async function fetchVoiceVariants(voiceId: string): Promise<VariantListItem[]> {
  return request<VariantListItem[]>(`/voices/${voiceId}/variants`)
}

export async function fetchVariantStatus(voiceId: string, modelId: string): Promise<VariantStatusResponse> {
  return request<VariantStatusResponse>(`/voices/${voiceId}/variants/${modelId}`)
}

export async function ensureVariant(
  voiceId: string, modelId?: string
): Promise<VariantBuildResponse> {
  const qs = modelId ? `?model_id=${encodeURIComponent(modelId)}` : ""
  return request<VariantBuildResponse>(`/voices/${voiceId}/variants${qs}`, {
    method: "POST",
  })
}

export async function rebuildVariant(voiceId: string, modelId: string): Promise<VariantBuildResponse> {
  return request<VariantBuildResponse>(`/voices/${voiceId}/variants/${modelId}/rebuild`, {
    method: "POST",
  })
}

export async function rollbackVariant(voiceId: string, modelId: string, version: number): Promise<VariantBuildResponse> {
  return request<VariantBuildResponse>(`/voices/${voiceId}/variants/${modelId}/rollback/${version}`, {
    method: "POST",
  })
}

export async function fetchArtifactVersions(voiceId: string, modelId: string): Promise<ArtifactVersionResponse[]> {
  return request<ArtifactVersionResponse[]>(`/voices/${voiceId}/variants/${modelId}/artifacts`)
}

export async function fetchVariantSummary(): Promise<VariantSummaryItem[]> {
  const res = await fetch(`${API_URL}/variants/summary`)
  if (!res.ok) throw new ApiError(res.status, "Failed to fetch variant summary")
  return res.json()
}

export async function backfillMissingVariants(modelFilter?: string): Promise<BackfillResponse> {
  const qs = modelFilter ? `?model_filter=${encodeURIComponent(modelFilter)}` : ""
  return request<BackfillResponse>(`/variants/backfill${qs}`, { method: "POST" })
}

// ── API keys (internal dashboard) ────────────────────────────────────────────
export async function fetchApiKeys(): Promise<ApiKey[]> {
  return request<ApiKey[]>("/api-keys")
}

export async function createApiKey(name: string): Promise<ApiKeyCreateResponse> {
  return request<ApiKeyCreateResponse>("/api-keys", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  })
}

export async function deleteApiKey(id: string): Promise<ApiKey> {
  return request<ApiKey>(`/api-keys/${id}`, { method: "DELETE" })
}

export async function submitGeneration(data: GenerationRequest): Promise<{ job_id: string }> {
  return request<{ job_id: string }>("/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  })
}

export async function fetchJob(jobId: string): Promise<JobResponse> {
  return request<JobResponse>(`/jobs/${jobId}`)
}

export async function fetchJobs(params?: {
  limit?: number
  offset?: number
  status?: string
}): Promise<JobResponse[]> {
  const qs = new URLSearchParams()
  if (params?.limit != null) qs.set("limit", String(params.limit))
  if (params?.offset != null) qs.set("offset", String(params.offset))
  if (params?.status) qs.set("status", params.status)
  const suffix = qs.toString() ? `?${qs.toString()}` : ""
  return request<JobResponse[]>(`/jobs${suffix}`)
}

export async function deleteJob(jobId: string): Promise<void> {
  await request<void>(`/jobs/${jobId}`, { method: "DELETE" })
}

export function getJobAudioUrl(jobId: string): string {
  return `${API_URL}/jobs/${jobId}/audio`
}

export function getJobAudioMp3Url(jobId: string): string {
  return `${API_URL}/jobs/${jobId}/audio/mp3`
}

export function getJobAudioConvertedUrl(jobId: string, format: "mp3" | "ogg"): string {
  return `${API_URL}/jobs/${jobId}/audio/${format}`
}

export async function fetchModels(): Promise<Model[]> {
  const data = await request<{ models: Model[] }>("/models")
  return data.models
}

export async function fetchModel(id: string): Promise<Model> {
  return request<Model>(`/models/${id}`)
}

export async function fetchModelTags(id: string): Promise<{ model_id: string; tags: ModelTagMetadata[] }> {
  return request<{ model_id: string; tags: ModelTagMetadata[] }>(`/models/${id}/tags`)
}

export async function fetchModelStatus(): Promise<ModelStatus> {
  return request<ModelStatus>("/models/status")
}

export async function installModel(id: string): Promise<{ id: string; status: Model["status"] }> {
  return request<{ id: string; status: Model["status"] }>(`/models/${id}/install`, { method: "POST" })
}

export async function updateModel(id: string): Promise<{ id: string; status: Model["status"] }> {
  return request<{ id: string; status: Model["status"] }>(`/models/${id}/update`, { method: "POST" })
}

export async function removeModel(id: string): Promise<{ id: string; removed: boolean }> {
  return request<{ id: string; removed: boolean }>(`/models/${id}/remove`, { method: "POST" })
}

export async function activateModel(id: string): Promise<{ id: string; status: Model["status"] }> {
  return request<{ id: string; status: Model["status"] }>(`/models/${id}/activate`, { method: "POST" })
}

export async function deactivateModel(id: string): Promise<{ id: string; status: Model["status"] }> {
  return request<{ id: string; status: Model["status"] }>(`/models/${id}/deactivate`, { method: "POST" })
}

export async function fetchDeviceSettings(): Promise<{ use_gpu: boolean; cuda_available: boolean }> {
  return request("/settings/device")
}

export async function updateDeviceSettings(useGpu: boolean): Promise<{ use_gpu: boolean; cuda_available: boolean }> {
  return request("/settings/device", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ use_gpu: useGpu }),
  })
}

export async function uploadAudio(file: File): Promise<{ filename: string }> {
  const formData = new FormData()
  formData.append("file", file)
  return request<{ filename: string }>("/upload", {
    method: "POST",
    body: formData,
  })
}

/**
 * Edition info + feature flags. Commercial nav (marketplace, creators, billing) renders only
 * when the matching flag is true — all false in Community Edition.
 */
export async function getFeatures(): Promise<PlatformInfo> {
  return request<PlatformInfo>("/platform/features")
}

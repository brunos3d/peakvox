import type {
  VoiceProfile,
  VoiceGenerationDefaults,
  VoiceListPage,
  VoicePreviewList,
  VoiceScope,
  VoiceQueryFilters,
  SortField,
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
  ProviderVoiceResponse,
  CreateFromPresetRequest,
  VoiceResourceResponse,
  RuntimeCard,
  RuntimesResponse,
  RuntimeStatePayload,
  RuntimeImage,
  RuntimeOperation,
  RuntimeOperationResponse,
  RuntimeOperationsResponse,
  ModelWithRuntimesCard,
  ModelsWithRuntimesResponse,
} from "@/types"
import { parseApiError, type ApiError } from "./api-error"

function normalizeApiBaseUrl(raw: string): string {
  const trimmed = raw.trim()
  if (!trimmed) return "http://localhost:8000"

  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
    return trimmed.replace(/\/+$/, "")
  }

  if (trimmed.startsWith("//")) {
    const protocol = typeof window !== "undefined" ? window.location.protocol : "http:"
    return `${protocol}${trimmed}`.replace(/\/+$/, "")
  }

  // Allow explicit same-origin proxy paths if configured (for example, "/api").
  if (trimmed.startsWith("/")) {
    return trimmed.replace(/\/+$/, "")
  }

  // Host[:port] values are treated as HTTP endpoints.
  return `http://${trimmed}`.replace(/\/+$/, "")
}

function resolveApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL
  if (configured && configured.trim()) {
    return normalizeApiBaseUrl(configured)
  }

  if (typeof window !== "undefined") {
    return `${window.location.protocol}//${window.location.hostname}:8000`
  }

  return "http://localhost:8000"
}

const API_URL = resolveApiBaseUrl()

/** Base URL of the OmniVoice backend — used to render API examples. */
export function getApiBaseUrl(): string {
  return API_URL
}

export { ApiError }

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_URL}${path}`
  let res: Response
  try {
    res = await fetch(url, {
      ...options,
      headers: {
        ...(options?.headers || {}),
      },
    })
  } catch (e) {
    // Network / abort / CORS — throw a structured ApiError so the consumer
    // can render it via <ApiErrorDialog />.
    const err = await parseApiError(null, e, url)
    throw Object.assign(new Error(err.message), err)
  }
  if (!res.ok) {
    const err = await parseApiError(res, null, url)
    throw Object.assign(new Error(err.message), err)
  }
  return res.json() as Promise<T>
}

export async function fetchVoices(): Promise<VoiceProfile[]> {
  return request<VoiceProfile[]>("/voices")
}

export async function fetchVoice(id: string): Promise<VoiceProfile> {
  return request<VoiceProfile>(`/voices/${id}`)
}

export async function fetchVoicePreviews(
  voiceId: string,
  params?: { language?: string; preview_origin?: string; source_model_id?: string }
): Promise<VoicePreviewList> {
  const qs = new URLSearchParams()
  if (params?.language) qs.set("language", params.language)
  if (params?.preview_origin) qs.set("preview_origin", params.preview_origin)
  if (params?.source_model_id) qs.set("source_model_id", params.source_model_id)
  const suffix = qs.toString() ? `?${qs.toString()}` : ""
  return request<VoicePreviewList>(`/voices/${voiceId}/previews${suffix}`)
}

export async function fetchVoicesPage(params: {
  scope?: VoiceScope
  search?: string
  filters?: VoiceQueryFilters
  limit?: number
  cursor?: string | null
  sort_by?: SortField
  sort_dir?: "asc" | "desc"
  creation_source?: string
  provider?: string
  recently_used?: string
}): Promise<VoiceListPage> {
  const qs = new URLSearchParams()
  if (params.scope) qs.set("scope", params.scope)
  if (params.search) qs.set("search", params.search)
  if (params.limit != null) qs.set("limit", String(params.limit))
  if (params.cursor) qs.set("cursor", params.cursor)
  if (params.sort_by) qs.set("sort_by", params.sort_by)
  if (params.sort_dir) qs.set("sort_dir", params.sort_dir)
  if (params.creation_source) qs.set("creation_source", params.creation_source)
  if (params.provider) qs.set("provider", params.provider)
  if (params.recently_used) qs.set("recently_used", params.recently_used)
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
  const url = `${API_URL}/variants/summary`
  const res = await fetch(url)
  if (!res.ok) {
    const err = await parseApiError(res, null, url)
    throw Object.assign(new Error("Failed to fetch variant summary"), err)
  }
  return res.json()
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

// ---------------------------------------------------------------------------
// Runtime API (Phase 3 — runtime-registry surface)
//
// The Models page renders from /api/runtimes when
// RUNTIME_SERVICE_ENABLED=true; the legacy /api/models is the fallback.
// The runtime API is gated: when no manager is attached (CE default), the
// endpoints return 503 with a clear error message.
// ---------------------------------------------------------------------------

export async function fetchRuntimes(): Promise<RuntimeCard[]> {
  const data = await request<RuntimesResponse>("/runtimes")
  return data.runtimes
}

export async function fetchRuntime(id: string): Promise<RuntimeCard> {
  return request<RuntimeCard>(`/runtimes/${id}`)
}

export async function fetchRuntimeState(id: string): Promise<RuntimeStatePayload> {
  return request<RuntimeStatePayload>(`/runtimes/${id}/state`)
}

export async function fetchRuntimeOperation(id: string): Promise<RuntimeOperation | null> {
  const data = await request<RuntimeOperationResponse>(`/runtimes/${id}/operation`)
  return data.operation
}

export async function fetchRuntimeOperations(activeOnly = true): Promise<RuntimeOperation[]> {
  const data = await request<RuntimeOperationsResponse>(`/runtime-operations?active_only=${activeOnly ? "true" : "false"}`)
  return data.operations
}

export async function cancelRuntimeOperation(id: string, operationId: string): Promise<RuntimeOperation | null> {
  const data = await request<RuntimeOperationResponse>(`/runtimes/${id}/operations/${operationId}/cancel`, {
    method: "POST",
  })
  return data.operation
}

export async function installRuntime(
  id: string,
): Promise<{ runtime_id: string; phase: string; image_identity: RuntimeImage }> {
  return request(`/runtimes/${id}/install`, { method: "POST" })
}

export async function startRuntime(
  id: string,
): Promise<{ runtime_id: string; phase: string; host: string; port: number; endpoint: string }> {
  return request(`/runtimes/${id}/start`, { method: "POST" })
}

export async function stopRuntime(id: string): Promise<{ runtime_id: string; phase: string }> {
  return request(`/runtimes/${id}/stop`, { method: "POST" })
}

export async function updateRuntime(
  id: string,
): Promise<{ runtime_id: string; phase: string; image_identity: RuntimeImage }> {
  return request(`/runtimes/${id}/update`, { method: "POST" })
}

export async function removeRuntime(id: string): Promise<{ runtime_id: string; phase: string }> {
  return request(`/runtimes/${id}/remove`, { method: "POST" })
}

// ---------------------------------------------------------------------------
// Composed view (R9) — Catalog + Runtime Registry + Runtime State
//
// The Models page renders from this endpoint. Available whether
// or not RUNTIME_SERVICE_ENABLED is true; the catalog portion is
// always present, the runtime portion is the augmentation.
// ---------------------------------------------------------------------------

export async function fetchModelsWithRuntimes(): Promise<ModelWithRuntimesCard[]> {
  const data = await request<ModelsWithRuntimesResponse>("/models/with-runtimes")
  return data.models
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

export async function fetchHuggingFaceStatus(): Promise<{ configured: boolean }> {
  return request("/settings/huggingface")
}

export async function saveHuggingFaceToken(token: string): Promise<{ configured: boolean }> {
  return request("/settings/huggingface", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  })
}

export async function deleteHuggingFaceToken(): Promise<{ configured: boolean }> {
  return request("/settings/huggingface", { method: "DELETE" })
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

export async function fetchProviderVoices(params?: {
  provider?: string
  language?: string
  gender?: string
  search?: string
}): Promise<ProviderVoiceResponse[]> {
  const qs = new URLSearchParams()
  if (params?.provider) qs.set("provider", params.provider)
  if (params?.language) qs.set("language", params.language)
  if (params?.gender) qs.set("gender", params.gender)
  if (params?.search) qs.set("search", params.search)
  const query = qs.toString()
  return request<ProviderVoiceResponse[]>(`/api/provider-voices${query ? `?${query}` : ""}`)
}

export async function fetchProviderVoice(id: string): Promise<ProviderVoiceResponse> {
  return request<ProviderVoiceResponse>(`/api/provider-voices/${id}`)
}

export async function createVoiceFromPreset(data: CreateFromPresetRequest): Promise<VoiceProfile> {
  return request<VoiceProfile>("/voices/from-preset", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  })
}

export interface FetchVoiceResourcesParams {
  resource_type?: string
  resource_origin?: string
  search?: string
  language?: string
  gender?: string
}

export async function fetchVoiceResources(params?: FetchVoiceResourcesParams): Promise<VoiceResourceResponse[]> {
  const qs = new URLSearchParams()
  if (params?.resource_type) qs.set("resource_type", params.resource_type)
  if (params?.resource_origin) qs.set("resource_origin", params.resource_origin)
  if (params?.search) qs.set("search", params.search)
  if (params?.language) qs.set("language", params.language)
  if (params?.gender) qs.set("gender", params.gender)
  const query = qs.toString()
  return request<VoiceResourceResponse[]>(`/api/voice-resources${query ? `?${query}` : ""}`)
}

export async function fetchVoiceResource(id: string): Promise<VoiceResourceResponse> {
  return request<VoiceResourceResponse>(`/api/voice-resources/${id}`)
}

export async function importVoiceResource(resourceId: string, modelId?: string): Promise<VoiceProfile> {
  return request<VoiceProfile>(`/api/voice-resources/${resourceId}/import`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model_id: modelId ?? null }),
  })
}

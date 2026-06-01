import type { VoiceProfile, GenerationRequest, JobResponse, ModelStatus } from "@/types"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

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
    throw new ApiError(res.status, body.detail || "Request failed")
  }
  return res.json()
}

export async function fetchVoices(): Promise<VoiceProfile[]> {
  return request<VoiceProfile[]>("/voices")
}

export async function fetchVoice(id: string): Promise<VoiceProfile> {
  return request<VoiceProfile>(`/voices/${id}`)
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

export function getVoiceAudioUrl(id: string): string {
  return `${API_URL}/voices/${id}/audio`
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

export function getJobAudioUrl(jobId: string): string {
  return `${API_URL}/jobs/${jobId}/audio`
}

export function getJobAudioMp3Url(jobId: string): string {
  return `${API_URL}/jobs/${jobId}/audio/mp3`
}

export async function fetchModelStatus(): Promise<ModelStatus> {
  return request<ModelStatus>("/models/status")
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

import { create } from "zustand"
import type { VoiceProfile, JobStatus, VoiceGenerationDefaults, GenerationRequest, TemporaryVoice, VoiceResourceResponse } from "@/types"

export const SYSTEM_DEFAULTS: VoiceGenerationDefaults = {
  num_step: 32,
  guidance_scale: 2.0,
  speed: null,
  duration: null,
  t_shift: 0.1,
  denoise: true,
  use_gpu: true,
  voice_design: [],
}

function persistModelSettings(settings: Record<string, Record<string, unknown>>) {
  if (typeof window !== "undefined") {
    try {
      localStorage.setItem("omnivoice:modelSettings", JSON.stringify(settings))
    } catch { /* quota exceeded — silently degrade */ }
  }
}

function loadModelSettings(): Record<string, Record<string, unknown>> {
  if (typeof window === "undefined") return {}
  try {
    return JSON.parse(localStorage.getItem("omnivoice:modelSettings") ?? "{}")
  } catch { return {} }
}

interface UploadedAudio {
  file: File
  url: string
  duration: number | null
}

export interface CurrentAudio {
  url: string
  duration: number | null
  jobId: string | null
  title: string
  subtitle?: string
}

interface AppState {
  selectedProfile: VoiceProfile | null
  temporaryVoice: TemporaryVoice | null
  uploadedAudio: UploadedAudio | null
  recordedAudio: UploadedAudio | null
  activeJobId: string | null
  activeJobStatus: JobStatus | null
  voiceDesign: string[]
  useGpu: boolean
  activeVoiceDefaults: VoiceGenerationDefaults | null
  voices: VoiceProfile[]
  ttsLanguage: string | null
  currentAudio: CurrentAudio | null
  ttsText: string
  lastRequest: GenerationRequest | null
  outputFormat: "wav" | "mp3" | "ogg"
  selectedModelId: string | null
  modelSettings: Record<string, Record<string, unknown>>

  setSelectedProfile: (profile: VoiceProfile | null) => void
  selectTemporaryVoice: (resource: VoiceResourceResponse) => void
  discardTemporaryVoice: () => void
  promoteTemporaryToPersisted: (profile: VoiceProfile) => void
  setSelectedModelId: (id: string | null) => void
  updateModelSetting: (key: string, value: unknown) => void
  initModelSettings: (modelId: string, settings: Record<string, unknown>) => void
  setTtsLanguage: (language: string | null) => void
  setCurrentAudio: (audio: CurrentAudio | null) => void
  setTtsText: (text: string) => void
  setLastRequest: (req: GenerationRequest | null) => void
  setOutputFormat: (format: "wav" | "mp3" | "ogg") => void
  setUploadedAudio: (audio: UploadedAudio | null) => void
  setRecordedAudio: (audio: UploadedAudio | null) => void
  setActiveJob: (jobId: string | null, status?: JobStatus | null) => void
  setActiveJobStatus: (status: JobStatus | null) => void
  setVoiceDesign: (values: string[]) => void
  setUseGpu: (value: boolean) => void
  setActiveVoiceDefaults: (defaults: VoiceGenerationDefaults | null) => void
  resetSettings: () => void
  setVoices: (voices: VoiceProfile[]) => void
  addVoice: (voice: VoiceProfile) => void
  removeVoice: (id: string) => void
  updateVoice: (id: string, updates: Partial<VoiceProfile>) => void
  resetAudio: () => void
}

export const useAppStore = create<AppState>((set, get) => ({
  selectedProfile: null,
  temporaryVoice: null,
  uploadedAudio: null,
  recordedAudio: null,
  activeJobId: null,
  activeJobStatus: null,
  voiceDesign: SYSTEM_DEFAULTS.voice_design,
  useGpu: SYSTEM_DEFAULTS.use_gpu,
  activeVoiceDefaults: null,
  voices: [],
  ttsLanguage: null,
  currentAudio: null,
  ttsText: "",
  lastRequest: null,
  selectedModelId: null,
  modelSettings: loadModelSettings(),
  outputFormat:
    (typeof window !== "undefined" && (localStorage.getItem("omnivoice:outputFormat") as "wav" | "mp3" | "ogg")) || "wav",

  setSelectedModelId: (id) => {
    const state = get()
    const oldKey = state.selectedModelId ?? "__default__"
    const newKey = id ?? "__default__"

    if (newKey === oldKey) return

    const updated = { ...state.modelSettings }

    let newSettings = updated[newKey]

    // Migrate __default__ settings to a newly selected model
    if (!newSettings && newKey !== "__default__" && updated["__default__"]) {
      newSettings = { ...updated["__default__"] }
      updated[newKey] = newSettings
    }

    set({ selectedModelId: id, modelSettings: updated })

    persistModelSettings(updated)
  },

  setCurrentAudio: (audio) => set({ currentAudio: audio }),
  setTtsText: (text) => set({ ttsText: text }),
  setLastRequest: (req) => set({ lastRequest: req }),

  setOutputFormat: (format) => {
    if (typeof window !== "undefined") localStorage.setItem("omnivoice:outputFormat", format)
    set({ outputFormat: format })
  },

  setSelectedProfile: (profile) => {
    if (!profile) {
      set({
        selectedProfile: null,
        temporaryVoice: null,
        uploadedAudio: null,
        recordedAudio: null,
        activeVoiceDefaults: null,
        voiceDesign: SYSTEM_DEFAULTS.voice_design,
        useGpu: SYSTEM_DEFAULTS.use_gpu,
      })
      return
    }

    const defaults = profile.generation_defaults
    if (defaults) {
      set({
        selectedProfile: profile,
        temporaryVoice: null,
        uploadedAudio: null,
        recordedAudio: null,
        activeVoiceDefaults: defaults,
        voiceDesign: defaults.voice_design ?? [],
        useGpu: defaults.use_gpu,
        ttsLanguage: profile.language_code ?? get().ttsLanguage,
      })
    } else {
      set({
        selectedProfile: profile,
        temporaryVoice: null,
        uploadedAudio: null,
        recordedAudio: null,
        activeVoiceDefaults: null,
        voiceDesign: SYSTEM_DEFAULTS.voice_design,
        useGpu: SYSTEM_DEFAULTS.use_gpu,
        ttsLanguage: profile.language_code ?? get().ttsLanguage,
      })
    }
  },

  selectTemporaryVoice: (resource) => {
    const tempVoice: TemporaryVoice = {
      id: `temp-${resource.id}`,
      source_resource_id: resource.id,
      name: resource.name,
      language: resource.language,
      language_code: null,
      compatible_models: resource.compatible_models,
      preview_summary: {
        origin: "provider",
        count: 0,
        languages: resource.language ? [resource.language] : [],
      },
      creation_source: "PRESET_VOICE",
      primary_model_id: null,
      recommended_model_id: resource.recommended_model_id,
      meta: {
        provider: resource.provider_id,
        external_id: resource.external_id,
      },
      isTemporary: true,
      transcript: null,
      audio_duration: null,
      generation_defaults: null,
      preview_audio_url: resource.preview_audio_url,
      provider_id: resource.provider_id,
      gender: resource.gender,
      description: resource.description,
      status: "ready",
      is_favorite: false,
      is_public: false,
      is_preset_voice: true,
      usage_count: 0,
    }
    set({
      temporaryVoice: tempVoice,
      selectedProfile: null,
      uploadedAudio: null,
      recordedAudio: null,
      activeVoiceDefaults: null,
      voiceDesign: SYSTEM_DEFAULTS.voice_design,
      useGpu: SYSTEM_DEFAULTS.use_gpu,
      ttsLanguage: resource.language ?? get().ttsLanguage,
    })
  },

  discardTemporaryVoice: () => {
    set({
      temporaryVoice: null,
      selectedProfile: null,
      activeVoiceDefaults: null,
      voiceDesign: SYSTEM_DEFAULTS.voice_design,
      useGpu: SYSTEM_DEFAULTS.use_gpu,
    })
  },

  promoteTemporaryToPersisted: (profile) => {
    const defaults = profile.generation_defaults
    set({
      selectedProfile: profile,
      temporaryVoice: null,
      activeVoiceDefaults: defaults ?? null,
      voiceDesign: defaults?.voice_design ?? SYSTEM_DEFAULTS.voice_design,
      useGpu: defaults?.use_gpu ?? SYSTEM_DEFAULTS.use_gpu,
    })
  },

  setTtsLanguage: (language) => set({ ttsLanguage: language }),

  setUploadedAudio: (audio) => set({ uploadedAudio: audio, selectedProfile: null, temporaryVoice: null }),
  setRecordedAudio: (audio) => set({ recordedAudio: audio, selectedProfile: null, temporaryVoice: null }),
  setActiveJob: (jobId, status) => set({ activeJobId: jobId, activeJobStatus: status ?? null }),
  setActiveJobStatus: (status) => set({ activeJobStatus: status }),
  setVoiceDesign: (values) => set({ voiceDesign: values }),

  updateModelSetting: (key, value) => {
    const state = get()
    const modelKey = state.selectedModelId ?? "__default__"
    const currentSettings = state.modelSettings[modelKey] ?? {}
    const updated = {
      ...state.modelSettings,
      [modelKey]: { ...currentSettings, [key]: value },
    }
    set({ modelSettings: updated })
    persistModelSettings(updated)
  },

  initModelSettings: (modelId, settings) => {
    const state = get()
    const key = modelId ?? "__default__"
    const updated = {
      ...state.modelSettings,
      [key]: settings,
    }
    set({ modelSettings: updated })
    persistModelSettings(updated)
  },

  setUseGpu: (value) => set({ useGpu: value }),

  setActiveVoiceDefaults: (defaults) => set({ activeVoiceDefaults: defaults }),

  resetSettings: () => {
    const ref = get().activeVoiceDefaults ?? SYSTEM_DEFAULTS
    set({
      voiceDesign: ref.voice_design ?? [],
      useGpu: ref.use_gpu,
    })
  },

  setVoices: (voices) => set({ voices }),
  addVoice: (voice) => set((state) => ({ voices: [voice, ...state.voices] })),
  removeVoice: (id) => set((state) => ({ voices: state.voices.filter((v) => v.id !== id) })),
  updateVoice: (id, updates) =>
    set((state) => ({
      voices: state.voices.map((v) => (v.id === id ? { ...v, ...updates } : v)),
    })),
  resetAudio: () => set({ uploadedAudio: null, recordedAudio: null, selectedProfile: null, temporaryVoice: null }),
}))

export function useActiveVoice() {
  const profile = useAppStore((s) => s.selectedProfile)
  const temp = useAppStore((s) => s.temporaryVoice)
  return temp ?? profile
}

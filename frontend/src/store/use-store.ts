import { create } from "zustand"
import type { VoiceProfile, JobStatus, GenerationSettings, VoiceGenerationDefaults, GenerationRequest } from "@/types"

// The application's built-in defaults — used when no voice profile is selected
// or when the selected profile has no saved generation_defaults.
export const SYSTEM_DEFAULTS: VoiceGenerationDefaults = {
  num_step: 32,
  guidance_scale: 2.0,
  speed: null,
  duration: null,
  t_shift: 0.1,
  denoise: true,
  use_gpu: true,
}

function defaultsToSettings(d: VoiceGenerationDefaults): GenerationSettings {
  return {
    num_step: d.num_step,
    guidance_scale: d.guidance_scale,
    speed: d.speed,
    duration: d.duration,
    t_shift: d.t_shift,
    denoise: d.denoise,
  }
}

interface UploadedAudio {
  file: File
  url: string
  duration: number | null
}

// The audio currently loaded into the persistent bottom player.
export interface CurrentAudio {
  url: string
  duration: number | null
  jobId: string | null
  title: string
  subtitle?: string
}

interface AppState {
  selectedProfile: VoiceProfile | null
  uploadedAudio: UploadedAudio | null
  recordedAudio: UploadedAudio | null
  activeJobId: string | null
  activeJobStatus: JobStatus | null
  generationSettings: GenerationSettings
  useGpu: boolean
  // The defaults that were loaded when the current profile was selected.
  // null means no profile is selected (or the profile has no saved defaults).
  activeVoiceDefaults: VoiceGenerationDefaults | null
  voices: VoiceProfile[]
  // Persistent bottom-player audio + the text bound to the TTS canvas (lifted
  // into the store so History "Regenerate" can prefill it across routes).
  currentAudio: CurrentAudio | null
  ttsText: string
  // The most recent generation request — enables one-click "Regenerate" from
  // the persistent bottom player regardless of the current route.
  lastRequest: GenerationRequest | null
  // Preferred download format (client-side preference).
  outputFormat: "wav" | "mp3"

  setSelectedProfile: (profile: VoiceProfile | null) => void
  setCurrentAudio: (audio: CurrentAudio | null) => void
  setTtsText: (text: string) => void
  setLastRequest: (req: GenerationRequest | null) => void
  setOutputFormat: (format: "wav" | "mp3") => void
  setUploadedAudio: (audio: UploadedAudio | null) => void
  setRecordedAudio: (audio: UploadedAudio | null) => void
  setActiveJob: (jobId: string | null, status?: JobStatus | null) => void
  setActiveJobStatus: (status: JobStatus | null) => void
  updateGenerationSettings: (settings: Partial<GenerationSettings>) => void
  setUseGpu: (value: boolean) => void
  // Called after a successful "Save to Voice Profile" to sync the reference point.
  setActiveVoiceDefaults: (defaults: VoiceGenerationDefaults | null) => void
  // Reset current settings to whatever was loaded from the active voice (or system defaults).
  resetSettings: () => void
  setVoices: (voices: VoiceProfile[]) => void
  addVoice: (voice: VoiceProfile) => void
  removeVoice: (id: string) => void
  updateVoice: (id: string, updates: Partial<VoiceProfile>) => void
  resetAudio: () => void
}

export const useAppStore = create<AppState>((set, get) => ({
  selectedProfile: null,
  uploadedAudio: null,
  recordedAudio: null,
  activeJobId: null,
  activeJobStatus: null,
  generationSettings: defaultsToSettings(SYSTEM_DEFAULTS),
  useGpu: SYSTEM_DEFAULTS.use_gpu,
  activeVoiceDefaults: null,
  voices: [],
  currentAudio: null,
  ttsText: "",
  lastRequest: null,
  outputFormat: "wav",

  setCurrentAudio: (audio) => set({ currentAudio: audio }),
  setTtsText: (text) => set({ ttsText: text }),
  setLastRequest: (req) => set({ lastRequest: req }),
  setOutputFormat: (format) => set({ outputFormat: format }),

  setSelectedProfile: (profile) => {
    if (!profile) {
      set({
        selectedProfile: null,
        uploadedAudio: null,
        recordedAudio: null,
        activeVoiceDefaults: null,
        generationSettings: defaultsToSettings(SYSTEM_DEFAULTS),
        useGpu: SYSTEM_DEFAULTS.use_gpu,
      })
      return
    }

    const defaults = profile.generation_defaults
    if (defaults) {
      set({
        selectedProfile: profile,
        uploadedAudio: null,
        recordedAudio: null,
        activeVoiceDefaults: defaults,
        generationSettings: defaultsToSettings(defaults),
        useGpu: defaults.use_gpu,
      })
    } else {
      // Profile exists but has no saved defaults — fall back to system defaults.
      set({
        selectedProfile: profile,
        uploadedAudio: null,
        recordedAudio: null,
        activeVoiceDefaults: null,
        generationSettings: defaultsToSettings(SYSTEM_DEFAULTS),
        useGpu: SYSTEM_DEFAULTS.use_gpu,
      })
    }
  },

  setUploadedAudio: (audio) => set({ uploadedAudio: audio, selectedProfile: null }),
  setRecordedAudio: (audio) => set({ recordedAudio: audio, selectedProfile: null }),
  setActiveJob: (jobId, status) => set({ activeJobId: jobId, activeJobStatus: status ?? null }),
  setActiveJobStatus: (status) => set({ activeJobStatus: status }),

  updateGenerationSettings: (settings) =>
    set((state) => ({ generationSettings: { ...state.generationSettings, ...settings } })),

  setUseGpu: (value) => set({ useGpu: value }),

  setActiveVoiceDefaults: (defaults) => set({ activeVoiceDefaults: defaults }),

  resetSettings: () => {
    const ref = get().activeVoiceDefaults ?? SYSTEM_DEFAULTS
    set({
      generationSettings: defaultsToSettings(ref),
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
  resetAudio: () => set({ uploadedAudio: null, recordedAudio: null, selectedProfile: null }),
}))

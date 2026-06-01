import { create } from "zustand"
import type { VoiceProfile, JobStatus, GenerationSettings } from "@/types"

interface UploadedAudio {
  file: File
  url: string
  duration: number | null
}

interface AppState {
  selectedProfile: VoiceProfile | null
  uploadedAudio: UploadedAudio | null
  recordedAudio: UploadedAudio | null
  activeJobId: string | null
  activeJobStatus: JobStatus | null
  generationSettings: GenerationSettings
  voices: VoiceProfile[]

  setSelectedProfile: (profile: VoiceProfile | null) => void
  setUploadedAudio: (audio: UploadedAudio | null) => void
  setRecordedAudio: (audio: UploadedAudio | null) => void
  setActiveJob: (jobId: string | null, status?: JobStatus | null) => void
  setActiveJobStatus: (status: JobStatus | null) => void
  updateGenerationSettings: (settings: Partial<GenerationSettings>) => void
  setVoices: (voices: VoiceProfile[]) => void
  addVoice: (voice: VoiceProfile) => void
  removeVoice: (id: string) => void
  updateVoice: (id: string, updates: Partial<VoiceProfile>) => void
  resetAudio: () => void
}

export const useAppStore = create<AppState>((set) => ({
  selectedProfile: null,
  uploadedAudio: null,
  recordedAudio: null,
  activeJobId: null,
  activeJobStatus: null,
  generationSettings: {
    num_step: 32,
    guidance_scale: 2.0,
    speed: null,
    duration: null,
    t_shift: 0.1,
    denoise: true,
  },
  voices: [],

  setSelectedProfile: (profile) => set({ selectedProfile: profile, uploadedAudio: null, recordedAudio: null }),
  setUploadedAudio: (audio) => set({ uploadedAudio: audio, selectedProfile: null }),
  setRecordedAudio: (audio) => set({ recordedAudio: audio, selectedProfile: null }),
  setActiveJob: (jobId, status) => set({ activeJobId: jobId, activeJobStatus: status ?? null }),
  setActiveJobStatus: (status) => set({ activeJobStatus: status }),
  updateGenerationSettings: (settings) =>
    set((state) => ({ generationSettings: { ...state.generationSettings, ...settings } })),
  setVoices: (voices) => set({ voices }),
  addVoice: (voice) => set((state) => ({ voices: [voice, ...state.voices] })),
  removeVoice: (id) => set((state) => ({ voices: state.voices.filter((v) => v.id !== id) })),
  updateVoice: (id, updates) =>
    set((state) => ({
      voices: state.voices.map((v) => (v.id === id ? { ...v, ...updates } : v)),
    })),
  resetAudio: () => set({ uploadedAudio: null, recordedAudio: null, selectedProfile: null }),
}))

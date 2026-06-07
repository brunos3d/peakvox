import { create } from "zustand"
import type { VoiceProfile, JobStatus, GenerationSettings, VoiceGenerationDefaults, GenerationRequest, TemporaryVoice, VoiceResourceResponse } from "@/types"

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
  voice_design: [],
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
  /** A non-persisted preset voice selected via "Use in TTS". Mutually exclusive
   *  with selectedProfile — when temporaryVoice is set, selectedProfile is null. */
  temporaryVoice: TemporaryVoice | null
  uploadedAudio: UploadedAudio | null
  recordedAudio: UploadedAudio | null
  activeJobId: string | null
  activeJobStatus: JobStatus | null
  generationSettings: GenerationSettings
  // Structured Voice Design attributes for the next generation. Loaded from the
  // selected profile's defaults and editable per-generation; the flat OmniVoice
  // `instruct` string is derived from this at submit time.
  voiceDesign: string[]
  useGpu: boolean
  // The defaults that were loaded when the current profile was selected.
  // null means no profile is selected (or the profile has no saved defaults).
  activeVoiceDefaults: VoiceGenerationDefaults | null
  voices: VoiceProfile[]
  // The TTS language (OmniVoice id, or null = Auto). Lifted into the store so that
  // selecting a voice can auto-apply its language (Sub-project E), consistent with
  // how the API applies a voice's language at generation time.
  ttsLanguage: string | null
  // Persistent bottom-player audio + the text bound to the TTS canvas (lifted
  // into the store so History "Regenerate" can prefill it across routes).
  currentAudio: CurrentAudio | null
  ttsText: string
  // The most recent generation request — enables one-click "Regenerate" from
  // the persistent bottom player regardless of the current route.
  lastRequest: GenerationRequest | null
  // Preferred download format (client-side preference).
  outputFormat: "wav" | "mp3" | "ogg"
  // The model selected by the user for generation; null = platform default.
  selectedModelId: string | null

  setSelectedProfile: (profile: VoiceProfile | null) => void
  /** Construct a TemporaryVoice from a VoiceResourceResponse and select it.
   *  Clears any previously selected VoiceProfile. Never calls the backend. */
  selectTemporaryVoice: (resource: VoiceResourceResponse) => void
  /** Discard the currently selected temporary voice (if any). Resets to no selection. */
  discardTemporaryVoice: () => void
  /** After importing a preset, promote the temporary selection to a real profile
   *  while preserving the user's current settings. */
  promoteTemporaryToPersisted: (profile: VoiceProfile) => void
  setSelectedModelId: (id: string | null) => void
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
  temporaryVoice: null,
  uploadedAudio: null,
  recordedAudio: null,
  activeJobId: null,
  activeJobStatus: null,
  generationSettings: defaultsToSettings(SYSTEM_DEFAULTS),
  voiceDesign: SYSTEM_DEFAULTS.voice_design,
  useGpu: SYSTEM_DEFAULTS.use_gpu,
  activeVoiceDefaults: null,
  voices: [],
  ttsLanguage: null,
  currentAudio: null,
  ttsText: "",
  lastRequest: null,
  selectedModelId: null,
  outputFormat:
    (typeof window !== "undefined" && (localStorage.getItem("omnivoice:outputFormat") as "wav" | "mp3" | "ogg")) || "wav",

  setSelectedModelId: (id) => set({ selectedModelId: id }),
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
        generationSettings: defaultsToSettings(SYSTEM_DEFAULTS),
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
        generationSettings: defaultsToSettings(defaults),
        voiceDesign: defaults.voice_design ?? [],
        useGpu: defaults.use_gpu,
        // Auto-apply the voice's language (keep current when the voice has none).
        ttsLanguage: profile.language_code ?? get().ttsLanguage,
      })
    } else {
      // Profile exists but has no saved defaults — fall back to system defaults.
      set({
        selectedProfile: profile,
        temporaryVoice: null,
        uploadedAudio: null,
        recordedAudio: null,
        activeVoiceDefaults: null,
        generationSettings: defaultsToSettings(SYSTEM_DEFAULTS),
        voiceDesign: SYSTEM_DEFAULTS.voice_design,
        useGpu: SYSTEM_DEFAULTS.use_gpu,
        // Auto-apply the voice's language (keep current when the voice has none).
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
      generationSettings: defaultsToSettings(SYSTEM_DEFAULTS),
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
      generationSettings: defaultsToSettings(SYSTEM_DEFAULTS),
      voiceDesign: SYSTEM_DEFAULTS.voice_design,
      useGpu: SYSTEM_DEFAULTS.use_gpu,
    })
  },

  promoteTemporaryToPersisted: (profile) => {
    set({
      selectedProfile: profile,
      temporaryVoice: null,
      // Keep current settings intact — user may have tweaked them while
      // the voice was still temporary.
    })
  },

  setTtsLanguage: (language) => set({ ttsLanguage: language }),

  setUploadedAudio: (audio) => set({ uploadedAudio: audio, selectedProfile: null, temporaryVoice: null }),
  setRecordedAudio: (audio) => set({ recordedAudio: audio, selectedProfile: null, temporaryVoice: null }),
  setActiveJob: (jobId, status) => set({ activeJobId: jobId, activeJobStatus: status ?? null }),
  setActiveJobStatus: (status) => set({ activeJobStatus: status }),
  setVoiceDesign: (values) => set({ voiceDesign: values }),

  updateGenerationSettings: (settings) =>
    set((state) => ({ generationSettings: { ...state.generationSettings, ...settings } })),

  setUseGpu: (value) => set({ useGpu: value }),

  setActiveVoiceDefaults: (defaults) => set({ activeVoiceDefaults: defaults }),

  resetSettings: () => {
    const ref = get().activeVoiceDefaults ?? SYSTEM_DEFAULTS
    set({
      generationSettings: defaultsToSettings(ref),
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

/** Returns the currently active voice — either the persisted profile or the
 *  temporary preset selection. Consumers that need a specific type (e.g.
 *  edit/delete/GenerationSettings save) should read selectedProfile directly. */
export function useActiveVoice() {
  const profile = useAppStore((s) => s.selectedProfile)
  const temp = useAppStore((s) => s.temporaryVoice)
  return temp ?? profile
}

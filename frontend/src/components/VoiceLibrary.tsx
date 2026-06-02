"use client";

import { useState } from "react";
import { Plus, User, Trash2, Edit3, Play, StopCircle } from "lucide-react";
import { useQueryClient, useMutation } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  VoiceProfileAudioInput,
  AudioInputResult,
} from "@/components/VoiceProfileAudioInput";
import {
  createVoice,
  updateVoice as updateVoiceApi,
  deleteVoice,
  getVoiceAudioUrl,
} from "@/lib/api";
import { useAppStore } from "@/store/use-store";
import { useVoices } from "@/hooks/use-generation";
import type { VoiceProfile } from "@/types";

const LANGUAGES = [
  "Auto",
  "English",
  "Portuguese",
  "Spanish",
  "French",
  "German",
  "Chinese",
  "Japanese",
];

function formatDuration(seconds: number | null): string {
  if (!seconds) return "--";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function VoiceLibrary() {
  const { data: voices, isLoading } = useVoices();
  const queryClient = useQueryClient();
  const setSelectedProfile = useAppStore((s) => s.setSelectedProfile);
  const selectedProfile = useAppStore((s) => s.selectedProfile);

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editingProfile, setEditingProfile] = useState<VoiceProfile | null>(
    null,
  );
  const [playingId, setPlayingId] = useState<string | null>(null);

  // Create form state
  const [createForm, setCreateForm] = useState({
    name: "",
    transcript: "",
    language: "Auto",
  });
  const [createAudio, setCreateAudio] = useState<AudioInputResult | null>(null);

  // Edit form state
  const [editForm, setEditForm] = useState({
    name: "",
    transcript: "",
    language: "Auto",
  });
  const [editAudio, setEditAudio] = useState<AudioInputResult | null>(null);

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteVoice(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["voices"] }),
  });

  const createMutation = useMutation({
    mutationFn: (formData: FormData) => createVoice(formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["voices"] });
      setIsCreateOpen(false);
      setCreateForm({ name: "", transcript: "", language: "Auto" });
      setCreateAudio(null);
    },
  });

  const editMutation = useMutation({
    mutationFn: ({ id, formData }: { id: string; formData: FormData }) =>
      updateVoiceApi(id, formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["voices"] });
      setIsEditOpen(false);
      setEditingProfile(null);
      setEditAudio(null);
    },
  });

  const handleCreate = () => {
    if (!createForm.name || !createAudio?.isValid) return;
    const fd = new FormData();
    fd.append("name", createForm.name);
    fd.append("transcript", createForm.transcript);
    fd.append(
      "language",
      createForm.language === "Auto" ? "" : createForm.language,
    );
    fd.append("file", createAudio.file);
    fd.append("crop_start", String(createAudio.cropStart));
    fd.append("crop_end", String(createAudio.cropEnd));
    createMutation.mutate(fd);
  };

  const openEdit = (profile: VoiceProfile, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingProfile(profile);
    setEditForm({
      name: profile.name,
      transcript: profile.transcript || "",
      language: profile.language || "Auto",
    });
    setEditAudio(null);
    setIsEditOpen(true);
  };

  const handleEditSave = () => {
    if (!editingProfile || !editForm.name) return;
    // If new audio is being set, it must be valid
    if (editAudio !== null && !editAudio.isValid) return;

    const fd = new FormData();
    fd.append("name", editForm.name);
    fd.append("transcript", editForm.transcript);
    fd.append(
      "language",
      editForm.language === "Auto" ? "" : editForm.language,
    );
    if (editAudio) {
      fd.append("file", editAudio.file);
      fd.append("crop_start", String(editAudio.cropStart));
      fd.append("crop_end", String(editAudio.cropEnd));
    }
    editMutation.mutate({ id: editingProfile.id, formData: fd });
  };

  const previewAudio = (profile: VoiceProfile) => {
    if (playingId === profile.id) {
      setPlayingId(null);
    } else {
      setPlayingId(profile.id);
    }
  };

  const isCreateValid = !!createForm.name && !!createAudio?.isValid;
  const isEditValid =
    !!editForm.name && (editAudio === null || editAudio.isValid);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">Voice Library</h3>

        {/* ── Create Dialog ── */}
        <Dialog
          open={isCreateOpen}
          onOpenChange={(open) => {
            setIsCreateOpen(open);
            if (!open) {
              setCreateForm({ name: "", transcript: "", language: "Auto" });
              setCreateAudio(null);
            }
          }}
        >
          <DialogTrigger asChild>
            <Button variant="outline" size="sm" className="gap-1">
              <Plus className="h-3 w-3" /> New
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-xl">
            <DialogHeader>
              <DialogTitle>Create Voice Profile</DialogTitle>
              <DialogDescription>
                Upload or record a voice sample. Files longer than 10s will open
                a crop editor.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Name</Label>
                <Input
                  placeholder="Voice name"
                  value={createForm.name}
                  onChange={(e) =>
                    setCreateForm({ ...createForm, name: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label>
                  Reference Transcript{" "}
                  <span className="text-muted-foreground font-normal">
                    (optional)
                  </span>
                </Label>
                <Textarea
                  placeholder="Transcript of the reference audio — improves cloning accuracy."
                  value={createForm.transcript}
                  onChange={(e) =>
                    setCreateForm({ ...createForm, transcript: e.target.value })
                  }
                  rows={2}
                />
              </div>
              <div className="space-y-2">
                <Label>Language</Label>
                <Select
                  value={createForm.language}
                  onValueChange={(v) =>
                    setCreateForm({ ...createForm, language: v })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {LANGUAGES.map((lang) => (
                      <SelectItem key={lang} value={lang}>
                        {lang}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Audio Sample</Label>
                <VoiceProfileAudioInput onChange={setCreateAudio} />
              </div>
              {createMutation.isError && (
                <p className="text-xs text-destructive">
                  {(createMutation.error as Error)?.message ??
                    "Failed to create profile"}
                </p>
              )}
              <Button
                className="w-full"
                onClick={handleCreate}
                disabled={!isCreateValid || createMutation.isPending}
              >
                {createMutation.isPending ? "Creating…" : "Create Profile"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>

        {/* ── Edit Dialog ── */}
        <Dialog
          open={isEditOpen}
          onOpenChange={(open) => {
            setIsEditOpen(open);
            if (!open) {
              setEditingProfile(null);
              setEditAudio(null);
            }
          }}
        >
          <DialogContent className="sm:max-w-xl">
            <DialogHeader>
              <DialogTitle>Edit Voice Profile</DialogTitle>
              <DialogDescription>
                Update profile details or replace the audio sample.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Name</Label>
                <Input
                  placeholder="Voice name"
                  value={editForm.name}
                  onChange={(e) =>
                    setEditForm({ ...editForm, name: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label>
                  Reference Transcript{" "}
                  <span className="text-muted-foreground font-normal">
                    (optional)
                  </span>
                </Label>
                <Textarea
                  placeholder="Transcript of the reference audio — improves cloning accuracy."
                  value={editForm.transcript}
                  onChange={(e) =>
                    setEditForm({ ...editForm, transcript: e.target.value })
                  }
                  rows={2}
                />
              </div>
              <div className="space-y-2">
                <Label>Language</Label>
                <Select
                  value={editForm.language}
                  onValueChange={(v) =>
                    setEditForm({ ...editForm, language: v })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {LANGUAGES.map((lang) => (
                      <SelectItem key={lang} value={lang}>
                        {lang}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>
                  Replace Audio{" "}
                  <span className="text-muted-foreground font-normal">
                    (optional)
                  </span>
                </Label>
                <VoiceProfileAudioInput onChange={setEditAudio} />
              </div>
              {editMutation.isError && (
                <p className="text-xs text-destructive">
                  {(editMutation.error as Error)?.message ??
                    "Failed to save changes"}
                </p>
              )}
              <Button
                className="w-full"
                onClick={handleEditSave}
                disabled={!isEditValid || editMutation.isPending}
              >
                {editMutation.isPending ? "Saving…" : "Save Changes"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* ── Voice list ── */}
      <ScrollArea className="h-[600px] pr-3">
        {isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-16 w-full rounded-lg" />
            ))}
          </div>
        ) : voices && voices.length > 0 ? (
          <div className="space-y-2">
            {voices.map((profile) => (
              <Card
                key={profile.id}
                className={`p-3 cursor-pointer transition-all hover:border-primary/50 ${
                  selectedProfile?.id === profile.id ? "border-primary" : ""
                }`}
                onClick={() => setSelectedProfile(profile)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 min-w-0">
                    <User className="h-4 w-4 shrink-0 text-muted-foreground" />
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">
                        {profile.name}
                      </p>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">
                          {formatDuration(profile.audio_duration)}
                        </span>
                        {profile.language && (
                          <Badge
                            variant="outline"
                            className="text-[10px] px-1 py-0"
                          >
                            {profile.language}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={(e) => {
                        e.stopPropagation();
                        previewAudio(profile);
                      }}
                    >
                      {playingId === profile.id ? (
                        <StopCircle className="h-3 w-3" />
                      ) : (
                        <Play className="h-3 w-3" />
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={(e) => openEdit(profile, e)}
                    >
                      <Edit3 className="h-3 w-3" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-destructive hover:text-destructive"
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteMutation.mutate(profile.id);
                      }}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
                {playingId === profile.id && (
                  <audio
                    src={getVoiceAudioUrl(profile.id)}
                    autoPlay
                    onEnded={() => setPlayingId(null)}
                    className="hidden"
                  />
                )}
              </Card>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground">
            <User className="h-8 w-8 mb-2 opacity-40" />
            <p className="text-sm">No voice profiles yet</p>
            <p className="text-xs">Create one to get started</p>
          </div>
        )}
      </ScrollArea>
    </div>
  );
}

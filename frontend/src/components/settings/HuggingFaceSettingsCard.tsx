"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { KeyRound, Eye, EyeOff, Check, ExternalLink, Loader2 } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import {
  fetchHuggingFaceStatus,
  saveHuggingFaceToken,
  deleteHuggingFaceToken,
} from "@/lib/api"
import { SettingsCard } from "@/components/settings/SettingsPanel"

const TOKENS_URL = "https://huggingface.co/settings/tokens"

export function HuggingFaceSettingsCard() {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ["hf-settings"],
    queryFn: fetchHuggingFaceStatus,
  })
  const configured = !!data?.configured

  const [token, setToken] = useState("")
  const [show, setShow] = useState(false)
  const [saved, setSaved] = useState(false)

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["hf-settings"] })

  const saveMutation = useMutation({
    mutationFn: (t: string) => saveHuggingFaceToken(t),
    onSuccess: () => {
      setToken("")
      setShow(false)
      setSaved(true)
      window.setTimeout(() => setSaved(false), 2500)
      invalidate()
    },
  })

  const removeMutation = useMutation({
    mutationFn: () => deleteHuggingFaceToken(),
    onSuccess: () => {
      setToken("")
      setShow(false)
      setSaved(false)
      invalidate()
    },
  })

  const pending = saveMutation.isPending || removeMutation.isPending
  const canSave = token.trim().length > 0 && !pending
  const error = saveMutation.error || removeMutation.error

  return (
    <SettingsCard
      icon={KeyRound}
      title="Hugging Face"
      description="Use your Hugging Face access token to increase download speed and avoid anonymous rate limits."
    >
      <div className="space-y-3">
        {configured && (
          <div className="flex items-center gap-2 text-sm text-emerald-500">
            <Check className="h-4 w-4" />
            <span>Token configured</span>
          </div>
        )}

        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Input
              type={show ? "text" : "password"}
              autoComplete="off"
              spellCheck={false}
              placeholder={configured ? "••••••••••••••••  (enter a new token to replace)" : "hf_…"}
              value={token}
              onChange={(e) => setToken(e.target.value)}
              disabled={pending}
              className="pr-10"
            />
            <button
              type="button"
              onClick={() => setShow((s) => !s)}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              aria-label={show ? "Hide token" : "Show token"}
              tabIndex={-1}
            >
              {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>

          <Button onClick={() => saveMutation.mutate(token)} disabled={!canSave}>
            {saveMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              "Save"
            )}
          </Button>

          {configured && (
            <Button
              variant="outline"
              onClick={() => removeMutation.mutate()}
              disabled={pending}
            >
              {removeMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                "Remove"
              )}
            </Button>
          )}
        </div>

        {saved && <p className="text-sm text-emerald-500">Saved.</p>}
        {error && (
          <p className="text-sm text-destructive">
            {(error as Error).message || "Something went wrong. Please try again."}
          </p>
        )}
        {isLoading && <p className="text-caption">Checking…</p>}

        <p className="text-caption">
          Need a token?{" "}
          <a
            href={TOKENS_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-primary underline-offset-4 hover:underline"
          >
            Create a Hugging Face access token
            <ExternalLink className="h-3 w-3" />
          </a>
        </p>
      </div>
    </SettingsCard>
  )
}

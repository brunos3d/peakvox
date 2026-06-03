"use client"

import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { KeyRound, Plus, Trash2, Copy, Check, AlertTriangle } from "lucide-react"
import { PageLayout } from "@/components/shell/PageLayout"
import { PageHeader } from "@/components/shell/PageHeader"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { EmptyState } from "@/components/common/EmptyState"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import { fetchApiKeys, createApiKey, deleteApiKey } from "@/lib/api"
import type { ApiKeyCreateResponse } from "@/types"

export default function ApiKeysPage() {
  const queryClient = useQueryClient()
  const { data: keys = [], isLoading } = useQuery({ queryKey: ["api-keys"], queryFn: fetchApiKeys })

  const [createOpen, setCreateOpen] = useState(false)
  const [name, setName] = useState("")
  const [newKey, setNewKey] = useState<ApiKeyCreateResponse | null>(null)
  const [copied, setCopied] = useState(false)

  const createMutation = useMutation({
    mutationFn: (n: string) => createApiKey(n),
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: ["api-keys"] })
      setNewKey(created)
      setCreateOpen(false)
      setName("")
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteApiKey(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["api-keys"] }),
  })

  const copyKey = () => {
    if (!newKey) return
    navigator.clipboard?.writeText(newKey.key).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }

  return (
    <PageLayout>
      <div className="mx-auto max-w-3xl">
        <PageHeader
          title="API Keys"
          description="Keys authenticate requests to the public API. The full key is shown only once."
          actions={
            <Button className="gap-2" onClick={() => setCreateOpen(true)}>
              <Plus className="h-4 w-4" /> Create key
            </Button>
          }
        />

        {newKey && (
          <Card className="mt-6 border-warning/40 bg-warning/5">
            <CardContent className="space-y-2 pt-6">
              <p className="flex items-center gap-2 text-sm font-medium text-warning">
                <AlertTriangle className="h-4 w-4" /> Copy your key now — it won&apos;t be shown again.
              </p>
              <button
                type="button"
                onClick={copyKey}
                className="flex w-full items-center justify-between gap-2 rounded-lg border border-border bg-surface px-3 py-2 text-sm font-mono hover:bg-surface-2"
              >
                <span className="truncate">{newKey.key}</span>
                {copied ? <Check className="h-4 w-4 shrink-0 text-success" /> : <Copy className="h-4 w-4 shrink-0 text-muted-foreground" />}
              </button>
              <Button variant="ghost" size="sm" onClick={() => setNewKey(null)}>Done</Button>
            </CardContent>
          </Card>
        )}

        <div className="mt-6">
          {!isLoading && keys.length === 0 ? (
            <EmptyState
              icon={KeyRound}
              title="No API keys yet"
              description="Create a key to start using the OmniVoice API."
              action={<Button className="gap-2" onClick={() => setCreateOpen(true)}><Plus className="h-4 w-4" /> Create key</Button>}
            />
          ) : (
            <div className="divide-y divide-border rounded-xl border border-border bg-surface">
              {keys.map((k) => (
                <div key={k.id} className="flex items-center justify-between gap-3 px-4 py-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">{k.name}</p>
                    <p className="text-caption font-mono">
                      {k.prefix}••••
                      {k.last_used_at ? ` · last used ${new Date(k.last_used_at).toLocaleDateString()}` : " · never used"}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Badge variant={k.status === "active" ? "secondary" : "outline"} className="capitalize">{k.status}</Badge>
                    {k.status === "active" && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-error hover:text-error"
                        onClick={() => deleteMutation.mutate(k.id)}
                        title="Revoke key"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Create API key</DialogTitle>
            <DialogDescription>Give the key a name so you can recognize it later.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Input
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Production server"
              onKeyDown={(e) => { if (e.key === "Enter" && name.trim()) createMutation.mutate(name.trim()) }}
            />
            {createMutation.isError && (
              <p className="text-xs text-error">{(createMutation.error as Error)?.message ?? "Failed to create key"}</p>
            )}
            <Button
              className="w-full"
              disabled={!name.trim() || createMutation.isPending}
              onClick={() => createMutation.mutate(name.trim())}
            >
              {createMutation.isPending ? "Creating…" : "Create key"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </PageLayout>
  )
}

"use client"

import { BookOpen, Lightbulb, Mic2, Megaphone, Newspaper, Youtube, type LucideIcon } from "lucide-react"

interface QuickPrompt {
  label: string
  icon: LucideIcon
  text: string
}

const PROMPTS: QuickPrompt[] = [
  {
    label: "Narrate a story",
    icon: BookOpen,
    text: "Once upon a time, in a valley wrapped in morning mist, a small lantern flickered to life — and with it, an adventure that no one in the village would ever forget.",
  },
  {
    label: "Explain a concept",
    icon: Lightbulb,
    text: "Let's break this down simply. Think of it like water flowing downhill: it always follows the path of least resistance, and once you see that pattern, everything else starts to make sense.",
  },
  {
    label: "Podcast introduction",
    icon: Mic2,
    text: "Welcome back to the show. I'm so glad you're here. Today we've got a fascinating conversation lined up, so grab a coffee, settle in, and let's get started.",
  },
  {
    label: "Advertisement",
    icon: Megaphone,
    text: "Introducing the all-new experience you've been waiting for. Faster, smarter, and designed just for you. Try it today — because you deserve nothing less than extraordinary.",
  },
  {
    label: "News report",
    icon: Newspaper,
    text: "Good evening. Our top story tonight: communities across the region are coming together in an inspiring show of support, and we have the full details for you right now.",
  },
  {
    label: "YouTube narration",
    icon: Youtube,
    text: "Hey everyone, welcome back to the channel! If you're new here, consider subscribing. Today we're diving into something I'm really excited to share with you.",
  },
]

export function QuickPrompts({ onSelect }: { onSelect: (text: string) => void }) {
  return (
    <div className="flex flex-wrap gap-2">
      {PROMPTS.map((p) => {
        const Icon = p.icon
        return (
          <button
            key={p.label}
            type="button"
            onClick={() => onSelect(p.text)}
            className="inline-flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
          >
            <Icon className="h-4 w-4 text-primary" />
            {p.label}
          </button>
        )
      })}
    </div>
  )
}

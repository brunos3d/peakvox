"use client"

import { useVoices } from "@/hooks/use-generation"

/**
 * Client island that warms the voices query once for the whole app (pages read
 * the result from the store). Rendered inside the shell so the preload survives
 * route changes, but kept as its own component so the layout frame can be a
 * Server Component. Renders nothing.
 */
export function VoicesPreloader() {
  useVoices()
  return null
}

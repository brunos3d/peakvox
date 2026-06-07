"use client"

import { ChevronDown, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"

interface PaginationControlsProps {
  hasNextPage: boolean
  isFetchingNextPage: boolean
  onLoadMore: () => void
}

export function PaginationControls({
  hasNextPage,
  isFetchingNextPage,
  onLoadMore,
}: PaginationControlsProps) {
  if (!hasNextPage) return null

  return (
    <div className="flex justify-center pt-2 pb-2">
      <Button
        variant="outline"
        size="sm"
        className="gap-2"
        onClick={onLoadMore}
        disabled={isFetchingNextPage}
      >
        {isFetchingNextPage ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5" />
        )}
        {isFetchingNextPage ? "Loading…" : "Load more"}
      </Button>
    </div>
  )
}

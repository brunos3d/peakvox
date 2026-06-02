"use client";

import { Cpu } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

/**
 * Model picker. OmniVoice is currently the only model; this is feature-ready
 * for additional models without changing the surrounding layout.
 */
export function ModelSelector() {
  return (
    <div className="space-y-2">
      <p className="text-caption uppercase tracking-wide">Model</p>
      <Select defaultValue="omnivoice">
        <SelectTrigger>
          <div className="flex items-center gap-2">
            <Cpu className="h-4 w-4 text-primary" />
            <SelectValue />
          </div>
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="omnivoice">OmniVoice</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
}

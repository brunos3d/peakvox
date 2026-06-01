"use client";

import { useEffect, useRef, useState } from "react";
import { Play, Pause, ZoomIn, ZoomOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";

const MAX_CLIP = 10;
const MIN_CLIP = 3;
const INITIAL_ZOOM = 50;

interface AudioCropEditorProps {
  audioUrl: string;
  totalDuration: number;
  onCropChange: (start: number, end: number, isValid: boolean) => void;
}

function fmt(s: number): string {
  const m = Math.floor(s / 60);
  const sec = (s % 60).toFixed(1).padStart(4, "0");
  return `${m}:${sec}`;
}

export function AudioCropEditor({
  audioUrl,
  totalDuration,
  onCropChange,
}: AudioCropEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<any>(null);
  const regionRef = useRef<any>(null);

  // Stable refs so handlers never go stale
  const onCropChangeRef = useRef(onCropChange);
  onCropChangeRef.current = onCropChange;
  const [zoom, setZoom] = useState(INITIAL_ZOOM);

  const [isReady, setIsReady] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [cropStart, setCropStart] = useState(0);
  const [cropEnd, setCropEnd] = useState(Math.min(MAX_CLIP, totalDuration));
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (wsRef.current) return;
    if (!containerRef.current) return;

    let destroyed = false;

    const init = async () => {
      const { default: WaveSurfer } = await import("wavesurfer.js");
      const { default: RegionsPlugin } =
        await import("wavesurfer.js/plugins/regions");

      if (destroyed || !containerRef.current) return;

      const regionsPlugin = RegionsPlugin.create();

      const ws = WaveSurfer.create({
        container: containerRef.current,
        waveColor: "rgba(148, 163, 184, 0.45)",
        progressColor: "rgba(99, 102, 241, 0.8)",
        cursorColor: "rgba(255, 255, 255, 0.75)",
        cursorWidth: 2,
        height: 80,
        width: containerRef.current.clientWidth,
        normalize: true,
        plugins: [regionsPlugin],
      });
      wsRef.current = ws;
      if (destroyed) {
        ws.destroy();
        wsRef.current = null;
        return;
      }

      ws.load(audioUrl);

      ws.on("ready", () => {
        if (destroyed) return;

        ws.zoom(zoom);

        setIsReady(true);

        const initialEnd = Math.min(MAX_CLIP, totalDuration);
        const region = regionsPlugin.addRegion({
          start: 0,
          end: initialEnd,
          color: "rgba(99, 102, 241, 0.18)",
          drag: true,
          resize: true,
          minLength: MIN_CLIP,
          maxLength: MAX_CLIP,
        });
        regionRef.current = region;

        setCropStart(0);
        setCropEnd(initialEnd);
        setValidationError(null);
        onCropChangeRef.current(0, initialEnd, true);

        region.on("update", () => {
          setCropStart(region.start);
          setCropEnd(region.end);
        });

        region.on("update-end", () => {
          const s = region.start;
          const e = region.end;
          const len = e - s;
          let error: string | null = null;
          let valid = true;
          if (len > MAX_CLIP) {
            error = `Reference voice samples must be ${MAX_CLIP} seconds or shorter.`;
            valid = false;
          } else if (len < MIN_CLIP) {
            error = `Minimum duration is ${MIN_CLIP} seconds.`;
            valid = false;
          }
          setValidationError(error);
          onCropChangeRef.current(s, e, valid);
        });
      });

      ws.on("audioprocess", (t: number) => setCurrentTime(t));
      ws.on("play", () => setIsPlaying(true));
      ws.on("pause", () => setIsPlaying(false));
      ws.on("finish", () => setIsPlaying(false));
    };

    init();

    return () => {
      destroyed = true;
      if (wsRef.current) {
        wsRef.current.destroy();
        wsRef.current = null;
      }
      regionRef.current = null;
    };
  }, [audioUrl]); // eslint-disable-line react-hooks/exhaustive-deps

  const handlePlayPause = () => {
    if (!wsRef.current || !isReady) return;
    if (isPlaying) {
      wsRef.current.pause();
    } else {
      regionRef.current ? regionRef.current.play() : wsRef.current.play();
    }
  };

  const handleZoom = (value: number) => {
    setZoom(value);
    wsRef.current?.zoom(value);
  };

  const clipLen = cropEnd - cropStart;
  const lenColor =
    clipLen > MAX_CLIP
      ? "text-destructive"
      : clipLen < MIN_CLIP
        ? "text-amber-500"
        : "text-primary";

  return (
    <div className="space-y-2 rounded-lg border bg-card/50 p-3">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>
          Drag the highlighted region — max {MAX_CLIP}s, min {MIN_CLIP}s
        </span>
        <span>Total: {fmt(totalDuration)}</span>
      </div>

      <div
        ref={containerRef}
        className="w-full overflow-hidden rounded bg-muted/30"
        style={{ minHeight: 80 }}
      />

      {!isReady && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="h-3 w-3 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          Loading waveform…
        </div>
      )}

      {validationError && (
        <p className="text-xs font-medium text-destructive">
          {validationError}
        </p>
      )}

      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="icon"
            className="h-7 w-7"
            onClick={handlePlayPause}
            disabled={!isReady}
          >
            {isPlaying ? (
              <Pause className="h-3 w-3" />
            ) : (
              <Play className="h-3 w-3" />
            )}
          </Button>
          <span className="w-12 text-xs tabular-nums text-muted-foreground">
            {fmt(currentTime)}
          </span>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="tabular-nums text-muted-foreground">
            {fmt(cropStart)} → {fmt(cropEnd)}
          </span>
          <span className={`font-semibold tabular-nums ${lenColor}`}>
            {clipLen.toFixed(1)}s
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <ZoomOut className="h-3 w-3 text-muted-foreground" />
          <Slider
            min={10}
            max={300}
            step={10}
            value={[zoom]}
            onValueChange={([v]) => handleZoom(v)}
            className="w-20"
          />
          <ZoomIn className="h-3 w-3 text-muted-foreground" />
        </div>
      </div>
    </div>
  );
}

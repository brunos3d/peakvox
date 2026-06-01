import json
import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MAX_REFERENCE_DURATION = 10.0
MIN_CROP_DURATION = 3.0


class AudioPreprocessingError(ValueError):
    """Raised when audio validation or processing fails."""


def _ffprobe(path: Path, entries: str, section: str = "format") -> str:
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-show_entries", f"{section}={entries}",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise AudioPreprocessingError(
            f"ffprobe failed on {path.name}: {result.stderr.decode(errors='replace')[-200:]}"
        )
    return result.stdout.decode().strip()


def probe_duration(path: Path) -> float:
    """Return audio duration in seconds using ffprobe."""
    raw = _ffprobe(path, "duration", section="format")
    # Some containers (e.g. OGG) don't report duration in the format section; try stream
    if not raw or raw == "N/A":
        raw = _ffprobe(path, "duration", section="stream")
        raw = raw.splitlines()[0].strip() if raw else ""
    try:
        return float(raw)
    except (ValueError, TypeError):
        raise AudioPreprocessingError(
            f"Could not determine audio duration for '{path.name}'"
        )


def probe_format_name(path: Path) -> str:
    """Return the primary format name (e.g. 'mp3', 'ogg', 'wav')."""
    try:
        raw = _ffprobe(path, "format_name", section="format")
        return raw.split(",")[0].strip() if raw else "unknown"
    except AudioPreprocessingError:
        return "unknown"


def validate_crop(total_duration: float, crop_start: float, crop_end: float) -> None:
    """Raise AudioPreprocessingError if the crop parameters are invalid."""
    if crop_start < 0:
        raise AudioPreprocessingError("crop_start must be >= 0")
    if crop_end <= crop_start:
        raise AudioPreprocessingError("crop_end must be greater than crop_start")
    if crop_start > total_duration:
        raise AudioPreprocessingError(
            f"crop_start ({crop_start:.2f}s) exceeds audio duration ({total_duration:.2f}s)"
        )
    # Allow a small tolerance for floating-point imprecision from the frontend
    if crop_end > total_duration + 0.5:
        raise AudioPreprocessingError(
            f"crop_end ({crop_end:.2f}s) exceeds audio duration ({total_duration:.2f}s)"
        )
    crop_len = crop_end - crop_start
    if crop_len > MAX_REFERENCE_DURATION + 0.05:
        raise AudioPreprocessingError(
            f"Reference voice samples must be {int(MAX_REFERENCE_DURATION)} seconds or shorter "
            f"(selected region is {crop_len:.2f}s)"
        )
    if crop_len < MIN_CROP_DURATION - 0.05:
        raise AudioPreprocessingError(
            f"Reference sample must be at least {int(MIN_CROP_DURATION)} seconds "
            f"(selected region is {crop_len:.2f}s)"
        )


def process_audio(
    source_path: Path,
    output_path: Path,
    crop_start: float,
    crop_end: float,
    source_filename: str = "",
) -> dict:
    """
    Trim [crop_start, crop_end] from source_path and normalize to:
        WAV / mono / 16 kHz / PCM 16-bit

    Writes the result to output_path. Returns a metadata dict.
    Raises AudioPreprocessingError on any validation or conversion failure.
    """
    total_duration = probe_duration(source_path)
    source_format = probe_format_name(source_path)

    validate_crop(total_duration, crop_start, crop_end)

    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(source_path),
            "-ss", f"{crop_start:.6f}",
            "-to", f"{crop_end:.6f}",
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            "-vn",              # discard video streams (e.g. MP4 with video track)
            str(output_path),
        ],
        capture_output=True,
        timeout=120,
    )

    if result.returncode != 0:
        logger.error("ffmpeg stderr: %s", result.stderr.decode(errors="replace"))
        raise AudioPreprocessingError(
            "Audio conversion failed. Ensure the file is a valid audio file."
        )

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise AudioPreprocessingError("Conversion produced no output file")

    # Final backend enforcement: reject if the normalized output still exceeds the limit
    output_duration = probe_duration(output_path)
    if output_duration > MAX_REFERENCE_DURATION + 0.5:
        output_path.unlink(missing_ok=True)
        raise AudioPreprocessingError(
            f"Processed audio is {output_duration:.2f}s — backend limit is "
            f"{int(MAX_REFERENCE_DURATION)}s"
        )

    return {
        "source_format": source_format,
        "source_filename": source_filename,
        "duration": round(output_duration, 3),
        "sample_rate": 16000,
        "channels": 1,
        "codec": "pcm_s16le",
        "crop_start": round(crop_start, 3),
        "crop_end": round(crop_end, 3),
    }


def write_metadata_json(path: Path, profile_id: str, name: str, meta: dict, **extra) -> None:
    """Write (or overwrite) the metadata.json file for a voice profile directory."""
    from datetime import datetime, timezone
    data = {
        "id": profile_id,
        "name": name,
        "language": extra.get("language"),
        "duration": meta["duration"],
        "sample_rate": meta["sample_rate"],
        "channels": meta["channels"],
        "codec": meta["codec"],
        "transcript": extra.get("transcript"),
        "source_format": meta["source_format"],
        "created_at": extra.get("created_at", datetime.now(timezone.utc).isoformat()),
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

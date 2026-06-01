import io
import logging
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)


def load_audio_as_wav(source: bytes | str | Path, target_sr: int = 24000) -> bytes:
    """Convert any audio format to WAV bytes at target_sr."""
    if isinstance(source, (str, Path)):
        audio, sr = librosa.load(str(source), sr=None, mono=True)
    else:
        audio, sr = librosa.load(io.BytesIO(source), sr=None, mono=True)

    if sr != target_sr:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=target_sr)

    buf = io.BytesIO()
    sf.write(buf, audio, target_sr, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def get_audio_duration(path: str | Path) -> float:
    """Return duration in seconds."""
    try:
        info = sf.info(str(path))
        return info.duration
    except Exception:
        try:
            y, sr = librosa.load(str(path), sr=None)
            return float(len(y) / sr)
        except Exception as e:
            logger.warning(f"Could not get audio duration: {e}")
            return 0.0


def save_numpy_as_wav(audio: np.ndarray, path: str | Path, sample_rate: int) -> float:
    """Save numpy audio array to WAV. Returns duration in seconds."""
    sf.write(str(path), audio, sample_rate, subtype="PCM_16")
    return float(len(audio) / sample_rate)

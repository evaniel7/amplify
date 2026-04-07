from pathlib import Path

import librosa
import numpy as np


SUPPORTED_FORMATS = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}


def validate_audio_path(file_path: str | Path) -> Path:
    path = Path(file_path).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(f"The file '{file_path}' does not exist.")

    if not path.is_file():
        raise ValueError(f"'{file_path}' is not a file.")

    if path.suffix.lower() not in SUPPORTED_FORMATS:
        supported = ", ".join(sorted(SUPPORTED_FORMATS))
        raise ValueError(f"Unsupported format '{path.suffix}'. Amplify accepts: {supported}.")

    return path


def load_sample(file_path: str | Path) -> tuple[np.ndarray, int]:
    """
    Load one audio file as mono audio at its original sample rate.

    Returns:
        (signal, sr)
    Raises:
        FileNotFoundError, ValueError, RuntimeError
    """
    path = validate_audio_path(file_path)

    try:
        signal, sr = librosa.load(str(path), sr=None, mono=True)
    except Exception as e:
        raise RuntimeError(f"Audio decoding failed: {e}") from e

    if signal is None or len(signal) == 0:
        raise RuntimeError(f"Audio file '{path}' loaded as empty.")

    return signal.astype(np.float32, copy=False), int(sr)


def get_sample_info(file_path: str | Path) -> dict:
    """
    Convenience helper for CLI display or debugging.
    """
    signal, sr = load_sample(file_path)
    duration = len(signal) / sr

    return {
        "path": str(Path(file_path).expanduser().resolve()),
        "sample_rate": sr,
        "samples": len(signal),
        "duration_seconds": duration,
        "channels": 1,
    }
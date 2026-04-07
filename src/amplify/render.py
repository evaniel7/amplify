from pathlib import Path

import librosa
import numpy as np
import soundfile as sf


def apply_scale(audio: np.ndarray, factor: float, preserve_pitch: bool) -> np.ndarray:
    """
    Scale audio in time.

    factor > 1.0  -> shorter / faster
    factor < 1.0  -> longer / slower

    If preserve_pitch is True, use time-stretching.
    If preserve_pitch is False, resample to change both speed and pitch,
    then resample back so the project still uses one consistent sample rate.
    """
    if factor <= 0:
        raise ValueError("Scale factor must be greater than 0.")

    if preserve_pitch:
        return librosa.effects.time_stretch(audio, rate=factor)

    # Change speed + pitch by resampling the waveform length directly.
    # This avoids returning audio tied to a different project sample rate.
    target_len = max(1, int(round(len(audio) / factor)))
    return librosa.resample(audio, orig_sr=len(audio), target_sr=target_len)


def apply_loop(
    audio: np.ndarray,
    *,
    count: int | None = None,
    bpm: float | None = None,
    bars: int | None = None,
    sr: int,
    beats_per_bar: int = 4,
) -> np.ndarray:
    """
    Loop audio either by explicit count or by musical length.
    """
    if len(audio) == 0:
        return audio

    if count is not None:
        if count < 1:
            raise ValueError("Loop count must be at least 1.")
        return np.tile(audio, count)

    if bpm is not None and bars is not None:
        if bpm <= 0:
            raise ValueError("BPM must be greater than 0.")
        if bars < 1:
            raise ValueError("Bars must be at least 1.")

        seconds_per_bar = (60.0 / bpm) * beats_per_bar
        target_seconds = bars * seconds_per_bar
        target_samples = max(1, int(round(target_seconds * sr)))

        repeats = int(np.ceil(target_samples / len(audio)))
        looped = np.tile(audio, repeats)
        return looped[:target_samples]

    raise ValueError("Loop operation requires either count or both bpm and bars.")


def apply_gain_db(audio: np.ndarray, gain_db: float) -> np.ndarray:
    """
    Apply gain in decibels.
    """
    linear = 10 ** (gain_db / 20.0)
    return audio * linear


def to_mono(audio: np.ndarray) -> np.ndarray:
    """
    Ensure audio is a 1D mono numpy array.
    """
    audio = np.asarray(audio)

    if audio.ndim == 1:
        return audio.astype(np.float32, copy=False)

    # Average channels if multi-channel slips through.
    return np.mean(audio, axis=0).astype(np.float32, copy=False)


def load_asset_audio(asset_path: str, target_sr: int | None = None) -> tuple[np.ndarray, int]:
    """
    Load one asset. If target_sr is provided, resample into the project rate.
    """
    audio, sr = librosa.load(asset_path, sr=target_sr, mono=True)
    return to_mono(audio), (target_sr or sr)


def build_asset_map(cfg_data: dict) -> dict[str, dict]:
    assets = cfg_data.get("assets", [])
    return {asset["id"]: asset for asset in assets}


def render_item(item: dict, asset_map: dict[str, dict], project_sr: int) -> tuple[np.ndarray, int]:
    """
    Render one timeline item into a processed clip plus its start offset in samples.
    """
    asset_id = item["asset"]
    if asset_id not in asset_map:
        raise ValueError(f"Timeline item references missing asset '{asset_id}'.")

    asset = asset_map[asset_id]
    audio, _ = load_asset_audio(asset["path"], target_sr=project_sr)

    for op in item.get("ops", []):
        op_type = op.get("type")

        if op_type == "scale":
            audio = apply_scale(
                audio,
                factor=float(op["factor"]),
                preserve_pitch=bool(op.get("preserve_pitch", False)),
            )
        elif op_type == "loop":
            audio = apply_loop(
                audio,
                count=op.get("count"),
                bpm=op.get("bpm"),
                bars=op.get("bars"),
                sr=project_sr,
            )
        else:
            raise ValueError(f"Unsupported operation type: {op_type}")

    gain_db = float(item.get("gain_db", 0.0))
    audio = apply_gain_db(audio, gain_db)

    start_seconds = float(item.get("start", 0.0))
    if start_seconds < 0:
        raise ValueError("Timeline item start time cannot be negative.")

    start_sample = int(round(start_seconds * project_sr))
    return audio, start_sample


def mix_timeline(rendered_items: list[tuple[np.ndarray, int]]) -> np.ndarray:
    """
    Mix all rendered clips into one output buffer.
    """
    if not rendered_items:
        return np.zeros(1, dtype=np.float32)

    total_length = max(start + len(audio) for audio, start in rendered_items)
    output = np.zeros(total_length, dtype=np.float32)

    for audio, start in rendered_items:
        end = start + len(audio)
        output[start:end] += audio

    return output


def normalize_audio(audio: np.ndarray) -> np.ndarray:
    peak = np.max(np.abs(audio))
    if peak > 0:
        return audio / peak
    return audio


def render(cfg_data: dict) -> tuple[np.ndarray, int]:
    """
    Render the full project to a mono output buffer and sample rate.
    """
    project = cfg_data.get("project", {})
    project_sr = int(project.get("sample_rate", 44100))

    asset_map = build_asset_map(cfg_data)
    timeline = cfg_data.get("timeline", [])

    rendered_items: list[tuple[np.ndarray, int]] = []
    for item in timeline:
        rendered_items.append(render_item(item, asset_map, project_sr))

    output = mix_timeline(rendered_items)

    mix_cfg = cfg_data.get("mix", {})
    if mix_cfg.get("normalize", True):
        output = normalize_audio(output)

    return output.astype(np.float32, copy=False), project_sr


def export(cfg_data: dict) -> Path:
    """
    Render and write the output file.
    """
    audio, sr = render(cfg_data)

    export_cfg = cfg_data.get("export", {})
    out_path = Path(export_cfg.get("path", "out.wav"))
    out_path.parent.mkdir(parents=True, exist_ok=True)

    sf.write(out_path, audio, sr)
    return out_path
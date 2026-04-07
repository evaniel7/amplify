# mixer.py
# ---------------------------------------------------------------------------
# Mixer module for Amplify
#
# Responsibilities:
#   - Load decoded audio arrays for each timeline item
#   - Apply any queued ops (scale, loop) to each track
#   - Stack (sum) all tracks into a single stereo output array
#   - Optionally normalize the final mix to prevent clipping
#
# This module is intentionally kept separate from cli.py and config.py so
# that the render logic can be tested and extended independently.
# ---------------------------------------------------------------------------

import numpy as np
from pathlib import Path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_audio(path: str, sample_rate: int, channels: int) -> np.ndarray:
    """
    Load an audio file from disk and return it as a float32 numpy array
    of shape (num_samples, channels), resampled to `sample_rate` if needed.

    Currently a STUB — returns a short block of silence so the rest of the
    pipeline can be developed and tested before the audio-decode layer is
    wired up.  Replace the body of this function (and add pydub/soundfile/
    librosa as a dependency) when the Audio File Input System is ready.

    Args:
        path:        Absolute or relative path to the audio file.
        sample_rate: Target sample rate in Hz (e.g. 44100).
        channels:    Number of output channels (1 = mono, 2 = stereo).

    Returns:
        np.ndarray of shape (num_samples, channels), dtype float32,
        values in [-1.0, 1.0].
    """
    # TODO: replace with real decode logic once FD-1 library is chosen
    #       e.g. soundfile.read(path, dtype="float32", always_2d=True)
    stub_duration_sec = 2
    num_samples = sample_rate * stub_duration_sec
    return np.zeros((num_samples, channels), dtype=np.float32)


def _apply_scale(audio: np.ndarray, factor: float, preserve_pitch: bool,
                 sample_rate: int) -> np.ndarray:
    """
    Time-scale `audio` by `factor` (0.5–2.0).

    Currently uses simple linear resampling (no pitch preservation).
    When preserve_pitch=True, a phase-vocoder pass should be applied
    before the resample — marked as TODO below.

    Args:
        audio:          Input array (num_samples, channels), float32.
        factor:         Speed multiplier.  >1.0 speeds up, <1.0 slows down.
        preserve_pitch: If True, attempt to keep pitch constant (phase vocoder).
        sample_rate:    Sample rate, needed by pitch-preservation code later.

    Returns:
        Resampled array with approximately len(audio) / factor samples.
    """
    if factor == 1.0:
        return audio  # nothing to do

    original_len = audio.shape[0]
    new_len = int(round(original_len / factor))

    # TODO: if preserve_pitch, apply phase-vocoder here before resampling
    #       (Feature 2.1.10 in the proposal)

    # Simple linear interpolation resample — meets the "minor artifacts
    # acceptable for MVP" requirement from section 2.1.9
    old_indices = np.linspace(0, original_len - 1, new_len)
    left = np.floor(old_indices).astype(int)
    right = np.clip(left + 1, 0, original_len - 1)
    frac = (old_indices - left)[:, np.newaxis]   # broadcast over channels

    resampled = audio[left] * (1 - frac) + audio[right] * frac
    return resampled.astype(np.float32)


def _apply_loop(audio: np.ndarray, count: int | None, bpm: float | None,
                bars: int | None, sample_rate: int) -> np.ndarray:
    """
    Repeat `audio` according to either a raw count or a musical meter.

    If `count` is given, the audio is simply tiled that many times.
    If `bpm` and `bars` are given, the desired loop length in samples is
    computed from the tempo and time signature, and the audio is tiled then
    trimmed/padded to that exact length (within 1% as required by 2.1.11).

    Args:
        audio:       Input array (num_samples, channels), float32.
        count:       Number of times to repeat, or None.
        bpm:         Beats per minute, or None.
        bars:        Number of bars to fill, or None.
        sample_rate: Sample rate used for BPM math.

    Returns:
        Looped array, float32.
    """
    if count is not None:
        # Simple tile — stacks the array `count` times along axis 0
        return np.tile(audio, (count, 1))

    if bpm is not None and bars is not None:
        # beats_per_bar is hard-coded to 4 for now (4/4 time signature).
        # TODO: read time_signature from the project config and parse the
        #       numerator so non-4/4 meters are supported.
        beats_per_bar = 4
        seconds_per_beat = 60.0 / bpm
        target_samples = int(round(bars * beats_per_bar * seconds_per_beat * sample_rate))

        # Tile enough copies to exceed the target, then trim to exact length
        needed_copies = int(np.ceil(target_samples / max(audio.shape[0], 1)))
        tiled = np.tile(audio, (max(needed_copies, 1), 1))
        return tiled[:target_samples]

    # No loop instruction — return audio unchanged
    return audio


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render(config: dict) -> np.ndarray:
    """
    Render a full composition defined by `config` into a single float32 array.

    Processing order for each timeline item:
        1. Load raw audio from disk (or stub)
        2. Apply ops in order: currently 'scale' and 'loop' are supported
        3. Offset the track in time if a non-zero 'start' is specified
        4. Accumulate into the master mix buffer

    After all tracks are summed:
        5. Normalize the mix if config["mix"]["normalize"] is True

    Args:
        config: A dict matching the schema produced by config.py (loaded from
                the project YAML).  Expected top-level keys:
                  "project"  → sample_rate, channels
                  "assets"   → list of {id, path}
                  "timeline" → list of {id, asset, start, gain_db, ops:[]}
                  "mix"      → {normalize: bool}

    Returns:
        np.ndarray of shape (total_samples, channels), dtype float32.
        Returns an empty (0, channels) array if the timeline is empty.
    """
    project   = config.get("project", {})
    sample_rate = int(project.get("sample_rate", 44100))
    channels    = int(project.get("channels", 2))

    # Build a quick lookup from asset id → file path
    asset_map = {a["id"]: a["path"] for a in config.get("assets", [])}

    # We'll collect rendered tracks here before summing
    rendered_tracks: list[np.ndarray] = []

    for item in config.get("timeline", []):
        asset_id = item.get("asset")
        if asset_id not in asset_map:
            # Asset referenced in timeline but not declared in assets block —
            # skip with a warning rather than crashing (matches 2.1.7 error
            # handling requirement)
            print(f"[mixer] Warning: asset '{asset_id}' not found, skipping.")
            continue

        # --- 1. Load audio ---
        audio = _load_audio(asset_map[asset_id], sample_rate, channels)

        # --- 2. Apply ops in the order they were queued ---
        for op in item.get("ops", []):
            op_type = op.get("type")

            if op_type == "scale":
                audio = _apply_scale(
                    audio,
                    factor=float(op.get("factor", 1.0)),
                    preserve_pitch=bool(op.get("preserve_pitch", False)),
                    sample_rate=sample_rate,
                )

            elif op_type == "loop":
                audio = _apply_loop(
                    audio,
                    count=op.get("count"),
                    bpm=op.get("bpm"),
                    bars=op.get("bars"),
                    sample_rate=sample_rate,
                )

            # TODO: add more op types here as they are implemented
            #       e.g. "fade_in", "fade_out", "eq", "reverb"

        # --- 3. Apply gain (convert dB to linear amplitude) ---
        gain_db = float(item.get("gain_db", 0.0))
        if gain_db != 0.0:
            audio = audio * (10.0 ** (gain_db / 20.0))

        # --- 4. Apply start offset (prepend silence) ---
        start_sec = float(item.get("start", 0.0))
        if start_sec > 0.0:
            offset_samples = int(round(start_sec * sample_rate))
            silence = np.zeros((offset_samples, channels), dtype=np.float32)
            audio = np.vstack([silence, audio])

        rendered_tracks.append(audio)

    if not rendered_tracks:
        return np.zeros((0, channels), dtype=np.float32)

    # --- Sum all tracks into a single mix buffer ---
    # Pad shorter tracks with trailing silence so they all match the longest
    max_len = max(t.shape[0] for t in rendered_tracks)
    mix = np.zeros((max_len, channels), dtype=np.float32)
    for track in rendered_tracks:
        pad_len = max_len - track.shape[0]
        if pad_len > 0:
            track = np.vstack([track, np.zeros((pad_len, channels), dtype=np.float32)])
        mix += track

    # --- 5. Normalize to prevent clipping ---
    if config.get("mix", {}).get("normalize", True):
        peak = np.max(np.abs(mix))
        if peak > 1.0:
            mix = mix / peak   # scale down to [-1.0, 1.0]

    return mix

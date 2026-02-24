import numpy as np
import librosa
import soundfile as sf
from pathlib import Path

def apply_scale(audio, sr, factor, preserve_pitch):
    """
    Time-scale audio
    Scale factor > 1.0 = faster audio
    Scale factor < 1.0 = slower audio
    """

    # if preserving pitch, change duration but keep pitch the same
    if preserve_pitch:
        return librosa.effects.time_stretch(audio, rate=factor)

    # if not preserving pitch, change sample rate by  a factor
    else:
        new_sr = int(sr * factor)
        return librosa.resample(audio, orig_sr = sr, target_sr = new_sr)

def render(cfg_data):

    # stores tracks
    mix_buffer = []

    # stores sample rate, set with first audio file in track
    sample_rate = None

    for item in cfg_data["timeline"]:
        # get asset id of current item
        asset_id = item["asset"]

        # finds next asset matching id
        asset = next(a for a in cfg_data["assets"] if a["id"] == asset_id)
        audio, file_sr = librosa.load(asset["path"], sr = None)

        if sample_rate is None:
            sample_rate = file_sr

        for op in item["ops"]:
            if op["type"] == "scale":
                audio = apply_scale(audio, file_sr, op["factor"], op["preserve_pitch"])
            elif op["type"] == "loop":
                if op["count"]:
                    audio = np.tile(audio, op["count"])
        mix_buffer.append(audio)
    output = np.sum(mix_buffer, axis = 0)

    if cfg_data["mix"]["normalize"]:
        peak = np.max(np.abs(output))
        if peak > 0:
            output = output / peak

    return output, sample_rate

def export(cfg_data):
    audio, sr = render(cfg_data)
    out_path = Path(cfg_data["export"]["path"])
    sf.write(out_path, audio, sr)
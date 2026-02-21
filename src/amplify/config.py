import yaml
from pathlib import Path

DEFAULT_CONFIG = {
    "version": 1,
    "project": {
        "name": "untitled",
        "sample_rate": 44100,
        "channels": 2,
        "bpm": 120,
        "time_signature": "4/4"
    },
    "assets": [],
    "timeline": [],
    "mix": {"normalize": True},
    "export": {"path": "out.wav", "format": "wav"}
}

def ensure_cfg(path: str):
    p = Path(path)
    if not p.exists():
        p.write_text(yaml.safe_dump(DEFAULT_CONFIG, sort_keys=False))

def load_cfg(path: str) -> dict:
    ensure_cfg(path)
    return yaml.safe_load(Path(path).read_text()) or {}

def save_cfg(path: str, data: dict) -> None:
    Path(path).write_text(yaml.safe_dump(data, sort_keys=False))

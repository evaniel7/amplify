from pathlib import Path

import yaml


DEFAULT_CONFIG = {
    "version": 1,
    "project": {
        "name": "untitled",
        "sample_rate": 44100,
        "channels": 1,
        "bpm": 120,
        "time_signature": "4/4",
    },
    "assets": [],
    "timeline": [],
    "mix": {
        "normalize": True,
    },
    "export": {
        "path": "out.wav",
        "format": "wav",
    },
}


def _deep_copy_default_config() -> dict:
    """
    Return a fresh copy of the default config so mutable nested values
    are not shared between calls.
    """
    return {
        "version": DEFAULT_CONFIG["version"],
        "project": dict(DEFAULT_CONFIG["project"]),
        "assets": list(DEFAULT_CONFIG["assets"]),
        "timeline": list(DEFAULT_CONFIG["timeline"]),
        "mix": dict(DEFAULT_CONFIG["mix"]),
        "export": dict(DEFAULT_CONFIG["export"]),
    }


def _merge_defaults(data: dict, defaults: dict) -> dict:
    """
    Recursively merge defaults into a loaded config without overwriting
    values that already exist.
    """
    for key, default_value in defaults.items():
        if key not in data:
            if isinstance(default_value, dict):
                data[key] = dict(default_value)
            elif isinstance(default_value, list):
                data[key] = list(default_value)
            else:
                data[key] = default_value
        else:
            if isinstance(default_value, dict) and isinstance(data[key], dict):
                _merge_defaults(data[key], default_value)

    return data


def ensure_cfg(path: str | Path) -> Path:
    """
    Create a new config file if it does not exist.
    If it already exists, leave it alone.
    """
    cfg_path = Path(path).expanduser()

    if cfg_path.exists():
        return cfg_path

    if cfg_path.parent and not cfg_path.parent.exists():
        cfg_path.parent.mkdir(parents=True, exist_ok=True)

    save_cfg(cfg_path, _deep_copy_default_config())
    return cfg_path


def load_cfg(path: str | Path) -> dict:
    """
    Load a YAML config and fill in any missing default keys.
    """
    cfg_path = Path(path).expanduser()

    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file '{cfg_path}' does not exist.")

    with cfg_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        data = {}

    if not isinstance(data, dict):
        raise ValueError(f"Config file '{cfg_path}' must contain a YAML mapping/object.")

    data = _merge_defaults(data, _deep_copy_default_config())
    return data


def save_cfg(path: str | Path, data: dict) -> Path:
    """
    Save config data as YAML.
    """
    cfg_path = Path(path).expanduser()

    if cfg_path.parent and not cfg_path.parent.exists():
        cfg_path.parent.mkdir(parents=True, exist_ok=True)

    with cfg_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

    return cfg_path
import typer
from pathlib import Path
from amplify.config import load_cfg, save_cfg, ensure_cfg
from amplify.render import export as render_export

app = typer.Typer(add_completion=False)

@app.command()
def init(cfg: str):
    """Create a new Amplify config."""
    ensure_cfg(cfg)
    typer.echo(f"Initialized {cfg}")

@app.command()
def load(cfg: str, files: list[str]):
    """Add audio files to config."""
    data = load_cfg(cfg)
    for f in files:
        asset_id = Path(f).stem
        data["assets"].append({"id": asset_id, "path": f})
        data["timeline"].append({
            "id": f"{asset_id}_1",
            "asset": asset_id,
            "start": 0.0,
            "gain_db": 0.0,
            "ops": []
        })
    save_cfg(cfg, data)
    typer.echo(f"Loaded {len(files)} file(s).")

@app.command()
def scale(
    cfg: str,
    target: str,
    factor: float = typer.Option(..., "--factor"),
    preserve_pitch: bool = False,
):
    """Time-scale a sample (0.5–2.0)."""
    if not (0.5 <= factor <= 2.0):
        raise typer.BadParameter("Factor must be between 0.5 and 2.0.")
    data = load_cfg(cfg)
    for item in data["timeline"]:
        if item["asset"] == target or item["id"] == target:
            item["ops"].append({
                "type": "scale",
                "factor": factor,
                "preserve_pitch": preserve_pitch
            })
    save_cfg(cfg, data)
    typer.echo(f"Queued scale on {target}.")

@app.command()
def loop(
    cfg: str,
    target: str,
    count: int = typer.Option(None),
    bpm: float = typer.Option(None),
    bars: int = typer.Option(None),
):
    """Loop by count OR musical bars."""
    if count is None and (bpm is None or bars is None):
        raise typer.BadParameter("Provide --count OR both --bpm and --bars.")
    data = load_cfg(cfg)
    for item in data["timeline"]:
        if item["asset"] == target or item["id"] == target:
            item["ops"].append({
                "type": "loop",
                "count": count,
                "bpm": bpm,
                "bars": bars
            })
    save_cfg(cfg, data)
    typer.echo(f"Queued loop on {target}.")

@app.command()
def mix(cfg: str, normalize: bool = True):
    """Set mix normalization."""
    data = load_cfg(cfg)
    data["mix"]["normalize"] = normalize
    save_cfg(cfg, data)
    typer.echo(f"Mix updated. Normalize={normalize}")

@app.command()
def export(cfg: str, out: str):
    """Export placeholder."""
    data = load_cfg(cfg)
    data["export"]["path"] = out
    save_cfg(cfg, data)
    render_export(data)
    typer.echo(f"Exported to {out}")

def main():
    app()

if __name__ == "__main__":
    main()

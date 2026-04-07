from pathlib import Path

import typer
from rich.console import Console

from amplify.config import ensure_cfg, load_cfg, save_cfg
from amplify.render import export as render_export
from amplify.sample_loader import load_sample

app = typer.Typer(add_completion=False)
console = Console()


def _find_timeline_item(data: dict, target: str) -> dict:
    for item in data.get("timeline", []):
        if item.get("asset") == target or item.get("id") == target:
            return item
    raise typer.BadParameter(f"Target '{target}' not found in timeline.")


def _unique_asset_id(data: dict, base_id: str) -> str:
    existing_ids = {asset.get("id") for asset in data.get("assets", [])}
    if base_id not in existing_ids:
        return base_id

    i = 2
    while f"{base_id}_{i}" in existing_ids:
        i += 1
    return f"{base_id}_{i}"


@app.command()
def init(cfg: Path):
    """Create a new Amplify config."""
    ensure_cfg(str(cfg))
    typer.echo(f"Initialized {cfg}")


@app.command()
def load(cfg: Path, files: list[Path]):
    """Load one or more audio files into the project config."""
    if not files:
        raise typer.BadParameter("Provide at least one audio file.")

    data = load_cfg(str(cfg))

    for file in files:
        try:
            with console.status(f"[bold cyan]Loading {file.name}...", spinner="dots"):
                signal, sr = load_sample(str(file))
        except (ValueError, FileNotFoundError) as e:
            console.print(f"[bold red]Input Error:[/bold red] {e}")
            raise typer.Exit(code=1)
        except RuntimeError as e:
            console.print(f"[bold red]System Error:[/bold red] {e}")
            raise typer.Exit(code=1)

        asset_id = _unique_asset_id(data, file.stem)

        data.setdefault("assets", []).append(
            {
                "id": asset_id,
                "path": str(file),
            }
        )

        data.setdefault("timeline", []).append(
            {
                "id": asset_id,
                "asset": asset_id,
                "start": 0.0,
                "gain_db": 0.0,
                "ops": [],
            }
        )

        duration = len(signal) / sr
        console.print(
            f"[bold green]✓[/bold green] Loaded [yellow]{file}[/yellow] "
            f"as [cyan]{asset_id}[/cyan]"
        )
        console.print(f"[dim]Rate: {sr}Hz | Duration: {duration:.2f}s[/dim]")

    save_cfg(str(cfg), data)
    typer.echo(f"Updated {cfg}")


@app.command()
def scale(
    cfg: Path,
    target: str,
    factor: float = typer.Option(..., "--factor"),
    preserve_pitch: bool = typer.Option(False, "--preserve-pitch"),
):
    """Queue a time-scale operation."""
    if not (0.5 <= factor <= 2.0):
        raise typer.BadParameter("Factor must be between 0.5 and 2.0.")

    data = load_cfg(str(cfg))
    item = _find_timeline_item(data, target)

    item.setdefault("ops", []).append(
        {
            "type": "scale",
            "factor": factor,
            "preserve_pitch": preserve_pitch,
        }
    )

    save_cfg(str(cfg), data)
    typer.echo(f"Queued scale on {target}.")


@app.command()
def loop(
    cfg: Path,
    target: str,
    count: int = typer.Option(None, "--count"),
    bpm: float = typer.Option(None, "--bpm"),
    bars: int = typer.Option(None, "--bars"),
):
    """Queue a loop operation."""
    if count is None and (bpm is None or bars is None):
        raise typer.BadParameter("Provide --count OR both --bpm and --bars.")

    data = load_cfg(str(cfg))
    item = _find_timeline_item(data, target)

    item.setdefault("ops", []).append(
        {
            "type": "loop",
            "count": count,
            "bpm": bpm,
            "bars": bars,
        }
    )

    save_cfg(str(cfg), data)
    typer.echo(f"Queued loop on {target}.")


@app.command()
def mix(
    cfg: Path,
    normalize: bool = typer.Option(True, "--normalize/--no-normalize"),
):
    """Set mix options."""
    data = load_cfg(str(cfg))
    data.setdefault("mix", {})["normalize"] = normalize
    save_cfg(str(cfg), data)
    typer.echo(f"Mix updated. Normalize={normalize}")


@app.command()
def export(cfg: Path, out: Path):
    """Render and export audio."""
    data = load_cfg(str(cfg))
    data.setdefault("export", {})["path"] = str(out)
    save_cfg(str(cfg), data)

    render_export(data)
    typer.echo(f"Exported to {out}")


@app.command()
def show(cfg: Path):
    """Print a summary of the current project."""
    data = load_cfg(str(cfg))

    console.print("\n[bold cyan]Project[/bold cyan]")
    console.print(data.get("project", {}))

    console.print("\n[bold green]Assets[/bold green]")
    for a in data.get("assets", []):
        console.print(f"- {a['id']} -> {a['path']}")

    console.print("\n[bold yellow]Timeline[/bold yellow]")
    for t in data.get("timeline", []):
        console.print(f"- {t['id']} (asset={t['asset']}, start={t['start']})")
        for op in t.get("ops", []):
            console.print(f"    op: {op}")

    console.print("\n[bold magenta]Mix[/bold magenta]")
    console.print(data.get("mix", {}))

    console.print("\n[bold blue]Export[/bold blue]")
    console.print(data.get("export", {}))


def main():
    app()


if __name__ == "__main__":
    main()
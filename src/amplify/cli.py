import typer
from pathlib import Path
from amplify.config import load_cfg, save_cfg, ensure_cfg
import sys
import argparse
from rich.console import Console
from amplify.sample_loader import load_sample
from amplify.render import export as render_export

app = typer.Typer(add_completion=False)
console = Console()

@app.command()
def init(cfg: str):
    """Create a new Amplify config."""
    ensure_cfg(cfg)
    typer.echo(f"Initialized {cfg}")

@app.command()
def load(args):
    """UI Wrapper for the loading process."""
    try:
        # Start the visual spinner
        with console.status("[bold cyan]Processing audio...", spinner="dots"):
            signal, sr = load_sample(args)
        
        # Success message
        duration = len(signal) / sr
        console.print(f"[bold green]✓[/bold green] Successfully loaded: [yellow]{args}[/yellow]")
        console.print(f"[dim]Rate: {sr}Hz | Duration: {duration:.2f}s[/dim]")

    except (ValueError, FileNotFoundError) as e:
        # Displays your custom "Unsupported format" or "File not found" messages
        console.print(f"[bold red]Input Error:[/bold red] {e}")
        sys.exit(1)
        
    except RuntimeError as e:
        # Displays corruption or system errors
        console.print(f"[bold red]System Error:[/bold red] {e}")
        sys.exit(1)

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
    parser = argparse.ArgumentParser(prog="amplify", description="Amplify Sample Loader")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Setup 'amplify load [filename]'
    load_parser = subparsers.add_parser("load", help="Load a WAV or MP3 file")
    load_parser.add_argument("filename", help="Path to the audio file")
    
    args = parser.parse_args()

    if args.command == "load":
        handle_load(args)

if __name__ == "__main__":
    main()

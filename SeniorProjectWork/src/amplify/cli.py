import sys
import argparse
from rich.console import Console
from amplify.sample_loader import load_sample

console = Console()

def handle_load(args):
    """UI Wrapper for the loading process."""
    try:
        # Start the visual spinner
        with console.status("[bold cyan]Processing audio...", spinner="dots"):
            signal, sr = load_sample(args.filename)
        
        # Success message
        duration = len(signal) / sr
        console.print(f"[bold green]✓[/bold green] Successfully loaded: [yellow]{args.filename}[/yellow]")
        console.print(f"[dim]Rate: {sr}Hz | Duration: {duration:.2f}s[/dim]")

    except (ValueError, FileNotFoundError) as e:
        # Displays your custom "Unsupported format" or "File not found" messages
        console.print(f"[bold red]Input Error:[/bold red] {e}")
        sys.exit(1)
        
    except RuntimeError as e:
        # Displays corruption or system errors
        console.print(f"[bold red]System Error:[/bold red] {e}")
        sys.exit(1)

def main():
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
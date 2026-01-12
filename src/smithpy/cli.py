import json
import shutil
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm
from rich.panel import Panel
from rich.text import Text
from pyfiglet import figlet_format

# Import version info
try:
    from smithpy.__version__ import __version__, __author__
except ImportError:
    __version__ = "unknown"
    __author__ = "Frank1o3"

app = typer.Typer(
    add_completion=False,
    no_args_is_help=False, # We handle this manually in the callback for the banner
)
console = Console()
REGISTRY_PATH = Path.home() / ".config" / "smithpy" / "registry.json"

def get_manifest(path: Path = Path.cwd()) -> Optional[dict[str, list[str]|str]]:
    p = path / "smithpy.json"
    return json.loads(p.read_text()) if p.exists() else None

def render_banner():
    """Renders a high-quality stylized banner"""
    ascii_art = figlet_format("SmithPy", font="slant")
    
    # Create a colorful gradient-like effect for the text
    banner_text = Text(ascii_art, style="bold cyan")
    
    # Add extra info line
    info_line = Text.assemble(
        (" ⛏  ", "yellow"),
        (f"v{__version__}", "bold white"),
        (" | ", "dim"),
        ("Created by ", "italic white"),
        (f"{__author__}", "bold magenta"),
    )
    
    # Wrap in a nice panel
    console.print(Panel(
        Text.assemble(banner_text, "\n", info_line),
        border_style="blue",
        padding=(1, 2),
        expand=False
    ))

@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(None, "--version", "-v", help="Show version and exit")
):
    """
    SmithPy: A powerful Minecraft modpack manager for Modrinth.
    """
    if version:
        console.print(f"SmithPy Version: [bold cyan]{__version__}[/bold cyan]")
        raise typer.Exit()

    # If no command is provided (e.g., just 'smithpy')
    if ctx.invoked_subcommand is None:
        render_banner()
        console.print("\n[bold yellow]Usage:[/bold yellow] smithpy [COMMAND] [ARGS]...")
        console.print("\n[bold cyan]Core Commands:[/bold cyan]")
        console.print("  [green]setup[/green]    Initialize a new modpack project")
        console.print("  [green]ls[/green]       List all registered projects")
        console.print("  [green]add[/green]      Add a mod/resource/shader to manifest")
        console.print("  [green]build[/green]    Download files and setup loader version")
        console.print("  [green]export[/green]   Create the final .mrpack zip")
        
        console.print("\nRun [white]smithpy --help[/white] for full command details.\n")

@app.command()
def setup(name: str, mc: str = "1.21.1", loader: str = "fabric"):
    """Initialize the working directory for a new pack"""
    pack_dir = Path.cwd() / name
    pack_dir.mkdir(parents=True, exist_ok=True)
    
    # Standard SmithPy structure (The Watermark)
    for folder in ["mods", "overrides/resourcepacks", "overrides/shaderpacks", "overrides/config", "versions"]:
        (pack_dir / folder).mkdir(parents=True,exist_ok=True)

    manifest:dict[str, list[str]|str] = {
        "name": name,
        "minecraft": mc,
        "loader": loader,
        "mods": [],
        "resourcepacks": [],
        "shaderpacks": []
    }
    (pack_dir / "smithpy.json").write_text(json.dumps(manifest, indent=4))
    
    # Register globally
    registry = json.loads(REGISTRY_PATH.read_text()) if REGISTRY_PATH.exists() else {}
    registry[name] = str(pack_dir.absolute())
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(registry, indent=4))
    
    index_data:dict[str, dict[str, str]|list[str]|str|int] = {
        "formatVersion": 1,
        "game": "minecraft",
        "versionId": "1.0.0",
        "name": name,
        "dependencies": {
            "minecraft": mc,
            loader: "*"
        },
        "files": []
    }
    (pack_dir / "modrinth.index.json").write_text(json.dumps(index_data, indent=2))

    console.print(f"🚀 Project [bold cyan]{name}[/bold cyan] ready at {pack_dir}", style="green")

@app.command()
def add(slug: str, type: str = "mod"):
    """Add a project slug (a the slug would be the mod name in its url or in some cases just a lowercase version) to the manifest (mod/resourcepack/shaderpack)"""
    manifest = get_manifest()
    if not manifest:
        console.print("[red]Error:[/red] No smithpy.json found here.")
        return

    key = f"{type}s" if not type.endswith('s') else type
    if key in manifest:
        if slug not in manifest[key]:
            manifest[key].append(slug)
            Path("smithpy.json").write_text(json.dumps(manifest, indent=4))
            console.print(f"✅ Added {slug} to {key}")
        else:
            console.print(f"⚠️ {slug} already in list.")

@app.command()
def build():
    """Download dependencies and set up the loader version"""
    manifest = get_manifest()
    if not manifest:
        return
    
    console.print(f"🛠  Building [bold]{manifest['name']}[/bold]...", style="blue")
    
    # 1. Trigger your resolver.py logic here
    # 2. Trigger downloader.sh for the specific loader/MC version
    # 3. Output into the /versions folder so launchers detect it
    
    console.print("✨ Build complete. Files are staged in the project folders.", style="green")

@app.command()
def export():
    """Compress the project into a .mrpack and optionally cleanup"""
    manifest = get_manifest()
    if not manifest:
        return

    pack_name = manifest['name']
    zip_name = f"{pack_name}.mrpack"
    
    console.print(f"📦 Exporting to {zip_name}...", style="yellow")
    
    # Create the zip from the current directory
    shutil.make_archive(pack_name, 'zip', Path.cwd())
    Path(f"{pack_name}.zip").rename(zip_name)
    
    console.print(f"✅ Exported {zip_name} successfully!", style="green bold")

    # Optional Cleanup
    if Confirm.ask("Do you want to delete the source project directory?"):
        shutil.rmtree(Path.cwd())
        console.print("🗑  Project directory removed.", style="dim")

@app.command(name="ls")
def list_projects():
    """Show all SmithPy projects"""
    if not REGISTRY_PATH.exists():
        console.print("No projects registered.")
        return
    
    registry = json.loads(REGISTRY_PATH.read_text())
    table = Table(title="SmithPy Managed Packs", header_style="bold magenta")
    table.add_column("Pack Name", style="cyan")
    table.add_column("Location", style="dim")
    
    for name, path in registry.items():
        table.add_row(name, path)
    console.print(table)

def main():
    app()


if __name__ == "__main__":
    main()
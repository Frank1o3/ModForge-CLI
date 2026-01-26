import asyncio
import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import typer
from pyfiglet import figlet_format
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table
from rich.text import Text

from modforge_cli.api import ModrinthAPIConfig
from modforge_cli.core import Manifest
from modforge_cli.core import ModPolicy, ModResolver
from modforge_cli.core import (
    self_update,
    install_fabric,
    get_manifest,
    perform_add,
    ensure_config_file,
    run,
)

# Import version info
try:
    from modforge_cli.__version__ import __author__, __version__
except ImportError:
    __version__ = "unknown"
    __author__ = "Frank1o3"

app = typer.Typer(
    add_completion=False,
    no_args_is_help=False,  # We handle this manually in the callback for the banner
)
console = Console()
FABRIC_LOADER_VERSION = "0.18.4"
CONFIG_PATH = Path().home() / ".config" / "ModForge-CLI"
REGISTRY_PATH = CONFIG_PATH / "registry.json"
MODRINTH_API = CONFIG_PATH / "modrinth_api.json"
POLICY_PATH = CONFIG_PATH / "policy.json"

FABRIC_INSTALLER_URL = (
    "https://maven.fabricmc.net/net/fabricmc/"
    "fabric-installer/1.1.1/fabric-installer-1.1.1.jar"
)
DEFAULT_MODRINTH_API_URL = "https://raw.githubusercontent.com/Frank1o3/ModForge-CLI/refs/heads/main/configs/modrinth_api.json"

DEFAULT_POLICY_URL = "https://raw.githubusercontent.com/Frank1o3/ModForge-CLI/refs/heads/main/configs/policy.json"


ensure_config_file(MODRINTH_API, DEFAULT_MODRINTH_API_URL, "Modrinth API", console)

ensure_config_file(POLICY_PATH, DEFAULT_POLICY_URL, "Policy", console)


api = ModrinthAPIConfig(MODRINTH_API)


def render_banner():
    """Renders a high-quality stylized banner that respects terminal width"""
    # Get the current terminal width
    width = console.width
    
    # Use a smaller font or logic if the terminal is very narrow
    font = "slant" if width > 60 else "small"
    
    ascii_art = figlet_format("ModForge-CLI", font=font)
    banner_text = Text(ascii_art, style="bold cyan")

    info_line = Text.assemble(
        (" ⛏  ", "yellow"),
        (f"v{__version__}", "bold white"),
        (" | ", "dim"),
        ("Created by ", "italic white"),
        (f"{__author__}", "bold magenta"),
    )

    # Use expand=False so the panel shrinks to fit the text, 
    # but stays within terminal bounds.
    console.print(
        Panel(
            Text.assemble(banner_text, "\n", info_line),
            border_style="blue",
            padding=(1, 2),
            expand=False, 
        ),
        justify="left"
    )


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", help="Show version and exit"
    ),
):
    """
    ModForge-CLI: A powerful Minecraft modpack manager for Modrinth.
    """
    if version:
        console.print(f"ModForge-CLI Version: [bold cyan]{__version__}[/bold cyan]", width=console.width)
        raise typer.Exit()

    # If no command is provided (e.g., just 'ModForge-CLI')
    if ctx.invoked_subcommand is None:
        render_banner()
        console.print(
            "\n[bold yellow]Usage:[/bold yellow] ModForge-CLI [COMMAND] [ARGS]...", width=console.width
        )
        console.print("\n[bold cyan]Core Commands:[/bold cyan]", width=console.width)
        console.print("  [green]setup[/green]    Initialize a new modpack project", width=console.width)
        console.print("  [green]ls[/green]       List all registered projects", width=console.width)
        console.print("  [green]add[/green]      Add a mod/resource/shader to manifest", width=console.width)
        console.print(
            "  [green]build[/green]    Download files and setup loader version", width=console.width
        )
        console.print("  [green]export[/green]   Create the final .mrpack zip", width=console.width)
        console.print(
            "  [green]remove[/green]   Removes a modpack that you have locally.", width=console.width
        )

        console.print(
            "\nRun [white]ModForge-CLI --help[/white] for full command details.\n", width=console.width
        )


@app.command()
def setup(
    name: str,
    mc: str = "1.21.1",
    loader: str = "fabric",
    loader_version: str = FABRIC_LOADER_VERSION,
):
    """Initialize the working directory for a new pack"""
    pack_dir = Path.cwd() / name
    pack_dir.mkdir(parents=True, exist_ok=True)

    # Standard ModForge-CLI structure (The Watermark)
    for folder in [
        "mods",
        "overrides/resourcepacks",
        "overrides/shaderpacks",
        "overrides/config",
        "overrides/config/openloader/data",
        "versions",
    ]:
        (pack_dir / folder).mkdir(parents=True, exist_ok=True)

    manifest: Manifest = Manifest(
        name=name, minecraft=mc, loader=loader, loader_version=loader_version
    )
    (pack_dir / "ModForge-CLI.json").write_text(manifest.model_dump_json(indent=4))

    # Register globally
    registry: dict[str, str] = (
        json.loads(REGISTRY_PATH.read_text()) if REGISTRY_PATH.exists() else {}
    )
    registry[name] = str(pack_dir.absolute())
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(registry, indent=4))

    index_data: dict[str, dict[str, str] | list[str] | str | int] = {
        "formatVersion": 1,
        "game": "minecraft",
        "versionId": "1.0.0",
        "name": name,
        "dependencies": {"minecraft": mc, loader: "*"},
        "files": [],
    }
    (pack_dir / "modrinth.index.json").write_text(json.dumps(index_data, indent=2))

    console.print(
        f"Project [bold cyan]{name}[/bold cyan] ready at {pack_dir}", style="green", width=console.width
    )


@app.command()
def add(name: str, project_type: str = "mod", pack_name: str = "testpack"):
    """Search and add a project to the manifest without overwriting existing data"""

    # --- API LIMITATION CHECK ---
    if project_type in ["resourcepack", "shaderpack"]:
        console.print(
            f"[bold yellow]Notice:[/bold yellow] Adding {project_type}s is currently [red]Not Implemented[/red]. "
            "The search API is currently limited to mods."
        )
        return

    registry = json.loads(REGISTRY_PATH.read_text())
    if pack_name not in registry:
        console.print(f"[red]Error:[/red] Pack '{pack_name}' not found in registry.")
        return

    pack_path = Path(registry[pack_name])
    manifest_file = pack_path / "ModForge-CLI.json"

    manifest = get_manifest(console, pack_path)
    if not manifest:
        console.print(f"[red]Error:[/red] Could not load manifest at {manifest_file}")
        return

    asyncio.run(perform_add(api, name, manifest, project_type, console, manifest_file))


@app.command()
def resolve(pack_name: str = "testpack"):
    # 1. Load Registry and Manifest
    registry = json.loads(REGISTRY_PATH.read_text())
    if pack_name not in registry:
        console.print(f"[red]Error:[/red] Pack '{pack_name}' not found in registry.", width=console.width)
        return

    pack_path = Path(registry[pack_name])
    manifest_file = pack_path / "ModForge-CLI.json"

    manifest = get_manifest(console, pack_path)
    if not manifest:
        console.print(f"[red]Error:[/red] Could not load manifest at {manifest_file}", width=console.width)
        return

    # 2. Run Resolution Logic
    console.print(
        f"Resolving dependencies for [bold cyan]{pack_name}[/bold cyan]...",
        style="yellow", width=console.width
    )
    policy = ModPolicy(POLICY_PATH)
    resolver = ModResolver(
        policy=policy, api=api, mc_version=manifest.minecraft, loader=manifest.loader
    )

    # This returns a Set[str] of unique Modrinth Project IDs
    resolved_mods = resolver.resolve(manifest.mods)

    # 3. Update Manifest with Resolved IDs
    # We convert the set to a sorted list for a clean JSON file
    manifest.mods = sorted(list(resolved_mods))

    # 4. Save back to ModForge-CLI.json
    try:
        manifest_file.write_text(manifest.model_dump_json(indent=4))
        console.print(f"Successfully updated [bold]{manifest_file.name}[/bold]", width=console.width)
        console.print(
            f"Total mods resolved: [bold green]{len(manifest.mods)}[/bold green]", width=console.width
        )
    except Exception as e:
        console.print(f"[red]Error saving manifest:[/red] {e}", width=console.width)

    # Optional: Print a summary table of the IDs
    if manifest.mods:
        table = Table(title=f"Resolved IDs for {pack_name}")
        table.add_column("Project ID", style="green")
        for mod_id in manifest.mods:
            table.add_row(mod_id)
        console.print(table, width=console.width)


@app.command()
def build(pack_name: str = "testpack"):
    """Download dependencies and set up the loader version"""

    # 1. Load Registry and Manifest
    registry = json.loads(REGISTRY_PATH.read_text())
    if pack_name not in registry:
        console.print(f"[red]Error:[/red] Pack '{pack_name}' not found in registry.", width=console.width)
        return

    pack_path = Path(registry[pack_name])
    manifest_file = pack_path / "ModForge-CLI.json"

    manifest = get_manifest(console, pack_path)
    if not manifest:
        console.print(f"[red]Error:[/red] Could not load manifest at {manifest_file}", width=console.width)
        return

    pack_root = Path.cwd() / manifest.name
    mods_dir = pack_root / "mods"
    index_file = pack_root / "modrinth.index.json"

    mods_dir.mkdir(exist_ok=True)

    console.print(f"🛠  Building [bold cyan]{manifest.name}[/bold cyan]...", width=console.width)
    asyncio.run(run(api, manifest, mods_dir, index_file))
    console.print("✨ Build complete. Mods downloaded and indexed.", style="green", width=console.width)


@app.command()
def export(pack_name: str = "testpack"):
    """Finalize and export the pack as a runnable .zip"""

    # 1. Load Registry and Manifest
    registry = json.loads(REGISTRY_PATH.read_text())
    if pack_name not in registry:
        console.print(f"[red]Error:[/red] Pack '{pack_name}' not found in registry.", width=console.width)
        return

    pack_path = Path(registry[pack_name])
    manifest_file = pack_path / "ModForge-CLI.json"

    manifest = get_manifest(console, pack_path)
    if not manifest:
        console.print(f"[red]Error:[/red] Could not load manifest at {manifest_file}", width=console.width)
        return
    loader_version = manifest.loader_version or FABRIC_LOADER_VERSION

    console.print("📦 Finalizing pack...", style="cyan", width=console.width)

    mods_dir = Path.cwd() / manifest.name / "mods"
    if not mods_dir.exists() or not any(mods_dir.iterdir()):
        console.print("[red]No mods found. Run `ModForge-CLI build` first.[/red]", width=console.width)
        raise typer.Exit(1)

    if manifest.loader == "fabric":
        installer = Path.cwd() / manifest.name / ".fabric-installer.jar"

        if not installer.exists():
            console.print("Downloading Fabric installer...", width=console.width)
            import urllib.request

            urllib.request.urlretrieve(FABRIC_INSTALLER_URL, installer)

        console.print("Installing Fabric...", width=console.width)
        install_fabric(
            installer=installer,
            mc_version=manifest.minecraft,
            loader_version=loader_version,
            game_dir=Path.cwd() / manifest.name,
        )

        index_file = Path.cwd() / manifest.name / "modrinth.index.json"
        index = json.loads(index_file.read_text())
        index["dependencies"]["fabric-loader"] = loader_version
        index_file.write_text(json.dumps(index, indent=2))

        installer.unlink(missing_ok=True)

    pack_name = manifest.name
    zip_path = Path.cwd().parent / f"{pack_name}.zip"

    shutil.make_archive(
        base_name=str(zip_path.with_suffix("")),
        format="zip",
        root_dir=Path.cwd(),
    )

    console.print(f"✅ Exported {zip_path.name}", style="green bold", width=console.width)


@app.command()
def remove(pack_name: str):
    """Completely remove a modpack and unregister it"""
    if not REGISTRY_PATH.exists():
        console.print("[red]No registry found.[/red]", width=console.width)
        raise typer.Exit(1)

    registry = json.loads(REGISTRY_PATH.read_text())

    if pack_name not in registry:
        console.print(f"[red]Pack '{pack_name}' not found in registry.[/red]", width=console.width)
        raise typer.Exit(1)

    pack_path = Path(registry[pack_name])

    console.print(
        Panel.fit(
            f"[bold red]This will permanently delete:[/bold red]\n\n"
            f"[white]{pack_name}[/white]\n"
            f"[dim]{pack_path}[/dim]",
            title="⚠️  Destructive Action",
            border_style="red", width=console.width
        )
    )

    if not Confirm.ask("Are you sure you want to continue?", default=False):
        console.print("Aborted.", style="dim")
        raise typer.Exit()

    # Remove directory
    try:
        if pack_path.exists():
            shutil.rmtree(pack_path)
        else:
            console.print(
                f"[yellow]Warning:[/yellow] Pack directory does not exist: {pack_path}", width=console.width
            )
    except Exception as e:
        console.print(f"[red]Failed to delete pack directory:[/red] {e}", width=console.width)
        raise typer.Exit(1)

    # Update registry
    del registry[pack_name]
    REGISTRY_PATH.write_text(json.dumps(registry, indent=4))

    console.print(
        f"🗑️  Removed pack [bold cyan]{pack_name}[/bold cyan] successfully.",
        style="green", width=console.width
    )


@app.command(name="ls")
def list_projects():
    """Show all ModForge-CLI projects"""
    if not REGISTRY_PATH.exists():
        console.print("No projects registered.")
        return

    registry = json.loads(REGISTRY_PATH.read_text())
    table = Table(title="ModForge-CLI Managed Packs", header_style="bold magenta")
    table.add_column("Pack Name", style="cyan")
    table.add_column("Location", style="dim")

    for name, path in registry.items():
        table.add_row(name, path)
    console.print(table, width=console.width)


@app.command()
def self_update_cmd():
    """
    Update ModForge-CLI to the latest version.
    """
    try:
        self_update(console)
    except subprocess.CalledProcessError:
        raise typer.Exit(code=1)


def main():
    app()


if __name__ == "__main__":
    main()

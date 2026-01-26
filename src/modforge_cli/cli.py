import asyncio
import json
import logging
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request

from pyfiglet import figlet_format
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table
from rich.text import Text
import typer

from modforge_cli.api import ModrinthAPIConfig
from modforge_cli.core import (
    Manifest,
    ModPolicy,
    ModResolver,
    ensure_config_file,
    get_api_session,
    get_manifest,
    install_fabric,
    load_registry,
    perform_add,
    run,
    save_registry_atomic,
    self_update,
    setup_crash_logging,
)

# Import version info
try:
    from modforge_cli.__version__ import __author__, __version__
except ImportError:
    __version__ = "unknown"
    __author__ = "Frank1o3"

app = typer.Typer(
    add_completion=False,
    no_args_is_help=False,
)
console = Console()

# Configuration
FABRIC_LOADER_VERSION = "0.18.4"
CONFIG_PATH = Path.home() / ".config" / "ModForge-CLI"
REGISTRY_PATH = CONFIG_PATH / "registry.json"
MODRINTH_API = CONFIG_PATH / "modrinth_api.json"
POLICY_PATH = CONFIG_PATH / "policy.json"

# Use versioned URLs to prevent breaking changes
GITHUB_RAW = "https://raw.githubusercontent.com/Frank1o3/ModForge-CLI"
VERSION_TAG = "v0.1.8"  # Update this with each release

FABRIC_INSTALLER_URL = (
    "https://maven.fabricmc.net/net/fabricmc/fabric-installer/1.1.1/fabric-installer-1.1.1.jar"
)
FABRIC_INSTALLER_SHA256 = (
    "8fa465768bd7fc452e08c3a1e5c8a6b4b5f6a4e64bc7def47f89d8d3a6f4e7b8"  # Replace with actual hash
)

DEFAULT_MODRINTH_API_URL = f"{GITHUB_RAW}/{VERSION_TAG}/configs/modrinth_api.json"
DEFAULT_POLICY_URL = f"{GITHUB_RAW}/{VERSION_TAG}/configs/policy.json"

# Setup crash logging
LOG_DIR = setup_crash_logging()

# Ensure configs exist
ensure_config_file(MODRINTH_API, DEFAULT_MODRINTH_API_URL, "Modrinth API", console)
ensure_config_file(POLICY_PATH, DEFAULT_POLICY_URL, "Policy", console)

# Initialize API
api = ModrinthAPIConfig(MODRINTH_API)


def render_banner() -> None:
    """Renders a stylized banner"""
    width = console.width
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

    console.print(
        Panel(
            Text.assemble(banner_text, "\n", info_line),
            border_style="blue",
            padding=(1, 2),
            expand=False,
        ),
        justify="left",
    )


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: bool | None = typer.Option(None, "--version", "-v", help="Show version and exit"),
    verbose: bool | None = typer.Option(None, "--verbose", help="Enable verbose logging"),
) -> None:
    """ModForge-CLI: A powerful Minecraft modpack manager for Modrinth."""

    if verbose:
        # Enable verbose logging

        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(LOG_DIR / f"modforge-{__version__}.log"),
                logging.StreamHandler(),
            ],
        )

    if version:
        console.print(f"ModForge-CLI Version: [bold cyan]{__version__}[/bold cyan]")
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        render_banner()
        console.print("\n[bold yellow]Usage:[/bold yellow] ModForge-CLI [COMMAND] [ARGS]...")
        console.print("\n[bold cyan]Core Commands:[/bold cyan]")
        console.print("  [green]setup[/green]    Initialize a new modpack project")
        console.print("  [green]ls[/green]       List all registered projects")
        console.print("  [green]add[/green]      Add a mod/resource/shader to manifest")
        console.print("  [green]resolve[/green]  Resolve all dependencies")
        console.print("  [green]build[/green]    Download files and setup loader")
        console.print("  [green]export[/green]   Create the final .mrpack")
        console.print("  [green]remove[/green]   Remove a modpack project")
        console.print("\n[bold cyan]Utility:[/bold cyan]")
        console.print("  [green]self-update[/green]  Update ModForge-CLI")
        console.print("  [green]doctor[/green]       Validate installation")
        console.print("\nRun [white]ModForge-CLI --help[/white] for details.\n")


@app.command()
def setup(
    name: str,
    mc: str = "1.21.1",
    loader: str = "fabric",
    loader_version: str = FABRIC_LOADER_VERSION,
) -> None:
    """Initialize a new modpack project"""
    pack_dir = Path.cwd() / name

    if pack_dir.exists():
        console.print(f"[red]Error:[/red] Directory '{name}' already exists")
        raise typer.Exit(1)

    pack_dir.mkdir(parents=True, exist_ok=True)

    # Create standard structure
    for folder in [
        "mods",
        "overrides/resourcepacks",
        "overrides/shaderpacks",
        "overrides/config",
        "overrides/config/openloader/data",
        "versions",
    ]:
        (pack_dir / folder).mkdir(parents=True, exist_ok=True)

    # Create manifest
    manifest = Manifest(name=name, minecraft=mc, loader=loader, loader_version=loader_version)
    (pack_dir / "ModForge-CLI.json").write_text(manifest.model_dump_json(indent=4))

    # Create Modrinth index
    # Map loader names to their dependency keys
    loader_key_map = {
        "fabric": "fabric-loader",
        "quilt": "quilt-loader",
        "forge": "forge",
        "neoforge": "neoforge",
    }
    loader_key = loader_key_map.get(loader.lower(), loader.lower())

    index_data = {
        "formatVersion": 1,
        "game": "minecraft",
        "versionId": "1.0.0",
        "name": name,
        "dependencies": {"minecraft": mc, loader_key: loader_version},
        "files": [],  # Only for overrides, not mods
    }
    (pack_dir / "modrinth.index.json").write_text(json.dumps(index_data, indent=2))

    # Register project
    registry = load_registry(REGISTRY_PATH)
    registry[name] = str(pack_dir.absolute())
    save_registry_atomic(registry, REGISTRY_PATH)

    console.print(f"[green]✓ Project '{name}' created at {pack_dir}[/green]")
    console.print(f"[dim]Run 'cd {name}' to enter the project[/dim]")


@app.command()
def add(name: str, project_type: str = "mod", pack_name: str | None = None) -> None:
    """Add a project to the manifest"""

    if project_type not in ["mod", "resourcepack", "shaderpack"]:
        console.print(f"[red]Invalid type:[/red] {project_type}")
        console.print("[yellow]Valid types:[/yellow] mod, resourcepack, shaderpack")
        raise typer.Exit(1)

    # Auto-detect pack if not specified
    if not pack_name:
        manifest = get_manifest(console, Path.cwd())
        if manifest:
            pack_name = manifest.name
        else:
            console.print("[red]No manifest found in current directory[/red]")
            console.print("[yellow]Specify --pack-name or run from project directory[/yellow]")
            raise typer.Exit(1)

    registry = load_registry(REGISTRY_PATH)
    if pack_name not in registry:
        console.print(f"[red]Pack '{pack_name}' not found in registry[/red]")
        console.print("[yellow]Available packs:[/yellow]")
        for p in registry:
            console.print(f"  - {p}")
        raise typer.Exit(1)

    pack_path = Path(registry[pack_name])
    manifest_file = pack_path / "ModForge-CLI.json"

    manifest = get_manifest(console, pack_path)
    if not manifest:
        console.print(f"[red]Could not load manifest at {manifest_file}[/red]")
        raise typer.Exit(1)

    asyncio.run(perform_add(api, name, manifest, project_type, console, manifest_file))


@app.command()
def resolve(pack_name: str | None = None) -> None:
    """Resolve all mod dependencies"""

    # Auto-detect pack
    if not pack_name:
        manifest = get_manifest(console, Path.cwd())
        if manifest:
            pack_name = manifest.name
        else:
            console.print("[red]No manifest found[/red]")
            raise typer.Exit(1)

    registry = load_registry(REGISTRY_PATH)
    if pack_name not in registry:
        console.print(f"[red]Pack '{pack_name}' not found[/red]")
        raise typer.Exit(1)

    pack_path = Path(registry[pack_name])
    manifest_file = pack_path / "ModForge-CLI.json"

    manifest = get_manifest(console, pack_path)
    if not manifest:
        console.print("[red]Could not load manifest[/red]")
        raise typer.Exit(1)

    console.print(f"[cyan]Resolving dependencies for {pack_name}...[/cyan]")

    policy = ModPolicy(POLICY_PATH)
    resolver = ModResolver(
        policy=policy, api=api, mc_version=manifest.minecraft, loader=manifest.loader
    )

    async def do_resolve():
        async with await get_api_session() as session:
            return await resolver.resolve(manifest.mods, session)

    try:
        resolved_mods = asyncio.run(do_resolve())
    except Exception as e:
        console.print(f"[red]Resolution failed:[/red] {e}")
        raise typer.Exit(1) from e

    manifest.mods = sorted(list(resolved_mods))
    manifest_file.write_text(manifest.model_dump_json(indent=4))

    console.print(f"[green]✓ Resolved {len(manifest.mods)} mods[/green]")


@app.command()
def build(pack_name: str | None = None) -> None:
    """Download all mods and dependencies"""

    if not pack_name:
        manifest = get_manifest(console, Path.cwd())
        if manifest:
            pack_name = manifest.name
        else:
            console.print("[red]No manifest found[/red]")
            raise typer.Exit(1)

    registry = load_registry(REGISTRY_PATH)
    if pack_name not in registry:
        console.print(f"[red]Pack '{pack_name}' not found[/red]")
        raise typer.Exit(1)

    pack_path = Path(registry[pack_name])
    manifest = get_manifest(console, pack_path)
    if not manifest:
        raise typer.Exit(1)

    pack_root = pack_path
    mods_dir = pack_root / "mods"
    index_file = pack_root / "modrinth.index.json"

    mods_dir.mkdir(exist_ok=True)

    console.print(f"[cyan]Building {manifest.name}...[/cyan]")

    try:
        asyncio.run(run(api, manifest, mods_dir, index_file))
        console.print("[green]✓ Build complete[/green]")
    except Exception as e:
        console.print(f"[red]Build failed:[/red] {e}")
        raise typer.Exit(1) from e


@app.command()
def export(pack_name: str | None = None) -> None:
    """Create final .mrpack file"""

    if not pack_name:
        manifest = get_manifest(console, Path.cwd())
        if manifest:
            pack_name = manifest.name
        else:
            console.print("[red]No manifest found[/red]")
            raise typer.Exit(1)

    registry = load_registry(REGISTRY_PATH)
    if pack_name not in registry:
        console.print(f"[red]Pack '{pack_name}' not found[/red]")
        raise typer.Exit(1)

    pack_path = Path(registry[pack_name])
    manifest = get_manifest(console, pack_path)
    if not manifest:
        raise typer.Exit(1)

    loader_version = manifest.loader_version or FABRIC_LOADER_VERSION

    console.print("[cyan]Exporting modpack...[/cyan]")

    mods_dir = pack_path / "mods"
    if not mods_dir.exists() or not any(mods_dir.iterdir()):
        console.print("[red]No mods found. Run 'ModForge-CLI build' first[/red]")
        raise typer.Exit(1)

    # Install loader if needed
    if manifest.loader == "fabric":
        installer = pack_path / ".fabric-installer.jar"

        if not installer.exists():
            console.print("[yellow]Downloading Fabric installer...[/yellow]")
            

            urllib.request.urlretrieve(FABRIC_INSTALLER_URL, installer)

            # Verify hash (security)
            # Note: Update FABRIC_INSTALLER_SHA256 with actual hash
            # actual_hash = hashlib.sha256(installer.read_bytes()).hexdigest()
            # if actual_hash != FABRIC_INSTALLER_SHA256:
            #     console.print("[red]Installer hash mismatch![/red]")
            #     installer.unlink()
            #     raise typer.Exit(1)

        console.print("[yellow]Installing Fabric...[/yellow]")
        try:
            install_fabric(
                installer=installer,
                mc_version=manifest.minecraft,
                loader_version=loader_version,
                game_dir=pack_path,
            )
            console.print(f"[green]✓ Fabric {loader_version} installed[/green]")
        except RuntimeError as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(1) from e

        installer.unlink(missing_ok=True)

    # Create .mrpack
    zip_path = pack_path.parent / f"{pack_name}.mrpack"
    shutil.make_archive(
        base_name=str(zip_path.with_suffix("")),
        format="zip",
        root_dir=pack_path,
    )

    # Rename .zip to .mrpack
    zip_file = pack_path.parent / f"{pack_name}.zip"
    if zip_file.exists():
        zip_file.rename(zip_path)

    console.print(f"[green bold]✓ Exported to {zip_path}[/green bold]")


@app.command()
def remove(pack_name: str) -> None:
    """Remove a modpack and unregister it"""
    registry = load_registry(REGISTRY_PATH)

    if pack_name not in registry:
        console.print(f"[red]Pack '{pack_name}' not found[/red]")
        raise typer.Exit(1)

    pack_path = Path(registry[pack_name])

    console.print(
        Panel.fit(
            f"[bold red]This will permanently delete:[/bold red]\n\n"
            f"[white]{pack_name}[/white]\n"
            f"[dim]{pack_path}[/dim]",
            title="⚠️  Destructive Action",
            border_style="red",
        )
    )

    if not Confirm.ask("Are you sure?", default=False):
        console.print("Aborted.")
        raise typer.Exit()

    # Remove directory
    if pack_path.exists():
        shutil.rmtree(pack_path)

    # Update registry
    del registry[pack_name]
    save_registry_atomic(registry, REGISTRY_PATH)

    console.print(f"[green]✓ Removed {pack_name}[/green]")


@app.command(name="ls")
def list_projects() -> None:
    """List all registered modpacks"""
    registry = load_registry(REGISTRY_PATH)

    if not registry:
        console.print("[yellow]No projects registered yet[/yellow]")
        console.print("[dim]Run 'ModForge-CLI setup <name>' to create one[/dim]")
        return

    table = Table(title="ModForge-CLI Projects", header_style="bold magenta")
    table.add_column("Name", style="cyan")
    table.add_column("Location", style="dim")

    for name, path in registry.items():
        table.add_row(name, path)

    console.print(table)


@app.command()
def doctor() -> None:
    """Validate ModForge-CLI installation"""
    console.print("[bold cyan]Running diagnostics...[/bold cyan]\n")

    issues = []

    # Check Python version

    py_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    console.print(f"[green]✓[/green] Python {py_version}")

    # Check config files
    for name, path in [("API Config", MODRINTH_API), ("Policy", POLICY_PATH)]:
        if path.exists():
            console.print(f"[green]✓[/green] {name}: {path}")
        else:
            console.print(f"[red]✗[/red] {name} missing")
            issues.append(f"Reinstall {name}")

    # Check registry
    registry = load_registry(REGISTRY_PATH)
    console.print(f"[green]✓[/green] Registry: {len(registry)} projects")

    # Check Java
    try:

        result = subprocess.run(["java", "-version"], capture_output=True, text=True, check=True)
        console.print("[green]✓[/green] Java installed")
    except (FileNotFoundError, subprocess.CalledProcessError):
        console.print("[yellow]![/yellow] Java not found (needed for Fabric)")
        issues.append("Install Java 17+")

    # Summary
    console.print()
    if issues:
        console.print("[yellow]Issues found:[/yellow]")
        for issue in issues:
            console.print(f"  - {issue}")
    else:
        console.print("[green bold]✓ All checks passed![/green bold]")


@app.command(name="self-update")
def self_update_cmd() -> None:
    """Update ModForge-CLI to latest version"""
    try:
        self_update(console)
    except Exception as e:
        console.print(f"[red]Update failed:[/red] {e}")
        raise typer.Exit(1) from e


def main() -> None:
    app()


if __name__ == "__main__":
    main()

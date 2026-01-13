import asyncio
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import aiohttp
import typer
from pyfiglet import figlet_format
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table
from rich.text import Text

from smithpy.api import ModrinthAPIConfig
from smithpy.core import Manifest, ModDownloader, SearchResult

# Import version info
try:
    from smithpy.__version__ import __author__, __version__
except ImportError:
    __version__ = "unknown"
    __author__ = "Frank1o3"

app = typer.Typer(
    add_completion=False,
    no_args_is_help=False,  # We handle this manually in the callback for the banner
)
console = Console()
FABRIC_LOADER_VERSION = "0.18.3"
CONFIG_PATH = Path().home() / ".config" / "smithpy"
REGISTRY_PATH = CONFIG_PATH / "registry.json"
MODRINTH_API = CONFIG_PATH / "modrinth_api.json"
POLICY_PATH = CONFIG_PATH / "policy.json"

FABRIC_INSTALLER_URL = (
    "https://maven.fabricmc.net/net/fabricmc/"
    "fabric-installer/1.1.1/fabric-installer-1.1.1.jar"
)
DEFAULT_MODRINTH_API_URL = "https://raw.githubusercontent.com/Frank1o3/smithpy/refs/heads/main/configs/modrinth_api.json"

DEFAULT_POLICY_URL = "https://raw.githubusercontent.com/Frank1o3/smithpy/refs/heads/main/configs/policy.json"


def ensure_config_file(path: Path, url: str, label: str):
    if path.exists():
        return

    path.parent.mkdir(parents=True, exist_ok=True)

    console.print(f"[yellow]Missing {label} config.[/yellow] Downloading default…")

    try:
        import urllib.request

        urllib.request.urlretrieve(url, path)
        console.print(f"[green]✓ {label} config installed at {path}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to download {label} config:[/red] {e}")
        raise typer.Exit(1)


ensure_config_file(
    MODRINTH_API,
    DEFAULT_MODRINTH_API_URL,
    "Modrinth API",
)

ensure_config_file(
    POLICY_PATH,
    DEFAULT_POLICY_URL,
    "Policy",
)


api = ModrinthAPIConfig(MODRINTH_API)


# --- Async Helper ---
async def get_api_session():
    """Returns a session with the correct SmithPy headers."""
    return aiohttp.ClientSession(
        headers={"User-Agent": f"{__author__}/SmithPy/{__version__}"},
        raise_for_status=True,
    )


def get_manifest(path: Path = Path.cwd()) -> Optional[Manifest]:
    p = path / "smithpy.json"
    if not p.exists():
        return None
    try:
        return Manifest.model_validate_json(p.read_text())
    except Exception as e:
        console.print(e)
        return None


def install_fabric(
    installer: Path,
    mc_version: str,
    loader_version: str,
    game_dir: Path,
):
    subprocess.run(
        [
            "java",
            "-jar",
            installer,
            "client",
            "-mcversion",
            mc_version,
            "-loader",
            loader_version,
            "-dir",
            str(game_dir),
            "-noprofile",
        ],
        check=True,
    )


def detect_install_method() -> str:
    prefix = Path(sys.prefix)

    if "pipx" in prefix.parts:
        return "pipx"
    return "pip"

def self_update():
    method = detect_install_method()

    if method == "pipx":
        console.print("[cyan]Updating SmithPy using pipx...[/cyan]")
        subprocess.run(["pipx", "upgrade", "smithpy"], check=True)

    else:
        console.print("[cyan]Updating SmithPy using pip...[/cyan]")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "smithpy"],
            check=True,
        )

    console.print("[green]SmithPy updated successfully.[/green]")


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
    console.print(
        Panel(
            Text.assemble(banner_text, "\n", info_line),
            border_style="blue",
            padding=(1, 2),
            expand=False,
        )
    )


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", help="Show version and exit"
    ),
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
        console.print(
            "  [green]build[/green]    Download files and setup loader version"
        )
        console.print("  [green]export[/green]   Create the final .mrpack zip")

        console.print("\nRun [white]smithpy --help[/white] for full command details.\n")


@app.command()
def setup(name: str, mc: str = "1.21.1", loader: str = "fabric", loader_version: str = FABRIC_LOADER_VERSION):
    """Initialize the working directory for a new pack"""
    pack_dir = Path.cwd() / name
    pack_dir.mkdir(parents=True, exist_ok=True)


    # Standard SmithPy structure (The Watermark)
    for folder in [
        "mods",
        "overrides/resourcepacks",
        "overrides/shaderpacks",
        "overrides/config",
        "versions",
    ]:
        (pack_dir / folder).mkdir(parents=True, exist_ok=True)

    manifest: Manifest = Manifest(name=name, minecraft=mc, loader=loader, loader_version=loader_version)
    (pack_dir / "smithpy.json").write_text(manifest.model_dump_json(indent=4))

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
        f"Project [bold cyan]{name}[/bold cyan] ready at {pack_dir}", style="green"
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
    manifest_file = pack_path / "smithpy.json"

    manifest = get_manifest(pack_path)
    if not manifest:
        console.print(f"[red]Error:[/red] Could not load manifest at {manifest_file}")
        return

    async def perform_add():
        async with await get_api_session() as session:
            url = api.search(
                name,
                game_versions=[manifest.minecraft],
                loaders=[manifest.loader],
                project_type=project_type,
            )

            async with session.get(url) as response:
                results = SearchResult.model_validate_json(await response.text())

            if not results or not results.hits:
                console.print(f"[red]No {project_type} found for '{name}'")
                return

            # Match slug
            target_hit = next(
                (h for h in results.hits if h.slug == name), results.hits[0]
            )
            slug = target_hit.slug

            # 3. Modify the existing manifest object
            # Only 'mod' will reach here currently due to the check above
            target_list = {
                "mod": manifest.mods,
                "resourcepack": manifest.resourcepacks,
                "shaderpack": manifest.shaderpacks,
            }.get(project_type, manifest.mods)

            if slug not in target_list:
                target_list.append(slug)
                manifest_file.write_text(manifest.model_dump_json(indent=4))
                console.print(f"Added [green]{slug}[/green] to {project_type}s")
            else:
                console.print(f"{slug} is already in the manifest.")

    asyncio.run(perform_add())


@app.command()
def resolve(pack_name: str = "testpack"):
    from smithpy.core import ModPolicy, ModResolver

    # 1. Load Registry and Manifest
    registry = json.loads(REGISTRY_PATH.read_text())
    if pack_name not in registry:
        console.print(f"[red]Error:[/red] Pack '{pack_name}' not found in registry.")
        return

    pack_path = Path(registry[pack_name])
    manifest_file = pack_path / "smithpy.json"

    manifest = get_manifest(pack_path)
    if not manifest:
        console.print(f"[red]Error:[/red] Could not load manifest at {manifest_file}")
        return

    # 2. Run Resolution Logic
    console.print(
        f"Resolving dependencies for [bold cyan]{pack_name}[/bold cyan]...",
        style="yellow",
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

    # 4. Save back to smithpy.json
    try:
        manifest_file.write_text(manifest.model_dump_json(indent=4))
        console.print(f"Successfully updated [bold]{manifest_file.name}[/bold]")
        console.print(
            f"Total mods resolved: [bold green]{len(manifest.mods)}[/bold green]"
        )
    except Exception as e:
        console.print(f"[red]Error saving manifest:[/red] {e}")

    # Optional: Print a summary table of the IDs
    if manifest.mods:
        table = Table(title=f"Resolved IDs for {pack_name}")
        table.add_column("Project ID", style="green")
        for mod_id in manifest.mods:
            table.add_row(mod_id)
        console.print(table)


@app.command()
def build(pack_name: str = "testpack"):
    """Download dependencies and set up the loader version"""

    # 1. Load Registry and Manifest
    registry = json.loads(REGISTRY_PATH.read_text())
    if pack_name not in registry:
        console.print(f"[red]Error:[/red] Pack '{pack_name}' not found in registry.")
        return

    pack_path = Path(registry[pack_name])
    manifest_file = pack_path / "smithpy.json"

    manifest = get_manifest(pack_path)
    if not manifest:
        console.print(f"[red]Error:[/red] Could not load manifest at {manifest_file}")
        return

    pack_root = Path.cwd() / manifest.name
    mods_dir = pack_root / "mods"
    index_file = pack_root / "modrinth.index.json"

    mods_dir.mkdir(exist_ok=True)

    async def run():
        async with aiohttp.ClientSession(
            headers={"User-Agent": f"{__author__}/SmithPy/{__version__}"},
            raise_for_status=True,
        ) as session:
            downloader = ModDownloader(
                api=api,
                mc_version=manifest.minecraft,
                loader=manifest.loader,
                output_dir=mods_dir,
                index_file=index_file,
                session=session,
            )
            await downloader.download_all(manifest.mods)

    console.print(f"🛠  Building [bold cyan]{manifest.name}[/bold cyan]...")
    asyncio.run(run())
    console.print("✨ Build complete. Mods downloaded and indexed.", style="green")


@app.command()
def export(pack_name: str = "testpack"):
    """Finalize and export the pack as a runnable .zip"""

    # 1. Load Registry and Manifest
    registry = json.loads(REGISTRY_PATH.read_text())
    if pack_name not in registry:
        console.print(f"[red]Error:[/red] Pack '{pack_name}' not found in registry.")
        return

    pack_path = Path(registry[pack_name])
    manifest_file = pack_path / "smithpy.json"

    manifest = get_manifest(pack_path)
    if not manifest:
        console.print(f"[red]Error:[/red] Could not load manifest at {manifest_file}")
        return
    loader_version = manifest.loader_version or FABRIC_LOADER_VERSION

    console.print("📦 Finalizing pack...", style="cyan")

    mods_dir = Path.cwd() / manifest.name / "mods"
    if not mods_dir.exists() or not any(mods_dir.iterdir()):
        console.print("[red]No mods found. Run `smithpy build` first.[/red]")
        raise typer.Exit(1)

    if manifest.loader == "fabric":
        installer = Path.cwd() / manifest.name / ".fabric-installer.jar"

        if not installer.exists():
            console.print("Downloading Fabric installer...")
            import urllib.request

            urllib.request.urlretrieve(FABRIC_INSTALLER_URL, installer)

        console.print("Installing Fabric...")
        install_fabric(
            installer=installer,
            mc_version=manifest.minecraft,
            loader_version=loader_version,
            game_dir=Path.cwd() / manifest.name,
        )

        index_file = Path.cwd() / manifest.name / "modrinth.index.json"
        index = json.loads(index_file.read_text())
        index["dependencies"]["fabric-loader"] = FABRIC_LOADER_VERSION
        index_file.write_text(json.dumps(index, indent=2))

        installer.unlink(missing_ok=True)

    pack_name = manifest.name
    zip_path = Path.cwd().parent / f"{pack_name}.zip"

    shutil.make_archive(
        base_name=str(zip_path.with_suffix("")),
        format="zip",
        root_dir=Path.cwd(),
    )

    console.print(f"✅ Exported {zip_path.name}", style="green bold")


@app.command()
def remove(pack_name: str):
    """Completely remove a modpack and unregister it"""
    if not REGISTRY_PATH.exists():
        console.print("[red]No registry found.[/red]")
        raise typer.Exit(1)

    registry = json.loads(REGISTRY_PATH.read_text())

    if pack_name not in registry:
        console.print(f"[red]Pack '{pack_name}' not found in registry.[/red]")
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

    if not Confirm.ask("Are you sure you want to continue?", default=False):
        console.print("Aborted.", style="dim")
        raise typer.Exit()

    # Remove directory
    try:
        if pack_path.exists():
            shutil.rmtree(pack_path)
        else:
            console.print(
                f"[yellow]Warning:[/yellow] Pack directory does not exist: {pack_path}"
            )
    except Exception as e:
        console.print(f"[red]Failed to delete pack directory:[/red] {e}")
        raise typer.Exit(1)

    # Update registry
    del registry[pack_name]
    REGISTRY_PATH.write_text(json.dumps(registry, indent=4))

    console.print(
        f"🗑️  Removed pack [bold cyan]{pack_name}[/bold cyan] successfully.",
        style="green",
    )


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

@app.command()
def self_update_cmd():
    """
    Update SmithPy to the latest version.
    """
    try:
        self_update()
    except subprocess.CalledProcessError:
        raise typer.Exit(code=1)


def main():
    app()


if __name__ == "__main__":
    main()

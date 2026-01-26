from datetime import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import traceback
import urllib.request

import aiohttp
from rich.console import Console
import typer

from modforge_cli.api import ModrinthAPIConfig
from modforge_cli.core import ModDownloader
from modforge_cli.core.models import Manifest, SearchResult

try:
    from modforge_cli.__version__ import __author__, __version__
except ImportError:
    __version__ = "unknown"
    __author__ = "Frank1o3"


def ensure_config_file(path: Path, url: str, label: str, console: Console) -> None:
    """Download config file if missing"""
    if path.exists():
        return

    path.parent.mkdir(parents=True, exist_ok=True)

    console.print(f"[yellow]Missing {label} config.[/yellow] Downloading default…")

    try:
        urllib.request.urlretrieve(url, path)
        console.print(f"[green]✓ {label} config installed at {path}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to download {label} config:[/red] {e}")
        raise typer.Exit(1) from e


# --- Async Helper ---
async def get_api_session() -> aiohttp.ClientSession:
    """Returns a session with the correct ModForge-CLI headers."""
    timeout = aiohttp.ClientTimeout(total=60, connect=10)
    return aiohttp.ClientSession(
        headers={"User-Agent": f"{__author__}/ModForge-CLI/{__version__}"},
        timeout=timeout,
        raise_for_status=False,  # Handle errors manually
    )


def get_manifest(console: Console, path: Path = Path.cwd()) -> Manifest | None:
    """Load and validate manifest file"""
    p = path / "ModForge-CLI.json"
    if not p.exists():
        return None
    try:
        return Manifest.model_validate_json(p.read_text())
    except Exception as e:
        console.print(f"[red]Error parsing manifest:[/red] {e}")
        return None


def save_registry_atomic(registry: dict, path: Path) -> None:
    """
    Atomically save registry to prevent corruption from concurrent access.

    Uses a temp file + atomic rename to ensure the registry is never
    left in a partially-written state.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file in same directory (required for atomic rename)
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, dir=path.parent, prefix=".registry-", suffix=".tmp"
    ) as f:
        json.dump(registry, f, indent=4)
        temp_path = Path(f.name)

    # Atomic rename (POSIX guarantees atomicity)
    try:
        temp_path.replace(path)
    except Exception as e:
        temp_path.unlink(missing_ok=True)
        raise RuntimeError(f"Failed to save registry: {e}") from e


def load_registry(path: Path) -> dict[str, str]:
    """Load registry with error handling"""
    if not path.exists():
        return {}

    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        # Registry is corrupted - back it up and start fresh
        backup = path.with_suffix(f".corrupt-{datetime.now():%Y%m%d-%H%M%S}.json")
        shutil.copy(path, backup)
        print(f"Warning: Corrupted registry backed up to {backup}")
        return {}


def setup_crash_logging() -> Path:
    """Configure crash logging for bug reports"""
    log_dir = Path.home() / ".config" / "ModForge-CLI" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    def excepthook(exc_type, exc_value, exc_traceback) -> None:
        """Log crashes for bug reports"""

        log_file = log_dir / f"crash-{datetime.now():%Y%m%d-%H%M%S}.log"

        with open(log_file, "w") as f:
            f.write(f"ModForge-CLI v{__version__}\n")
            f.write(f"Python {sys.version}\n")
            f.write(f"Platform: {sys.platform}\n\n")
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)

        console = Console()
        console.print(f"\n[red bold]ModForge-CLI crashed![/red bold]")
        console.print(f"[yellow]Crash log saved to:[/yellow] {log_file}")
        console.print("[dim]Please include this file when reporting the issue at:")
        console.print("[dim]https://github.com/Frank1o3/ModForge-CLI/issues\n")

    sys.excepthook = excepthook
    return log_dir


def install_fabric(
    installer: Path,
    mc_version: str,
    loader_version: str,
    game_dir: Path,
) -> None:
    """Install Fabric loader with better error handling"""
    try:
        result = subprocess.run(
            [
                "java",
                "-jar",
                str(installer),
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
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Fabric installation failed:\n{e.stderr}\n\n"
            f"Make sure Java is installed and accessible."
        ) from e
    except FileNotFoundError as e:
        raise RuntimeError("Java not found. Please install Java 17 or higher and try again.") from e


def detect_install_method() -> str:
    """Detect how ModForge-CLI was installed"""
    prefix = Path(sys.prefix)

    if "pipx" in prefix.parts or "pipx" in str(prefix):
        return "pipx"
    return "pip"


def self_update(console: Console) -> None:
    """Update ModForge-CLI to latest version"""
    method = detect_install_method()

    try:
        if method == "pipx":
            console.print("[cyan]Updating ModForge-CLI using pipx...[/cyan]")
            subprocess.run(["pipx", "upgrade", "ModForge-CLI"], check=True)
        else:
            console.print("[cyan]Updating ModForge-CLI using pip...[/cyan]")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "ModForge-CLI"],
                check=True,
            )

        console.print("[green]✓ ModForge-CLI updated successfully.[/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Update failed:[/red] {e}")
        raise


async def run(api: ModrinthAPIConfig, manifest: Manifest, mods_dir: Path, index_file: Path) -> None:
    """Download all mods with progress tracking"""
    async with await get_api_session() as session:
        downloader = ModDownloader(
            api=api,
            mc_version=manifest.minecraft,
            loader=manifest.loader,
            output_dir=mods_dir,
            index_file=index_file,
            session=session,
        )
        await downloader.download_all(manifest.mods)


async def perform_add(
    api: ModrinthAPIConfig,
    name: str,
    manifest: Manifest,
    project_type: str,
    console: Console,
    manifest_file: Path,
) -> None:
    """Search and add a project to the manifest"""
    async with await get_api_session() as session:
        url = api.search(
            name,
            game_versions=[manifest.minecraft],
            loaders=[manifest.loader],
            project_type=project_type,
        )

        try:
            async with session.get(url) as response:
                if response.status != 200:
                    console.print(f"[red]API request failed with status {response.status}[/red]")
                    return

                results = SearchResult.model_validate_json(await response.text())
        except Exception as e:
            console.print(f"[red]Failed to search Modrinth:[/red] {e}")
            return

        if not results or not results.hits:
            console.print(f"[red]No {project_type} found for '{name}'[/red]")
            console.print(f"[dim]Try searching on https://modrinth.com/mods?q={name}[/dim]")
            return

        # Match slug exactly, or use first result
        target_hit = next((h for h in results.hits if h.slug == name), results.hits[0])
        slug = target_hit.slug

        # Add to appropriate list
        target_list = {
            "mod": manifest.mods,
            "resourcepack": manifest.resourcepacks,
            "shaderpack": manifest.shaderpacks,
        }.get(project_type, manifest.mods)

        if slug not in target_list:
            target_list.append(slug)
            try:
                manifest_file.write_text(manifest.model_dump_json(indent=4))
                console.print(f"[green]✓ Added {slug} to {project_type}s[/green]")
            except Exception as e:
                console.print(f"[red]Failed to save manifest:[/red] {e}")
        else:
            console.print(f"[yellow]{slug} is already in the manifest[/yellow]")

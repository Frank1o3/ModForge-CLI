import sys
import subprocess
from pathlib import Path
import urllib.request
from typing import Optional
from modforge_cli.core.models import Manifest, SearchResult
from modforge_cli.api import ModrinthAPIConfig
from modforge_cli.core import ModDownloader

import typer
import aiohttp
from rich.console import Console

try:
    from modforge_cli.__version__ import __author__, __version__
except ImportError:
    __version__ = "unknown"
    __author__ = "Frank1o3"


def ensure_config_file(path: Path, url: str, label: str, console: Console):
    if path.exists():
        return

    path.parent.mkdir(parents=True, exist_ok=True)

    console.print(f"[yellow]Missing {label} config.[/yellow] Downloading default…")

    try:
        urllib.request.urlretrieve(url, path)
        console.print(f"[green]✓ {label} config installed at {path}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to download {label} config:[/red] {e}")
        raise typer.Exit(1)


# --- Async Helper ---
async def get_api_session():
    """Returns a session with the correct ModForge-CLI headers."""
    return aiohttp.ClientSession(
        headers={"User-Agent": f"{__author__}/ModForge-CLI/{__version__}"},
        raise_for_status=True,
    )


def get_manifest(console: Console, path: Path = Path.cwd()) -> Optional[Manifest]:
    p = path / "ModForge-CLI.json"
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


def self_update(console: Console):
    method = detect_install_method()

    if method == "pipx":
        console.print("[cyan]Updating ModForge-CLI using pipx...[/cyan]")
        subprocess.run(["pipx", "upgrade", "ModForge-CLI"], check=True)

    else:
        console.print("[cyan]Updating ModForge-CLI using pip...[/cyan]")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "ModForge-CLI"],
            check=True,
        )

    console.print("[green]ModForge-CLI updated successfully.[/green]")


async def run(
    api: ModrinthAPIConfig, manifest: Manifest, mods_dir: Path, index_file: Path
):
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
):
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
        target_hit = next((h for h in results.hits if h.slug == name), results.hits[0])
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

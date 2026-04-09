"""
Mod management command - List, inspect, and verify mods in a modpack
"""

import asyncio
from pathlib import Path

import aiohttp
from rich.table import Table
import typer

from modforge_cli.api import ModrinthAPIConfig
from modforge_cli.cli.shared import MODRINTH_API, REGISTRY_PATH, console
from modforge_cli.core import get_api_session, get_manifest, load_registry

app = typer.Typer()


@app.command("list")
def list_mods(pack_name: str | None = None, resolved: bool = False) -> None:
    """
    List all mods in the current modpack.

    Shows mod names, slugs, and project IDs from the manifest.
    Use --resolved to also fetch and display actual mod names from Modrinth.

    Examples:
        ModForge-CLI mods list                  # Show manifest entries
        ModForge-CLI mods list --resolved       # Fetch and show actual mod names
        ModForge-CLI mods list --pack-name MyPack
    """
    # Auto-detect pack if not specified
    if not pack_name:
        manifest = get_manifest(console, path=Path.cwd())
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
    manifest = get_manifest(console, pack_path)
    if not manifest:
        console.print(f"[red]Could not load manifest for '{pack_name}'[/red]")
        raise typer.Exit(1)

    if not manifest.mods:
        console.print("[yellow]No mods in this modpack[/yellow]")
        return

    if resolved:
        # Fetch actual mod names from Modrinth
        asyncio.run(_fetch_and_display_mod_info(manifest.mods))
    else:
        # Just show what's in the manifest
        _show_manifest_mods(manifest.mods, manifest.name)


def _show_manifest_mods(mods: list[str], pack_name: str) -> None:
    """Display mods from manifest without API calls"""
    console.print(f"\n[cyan bold]Mods in '{pack_name}' (from manifest):[/cyan bold]\n")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=4)
    table.add_column("Slug / ID", style="green")
    table.add_column("Type", style="dim")

    for idx, mod in enumerate(sorted(mods), 1):
        # Heuristic: project IDs are typically numeric-like strings (e.g., "AANobbMI")
        # Slugs are typically lowercase with dashes
        if any(c.isupper() for c in mod) or len(mod) < 5:
            mod_type = "Project ID"
        else:
            mod_type = "Slug"
        table.add_row(str(idx), mod, mod_type)

    console.print(table)
    console.print(f"\n[dim]Total: {len(mods)} mod(s)[/dim]")
    console.print("[yellow]Tip: Use 'ModForge-CLI mods list --resolved' to fetch actual names[/yellow]\n")


async def _fetch_and_display_mod_info(mod_entries: list[str]) -> None:
    """Fetch mod info from Modrinth API and display"""
    api = ModrinthAPIConfig(MODRINTH_API)

    console.print("\n[cyan bold]Fetching mod information from Modrinth...[/cyan bold]\n")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=4)
    table.add_column("Name", style="green")
    table.add_column("Slug", style="cyan")
    table.add_column("Project ID", style="dim")
    table.add_column("Summary", style="yellow")

    async with await get_api_session() as session:
        tasks = [_fetch_mod_info(api, entry, session) for entry in sorted(mod_entries)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    success_count = 0
    for idx, result in enumerate(results, 1):
        if isinstance(result, BaseException):
            table.add_row(str(idx), "[red]Error[/red]", "[red]Error[/red]", "[red]Error[/red]", "")
            continue

        if result is None:
            table.add_row(str(idx), "[yellow]Not found[/yellow]", "[yellow]N/A[/yellow]", "[yellow]N/A[/yellow]", "")
            continue

        success_count += 1
        name, slug, project_id, summary = result
        # Truncate summary if too long
        if summary and len(summary) > 60:
            summary = summary[:57] + "..."
        table.add_row(str(idx), name, slug, project_id, summary or "")

    console.print(table)
    console.print(f"\n[dim]Resolved: {success_count}/{len(mod_entries)} mod(s)[/dim]\n")


async def _fetch_mod_info(
    api: ModrinthAPIConfig, entry: str, session: aiohttp.ClientSession
) -> tuple[str, str, str, str] | None:
    """
    Fetch mod information from Modrinth API.

    Args:
        entry: Can be either a slug or project ID
        session: Active aiohttp session

    Returns:
        Tuple of (name, slug, project_id, summary) or None on failure
    """
    url = api.project(entry)

    try:
        async with session.get(url) as response:
            if response.status != 200:
                console.print(f"[dim]  Warning: Failed to fetch '{entry}' (HTTP {response.status})[/dim]")
                return None

            data = await response.json()

            name = data.get("title", entry)
            slug = data.get("slug", entry)
            project_id = data.get("id", entry)
            summary = data.get("description", "")

            return (name, slug, project_id, summary)

    except Exception as e:
        console.print(f"[dim]  Error fetching '{entry}': {e}[/dim]")
        return None

"""
Modpack operations - Add, resolve, build
"""

import asyncio
from pathlib import Path

import typer

from modforge_cli.api import ModrinthAPIConfig
from modforge_cli.cli.shared import MODRINTH_API, POLICY_PATH, REGISTRY_PATH, console
from modforge_cli.core import (
    ModPolicy,
    ModResolver,
    get_api_session,
    get_manifest,
    load_registry,
    perform_add,
    run,
)

app = typer.Typer()

# Initialize API
api = ModrinthAPIConfig(MODRINTH_API)


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

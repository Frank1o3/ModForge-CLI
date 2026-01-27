"""
Setup command - Initialize a new modpack project
"""

import json
from pathlib import Path

import typer

from modforge_cli.cli.shared import FABRIC_LOADER_VERSION, REGISTRY_PATH, console
from modforge_cli.core import Manifest, load_registry, save_registry_atomic

app = typer.Typer()


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
        "files": [],
        "dependencies": {loader_key: loader_version, "minecraft": mc},
    }
    (pack_dir / "modrinth.index.json").write_text(json.dumps(index_data, indent=2))

    # Register project
    registry = load_registry(REGISTRY_PATH)
    registry[name] = str(pack_dir.absolute())
    save_registry_atomic(registry, REGISTRY_PATH)

    console.print(f"[green]✓ Project '{name}' created at {pack_dir}[/green]")
    console.print(f"[dim]Run 'cd {name}' to enter the project[/dim]")

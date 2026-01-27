"""
SKLauncher integration command
"""

from datetime import datetime
import json
from pathlib import Path
import platform
import shutil

import typer

from modforge_cli.cli.shared import FABRIC_LOADER_VERSION, REGISTRY_PATH, console
from modforge_cli.core import get_manifest, load_registry

app = typer.Typer()


@app.command()
def sklauncher(pack_name: str | None = None, profile_name: str | None = None) -> None:
    """Create SKLauncher-compatible profile (alternative to export)"""

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

    # Check if mods are built
    mods_dir = pack_path / "mods"
    if not mods_dir.exists() or not any(mods_dir.iterdir()):
        console.print("[red]No mods found. Run 'ModForge-CLI build' first[/red]")
        raise typer.Exit(1)

    # Get Minecraft directory
    if platform.system() == "Windows":
        minecraft_dir = Path.home() / "AppData" / "Roaming" / ".minecraft"
    elif platform.system() == "Darwin":
        minecraft_dir = Path.home() / "Library" / "Application Support" / "minecraft"
    else:
        minecraft_dir = Path.home() / ".minecraft"

    if not minecraft_dir.exists():
        console.print(f"[red]Minecraft directory not found: {minecraft_dir}[/red]")
        raise typer.Exit(1)

    # Use pack name if profile name not specified
    if not profile_name:
        profile_name = pack_name

    console.print(f"[cyan]Creating SKLauncher profile '{profile_name}'...[/cyan]")

    # Create instance directory
    instance_dir = minecraft_dir / "instances" / profile_name
    instance_dir.mkdir(parents=True, exist_ok=True)

    # Copy mods
    dst_mods = instance_dir / "mods"
    if dst_mods.exists():
        shutil.rmtree(dst_mods)
    shutil.copytree(mods_dir, dst_mods)
    mod_count = len(list(dst_mods.glob("*.jar")))
    console.print(f"[green]✓ Copied {mod_count} mods[/green]")

    # Copy overrides
    overrides_src = pack_path / "overrides"
    if overrides_src.exists():
        for item in overrides_src.iterdir():
            dst = instance_dir / item.name
            if item.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(item, dst)
            else:
                shutil.copy2(item, dst)
        console.print("[green]✓ Copied overrides[/green]")

    # Update launcher_profiles.json
    profiles_file = minecraft_dir / "launcher_profiles.json"

    if profiles_file.exists():
        profiles_data = json.loads(profiles_file.read_text())
    else:
        profiles_data = {"profiles": {}, "settings": {}, "version": 3}

    # Create profile entry
    profile_id = profile_name.lower().replace(" ", "_").replace("-", "_")
    loader_version = manifest.loader_version or FABRIC_LOADER_VERSION

    profiles_data["profiles"][profile_id] = {
        "name": profile_name,
        "type": "custom",
        "created": datetime.now().isoformat() + "Z",
        "lastUsed": datetime.now().isoformat() + "Z",
        "icon": "Furnace_On",
        "lastVersionId": f"fabric-loader-{loader_version}-{manifest.minecraft}",
        "gameDir": str(instance_dir),
    }

    # Save profiles
    profiles_file.write_text(json.dumps(profiles_data, indent=2))

    console.print("\n[green bold]✓ SKLauncher profile created![/green bold]")
    console.print(f"\n[cyan]Profile:[/cyan] {profile_name}")
    console.print(f"[cyan]Location:[/cyan] {instance_dir}")
    console.print(f"[cyan]Version:[/cyan] fabric-loader-{loader_version}-{manifest.minecraft}")
    console.print("\n[yellow]Next steps:[/yellow]")
    console.print("  1. Close SKLauncher if it's open")
    console.print("  2. Restart SKLauncher")
    console.print(f"  3. Select profile '{profile_name}'")
    console.print("  4. If Fabric isn't installed, install it from SKLauncher:")
    console.print(f"     - MC: {manifest.minecraft}")
    console.print(f"     - Fabric: {loader_version}")

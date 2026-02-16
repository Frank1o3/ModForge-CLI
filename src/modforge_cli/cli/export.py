"""
Export and validation commands
"""

import json
from pathlib import Path
import zipfile
from zipfile import ZIP_DEFLATED, ZipFile

import typer

from modforge_cli.cli.shared import REGISTRY_PATH, console
from modforge_cli.core import get_manifest, load_registry

app = typer.Typer()


@app.command()
def export(pack_name: str | None = None) -> None:
    """Create final .mrpack file"""

    # Resolve pack name
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

    console.print("[cyan]Exporting modpack...[/cyan]")

    index_file = pack_path / "modrinth.index.json"

    if not index_file.exists():
        console.print("[red]No modrinth.index.json found[/red]")
        raise typer.Exit(1)

    # Validate index JSON before export
    try:
        index_data = json.loads(index_file.read_text())
    except json.JSONDecodeError as e:
        console.print("[red]Invalid modrinth.index.json[/red]")
        console.print(f"[dim]{e}[/dim]")
        raise typer.Exit(1) from e

    if not index_data.get("files"):
        console.print("[yellow]Warning: No files registered in index[/yellow]")
        console.print("[yellow]Run 'ModForge-CLI build' if this is unintended.[/yellow]")

    # Output file (.mrpack extension)
    mrpack_path = pack_path.parent / f"{pack_name}.mrpack"

    # Create archive
    with ZipFile(mrpack_path, "w", ZIP_DEFLATED) as zipf:
        for file_path in pack_path.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(pack_path)
                zipf.write(file_path, arcname)

    console.print(f"[green bold]✓ Exported to {mrpack_path}[/green bold]")

    # ---- Summary ----
    file_count = len(index_data.get("files", []))

    console.print("\n[cyan]Summary:[/cyan]")
    console.print(f"  Files registered in index: {file_count}")
    console.print(f"  Minecraft: {index_data['dependencies'].get('minecraft')}")

    for loader in ["fabric-loader", "quilt-loader", "forge", "neoforge"]:
        if loader in index_data["dependencies"]:
            console.print(f"  Loader: {loader} {index_data['dependencies'][loader]}")

    has_env = any("env" in f for f in index_data.get("files", []))
    if has_env:
        console.print("  [green]✓ Environment data included[/green]")
    else:
        console.print("  [yellow]⚠ No environment data (older format)[/yellow]")

    console.print("\n[dim]Import this in SKLauncher, Prism, ATLauncher, etc.[/dim]")


@app.command()
def validate(mrpack_file: str | None = None) -> None:
    """Validate .mrpack file for launcher compatibility"""

    if not mrpack_file:
        # Look for .mrpack in current directory
        mrpacks = list(Path.cwd().glob("*.mrpack"))
        if not mrpacks:
            console.print("[red]No .mrpack file found in current directory[/red]")
            console.print("[yellow]Usage: ModForge-CLI validate <file.mrpack>[/yellow]")
            raise typer.Exit(1)
        mrpack_path = mrpacks[0]
    else:
        mrpack_path = Path(mrpack_file)

    if not mrpack_path.exists():
        console.print(f"[red]File not found: {mrpack_path}[/red]")
        raise typer.Exit(1)

    console.print(f"[cyan]Validating {mrpack_path.name}...[/cyan]\n")

    issues = []
    warnings = []

    try:
        with zipfile.ZipFile(mrpack_path, "r") as z:
            files = z.namelist()

            # Check for modrinth.index.json
            if "modrinth.index.json" not in files:
                console.print("[red]❌ CRITICAL: modrinth.index.json not found at root[/red]")
                raise typer.Exit(1)

            console.print("[green]✅ modrinth.index.json found[/green]")

            # Read and validate index
            index_data = json.loads(z.read("modrinth.index.json"))

            # Check required fields
            required = ["formatVersion", "game", "versionId", "name", "dependencies"]
            for field in required:
                if field not in index_data:
                    issues.append(f"Missing required field: {field}")
                    console.print(f"[red]❌ Missing: {field}[/red]")
                else:
                    value = index_data[field]
                    if isinstance(value, dict):
                        console.print(f"[green]✅ {field}[/green]")
                    else:
                        console.print(f"[green]✅ {field}: {value}[/green]")

            # Check optional summary
            if "summary" not in index_data:
                warnings.append("Missing optional summary field")
                console.print("[yellow]⚠️  Missing summary (optional but recommended)[/yellow]")
            else:
                console.print(f"[green]✅ summary: {index_data['summary'][:50]}...[/green]")

            # Check dependencies
            deps = index_data.get("dependencies", {})
            if "minecraft" not in deps:
                issues.append("Missing minecraft in dependencies")
                console.print("[red]❌ Missing: minecraft version[/red]")
            else:
                console.print(f"[green]✅ Minecraft: {deps['minecraft']}[/green]")

            # Check for loader
            loaders = ["fabric-loader", "quilt-loader", "forge", "neoforge"]
            has_loader = any(l in deps for l in loaders)

            if not has_loader:
                issues.append("No mod loader in dependencies")
                console.print("[red]❌ Missing mod loader[/red]")
            else:
                for loader in loaders:
                    if loader in deps:
                        console.print(f"[green]✅ Loader: {loader} = {deps[loader]}[/green]")

            # Check files array
            files_list = index_data.get("files", [])
            console.print(f"\n[cyan]📦 Files registered: {len(files_list)}[/cyan]")

            if len(files_list) == 0:
                warnings.append("No files in array (pack might not work)")
                console.print("[yellow]⚠️  WARNING: files array is empty[/yellow]")
            else:
                # Check first file structure
                sample = files_list[0]
                file_required = ["path", "hashes", "downloads", "fileSize"]

                missing_fields = [f for f in file_required if f not in sample]
                if missing_fields:
                    issues.append(f"Files missing fields: {missing_fields}")
                    console.print(f"[red]❌ Files missing: {', '.join(missing_fields)}[/red]")
                else:
                    console.print("[green]✅ File structure looks good[/green]")

                # Check path security
                for file_entry in files_list:
                    path = file_entry.get("path", "")
                    if ".." in path or path.startswith(("/", "\\")):
                        issues.append(f"Security: invalid path: {path}")
                        console.print(f"[red]❌ SECURITY: Invalid path: {path}[/red]")

                # Check hashes
                if "hashes" in sample:
                    if "sha1" not in sample["hashes"]:
                        issues.append("Files missing sha1 hash")
                        console.print("[red]❌ Missing sha1 hashes[/red]")
                    else:
                        console.print("[green]✅ sha1 hashes present[/green]")

                    if "sha512" not in sample["hashes"]:
                        warnings.append("Files missing sha512 hash")
                        console.print("[yellow]⚠️  Missing sha512 hashes (optional)[/yellow]")
                    else:
                        console.print("[green]✅ sha512 hashes present[/green]")

                # Check env field (NEW)
                if "env" not in sample:
                    warnings.append("Files missing env field")
                    console.print("[yellow]⚠️  Missing env field (recommended)[/yellow]")
                else:
                    env = sample["env"]
                    if "client" in env and "server" in env:
                        console.print("[green]✅ env field present[/green]")
                    else:
                        warnings.append("env field incomplete")
                        console.print("[yellow]⚠️  env field incomplete[/yellow]")

            # Check for overrides and server-overrides
            has_overrides = any(f.startswith("overrides/") for f in files)
            has_server_overrides = any(f.startswith("server-overrides/") for f in files)

            if has_overrides:
                console.print("[green]✅ overrides/ folder present[/green]")
            else:
                console.print("[dim]No overrides/ folder (optional)[/dim]")

            if has_server_overrides:
                console.print("[green]✅ server-overrides/ folder present[/green]")
            else:
                console.print("[dim]No server-overrides/ folder (optional)[/dim]")

        # Summary
        console.print("\n" + "=" * 60)

        if issues:
            console.print(f"\n[red bold]❌ CRITICAL ISSUES ({len(issues)}):[/red bold]")
            for issue in issues:
                console.print(f"  [red]• {issue}[/red]")

        if warnings:
            console.print(f"\n[yellow bold]⚠️  WARNINGS ({len(warnings)}):[/yellow bold]")
            for warning in warnings:
                console.print(f"  [yellow]• {warning}[/yellow]")

        if not issues and not warnings:
            console.print("\n[green bold]✅ All checks passed![/green bold]")
            console.print("[dim]Pack should work in all Modrinth-compatible launchers[/dim]")
        elif not issues:
            console.print("\n[green]✅ No critical issues[/green]")
            console.print("[dim]Pack should work, but consider addressing warnings[/dim]")
        else:
            console.print("\n[red bold]❌ Pack has critical issues[/red bold]")
            console.print("[yellow]Run 'ModForge-CLI build' again to fix[/yellow]")
            raise typer.Exit(1)

    except zipfile.BadZipFile as e:
        console.print("[red]❌ ERROR: Not a valid ZIP/MRPACK file[/red]")
        raise typer.Exit(1) from e
    except json.JSONDecodeError as e:
        console.print("[red]❌ ERROR: Invalid JSON in modrinth.index.json[/red]")
        console.print(f"[dim]{e}[/dim]")
        raise typer.Exit(1) from e

"""
Utility commands - Doctor and self-update
"""

import subprocess
import sys

import typer

from modforge_cli.cli.shared import MODRINTH_API, POLICY_PATH, REGISTRY_PATH, console
from modforge_cli.core import load_registry, self_update as core_self_update

app = typer.Typer()


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
        subprocess.run(["java", "-version"], capture_output=True, text=True, check=True)
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
        core_self_update(console)
    except Exception as e:
        console.print(f"[red]Update failed:[/red] {e}")
        raise typer.Exit(1) from e

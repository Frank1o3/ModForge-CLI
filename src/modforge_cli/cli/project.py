"""
Project management commands - List and remove projects
"""

from pathlib import Path
import shutil

from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table
import typer

from modforge_cli.cli.shared import REGISTRY_PATH, console
from modforge_cli.core import load_registry, save_registry_atomic

app = typer.Typer()


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

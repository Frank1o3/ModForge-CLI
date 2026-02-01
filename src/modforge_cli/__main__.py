"""
Main CLI entry point - Registers all commands
"""

import logging

from pyfiglet import figlet_format
from rich.panel import Panel
from rich.text import Text
import typer

from modforge_cli.cli import export, modpack, project, setup, sklauncher, utils
from modforge_cli.cli.shared import (
    DEFAULT_MODRINTH_API_URL,
    DEFAULT_POLICY_URL,
    MODRINTH_API,
    POLICY_PATH,
    console,
    get_version_info,
)
from modforge_cli.core import ensure_config_file, setup_crash_logging

# Get version info
__version__, __author__ = get_version_info()

# Create main app
app = typer.Typer(
    add_completion=False,
    no_args_is_help=False,
)

# Setup crash logging


LOG_DIR = setup_crash_logging()

# Ensure configs exist
ensure_config_file(MODRINTH_API, DEFAULT_MODRINTH_API_URL, "Modrinth API", console)
ensure_config_file(POLICY_PATH, DEFAULT_POLICY_URL, "Policy", console)


def render_banner() -> None:
    """Renders a stylized banner"""
    width = console.width
    font = "slant" if width > 60 else "small"

    ascii_art = figlet_format("ModForge-CLI", font=font)
    banner_text = Text(ascii_art, style="bold cyan")

    info_line = Text.assemble(
        (" ⛏  ", "yellow"),
        (f"v{__version__}", "bold white"),
        (" | ", "dim"),
        ("Created by ", "italic white"),
        (f"{__author__}", "bold magenta"),
    )

    console.print(
        Panel(
            Text.assemble(banner_text, "\n", info_line),
            border_style="blue",
            padding=(1, 2),
            expand=False,
        ),
        justify="left",
    )


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: bool | None = typer.Option(None, "--version", "-v", help="Show version and exit"),
    verbose: bool | None = typer.Option(None, "--verbose", help="Enable verbose logging"),
) -> None:
    """ModForge-CLI: A powerful Minecraft modpack manager for Modrinth."""

    if verbose:
        # Enable verbose logging
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(LOG_DIR / f"modforge-{__version__}.log"),
                logging.StreamHandler(),
            ],
        )

    if version:
        console.print(f"ModForge-CLI Version: [bold cyan]{__version__}[/bold cyan]")
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        render_banner()
        console.print("\n[bold yellow]Usage:[/bold yellow] ModForge-CLI [COMMAND] [ARGS]...")
        console.print("\n[bold cyan]Core Commands:[/bold cyan]")
        console.print("  [green]setup[/green]       Initialize a new modpack project")
        console.print("  [green]ls[/green]          List all registered projects")
        console.print("  [green]add[/green]         Add a mod/resource/shader to manifest")
        console.print("  [green]resolve[/green]     Resolve all dependencies")
        console.print("  [green]build[/green]       Download files and setup loader")
        console.print("  [green]export[/green]      Create the final .mrpack")
        console.print("  [green]validate[/green]    Check .mrpack for issues")
        console.print("  [green]sklauncher[/green]  Create SKLauncher profile (no .mrpack)")
        console.print("  [green]remove[/green]      Remove a modpack project")
        console.print("\nRun [white]ModForge-CLI --help[/white] for details.\n")


# Register all command groups
app.command()(setup.setup)
app.add_typer(project.app, name="project", help="Project management commands")
app.command("ls")(project.list_projects)
app.command()(project.remove)
app.command()(modpack.add)
app.command()(modpack.resolve)
app.command()(modpack.build)
app.command()(export.export)
app.command()(export.validate)
app.command()(sklauncher.sklauncher)


def main() -> None:
    """Main entry point"""
    app()


if __name__ == "__main__":
    main()

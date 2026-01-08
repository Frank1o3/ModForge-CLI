"""
cli.py - Entry point for the SmithPy CLI
"""
from pathlib import Path
from typing import Optional

import typer
from colorama import init
from pyfiglet import figlet_format
from rich.console import Console
from rich.table import Table

from smithpy.api import ModrinthAPIConfig

# Initialize colorama for Windows compatibility
init(autoreset=True)

app = typer.Typer()
console = Console()


def show_banner():
    """Display the SmithPy ASCII banner"""
    banner = figlet_format("SmithPy", font="slant")
    console.print(banner, style="cyan bold")
    console.print("⛏  CLI tool for Minecraft modpack management\n", style="dim")


@app.command()
def setup(
    name: str = typer.Argument(..., help="Name of the modpack"),
    mc_version: str = typer.Option(..., "--mc-version", "-v", help="Minecraft version (e.g., 1.21.1)"),
    loader: str = typer.Option("fabric", "--loader", "-l", help="Mod loader (fabric/forge/quilt)"),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory (default: ./modpacks)")
):
    """Setup directory structure for a new modpack"""
    
    # Use current working directory if no output specified
    base_dir = output_dir or Path.cwd() / "modpacks"
    pack_dir = base_dir / name
    
    try:
        # Create directory structure
        dirs_to_create = {
            "mods": pack_dir / "mods",
            "resourcepacks": pack_dir / "resourcepacks",
            "shaderpacks": pack_dir / "shaderpacks",  # Fixed typo: shaderpack -> shaderpacks
            "config": pack_dir / "config",
        }
        
        for dir_name, dir_path in dirs_to_create.items():
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Create modrinth.index.json with basic structure
        modrinth_index = pack_dir / "modrinth.index.json"
        if not modrinth_index.exists():
            import json
            index_data = {
                "formatVersion": 1,
                "game": "minecraft",
                "versionId": "1.0.0",
                "name": name,
                "dependencies": {
                    "minecraft": mc_version,
                    loader: "*"
                },
                "files": []
            }
            modrinth_index.write_text(json.dumps(index_data, indent=2))
        
        console.print(f"\n Modpack '{name}' created successfully!", style="green bold")
        console.print(f" Location: {pack_dir.absolute()}", style="dim")
        console.print(f" Minecraft: {mc_version} | Loader: {loader}", style="dim")
        
        # Show directory tree
        console.print("\n Directory structure:", style="yellow")
        for dir_name in dirs_to_create.keys():
            console.print(f"  ├── {dir_name}/", style="blue")
        console.print("  └── modrinth.index.json", style="blue")
        
    except Exception as e:
        console.print(f"❌ Error creating modpack: {e}", style="red bold")
        raise typer.Exit(1)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of results"),
    project_type: str = typer.Option("mod", "--type", "-t", help="Project type (mod/modpack/resourcepack)"),
):
    """Search for projects on Modrinth"""
    
    try:
        # Get config path relative to package
        config_path = Path(__file__).parent.parent.parent / "configs" / "modrinth_api.json"
        api = ModrinthAPIConfig(config_path)
        
        import requests
        
        search_url = api.search(
            query=query,
            limit=limit,
            project_type=project_type
        )
        
        console.print(f"\n🔍 Searching for '{query}'...\n", style="yellow")
        
        response = requests.get(search_url)
        response.raise_for_status()
        results = response.json()
        
        if not results.get("hits"):
            console.print("No results found.", style="red")
            return
        
        # Create a nice table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Slug", style="cyan")
        table.add_column("Title", style="green")
        table.add_column("Downloads", justify="right", style="yellow")
        table.add_column("Type", style="blue")
        
        for hit in results["hits"][:limit]:
            table.add_row(
                hit["slug"],
                hit["title"][:40] + "..." if len(hit["title"]) > 40 else hit["title"],
                f"{hit['downloads']:,}",
                hit["project_type"]
            )
        
        console.print(table)
        console.print(f"\n📊 Showing {len(results['hits'][:limit])} of {results['total_hits']} results", style="dim")
        
    except FileNotFoundError:
        console.print(f"❌ Config file not found: {config_path}", style="red bold")
        raise typer.Exit(1)
    except requests.RequestException as e:
        console.print(f"❌ API request failed: {e}", style="red bold")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red bold")
        raise typer.Exit(1)


@app.command()
def install(
    mods: list[str] = typer.Argument(..., help="List of mod slugs to install"),
    mc_version: str = typer.Option(..., "--mc-version", "-v", help="Minecraft version"),
    loader: str = typer.Option("fabric", "--loader", "-l", help="Mod loader"),
):
    """Install mods from Modrinth"""
    
    console.print(f"\n Installing {len(mods)} mod(s)...", style="yellow bold")
    console.print(f"🎮 Target: Minecraft {mc_version} ({loader})\n", style="dim")
    
    for mod in mods:
        console.print(f"  • {mod}", style="cyan")
    
    console.print("\n  Installation not yet implemented", style="yellow")
    console.print("Coming soon: dependency resolution, version selection, and downloads!", style="dim")


@app.callback()
def callback():
    """
    SmithPy - A powerful CLI tool for Minecraft modpack management
    """
    pass


def main() -> None:
    """Main CLI entry point"""
    show_banner()
    app()


if __name__ == "__main__":
    main()
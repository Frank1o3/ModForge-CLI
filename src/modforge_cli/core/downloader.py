from __future__ import annotations

import asyncio
from collections.abc import Iterable
import hashlib
import json
from pathlib import Path

import aiohttp
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

from modforge_cli.api import ModrinthAPIConfig

console = Console()


class ModDownloader:
    def __init__(
        self,
        api: ModrinthAPIConfig,
        mc_version: str,
        loader: str,
        output_dir: Path,
        index_file: Path,
        session: aiohttp.ClientSession,
    ):
        self.api = api
        self.mc_version = mc_version
        self.loader = loader
        self.output_dir = output_dir
        self.index_file = index_file
        self.session = session

        self.index = json.loads(index_file.read_text())

        # Ensure files array exists
        if "files" not in self.index:
            self.index["files"] = []

    def _select_compatible_version(self, versions: list[dict]) -> dict | None:
        """
        Select the most appropriate version based on:
        1. Loader compatibility (fabric/forge/quilt/neoforge)
        2. Minecraft version
        3. Version type (prefer release > beta > alpha)
        """
        # Normalize loader name for comparison
        loader_lower = self.loader.lower()

        # Filter versions that match both MC version and loader
        compatible = []
        for v in versions:
            # Check if MC version matches
            if self.mc_version not in v.get("game_versions", []):
                continue

            # Check if loader matches (case-insensitive)
            loaders = [l.lower() for l in v.get("loaders", [])]
            if loader_lower not in loaders:
                continue

            compatible.append(v)

        if not compatible:
            return None

        # Prioritize by version type: release > beta > alpha
        version_priority = {"release": 3, "beta": 2, "alpha": 1}

        def version_score(v) -> int:
            vtype = v.get("version_type", "alpha")
            return version_priority.get(vtype, 0)

        # Sort by version type, then by date (newest first)
        compatible.sort(key=lambda v: (version_score(v), v.get("date_published", "")), reverse=True)

        return compatible[0]

    async def download_all(self, project_ids: Iterable[str]) -> None:
        """
        Download all mods and register them in modrinth.index.json.

        The index format follows Modrinth's standard:
        - files: array of all mods with hashes, URLs, and metadata
        - dependencies: MC version and loader version
        """
        tasks = [self._download_project(pid) for pid in project_ids]

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            console=console,
        ) as progress:
            task_id = progress.add_task("Downloading mods", total=len(tasks))
            for coro in asyncio.as_completed(tasks):
                await coro
                progress.advance(task_id)

        # Write updated index
        self.index_file.write_text(json.dumps(self.index, indent=2))

    async def _download_project(self, project_id: str) -> None:
        # 1. Fetch all versions for this project
        url = self.api.project_versions(project_id)

        try:
            async with self.session.get(url) as r:
                if r.status != 200:
                    console.print(
                        f"[red]Failed to fetch versions for {project_id}: HTTP {r.status}[/red]"
                    )
                    return
                versions = await r.json()
        except Exception as e:
            console.print(f"[red]Error fetching {project_id}: {e}[/red]")
            return

        if not versions:
            console.print(f"[yellow]No versions found for {project_id}[/yellow]")
            return

        # 2. Select compatible version
        version = self._select_compatible_version(versions)

        if not version:
            console.print(
                f"[yellow]No compatible version for {project_id}[/yellow]\n"
                f"[dim]  Required: MC {self.mc_version}, Loader: {self.loader}[/dim]"
            )
            return

        # 3. Find primary file
        files = version.get("files", [])
        primary_file = next((f for f in files if f.get("primary")), None)

        if not primary_file and files:
            # Fallback to first file if no primary is marked
            primary_file = files[0]

        if not primary_file:
            console.print(
                f"[yellow]No files found for {project_id} version {version.get('version_number')}[/yellow]"
            )
            return

        # 4. Download file to mods/ directory
        dest = self.output_dir / primary_file["filename"]

        # Check if already registered in index
        existing_entry = next(
            (f for f in self.index["files"] if f["path"] == f"mods/{primary_file['filename']}"),
            None,
        )

        if existing_entry and dest.exists():
            # Verify hash matches
            existing_hash = hashlib.sha1(dest.read_bytes()).hexdigest()
            if existing_hash == primary_file["hashes"]["sha1"]:
                console.print(f"[dim]✓ {primary_file['filename']} (cached)[/dim]")
                return

        # Download the file
        try:
            async with self.session.get(primary_file["url"]) as r:
                if r.status != 200:
                    console.print(
                        f"[red]Failed to download {primary_file['filename']}: HTTP {r.status}[/red]"
                    )
                    return
                data = await r.read()
                dest.write_bytes(data)
        except Exception as e:
            console.print(f"[red]Download error for {primary_file['filename']}: {e}[/red]")
            return

        # 5. Verify hash
        sha1 = hashlib.sha1(data).hexdigest()
        sha512 = hashlib.sha512(data).hexdigest()

        if sha1 != primary_file["hashes"]["sha1"]:
            dest.unlink(missing_ok=True)
            raise RuntimeError(
                f"Hash mismatch for {primary_file['filename']}\n"
                f"  Expected: {primary_file['hashes']['sha1']}\n"
                f"  Got:      {sha1}"
            )

        # 6. Register in index (Modrinth format)
        file_entry = {
            "path": f"mods/{primary_file['filename']}",
            "hashes": {"sha1": sha1, "sha512": sha512},
            "downloads": [primary_file["url"]],
            "fileSize": primary_file["size"],
        }

        # Remove existing entry if present (update scenario)
        self.index["files"] = [f for f in self.index["files"] if f["path"] != file_entry["path"]]

        # Add new entry
        self.index["files"].append(file_entry)

        console.print(
            f"[green]✓[/green] {primary_file['filename']} "
            f"[dim](v{version.get('version_number')}, {self.loader})[/dim]"
        )

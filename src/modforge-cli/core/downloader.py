from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Iterable

import aiohttp
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

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

    async def download_all(self, project_ids: Iterable[str]):
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

        self.index_file.write_text(json.dumps(self.index, indent=2))

    async def _download_project(self, project_id: str):
        # 1. Fetch compatible version
        url = self.api.project_versions(
            project_id
        )

        async with self.session.get(url) as r:
            versions = await r.json()

        if not versions:
            console.print(f"[yellow]No compatible version for {project_id}[/yellow]")
            return

        version = versions[0]
        file = next(f for f in version["files"] if f["primary"])

        # 2. Download file
        dest = self.output_dir / file["filename"]
        async with self.session.get(file["url"]) as r:
            data = await r.read()
            dest.write_bytes(data)

        # 3. Verify hash
        sha1 = hashlib.sha1(data).hexdigest()
        if sha1 != file["hashes"]["sha1"]:
            raise RuntimeError(f"Hash mismatch for {file['filename']}")

        # 4. Register in index
        self.index["files"].append(
            {
                "path": f"mods/{file['filename']}",
                "hashes": {"sha1": sha1},
                "downloads": [file["url"]],
                "fileSize": file["size"],
            }
        )
